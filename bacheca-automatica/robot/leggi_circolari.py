import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from supabase import create_client
import urllib.parse

print("🤖 Robot avviato automaticamente")

# Config da variabili ambiente
config = {
    'ARGO_USER': os.environ.get('ARGO_USER'),
    'ARGO_PASS': os.environ.get('ARGO_PASS'),
    'SUPABASE_URL': os.environ.get('SUPABASE_URL'),
    'SUPABASE_KEY': os.environ.get('SUPABASE_KEY')
}

# Qui inserisci il resto del tuo codice robot (la parte di scraping)
# Mantieni la logica principale ma rimuovi i print decorativi
# Usa solo logging essenziale per l'automazione

print("✅ Robot completato")