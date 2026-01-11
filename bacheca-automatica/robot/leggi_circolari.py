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
import chromedriver_autoinstaller

# ==================== CONFIGURAZIONE PATH ====================
# Assicura che config.py venga trovato correttamente
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONFIG, ARGO_USER, ARGO_PASS, ARGO_URL, CHROME_OPTIONS

# ==================== CONFIGURAZIONE LOGGING ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ==================== FUNZIONI DATABASE ====================
def init_database():
    """Inizializza la connessione al database e crea la tabella se non esiste"""
    logger.info("📡 Mi collego al database PostgreSQL...")
    try:
        # Usa la configurazione da config.py
        conn = psycopg.connect(**DB_CONFIG)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Crea la tabella se non esiste
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
        
        logger.info("✅ Connesso al database Supabase! Tabella verificata.")
        return conn, cursor
        
    except Exception as e:
        logger.error(f"❌ Errore connessione database: {e}")
        raise

def circolare_esiste(cursor, numero):
    """Controlla se una circolare esiste già nel database"""
    cursor.execute("SELECT id FROM circolari WHERE numero = %s", (numero,))
    return cursor.fetchone() is not None

def salva_circolare(cursor, circolare):
    """Salva una nuova circolare nel database"""
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
        logger.error(f"❌ Errore salvataggio circolare {circolare['numero']}: {e}")
        return False

# ==================== FUNZIONI SCRAPING ====================
def setup_chrome():
    """Configura Chrome per Render.com"""
    logger.info("⚙️ Configuro Chrome per Render...")
    
    # Installa/aggiorna ChromeDriver
    chromedriver_autoinstaller.install()
    
    # Configura le opzioni
    options = webdriver.ChromeOptions()
    
    # Applica tutte le opzioni da config.py
    for option, value in CHROME_OPTIONS.items():
        if isinstance(value, bool) and value:
            options.add_argument(f"--{option}")
        elif isinstance(value, str):
            if option == "headless" and value == "new":
                options.add_argument("--headless=new")
            else:
                options.add_argument(f"--{option}={value}")
        else:
            options.add_argument(f"--{option}")
    
    # Opzioni aggiuntive
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Crea il driver
    driver = webdriver.Chrome(options=options)
    
    # Nasconde l'automazione
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    logger.info("✅ Browser Chrome configurato")
    return driver

def login_argo(driver):
    """Effettua il login su Argo Scuola"""
    logger.info(f"🔐 Accesso a Argo Scuola...")
    
    try:
        driver.get(ARGO_URL)
        time.sleep(3)
        
        # Accetta i cookie se presenti
        try:
            cookie_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Accetta') or contains(text(), 'Accetto')]")
            cookie_btn.click()
            time.sleep(1)
            logger.info("🍪 Cookie accettati")
        except:
            pass
        
        # Inserimento credenziali
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        password_field = driver.find_element(By.ID, "password")
        
        username_field.send_keys(ARGO_USER)
        password_field.send_keys(ARGO_PASS)
        
        # Clicca login
        login_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_btn.click()
        
        # Attendi il caricamento
        time.sleep(5)
        
        # Verifica login riuscito
        if "dashboard" in driver.current_url.lower() or "benvenuto" in driver.page_source.lower():
            logger.info("✅ Login effettuato con successo!")
            return True
        else:
            logger.error("❌ Login fallito - verificare credenziali")
            return False
            
    except Exception as e:
        logger.error(f"❌ Errore durante il login: {e}")
        return False

def estrai_circolari(driver):
    """Estrae le circolari dalla bacheca"""
    logger.info("🔍 Cerco nuove circolari...")
    
    try:
        # Vai alla sezione circolari (modifica questo percorso in base al sito reale)
        # Questo è un esempio, dovrai adattarlo alla struttura reale di Argo
        driver.get(f"{ARGO_URL}/circolari")
        time.sleep(5)
        
        # Cerca la tabella delle circolari
        # MODIFICA QUESTI SELECTOR in base alla struttura reale del sito
        rows = driver.find_elements(By.XPATH, "//table[@class='circolari']/tbody/tr")
        
        if not rows:
            # Prova un pattern alternativo
            rows = driver.find_elements(By.XPATH, "//div[contains(@class, 'circolare')]")
        
        circolari = []
        
        for row in rows:
            try:
                # MODIFICA QUESTA PARTE in base alla struttura reale
                numero = row.find_element(By.XPATH, "./td[1]").text.strip()
                titolo = row.find_element(By.XPATH, "./td[2]").text.strip()
                data_str = row.find_element(By.XPATH, "./td[3]").text.strip()
                destinatari = row.find_element(By.XPATH, "./td[4]").text.strip()
                
                # Parsing data
                try:
                    data_pubblicazione = datetime.strptime(data_str, "%d/%m/%Y").date()
                except:
                    data_pubblicazione = datetime.now().date()
                
                circolare = {
                    'numero': numero,
                    'titolo': titolo,
                    'data_pubblicazione': data_pubblicazione,
                    'destinatari': destinatari,
                    'allegati': '',
                    'data_scadenza': None
                }
                
                circolari.append(circolare)
                logger.info(f"📄 Trovata circolare: {numero} - {titolo}")
                
            except Exception as e:
                logger.warning(f"⚠️ Errore parsing riga: {e}")
                continue
        
        logger.info(f"✅ Trovate {len(circolari)} circolari")
        return circolari
        
    except Exception as e:
        logger.error(f"❌ Errore estrazione circolari: {e}")
        return []

# ==================== FUNZIONE PRINCIPALE ====================
def main():
    """Funzione principale dello script"""
    print("=" * 60)
    print("🤖 BACHECA CIRCOLARI ROBOT - AVVIATO")
    print("=" * 60)
    
    driver = None
    conn = None
    cursor = None
    
    try:
        # 1. Setup Chrome
        driver = setup_chrome()
        
        # 2. Connessione database
        conn, cursor = init_database()
        
        # 3. Login Argo
        if not login_argo(driver):
            logger.error("❌ Impossibile procedere senza login")
            return
        
        # 4. Estrai circolari
        circolari = estrai_circolari(driver)
        
        if not circolari:
            logger.warning("⚠️ Nessuna circolare trovata")
            return
        
        # 5. Salva nel database
        nuove = 0
        esistenti = 0
        
        for circolare in circolari:
            if circolare_esiste(cursor, circolare['numero']):
                esistenti += 1
                logger.debug(f"📋 Circolare {circolare['numero']} già esistente")
            else:
                if salva_circolare(cursor, circolare):
                    nuove += 1
                    logger.info(f"💾 SALVATA NUOVA: {circolare['numero']} - {circolare['titolo']}")
                else:
                    logger.error(f"❌ Errore salvataggio: {circolare['numero']}")
        
        # 6. Report finale
        print("\n" + "=" * 60)
        print("📊 REPORT FINALE:")
        print(f"   📄 Circolari trovate: {len(circolari)}")
        print(f"   🆕 Nuove salvate: {nuove}")
        print(f"   ✅ Già presenti: {esistenti}")
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Errore critico: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
    finally:
        # 7. Pulizia
        if driver:
            driver.quit()
            logger.info("🔚 Browser chiuso")
        
        if cursor:
            cursor.close()
        
        if conn:
            conn.close()
            logger.info("🔚 Connessione database chiusa")
        
        logger.info("🤖 Script terminato")

# ==================== AVVIO ====================
if __name__ == "__main__":
    main()
