import os
import sys
import logging
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import psycopg

# ==================== CONFIGURAZIONE PATH ====================
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONFIG, ARGO_USER, ARGO_PASS, ARGO_URL

# ==================== CONFIGURAZIONE LOGGING ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ==================== FUNZIONI DATABASE ====================
def init_database():
    """Inizializza la connessione al database"""
    logger.info("📡 Mi collego al database PostgreSQL...")
    try:
        conn = psycopg.connect(**DB_CONFIG)
        conn.autocommit = True
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS circolari (
                id SERIAL PRIMARY KEY,
                numero VARCHAR(50) UNIQUE NOT NULL,
                titolo TEXT NOT NULL,
                data_pubblicazione DATE NOT NULL,
                destinatari TEXT,
                allegati TEXT,
                data_scadenza DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        logger.info("✅ Connesso al database Supabase!")
        return conn, cursor
        
    except Exception as e:
        logger.error(f"❌ Errore connessione database: {e}")
        raise

def circolare_esiste(cursor, numero):
    """Controlla se una circolare esiste già"""
    cursor.execute("SELECT id FROM circolari WHERE numero = %s", (numero,))
    return cursor.fetchone() is not None

def salva_circolare(cursor, circolare):
    """Salva una nuova circolare"""
    try:
        cursor.execute("""
            INSERT INTO circolari (numero, titolo, data_pubblicazione, destinatari, allegati, data_scadenza)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (numero) DO NOTHING
        """, (
            circolare['numero'],
            circolare['titolo'],
            circolare['data_pubblicazione'],
            circolare['destinatari'],
            circolare['allegati'],
            circolare['data_scadenza']
        ))
        return True
    except Exception as e:
        logger.error(f"❌ Errore salvataggio {circolare['numero']}: {e}")
        return False

# ==================== FUNZIONI BROWSER ====================
def setup_browser():
    """Configura browser per Render (Chrome o Firefox)"""
    logger.info("⚙️ Configuro browser per Render...")
    
    try:
        # Prova Chrome prima (più comune)
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        driver = webdriver.Chrome(options=options)
        logger.info("✅ Browser Chrome configurato")
        
    except Exception as e:
        logger.warning(f"⚠️ Chrome non disponibile: {e}")
        
        # Fallback a Firefox
        try:
            options = webdriver.FirefoxOptions()
            options.add_argument("--headless")
            driver = webdriver.Firefox(options=options)
            logger.info("✅ Browser Firefox configurato")
        except Exception as e2:
            logger.error(f"❌ Nemmeno Firefox disponibile: {e2}")
            raise
    
    # Configurazione comune
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def login_argo(driver):
    """Effettua il login su Argo"""
    logger.info("🔐 Accesso a Argo Scuola...")
    
    try:
        driver.get(ARGO_URL)
        time.sleep(3)
        
        # Cookie
        try:
            cookie_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Accetta')]")
            cookie_btn.click()
            time.sleep(1)
            logger.info("🍪 Cookie accettati")
        except:
            pass
        
        # Credenziali
        username = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        password = driver.find_element(By.ID, "password")
        
        username.send_keys(ARGO_USER)
        password.send_keys(ARGO_PASS)
        
        # Login
        login_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_btn.click()
        
        time.sleep(5)
        
        # Verifica
        if "dashboard" in driver.current_url or "benvenuto" in driver.page_source:
            logger.info("✅ Login effettuato!")
            return True
        else:
            logger.error("❌ Login fallito")
            return False
            
    except Exception as e:
        logger.error(f"❌ Errore login: {e}")
        return False

def estrai_circolari(driver):
    """Estrae le circolari"""
    logger.info("🔍 Cerco nuove circolari...")
    
    # ESEMPIO - DEVI MODIFICARE QUESTA PARTE PER IL TUO SITO ARGO
    circolari = []
    
    try:
        # Modifica questo URL e i selector per il tuo sito Argo
        driver.get(f"{ARGO_URL}/circolari")
        time.sleep(5)
        
        # ESEMPIO: Cerca una tabella - MODIFICA QUESTI SELECTOR
        try:
            rows = driver.find_elements(By.CSS_SELECTOR, "table.circolari tbody tr")
            
            for i, row in enumerate(rows[:5]):  # Limita a 5 per test
                try:
                    # MODIFICA QUESTI SELECTOR PER LA TUA SCUOLA
                    cells = row.find_elements(By.TAG_NAME, "td")
                    
                    if len(cells) >= 3:
                        circolare = {
                            'numero': f"TEST-{i+1}",  # Modifica
                            'titolo': cells[1].text if len(cells) > 1 else "Test",
                            'data_pubblicazione': datetime.now().date(),
                            'destinatari': cells[2].text if len(cells) > 2 else "Tutti",
                            'allegati': "",
                            'data_scadenza': None
                        }
                        circolari.append(circolare)
                        logger.info(f"📄 Trovata: {circolare['numero']}")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Errore parsing riga {i}: {e}")
                    
        except Exception as e:
            logger.warning(f"⚠️ Tabella non trovata: {e}")
            
            # Fallback: crea dati di test
            for i in range(3):
                circolari.append({
                    'numero': f"TEST-{i+1}",
                    'titolo': f"Circolare di test {i+1}",
                    'data_pubblicazione': datetime.now().date(),
                    'destinatari': "Studenti",
                    'allegati': "",
                    'data_scadenza': None
                })
                logger.info(f"📄 Dato test: TEST-{i+1}")
        
    except Exception as e:
        logger.error(f"❌ Errore estrazione: {e}")
    
    logger.info(f"✅ Trovate {len(circolari)} circolari")
    return circolari

# ==================== MAIN ====================
def main():
    print("=" * 60)
    print("🤖 BACHECA CIRCOLARI ROBOT - AVVIATO")
    print("=" * 60)
    
    driver = None
    conn = None
    
    try:
        # 1. Browser
        driver = setup_browser()
        
        # 2. Database
        conn, cursor = init_database()
        
        # 3. Login
        if not login_argo(driver):
            logger.error("❌ Login fallito - verifica credenziali")
            # Continua comunque per test database
            
        # 4. Estrai circolari
        circolari = estrai_circolari(driver)
        
        # 5. Salva
        nuove = 0
        for circ in circolari:
            if not circolare_esiste(cursor, circ['numero']):
                if salva_circolare(cursor, circ):
                    nuove += 1
                    logger.info(f"💾 Salvata: {circ['numero']}")
        
        # 6. Report
        print(f"\n📊 Trovate: {len(circolari)} | Salvate: {nuove}")
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Errore: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
    finally:
        if driver:
            driver.quit()
            logger.info("🔚 Browser chiuso")
        
        if conn:
            conn.close()
            logger.info("🔚 Database chiuso")
        
        logger.info("🤖 Script terminato")

if __name__ == "__main__":
    main()
