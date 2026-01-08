files = {
    "app.py": "...contenuto app.py sopra...",
    "requirements.txt": "...contenuto requirements.txt sopra...",
    # ... aggiungi tutti i file
}

for filename, content in files.items():
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Creato: {filename}")
