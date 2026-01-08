# Bacheca Circolari Automatica

Webapp automatica per la pubblicazione delle circolari scolastiche.

## Funzionalità
- Visualizzazione circolari in tempo reale
- Collegamento a documenti PDF
- Aggiornamento automatico da Supabase

## Installazione Locale
1. Clona il repository
2. Crea ambiente virtuale: `python -m venv venv`
3. Attiva: `venv\Scripts\activate` (Windows) o `source venv/bin/activate` (Mac/Linux)
4. Installa dipendenze: `pip install -r requirements.txt`
5. Crea file `.env` con le credenziali Supabase
6. Avvia: `streamlit run app.py`

## Deploy su Render
1. Push su GitHub
2. Crea Web Service su Render
3. Configura:
   - Root Directory: `bacheca-automatica`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
4. Aggiungi variabili d'ambiente:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `PORT=10000`

## Tecnologie
- Streamlit
- Supabase
- Python
- Render
