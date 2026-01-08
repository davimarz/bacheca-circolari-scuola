# 🏫 Bacheca Circolari Automatica

Applicazione web per la gestione automatica delle circolari scolastiche.

## ✨ Nuove Funzionalità

### 1. Aggiornamento Automatico
- ✅ Controllo automatico ogni **30 minuti**
- ✅ Eliminazione automatica circolari > 30 giorni
- ✅ Aggiunta nuove circolari dal sito scuola

### 2. Design Moderno
- ✅ **Colori pastello** con gradienti eleganti
- ✅ Card animate con hover effect
- ✅ Layout responsive
- ✅ Icone e badge colorati

### 3. Documenti Allegati
- ✅ Rinomina automatica: "Doc.1", "Doc.2", ecc.
- ✅ Layout orizzontale pulsanti
- ✅ Pulsanti con gradient e ombre

### 4. Condivisione
- ✅ Pulsante condividi su ogni circolare
- ✅ Copia titolo + contenuto negli appunti
- ✅ Notifica di conferma

## 🛠️ Configurazione Scraping

### Passo 1: Modifica `scraper.py`
Apri `scraper.py` e modifica:
```python
# Riga 22 - URL del sito reale
url_sito = "https://www.tua-scuola.edu.it/circolari"
