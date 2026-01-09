"""
Configurazioni dell'applicazione Bacheca Circolari
"""

# Impostazioni app
CONFIG = {
    # Intervallo aggiornamento automatico (minuti)
    'UPDATE_INTERVAL': 30,
    
    # Giorni di validità circolari (per il robot di cancellazione automatica)
    'CIRCOLARI_VALIDITA_GIORNI': 30,
    
    # URL sito scuola (per lo scraper)
    'URL_SITO_SCUOLA': "https://www.icannafrankag.edu.it/circolari",
    
    # URL Argo (per il robot di scraping)
    'URL_ARGO': "https://www.portaleargo.it/famiglia",
    
    # Fuso orario Italia
    'TIMEZONE_ITALIA': "Europe/Rome",
    
    # =============================================
    # COLORI PASTELLO - palette dallo screenshot 3.png
    # =============================================
    'COLORS': {
        # Colori principali
        'primary': '#a8d8ea',      # Azzurro pastello - pulsanti principali
        'secondary': '#f8a8b8',    # Rosa pastello - badge "NUOVA", pulsante cancella
        'accent': '#fff9f0',       # Beige chiaro - sfondo header
        'success': '#c8e8c0',      # Verde menta - elementi successo
        'warning': '#f8d8a8',      # Giallo pesca - elementi warning
        'danger': '#f8a8a8',       # Rosso pastello - elementi pericolo
        
        # Sfondi
        'background': '#f0f9f4',   # Verde menta chiaro - sfondo principale app
        'card': '#fffefb',         # Beige molto chiaro - sfondo card circolari
        'header_bg': '#fff9f0',    # Beige pastello - sfondo header principale
        'container_bg': '#fff9f0', # Beige pastello - sfondo contenitori
        
        # Testi
        'text_primary': '#4a6572',   # Blu-grigio scuro - titoli principali
        'text_secondary': '#6a7b8c', # Blu-grigio medio - sottotitoli
        'text_light': '#8a9aab',     # Blu-grigio chiaro - testo secondario
        'text_muted': '#a8b8c8',     # Blu-grigio molto chiaro - testo disabilitato
        
        # Bordi
        'border_primary': '#e8e2d6',   # Beige - bordi principali
        'border_secondary': '#d8e2e8', # Azzurro chiaro - bordi secondari
        'border_accent': '#c8e4f0',    # Azzurro - bordi accentati
        
        # Pulsanti
        'button_primary': '#a8d8ea',   # Azzurro pastello
        'button_primary_hover': '#8cc6e0',
        'button_secondary': '#f8a8b8', # Rosa pastello
        'button_secondary_hover': '#f58ca0',
        'button_success': '#c8e8c0',   # Verde menta
        'button_success_hover': '#a8d8a8',
        
        # Badge
        'badge_new': '#f8a8b8',        # Rosa pastello - badge "NUOVA"
        'badge_old': '#c8d8e0',        # Grigio azzurro - badge "ARCHIVIO"
        'badge_number': '#e8f4f8',     # Azzurro chiaro - numero circolare
    },
    
    # Nome scuola
    'SCUOLA_NOME': "IC Anna Frank - Agrigento",
    
    # Nome app
    'APP_NOME': "Bacheca Circolari",
    
    # Anni scolastici disponibili nel selettore
    # Formato: 'AAAA/AA' (es: '2024/25')
    'ANNI_SCOLASTICI': ['2024/25', '2025/26', '2026/27'],
    
    # Anno scolastico di default (deve essere presente in ANNI_SCOLASTICI)
    'ANNO_SCOLASTICO_DEFAULT': '2025/26',
    
    # Configurazione database Supabase
    'SUPABASE': {
        'TABLE_CIRCOLARI': 'circolari',
        'COLUMN_TITOLO': 'titolo',
        'COLUMN_CONTENUTO': 'contenuto',
        'COLUMN_DATA': 'data_pubblicazione',  # Colonna data nel database
        'COLUMN_PDF_URL': 'pdf_url',
        'STORAGE_BUCKET': 'documenti',
    },
    
    # Configurazione scraping
    'SCRAPING': {
        'MAX_RETRIES': 3,
        'TIMEOUT_SECONDS': 30,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'WAIT_TIME_SECONDS': 5,
    },
    
    # Configurazione UI/UX
    'UI': {
        'CARD_HOVER_EFFECT': True,
        'SHOW_BADGES': True,
        'SHOW_CIRC_NUMBER': True,
        'ITEMS_PER_PAGE': 20,  # Per eventuale paginazione futura
        'ANIMATION_DURATION': '0.2s',
        'SHADOW_INTENSITY': '0.08',  # Opacità ombre
    },
    
    # Configurazione notifiche
    'NOTIFICATIONS': {
        'SHOW_NEW_BADGE_DAYS': 7,  # Giorni per considerare una circolare "NUOVA"
        'UPDATE_NOTIFICATION': True,
    }
}

# Formati data utilizzati nell'applicazione
DATE_FORMATS = {
    'display': '%d/%m/%Y',          # Visualizzazione: 15/01/2024
    'display_full': '%d/%m/%Y alle %H:%M',  # Con orario: 15/01/2024 alle 14:30
    'database': '%Y-%m-%d %H:%M:%S', # Formato database SQL: 2024-01-15 
