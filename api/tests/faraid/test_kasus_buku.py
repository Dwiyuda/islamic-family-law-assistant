"""Matriks kasus buku faraid. Nilai harapan dihitung manual dari KHI Buku II / kaidah faraid
(BUKAN disalin dari keluaran mesin); tiap baris menyertakan rujukan.

Baris inti: (input, {nama: (pembilang, penyebut) | None}, rujukan). None = ahli waris tidak
boleh muncul (terhijab / tidak berbagian)."""
from fractions import Fraction

import pytest

from app.faraid import hitung_faraid
from app.faraid.models import AhliWaris, FaraidRequest, Pengganti

TAFSIR = {"kakek", "nenek"}  # ahli waris bertafsir (docs/faraid-notes.md a, b)

KASUS = [
    # --- setiap ahli waris sendiri (sisa: asabah, atau radd ke dzawil furudh nasab; pasangan tanpa radd)
    (dict(suami=1), {"suami": (1, 2)}, "Pasal 179: duda 1/2 tanpa anak; tanpa radd ke pasangan"),
    (dict(istri=1), {"istri": (1, 4)}, "Pasal 180: janda 1/4 tanpa anak"),
    (dict(istri=4), {"istri": (1, 4)}, "Pasal 180: 4 istri berbagi rata 1/4"),
    (dict(anak_laki=1), {"anak_laki": (1, 1)}, "Pasal 176/ashabah: anak laki seluruh harta"),
    (dict(anak_perempuan=1), {"anak_perempuan": (1, 1)}, "Pasal 176 (1/2) + Pasal 193 radd"),
    (dict(anak_perempuan=3), {"anak_perempuan": (1, 1)}, "Pasal 176 (2/3) + Pasal 193 radd"),
    (dict(ayah=1), {"ayah": (1, 1)}, "Pasal 177: ayah ashabah tanpa keturunan"),
    (dict(ibu=1), {"ibu": (1, 1)}, "Pasal 178 ayat 1 (1/3) + Pasal 193 radd"),
    (dict(saudara_laki_kandung=1), {"saudara_laki_kandung": (1, 1)}, "Pasal 182: ashabah"),
    (dict(saudara_perempuan_kandung=1), {"saudara_perempuan_kandung": (1, 1)},
     "Pasal 182 ayat 1 (1/2) + radd 193"),
    (dict(saudara_laki_seayah=1), {"saudara_laki_seayah": (1, 1)}, "Pasal 182: ashabah"),
    (dict(saudara_perempuan_seayah=1), {"saudara_perempuan_seayah": (1, 1)},
     "Pasal 182 ayat 1 (1/2) + radd 193"),
    (dict(saudara_seibu=1), {"saudara_seibu": (1, 1)}, "Pasal 181 ayat 1 (1/6) + radd 193"),
    (dict(saudara_seibu=3), {"saudara_seibu": (1, 1)}, "Pasal 181 ayat 2 (1/3) + radd 193"),
    (dict(kakek=1), {"kakek": (1, 1)}, "Tafsir PA: kakek seperti ayah (faraid-notes b)"),
    (dict(nenek=1), {"nenek": (1, 1)}, "Tafsir PA: nenek 1/6 + radd (faraid-notes a)"),
    # --- suami/istri + anak
    (dict(suami=1, anak_laki=1), {"suami": (1, 4), "anak_laki": (3, 4)}, "Pasal 179, 176"),
    (dict(suami=1, anak_perempuan=1), {"suami": (1, 4), "anak_perempuan": (3, 4)},
     "Pasal 179, 176, 193: radd hanya ke anak, tidak ke duda"),
    (dict(suami=1, anak_perempuan=2), {"suami": (1, 4), "anak_perempuan": (3, 4)},
     "Pasal 179, 176 (2/3), 193 radd"),
    (dict(istri=1, anak_laki=1), {"istri": (1, 8), "anak_laki": (7, 8)}, "Pasal 180, 176"),
    (dict(istri=1, anak_perempuan=1), {"istri": (1, 8), "anak_perempuan": (7, 8)},
     "Pasal 180, 176, 193: radd tanpa pasangan"),
    (dict(istri=2, anak_laki=1, anak_perempuan=1),
     {"istri": (1, 8), "anak_laki": (7, 12), "anak_perempuan": (7, 24)},
     "Pasal 180 (2 istri berbagi 1/8), 176 ayat 2:1"),
    (dict(anak_laki=2, anak_perempuan=1), {"anak_laki": (4, 5), "anak_perempuan": (1, 5)},
     "Pasal 176: 2:1 (unit 5)"),
    (dict(anak_laki=1, anak_perempuan=2), {"anak_laki": (1, 2), "anak_perempuan": (1, 2)},
     "Pasal 176: 2:1 (unit 4)"),
    # --- ayah / ibu / anak
    (dict(ayah=1, anak_laki=1), {"ayah": (1, 6), "anak_laki": (5, 6)}, "Pasal 177, 176"),
    (dict(ayah=1, anak_perempuan=2), {"ayah": (1, 3), "anak_perempuan": (2, 3)},
     "Pasal 177 (1/6 + sisa), 176 (2/3)"),
    (dict(ayah=1, ibu=1, anak_laki=1), {"ayah": (1, 6), "ibu": (1, 6), "anak_laki": (2, 3)},
     "Pasal 177, 178 ayat 1, 176"),
    (dict(ayah=1, ibu=1, anak_perempuan=1),
     {"ayah": (1, 3), "ibu": (1, 6), "anak_perempuan": (1, 2)},
     "Pasal 176 (1/2), 178 (1/6), 177 (1/6 + sisa 1/6)"),
    (dict(ayah=1, ibu=1), {"ayah": (2, 3), "ibu": (1, 3)},
     "Pasal 178 ayat 1 (ibu 1/3); ayah ashabah 2/3 (praktik klasik/PA)"),
    (dict(ayah=1, istri=1), {"ayah": (3, 4), "istri": (1, 4)}, "Pasal 180, 177"),
    (dict(ayah=1, suami=1), {"ayah": (1, 2), "suami": (1, 2)}, "Pasal 179, 177"),
    (dict(suami=1, anak_laki=1, anak_perempuan=1, ibu=1, ayah=1),
     {"suami": (1, 4), "ibu": (1, 6), "ayah": (1, 6), "anak_laki": (5, 18),
      "anak_perempuan": (5, 36)},
     "Pasal 179,178,177,176: sisa 5/12 dibagi 2:1 (asal masalah 36)"),
    # --- gharrawayn / umariyyatan (Pasal 178 ayat 2)
    (dict(suami=1, ibu=1, ayah=1), {"suami": (1, 2), "ibu": (1, 6), "ayah": (1, 3)},
     "Pasal 178 ayat 2 gharrawayn: ibu 1/3 sisa setelah duda"),
    (dict(istri=1, ibu=1, ayah=1), {"istri": (1, 4), "ibu": (1, 4), "ayah": (1, 2)},
     "Pasal 178 ayat 2 gharrawayn: ibu 1/3 x 3/4 setelah janda"),
    # --- ibu + saudara
    (dict(ibu=1, saudara_laki_kandung=1), {"ibu": (1, 3), "saudara_laki_kandung": (2, 3)},
     "Pasal 178 ayat 1 (1 saudara: ibu 1/3), 182"),
    (dict(ibu=1, saudara_laki_kandung=2), {"ibu": (1, 6), "saudara_laki_kandung": (5, 6)},
     "Pasal 178 ayat 1 (2 saudara: ibu 1/6), 182"),
    (dict(suami=1, ibu=1, saudara_laki_kandung=1),
     {"suami": (1, 2), "ibu": (1, 3), "saudara_laki_kandung": (1, 6)}, "Pasal 179,178,182"),
    (dict(istri=2, saudara_laki_kandung=1), {"istri": (1, 4), "saudara_laki_kandung": (3, 4)},
     "Pasal 180, 182"),
    # --- 'aul (Pasal 192)
    (dict(suami=1, saudara_perempuan_kandung=1, saudara_seibu=1),
     {"suami": (3, 7), "saudara_perempuan_kandung": (3, 7), "saudara_seibu": (1, 7)},
     "Pasal 192: 'aul 6->7 (3+3+1)"),
    (dict(suami=1, saudara_perempuan_kandung=2),
     {"suami": (3, 7), "saudara_perempuan_kandung": (4, 7)}, "Pasal 192: 'aul 6->7 (3+4)"),
    (dict(suami=1, saudara_perempuan_kandung=2, ibu=1),
     {"suami": (3, 8), "saudara_perempuan_kandung": (1, 2), "ibu": (1, 8)},
     "Pasal 192: 'aul 6->8 (3+4+1), mubahalah"),
    (dict(suami=1, saudara_perempuan_kandung=2, saudara_seibu=2),
     {"suami": (1, 3), "saudara_perempuan_kandung": (4, 9), "saudara_seibu": (2, 9)},
     "Pasal 192: 'aul 6->9 (3+4+2), marwaniyyah"),
    (dict(istri=1, ibu=1, saudara_perempuan_kandung=2),
     {"istri": (3, 13), "ibu": (2, 13), "saudara_perempuan_kandung": (8, 13)},
     "Pasal 192: 'aul 12->13 (3+2+8)"),
    (dict(istri=1, saudara_perempuan_kandung=2, saudara_seibu=2),
     {"istri": (1, 5), "saudara_perempuan_kandung": (8, 15), "saudara_seibu": (4, 15)},
     "Pasal 192: 'aul 12->15 (3+8+4)"),
    (dict(istri=1, ibu=1, saudara_perempuan_kandung=2, saudara_seibu=2),
     {"istri": (3, 17), "ibu": (2, 17), "saudara_perempuan_kandung": (8, 17),
      "saudara_seibu": (4, 17)},
     "Pasal 192: 'aul 12->17 (3+2+8+4)"),
    (dict(istri=1, ibu=1, ayah=1, anak_perempuan=2),
     {"istri": (1, 9), "ibu": (4, 27), "ayah": (4, 27), "anak_perempuan": (16, 27)},
     "Pasal 192: 'aul 24->27 (3+4+4+16), masalah minbariyyah"),
    # --- radd (Pasal 193)
    (dict(anak_perempuan=1, ibu=1), {"anak_perempuan": (3, 4), "ibu": (1, 4)},
     "Pasal 193: radd tanpa pasangan, sisa 1/3 dibagi 3:1"),
    (dict(ibu=1, saudara_seibu=1), {"ibu": (2, 3), "saudara_seibu": (1, 3)},
     "Pasal 193: radd tanpa pasangan (1/3 : 1/6 = 2:1)"),
    (dict(ibu=1, saudara_seibu=2), {"ibu": (1, 3), "saudara_seibu": (2, 3)},
     "Pasal 193: radd tanpa pasangan (1/6 : 1/3 = 1:2)"),
    (dict(istri=1, ibu=1, saudara_seibu=1),
     {"istri": (1, 4), "ibu": (1, 2), "saudara_seibu": (1, 4)},
     "Pasal 193: radd dengan pasangan; pasangan tidak ikut radd, sisa 3/4 dibagi 2:1"),
    (dict(suami=1, saudara_seibu=1), {"suami": (1, 2), "saudara_seibu": (1, 2)},
     "Pasal 193: radd dengan pasangan; seibu menerima sisa"),
    (dict(saudara_perempuan_kandung=1, ibu=1), {"saudara_perempuan_kandung": (3, 5), "ibu": (2, 5)},
     "Pasal 182 (1/2), 178 (1/3), 193 radd 3:2"),
    (dict(istri=1, saudara_perempuan_kandung=2), {"istri": (1, 4), "saudara_perempuan_kandung": (3, 4)},
     "Pasal 180, 182 (2/3), 193 radd tanpa pasangan"),
    # --- saudara seibu
    (dict(saudara_seibu=1, saudara_laki_kandung=1),
     {"saudara_seibu": (1, 6), "saudara_laki_kandung": (5, 6)}, "Pasal 181 ayat 1, 182"),
    (dict(saudara_seibu=3, saudara_laki_kandung=1),
     {"saudara_seibu": (1, 3), "saudara_laki_kandung": (2, 3)},
     "Pasal 181 ayat 2: >=2 seibu berbagi rata 1/3"),
    (dict(saudara_seibu=1, anak_laki=1), {"anak_laki": (1, 1), "saudara_seibu": None},
     "Pasal 181: seibu gugur bila ada keturunan"),
    (dict(saudara_seibu=1, ayah=1), {"ayah": (1, 1), "saudara_seibu": None},
     "Pasal 181: seibu gugur bila ada ayah"),
    # --- saudari kandung
    (dict(suami=1, saudara_perempuan_kandung=1),
     {"suami": (1, 2), "saudara_perempuan_kandung": (1, 2)}, "Pasal 179, 182 ayat 1"),
    (dict(saudara_laki_kandung=1, saudara_perempuan_kandung=1),
     {"saudara_laki_kandung": (2, 3), "saudara_perempuan_kandung": (1, 3)}, "Pasal 182 ayat 3: 2:1"),
    (dict(saudara_laki_kandung=2, saudara_perempuan_kandung=1),
     {"saudara_laki_kandung": (4, 5), "saudara_perempuan_kandung": (1, 5)}, "Pasal 182 ayat 3: 2:1"),
    # --- saudara seayah
    (dict(suami=1, saudara_perempuan_seayah=1),
     {"suami": (1, 2), "saudara_perempuan_seayah": (1, 2)},
     "Pasal 182 ayat 1 (seayah tanpa saudari kandung: 1/2)"),
    (dict(saudara_perempuan_seayah=1, ibu=1), {"saudara_perempuan_seayah": (3, 5), "ibu": (2, 5)},
     "Pasal 182 (1/2), 178 (1/3), radd 3:2"),
    (dict(saudara_perempuan_seayah=2, ibu=1), {"saudara_perempuan_seayah": (4, 5), "ibu": (1, 5)},
     "Pasal 182 ayat 2 (seayah >=2: 2/3), 178 (1/6), radd 4:1"),
    (dict(saudara_laki_seayah=1, saudara_perempuan_seayah=1),
     {"saudara_laki_seayah": (2, 3), "saudara_perempuan_seayah": (1, 3)}, "Pasal 182 ayat 3: 2:1"),
    (dict(saudara_laki_kandung=1, saudara_laki_seayah=1),
     {"saudara_laki_kandung": (1, 1), "saudara_laki_seayah": None},
     "Kandung menghijab seayah (Pasal 182)"),
    (dict(saudara_laki_kandung=1, saudara_perempuan_seayah=1),
     {"saudara_laki_kandung": (1, 1), "saudara_perempuan_seayah": None},
     "Saudara laki kandung menghijab saudari seayah"),
    (dict(saudara_perempuan_kandung=2, saudara_perempuan_seayah=1),
     {"saudara_perempuan_kandung": (1, 1), "saudara_perempuan_seayah": None},
     "Saudari kandung >=2 (2/3) menghabiskan furudh; saudari seayah tanpa bagian"),
    (dict(saudara_perempuan_kandung=1, saudara_laki_seayah=1),
     {"saudara_perempuan_kandung": (1, 2), "saudara_laki_seayah": (1, 2)},
     "Saudari kandung 1/2, saudara laki seayah ashabah sisa"),
    # --- takmilah (saudari kandung 1 + saudari seayah -> 2/3)
    (dict(saudara_perempuan_kandung=1, saudara_perempuan_seayah=1),
     {"saudara_perempuan_kandung": (3, 4), "saudara_perempuan_seayah": (1, 4)},
     "Takmilah: 1/2 + 1/6 = 2/3, lalu radd 3:1 (Pasal 182, 193)"),
    (dict(suami=1, saudara_perempuan_kandung=1, saudara_perempuan_seayah=1),
     {"suami": (3, 7), "saudara_perempuan_kandung": (3, 7), "saudara_perempuan_seayah": (1, 7)},
     "Takmilah 1/6 + 'aul 6->7 (Pasal 182, 192)"),
    # --- asabah ma'al-ghair (saudari bersama anak perempuan)
    (dict(anak_perempuan=1, saudara_perempuan_kandung=1),
     {"anak_perempuan": (1, 2), "saudara_perempuan_kandung": (1, 2)},
     "Asabah ma'al-ghair: saudari kandung ambil sisa (Pasal 176, 182)"),
    (dict(anak_perempuan=1, saudara_perempuan_seayah=1),
     {"anak_perempuan": (1, 2), "saudara_perempuan_seayah": (1, 2)},
     "Asabah ma'al-ghair: saudari seayah ambil sisa"),
    (dict(anak_perempuan=1, saudara_perempuan_kandung=2),
     {"anak_perempuan": (1, 2), "saudara_perempuan_kandung": (1, 2)},
     "Asabah ma'al-ghair: 2 saudari berbagi sisa 1/2"),
    (dict(anak_perempuan=2, saudara_perempuan_kandung=1),
     {"anak_perempuan": (2, 3), "saudara_perempuan_kandung": (1, 3)},
     "Asabah ma'al-ghair: sisa 1/3 setelah 2/3"),
    (dict(anak_perempuan=1, ibu=1, saudara_perempuan_kandung=1),
     {"anak_perempuan": (1, 2), "ibu": (1, 6), "saudara_perempuan_kandung": (1, 3)},
     "Asabah ma'al-ghair + ibu 1/6 (Pasal 176, 178, 182)"),
    (dict(anak_perempuan=1, saudara_perempuan_kandung=1, saudara_perempuan_seayah=1),
     {"anak_perempuan": (1, 2), "saudara_perempuan_kandung": (1, 2), "saudara_perempuan_seayah": None},
     "Saudari kandung (asabah ma'al-ghair) menghijab saudari seayah"),
    # --- hijab
    (dict(ayah=1, saudara_laki_kandung=1), {"ayah": (1, 1), "saudara_laki_kandung": None},
     "Pasal 182: saudara gugur bila ada ayah"),
    (dict(anak_laki=1, saudara_laki_kandung=1), {"anak_laki": (1, 1), "saudara_laki_kandung": None},
     "Pasal 182: saudara gugur bila ada anak"),
    # --- nenek (tafsir 1/6)
    (dict(nenek=1, anak_laki=1), {"nenek": (1, 6), "anak_laki": (5, 6)},
     "Tafsir PA: nenek 1/6 (faraid-notes a)"),
    (dict(nenek=2, anak_laki=1), {"nenek": (1, 6), "anak_laki": (5, 6)},
     "Tafsir PA: 2 nenek berbagi rata 1/6 (faraid-notes a)"),
    (dict(nenek=1, anak_perempuan=1), {"nenek": (1, 4), "anak_perempuan": (3, 4)},
     "Nenek 1/6 + anak perempuan 1/2, radd 3:1 (faraid-notes a, Pasal 193)"),
    # --- kakek pengganti ayah (tafsir)
    (dict(kakek=1, istri=1), {"kakek": (3, 4), "istri": (1, 4)},
     "Kakek pengganti ayah tanpa keturunan: ashabah (faraid-notes b)"),
    (dict(kakek=1, anak_laki=1), {"kakek": (1, 6), "anak_laki": (5, 6)},
     "Kakek dengan keturunan laki: 1/6 (faraid-notes b)"),
    (dict(kakek=1, anak_perempuan=1), {"kakek": (1, 2), "anak_perempuan": (1, 2)},
     "Kakek dengan keturunan perempuan: 1/6 + sisa 1/3 (faraid-notes b)"),
    (dict(kakek=1, ibu=1, anak_laki=1), {"kakek": (1, 6), "ibu": (1, 6), "anak_laki": (2, 3)},
     "Kakek 1/6, ibu 1/6, anak laki sisa (faraid-notes b)"),
    (dict(kakek=1, saudara_laki_kandung=1), {"kakek": (1, 1), "saudara_laki_kandung": None},
     "Kakek menghijab saudara (tafsir PA, beda dengan muqasamah; faraid-notes b)"),
]


def _req(input_, harta=0, **kw):
    jk = "P" if input_.get("suami") else "L"
    return FaraidRequest(harta_bersih=harta, pewaris_jenis_kelamin=jk,
                         ahli_waris=AhliWaris(**input_), **kw)


def _got(r):
    return {b.ahli_waris: (b.bagian_pembilang, b.bagian_penyebut) for b in r.bagian}


def _cek_invarian(r, input_):
    total = sum((Fraction(b.bagian_pembilang, b.bagian_penyebut) for b in r.bagian), Fraction(0))
    assert total <= 1
    if set(k for k, v in input_.items() if v) - {"suami", "istri"}:
        assert total == 1  # ada ahli waris nasab -> seluruh harta terbagi


def test_jumlah_kasus_minimal():
    assert len(KASUS) + len(PENGGANTI) + len(DI_LUAR) >= 50


@pytest.mark.parametrize("input_,harap,rujukan", KASUS)
def test_kasus_buku(input_, harap, rujukan):
    r = hitung_faraid(_req(input_))
    assert r.status == "ok", rujukan
    got = _got(r)
    for nama, nilai in harap.items():
        assert got.get(nama) == nilai, f"{rujukan}: {nama} = {got.get(nama)} != {nilai}"
    _cek_invarian(r, input_)
    # kasus bertafsir (kakek/nenek menerima bagian) wajib ditandai; kasus inti tidak
    bertafsir = any(input_.get(k) and got.get(k) for k in TAFSIR)
    assert r.perlu_verifikasi_ahli is bertafsir, rujukan


# --- Pasal 185: (input hidup, pengganti, harap, rujukan, dibatasi_ayat2)
PENGGANTI = [
    (dict(anak_laki=1), [Pengganti(menggantikan="anak_laki", anak_laki=1, anak_perempuan=1)],
     {"anak_laki": (1, 2), "pengganti_anak_laki": (1, 2)},
     "Pasal 185: cucu dari anak laki wafat; 1/2 = batas anak laki hidup, tidak terpotong", False),
    (dict(istri=1), [Pengganti(menggantikan="anak_laki", anak_laki=1)],
     {"istri": (1, 8), "pengganti_anak_laki": (7, 8)},
     "Pasal 185: tanpa ahli waris sederajat hidup, tidak ada batas; istri 1/8", False),
    (dict(anak_laki=1), [Pengganti(menggantikan="anak_perempuan", anak_perempuan=1)],
     {"anak_laki": (2, 3), "pengganti_anak_perempuan": (1, 3)},
     "Pasal 185: cucu dari anak perempuan wafat menerima bagian ibunya (1/3)", False),
    (dict(anak_laki=1), [Pengganti(menggantikan="anak_perempuan", anak_laki=1, anak_perempuan=1)],
     {"anak_laki": (2, 3), "pengganti_anak_perempuan": (1, 3)},
     "Pasal 185: cucu dari anak perempuan wafat, bagian 1/3 dibagi 2:1", False),
    (dict(anak_perempuan=1), [Pengganti(menggantikan="anak_laki", anak_laki=1)],
     {"anak_perempuan": (2, 3), "pengganti_anak_laki": (1, 3)},
     "Pasal 185 ayat 2: 2/3 dipotong ke bagian anak perempuan hidup (1/3); selisih kembali (faraid-notes c)",
     True),
    (dict(anak_perempuan=2), [Pengganti(menggantikan="anak_laki", anak_laki=2)],
     {"anak_perempuan": (3, 4), "pengganti_anak_laki": (1, 4)},
     "Pasal 185 ayat 2: 1/2 dipotong ke 1/4 (per anak perempuan); selisih 1/4 kembali", True),
    (dict(ayah=1, ibu=1), [Pengganti(menggantikan="anak_laki", anak_laki=1)],
     {"ayah": (1, 6), "ibu": (1, 6), "pengganti_anak_laki": (2, 3)},
     "Pasal 185: anak wafat dihitung hidup -> ayah/ibu 1/6 (Pasal 177, 178)", False),
    (dict(saudara_laki_kandung=1), [Pengganti(menggantikan="saudara_laki_kandung", anak_laki=1)],
     {"saudara_laki_kandung": (1, 2), "pengganti_saudara_laki_kandung": (1, 2)},
     "Pasal 185 untuk saudara kandung wafat (faraid-notes c)", False),
    (dict(saudara_perempuan_kandung=1),
     [Pengganti(menggantikan="saudara_laki_kandung", anak_laki=1)],
     {"saudara_perempuan_kandung": (2, 3), "pengganti_saudara_laki_kandung": (1, 3)},
     "Pasal 185 ayat 2 untuk saudara: 2/3 dipotong ke 1/3 (bagian saudari hidup); selisih kembali", True),
    (dict(anak_laki=1),
     [Pengganti(menggantikan="anak_laki", anak_laki=1),
      Pengganti(menggantikan="anak_perempuan", anak_perempuan=1)],
     {"anak_laki": (2, 5), "pengganti_anak_laki": (2, 5), "pengganti_anak_perempuan": (1, 5)},
     "Pasal 185: dua entri posisi berbeda; hipotetis 2 anak laki + 1 anak perempuan (unit 5)", False),
    (dict(anak_laki=1),
     [Pengganti(menggantikan="anak_laki", anak_laki=1),
      Pengganti(menggantikan="anak_laki", anak_perempuan=2)],
     {"anak_laki": (1, 3), "pengganti_anak_laki": (1, 3), "pengganti_anak_laki_2": (1, 3)},
     "Pasal 185: dua entri posisi sama (3 anak laki hipotetis, 1/3 masing-masing)", False),
    (dict(anak_perempuan=1),
     [Pengganti(menggantikan="anak_laki", anak_laki=1),
      Pengganti(menggantikan="anak_laki", anak_perempuan=1)],
     {"anak_perempuan": (3, 5), "pengganti_anak_laki": (1, 5), "pengganti_anak_laki_2": (1, 5)},
     "Pasal 185 ayat 2: dua entri sama, tiap grup 2/5 dipotong ke 1/5; selisih 2/5 ke anak perempuan", True),
]


@pytest.mark.parametrize("input_,pengganti,harap,rujukan,dibatasi", PENGGANTI)
def test_pengganti_pasal_185(input_, pengganti, harap, rujukan, dibatasi):
    r = hitung_faraid(_req(input_, pengganti=pengganti))
    assert r.status == "ok", rujukan
    assert _got(r) == {n: v for n, v in harap.items()}, rujukan
    assert sum(Fraction(p, q) for p, q in _got(r).values()) == 1
    assert r.perlu_verifikasi_ahli is True, rujukan
    assert any("ayat 2" in c for c in r.catatan) is dibatasi, rujukan


def _ket(r, nama):
    return next(b.keterangan for b in r.bagian if b.ahli_waris == nama)


def test_pengganti_split_2_banding_1_cucu_laki_perempuan():
    # cucu laki 1 + cucu perempuan 1 dari anak laki wafat; grup 1/2 -> laki 1/3, perempuan 1/6
    r = hitung_faraid(_req(dict(anak_laki=1), pengganti=[
        Pengganti(menggantikan="anak_laki", anak_laki=1, anak_perempuan=1)]))
    assert "laki-laki 1/3, perempuan 1/6" in _ket(r, "pengganti_anak_laki")
    # grup 1/3 dari anak perempuan wafat -> laki 2/9, perempuan 1/9
    r = hitung_faraid(_req(dict(anak_laki=1), pengganti=[
        Pengganti(menggantikan="anak_perempuan", anak_laki=1, anak_perempuan=1)]))
    assert "laki-laki 2/9, perempuan 1/9" in _ket(r, "pengganti_anak_perempuan")


# --- di luar cakupan (ditolak, tanpa menghitung)
DI_LUAR = [
    (["dzawil_arham"], [], "Dzawil arham tidak diatur KHI"),
    (["janin"], [], "Janin: pewarisan menunggu kelahiran, di luar mesin"),
    (["khuntsa"], [], "Khuntsa (kelamin ganda), di luar mesin"),
    (["munasakhah"], [], "Munasakhah (ahli waris wafat sebelum pembagian), di luar mesin"),
    (["dzawil_arham", "janin"], [], "Gabungan dua kategori"),
    ([], ["ayah"], "Pengganti untuk ayah tidak didukung (faraid-notes c)"),
    ([], ["suami"], "Pengganti untuk suami tidak didukung (faraid-notes c)"),
]


@pytest.mark.parametrize("luar,posisi,rujukan", DI_LUAR)
def test_di_luar_cakupan(luar, posisi, rujukan):
    pengganti = [Pengganti(menggantikan=p, anak_laki=1) for p in posisi]
    r = hitung_faraid(_req(dict(anak_laki=1), pengganti=pengganti, di_luar_cakupan=luar))
    assert r.status == "di_luar_cakupan", rujukan
    assert r.bagian == [] and r.catatan, rujukan


# --- asal masalah, 'aul, radd (diturunkan manual)
ASAL = [
    (dict(suami=1, ibu=1, ayah=1), 6, False, False, "1/2,1/6,1/3 -> KPK 6"),
    (dict(istri=1, anak_laki=1), 8, False, False, "1/8,7/8 -> 8"),
    (dict(suami=1, anak_laki=1, anak_perempuan=1, ibu=1, ayah=1), 36, False, False, "KPK 4,6,18,36"),
    (dict(istri=1, ibu=1, saudara_perempuan_kandung=2), 13, True, False, "12->13"),
    (dict(istri=1, ibu=1, ayah=1, anak_perempuan=2), 27, True, False, "24->27"),
    (dict(anak_perempuan=1, ibu=1), 4, False, True, "radd 3/4,1/4"),
]


@pytest.mark.parametrize("input_,asal,aul,radd,rujukan", ASAL)
def test_asal_masalah_aul_radd(input_, asal, aul, radd, rujukan):
    r = hitung_faraid(_req(input_))
    assert (r.asal_masalah, r.aul_terjadi, r.radd_terjadi) == (asal, aul, radd), rujukan


def test_nominal_dan_sisa_pembulatan():
    # gharrawayn 1/2, 1/6, 1/3 dari 1000: 500 + floor(166,67)=166 + floor(333,33)=333 = 999 -> sisa 1
    r = hitung_faraid(_req(dict(suami=1, ibu=1, ayah=1), harta=1000))
    nominal = {b.ahli_waris: b.nominal for b in r.bagian}
    assert nominal == {"suami": 500, "ibu": 166, "ayah": 333}
    assert r.sisa_pembulatan == 1
    # 'aul 12->13: 3/13, 2/13, 8/13 dari 1000 -> 230 + 153 + 615 = 998 -> sisa 2
    r = hitung_faraid(_req(dict(istri=1, ibu=1, saudara_perempuan_kandung=2), harta=1000))
    nominal = {b.ahli_waris: b.nominal for b in r.bagian}
    assert nominal == {"istri": 230, "ibu": 153, "saudara_perempuan_kandung": 615}
    assert r.sisa_pembulatan == 2
    # habis dibagi: 1/8 dan 7/8 dari 1000
    r = hitung_faraid(_req(dict(istri=1, anak_laki=1), harta=1000))
    assert {b.ahli_waris: b.nominal for b in r.bagian} == {"istri": 125, "anak_laki": 875}
    assert r.sisa_pembulatan == 0
