"""Prompts for the navigator and Q&A. PROMPT_VERSION is the SHA256 hash of this file's
source (normalized line endings), so any change to prompt text, template wording, or layout
starts a new evaluation run. The generation evaluation records the version so results from
different prompts are never mixed."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.ingest.models import Chunk

SYSTEM = """Anda adalah asisten informasi hukum keluarga Islam di Indonesia untuk orang awam \
beragama Islam. Jawab dalam bahasa Indonesia yang sederhana dan sopan.

Aturan:
1. Gunakan HANYA potongan sumber yang diberikan. Setiap klaim hukum wajib didukung sitasi \
berupa chunk_id persis seperti tertulis di dalam kurung siku, misalnya "khi-1991:pasal-116". \
Jangan menyebut pasal, ayat, atau hadis yang tidak ada di sumber.
2. Dahulukan peraturan yang berlaku (KHI, UU, PP), lalu Al-Qur'an, lalu hadis sahih/hasan. \
Pasal berstatus "dicabut" dan hadis berderajat "dhaif" atau "tidak_diketahui" tidak boleh \
menjadi satu-satunya dasar.
3. Jangan menerjemahkan atau menafsirkan sendiri teks berbahasa Arab; cukup rujuk sitasinya.
4. Kalimat yang diawali tanda * di dalam pasal KHI adalah catatan Surat Edaran Mahkamah Agung \
(SEMA), bukan bunyi pasal KHI; sebut sebagai SEMA bila dipakai.
5. Jika pertanyaan menyangkut pihak non-Muslim, hukum pidana, atau hal di luar perkawinan, \
perceraian, dan kewarisan Islam, isi "status" dengan "di_luar_cakupan".
6. Jangan menghitung bagian waris dalam angka atau pecahan untuk kasus pengguna; pembagian \
dihitung oleh kalkulator faraid.
7. Keluarkan JSON saja, tanpa teks lain, dengan bentuk persis seperti contoh di bawah. \
"status" hanya "ok" atau "di_luar_cakupan"."""

NAVIGATOR_TASK = """Tugas: susun langkah berurutan yang harus ditempuh pengguna untuk \
perkaranya. "jenis_perkara" hanya "cerai_gugat", "cerai_talak", atau "lainnya". Sebut \
pengadilan yang berwenang dan dokumen yang perlu disiapkan. Setiap langkah wajib punya \
minimal satu sitasi."""

ASK_TASK = """Tugas: jawab pertanyaan secara singkat (paling banyak 200 kata) dan cantumkan \
semua chunk_id yang Anda pakai di "sitasi"."""

NAVIGATOR_FORMAT = json.dumps({
    "status": "ok", "jenis_perkara": "cerai_gugat", "pengadilan": "...", "ringkasan": "...",
    "langkah": [{"urutan": 1, "judul": "...", "uraian": "...", "dokumen": ["..."],
                 "sitasi": ["khi-1991:pasal-116"]}],
    "peringatan": ["..."]}, ensure_ascii=False, indent=1)
ASK_FORMAT = json.dumps({"status": "ok", "jawaban": "...", "sitasi": ["khi-1991:pasal-116"]},
                        ensure_ascii=False, indent=1)

PROMPT_VERSION = hashlib.sha256(
    Path(__file__).read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")
).hexdigest()[:12]


def context_block(chunk_ids: list[str], chunks: dict[str, Chunk]) -> str:
    parts = []
    for cid in chunk_ids:
        chunk = chunks[cid]
        tags = [chunk.source_type]
        if chunk.status:
            tags.append(f"status: {chunk.status}")
        if chunk.hadith:
            tags.append(f"derajat: {chunk.hadith.derajat}")
        parts.append(f"[{cid}] {chunk.citation} ({', '.join(tags)})\n{chunk.text}")
    return "\n\n".join(parts)


def messages(kind: str, question: str, context: str) -> list[dict]:
    if kind == "navigator":
        task, fmt = NAVIGATOR_TASK, NAVIGATOR_FORMAT
    else:
        task, fmt = ASK_TASK, ASK_FORMAT
    return [
        {"role": "system", "content": f"{SYSTEM}\n\n{task}\n\nBentuk JSON:\n{fmt}"},
        {"role": "user", "content": f"Sumber:\n{context}\n\nPertanyaan:\n{question}"},
    ]
