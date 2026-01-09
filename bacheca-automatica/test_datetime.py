"""
Test per verificare il corretto funzionamento delle date
"""

from datetime import datetime, timedelta, timezone
import pandas as pd

def test_date_functions():
    print("=" * 50)
    print("TEST FUNZIONI DATE")
    print("=" * 50)
    
    # Test 1: Data naive vs aware
    print("\n1. Test naive vs aware:")
    naive_date = datetime(2024, 1, 1)
    aware_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
    print(f"   Naive: {naive_date}")
    print(f"   Aware: {aware_date}")
    print(f"   naive.tzinfo: {naive_date.tzinfo}")
    print(f"   aware.tzinfo: {aware_date.tzinfo}")
    
    # Test 2: Conversione
    print("\n2. Test conversione:")
    converted = naive_date.replace(tzinfo=timezone.utc)
    print(f"   Naive -> Aware: {converted}")
    print(f"   Sono uguali? {converted == aware_date}")
    
    # Test 3: Confronto corretto
    print("\n3. Test confronto:")
    now_utc = datetime.now(timezone.utc)
    week_ago = now_utc - timedelta(days=7)
    month_ago = now_utc - timedelta(days=31)
    
    print(f"   Ora UTC: {now_utc}")
    print(f"   7 giorni fa: {week_ago}")
    print(f"   31 giorni fa: {month_ago}")
    print(f"   7 giorni fa < Ora? {week_ago < now_utc}")
    print(f"   31 giorni fa < Ora? {month_ago < now_utc}")
    
    # Test 4: Pandas con timezone
    print("\n4. Test Pandas:")
    dates = [
        "2024-01-01 10:00:00",
        "2024-01-15 14:30:00",
        "2023-12-01 09:00:00"
    ]
    
    df = pd.DataFrame({'date': dates})
    df['date_utc'] = pd.to_datetime(df['date'], utc=True)
    print(f"   Date convertite:\n{df['date_utc']}")
    
    # Test 5: Fuso orario Italia
    print("\n5. Test fuso orario Italia:")
    italy_tz = timezone(timedelta(hours=1))  # GMT+1
    date_italy = now_utc.astimezone(italy_tz)
    print(f"   UTC: {now_utc.strftime('%Y-%m-%d %H:%M')}")
    print(f"   Italia: {date_italy.strftime('%Y-%m-%d %H:%M')}")
    
    # Test 6: Il problema specifico - replace() su timezone-aware
    print("\n6. Test problema specifico (replace() su aware):")
    aware_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
    print(f"   Data aware originale: {aware_date}")
    
    try:
        # Questo causa l'errore tz_convert()
        bad_conversion = aware_date.replace(tzinfo=timezone.utc)
        print(f"   DOPO replace(tzinfo=...): {bad_conversion}")
    except Exception as e:
        print(f"   ❌ Errore con replace(): {type(e).__name__}: {e}")
    
    # Soluzione corretta
    print(f"\n   Soluzione corretta (astimezone()):")
    try:
        correct_conversion = aware_date.astimezone()
        print(f"   DOPO astimezone(): {correct_conversion}")
        print(f"   ✅ Funziona correttamente!")
    except Exception as e:
        print(f"   ❌ Errore con astimezone(): {type(e).__name__}: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Tutti i test completati!")

if __name__ == "__main__":
    test_date_functions()
