# Corpus build: parser fixes and spot-check (Task 9)

## Parser fixes made during the real corpus build

All fixes are in `api/app/ingest/regulation.py`, with regression tests in
`api/tests/ingest/test_regulation.py`. Found by running `parse_regulation` on
the real `extract_text()` output of each raw regulation document and diffing
produced pasal numbers against the known contiguous pasal range of that
document (see the per-document table below).

1. **`RE_PASAL` too strict for OCR'd headings.** The original regex required a
   literal space between "Pasal" and the number (`Pasal\s+...`) and only
   tolerated `\d+[A-Z]?` or a pure-roman numeral. The real KHI PDF's OCR
   glues "Pasal" straight to the number with no space, and inside the number
   misreads digit `1` as lowercase `l` (or occasionally uppercase `I`/lowercase
   `i`) and digit `0` as uppercase `O` (or lowercase `o`): `Pasall` (Pasal 1),
   `Pasal2`..`Pasal9` (plain, no space), `PasallO` (Pasal 10), `Pasall3`
   (Pasal 13), `Pasalll` (Pasal 11). Fixed by widening the numeral character
   class to `[0-9lIOoiVXLC]+` (optional trailing `[A-Z]?` suffix for inserted
   articles like "7A"), tolerating zero whitespace, and adding
   `_normalize_pasal()`: if the captured string is composed *only* of
   uppercase roman characters (`I`,`V`,`X`,`L`,`C`) it is left untouched (this
   preserves genuine roman-numeral amendment articles like "Pasal I", "Pasal
   II" used in UU 16/2019 and UU 3/2006); otherwise `l`/`I`/`i` -> `1` and
   `O`/`o` -> `0` via `str.translate`.
2. **OCR also drops the final "l" of the word "Pasal" itself**, e.g. real
   KHI text "Pasal 24" -> `Pasa124`, "Pasal 101" -> `PasaliOI`. Fixed by
   widening the literal prefix from `Pasal` to `Pasa[l1]`.
3. **`PENJELASAN` stop condition fired inside the table of contents**, before
   any real `Pasal` heading. The KHI PDF's daftar isi has a line
   `PENJELASAN ATAS` (announcing the explanatory-memorandum section title in
   the TOC) at line ~137, long before the real body starts at line ~166. The
   original code did `if RE_STOP.match(line): break` unconditionally, so
   parsing stopped before it ever produced a single chunk for `khi-1991`
   (0 chunks). Fixed by gating `RE_STOP` on `seen_pasal`, mirroring the
   existing `RE_LAMPIRAN` gate — the explanatory-memorandum heading is only
   honored once real pasal parsing has actually started.
4. **Ayat over-split from a PDF line-wrap false positive.** In
   `perma-1-2016.pdf`, Pasal 17's ayat (2) wraps mid-sentence: "...dimaksud
   pada ayat" ends one line, and the continuation "(1) berdasarkan panggilan
   yang sah dan patut." starts the next — `_split_ayat`'s regex matched that
   `(1)` as a *new* ayat 1, producing a second `khi... :pasal-17:ayat-1` and
   crashing `write_chunks` on a duplicate `chunk_id`. Fixed by requiring the
   matched ayat number to equal the next *expected* sequential number
   (starting at 1, incrementing on each accepted match); anything else
   (like a stray `(1)` while ayat 2 is still open) is treated as body text.
5. **Manifest-level `pasal_overrides` for an isolated digit misread that
   `_normalize_pasal` can't cover.** See "Correction: khi-1991 Pasal 138 -> 139"
   below. Added `Source.pasal_overrides: dict[str, str]` (OCR-read pasal
   number -> correct pasal number), applied in `parse_regulation` right after
   `_normalize_pasal`, before `chunk_id`/`citation`/`hierarchy` are built.

## Correction: khi-1991 Pasal 138 is correctly numbered (Fase 2 Task 2, supersedes fix round 1)

Fase 1's "fix round 1" (below, kept for history) guessed — from a KHI-number
= PP-9/1975-number + 112 correspondence — that the OCR'd heading `Pasall38`
(normalized to "138") was really a mislabeled Pasal 139, and relabelled it via
`Source.pasal_overrides: {'138': '139'}`. Fase 2 Task 2 obtained a second,
independent, born-digital KHI text (Mahkamah Agung Direktori Putusan,
`data/raw/khi-1991-ma.pdf`, reference-only, never chunked) and the controller
verified by hand on 27 Sep 2026 that **both** official texts — the Kemenag
book (this corpus's source) and the MA text — number "Apabila tempat
kediaman tergugat tidak jelas..." **as Pasal 138**, jumping straight from
Pasal 123 to 125 and from 138 to 140. The PP-9/1975-plus-112 inference was
therefore wrong (it happens to fit an off-by-one artifact, not the real
numbering), and the relabel has been **reverted**: `khi-1991:pasal-138` now
exists (this chunk), `khi-1991:pasal-139` no longer does. The
`pasal_overrides` mechanism itself has been deleted from `Source` and
`parse_regulation` (no manifest entry needs it any more).

The real, confirmed-in-both-texts gaps are **Pasal 124** (khuluk) and
**Pasal 139** ("...melalui perwakilan Republik Indonesia setempat"), absent
from both the Kemenag and MA texts — not 124/138 as Fase 1 documented. No
text was added for either gap from memory or any other source; they remain
documented gaps in `khi-1991`'s pasal range (1-214, Buku III skipped).

### Fix round 1 (Fase 1, superseded above)

An earlier version of this document misdiagnosed this area as "Pasal 124 and
139 mislabeled as 125 and 140". That diagnosis was **wrong** and was
corrected to "Pasal 138 mislabeled as 139" (Task 9 fix round 2) — which
Fase 2 Task 2 has now also found to be wrong, per the finding above.

## Per-document chunk counts vs known pasal counts

| doc_id | jenis | chunks | distinct pasal | pasal range | gaps |
|---|---|---|---|---|---|
| uu-1-1974 | uu | 67 | 67 | 1-67 | none (matches known 67 pasal) |
| pp-9-1975 | pp | 49 | 49 | 1-49 | none |
| khi-1991 | inpres | 212 | 212 | 1-214 | 124, 139 missing from source text, confirmed absent from both the Kemenag and MA official texts (see "Correction" above); Buku III (pasal 215-229) correctly skipped by `domain_rules` |
| uu-7-1989 | uu | 108 | 108 | 1-108 | none |
| uu-3-2006 | uu | 43 | 43 | 2-105 | expected — this is an amendment law (UU Perubahan) that only touches specific pasal of UU 7/1989; gaps are the untouched pasal, not a parser defect |
| uu-50-2009 | uu | 35 | 35 | 1-53 | expected — same reason, second amendment law |
| uu-16-2019 | uu | 4 | 4 | 7 (+ roman "I"/"II" articles) | expected — short amendment law |
| perma-1-2016 | perma | 51 | 39 | 1-39 | none (some pasal split into multiple ayat chunks) |
| prosedur-cerai-gugat | prosedur | 3 | n/a | n/a | n/a |
| prosedur-cerai-talak | prosedur | 3 | n/a | n/a | n/a |
| prosedur-waris | prosedur | 1 | n/a | n/a | n/a |

## Final `data/processed/stats.json` (post final-review fixes)

Rebuilt after the final whole-branch review: hadith chunks are now Arabic-matn-only
(spec Sec 4.1 — the six Indonesian hadith translation editions are unverifiable and no
longer used, see docs/sources-verification.md "Hadith translation provenance"), and
Sahih Muslim chunks are keyed and merged by the real Abdul Baqi print number instead of
hadith-api's internal sequential `hadithnumber` (see "Sahih Muslim numbering" below).
Only `hadith`'s total and `hadis-muslim`'s count changed; regulation, procedure, and
quran counts and chunk_ids are byte-for-byte unchanged from the Task 9 build.

```json
{
  "total": 2356,
  "by_source_type": {
    "regulation": 569,
    "procedure": 7,
    "quran": 72,
    "hadith": 1708
  },
  "by_domain": {
    "perkawinan": 1069,
    "perceraian": 653,
    "kewarisan": 390,
    "peradilan": 186,
    "prosedur": 58
  },
  "by_doc": {
    "uu-1-1974": 67,
    "uu-16-2019": 4,
    "pp-9-1975": 49,
    "khi-1991": 212,
    "uu-7-1989": 108,
    "uu-3-2006": 43,
    "uu-50-2009": 35,
    "perma-1-2016": 51,
    "prosedur-cerai-gugat": 3,
    "prosedur-cerai-talak": 3,
    "prosedur-waris": 1,
    "quran": 72,
    "hadis-bukhari": 369,
    "hadis-muslim": 112,
    "hadis-abudawud": 333,
    "hadis-tirmidhi": 162,
    "hadis-nasai": 428,
    "hadis-ibnmajah": 304
  }
}
```

### Sahih Muslim numbering (final review, Fix 2)

hadith-api's `hadithnumber` for `muslim` is that dataset's own flat sequential count
(e.g. hadithnumber 4140 = Abdul Baqi print no. 1614) — not a number a user could look up
in a printed Sahih Muslim. For the other five collections `hadithnumber == arabicnumber`
(spot-checked across the first 2000 entries of each collection, 0 mismatches), so this
only affects `muslim`. Investigation of `data/raw/hadis-muslim-ara.json` +
`data/raw/hadis-info.json`:

- All 392 family-law-domain `muslim` entries carry an `arabicnumber` (0 missing).
- `arabicnumber` is a string: either a plain Abdul Baqi number ("1401") or
  `"<abdul-baqi-number>.<chain-index>"` ("1400.01".."1400.05") when several
  isnad-only chain variants of the same hadith share one Abdul Baqi number — a normal
  feature of the printed edition, not a data defect. Grouping by the part before the
  dot gives **113 distinct Abdul Baqi numbers** across the 392 entries, 85 of which
  have more than one chain variant (sizes 2-21; the largest, no. 1471, is a hadith
  reported through 21 separate isnads, all textually beginning with a narrator chain
  and confirmed to share the same `reference.book`/domain).
  Every group is internally consistent: no group spans two different domains or books.
- One entry (hadithnumber 388, arabicnumber "154.02") has empty Arabic text and is
  alone in its group, so it is dropped — the same drop the old per-entry logic already
  made (392 entries -> 391 non-empty chunks before this fix).

Fix: `hadith.py`'s `_parse_muslim` groups entries by the Abdul Baqi base number, joins
each group's non-empty Arabic texts in hadithnumber order (`"\n\n".join(...)`), and
emits one chunk per group — `chunk_id = hadith:muslim:<abdul-baqi-number>`,
`citation = "HR. Muslim no. <abdul-baqi-number>"`. Result: 113 groups -> 112 chunks
(1 dropped, the empty-text singleton above; no other drops). `write_chunks`'s duplicate
check confirms all 112 chunk_ids are unique. Example:
`hadith:muslim:1400` merges hadithnumbers 3398-3402 (5 chain variants) into one chunk
whose citation, "HR. Muslim no. 1400", is now the number a reader can actually look up.
The other five collections are untouched (`hadithnumber`-keyed, as before).

## Spot-check (20 chunks, `random.Random(7).sample(group, 5)` per source_type, in
`regulation, procedure, quran, hadith` order)

### Method note

Each row compares the printed chunk against the **extracted/OCR text** — `extract_text()`
output for regulation/procedure, the raw quran/hadith JSON for the others — not against
the original printed/scanned document. This spot-check therefore verifies that a chunk
faithfully reproduces what the parser saw, not that the underlying PDF's OCR is itself
correct. It follows that a systematic OCR misread that reads consistently (same wrong
word every time) will look "text complete: yes" here even though the word is wrong — see
"Known OCR-quality issues" below, found by inspection while re-running this spot-check
after the final-review fixes, not by this table's methodology.

| chunk_id | citation correct (yes/no) | domain correct? | text complete? | notes |
|---|---|---|---|---|
| khi-1991:pasal-214 | yes (KHI Pasal 214; verified against `extract_text` lines 2376-2381) | yes (kewarisan — last pasal of Buku II, `domain_rules: {buku: II -> kewarisan}`; confirmed "BUKU Ill" starts right after) | yes | none |
| khi-1991:pasal-35 | yes (KHI Pasal 35; verified against lines 501-507) | yes (perkawinan, Buku I, no override) | yes | none |
| uu-7-1989:pasal-73 | yes (UU 7/1989 Pasal 73) | yes (peradilan, manifest default domain) | yes | none |
| uu-1-1974:pasal-50 | yes (UU 1/1974 Pasal 50) | yes (perkawinan; perwalian content, not in the perceraian bab range) | yes | none |
| pp-9-1975:pasal-4 | yes (PP 9/1975 Pasal 4) | yes (perkawinan; content is about the marriage-notice procedure, not divorce) | yes | none |
| prosedur-waris:bagian-1 | yes (Prosedur Waris, bagian 1) | yes (prosedur) | yes | procedure text preserves the source HTML's list/checklist content |
| prosedur-cerai-talak:bagian-2 | yes (Prosedur Cerai Talak, bagian 2) | yes (prosedur) | yes | none |
| prosedur-cerai-gugat:bagian-1 | yes (Prosedur Cerai Gugat, bagian 1) | yes (prosedur) | yes | includes page chrome (breadcrumbs, "Published:...") from the HTML source, harmless for retrieval |
| prosedur-cerai-gugat:bagian-3 | yes (Prosedur Cerai Gugat, bagian 3) | yes (prosedur) | yes | includes trailing site-footer noise ("linktr.ee/...", "Pencarian") from the HTML source |
| prosedur-cerai-talak:bagian-1 | yes (Prosedur Cerai Talak, bagian 1) | yes (prosedur) | yes | same page-chrome note as above |
| quran:2:225 | yes (QS Al-Baqarah [2]: 225) | yes (perceraian — within the 2:224-242 selection range: ila'/talak/iddah) | yes | none |
| quran:58:4 | yes (QS Al-Mujadilah [58]: 4) | yes (perceraian — zihar, 58:1-4 range) | yes | none |
| quran:4:3 | yes (QS An-Nisa [4]: 3) | yes (perkawinan, 4:1-6 range) | yes | none |
| quran:2:222 | yes (QS Al-Baqarah [2]: 222) | yes (perkawinan, 2:221-223 range) | yes | none |
| quran:2:229 | yes (QS Al-Baqarah [2]: 229) | yes (perceraian, 2:224-242 range) | yes | none |
| hadith:tirmidhi:1153 | yes (HR. Tirmidzi no. 1153; hadithnumber==arabicnumber, text matches raw Arabic byte-for-byte) | yes (perkawinan) | yes | Arabic matn only, per Fix 1 |
| hadith:tirmidhi:1121 | yes (HR. Tirmidzi no. 1121; text matches raw Arabic byte-for-byte) | yes (perkawinan) | yes | Arabic matn only |
| hadith:bukhari:5165 | yes (HR. Bukhari no. 5165; text matches raw Arabic byte-for-byte) | yes (perkawinan) | yes | Arabic matn only |
| hadith:abudawud:2057 | yes (HR. Abu Dawud no. 2057; text matches raw Arabic byte-for-byte) | yes (perkawinan) | yes | Arabic matn only |
| hadith:bukhari:5209 | yes (HR. Bukhari no. 5209; text matches raw Arabic byte-for-byte) | yes (perkawinan) | yes | Arabic matn only |

The random sample above happened not to draw a `muslim` chunk this round (5 of 1708
hadith chunks, no `muslim` in this particular `Random(7).sample`); `hadith:muslim:1400`
is checked separately above under "Sahih Muslim numbering" as a targeted case for Fix 2,
confirmed byte-for-byte equal to the in-order join of hadithnumbers 3398-3402's Arabic
text.

No citation, domain, or completeness problems found in this sample, beyond the
two documented gaps (Pasal 124, 139 — see "Correction" above, updated in Fase 2
Task 2) and the OCR-quality issues below (found outside this sample, not by it,
and fixed in Fase 2 Task 2 — see "Fase 2 Task 2" below).

### Known OCR-quality issues (limitation, to fix in Fase 2)

Because this spot-check (and the parser) only ever sees `extract_text()`'s output, a
systematic OCR misread is invisible to it as long as the parser reproduces that
misread faithfully. One confirmed instance, found while re-checking KHI text for the
Fase 1 final review: **`khi-1991:pasal-176` and `khi-1991:pasal-177`** (both kewarisan,
Buku II) have `b` consistently misread as `h` by the source PDF's OCR — "hila" for
"bila", "hagian" for "bagian", "lehih" for "lebih", "apahila" for "apabila",
"hersama-sama" for "bersama-sama". The chunk text is a faithful transcription of what
`extract_text()` produced (so "text complete" would read "yes" against the OCR text),
but the OCR text itself is wrong relative to the printed KHI. Left unfixed in Fase 1 —
flagged here as a known limitation. **Fixed in Fase 2 Task 2**, see below.

## Fase 2 Task 2: page chrome, closing formula, KHI OCR corrections

**What was stripped from every regulation document** (`api/app/ingest/regulation.py`):

- **Page chrome**: `PRESIDEN`, `REPUBLIK INDONESIA`, `www.djpp.depkumham.go.id` — page
  headers repeated on every page of the peraturan.go.id / djpp-hosted PDFs, dropped
  by exact-match against `_CHROME_LINES`.
- **Page-turn catchwords**: a short line (<= 60 chars) ending in `...`/`…` — the PDF's
  bottom-of-page repeat of the next page's opening words (e.g. `"Pasal 2 …"`,
  `"(3) Ketentuan- ..."`), dropped by `RE_CATCHWORD`.
- **The enactment/closing formula**: everything from `"Agar (supaya) setiap orang
  dapat mengetahuinya..."` onward (the standard Indonesian enactment sentence,
  followed by "Disahkan di Jakarta", "ttd", the signer's name, and gazette numbers) —
  previously absorbed into the last pasal of each law as body text. `RE_CLOSING` now
  stops parsing at that line, same as `RE_STOP`/`RE_LAMPIRAN`.

**KHI OCR word corrections** (`Source.text_corrections`, applied whole-word,
case-preserving, before any heading/body parsing): a lowercase-keyed dict of
misread-word -> correct-word, applied only to `khi-1991` (the one OCR-scanned
source; born-digital sources get an empty dict, so `_corrector` is a no-op for
them). Two extra generic rules run first, only when `text_corrections` is
non-empty: a digit `1` between two lowercase letters is treated as a misread
letter `l` (`a1asan` -> `alasan`), and a reduplicated word glued together by the
extractor's soft-hyphen join is given its hyphen back (`masingmasing` ->
`masing-masing`).

Derivation rule for the word list: every key is a token that appears in
`khi-1991`'s OCR'd text but never in the other, born-digital regulations
(`uu-1-1974`, `uu-16-2019`, `pp-9-1975`, `uu-7-1989`, `uu-3-2006`, `uu-50-2009`,
`perma-1-2016`) while its corrected, real-word form does — i.e. a word that is
implausible as a genuine spelling but plausible as a b/h, m/rn, i/l, f/t, or
r-before-consonant/t OCR misread. The list was extended by cross-checking
`khi-1991` against the independent, born-digital `khi-1991-ma` reference text
(Mahkamah Agung Direktori Putusan): per shared pasal, every word present in the
Kemenag text but absent from the MA text was fuzzy-matched (`difflib`,
cutoff 0.8) against the MA text's words, and each candidate pair was reviewed by
hand — accepted only when the Kemenag word was implausible as a real word and
the MA word was a real word reachable by a documented OCR letter-swap; rejected
when the *MA* word was the wrong one (its own typo, e.g. `tentang` -> `tenyang`),
when the MA word was a fragment of the same word split by the MA extractor's
mid-word spacing (e.g. `pengadilan` -> `pengadil`, ~156 pairs — the bulk of the
candidates), or when the two were genuinely different real words (e.g.
`melakukan`/`meletakkan`, `iwadh`/`iwadl` — two valid transliteration spellings,
not a misread). 35 new corrections were accepted this way (e.g. `tetjadi` ->
`terjadi`, `petjanjian` -> `perjanjian`, `besamya` -> `besarnya`, `pennohonan` ->
`permohonan`); the cross-check confirmed `pasal only in Kemenag: []` and
`pasal only in MA: [215..229]` (Buku III, correctly skipped from `khi-1991` by
`domain_rules`) — i.e. every pasal `khi-1991` produces is also in the reference
text, so no OCR-scan-only content is going unchecked.

**KHI Pasal 138/139 relabel reverted**: see "Correction: khi-1991 Pasal 138 is
correctly numbered" above — the `pasal_overrides` mechanism is deleted, and the
only `chunk_id` change from this task is `khi-1991:pasal-139` -> `khi-1991:pasal-138`.

**Before/after, KHI Pasal 176** (`khi-1991:pasal-176`, kewarisan):

Before (raw OCR, as chunked in Fase 1):

```
Pasal 176
Anak perempuan hila hanya seorang ia mendapat
separoh hagian, hila dua orang atau lehih mereka
bersama-sama mendapat dua pertiga hagian, dan
apahila anak perempuan hersama-sama dengan anak
laki-laki. maka hagian anak laki-laki adalah dua
berbanding satu dengan anak perempuan.
```

After (`text_corrections` applied):

```
Pasal 176
Anak perempuan bila hanya seorang ia mendapat
separoh bagian, bila dua orang atau lebih mereka
bersama-sama mendapat dua pertiga bagian, dan
apabila anak perempuan bersama-sama dengan anak
laki-laki. maka bagian anak laki-laki adalah dua
berbanding satu dengan anak perempuan.
```

Regulation chunk count is unchanged at 569 (verified after rebuild); the only
`chunk_id` change in the whole corpus is the Pasal 138 relabel above.

## Fase 2b Task 2: page chrome, KHI OCR and the SEMA footnote

Every KHI correction below was checked against the Mahkamah Agung Direktori Putusan text
(`data/raw/khi-1991-ma.pdf`, reference only); nothing was filled from memory. Chunk ids and the
chunk count (2491) are unchanged; nine chunks changed text.

| Chunk | Fix | Mechanism |
|---|---|---|
| `uu-16-2019:pasal-7`, `pasal-ii` | page-chrome lines ("SK No 006?66 A", "trRESIDEN", "REPUBLIK' INDONESIA", lone "Agar") dropped | `RE_FUZZY_CHROME`, `"Agar"` in `_CHROME_LINES` |
| `khi-1991:pasal-116` | second "c. ... cacat badan" is "e." in the MA text; the last item stays "k." (both official texts say "k.") | `text_replacements` |
| `khi-1991:pasal-149` a | "Ia yak" -> "layak" | `text_replacements` |
| `khi-1991:pasal-149` c | scrambled lines restored to the MA order | `text_replacements` |
| `khi-1991:pasal-149` d, `-146` (2) | "anakanaknya" -> "anak-anaknya", "akibatakibatnya" -> "akibat-akibatnya" (MA: "akibat-akibatnya") | glued-reduplication rule learns `nya|lah|kah` |
| `khi-1991:pasal-183`, `-191` | "ahli wans" -> "ahli waris" | `text_corrections` `wans: waris` |
| `khi-1991:pasal-191` | "urn urn" -> "umum" | `text_replacements` |
| `khi-1991:pasal-185` -> `-177` | the "* Berdasarkan Surat Edaran Mahkamah Agung Nomor : 2 Tahun 1994 ..." footnote closes Pasal 177 in the MA text, not Pasal 185 | `footnote_moves: {"185": "177"}` |

`text_replacements` keys must each match at least once in the document and `footnote_moves`
must find both the footnote and its target, otherwise the build raises `ValueError`, so a
fix cannot silently stop applying.

Before (`khi-1991:pasal-149` c):

```
c. melunasi mahar yang
seluruhnya, dan separoh
dukhul;
masih terhutang
apabila qobla al
```

After:

```
c. melunasi mahar yang masih terhutang seluruhnya, dan separoh apabila qobla al dukhul;
```

Before (`khi-1991:pasal-185`): the footnote sat between ayat (1) and (2).

```
Pasal 185
( 1) Ahli waris yang meninggal lebih dahulu dari
...
* Berdasarkan Surat Edaran Mahkamah Agung
Nomor : 2 Tahun 1994, maksud pasal tersebut
...
(2) Bagian ahli waris pengganti tidak boleh melebihi
```

After: `khi-1991:pasal-185` runs ayat (1) straight into ayat (2); `khi-1991:pasal-177` ends with
the footnote ("* Berdasarkan Surat Edaran Mahkamah Agung ... ayah mendapat seperenam bagian.").

### Remaining OCR fixes (six more chunks, ids unchanged)

| Chunk | Fix | Evidence |
|---|---|---|
| `khi-1991:pasal-13`, `-184` | "bel urn" -> "belum" | MA text: "Pinangan belum menimbulkan", "ahli waris yang belum dewasa" |
| `khi-1991:pasal-149` a, `-160` | "mut' ah" -> "mut'ah" | MA text prints "mut`ah" (backtick) in both; the KHI chunk keeps the straight apostrophe |
| `uu-16-2019:pasal-ii` | "ini mulai berlaku pada tanggal" -> "Undang-Undang ini mulai berlaku pada tanggal diundangkan." | `extract_text` of the raw PDF puts "Undang-Undang" and "diundangkan." on lines before the "Pasal II" heading |
| `uu-16-2019:pasal-65a` | stray trailing "Undang-Undang\ndiundangkan." removed (they belong to Pasal II) | same extraction: the two lines follow Pasal 65A's last sentence |

All three are `text_replacements`. Known leftover, not touched: "Tahun L974" in `uu-16-2019:pasal-65a`
(OCR "L" for "1"; no second text checked yet).
