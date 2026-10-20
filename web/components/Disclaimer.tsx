export function Disclaimer({ teks }: { teks: string }) {
  return (
    <div className="mt-6 flex items-start gap-2.5 rounded-xl border border-line bg-paper px-4 py-3 text-sm text-muted">
      <svg
        aria-hidden
        viewBox="0 0 20 20"
        className="mt-0.5 h-4 w-4 shrink-0 text-primary"
        fill="currentColor"
      >
        <path
          fillRule="evenodd"
          d="M10 18a8 8 0 100-16 8 8 0 000 16zM9 9a1 1 0 112 0v4a1 1 0 11-2 0V9zm1-4.5a1 1 0 100 2 1 1 0 000-2z"
          clipRule="evenodd"
        />
      </svg>
      <p>{teks}</p>
    </div>
  );
}
