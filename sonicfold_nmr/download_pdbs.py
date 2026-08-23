import os
import shutil
from backend_app import fetch_protein_data

pdbs = """1G8K 1G8L 1G8M 1G8N 1G8P 1G8Q 1G8R 1G8S 1G8T 1G8U
1G8V 1G8W 1G8X 1G8Y 1G8Z 1G9A 1G9B 1G9C 1G9D 1G9E
1G9F 1G9G 1G9H 1G9I 1G9J 1G9K 1G9L 1G9M 1G9N 1G9O
1G9P 1G9Q 1G9R 1G9S 1G9T 1G9U 1G9V 1G9W 1G9X 1G9Y
1G9Z 1GA0 1GA1 1GA2 1GA3 1GA4 1GA5 1GA6 1GA7 1GA8
1GA9 1GAA 1GAB 1GAC 1GAD 1GAE 1GAF 1GAG 1GAH 1GAI
1GAJ 1GAK 1GAL 1GAM 1GAN 1GAO 1GAP 1GAQ 1GAR 1GAS""".split()
folder = "downloaded_pdb_csvs"
os.makedirs(folder, exist_ok=True)

for pdb in pdbs:
    print(f"Fetching {pdb}...")
    res = fetch_protein_data(pdb)
    if isinstance(res, dict) and res.get("status") == "success":
        csv_path = f"outputs/{pdb}_dataset.csv"
        if os.path.exists(csv_path):
            shutil.copy(csv_path, os.path.join(folder, f"{pdb}_dataset.csv"))
            print(f"Successfully saved {pdb} to {folder}")
        else:
            print(f"Warning: could not find {csv_path}")
    else:
        print(f"Failed to fetch {pdb}: {res}")
