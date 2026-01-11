print("=" * 60)
print("🎯 TEST FINALE DEFINITIVO")
print("=" * 60)

import os
import sys

print("📋 1. SISTEMA OPERATIVO E PYTHON")
print(f"   Python: {sys.version}")
print(f"   OS: {os.name}")

print("\n🔑 2. VARIABILI D'AMBIENTE (Render)")
env_vars = ['ARGO_USER', 'ARGO_PASS', 'DB_PASSWORD']
all_ok = True

for var in env_vars:
    value = os.environ.get(var)
    if value:
        print(f"   ✅ {var}: configurata")
    else:
        print(f"   ❌ {var}: MANCANTE!")
        all_ok = False

if not all_ok:
    print("\n⚠️  Configura le variabili su Render:")
    print("   Render → Environment → Add Environment Variable")
    exit(1)

print("\n📦 3. LIBRERIE INSTALLATE")
libraries = [
    ('selenium', 'from selenium import webdriver'),
    ('psycopg', 'import psycopg'),
    ('chromedriver_autoinstaller', 'import chromedriver_autoinstaller')
]

for lib_name, import_cmd in libraries:
    try:
        exec(import_cmd)
        print(f"   ✅ {lib_name}: installata correttamente")
    except ImportError as e:
        print(f"   ❌ {lib_name}: NON installata - {e}")
        all_ok = False

print("\n🌐 4. TEST CONNESSIONE INTERNET")
try:
    import socket
    socket.create_connection(("www.google.com", 80), timeout=5)
    print("   ✅ Connessione internet: OK")
except:
    print("   ❌ Connessione internet: FALLITA")

print("\n" + "=" * 60)
if all_ok:
    print("🎉 TUTTI I TEST SUPERATI CON SUCCESSO!")
    print("✅ Il sistema è pronto per lo scraping")
    print("✅ Requirements.txt è CORRETTO")
    print("✅ Puoi usare leggi_circolari.py completo")
else:
    print("⚠️  Alcuni test falliti")
    print("📋 Controlla:")
    print("   1. requirements.txt su GitHub")
    print("   2. Variabili d'ambiente su Render")
    print("   3. Build Command su Render")
print("=" * 60)
