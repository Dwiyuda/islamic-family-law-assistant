"use client";

import { useState } from "react";
import { postAsk, type AskResponse } from "@/lib/api";
import { Loading } from "@/components/Loading";
import { Disclaimer } from "@/components/Disclaimer";
import { Sumber } from "@/components/Sumber";
import { ModeTag } from "@/components/ModeTag";

export default function Page() {
  const [pertanyaan, setPertanyaan] = useState("");
  const [hasil, setHasil] = useState<AskResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setHasil(null);
    try {
      setHasil(await postAsk(pertanyaan.trim()));
    } catch {
      setError("Tidak bisa terhubung ke layanan. Pastikan server berjalan, lalu coba lagi.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl">Tanya jawab</h2>
        <p className="lead mt-1">
          Ajukan pertanyaan seputar perkawinan, perceraian, atau kewarisan. Jawaban selalu
          menyertakan pasal atau dalil rujukannya.
        </p>
      </div>

      <form onSubmit={submit} className="card space-y-3 p-5">
        <label htmlFor="ask-q" className="field-label">
          Pertanyaan Anda
        </label>
        <textarea
          id="ask-q"
          value={pertanyaan}
          onChange={(e) => setPertanyaan(e.target.value)}
          rows={3}
          required
          placeholder="Contoh: Berapa bagian warisan untuk anak perempuan tunggal?"
          className="control"
        />
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs text-muted">Jawaban butuh ~45 detik (model berjalan lokal).</p>
          <button type="submit" disabled={loading || !pertanyaan.trim()} className="btn">
            Tanya
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
          <p>{hasil.jawaban}</p>
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
            <p className="whitespace-pre-wrap text-ink-soft">{hasil.jawaban}</p>
            {hasil.sitasi.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {hasil.sitasi.map((s, i) => (
                  <span key={i} className="chip">
                    {s}
                  </span>
                ))}
              </div>
            )}
            <ModeTag mode={hasil.mode} />
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
