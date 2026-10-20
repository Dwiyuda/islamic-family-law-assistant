"""Runtime settings shared by retrieval, evaluation and (Fase 3) generation."""

import os

# ponytail: this laptop's GPU overheats under sustained load (see thermal.py); default to CPU
# everywhere and require an explicit opt-in (--device cuda / IFLA_DEVICE=cuda) for GPU runs.
DEFAULT_DEVICE = os.environ.get("IFLA_DEVICE", "cpu")

RRF_K = 60  # spec 5: reciprocal rank fusion constant
RERANK_CANDIDATES = 30  # fused candidates the reranker scores
TOP_K = 8  # chunks handed to generation

# Calibrated in Fase 2 on 80 in-domain + 20 out-of-domain gold questions (balanced accuracy);
# see eval/results/refusal.md. Re-run `python -m app.evaluation.refusal` after a new eval.
REFUSAL_THRESHOLD = 0.0333


def load_env_file(path) -> None:
    """Minimal `.env` reader (KEY=VALUE lines, `#` comments); real environment variables win.

    ponytail: no python-dotenv; add it if `.env` ever needs quoting/escapes/multiline values.
    """
    from pathlib import Path

    path = Path(path)
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def cors_origins() -> list[str]:
    """Origin yang diizinkan untuk CORS (spec Fase 5). Default dev Next.js."""
    raw = os.environ.get("CORS_ORIGINS", "http://localhost:3000")
    return [o.strip() for o in raw.split(",") if o.strip()]
