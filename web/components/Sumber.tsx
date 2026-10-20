import { type Sumber as SumberType } from "@/lib/api";
import { safeHref } from "@/lib/url";

export function Sumber({ sumber }: { sumber: SumberType[] }) {
  if (sumber.length === 0) return null;
  return (
    <section>
      <h3 className="mb-3 text-lg">Sumber &amp; dasar hukum</h3>
      <ul className="space-y-3">
        {sumber.map((s) => {
          const href = safeHref(s.source_url);
          return (
            <li key={s.chunk_id} className="card p-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-semibold text-ink">{s.citation}</span>
                {s.derajat && <span className="tag">{s.derajat}</span>}
              </div>
              <p className="mt-1.5 text-sm text-ink-soft">
                {s.text.slice(0, 280)}
                {s.text.length > 280 ? "…" : ""}
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
                {href ? (
                  <a href={href} target="_blank" rel="noreferrer" className="underline">
                    Buka sumber
                  </a>
                ) : null}
                <span>{s.license}</span>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
