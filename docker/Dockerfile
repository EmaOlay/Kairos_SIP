FROM python:3.11-slim

LABEL maintainer="Kairós Development Team"
LABEL description="Motor de Analítica Prescriptiva para Optimización Académica"

# Configurar directorio de trabajo
WORKDIR /app

# Configurar variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos de dependencias
COPY requirements.txt pyproject.toml ./

# Instalar dependencias Python
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# Copiar código fuente
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY data/ ./data/
COPY config/ ./config/

# Crear usuario no-root por seguridad
RUN useradd -m -u 1000 kairos && \
    chown -R kairos:kairos /app

USER kairos

# Health check (opcional)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Comando por defecto
CMD ["python", "scripts/ejemplo_demo.py"]
