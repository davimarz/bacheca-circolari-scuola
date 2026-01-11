import os

# ==================== CONFIGURAZIONE SUPABASE ====================
# BASATO SUL TUO URL: https://ojnofjebr.lwrlowovvjd.supabase.co

DB_CONFIG = {
    # USIAMO IL CONNECTION POOLER (GARANTITO PER RENDER)
    "host": "aws-0-eu-central-1.pooler.supabase.co",  # POOLER STANDARD SUPABASE
    "port": 6543,  # PORTA POOLER
    "database": "postgres",  # DATABASE DEFAULT
    "user": "postgres.ojnofjebrlwrlowovvjd",  # FORMATO: postgres.[project-id]
    "password": os.environ.get("DB_PASSWORD", "dvd2Web@17."),
    
    # IMPOSTAZIONI OBBLIGATORIE:
    "sslmode": "require",  # SSL RICHIESTO
    "connect_timeout": 15,  # TIMEOUT CONNESSIONE
    
    # OTTIMIZZAZIONI:
    "keepalives": 1,
    "keepalives_idle": 30,
    "keepalives_interval": 5,
    "keepalives_count": 5,
    
    # ALTRE OPZIONI:
    "target_session_attrs": "read-write",
    "application_name": "bacheca_circolari_app",
}

# ==================== CREDENZIALI ARGO ====================
ARGO_USER = os.environ.get("ARGO_USER", "davide.marziano.sc26953")
ARGO_PASS = os.environ.get("ARGO_PASS", "")

# ==================== URL SITI ====================
ARGO_URL = "https://www.argoscuola.it"

# ==================== CONFIGURAZIONE CHROME ====================
CHROME_OPTIONS = {
    "headless": "new",  # NUOVA MODALITÀ HEADLESS (MIGLIORE)
    "no-sandbox": True,
    "disable-dev-shm-usage": True,
    "disable-gpu": True,
    "window-size": "1920,1080",
    "disable-blink-features": "AutomationControlled",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}
