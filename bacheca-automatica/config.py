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
    
    # Color palette pastello
    'COLORS': {
        'primary': '#667eea',
        'secondary': '#764ba2',
        'accent': '#f093fb',
        'success': '#43e97b',
        'warning': '#ff9a9e',
        'background': '#f5f7fa',
        'card': '#ffffff'
    },
    
    # Nome scuola
    'SCUOLA_NOME': "IC Anna Frank - Agrigento",
    
    # Nome app
    'APP_NOME': "Bacheca Circolari"
}

# Formati data
DATE_FORMATS = {
    'display': '%d/%m/%Y alle %H:%M',
    'database': '%Y-%m-%d %H:%M:%S',
    'short': '%d/%m/%Y'
}
