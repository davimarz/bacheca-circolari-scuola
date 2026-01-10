import os
print("=" * 60)
print("🤖 TEST BASICO - AVVIATO")
print("=" * 60)

# Test variabili
print("📝 Variabili d'ambiente:")
print(f"  ARGO_USER: {'✅' if os.environ.get('ARGO_USER') else '❌'}")
print(f"  ARGO_PASS: {'✅' if os.environ.get('ARGO_PASS') else '❌'}")
print(f"  DB_PASSWORD: {'✅' if os.environ.get('DB_PASSWORD') else '❌'}")

# Test import
print("\n📦 Test import librerie...")
try:
    from selenium import webdriver
    print("  ✅ selenium")
except ImportError as e:
    print(f"  ❌ selenium: {e}")

try:
    import psycopg
    print("  ✅ psycopg")
except ImportError as e:
    print(f"  ❌ psycopg: {e}")

print("\n" + "=" * 60)
print("🎉 TEST COMPLETATO")
print("=" * 60)
