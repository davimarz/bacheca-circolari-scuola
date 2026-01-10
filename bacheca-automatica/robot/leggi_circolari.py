import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

print("=" * 60)
print("🤖 TEST BASE - AVVIATO")
print("=" * 60)

# 1. Test variabili
print("📝 Variabili d'ambiente:")
ARGO_USER = os.environ.get('ARGO_USER')
ARGO_PASS = os.environ.get('ARGO_PASS')
DB_PASS = os.environ.get('DB_PASSWORD')

print(f"  ARGO_USER: {'✅' if ARGO_USER else '❌'}")
print(f"  ARGO_PASS: {'✅' if ARGO_PASS else '❌'}")
print(f"  DB_PASSWORD: {'✅' if DB_PASS else '❌'}")

if not all([ARGO_USER, ARGO_PASS, DB_PASS]):
    print("❌ ERRORE: Variabili mancanti!")
    exit(1)

# 2. Test Selenium
print("\n🌐 Test Selenium...")
try:
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    
    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    print("  ✅ Selenium installato e funzionante")
    
    # Test pagina web
    driver.get("https://www.google.com")
    print(f"  ✅ Pagina caricata: {driver.title}")
    
    driver.quit()
    print("  ✅ Browser chiuso correttamente")
    
except Exception as e:
    print(f"  ❌ Errore Selenium: {e}")

# 3. Test psycopg (opzionale)
print("\n🗄️ Test database...")
try:
    import psycopg
    print("  ✅ psycopg installato")
    
    # Prova connessione
    conn = psycopg.connect(
        host='db.ojnofjebrlwrlowovvjd.supabase.co',
        dbname='postgres',
        user='postgres',
        password=DB_PASS,
        sslmode='require',
        connect_timeout=5
    )
    conn.close()
    print("  ✅ Connessione database riuscita")
    
except ImportError:
    print("  ❌ psycopg NON installato")
    print("  ℹ️  Controlla requirements.txt!")
except Exception as e:
    print(f"  ⚠️  Errore connessione: {e}")

print("\n" + "=" * 60)
print("🎉 TEST COMPLETATO")
print("=" * 60)
