import os

# ==================== CONFIGURAZIONE SUPABASE ====================
DB_CONFIG = {
    # HOSTNAME CORRETTO: aggiungi "db." all'inizio
    "host": "db.ojnofjebrlwrlowovvjd.supabase.co",
    "port": 5432,
    "database": "postgres",
    "user": "postgres",
    "password": os.environ.get("DB_PASSWORD", "dvd2Web@17."),
    
    # IMPOSTAZIONI OBBLIGATORIE:
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
