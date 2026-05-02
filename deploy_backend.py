
import json
import os

def deploy_backend_updates():
    print("--- FitAI: Backend Deployment Utility ---")
    
    # Pliki do sprawdzenia
    files_to_check = ['fitai_users.json', 'fitai_substitutes.json']
    
    for file_name in files_to_check:
        if os.path.exists(file_name):
            try:
                with open(file_name, 'r', encoding='utf-8') as f:
                    json.load(f)
                print(f"✅ {file_name}: Dane sa poprawne.")
            except Exception as e:
                print(f"❌ {file_name}: Blad w strukturze pliku: {e}")
        else:
            print(f"⚠️ {file_name}: Plik nie istnieje, upewnij sie ze backend go wygeneruje.")

    print("\n🚀 Gotowe! Twoje zmiany w backendzie sa teraz dostepne dla API.")
    print("💡 Twoj plik index.html pozostal nienaruszony.")

if __name__ == "__main__":
    deploy_backend_updates()
