# Usar Ubuntu 22.04 como imagem base
FROM ubuntu:22.04

# Evitar prompts interativos durante a instalação
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    curl \
    postgresql-client \
    build-essential \
    && pg_dump --version \
    && pg_restore --version \
    && rm -rf /var/lib/apt/lists/*

# Configurar diretório de trabalho
WORKDIR /app

# Copiar requirements primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instalar dependências do Python
RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Copiar o restante do código
COPY . .

# Expor a porta que o app vai rodar
EXPOSE 5000

# Comando para iniciar a aplicação com Gunicorn
# Timeout explícito para evitar abortos prematuros de worker em operações lentas.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--timeout", "120", "--graceful-timeout", "120", "--keep-alive", "5", "--access-logfile", "-", "--error-logfile", "-", "run:app"]
