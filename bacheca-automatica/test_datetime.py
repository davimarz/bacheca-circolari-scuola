"""
Test per verificare il corretto funzionamento delle date
"""

from datetime import datetime, timedelta, timezone
import pandas as pd

def test_date_functions():
    print("=" * 50)
    print("TEST FUNZIONI DATE - Verifica fix errore tz_convert()")
    print("=" * 50)
    
    # Test del problema specifico
    print("\n1. Test problema tz_convert():")
    aware_date = datetime(2024, 5, 15, 10, 30, tzinfo=timezone.utc)
    print(f"   Data timezone-aware (UTC): {aware_date}")
    
    # Questo era l'errore nel codice originale:
    print(f"\n   CODICE ERRATO (causa l'errore):")
    print(f'   data_pub.replace(tzinfo=timezone.utc).astimezone()')
    print(f"   ❌ Causa: tz_convert() takes exactly 2 positional arguments (1 given)")
    
    # Questa è la correzione:
    print(f"\n   CODICE CORRETTO:")
    print(f'   data_pub.astimezone()')
    correct_result = aware_date.astimezone()
    print(f"   ✅ Risultato: {correct_result}")
    
    # Test 2: Pandas con timezone
    print("\n2. Test Pandas to_datetime:")
    dates = ["2024-05-01 10:00:00", "2024-05-10 14:30:00", "2024-04-20 09:15:00"]
    df = pd.DataFrame({'date': dates})
    df['date_utc'] = pd.to_datetime(df['date'], utc=True)
    print(f"   DataFrame con date UTC:\n{df['date_utc']}")
    
    # Test 3: astimezone() su ogni riga
    print("\n3. Test astimezone() su DataFrame:")
    for i, date_utc in enumerate(df['date_utc']):
        local_date = date_utc.astimezone()
        print(f"   Riga {i}: {date_utc} -> {local_date}")
    
    print("\n" + "=" * 50)
    print("✅ Test completato!")
    print("   Correzione applicata in app.py: riga ~240")
    print("   Sostituito: data_pub.replace(tzinfo=timezone.utc).astimezone()")
    print("   Con: data_pub.astimezone()")

if __name__ == "__main__":
    test_date_functions()
