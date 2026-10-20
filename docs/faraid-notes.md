# Catatan Tafsir Mesin Faraid

Mesin (`api/app/faraid/`) menghitung berdasarkan KHI Buku II (Pasal 171-193). Beberapa hal tidak diatur
rinci oleh teks KHI sehingga mesin memakai tafsir (praktik Pengadilan Agama / fikih). Setiap hasil yang
memakai tafsir di bawah ini otomatis ditandai `perlu_verifikasi_ahli=True` dan `catatan` merujuk berkas ini.
Perhitungan ini informasi umum, bukan nasihat hukum.

## (a) Nenek 1/6 -- di luar teks literal KHI, perlu verifikasi ahli
- KHI hanya menyebut nenek sebagai ahli waris dalam Pasal 174 ayat (1) huruf a (golongan perempuan: ibu, anak
  perempuan, saudara perempuan dari pewaris, **nenek**); tidak ada pasal yang menentukan bagiannya.
- Mesin: nenek menerima **1/6**; satu atau lebih nenek **berbagi rata** dalam 1/6 itu. Dasar: praktik PA / fikih.
- Terhalang **ibu** (hijab oleh ibu juga tafsir; KHI tidak mengaturnya).
- **Batasan yang diketahui:** model input hanya punya satu kolom `nenek` tanpa sisi (pihak ayah/pihak ibu).
  Aturan "ayah juga menghalangi nenek pihak ayah" tidak dapat dibedakan, sehingga nenek hanya dihalangi ibu.
  Bila ayah hidup dan nenek dari pihak ayah, hasil bisa keliru; wajib diverifikasi ahli.

## (b) Kakek seperti ayah, menghijab saudara -- di luar teks literal KHI, perlu verifikasi ahli
- KHI hanya menyebut kakek di Pasal 174 ayat (1) huruf a (golongan laki-laki); bagian dan hijabnya tidak diatur.
- Mesin (hanya bila ayah tidak ada; ayah menghalangi kakek): kakek menempati posisi ayah (Pasal 177):
  **1/6** bila ada keturunan (anak/anak perempuan), ditambah **sisa sebagai asabah** (tanpa keturunan: seluruh sisa),
  dan **menghijab semua saudara** (kandung, seayah, seibu), seperti ayah.
- **Beda dengan fikih klasik:** mazhab Zaid bin Tsabit (jumhur) memakai *muqasamah*: kakek berbagi sisa dengan
  saudara kandung/seayah (kakek mengambil yang terbaik antara muqasamah, 1/3 sisa, atau 1/6), jadi saudara
  tidak otomatis gugur. Pendapat Abu Bakr, Ibnu Abbas, dan Abu Hanifah menyamakan kakek dengan ayah (menghijab
  saudara). Mesin mengikuti pendapat kedua yang diamalkan PA; hasil bisa berbeda dari muqasamah.
- Tidak ada gharrawayn (Pasal 178 ayat 2) untuk kakek; hanya untuk ayah.

## (c) Ahli waris pengganti, Pasal 185 -- di luar teks literal KHI (mekanisme), perlu verifikasi ahli
- **Teks KHI:** Pasal 185 ayat (1): ahli waris yang meninggal lebih dahulu daripada pewaris, kedudukannya dapat
  digantikan oleh anaknya, kecuali mereka yang tersebut dalam Pasal 173. Ayat (2): bagian ahli waris pengganti
  tidak boleh melebihi bagian ahli waris yang sederajat dengan yang diganti. KHI tidak menjelaskan cara menghitung.
- **Posisi yang didukung:** `anak_laki`, `anak_perempuan`, `saudara_laki/perempuan_kandung`,
  `saudara_laki/perempuan_seayah`. Posisi lain (mis. `ayah`, `suami`) -> `status="di_luar_cakupan"`.
  Satu entri `Pengganti` = satu ahli waris yang wafat, dengan anak-anaknya (`anak_laki`, `anak_perempuan`).
  Pengganti satu tingkat saja (anak langsung); cucu dari cucu tidak dimodelkan.
- **Mekanisme hitung (tafsir):**
  1. Ahli waris yang wafat dihitung seolah hidup, sehingga ikut menentukan hijab dan bagian ahli waris lain
     (mis. ibu 1/6 karena ada keturunan; saudara terhijab anak laki).
  2. Bagian orang tua yang wafat (bagian per orang pada posisinya) diserahkan seluruhnya kepada anak-anaknya,
     dibagi **2:1** (laki-laki : perempuan). Hasil: baris `pengganti_<posisi>` (dasar `khi-1991:pasal-185`);
     bila ada lebih dari satu entri untuk posisi sama, `pengganti_<posisi>_2`, dst.
  3. **Batas ayat (2):** bagian grup pengganti tidak melebihi bagian per orang ahli waris sederajat yang **hidup**
     (anak laki/perempuan satu kelompok; saudara laki/perempuan sekelompok kandung atau seayah). Bila terlampaui
     (mis. anak laki wafat, hanya anak perempuan hidup), grup dipotong ke batas itu dan selisihnya diberikan kepada
     ahli waris sederajat yang hidup, sebanding bagiannya (tafsir; KHI tidak mengatur ke mana selisih pergi).
     Diberi `catatan` khusus bila batas ini bekerja.
- Pengganti tidak berlaku bagi yang terhalang Pasal 173 (pembunuh/murtad/fitnah); mesin tidak menilai Pasal 173,
  pemeriksaan itu ada di luar mesin.

## (d) 'Radd tidak ke suami/istri -- tafsir PA, perlu verifikasi ahli
- Pasal 193 mengatur 'aul dan radd tetapi tidak menyebut pengecualian pasangan. Mesin mengikuti praktik PA /
  jumhur: sisa harta (tanpa asabah) dikembalikan (radd) hanya kepada dzawil furudh nasab, **tidak** kepada
  suami/istri (`normalisasi.PASANGAN`). Pendapat sebagian ulama dan khalifah Utsman memberi radd kepada pasangan
  atau menyerahkannya ke Baitul Mal; mesin tidak memakainya. Bila hanya pasangan yang ada, tidak ada radd.
- Berbeda dengan (a)-(c), (d) saat ini tidak menyalakan `perlu_verifikasi_ahli` secara otomatis (tafsir dari
  Task 6, perilaku sudah ada sebelum berkas ini).

## Ringkasan penanda otomatis
| Kasus | `perlu_verifikasi_ahli` |
|---|---|
| nenek menerima bagian | ya |
| kakek menerima bagian (ayah tiada) | ya |
| ada pengganti | ya |
| ahli waris inti saja (termasuk radd) | tidak |
