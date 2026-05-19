import os
import sys
import requests

# Změňte API_URL podle potřeby
API_URL = os.environ.get("S3_GATEWAY_URL", "http://localhost:8000")
VOLUMES_DIR = os.environ.get("VOLUMES_DIR", "volumes")

def compact_volume(volume_id: int):
    """
    Zkomprimuje konkrétní svazek přesunutím všech nesmazaných souborů k sobě.
    """
    print(f"Získávám seznam souborů pro svazek {volume_id} z {API_URL}...")
    resp = requests.get(f"{API_URL}/admin/volumes/{volume_id}/files")
    if resp.status_code != 200:
        print(f"Chyba při stahování seznamu souborů: {resp.text}")
        return
    
    files = resp.json()
    if not files:
        print(f"Žádné nesmazané soubory pro svazek {volume_id}. Soubor může být prázdný.")
        return

    # Seřadit podle existujícího offsetu pro optimálnější čtení (i když to není nutné)
    files.sort(key=lambda x: x["offset"] if x["offset"] is not None else 0)

    old_file_path = os.path.join(VOLUMES_DIR, f"volume_{volume_id}.dat")
    new_file_path = os.path.join(VOLUMES_DIR, f"volume_{volume_id}_compacted.dat")

    if not os.path.exists(old_file_path):
        print(f"Soubor svazku {old_file_path} nebyl nalezen.")
        return

    print(f"Nalezeno {len(files)} souborů k zachování. Začínám kompakci do {new_file_path}...")

    with open(old_file_path, "rb") as old_f, open(new_file_path, "wb") as new_f:
        for file_info in files:
            file_id = file_info["id"]
            old_offset = file_info["offset"]
            size = file_info["size"]
            
            if old_offset is None or size is None:
                print(f"Přeskakuji soubor {file_id}, nemá offset nebo size.")
                continue

            # Čtení ze staré pozice
            old_f.seek(old_offset)
            data = old_f.read(size)
            
            # Zápis na novou pozici
            new_offset = new_f.tell()
            new_f.write(data)
            
            # Odeslání updatu na S3 Gateway
            print(f"Soubor {file_id} přesunut z pozice {old_offset} na {new_offset}. Aktualizuji S3 Gateway...")
            update_resp = requests.patch(f"{API_URL}/admin/files/{file_id}", json={
                "offset": new_offset,
                "volume_id": volume_id,
            })
            
            if update_resp.status_code != 200:
                print(f"Chyba při aktualizaci souboru {file_id}: {update_resp.text}")
                
    # 5. Odstranění starého a přejmenování zkompaktněného
    print("Nahrazuji starý soubor zkompaktovanou verzí...")
    try:
        os.remove(old_file_path)
    except OSError as e:
        print(f"Chyba při mazání starého souboru: {e}")
        # Pokračujeme, ale s rizikem, že přejmenování selže (na Windows určitě, na Linuxu možná ne)
        
    try:
        os.rename(new_file_path, old_file_path)
        print(f"Kompakce svazku {volume_id} byla úspěšně dokončena.")
    except OSError as e:
        print(f"Chyba při přejmenování souboru zkompaktovaného svazku: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Použití: python compact.py <volume_id>")
        sys.exit(1)
    
    try:
        vol_id = int(sys.argv[1])
        compact_volume(vol_id)
    except ValueError:
        print("Prosím zadejte platné ID svazku jako číslo.")
        sys.exit(1)
