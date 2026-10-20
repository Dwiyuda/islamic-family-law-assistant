# Sampel Gold Set untuk Diperiksa Pemilik

Sepuluh pertanyaan dalam domain, dipilih acak (`random.Random(11)`) dari `eval/gold.jsonl`.
Gold set disusun oleh agen AI dengan membaca pasal, bukan dengan mesin pencari, lalu diperiksa reviewer AI.
Belum ada orang dengan latar hukum yang memeriksanya.

Untuk tiap pertanyaan, tolong cek:

1. Apakah pertanyaannya wajar ditanyakan orang awam?
2. Apakah setiap pasal di **Label** benar-benar menjawab pertanyaan itu?
3. Apakah ada pasal lain yang lebih tepat tapi belum dicantumkan?

Tulis catatan langsung di bawah tiap pertanyaan (bagian **Catatan pemilik**), lalu beri tahu Claude.
Kolom *Hasil sistem* hanya informasi: 5 hasil teratas metode `hybrid_rerank` saat evaluasi.

## cerai-024 (perceraian)

**Pertanyaan:** Sebulan lalu suami menjatuhkan talak satu, sekarang dia menyesal dan ingin kembali. Bagaimana caranya supaya rujuknya sah?

**Alasan label (dari penyusun):** KHI 163: rujuk dalam masa idah; KHI 167: tata cara rujuk di PPN; KHI 150: hak rujuk bekas suami; QS 2:228: suami lebih berhak kembali dalam masa itu; HadeethEnc 58149: persaksian rujuk

**Label:**

- `khi-1991:pasal-163` · **KHI Pasal 163** · status: berlaku
  > Pasal 163 ( l) Seorang suami dapat merujuk isterinya yang dalam masa iddah. (2) Rujuk dapat dilakukan dalam hal-hal : a. putusnya perkawinan karena talak, kecuali talak yang telah jatuh tiga kali talak yang dijatuhkan qobla al dukhul; b. putusnya perkawinan berdasarkan putusan pengadilan dengan alasan atau alasan-alasa…

- `khi-1991:pasal-167` · **KHI Pasal 167** · status: berlaku
  > Pasal 167 (I) Suami yang hendak merujuk isterinya datang bersama-sama isterinya ke Pegawai Pencatat Nikah atau Pembantu Pegawai Pencatat Nikah yang mewilayahi tempat tinggal suami isteri dengan membawa penetapan tentang terjadinya talak dan surat keterangan lain yang diperlukan. (2) Rujuk dilakukan dengan persetujuan i…

- `khi-1991:pasal-150` · **KHI Pasal 150** · status: berlaku
  > Pasal 150 Bekas suami berhak melakukan ruju' kepada bekas istrinya yang masih dalam iddah.

- `quran:2:228` · **QS Al-Baqarah [2]: 228**
  > Dan para istri yang diceraikan (wajib) menahan diri mereka (menunggu) tiga kali quru`. Mereka tidak boleh menyembunyikan apa yang diciptakan Allah dalam rahim mereka, jika mereka beriman kepada Allah dan hari akhir. Dan para suami mereka lebih berhak kembali kepada mereka dalam (masa) itu, jika mereka menghendaki perba…

- `hadith:hadeethenc:58149` · **Diriwayatkan oleh Ibnu Mājah - Diriwayatkan oleh Abu Daud (HadeethEnc no. 58149)**
  > Dari 'Imrān bin Ḥuṣain bahwasannya dia ditanya tentang seseorang yang menceraikan istrinya lalu menyetubuhinya tanpa memberi kesaksian atas perceraiannya dan rujuknya. Lantas ia menjawab, "Engkau telah menjatuhkan talak yang tak sesuai sunah dan melakukan rujuk yang tak sesuai sunah. Bersaksilah atas talak dan rujuknya…

*Hasil sistem (top 5, ✓ = cocok label):* hadith:hadeethenc:8286, khi-1991:pasal-167 ✓, hadith:hadeethenc:58149 ✓, khi-1991:pasal-169, hadith:hadeethenc:58078

**Catatan pemilik:** 

---

## cerai-025 (perceraian)

**Pertanyaan:** Mantan suami mau rujuk, tapi saya sudah tidak mau lagi hidup dengannya. Apakah saya boleh menolak?

**Alasan label (dari penyusun):** KHI 164: istri berhak mengajukan keberatan atas rujuk; KHI 165: rujuk tanpa sepengetahuan istri dapat dinyatakan tidak sah

**Label:**

- `khi-1991:pasal-164` · **KHI Pasal 164** · status: berlaku
  > Pasal 164 Seorang wan ita dalam iddah talak raj' i berhak mengajukan keberatan atas kehendak rujuk dari bekas suaminya dihadapan Pegawai Pencatat Nikah disaksikan dua orang saksi

- `khi-1991:pasal-165` · **KHI Pasal 165** · status: berlaku
  > Pasal 165 Rujuk yang dilakukan tanpa sepengetahuan bekas isteri, dapat dinyatakan tidak sah dengan putusan Pengadilan Agama.

*Hasil sistem (top 5, ✓ = cocok label):* hadith:hadeethenc:58078, hadith:hadeethenc:6089, khi-1991:pasal-164 ✓, khi-1991:pasal-167, khi-1991:pasal-119

**Catatan pemilik:** 

---

## peradilan-001 (peradilan)

**Pertanyaan:** Sengketa pembagian warisan di keluarga kami yang semuanya muslim, harus dibawa ke pengadilan negeri atau pengadilan agama?

**Alasan label (dari penyusun):** UU 7/1989 Pasal 49 sebagaimana diubah UU 3/2006: kewenangan PA di bidang waris; UU 7/1989 Pasal 49 asli ayat (3) merinci lingkup kewarisan; KHI 188: gugatan pembagian warisan melalui PA

**Label:**

- `uu-3-2006:pasal-49` · **UU 7/1989 Pasal 49 sebagaimana diubah UU 3/2006** · status: berlaku
  > Pasal 49 Pengadilan agama bertugas dan berwenang memeriksa, memutus, dan menyelesaikan perkara di tingkat pertama antara orang-orang yang beragama Islam di bidang: a. perkawinan; b. waris; c. wasiat; d. hibah; e. wakaf; f. zakat; g. infaq ; h. shadaqah; dan i. ekonomi syari'ah.

- `uu-7-1989:pasal-49` · **UU 7/1989 Pasal 49** · status: diubah
  > Pasal 49 (1) Pengadilan Agama bertugas dan berwenang memeriksa, memutus, dan menyelesaikan perkara-perkara di tingkat pertama antara orang-orang yang beragama Islam di bidang: a. perkawinan; b. kewarisan, wasiat, dan hibah, yang dilakukan berdasarkan hukum Islam; c. wakaf dan shadaqah. (2) Bidang perkawinan sebagaimana…

- `khi-1991:pasal-188` · **KHI Pasal 188** · status: berlaku
  > Pasal 188 Para ahli waris baik secara bersama-sama atau perseorangan dapat mengajukan permintaan kepada ahli waris yang lain untuk melakukan pembagian harta warisan. Bila ada diantara ahli waris yang tidak menyetujui permintaan itu, maka yang bersangkutan dapat mengajukan gugatan melalui Pengadilan Agama untuk dilakuka…

*Hasil sistem (top 5, ✓ = cocok label):* uu-7-1989:pasal-49 ✓, uu-3-2006:pasal-50, khi-1991:pasal-188 ✓, uu-3-2006:pasal-49 ✓, uu-50-2009:pasal-1

**Catatan pemilik:** 

---

## peradilan-007 (peradilan)

**Pertanyaan:** Berapa lama proses mediasi di pengadilan agama? Dan bisakah mediasinya dilakukan lewat video call karena saya tinggal di luar kota?

**Alasan label (dari penyusun):** PERMA 1/2016 Pasal 24: 30 hari, dapat diperpanjang 30 hari; Pasal 5 ayat (3) & Pasal 6 ayat (2): mediasi melalui komunikasi audio visual jarak jauh

**Label:**

- `perma-1-2016:pasal-24` · **PERMA 1/2016 Pasal 24** · status: berlaku
  > Pasal 24 (1) Dalam waktu paling lama 5 (lima) hari terhitung sejak penetapan sebagaimana dimaksud dalam Pasal 20 ayat (5), Para Pihak dapat menyerahkan Resume Perkara kepada pihak lain dan Mediator. (2) Proses Mediasi berlangsung paling lama 30 (tiga puluh) hari terhitung sejak penetapan perintah melakukan Mediasi. (3)…

- `perma-1-2016:pasal-5` · **PERMA 1/2016 Pasal 5** · status: berlaku
  > Pasal 5 (1) Proses Mediasi pada dasarnya bersifat tertutup kecuali Para Pihak menghendaki lain. (2) Penyampaian laporan Mediator mengenai pihak yang tidak beriktikad baik dan ketidakberhasilan proses Mediasi kepada Hakim Pemeriksa Perkara bukan merupakan pelanggaran terhadap sifat tertutup Mediasi. (3) Pertemuan Medias…

- `perma-1-2016:pasal-6` · **PERMA 1/2016 Pasal 6** · status: berlaku
  > Pasal 6 (1) Para Pihak wajib menghadiri secara langsung pertemuan Mediasi dengan atau tanpa didampingi oleh kuasa hukum. (2) Kehadiran Para Pihak melalui komunikasi audio visual jarak jauh sebagaimana dimaksud dalam Pasal 5 ayat (3) dianggap sebagai kehadiran langsung. (3) Ketidakhadiran Para Pihak secara langsung dala…

*Hasil sistem (top 5, ✓ = cocok label):* perma-1-2016:pasal-3, perma-1-2016:pasal-2, perma-1-2016:pasal-6 ✓, perma-1-2016:pasal-1, perma-1-2016:pasal-11

**Catatan pemilik:** 

---

## peradilan-009 (peradilan)

**Pertanyaan:** Saya tidak punya uang untuk membayar biaya perkara cerai. Apakah ada cara berperkara gratis?

**Alasan label (dari penyusun):** UU 7/1989 Pasal 60B & 60C sebagaimana diubah UU 50/2009: negara menanggung biaya bagi yang tidak mampu (SKTM), posbakum; prosedur: berperkara prodeo

**Label:**

- `uu-50-2009:pasal-60b` · **UU 7/1989 Pasal 60B sebagaimana diubah UU 50/2009** · status: berlaku
  > Pasal 60B (1) Setiap orang yang tersangkut perkara berhak memperoleh bantuan hukum. (2) Negara menanggung biaya perkara bagi pencari keadilan yang tidak mampu. (3) Pihak yang tidak mampu sebagaimana dimaksud pada ayat (2) harus melampirkan surat keterangan tidak mampu dari kelurahan tempat domisili yang bersangkutan.

- `uu-50-2009:pasal-60c` · **UU 7/1989 Pasal 60C sebagaimana diubah UU 50/2009** · status: berlaku
  > Pasal 60C (1) Pada setiap pengadilan agama dibentuk pos bantuan hukum untuk pencari keadilan yang tidak mampu dalam memperoleh bantuan hukum. (2) Bantuan hukum sebagaimana dimaksud pada ayat (1) diberikan secara cuma-cuma kepada semua tingkat peradilan sampai putusan terhadap perkara tersebut memperoleh kekuatan hukum …

- `prosedur-cerai-gugat:langkah-5` · **Prosedur Cerai Gugat langkah 5**
  > Membayar biaya perkara (pasal 121 ayat (4) HIR, 145 ayat (4) Rbg jo pasal 89 UU no 7 tahun 1989 yang telah diubah oleh Undang-Undang Nomor 3 Tahun 2006. Bagi yang tidak mampu, dapat berperkara secara cuma-cuma/prodeo (pasal 237 HIR, 273 Rbg).

- `prosedur-cerai-talak:langkah-6` · **Prosedur Cerai Talak langkah 6**
  > Membayar biaya perkara (pasal 121 ayat (4) HIR, 145 ayat (4) Rbg jo pasal 89 UU no 7 tahun 1989). Bagi yang tidak mampu, dapat berperkara secara cuma-cuma/prodeo (pasal 237 HIR, 273 Rbg).

*Hasil sistem (top 5, ✓ = cocok label):* prosedur-cerai-gugat:langkah-5 ✓, prosedur-cerai-talak:langkah-6 ✓, uu-50-2009:pasal-60b ✓, perma-1-2016:pasal-23, prosedur-waris:bagian-1

**Catatan pemilik:** 

---

## peradilan-011 (peradilan)

**Pertanyaan:** Saya mau mengurus penetapan ahli waris di pengadilan agama supaya bisa mencairkan tabungan almarhum ayah. Dokumen apa saja yang perlu disiapkan?

**Alasan label (dari penyusun):** Prosedur waris bagian 1-2: syarat permohonan penetapan ahli waris

**Label:**

- `prosedur-waris:bagian-1` · **Prosedur Waris bagian 1**
  > SYARAT PENGAJUAN PERMOHONAN PENETAPAN AHLI WARIS Membuat Surat Permohonan (disertai softcopy berformat file .rtf jika dibuat diluar POSBAKUM PA Wonosobo). Fotokopi KTP Para Pemohon 1 lembar Fotokopi Kartu Keluarga Para Pemohon lembar Fotokopi Akte Lahir Para Pemohon 1 lembar Fotokopi Buku Nikah / Akta Cerai Pewaris lem…

- `prosedur-waris:bagian-2` · **Prosedur Waris bagian 2**
  > Catatan : Persyaratan asli dibawa saat persidangan. Persyaratan alat bukti dileges (diberi materai Rp. 10.000,- dan di cap POS). Persyaratan ini merupakan persyaratan awal, untuk selanjutnya mengikuti petunjuk/perintah Majelis Hakim di dalam persidangan. Semua potokopi dokumen permohonan menggunakan kertas A4.

*Hasil sistem (top 5, ✓ = cocok label):* prosedur-waris:bagian-1 ✓, uu-7-1989:pasal-49, prosedur-waris:bagian-2 ✓, khi-1991:pasal-188, khi-1991:pasal-171

**Catatan pemilik:** 

---

## peradilan-015 (peradilan)

**Pertanyaan:** Bisakah tuntutan hak asuh anak dan pembagian gono-gini diajukan sekaligus dengan gugatan cerai, atau harus terpisah?

**Alasan label (dari penyusun):** UU 7/1989 Pasal 86 ayat (1) & Pasal 66 ayat (5), prosedur langkah 4/5: dapat diajukan bersama atau sesudah putusan; PERMA 1/2016 Pasal 31: mediasi tuntutan kumulasi dalam perkara cerai

**Label:**

- `uu-7-1989:pasal-86` · **UU 7/1989 Pasal 86** · status: berlaku
  > Pasal 86 (1) Gugatan soal penguasaan anak, nafkah anak, nafkah istri, dan harta bersama suami istri dapat diajukan bersama-sama dengan gugatan perceraian ataupun sesudah putusan perceraian memperoleh kekuatan hukum tetap. (2) Jika ada tuntutan pihak ketiga, maka Pengadilan menunda terlebih dahulu perkara harta bersama …

- `uu-7-1989:pasal-66` · **UU 7/1989 Pasal 66** · status: berlaku
  > Pasal 66 (1) Seorang suami yang beragama Islam yang akan menceraikan istrinya mengajukan permohonan kepada Pengadilan untuk mengadakan sidang guna menyaksikan ikrar talak. (2) Permohonan sebagaimana yang dimaksud dalam ayat (1) diajukan kepada Pengadilan yang daerah hukumnya meliputi tempat kediaman termohon, kecuali a…

- `prosedur-cerai-gugat:langkah-4` · **Prosedur Cerai Gugat langkah 4**
  > Gugatan soal penguasaan anak, nafkah anak, nafkah istri dan harta bersama, dapat diajukan bersama-sama dengan gugatan atau sesudah putusan perceraian memperoleh kekuatan hukum tetap (pasal 66 ayat (5) UU no 7 tahun 1989 yang telah diubah oleh Undang-Undang Nomor 3 Tahun 2006).

- `prosedur-cerai-talak:langkah-5` · **Prosedur Cerai Talak langkah 5**
  > Permohonan soal penguasaan anak, nafkah anak, nafkah istri dan harta bersama, dapat diajukan bersama-sama dengan permohonan cerai talak atau sesudah ikrar talak diucapkan (pasal 66 ayat (5) UU no 7 tahun 1989 yang telah diubah oleh Undang-Undang Nomor 3 Tahun 2006).

- `perma-1-2016:pasal-31` · **PERMA 1/2016 Pasal 31** · status: berlaku
  > Pasal 31 (1) Untuk Mediasi perkara perceraian dalam lingkungan peradilan agama yang tuntutan perceraian dikumulasikan dengan tuntutan lainnya, jika Para Pihak tidak mencapai kesepakatan untuk hidup rukun kembali, Mediasi dilanjutkan dengan tuntutan lainnya. (2) Dalam hal Para Pihak mencapai kesepakatan atas tuntutan la…

*Hasil sistem (top 5, ✓ = cocok label):* uu-7-1989:pasal-86 ✓, prosedur-cerai-gugat:langkah-4 ✓, uu-7-1989:pasal-66 ✓, prosedur-cerai-talak:langkah-5 ✓, perma-1-2016:pasal-31 ✓

**Catatan pemilik:** 

---

## waris-023 (kewarisan)

**Pertanyaan:** Orang tua saya sudah menghibahkan sebidang tanah kepada saya, tapi sekarang ingin memintanya kembali. Apakah boleh?

**Alasan label (dari penyusun):** KHI 212: hibah tidak dapat ditarik kecuali hibah orang tua kepada anak

**Label:**

- `khi-1991:pasal-212` · **KHI Pasal 212** · status: berlaku
  > Pasal 212 Hibah tidak dapat ditarik kembali, kecuali hibah orang tua kepada anaknya.

*Hasil sistem (top 5, ✓ = cocok label):* khi-1991:pasal-212 ✓, hadith:hadeethenc:6035, khi-1991:pasal-211, quran:4:19, khi-1991:pasal-210

**Catatan pemilik:** 

---

## waris-025 (kewarisan)

**Pertanyaan:** Suami meninggal. Rumah kami dibeli berdua selama menikah. Apakah seluruh rumah itu masuk harta warisan yang dibagi ke ahli waris?

**Alasan label (dari penyusun):** KHI 96 ayat (1): separuh harta bersama menjadi hak pasangan yang hidup lebih lama; KHI 171 huruf e: harta waris = harta bawaan + bagian dari harta bersama

**Label:**

- `khi-1991:pasal-96` · **KHI Pasal 96** · status: berlaku
  > Pasal 96 1. Apabila terjadi cerai mati, maka separuh harta bersama menjadi hak pasangan yang hidup lebih lama. 2. Pembangian harta bersama bagi seorang suami atau isteri yang isteri atau suaminya hutang harus ditangguhkan sampai adanya kepastian matinya yang hakiki atau matinya secara hukum atas dasar putusan Pengadila…

- `khi-1991:pasal-171` · **KHI Pasal 171** · status: berlaku
  > Pasal 171 Yang dimaksud dengan: a. Hukum kewarisan adalah hukum yang mengatur tentang pemindahan hak pemilikan harta peninggalan (tirkah) pewaris, menentukan siapa-siapa yang berhak menjadi ahli waris dan berapa bagiannya masing-masing. b. Pewaris adalah orang yang pada saat meninggalnya atau yang dinyatakan meninggal …

*Hasil sistem (top 5, ✓ = cocok label):* hadith:hadeethenc:10986, khi-1991:pasal-190, khi-1991:pasal-187, hadith:hadeethenc:5887, quran:4:12

**Catatan pemilik:** 

---

## waris-026 (kewarisan)

**Pertanyaan:** Almarhum suami saya punya dua istri. Bagaimana pembagian hartanya untuk masing-masing istri?

**Alasan label (dari penyusun):** KHI 190: tiap istri berhak atas gono-gini rumah tangganya; KHI 180: bagian janda; KHI 94: harta bersama tiap perkawinan terpisah

**Label:**

- `khi-1991:pasal-190` · **KHI Pasal 190** · status: berlaku
  > Pasal 190 Bagi pewaris yang beristeri lebih dari seorang, maka masing-masing isteri berhak mendapat bagian atas gono-gini dari rumah tangga dengan suaminya, sedangkan keseluruhan bagian pewaris adalah menjadi hak para ahli warisnya.

- `khi-1991:pasal-180` · **KHI Pasal 180** · status: berlaku
  > Pasal 180 Janda mendapat seperempat bagian bila pewaris tidak meninggalkan anak, dan bila pewaris meninggalkan anak maka janda mendapat seperdelapan bagian.

- `khi-1991:pasal-94` · **KHI Pasal 94** · status: berlaku
  > Pasal 94 I. Harta bersama dari perkawinan seorang suami yang mempunyai isteri lebih dari seorang, masing-masing terpisah dan berdiri sendiri. 2. Pemilikan harta bersama dari perkawinan seorang suami yang mempunyai isteri lebih dari seorang sebagaimana tersebut ayat ( 1 ), dihitung pada saat berlangsungnya akad perkawin…

*Hasil sistem (top 5, ✓ = cocok label):* quran:4:12, khi-1991:pasal-94 ✓, khi-1991:pasal-190 ✓, khi-1991:pasal-82, khi-1991:pasal-87

**Catatan pemilik:** 

---
