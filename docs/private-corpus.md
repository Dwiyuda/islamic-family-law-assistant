# Private corpus (copyrighted faraid books)

Copyrighted books are **never** committed. To use a book you legally own:

1. Put the file in `data/private/raw/<doc_id>.<pdf|txt|html>`.
2. Create `data/private/sources_private.yaml`:

   sources:
     - doc_id: buku-faraid-<slug>
       judul: <full title, author, publisher, year>
       singkatan: <short name used in citations>
       jenis: buku
       url_sumber: local
       format: pdf
       lisensi: hak cipta penulis/penerbit - penggunaan pribadi
       domain: kewarisan
       visibility: private

3. Run `python -m app.ingest.build --data-dir ../data` from `api/`.
   Output: `data/private/chunks_private.jsonl` (git-ignored).

Both files live under `data/private/`, which is listed in `.gitignore`.
