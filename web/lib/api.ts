export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Sumber = {
  chunk_id: string; citation: string; text: string; text_ar: string | null;
  source_type: string; status: string | null; derajat: string | null;
  source_url: string; license: string;
};
export type Langkah = {
  urutan: number; judul: string; uraian: string; dokumen: string[]; sitasi: string[];
};
export type NavigatorResponse = {
  status: "ok" | "ditolak" | "di_luar_cakupan";
  jenis_perkara: string | null; pengadilan: string | null; ringkasan: string;
  langkah: Langkah[]; peringatan: string[]; sumber: Sumber[];
  disclaimer: string; mode: "llm" | "retrieval_only";
};
export type AskResponse = {
  status: "ok" | "ditolak" | "di_luar_cakupan"; jawaban: string; sitasi: string[];
  peringatan: string[]; sumber: Sumber[]; disclaimer: string; mode: "llm" | "retrieval_only";
};
export type AhliWaris = {
  suami: number; istri: number; anak_laki: number; anak_perempuan: number;
  ayah: number; ibu: number; kakek: number; nenek: number;
  saudara_laki_kandung: number; saudara_perempuan_kandung: number;
  saudara_laki_seayah: number; saudara_perempuan_seayah: number; saudara_seibu: number;
};
export type FaraidRequest = {
  harta_bersih: number; pewaris_jenis_kelamin: "L" | "P"; ahli_waris: AhliWaris;
  pengganti: []; di_luar_cakupan: [];
};
export type BagianWaris = {
  ahli_waris: string; jumlah: number; bagian_pembilang: number; bagian_penyebut: number;
  nominal: number; dasar: string[]; keterangan: string;
};
export type FaraidResult = {
  status: "ok" | "di_luar_cakupan"; bagian: BagianWaris[]; asal_masalah: number | null;
  aul_terjadi: boolean; radd_terjadi: boolean; perlu_verifikasi_ahli: boolean;
  sisa_pembulatan: number; catatan: string[]; disclaimer: string; penjelasan: string | null;
};

async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${API_URL}${path}`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`API ${path} gagal (${r.status})`);
  return r.json() as Promise<T>;
}
export const postNavigator = (pertanyaan: string) =>
  post<NavigatorResponse>("/navigator", { pertanyaan });
export const postAsk = (pertanyaan: string) => post<AskResponse>("/ask", { pertanyaan });
export const postFaraid = (req: FaraidRequest) => post<FaraidResult>("/faraid", req);
