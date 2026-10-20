# Verifikasi Sumber Korpus

Satu baris per `doc_id`. Semua PDF dicek dengan `pypdf`: halaman body pertama harus
menghasilkan >= 200 karakter teks. Tanggal unduh dan sha256 tersimpan di `data/sources.yaml`
(hasil `python -m app.ingest.download`, dijalankan 2026-09-27).

## Qur'an dan Hadis

| doc_id | URL | Verifikasi | Text-extractable | Lisensi |
|---|---|---|---|---|
| `quran-ara` | `cdn.jsdelivr.net/gh/fawazahmed0/quran-api@1/editions/ara-quransimple.min.json` | Edisi resmi di `editions.min.json` milik repo fawazahmed0/quran-api (tag `@1`), teks Arab mushaf standar | ya (JSON teks biasa) | Unlicense (repo); teks Arab Al-Qur'an domain publik |
| `quran-ind` | `cdn.jsdelivr.net/gh/fawazahmed0/quran-api@1/editions/ind-indonesianislam.min.json` | Dicek di `quran-api/editions.min.json`: entri `ind_indonesianislam` — `"author": "Indonesian Islamic Affairs Ministry"`, `"source": "https://quranenc.com/check/indonesian_affairs/..."`. Ini terjemahan Kemenag RI yang didistribusikan via QuranEnc.com | ya | Unlicense (repo); terjemahan Kemenag RI |
| `hadis-info` | `cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/info.min.json` | File metadata resmi repo hadith-api (tag `@1`), berisi nama kitab, daftar section, dan derajat per hadis | ya | Unlicense (repo) |
| `hadis-bukhari-ara` / `-ind` | `.../editions/ara-bukhari.min.json` / `ind-bukhari.min.json` | Edisi terdaftar di `hadith-api/editions.min.json` untuk book `bukhari` | ya | Unlicense; matan Arab domain publik, terjemahan lihat bagian provenance di bawah |
| `hadis-muslim-ara` / `-ind` | `.../ara-muslim.min.json` / `ind-muslim.min.json` | sda, book `muslim` | ya | sda |
| `hadis-abudawud-ara` / `-ind` | `.../ara-abudawud.min.json` / `ind-abudawud.min.json` | sda, book `abudawud` | ya | sda |
| `hadis-tirmidhi-ara` / `-ind` | `.../ara-tirmidhi.min.json` / `ind-tirmidhi.min.json` | sda, book `tirmidhi` | ya | sda |
| `hadis-nasai-ara` / `-ind` | `.../ara-nasai.min.json` / `ind-nasai.min.json` | sda, book `nasai` | ya | sda |
| `hadis-ibnmajah-ara` / `-ind` | `.../ara-ibnmajah.min.json` / `ind-ibnmajah.min.json` | sda, book `ibnmajah` | ya | sda |

Semua URL hadis/Qur'an di atas diverifikasi dengan mengunduh
`https://cdn.jsdelivr.net/gh/fawazahmed0/quran-api@1/editions.min.json` dan
`https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions.min.json`, lalu mencocokkan
setiap edisi (`ara-*`, `ind-*`) yang dipakai di `sources.yaml` terhadap entri resminya.

### Hadith translation provenance

Metadata edisi Indonesia (`ind-bukhari`, `ind-muslim`, `ind-abudawud`, `ind-tirmidhi`,
`ind-nasai`, `ind-ibnmajah`) diambil langsung dari file sumber repo, contoh isi blok metadata
di akhir `database/originals/ind-bukhari.txt` (commit tag `1`):

```
"name": "ind-bukhari",
"book": "bukhari",
"author": "Unknown",
"language": "Indonesian",
"source": "",
"comments": "",
```

Jadi repo `fawazahmed0/hadith-api` sendiri **tidak mencatat penerjemah maupun sumber**
untuk keenam edisi terjemahan Indonesia ini (`author: "Unknown"`, `source: ""`) — sama
untuk semua enam kitab yang dipakai di sini. Ini beda dengan edisi Qur'an Indonesia
(`ind-indonesianislam`), yang metadatanya mencantumkan penerjemah dan sumber (Kemenag RI
via QuranEnc). README dan `CONTRIBUTING.md` repo hanya menjelaskan mekanisme kontribusi
terjemahan (upload file teks + JSON metadata di akhir file), tidak menyebut asal spesifik
terjemahan Indonesia yang sudah ada.

**Keputusan (final review, pre-merge):** karena lisensi/provenance-nya tidak terlacak dan
tidak bisa diverifikasi, keenam edisi terjemahan Indonesia (`ind-bukhari`, `ind-muslim`,
`ind-abudawud`, `ind-tirmidhi`, `ind-nasai`, `ind-ibnmajah`) **tidak dipakai sama sekali**
di korpus publik — sesuai spec Sec 4.1: terjemahan Indonesia hanya boleh dipakai kalau
lisensinya sudah diverifikasi mengizinkan reuse, dan itu tidak terjadi di sini. Chunk hadis
publik hanya berisi matan Arab (`text` = `text_ar` = teks Arab) plus referensi (kitab dan
nomor); tidak ada teks terjemahan Indonesia di chunk manapun. Entri `hadis-<kitab>-ind` tetap
ada di `data/sources.yaml` (didownload, sha256 tercatat) untuk keperluan dokumentasi/audit,
tapi field `catatan`-nya masing-masing menyatakan tidak dipakai, dan `parse_hadith`/`build.py`
tidak lagi membaca file edisi terjemahan ini sama sekali.

**Penelusuran rantai asal (dicek di browser, 27 Sep 2026):**

| Langkah | Halaman | Temuan |
|---|---|---|
| 1 | `https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions.json` | `ind-bukhari` (dan lima edisi `ind-*` lain): `"author": "Unknown"`, `"source": ""` |
| 2 | `https://cdn.jsdelivr.net/gh/fawazahmed0/quran-api@1/editions.json` (pembanding) | `ind-indonesianislam`: `"author": "Indonesian Islamic Affairs Ministry"`, sumber QuranEnc — asal tercatat jelas |
| 3 | `https://github.com/fawazahmed0/hadith-api/blob/1/References.md` | Hanya daftar situs yang "membantu", termasuk `https://github.com/gadingnst/hadith-api` |
| 4 | `https://github.com/gadingnst/hadith-api` | "Simple Islamic Hadith API with Indonesia Translation"; Data Source: **tafsirq.com**, dikumpulkan lewat crawler; lisensi repo MIT |
| 5 | `https://tafsirq.com/page/source` | Konten TafsirQ terdiri dari Open Data, *Scrapping Data* (diagregasi dari situs lain), *Partner Data* (kerja sama dengan pemegang hak cipta), dan User Generated. Sumber terjemahan hadis **tidak disebut**. Halaman hadis (`/hadits/...`) kini dialihkan ke beranda. |

Kesimpulan: terjemahan berpindah tangan tafsirq.com → gadingnst/hadith-api → fawazahmed0/hadith-api.
Lisensi MIT (gadingnst) dan Unlicense (fawazahmed0) hanya mencakup kode/kompilasi mereka, bukan
teks terjemahan yang bukan karya mereka. Sumber paling awal sendiri menyatakan sebagian kontennya
hasil scraping atau milik mitra pemegang hak cipta, dan pemegang hak cipta terjemahan hadis ini
tidak diketahui. Keputusan Arab-saja di atas tetap berlaku.

## HadeethEnc (terjemahan hadis berlisensi)

URL syarat: dialog "Terms and Policies" di `https://hadeethenc.com/id/home` (diverifikasi lewat
browser 27 Sep 2026). Tujuh syarat republikasi terjemahan (diparafrasekan):

1. Tidak boleh mengubah isi terjemahan.
2. Tidak boleh menambah isi.
3. Tidak boleh menghapus sebagian isi.
4. Penerbit (publisher) dari hasil unduhan harus disebutkan.
5. Sumber asal (HadeethEnc.com) harus disebutkan.
6. Nomor versi harus dicantumkan.
7. Isi yang dipublikasikan ulang harus tetap diperbarui (kept up to date).

API dipakai: `https://hadeethenc.com/api/v1/` — `categories/list`, `hadeeths/list` (paginasi per
kategori), `hadeeths/one` (detail per hadis, termasuk field `grade` dan `attribution`). API tidak
menyediakan nomor hadis per kitab maupun nomor versi eksplisit, jadi tanggal snapshot dipakai
sebagai nomor versi (`license` chunk berakhir dengan `"; versi <tanggal snapshot>"`).

Kategori fikih keluarga dan waris yang di-snapshot (domain korpus; urutan menentukan pemenang
kalau satu hadis muncul di beberapa kategori — kewarisan > perceraian > perkawinan):

| Kategori HadeethEnc (id) | domain |
|---|---|
| 123 Ilmu Waris, 166 Wasiat | kewarisan |
| 192 Talak, 193 Rujuk, 194 Khuluk, 195 Īlā', 196 Ẓihār, 197 Li'ān, 198 Idah, 200 Pengasuhan | perceraian |
| 191 Pernikahan, 199 Penyusuan, 201 Nafkah, 605 Poligami, 610 Nafkah Untuk Anak | perkawinan |

Snapshot dijalankan 27 Sep 2026 (`data/raw/hadeethenc-id.json`, git-ignored), menghasilkan 128
hadis (dalam rentang 120–180 yang diharapkan): 79 perkawinan, 42 perceraian, 7 kewarisan; derajat
112 sahih, 15 hasan, 1 tidak_diketahui (hadis no. 58153 — field `grade` API-nya berisi catatan
"Aku tidak menemukan hukum (hadis tersebut) dari syaikh al-Albāni", bukan derajat baku), 0 dhaif.
Tanggal snapshot (`2026-09-27`) itu sendiri yang dipakai sebagai nomor versi di setiap chunk.

Teks chunk = terjemahan (`hadeeth`) + `Penjelasan:` (`explanation`) + `Pelajaran:` (`hints`),
semuanya verbatim; `hints` (23 dari 128 hadis) semula dibuang, padahal syarat 3 melarang menghapus
sebagian isi, sehingga kini disertakan (baris kosong dibuang, spasi/`\r` pinggir dipangkas). Perawi
(`hadith.perawi`) diambil dari `hadeeth_intro`, kalau kosong dari awal teks `hadeeth`: pola
"X -raḍiyallāhu 'anhu-", "Dari X, …/bahwa…", atau "X meriwayatkan"; `null` bila teks tidak menyebut
perawi di awal. Hasil: 115 dari 128 hadis punya perawi (sebelumnya 23). Presisi didahulukan: bila nama yang tertangkap adalah tabi'i (rantai "dari bapaknya", "dari X", dua nama, atau dua tabi'in yang diketahui) atau tangkapannya meragukan, perawi dibiarkan kosong.

## Peraturan dan Prosedur

| doc_id | URL | Verifikasi nomor/tahun/status | Text-extractable | Lisensi |
|---|---|---|---|---|
| `uu-1-1974` | `peraturan.bpk.go.id/Download/36382/UU Nomor 1 Tahun 1974.pdf` | Halaman detail JDIH BPK `peraturan.bpk.go.id/Details/...` (hasil pencarian) mengonfirmasi UU 1/1974 tentang Perkawinan; status **diubah** oleh UU 16/2019 (dikonfirmasi UU 16/2019 sendiri berjudul "Perubahan atas UU 1/1974") | ya, halaman 1 (888 char) | public-domain (UU 28/2014 Pasal 42) |
| `uu-16-2019` | `peraturan.bpk.go.id/Download/113523/UU Nomor 16 Tahun 2019.pdf` | Detail JDIH BPK: UU 16/2019 tentang Perubahan atas UU 1/1974, diundangkan 15 Okt 2019; status **berlaku** | ya, halaman 1 (1280 char) | public-domain (UU 28/2014 Pasal 42) |
| `pp-9-1975` | `peraturan.bpk.go.id/Download/58020/PP NO 9 TH 1975.pdf` | Halaman detail JDIH BPK (`peraturan.bpk.go.id/Details/67678/pp-no-9-tahun-1975`) menampilkan status **Berlaku**, LN 1975 No. 12 | ya, halaman 1 (810 char) | public-domain (UU 28/2014 Pasal 42) |
| `khi-1991` | `simbi.kemenag.go.id/eliterasi/.../b5c07c0ce34195adb3cd15ad059b33f2.pdf` | Inpres 1/1991 (JDIH BPK `Details/293351/inpres-no-1-tahun-1991`, status **Berlaku**) hanya berisi 2 halaman instruksi penyebarluasan, **bukan** teks KHI itu sendiri. Teks lengkap KHI (Buku I–III) diverifikasi dari buku terbitan resmi Ditjen Bimas Islam Kemenag RI yang di-hosting di `simbi.kemenag.go.id` (SIMBI = Sistem Informasi Manajemen Bimas Islam, subdomain Kemenag). File ini 262 halaman, memuat kata pengantar Ditjen dan teks lengkap Buku I (Hukum Perkawinan, Bab I–XIX), Buku II (Hukum Kewarisan, Bab I–VI), Buku III (Hukum Perwakafan). File juga berisi ~108 halaman lampiran non-KHI setelah Buku III — lihat "KHI source file structure" di bawah | ya, halaman body pertama (indeks 4, 885 char); 4 halaman sebelumnya adalah sampul/kosong | public-domain (UU 28/2014 Pasal 42) |
| `khi-1991-ma` | `putusan3.mahkamahagung.go.id/peraturan/download_file/...` (Direktori Putusan MA) | **Reference-only** (`role: reference`, tidak di-chunk): teks KHI edisi lain (born-digital "WordToPDF" 2007, 35 halaman), dipakai Fase 2 Task 2 semata untuk cek silang OCR `khi-1991`. Diunduh manual oleh pemilik lewat browser (unduhan otomatis terhalang proteksi bot) | ya (35 halaman) | public-domain (UU 28/2014 Pasal 42) |
| `uu-7-1989` | `peraturan.bpk.go.id/Download/35577/UU Nomor 7 Tahun 1989.pdf` | Detail JDIH BPK: UU 7/1989 tentang Peradilan Agama; status **diubah** (oleh UU 3/2006 dan UU 50/2009, dikonfirmasi lewat judul kedua UU tsb yang eksplisit "Perubahan atas UU 7/1989" dan "Perubahan Kedua atas UU 7/1989") | ya, halaman 1 (1757 char) | public-domain (UU 28/2014 Pasal 42) |
| `uu-3-2006` | `peraturan.bpk.go.id/Download/29789/UU Nomor 3 Tahun 2006.pdf` | Detail JDIH BPK: UU 3/2006 tentang Perubahan atas UU 7/1989; status **berlaku** | ya, halaman 1 (1624 char) | public-domain (UU 28/2014 Pasal 42) |
| `uu-50-2009` | `peraturan.bpk.go.id/Download/28124/UU Nomor 50 Tahun 2009.pdf` | Detail JDIH BPK: UU 50/2009 tentang Perubahan Kedua atas UU 7/1989; status **berlaku** | ya, halaman 1 (1667 char) | public-domain (UU 28/2014 Pasal 42) |
| `perma-1-2016` | `jdih.mahkamahagung.go.id/storage/uploads/produk_hukum/PERMA NOMOR 1 TAHUN 2016/..._PERMA_MEDIASI_PENGADILAN_WEB.pdf` | Dihost langsung di domain resmi Mahkamah Agung (`jdih.mahkamahagung.go.id`). Berdasarkan pencarian, PERMA 1/2016 mencabut PERMA 1/2008 dan sampai saat verifikasi (27 Sep 2026) tidak ditemukan PERMA baru yang mencabut/menggantikannya — status **berlaku** sebagai aturan mediasi terkini | ya, halaman 1 (1163 char) | public-domain (UU 28/2014 Pasal 42) |
| `prosedur-cerai-gugat` | `pa-bogor.go.id/pelayanan/prosedur-berperkara/tingkat-pertama/cerai-gugat` | Halaman resmi Pengadilan Agama Bogor (`*.go.id`), bagian "Prosedur Berperkara Tingkat Pertama", berisi 6 langkah pengajuan gugatan cerai | ya (HTML, bukan dicek pypdf) | dokumen resmi pemerintah, dikutip dengan sumber |
| `prosedur-cerai-talak` | `pa-bogor.go.id/pelayanan/prosedur-berperkara/tingkat-pertama/cerai-talak` | Halaman resmi PA Bogor, sibling dari halaman cerai gugat di menu yang sama, berisi 6 langkah pengajuan permohonan talak | ya (HTML) | dokumen resmi pemerintah, dikutip dengan sumber |
| `prosedur-waris` | `ptsp.pa-wonosobo.go.id/syarat-berperkara/penetapan-ahli-waris/` | Halaman resmi PTSP Pengadilan Agama Wonosobo (`*.go.id`), memuat 13 kategori syarat berkas untuk permohonan Penetapan Ahli Waris (P3HP) | ya (HTML) | dokumen resmi pemerintah, dikutip dengan sumber |

### Catatan status UU 3/2006 dan UU 50/2009

Keduanya berstatus "berlaku" sebagai instrumen hukum yang sah (bukan dicabut) meskipun
secara materi telah menyisipkan/mengubah pasal UU 7/1989 — konsisten dengan cara JDIH BPK
menandai status masing-masing UU perubahan tersebut secara terpisah dari UU induknya.

### domain_rules — heading yang jadi dasar

- **`uu-1-1974` → Bab VIII**: teks halaman 14 PDF: `"BAB VIII\nPUTUSNYA PERKAWINAN SERTA AKIBATNYA"` (persis judul yang disebut di brief) → `domain: perceraian`.
- **`pp-9-1975` → Bab V**: teks halaman 9 PDF: `"BAB V\nTATACARA PERCERARIAN"` (ejaan asli dokumen, ada typo "PERCERARIAN") → `domain: perceraian`.
- **`khi-1991` → Buku I Bab XVI–XIX**: ditemukan di badan teks (bukan daftar isi, yang OCR-nya kurang bersih):
  - halaman body 68: `"BABXVI\nPUTUSNYA PERKAWINAN"` → Bab XVI = Putusnya Perkawinan
  - halaman body 84: `"BABXVII\nAKIBAT PUTUSNYA PERKAWINAN"` → Bab XVII = Akibat Putusnya Perkawinan
  - halaman body 91: `"BAH XVIII\nRUJUK"` (OCR "BAH" untuk "BAB") → Bab XVIII = Rujuk
  - halaman body 96: `"BAD XIX\nMASA BERKABUNG"` (OCR "BAD" untuk "BAB") → Bab XIX = Masa Berkabung (berisi ketentuan iddah/masa tunggu berkabung)
  - Semua empat bab di atas ada di dalam **Buku I** (halaman 8, daftar isi: "BUKU I HUKUM PERKAWINAN"; Buku II dimulai di halaman body 98: `"BUKU II\nHOKUM KEWARISAN"`; Buku III di halaman body 120: `"BUKU Ill\nHUKUM PERWAKAFAN"`).
  - Aturan: `buku: "I", bab: "XVI"/"XVII"/"XVIII"/"XIX"` → `perceraian`; `buku: "II"` (semua bab) → `kewarisan`; `buku: "III"` (semua bab) → `skip` (di luar cakupan proyek).

### KHI source file structure

`data/raw/khi-1991.pdf` (262 halaman) bukan cuma teks KHI — file terbitan Kemenag ini juga
menyertakan tiga lampiran peraturan lain di baliknya. Nomor halaman di bawah adalah **indeks
`pypdf` (0-based)**, dikonfirmasi dengan memindai teks tiap halaman untuk heading BAB/BUKU
dan judul dokumen:

```
cd api && .venv/Scripts/python -c "
from pypdf import PdfReader
r = PdfReader('../data/raw/khi-1991.pdf')
print('total pages:', len(r.pages))
for i in range(len(r.pages)):
    t = r.pages[i].extract_text() or ''
    for line in t.split(chr(10)):
        ls = line.strip()
        if ls.upper().replace(' ','').startswith(('BUKUI','BUKUII','BUKUIII')) or ls.upper().startswith('LAMPIRAN') or 'LAMPI RAN' in ls.upper():
            print(i, repr(ls))
"
```
→ `total pages: 262`, lalu heading body (bukan daftar isi) ditemukan di indeks 12 (`BUKUI`),
98 (`BUKU II`), 120 (`BUKU Ill`), dan 140 (`LAMPI RAN`).

Rentang halaman (indeks pypdf, 0-based):

| Bagian | Rentang indeks | Isi |
|---|---|---|
| Sampul kosong | 0–3 | tidak ada teks (halaman gambar) |
| Kata Pengantar | 4–5 | kata pengantar penyusun |
| Sambutan Direktur Jenderal | 6–7 | sambutan Ditjen Bimas Islam |
| Daftar Isi | 8–11 | `"DAFTARISI"` (OCR tanpa spasi), memuat daftar Bab Buku I–III sampai ke Inpres 1/1991 |
| **Buku I — Hukum Perkawinan** | 12–97 | heading body: `"BUKUI\nHOKUM PERKAWINAN"` (indeks 12); berisi Bab I–XIX, termasuk Bab XVI–XIX yang dipakai di `domain_rules` |
| **Buku II — Hukum Kewarisan** | 98–119 | heading body: `"BUKU II\nHOKUM KEWARISAN"` (indeks 98); Bab I–VI |
| **Buku III — Hukum Perwakafan** | 120–133 | heading body: `"BUKU Ill\nHUKUM PERWAKAFAN"` (indeks 120, OCR merender "III" sebagai "Ill") |
| Penjelasan atas Buku KHI | 134–139 | `"PENJELASAN\nATAS\nBUKU KOMPILASI HUKUM ISLAM"` (indeks 134), penjelasan pasal demi pasal sampai Pasal 148 |
| **LAMPIRAN** | mulai indeks 140 | heading: `"LAMPI RAN"` (OCR memecah jadi dua kata) |
| — isi 1: UU 1/1974 + Penjelasannya | 142–197 | teks lengkap UU 1/1974 tentang Perkawinan dicetak ulang, termasuk penjelasan pasal demi pasalnya (bukan dokumen `uu-1-1974` yang terpisah — itu diambil dari sumber sendiri di JDIH BPK) |
| — isi 2: PP 9/1975 | 198–229 | teks lengkap PP 9/1975 (indeks 198: `"PERATURAN PEMERINTAH ... NOMOR 9 TAHUN 1975"`), plus penjelasannya mulai indeks 230 (`"PENJELASAN\nATAS\nPERATURAN PEMERINTAH ... NOMOR 9 TAHUN 1975"`) |
| — isi 3: Kepmenag 154/1991 | 254–261 | `"KEPUTUSAN MENTERI AGAMA ... NOMOR: 154 TAHUN 1991 TENTANG PELAKSANAAN INSTRUKSI PRESIDEN ... NOMOR 1 TAHUN 1991"` (indeks 254) sampai akhir file |

Sebagai catatan tambahan yang dikonfirmasi controller: penghitungan naif baris `"Pasal <n>"` di
seluruh file menghasilkan ~441 kemunculan, jauh di atas 229 pasal KHI yang sebenarnya —
selisihnya berasal dari pasal-pasal UU 1/1974 dan PP 9/1975 yang tercetak ulang di LAMPIRAN.

OCR/text-extraction pada file ini cukup berisik; beberapa pola yang teramati:
- `"BUKU Ill"` untuk "BUKU III" (huruf `l` kecil menggantikan `I` ketiga)
- `"BAH XVIII"` dan `"BAD XIX"` untuk "BAB XVIII" / "BAB XIX" (huruf terakhir kata "BAB" salah OCR)
- `"BABXVI"`, `"BABXVII"`, `"BUKUI"`, `"DAFTARISI"` — spasi antar kata hilang
- `"LAMPI RAN"` — spasi tersisip di tengah kata "LAMPIRAN"

### KHI Pasal 138 (not 139) and the Pasal 124/139 gaps (Fase 2 Task 2, corrected)

Task 9 (Fase 1) had guessed, from a KHI-numbers-PP-plus-112 correspondence,
that the OCR'd heading `"Pasall38"` (normalized to "138") was really Pasal 139
mislabeled, and applied a `Source.pasal_overrides: {'138': '139'}` relabel.
That inference has been **reverted** in Fase 2 Task 2: the owner obtained a
second, independent, born-digital KHI text from the Mahkamah Agung Direktori
Putusan (`data/raw/khi-1991-ma.pdf`, reference-only, `role: reference` — see
the sources table above) and the controller verified by hand on 27 Sep 2026
that **both** official texts (the Kemenag book and the MA text) jump from
Pasal 123 straight to 125, and number "Apabila tempat kediaman tergugat tidak
jelas..." **as Pasal 138** — then jump from 138 to 140. So the pasal_overrides
relabel was wrong: it renumbered a correctly-numbered pasal. The real gaps
(missing from both official texts) are **Pasal 124** (khuluk) and **Pasal
139** ("...melalui perwakilan Republik Indonesia setempat"), not 124/138 as
Fase 1 documented. The `pasal_overrides` mechanism has been deleted entirely
(`Source.pasal_overrides`, the `regulation.py` lookup, and its tests) since no
manifest entry uses it any more. `khi-1991`'s `catatan` field now records this
finding directly.

### KHI OCR fixes against the MA text and the SEMA footnote (Fase 2b Task 2)

The MA Direktori Putusan text (`khi-1991-ma`) is the arbiter for the OCR'd Kemenag book
(`khi-1991`): a correction is made only where the MA text shows the intended wording.
Applied: Pasal 116 second "c." -> "e."; Pasal 149 a "Ia yak" -> "layak", c line order, d
"anak-anaknya"; Pasal 146(2) "akibat-akibatnya"; Pasal 183 and 191 "wans" -> "waris"; Pasal 191
"urn urn" -> "umum". The last item of Pasal 116 stays **"k."** because both official texts
print "k." (it is not "corrected" to "h."). The editorial footnote "* Berdasarkan Surat Edaran
Mahkamah Agung Nomor : 2 Tahun 1994 ..." was extracted inside Pasal 185 but the asterisk
closes Pasal 177 in the MA text, so `footnote_moves` ({"185": "177"}) moves it. `khi-1991-ma` is
now `fetcher: manual` (downloaded by the owner; `download.sync` skips it).

### Conventions

- `domain_rules` di `sources.yaml` **selalu memakai angka Romawi kanonik** (mis. `buku: III`,
  bukan `buku: Ill`). Normalisasi varian OCR (`Ill`→`III`, `BAH`/`BAD`→`BAB`, spasi yang
  hilang) adalah tanggung jawab parser di Task 5, bukan manifest ini.
- Parser Task 5 berhenti memproses `khi-1991.pdf` begitu menemukan baris yang diawali
  `LAMPIRAN` setelah minimal satu `Pasal` sudah terlihat — jadi 108 halaman lampiran
  (UU 1/1974 + Penjelasan, PP 9/1975 + Penjelasan, Kepmenag 154/1991) **tidak pernah
  masuk ke chunk KHI**. UU 1/1974 dan PP 9/1975 tetap diingest, tapi dari entri manifest
  masing-masing (`uu-1-1974`, `pp-9-1975`), bukan dari salinan yang tercetak ulang di
  lampiran KHI ini.

## Skipped sources

- **`kitab-rahbiyyah` (Matn ar-Rahbiyyah, Step 3, opsional)** — **dilewati**. Pencarian dilakukan di Arabic Wikisource (`ar.wikisource.org`, pencarian judul "الرحبية" → hasil "halaman tidak ada") dan archive.org. Ditemukan beberapa item archive.org:
  - `archive.org/details/alrahabya` — berupa rekaman audio MP3 (bukan teks).
  - `archive.org/details/Rahbya` — ada file teks (`_djvu.txt`, PDF), tapi item ini adalah unggahan pengguna tanpa metadata edisi/penerbit/tahun cetak, tidak jelas ini scan dari edisi cetak resmi atau institusional (bukan scan perpustakaan dengan tahun terbit tercatat).
  Karena brief mensyaratkan hanya menerima sumber institusional/perpustakaan ternama (Wikisource, atau scan archive.org dari edisi cetak pra-1926 dengan text layer), dan tidak ditemukan kandidat yang memenuhi syarat itu dalam upaya pencarian yang wajar, entri ini **tidak ditambahkan** ke `sources.yaml`. Tidak blocking sesuai brief. Total sumber final: **26** (bukan 27).

## Peringatan Putusan MK (Fase 3)

Dua pasal UU 1/1974 telah dimaknai ulang oleh putusan Mahkamah Konstitusi. Putusan itu
**tidak** masuk korpus (mkri.id di luar domain unduhan yang diizinkan), jadi sistem hanya
memberi peringatan dan menunjuk ke nomor putusannya (`CHUNK_NOTES` di
`api/app/generation/sources.py`); isi amar tidak pernah ditulis dari ingatan.

Diverifikasi langsung di mkri.id pada 2026-10-18:

| Pasal (chunk_id) | Putusan MK | Pokok perkara (mkri.id) | Amar |
|---|---|---|---|
| `uu-1-1974:pasal-43` | 46/PUU-VIII/2010 | Pengujian UU No. 1/1974 tentang Perkawinan (pemohon Hj. Aisyah/Machica Mochtar); kata kunci "Anak Yang Dilahirkan Diluar Perkawinan", "Hubungan Perdata Dengan Keluarga Ayahnya" | Dikabulkan Sebagian |
| `uu-1-1974:pasal-29` | 69/PUU-XIII/2015 | Pengujian UU No. 5/1960 (Agraria) dan UU No. 1/1974 tentang Perkawinan (pemohon Ny. Ike Farida); perjanjian perkawinan | Dikabulkan Sebagian |
