import os
import time
import glob
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import psycopg
from psycopg.rows import dict_row
import re
import logging

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

print("=" * 60)
print("🤖 BACHECA CIRCOLARI ROBOT - AVVIATO")
print("=" * 60)

# ==============================================================================
# 🛑 CONFIGURAZIONE DA VARIABILI D'AMBIENTE
# ==============================================================================
config = {
    'ARGO_USER': os.environ.get('ARGO_USER'),
    'ARGO_PASS': os.environ.get('ARGO_PASS'),
    'DB_HOST': 'db.ojnofjebrlwrlowovvjd.supabase.co',
    'DB_PORT': '5432',
    'DB_NAME': 'postgres',
    'DB_USER': 'postgres',
    'DB_PASSWORD': os.environ.get('DB_PASSWORD'),
}

# Verifica configurazione
missing_vars = []
for key, value in config.items():
    if not value and key in ['ARGO_USER', 'ARGO_PASS', 'DB_PASSWORD']:
        missing_vars.append(key)

if missing_vars:
    logger.error(f"❌ ERRORE: Configura queste variabili d'ambiente: {', '.join(missing_vars)}")
    exit(1)

# ==============================================================================

# --- CONFIGURAZIONE CHROME PER RENDER FREE ---
logger.info("⚙️ Configuro Chrome per Render...")
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

# Configurazione download PDF (opzionale)
cartella_download = os.path.join(os.getcwd(), "downloads_temp")
if not os.path.exists(cartella_download):
    os.makedirs(cartella_download)

# Avvia browser
try:
    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    logger.info("✅ Browser Chrome configurato")
except Exception as e:
    logger.error(f"❌ Errore avvio Chrome: {e}")
    exit(1)

wait = WebDriverWait(driver, 30)

# --- CONNESSIONE POSTGRESQL (psycopg3) ---
def get_db_connection():
    """Crea e restituisce una connessione al database PostgreSQL"""
    try:
        conn = psycopg.connect(
            host=config['DB_HOST'],
            port=config['DB_PORT'],
            dbname=config['DB_NAME'],
            user=config['DB_USER'],
            password=config['DB_PASSWORD'],
            sslmode='require'
        )
        logger.info("✅ Connessione database stabilita")
        return conn
    except Exception as e:
        logger.error(f"❌ Errore connessione database: {e}")
        raise

logger.info("📡 Mi collego al database PostgreSQL...")
try:
    conn = get_db_connection()
    cur = conn.cursor(row_factory=dict_row)
except Exception as e:
    logger.error(f"❌ Impossibile connettersi al database: {e}")
    driver.quit()
    exit(1)

# ==============================================================================
# FUNZIONI UTILITY
# ==============================================================================

def estrai_data_dal_testo(testo):
    """Estrae la data di pubblicazione dal testo della circolare"""
    if not testo:
        return None
    
    # Cerca pattern di data nel formato DD/MM/YYYY
    pattern = r'(\d{2})/(\d{2})/(\d{4})'
    matches = re.findall(pattern, testo)
    
    for match in matches:
        try:
            giorno, mese, anno = map(int, match)
            # Validazione base
            if 1 <= giorno <= 31 and 1 <= mese <= 12 and anno >= 2020:
                return datetime(anno, mese, giorno)
        except:
            continue
    
    return None

def salva_circolare_db(titolo, contenuto, data_pubblica, pdf_url=""):
    """Salva una circolare nel database PostgreSQL"""
    try:
        # Prima controlla se esiste già
        cur.execute(
            "SELECT id FROM circolari WHERE titolo = %s AND data_pubblica = %s",
            (titolo, data_pubblica)
        )
        if cur.fetchone():
            logger.info(f"   💤 Già presente nel database: {titolo[:50]}...")
            return False
        
        # Inserisci nuova circolare
        cur.execute(
            """INSERT INTO circolari (titolo, contenuto, data_pubblica, pdf_url, created_at)
               VALUES (%s, %s, %s, %s, NOW())""",
            (titolo, contenuto, data_pubblica, pdf_url)
        )
        conn.commit()
        logger.info(f"   ✅ Salvata nel database: {titolo[:50]}...")
        return True
    except Exception as e:
        logger.error(f"   ❌ Errore salvataggio database: {e}")
        conn.rollback()
        return False

def pulisci_circolari_vecchie():
    """Rimuove le circolari più vecchie di 30 giorni"""
    logger.info("🧹 Pulizia circolari vecchie (>30 giorni)...")
    try:
        data_limite = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("DELETE FROM circolari WHERE data_pubblica < %s", (data_limite,))
        deleted_count = cur.rowcount
        conn.commit()
        logger.info(f"   ✅ Pulizia completata: rimosse {deleted_count} circolari")
    except Exception as e:
        logger.error(f"   ⚠️  Errore pulizia: {e}")

# ==============================================================================
# LOGICA PRINCIPALE
# ==============================================================================

try:
    # --- PULIZIA INIZIALE ---
    pulisci_circolari_vecchie()
    
    # --- LOGIN SU ARGO ---
    logger.info("🌍 Login su Argo...")
    driver.get("https://www.portaleargo.it/famiglia")
    time.sleep(3)
    
    # Compila login
    username_field = driver.find_element(By.ID, "username")
    username_field.send_keys(config['ARGO_USER'])
    
    password_field = driver.find_element(By.ID, "password")
    password_field.send_keys(config['ARGO_PASS'])
    
    login_button = driver.find_element(By.ID, "login-button")
    login_button.click()
    
    logger.info("⏳ Attendo login...")
    time.sleep(5)
    
    # Screenshot per debug
    driver.save_screenshot("01_dopo_login.png")
    logger.info("📸 Screenshot salvato: 01_dopo_login.png")
    
    # --- VAI ALLE CIRCOLARI ---
    logger.info("👉 Navigo alle Circolari...")
    
    # Cerca link "Circolari"
    found = False
    try:
        # Prima prova con link esatto
        circolari_link = driver.find_element(By.LINK_TEXT, "Circolari")
        circolari_link.click()
        found = True
    except:
        pass
    
    if not found:
        try:
            # Prova con testo parziale
            circolari_link = driver.find_element(By.XPATH, "//a[contains(text(), 'Circolari')]")
            circolari_link.click()
            found = True
        except:
            pass
    
    if not found:
        # Cerca qualsiasi link che contenga "circolari"
        links = driver.find_elements(By.TAG_NAME, "a")
        for link in links:
            if 'circolari' in link.text.lower():
                link.click()
                found = True
                break
    
    if not found:
        logger.error("❌ Non trovo il link delle circolari")
        driver.save_screenshot("errore_circolari.png")
        logger.info("📸 Screenshot salvato: errore_circolari.png")
        exit(1)
    
    logger.info("⏳ Caricamento pagina circolari...")
    time.sleep(8)
    
    # --- CERCA LE CIRCOLARI ---
    logger.info("🔍 Cerco le circolari nella pagina...")
    
    # Prendi tutto il testo della pagina
    page_text = driver.find_element(By.TAG_NAME, "body").text
    logger.info(f"📄 Contenuto pagina: {len(page_text)} caratteri")
    
    # Dividi in righe
    lines = page_text.split('\n')
    circolari_trovate = 0
    
    for line in lines:
        line = line.strip()
        if not line or len(line) < 20:
            continue
            
        # Cerca indicatori di circolare
        if ('CIRCOLARE' in line or 'Circolare' in line or 
            'PROT.' in line or 'Prot.' in line or 
            'N.' in line and '/' in line):
            
            logger.info(f"📌 Trovata possibile circolare: {line[:80]}...")
            
            # Estrai data
            data_circolare = estrai_data_dal_testo(line)
            
            if data_circolare:
                # Filtro 30 giorni
                giorni_passati = (datetime.now() - data_circolare).days
                if giorni_passati > 30:
                    logger.info(f"   ⏹️  Troppo vecchia ({giorni_passati} giorni)")
                    continue
                
                # Salva nel database
                data_pubblica_db = data_circolare.strftime("%Y-%m-%d %H:%M:%S")
                if salva_circolare_db(
                    titolo=line[:200],
                    contenuto=line,
                    data_pubblica=data_pubblica_db
                ):
                    circolari_trovate += 1
    
    # Risultati
    logger.info(f"\n{'='*60}")
    logger.info(f"🎉 ELABORAZIONE COMPLETATA!")
    logger.info(f"   • Righe analizzate: {len(lines)}")
    logger.info(f"   • Circolari salvate: {circolari_trovate}")
    
    if circolari_trovate == 0:
        logger.info("ℹ️  Nessuna nuova circolare trovata o tutte già presenti nel database")

except Exception as e:
    logger.error(f"\n❌ ERRORE CRITICO: {e}")
    import traceback
    logger.error(traceback.format_exc())
    
    # Screenshot dell'errore
    try:
        driver.save_screenshot("errore_finale.png")
        logger.info("📸 Screenshot salvato: errore_finale.png")
    except:
        pass

finally:
    # --- PULIZIA FINALE ---
    logger.info("\n🧹 Pulizia finale...")
    
    # Chiudi database
    try:
        cur.close()
        conn.close()
        logger.info("   🔒 Connessione database chiusa")
    except:
        pass
    
    # Chiudi browser
    try:
        driver.quit()
        logger.info("   🔒 Browser chiuso")
    except:
        pass
    
    # Pulisci cartella download
    try:
        files = glob.glob(os.path.join(cartella_download, "*"))
        for f in files:
            try:
                os.remove(f)
            except:
                pass
        if os.path.exists(cartella_download):
            os.rmdir(cartella_download)
        logger.info("   🗑️  Cartella temporanea pulita")
    except:
        pass

logger.info("\n✅ Robot completato con successo!")
print("=" * 60)
