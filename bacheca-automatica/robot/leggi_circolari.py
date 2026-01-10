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

# Per Render, usa ChromeDriver con Service
try:
    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    logger.info("✅ Browser Chrome configurato")
except Exception as e:
    logger.error(f"❌ Errore avvio Chrome: {e}")
    exit(1)

wait = WebDriverWait(driver, 30)

# Configurazione download PDF (opzionale)
cartella_download = os.path.join(os.getcwd(), "downloads_temp")
if not os.path.exists(cartella_download):
    os.makedirs(cartella_download)

# --- CONNESSIONE POSTGRESQL ---
def get_db_connection():
    """Crea e restituisce una connessione al database PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host=config['DB_HOST'],
            port=config['DB_PORT'],
            database=config['DB_NAME'],
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
    cur = conn.cursor(cursor_factory=RealDictCursor)
except Exception as e:
    logger.error(f"❌ Impossibile connettersi al database: {e}")
    driver.quit()
    exit(1)

# ==============================================================================
# FUNZIONI UTILITY
# ==============================================================================

def attendi_e_trova_file():
    """Attende il download del file e restituisce il percorso"""
    tempo_max = 20
    timer = 0
    while timer < tempo_max:
        files = glob.glob(os.path.join(cartella_download, "*.*"))
        files_completi = [f for f in files if not f.endswith('.crdownload') and not f.endswith('.tmp')]
        if files_completi:
            return max(files_completi, key=os.path.getctime)
        time.sleep(1)
        timer += 1
    return None

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
    
    # Screenshot per debug
    driver.save_screenshot("01_dopo_accesso.png")
    
    # Compila login
    username_field = driver.find_element(By.ID, "username")
    username_field.send_keys(config['ARGO_USER'])
    
    password_field = driver.find_element(By.ID, "password")
    password_field.send_keys(config['ARGO_PASS'])
    
    login_button = driver.find_element(By.ID, "login-button")
    login_button.click()
    
    logger.info("⏳ Attendo login...")
    time.sleep(5)
    
    # Screenshot dopo login
    driver.save_screenshot("02_dopo_login.png")
    
    # --- VAI ALLE CIRCOLARI ---
    logger.info("👉 Navigo alle Circolari...")
    
    # Cerca il link "Circolari" - APPROCCIO DIRETTO
    try:
        # Prima prova con link esatto
        circolari_link = driver.find_element(By.LINK_TEXT, "Circolari")
        circolari_link.click()
    except:
        # Se non trova, prova con testo parziale
        try:
            circolari_link = driver.find_element(By.XPATH, "//a[contains(text(), 'Circolari')]")
            circolari_link.click()
        except:
            # Ultimo tentativo: cerca qualsiasi link che contenga "circolari"
            try:
                links = driver.find_elements(By.TAG_NAME, "a")
                for link in links:
                    if 'circolari' in link.text.lower():
                        link.click()
                        break
                else:
                    raise Exception("Link non trovato")
            except:
                logger.error("❌ Non trovo il link delle circolari")
                driver.save_screenshot("errore_circolari.png")
                logger.info("📸 Screenshot salvato come 'errore_circolari.png'")
                exit(1)
    
    logger.info("⏳ Caricamento pagina circolari...")
    time.sleep(8)
    driver.save_screenshot("03_pagina_circolari.png")
    
    # --- CERCA LE CIRCOLARI ---
    logger.info("🔍 Cerco le circolari nella pagina...")
    
    # APPROCCIO: Cerca qualsiasi elemento che potrebbe contenere circolari
    elementi_circolari = []
    
    # Prova diverse strategie
    strategie = [
        ("//tr[contains(., 'CIRCOLARE') or contains(., 'Circolare')]", "XPath per righe tabella"),
        ("//div[contains(., 'CIRCOLARE') or contains(., 'Circolare')]", "XPath per div"),
        ("//*[contains(text(), 'CIRCOLARE') or contains(text(), 'Circolare')]", "XPath generico")
    ]
    
    for xpath, descrizione in strategie:
        try:
            elementi = driver.find_elements(By.XPATH, xpath)
            if elementi:
                logger.info(f"   ✅ Trovati {len(elementi)} elementi con strategia: {descrizione}")
                elementi_circolari.extend(elementi)
                break
        except:
            continue
    
    if not elementi_circolari:
        # Ultima strategia: cerca qualsiasi elemento con testo significativo
        tutti_elementi = driver.find_elements(By.XPATH, "//*")
        for elemento in tutti_elementi[:100]:  # Limita a primi 100 per performance
            testo = elemento.text.strip()
            if len(testo) > 50 and any(keyword in testo.lower() for keyword in ['circolare', 'prot.', 'n.']):
                elementi_circolari.append(elemento)
    
    logger.info(f"📊 Totale elementi trovati: {len(elementi_circolari)}")
    
    if not elementi_circolari:
        logger.warning("⚠️ Nessuna circolare identificata.")
        logger.info("Contenuto pagina (primi 2000 caratteri):")
        logger.info(driver.page_source[:2000])
        exit(0)  # Esci senza errore, forse non ci sono circolari oggi
    
    # --- ELABORA OGNI CIRCOLARE ---
    logger.info(f"\n🎯 Inizio elaborazione di {len(elementi_circolari)} circolari...")
    circolari_salvate = 0
    
    for idx, elemento in enumerate(elementi_circolari[:10]):  # Limita a 10 per sicurezza
        logger.info(f"\n{'='*60}")
        logger.info(f"🔄 [{idx+1}/{len(elementi_circolari)}] Processo circolare...")
        
        try:
            testo_elemento = elemento.text.strip()
            if len(testo_elemento) < 20:
                logger.info("   ⏭️  Testo troppo corto, salto")
                continue
            
            logger.info(f"   📄 Testo ({len(testo_elemento)} caratteri):")
            logger.info(f"      {testo_elemento[:150]}...")
            
            # Estrai titolo (prima linea significativa)
            linee = testo_elemento.split('\n')
            titolo = ""
            for linea in linee:
                linea = linea.strip()
                if linea and len(linea) > 10:
                    titolo = linea[:200]
                    break
            
            if not titolo:
                titolo = f"Circolare {idx+1}"
            
            logger.info(f"   📌 Titolo: {titolo[:80]}...")
            
            # Cerca data
            data_circolare = estrai_data_dal_testo(testo_elemento)
            
            if data_circolare:
                logger.info(f"   📅 Data trovata: {data_circolare.strftime('%d/%m/%Y')}")
                
                # FILTRO 30 GIORNI
                giorni_passati = (datetime.now() - data_circolare).days
                if giorni_passati > 30:
                    logger.info(f"⏹️  CIRCOLARE VECCHIA: {giorni_passati} giorni")
                    continue
                
                logger.info(f"   ✅ Circolare recente ({giorni_passati} giorni fa)")
                
                # Prova a cliccare per dettagli
                contenuto_completo = testo_elemento
                try:
                    # Salva URL corrente
                    url_corrente = driver.current_url
                    
                    # Clicca sull'elemento
                    elemento.click()
                    time.sleep(3)
                    
                    # Estrai contenuto della nuova pagina
                    try:
                        corpo_pagina = driver.find_element(By.TAG_NAME, "body")
                        contenuto_completo = corpo_pagina.text
                        
                        # Cerca data anche nel contenuto completo
                        data_dal_contenuto = estrai_data_dal_testo(contenuto_completo)
                        if data_dal_contenuto:
                            data_circolare = data_dal_contenuto
                    except:
                        pass
                    
                    # Torna indietro
                    driver.back()
                    time.sleep(3)
                    
                except Exception as e:
                    logger.info(f"   ⚠️  Non posso aprire dettagli: {e}")
                
                # SALVA NEL DATABASE
                data_pubblica_db = data_circolare.strftime("%Y-%m-%d %H:%M:%S")
                
                if salva_circolare_db(titolo, contenuto_completo, data_pubblica_db):
                    circolari_salvate += 1
                else:
                    logger.info("   ⚠️  Saltata (già presente)")
                    
            else:
                logger.info("   ⚠️  Data non trovata, salto")
                
        except Exception as e:
            logger.error(f"   ❌ Errore elaborazione: {e}")
            continue
    
    logger.info(f"\n{'='*60}")
    logger.info(f"🎉 ELABORAZIONE COMPLETATA!")
    logger.info(f"   • Elementi trovati: {len(elementi_circolari)}")
    logger.info(f"   • Circolari salvate: {circolari_salvate}")
    logger.info(f"   • Database PostgreSQL aggiornato")

except Exception as e:
    logger.error(f"\n❌ ERRORE CRITICO: {e}")
    import traceback
    logger.error(traceback.format_exc())
    
    # Fa screenshot dell'errore
    try:
        driver.save_screenshot("errore_finale.png")
        logger.info("📸 Screenshot errore salvato come 'errore_finale.png'")
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
