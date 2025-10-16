uv run dataset/download.py \
  --root "Category:Tudor monarchs of England" \
  --root "Category:Children of English monarchs" \
  --root "Category:Tudor princes" \
  --root "Category:Tudor princesses" \
  --depth 1 \
  --search 'incategory:"Category:Tudor monarchs of England" OR incategory:"Category:Children of English monarchs"' \
  --sample 400 \
  --out pdfs/tudor_royal_line


uv run dataset/download.py \
  --root "Category:ADHD" \
  --root "Category:Attention deficit hyperactivity disorder" \
  --root "Category:Dopamine reuptake inhibitors" \
  --root "Category:Norepinephrine reuptake inhibitors" \
  --depth 1 \
  --search "ADHD medication" \
  --search-max 200 \
  --sample 250 \
  --seed 42 \
  --out pdfs/adhd_meds \
  --concurrency 6 \
  --rps 2 \
  --log-level INFO