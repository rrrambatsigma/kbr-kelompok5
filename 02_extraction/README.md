# EKSTRAKSI

## Chunk Markdown DOC005

`DOC005.md` dipecah menjadi chunk per penyakit untuk bukti enrichment Tahap 2.
Output `extracted_text/DOC005.chunks.jsonl` bersifat generated dan tidak masuk
Git.

```powershell
# dari root repo
python 02_extraction/build_doc005_chunks.py
python 02_extraction/build_doc005_chunks.py --check

# dari folder ini
python -m unittest discover -s tests -p "test_*.py"
```
