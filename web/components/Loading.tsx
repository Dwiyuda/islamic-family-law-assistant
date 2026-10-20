export function Loading() {
  return (
    <div className="card flex items-center gap-3 p-4 text-ink-soft">
      <span
        aria-hidden
        className="h-5 w-5 shrink-0 animate-spin rounded-full border-2 border-primary-soft border-t-primary"
      />
      <span className="text-sm">
        Sedang menyusun jawaban… Ini bisa memakan waktu hingga <b>sekitar 45 detik</b>, karena
        model berjalan di komputer lokal.
      </span>
    </div>
  );
}
