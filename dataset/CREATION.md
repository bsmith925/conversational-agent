uv run dataset/download.py \
  --root "Category:Tudor monarchs of England" \
  --root "Category:Children of English monarchs" \
  --root "Category:Tudor princes" \
  --root "Category:Tudor princesses" \
  --depth 1 \
  --search 'incategory:"Category:Tudor monarchs of England" OR incategory:"Category:Children of English monarchs"' \
  --sample 400 \
  --out pdfs/tudor_royal_line
