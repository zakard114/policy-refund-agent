# Policy & Refund Support Agent — Streamlit UI (Module 5-4b)
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=8502 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1

COPY pyproject.toml README.md ./
COPY app ./app
COPY data ./data
COPY streamlit_app.py ./

RUN pip install --upgrade pip \
    && pip install . "numpy>=1.26"

# Render injects PORT; local Compose uses 8502.
EXPOSE 8502

CMD ["sh", "-c", "exec python -m streamlit run streamlit_app.py --server.headless true --server.address 0.0.0.0 --server.port ${PORT:-8502}"]
