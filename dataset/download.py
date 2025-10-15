#!/usr/bin/env python3
"""
Wikipedia subject-scoped PDF builder — polite, resumable, logged.

Features
- Skips existing PDFs unless --overwrite
- Bounded concurrency + global requests-per-second limiter
- Retries on 429/5xx/timeouts with exponential backoff + jitter and honors Retry-After
- Reproducible sampling with --seed
- Standard logging to console (and optional file)

Example:
  uv run dataset/download.py \
    --root "Category:Tudor England" \
    --root "Category:House of Tudor" \
    --root "Category:People of the Tudor period" \
    --root "Category:16th-century English nobility" \
    --root "Category:Court of Henry VIII" \
    --root "Category:Court of Elizabeth I" \
    --depth 1 \
    --sample 50 \
    --out pdfs/tudor \
    --concurrency 6 \
    --rps 2 \
    --log-level INFO
"""

from __future__ import annotations
import argparse
import asyncio
import logging
import math
import random
import time
import urllib.parse
from collections import deque
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import aiohttp
import requests

# ---------- Endpoints / UA ----------
API = "https://en.wikipedia.org/w/api.php"
REST_PDF = "https://en.wikipedia.org/api/rest_v1/page/pdf/{title}"
UA = "conversational-agent/1.0 (contact: bssmith925@gmail.com)"

REQS = requests.Session()
REQS.headers.update({"User-Agent": UA})

# ---------- Logging ----------
logger = logging.getLogger("wiki_pdf_builder")

def setup_logging(level: str, log_file: Optional[Path]) -> None:
    logger.setLevel(getattr(logging, level.upper()))
    fmt = logging.Formatter(fmt="%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S")
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    ch.setLevel(getattr(logging, level.upper()))
    logger.handlers.clear()
    logger.addHandler(ch)
    if log_file:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(fmt)
        fh.setLevel(getattr(logging, level.upper()))
        logger.addHandler(fh)

# ---------- MediaWiki Action API ----------
def mw_api(params: Dict, tries: int = 3, backoff: float = 1.5) -> Dict:
    params = {"format": "json", "formatversion": 2, **params}
    for attempt in range(tries):
        r = REQS.get(API, params=params, timeout=30)
        if r.status_code in (429,) or r.status_code >= 500:
            logger.debug("mw_api backoff: status %s (attempt %d)", r.status_code, attempt + 1)
            if attempt + 1 == tries:
                r.raise_for_status()
            time.sleep(backoff ** (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()
    return {}

def gather_category_pages(roots: Iterable[str], depth: int = 1, limit_per_cat: int = 1000) -> Set[str]:
    to_visit: List[Tuple[str, int]] = [(root, 0) for root in roots]
    seen_cats: Set[str] = set()
    pages: Set[str] = set()
    while to_visit:
        cat, d = to_visit.pop()
        if cat in seen_cats or d > depth:
            continue
        seen_cats.add(cat)
        logger.debug("Visiting category '%s' at depth %d", cat, d)

        cmcontinue = None
        fetched = 0
        while True:
            params = {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": cat,
                "cmprop": "title|type",
                "cmlimit": "500",
            }
            if cmcontinue:
                params["cmcontinue"] = cmcontinue
            data = mw_api(params)
            cms = data.get("query", {}).get("categorymembers", [])
            for item in cms:
                if item.get("type") == "page":
                    pages.add(item["title"])
                elif item.get("type") == "subcat" and d < depth:
                    to_visit.append((item["title"], d + 1))
            fetched += len(cms)
            cmcontinue = data.get("continue", {}).get("cmcontinue")
            if not cmcontinue or fetched >= limit_per_cat:
                break
        time.sleep(0.1)  # small courtesy pause
    return pages

def search_pages(query: str, max_results: int = 500) -> Set[str]:
    titles: Set[str] = set()
    sroffset = 0
    while len(titles) < max_results:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": 50,
            "srnamespace": 0,
            "sroffset": sroffset,
        }
        data = mw_api(params)
        results = data.get("query", {}).get("search", [])
        if not results:
            break
        for hit in results:
            titles.add(hit["title"])
        sroffset = data.get("continue", {}).get("sroffset")
        if not sroffset:
            break
        time.sleep(0.1)
    return titles

# ---------- RPS limiter ----------
class RPSLimiter:
    """Limit request start rate to ~rps (per second)."""
    def __init__(self, rps: float):
        self.rps = max(0.1, rps)
        self.window = deque()
        self.lock = asyncio.Lock()
    async def wait(self):
        async with self.lock:
            now = time.monotonic()
            while self.window and now - self.window[0] >= 1.0:
                self.window.popleft()
            if len(self.window) >= math.floor(self.rps):
                sleep_time = 1.0 - (now - self.window[0])
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                now = time.monotonic()
                while self.window and now - self.window[0] >= 1.0:
                    self.window.popleft()
            self.window.append(time.monotonic())

# ---------- Download helpers ----------
def pdf_path_for(title: str, out_dir: Path) -> Path:
    safe_stem = title.replace("/", " ").strip()
    return out_dir / f"{safe_stem}.pdf"

async def fetch_pdf(
    session: aiohttp.ClientSession,
    title: str,
    out_dir: Path,
    timeout: int,
    retries: int,
    base_backoff: float,
    overwrite: bool,
    semaphore: asyncio.Semaphore,
    rps_limiter: RPSLimiter,
) -> tuple[str, str, Optional[str], Path]:
    """
    Returns (title, status, error, path)
      status ∈ {"downloaded","skipped_existing","failed"}
    """
    path = pdf_path_for(title, out_dir)
    if path.exists() and not overwrite:
        logger.debug("Skip existing: %s", path.name)
        return (title, "skipped_existing", None, path)

    enc = urllib.parse.quote(title, safe="")
    url = REST_PDF.format(title=enc)

    attempt = 0
    while attempt <= retries:
        try:
            await rps_limiter.wait()
            async with semaphore:
                async with session.get(url, allow_redirects=True, timeout=timeout) as resp:
                    if resp.status in (429,) or 500 <= resp.status < 600:
                        retry_after = resp.headers.get("Retry-After")
                        _ = await resp.read()  # free the connection
                        attempt += 1
                        if attempt > retries:
                            return (title, "failed", f"HTTP {resp.status} after retries", path)
                        sleep_s = float(retry_after) if (retry_after and retry_after.isdigit()) else (base_backoff ** attempt)
                        sleep_s += random.uniform(0, 0.5)  # jitter
                        logger.warning("Rate/server busy (%s). Retrying %r in %.2fs (attempt %d/%d)",
                                       resp.status, title, sleep_s, attempt, retries)
                        await asyncio.sleep(sleep_s)
                        continue

                    if resp.status != 200:
                        txt = await resp.text()
                        return (title, "failed", f"HTTP {resp.status}: {txt[:200]}", path)

                    ctype = resp.headers.get("Content-Type", "")
                    if "pdf" not in ctype.lower():
                        txt = await resp.text()
                        return (title, "failed", f"Unexpected content type: {ctype}; body: {txt[:200]}", path)

                    out_dir.mkdir(parents=True, exist_ok=True)
                    data = await resp.read()
                    path.write_bytes(data)
                    logger.info("[OK] %s -> %s", title, path.name)
                    return (title, "downloaded", None, path)

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            attempt += 1
            if attempt > retries:
                return (title, "failed", f"{type(e).__name__}: {e}", path)
            sleep_s = (base_backoff ** attempt) + random.uniform(0, 0.5)
            logger.warning("Network issue. Retrying %r in %.2fs (attempt %d/%d): %s",
                           title, sleep_s, attempt, retries, e)
            await asyncio.sleep(sleep_s)
        except Exception as e:
            return (title, "failed", f"{type(e).__name__}: {e}", path)

    return (title, "failed", "Exhausted retries", path)

async def download_many(
    titles: List[str],
    out_dir: Path,
    concurrency: int,
    overwrite: bool,
    timeout: int,
    retries: int,
    backoff: float,
    rps: float,
) -> tuple[int, int, int]:
    connector = aiohttp.TCPConnector(limit_per_host=concurrency, ttl_dns_cache=300)
    headers = {
        "User-Agent": UA,
        "Accept": "application/pdf",
        "Accept-Encoding": "gzip, deflate, br",
    }
    semaphore = asyncio.Semaphore(concurrency)
    rps_limiter = RPSLimiter(rps=rps)

    new_count = skipped_count = failed_count = 0

    async with aiohttp.ClientSession(connector=connector, headers=headers, raise_for_status=False) as session:
        tasks = [
            fetch_pdf(
                session=session,
                title=t,
                out_dir=out_dir,
                timeout=timeout,
                retries=retries,
                base_backoff=backoff,
                overwrite=overwrite,
                semaphore=semaphore,
                rps_limiter=rps_limiter,
            )
            for t in titles
        ]
        for coro in asyncio.as_completed(tasks):
            title, status, err, path = await coro
            if status == "downloaded":
                new_count += 1
            elif status == "skipped_existing":
                skipped_count += 1
                logger.info("[SKIP] %s -> %s", title, path.name)
            else:
                failed_count += 1
                logger.error("[FAIL] %s: %s", title, err)

    return new_count, skipped_count, failed_count

# ---------- Main ----------
def main():
    ap = argparse.ArgumentParser(description="Wikipedia PDF dataset builder (concurrent, rate-limited, logging).")
    ap.add_argument("--root", action="append", required=True,
                    help='Root category (e.g., "Category:Tudor England"). Can be used multiple times.')
    ap.add_argument("--depth", type=int, default=1, help="Category crawl depth (default: 1).")
    ap.add_argument("--search", type=str, default="", help="Optional full-text search query to mix in.")
    ap.add_argument("--search-max", type=int, default=300, help="Max search titles to include (default: 300).")
    ap.add_argument("--sample", type=int, default=100, help="Random sample size for final set (default: 100).")
    ap.add_argument("--seed", type=int, default=None, help="Random seed for reproducible sampling.")
    ap.add_argument("--out", type=Path, default=Path("pdfs"), help="Output directory for PDFs.")
    ap.add_argument("--concurrency", type=int, default=6, help="Concurrent downloads (default: 6).")
    ap.add_argument("--rps", type=float, default=2.0, help="Global requests per second limit (default: 2).")
    ap.add_argument("--overwrite", action="store_true", help="Re-download and overwrite existing PDFs.")
    ap.add_argument("--timeout", type=int, default=90, help="Per-request timeout in seconds (default: 90).")
    ap.add_argument("--retries", type=int, default=4, help="Retries for 429/5xx/timeouts (default: 4).")
    ap.add_argument("--backoff", type=float, default=1.7, help="Exponential backoff base (default: 1.7).")
    ap.add_argument("--log-level", type=str, default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR).")
    ap.add_argument("--log-file", type=Path, default=None, help="Optional log file path.")
    args = ap.parse_args()

    setup_logging(args.log_level, args.log_file)
    if args.seed is not None:
        random.seed(args.seed)

    # 1) Gather titles
    cat_titles = gather_category_pages(args.root, depth=args.depth)
    logger.info("Category crawl collected %d titles.", len(cat_titles))

    search_titles: Set[str] = set()
    if args.search.strip():
        search_titles = search_pages(args.search.strip(), max_results=args.search_max)
        logger.info("Search collected %d titles.", len(search_titles))

    all_titles = list(cat_titles | search_titles)
    if not all_titles:
        logger.error("No titles found. Check your categories/search query.")
        return

    random.shuffle(all_titles)
    take = min(args.sample, len(all_titles))
    chosen = all_titles[:take]
    logger.info("Sampling %d titles from %d collected.", take, len(all_titles))

    # 2) Download with logging + summary
    new_count, skipped_count, failed_count = asyncio.run(
        download_many(
            chosen,
            args.out,
            concurrency=args.concurrency,
            overwrite=args.overwrite,
            timeout=args.timeout,
            retries=args.retries,
            backoff=args.backoff,
            rps=args.rps,
        )
    )

    logger.info("Done. New: %d | Skipped (already had): %d | Failed: %d | Out: %s",
                new_count, skipped_count, failed_count, args.out.resolve())

if __name__ == "__main__":
    main()
