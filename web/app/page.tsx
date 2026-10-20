"use client";

import { useState } from "react";
import { postNavigator, type NavigatorResponse } from "@/lib/api";
import { Loading } from "@/components/Loading";
import { Disclaimer } from "@/components/Disclaimer";
import { Sumber } from "@/components/Sumber";
import { ModeTag } from "@/components/ModeTag";

export default function Page() {
  const [pertanyaan, setPertanyaan] = useState("");
  const [hasil, setHasil] = useState<NavigatorResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setHasil(null);
    try {
      setHasil(await postNavigator(pertanyaan.trim()));
    } catch {
      setError("Tidak bisa terhubung ke layanan. Pastikan server berjalan, lalu coba lagi.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl">Navigator perkara</h2>
        <p className="lead mt-1">
          Ceritakan situasi Anda. Kami tunjukkan jenis perkara, pengadilan yang berwenang,
          dokumen yang disiapkan, dan langkahnya — beserta dasar hukumnya.
        </p>
      </div>

      <form onSubmit={submit} className="card space-y-3 p-5">
        <label htmlFor="nav-q" className="field-label">
          Ceritakan masalah Anda
        </label>
        <textarea
          id="nav-q"
          value={pertanyaan}
          onChange={(e) => setPertanyaan(e.target.value)}
          rows={4}
          required
          placeholder="Contoh: Suami saya melanggar taklik talak dan saya ingin mengajukan cerai."
          className="control"
        />
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs text-muted">Jawaban butuh ~45 detik (model berjalan lokal).</p>
          <button type="submit" disabled={loading || !pertanyaan.trim()} className="btn">
            Cari langkah
          </button>
        </div>
      </form>

      {loading && <Loading />}
      {error && (
        <div className="notice" style={{ color: "var(--color-danger)" }}>
          {error}
        </div>
      )}

      {hasil && hasil.status !== "ok" && (
        <div className="notice space-y-1">
          <p>{hasil.ringkasan}</p>
          {hasil.peringatan.map((p, i) => (
            <p key={i} className="text-sm">
              {p}
            </p>
          ))}
        </div>
      )}

      {hasil && hasil.status === "ok" && (
        <div className="space-y-5">
          <div className="card space-y-3 p-5">
            <div className="flex flex-wrap gap-3">
              {hasil.jenis_perkara && (
                <div>
                  <p className="text-xs font-semibold text-muted">Jenis perkara</p>
                  <p className="font-semibold text-ink">
                    {hasil.jenis_perkara.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase())}
                  </p>
                </div>
              )}
              {hasil.pengadilan && (
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-muted">Pengadilan</p>
                  <p className="font-semibold text-ink">{hasil.pengadilan}</p>
                </div>
              )}
            </div>
            {hasil.ringkasan && <p>{hasil.ringkasan}</p>}
            <ModeTag mode={hasil.mode} />
          </div>

          <div>
            <h3 className="mb-3 text-lg">Langkah yang perlu ditempuh</h3>
            <ol className="space-y-3">
              {[...hasil.langkah]
                .sort((a, b) => a.urutan - b.urutan)
                .map((l, idx) => (
                  <li key={idx} className="card p-5">
                    <div className="flex gap-3.5">
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary-soft text-sm font-semibold text-primary-strong">
                        {l.urutan}
                      </span>
                      <div className="min-w-0 flex-1 space-y-2">
                        <p className="font-semibold text-ink">{l.judul}</p>
                        <p className="text-ink-soft">{l.uraian}</p>
                        {l.dokumen.length > 0 && (
                          <div>
                            <p className="text-xs font-semibold text-muted">Dokumen</p>
                            <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm">
                              {l.dokumen.map((d, i) => (
                                <li key={i}>{d}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {l.sitasi.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 pt-1">
                            {l.sitasi.map((s, i) => (
                              <span key={i} className="chip">
                                {s}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </li>
                ))}
            </ol>
          </div>

          {hasil.peringatan.length > 0 && (
            <div className="notice">
              <p className="font-semibold">Perlu diperhatikan</p>
              <ul className="mt-1 list-disc space-y-0.5 pl-5">
                {hasil.peringatan.map((p, i) => (
                  <li key={i}>{p}</li>
                ))}
              </ul>
            </div>
          )}

          <Sumber sumber={hasil.sumber} />
          <Disclaimer teks={hasil.disclaimer} />
        </div>
      )}
    </div>
  );
}
