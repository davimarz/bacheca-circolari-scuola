import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime, timezone
import urllib.parse
import os
import re

st.set_page_config(
    page_title="Bacheca Circolari",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    
    .stApp {
        background-color: #f8f9fa;
        font-family: 'Arial', sans-serif;
    }
    
    .main-header {
        text-align: center;
        padding: 2rem 1rem;
        background-color: #2c3e50;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
    }
    
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        color: white;
    }
    
    .school-info {
        font-size: 1.3rem;
        color: #ecf0f1;
        margin-bottom: 0.5rem;
    }
    
    .author-info {
        font-size: 0.9rem;
        color: #bdc3c7;
        font-style: italic;
    }
    
    .circolare-card {
        background-color: white;
        border-radius: 8px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-left: 4px solid #3498db;
    }
    
    .circolare-header {
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .circolare-number {
        font-size: 0.9rem;
        color: #3498db;
        font-weight: 600;
        background-color: #ecf0f1;
        padding: 2px 8px;
        border-radius: 4px;
    }
    
    .circolare-date {
        font-size: 0.85rem;
        color: #7f8c8d;
    }
    
    .circolare-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #2c3e50;
        margin-bottom: 0.8rem;
        line-height: 1.4;
    }
    
    .doc-buttons-container {
        display: flex;
        flex-direction: row;
        gap: 8px;
        flex-wrap: wrap;
        align-items: center;
    }
    
    .doc-button {
        background-color: #2c3e50;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 6px 12px;
        text-decoration: none;
        font-size: 0.85rem;
        font-weight: 500;
        transition: background-color 0.2s;
        display: inline-flex;
        align-items: center;
        gap: 5px;
        white-space: nowrap;
    }
    
    .doc-button:hover {
        background-color: #34495e;
        color: white;
        text-decoration: none;
    }
    
    .update-info {
        background-color: #ecf0f1;
        border-radius: 6px;
        padding: 0.8rem;
        margin-bottom: 1.5rem;
        text-align: center;
        font-size: 0.9rem;
        color: #2c3e50;
    }
    
    .badge {
        font-size: 0.7rem;
        padding: 2px 6px;
        border-radius: 3px;
        margin-left: 8px;
    }
    
    .badge-new {
        background-color: #2ecc71;
        color: white;
    }
    
    .badge-old {
        background-color: #95a5a6;
        color: white;
    }
    
    .empty-state {
        text-align: center;
        padding: 3rem;
        color: #7f8c8d;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <div class="main-title">🏫 Bacheca Circolari</div>
    <div class="school-info">IC Anna Frank - Agrigento</div>
    <div class="author-info">realizzato da: Davide prof. Marziano</div>
</div>
""", unsafe_allow_html=True)

@st.cache_resource
def init_supabase():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        st.error("❌ Configura SUPABASE_URL e SUPABASE_KEY")
        return None
    
    if not url.startswith("https://"):
        st.error("❌ URL deve iniziare con https://")
        return None
    
    try:
        return create_client(url, key)
    except Exception as e:
        st.error(f"❌ Errore connessione Supabase: {str(e)}")
        return None

def extract_circolare_number(titolo):
    if isinstance(titolo, str):
        titolo_pulito = str(titolo).strip()
        match = re.search(r'N\.?\s*(\d+)', titolo_pulito, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return 0

def extract_circolare_year(titolo):
    if isinstance(titolo, str):
        titolo_pulito = str(titolo).strip()
        match = re.search(r'(\d{4})[/-](\d{4})', titolo_pulito)
        if match:
            return f"{match.group(1)}-{match.group(2)}"
    
    data_attuale = datetime.now()
    if data_attuale.month >= 9:
        return f"{data_attuale.year}-{data_attuale.year + 1}"
    else:
        return f"{data_attuale.year - 1}-{data_attuale.year}"

if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.now(timezone.utc)

tempo_trascorso = (datetime.now(timezone.utc) - st.session_state.last_update).seconds / 60
tempo_rimanente = max(0, 30 - int(tempo_trascorso))

st.markdown(f"""
<div class="update-info">
    🔄 Prossimo aggiornamento automatico tra: <strong>{tempo_rimanente} minuti</strong>
</div>
""", unsafe_allow_html=True)

supabase = init_supabase()

if supabase:
    try:
        response = supabase.table('circolari')\
            .select("*")\
            .execute()
        
        df = pd.DataFrame(response.data)
        
        if not df.empty:
            df['data_pubblicazione'] = pd.to_datetime(df['data_pubblicazione'], utc=True)
            df['numero_circolare'] = df['titolo'].apply(extract_circolare_number)
            df['anno_scolastico'] = df['titolo'].apply(extract_circolare_year)
            
            anno_corrente = extract_circolare_year("")
            df_anno_corrente = df[df['anno_scolastico'] == anno_corrente]
            
            if not df_anno_corrente.empty:
                df_anno_corrente = df_anno_corrente.sort_values('numero_circolare', ascending=False)
                
                oggi = datetime.now(timezone.utc)
                
                for idx, row in df_anno_corrente.iterrows():
                    data_pub = row['data_pubblicazione']
                    is_new = (oggi - data_pub).days < 7
                    data_pub_local = data_pub.astimezone(timezone.utc).astimezone()
                    
                    badge_html = f'<span class="badge badge-{"new" if is_new else "old"}">{"NUOVA" if is_new else "ARCHIVIO"}</span>'
                    
                    numero_html = ""
                    if row['numero_circolare'] > 0:
                        numero_html = f'<span class="circolare-number">N.{row["numero_circolare"]}</span>'
                    
                    titolo_pulito = str(row['titolo']).strip()
                    
                    card_html = f'''
                    <div class="circolare-card">
                        <div class="circolare-header">
                            {numero_html}
                            <span class="circolare-date">📅 Pubblicata il {data_pub_local.strftime('%d/%m/%Y')}</span>
                        </div>
                        <div class="circolare-title">
                            {titolo_pulito} {badge_html}
                        </div>
                    '''
                    
                    if 'pdf_url' in row and pd.notna(row['pdf_url']):
                        urls = str(row['pdf_url']).split(';;;')
                        valid_urls = [url.strip() for url in urls if url.strip()]
                        
                        if valid_urls:
                            card_html += '<div class="doc-buttons-container">'
                            
                            for i, url in enumerate(valid_urls):
                                base = os.environ.get("SUPABASE_URL", "").rstrip('/')
                                if not url.startswith('http'):
                                    url = f"{base}/storage/v1/object/public/documenti/{urllib.parse.quote(url)}"
                                
                                card_html += f'<a href="{url}" target="_blank" class="doc-button">📄 Documento {i+1}</a>'
                            
                            card_html += '</div>'
                    
                    card_html += '</div>'
                    st.markdown(card_html, unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="empty-state">📭 Nessuna circolare per l\'anno scolastico {anno_corrente}</div>', unsafe_allow_html=True)
        
        else:
            st.markdown('<div class="empty-state">📭 Nessuna circolare presente nel database</div>', unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"❌ Errore nel caricamento dei dati: {str(e)}")
else:
    st.warning("⚠️ Impossibile connettersi al database.")

st.markdown("""
<div style="text-align: center; margin-top: 3rem; padding: 1rem; color: #7f8c8d; font-size: 0.8rem;">
    <hr style="border: none; height: 1px; background-color: #bdc3c7; margin: 1rem 0;">
    Bacheca Circolari IC Anna Frank - Agrigento
</div>
""", unsafe_allow_html=True)
