# Dockerfile pour le Bot de Trading Python
# ==========================================
# Image optimisée pour le paper trading sur QNAP
# Basée sur python:3.12-slim (Alpine Linux)

# Utiliser une image Python officielle légère
FROM python:3.12-slim

# Définir le répertoire de travail
WORKDIR /app

# Installer les dépendances système nécessaires
# (certaines libs Python nécessitent des dépendances système)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    python3-dev \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copier les fichiers du projet
COPY requirements.txt .
COPY bot/ ./bot/
COPY config.yaml .
COPY strategies.yaml .
COPY .env.example .
COPY generate_discord_report.py .
COPY generate_final_reports.py .

# Créer les dossiers pour les données persistantes
RUN mkdir -p data logs state reports

# Installer les dépendances Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Créer un utilisateur non-root pour la sécurité (recommandé pour la production)
RUN useradd -m botuser && \
    chown -R botuser:botuser /app

# Basculer vers l'utilisateur non-root
USER botuser

# Variable d'environnement par défaut
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Commande par défaut (peut être surchargée)
CMD ["python", "-m", "bot", "paper"]
