import os

# ==================== CONFIGURAZIONE SUPABASE ====================
DB_CONFIG = {
    "host": "aws-0-eu-central-1.pooler.supabase.co",
    "port": 6543,
    "database": "postgres",
    "user": "postgres.ojnofjebrlwrlowovvjd",
    "password": os.environ.get("DB_PASSWORD", "dvd2Web@17."),
    "sslmode": "require",
    "connect_timeout": 15,
    "keepalives": 1,
    "keepalives_idle": 30,
}

# ==================== CREDENZIALI ARGO ====================
ARGO_USER = os.environ.get("ARGO_USER", "davide.marziano.sc26953")
ARGO_PASS = os.environ.get("ARGO_PASS", "")

# ==================== URL SITI ====================
ARGO_URL = "https://www.argoscuola.it"
