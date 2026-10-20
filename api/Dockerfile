FROM python:3.12-slim
# WORKDIR /app/api (bukan /app): kode memakai REPO_ROOT = parents[3] dari app/retrieval/corpus.py.
# Di host itu <repo>/api/app/... → repo root. Agar REPO_ROOT di container = /app (tempat ./data
# di-mount), app harus berada di /app/api/app, jadi WORKDIR = /app/api dan `data` ada di /app/data.
WORKDIR /app/api
ENV HF_HUB_OFFLINE=1 HF_HOME=/models PYTHONUNBUFFERED=1
COPY pyproject.toml ./
# ponytail: pasang torch CPU (~190MB) dari index CPU dulu — default PyPI menarik wheel CUDA
# (~2.5GB) yang bikin build lama & gampang timeout; proyek ini CPU-only. --timeout/--retries
# tahan koneksi lambat. Sesudah ini FlagEmbedding (models) pakai torch yang sudah terpasang.
RUN pip install --no-cache-dir --timeout 180 --retries 5 \
      torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir --timeout 180 --retries 5 ".[retrieval,models,api]"
COPY app ./app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
