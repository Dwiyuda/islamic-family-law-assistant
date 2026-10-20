from __future__ import annotations

import re

from .models import Chunk
from .sources import Source

# (surah, first ayat, last ayat, domain)
QURAN_SELECTION: list[tuple[int, int, int, str]] = [
    (2, 180, 182, "kewarisan"),   # wasiat
    (2, 221, 223, "perkawinan"),
    (2, 224, 242, "perceraian"),  # ila', talak, iddah, rujuk, nafkah
    (4, 1, 6, "perkawinan"),
    (4, 7, 14, "kewarisan"),      # ayat waris
    (4, 19, 25, "perkawinan"),
    (4, 34, 35, "perceraian"),    # nusyuz, syiqaq
    (4, 127, 130, "perkawinan"),
    (4, 176, 176, "kewarisan"),   # kalalah
    (5, 106, 108, "kewarisan"),   # saksi wasiat
    (8, 75, 75, "kewarisan"),
    (24, 32, 33, "perkawinan"),
    (33, 6, 6, "kewarisan"),
    (33, 49, 49, "perceraian"),
    (58, 1, 4, "perceraian"),     # zihar
    (65, 1, 7, "perceraian"),     # At-Talaq
]

SURAH_NAMES: dict[int, str] = {
    2: "Al-Baqarah", 4: "An-Nisa", 5: "Al-Ma'idah", 8: "Al-Anfal",
    24: "An-Nur", 33: "Al-Ahzab", 58: "Al-Mujadilah", 65: "At-Talaq",
}

_FOOTNOTE = re.compile(r"(?<![(\d])\d{1,4}\)")


def clean_translation(text: str) -> str:
    return re.sub(r"\s{2,}", " ", _FOOTNOTE.sub("", text)).strip()


def _index(edition: dict) -> dict[tuple[int, int], str]:
    return {(v["chapter"], v["verse"]): v["text"] for v in edition["quran"]}


def parse_quran(ara_json: dict, ind_json: dict, ara: Source, ind: Source) -> list[Chunk]:
    arabic, indonesian = _index(ara_json), _index(ind_json)
    chunks: list[Chunk] = []
    for surah, first, last, domain in QURAN_SELECTION:
        for ayat in range(first, last + 1):
            key = (surah, ayat)
            if key not in arabic or key not in indonesian:
                continue
            chunks.append(Chunk(
                chunk_id=f"quran:{surah}:{ayat}", doc_id="quran",
                doc_title="Al-Qur'an dan terjemahan Kementerian Agama RI",
                source_type="quran", domain=domain,
                hierarchy={"surah": str(surah), "ayat": str(ayat)},
                citation=f"QS {SURAH_NAMES[surah]} [{surah}]: {ayat}",
                text=clean_translation(indonesian[key]), text_ar=arabic[key].strip(),
                source_url=ind.url_sumber, license=f"{ara.lisensi}; terjemahan: {ind.lisensi}",
            ))
    return chunks
