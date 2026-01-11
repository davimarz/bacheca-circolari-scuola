import os

# ==================== CONFIGURAZIONE SUPABASE ====================
# USA L'HOSTNAME DIRETTO BASATO SUL TUO PROJECT URL
# Il tuo Project URL è: https://ojnofjebr.lwrlowovvjd.supabase.co
# Quindi l'hostname del database è: db.ojnofjebrlwrlowovvjd.supabase.co

DB_CONFIG = {
    "host": "db.ojnofjebr.lwrlowovvjd.supabase.co",
    "port": 5432,  # Porta standard PostgreSQL
    "database": "postgres",
    "user": "postgres",  # Username semplice (senza .project-id)
    "password": os.environ.get("DB_PASSWORD", "dvd2Web@17."),
    
    # IMPOSTAZIONI CRITICHE:
    "sslmode": "require",  # SSL obbligatorio per Supabase
    "connect_timeout": 15,
    "keepalives": 1,
    "keepalives_idle": 30,
}

# ==================== CREDENZIALI ARGO ====================
ARGO_USER = os.environ.get("ARGO_USER", "davide.marziano.sc26953")
ARGO_PASS = os.environ.get("ARGO_PASS", "")

# ==================== URL SITI ====================
ARGO_URL = "https://www.argoscuola.it"
