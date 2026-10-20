export function ModeTag({ mode }: { mode: "llm" | "retrieval_only" }) {
  return (
    <span className="tag">
      {mode === "llm" ? "Dirangkum dengan bantuan AI" : "Mode tanpa AI — hanya kutipan sumber"}
    </span>
  );
}
