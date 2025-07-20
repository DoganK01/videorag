# VideoRAG/Dockerfile
# Bu, ortam değişkenlerinin her aşamada doğru şekilde tanımlandığı,
# 'src/app' yapısıyla uyumlu, son ve en sağlam versiyondur.

ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim-bullseye AS base

# --- Ortam Değişkenleri (Düzeltilmiş Bölüm) ---
# Değişkenleri iki ayrı adımda tanımlayarak "tanımsız değişken" hatasını çözüyoruz.

# 1. Temel, bağımsız değişkenleri tanımla.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VENV_PATH=/opt/venv

# 2. Önceki adımda tanımlanan VENV_PATH'i kullanarak PATH'i güncelle.
ENV PATH="${VENV_PATH}/bin:${PATH}"
# ---------------------------------------------

WORKDIR /app

# Gerekli sistem bağımlılıklarını ve uv'yi tek bir RUN katmanında kur.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ffmpeg \
    build-essential \
    libsm6 \
    libxext6 \
    dos2unix \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir uv


# ===== AŞAMA: builder =====
# Bu aşama, tüm bağımlılıkları ve projeyi kurar.
FROM base AS builder

# Sanal ortamı oluştur
RUN python3 -m venv ${VENV_PATH}

# Önce build için gerekli tüm dosyaları kopyala. Bu, `README.md` hatasını önler.
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src
COPY ImageBind/ ./ImageBind

# Hem harici paketleri hem de kendi projenizi sanal ortama kur.
RUN uv sync --no-cache --all-extras --python ${VENV_PATH}/bin/python

# İzinleri ve satır sonlarını düzelt (Windows'ta geliştirme için önemli).
RUN find ${VENV_PATH}/bin -type f -print0 | xargs -0 dos2unix
RUN chmod -R +x ${VENV_PATH}/bin


# ===== AŞAMA: runtime =====
# Bu aşama, son imajın temelini oluşturur.
FROM python:${PYTHON_VERSION}-slim-bullseye AS runtime

# --- Ortam Değişkenleri (Runtime için de düzeltildi) ---
# Tutarlılık ve netlik için runtime aşamasında da ENV'leri yeniden tanımlıyoruz.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VENV_PATH=/opt/venv \
    PATH="/opt/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    # PYTHONPATH, Python'a modülleri nerede arayacağını söyler. 'src' layout için kritiktir.
    PYTHONPATH=/app/src

# Güvenlik için sisteme özel kullanıcı oluştur
RUN groupadd --system appgroup && useradd --system --gid appgroup --no-create-home appuser
WORKDIR /app

# Builder aşamasından sadece gerekli olanları kopyala:
# 1. Tamamen kurulmuş sanal ortam
COPY --from=builder --chown=appuser:appgroup ${VENV_PATH} ${VENV_PATH}
# 2. Uygulamanın kaynak kodu
COPY --from=builder --chown=appuser:appgroup /app/src/ ./src
COPY --from=builder --chown=appuser:appgroup /app/ImageBind/ ./ImageBind

USER appuser

# ===== HEDEF: api =====
FROM runtime AS api

# healthcheck için curl kur
# RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

EXPOSE 8000

# Sunucuyu başlat. Python, PYTHONPATH sayesinde 'app.api.main' yolunu bulacaktır.
CMD ["python", "-m", "gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app.api.main:app", "-b", "0.0.0.0:8000"]


# ===== HEDEF: indexer =====
FROM runtime AS indexer

# Indexer için gerekli olan ffmpeg'i kur
# Not: ffmpeg zaten base imajda kuruluydu, bu adım aslında gereksiz ama zararı yok.
# RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

# Indexer betiğini çalıştır. Python, PYTHONPATH sayesinde 'app.indexing.main' yolunu bulacaktır.
ENTRYPOINT ["python", "-m", "app.indexing.main"]