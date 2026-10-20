"use client";

import { useState } from "react";
import { postFaraid, type AhliWaris, type FaraidResult } from "@/lib/api";
import { Loading } from "@/components/Loading";
import { Disclaimer } from "@/components/Disclaimer";

type Field = { key: keyof AhliWaris; label: string; min: number; max?: number };

const GROUPS: { title: string; fields: Field[] }[] = [
  {
    title: "Pasangan & anak",
    fields: [
      { key: "suami", label: "Suami", min: 0, max: 1 },
      { key: "istri", label: "Istri", min: 0, max: 4 },
      { key: "anak_laki", label: "Anak laki-laki", min: 0 },
      { key: "anak_perempuan", label: "Anak perempuan", min: 0 },
    ],
  },
  {
    title: "Orang tua & kakek-nenek",
    fields: [
      { key: "ayah", label: "Ayah", min: 0, max: 1 },
      { key: "ibu", label: "Ibu", min: 0, max: 1 },
      { key: "kakek", label: "Kakek (dari ayah)", min: 0, max: 1 },
      { key: "nenek", label: "Nenek", min: 0, max: 2 },
    ],
  },
  {
    title: "Saudara",
    fields: [
      { key: "saudara_laki_kandung", label: "Saudara laki-laki kandung", min: 0 },
      { key: "saudara_perempuan_kandung", label: "Saudara perempuan kandung", min: 0 },
      { key: "saudara_laki_seayah", label: "Saudara laki-laki seayah", min: 0 },
      { key: "saudara_perempuan_seayah", label: "Saudara perempuan seayah", min: 0 },
      { key: "saudara_seibu", label: "Saudara seibu", min: 0 },
    ],
  },
];

const NAMA: Record<string, string> = Object.fromEntries(
  GROUPS.flatMap((g) => g.fields.map((f) => [f.key, f.label])),
);
const namaAhli = (k: string) =>
  NAMA[k] ?? k.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());

const EMPTY: AhliWaris = {
  suami: 0, istri: 0, anak_laki: 0, anak_perempuan: 0, ayah: 0, ibu: 0, kakek: 0, nenek: 0,
  saudara_laki_kandung: 0, saudara_perempuan_kandung: 0, saudara_laki_seayah: 0,
  saudara_perempuan_seayah: 0, saudara_seibu: 0,
};

const rupiah = (n: number) =>
  new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n);

export default function WarisPage() {
  const [harta, setHarta] = useState("");
  const [jk, setJk] = useState<"L" | "P" | "">("");
  const [aw, setAw] = useState<AhliWaris>(EMPTY);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasil, setHasil] = useState<FaraidResult | null>(null);

  async function hitung(e: React.FormEvent) {
    e.preventDefault();
    if (!jk) return;
    setLoading(true);
    setError(null);
    setHasil(null);
    try {
      setHasil(
        await postFaraid({
          harta_bersih: Math.round(Number(harta) || 0),
          pewaris_jenis_kelamin: jk,
          ahli_waris: aw,
          pengganti: [],
          di_luar_cakupan: [],
        }),
      );
    } catch {
      setError("Tidak bisa terhubung ke layanan. Pastikan server berjalan, lalu coba lagi.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl">Kalkulator waris (faraid)</h2>
        <p className="lead mt-1">
          Masukkan harta bersih dan jumlah ahli waris yang masih hidup. Bagian dihitung dengan
          mesin aturan berdasarkan Kompilasi Hukum Islam — bukan perkiraan.
        </p>
      </div>

      <form onSubmit={hitung} className="card space-y-6 p-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="harta" className="field-label">Harta bersih (Rp)</label>
            <input
              id="harta" type="number" inputMode="numeric" min={0} step={1} required
              value={harta} onChange={(e) => setHarta(e.target.value)}
              placeholder="contoh: 120000000" className="control"
            />
          </div>
          <div>
            <label htmlFor="jk" className="field-label">Jenis kelamin pewaris</label>
            <select id="jk" required value={jk} onChange={(e) => setJk(e.target.value as "L" | "P" | "")} className="control">
              <option value="">Pilih…</option>
              <option value="L">Laki-laki</option>
              <option value="P">Perempuan</option>
            </select>
          </div>
        </div>

        {GROUPS.map((g) => (
          <fieldset key={g.title} className="space-y-3">
            <legend className="text-xs font-semibold tracking-wide text-muted">{g.title}</legend>
            <div className="grid gap-3 sm:grid-cols-2">
              {g.fields.map((f) => (
                <div key={f.key} className="flex items-center justify-between gap-3">
                  <label htmlFor={f.key} className="text-sm text-ink-soft">{f.label}</label>
                  <input
                    id={f.key} type="number" min={f.min} max={f.max}
                    value={aw[f.key]}
                    onChange={(e) => setAw({ ...aw, [f.key]: Number(e.target.value) })}
                    className="control w-20 shrink-0 text-center"
                  />
                </div>
              ))}
            </div>
          </fieldset>
        ))}

        <button type="submit" disabled={loading} className="btn">Hitung bagian</button>
      </form>

      {loading && <Loading />}
      {error && <div className="notice" style={{ color: "var(--color-danger)" }}>{error}</div>}

      {hasil && (
        <div className="space-y-4">
          {hasil.perlu_verifikasi_ahli && (
            <div className="notice">
              <p className="font-semibold">Perlu diverifikasi ahli</p>
              <p className="mt-1 text-sm">
                Hasil ini memakai tafsir di luar teks literal KHI (mis. kakek, nenek, atau ahli
                waris pengganti). Mohon konsultasikan dengan ahli hukum atau fikih sebelum dipakai.
              </p>
            </div>
          )}

          {hasil.status === "di_luar_cakupan" ? (
            <div className="card p-5">
              <p className="text-ink-soft">Kasus ini berada di luar cakupan kalkulator.</p>
              {hasil.catatan.length > 0 && (
                <ul className="mt-2 list-disc space-y-0.5 pl-5 text-sm">
                  {hasil.catatan.map((c, i) => <li key={i}>{c}</li>)}
                </ul>
              )}
            </div>
          ) : (
            <>
              <div className="card overflow-hidden p-0">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="bg-paper text-xs text-muted">
                      <th className="px-4 py-2.5 font-semibold">Ahli waris</th>
                      <th className="px-4 py-2.5 text-center font-semibold">Jumlah</th>
                      <th className="px-4 py-2.5 text-center font-semibold">Bagian</th>
                      <th className="px-4 py-2.5 text-right font-semibold">Nominal</th>
                    </tr>
                  </thead>
                  <tbody>
                    {hasil.bagian.map((b, i) => (
                      <tr key={i} className="border-t border-line">
                        <td className="px-4 py-2.5">
                          <span className="font-medium text-ink">{namaAhli(b.ahli_waris)}</span>
                          {b.keterangan && <span className="block text-xs text-muted">{b.keterangan}</span>}
                        </td>
                        <td className="px-4 py-2.5 text-center">{b.jumlah}</td>
                        <td className="px-4 py-2.5 text-center tabular-nums">
                          {b.bagian_pembilang}/{b.bagian_penyebut}
                        </td>
                        <td className="px-4 py-2.5 text-right font-semibold text-ink tabular-nums">
                          {rupiah(b.nominal)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-line bg-paper px-4 py-2.5 text-xs text-muted">
                  <span>Asal masalah: <b className="text-ink-soft">{hasil.asal_masalah ?? "-"}</b></span>
                  {hasil.sisa_pembulatan > 0 && <span>Sisa pembulatan: {rupiah(hasil.sisa_pembulatan)}</span>}
                  {hasil.aul_terjadi && <span className="chip">ʿAul</span>}
                  {hasil.radd_terjadi && <span className="chip">Radd</span>}
                </div>
              </div>

              {hasil.penjelasan && (
                <div className="card p-5">
                  <p className="whitespace-pre-wrap text-ink-soft">{hasil.penjelasan}</p>
                </div>
              )}
            </>
          )}

          <Disclaimer teks={hasil.disclaimer} />
        </div>
      )}
    </div>
  );
}
