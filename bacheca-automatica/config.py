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
}

# ==================== CREDENZIALI ARGO ====================
ARGO_USER = os.environ.get("ARGO_USER", "davide.marziano.sc26953")
ARGO_PASS = os.environ.get("ARGO_PASS", "")

# ==================== URL SITI ====================
ARGO_URL = "https://www.argoscuola.it"

# ==================== CONFIGURAZIONE CHROME ====================
# Path dove Chrome sarà installato su Render
CHROME_PATH = "/usr/bin/google-chrome-stable"

CHROME_OPTIONS = {
    "headless": "new",
    "no-sandbox": True,
    "disable-dev-shm-usage": True,
    "disable-gpu": True,
    "window-size": "1920,1080",
}
