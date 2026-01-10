print("=" * 60)
print("🤖 TEST IMPORTAZIONI - AVVIATO")
print("=" * 60)

print("📦 Provo a importare le librerie...")

try:
    from selenium import webdriver
    print("✅ selenium importato")
except ImportError as e:
    print(f"❌ selenium: {e}")

try:
    import psycopg
    print("✅ psycopg importato")
except ImportError as e:
    print(f"❌ psycopg: {e}")

try:
    import chromedriver_autoinstaller
    print("✅ chromedriver_autoinstaller importato")
except ImportError as e:
    print(f"❌ chromedriver_autoinstaller: {e}")

print("\n" + "=" * 60)
print("🎉 TEST COMPLETATO")
print("=" * 60)
