[file name]: config.py
[file content begin]
"""
Configurazioni dell'applicazione
"""

# Impostazioni app
CONFIG = {
    # Intervallo aggiornamento automatico (minuti)
    'UPDATE_INTERVAL': 30,
    
    # Giorni di validità circolari
    'CIRCOLARI_VALIDITA_GIORNI': 30,
    
    # URL sito scuola (DA MODIFICARE)
    'URL_SITO_SCUOLA': "https://www.icannafrankag.edu.it/circolari",
    
    # Fuso orario Italia (GMT+1, GMT+2 in ora legale)
    'TIMEZONE_ITALIA': 1,
    
    # COLORI PASTELLO (dallo screenshot 3.png)
    'COLORS': {
        'primary': '#a8d8ea',      # Azzurro pastello
        'secondary': '#f8a8b8',    # Rosa pastello
        'accent': '#fff9f0',       # Beige chiaro
        'success': '#c8e8c0',      # Verde menta
        'warning': '#f8d8a8',      # Giallo pesca
        'background': '#f0f9f4',   # Verde menta chiaro (sfondo)
        'card': '#fffefb',         # Beige molto chiaro (card)
        'text_primary': '#4a6572', # Blu-grigio scuro
        'text_secondary': '#6a7b8c', # Blu-grigio medio
        'border': '#e8e2d6'        # Beige bordi
    },
    
    # Nome scuola
    'SCUOLA_NOME': "IC Anna Frank - Agrigento",
    
    # Nome app
    'APP_NOME': "Bacheca Circolari",
    
    # Anni scolastici disponibili
    'ANNI_SCOLASTICI': ['2024/25', '2025/26', '2026/27']
}

# Formati data
DATE_FORMATS = {
    'display': '%d/%m/%Y alle %H:%M',
    'database': '%Y-%m-%d %H:%M:%S',
    'short': '%d/%m/%Y'
}
[file content end]
