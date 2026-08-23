"""
batch_generate_20.py
====================
Generates music for the first 20 PDB/BMRB entries from the 100-PDB list.
Each protein gets a unique instrument palette, Raag, root note, and tempo.

Run:
    python3 batch_generate_20.py

Outputs go to:  batch_music_outputs/20_proteins/<PDB>_<BMRB>/
"""

import os, sys, json, time
import requests
import pandas as pd

# ── Configuration ─────────────────────────────────────────────────────────────
BASE_URL     = "http://localhost:8080"
OUTPUT_ROOT  = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "batch_music_outputs", "20_proteins")
CSV_100      = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "100 pdb with chemmical shift values .csv")

os.makedirs(OUTPUT_ROOT, exist_ok=True)

# ── First 20 entries from the 100-PDB list ────────────────────────────────────
df100 = pd.read_csv(CSV_100)
TARGETS = [
    {"pdb_id": str(row["pdb_id"]).strip().upper(),
     "bmrb_id": str(int(row["bmrb_id"])).strip()}
    for _, row in df100.head(20).iterrows()
]

# ── Instrument palette (MIDI General program numbers) ─────────────────────────
INSTRUMENT_PRESETS = [
    {"name": "Santoor & Bansuri",   "lead": 107, "echo":  74, "accent": 104},
    {"name": "Bansuri & Strings",   "lead":  74, "echo":  40, "accent": 110},
    {"name": "Violin & Santoor",    "lead":  40, "echo": 107, "accent": 104},
    {"name": "Shehnai & Bansuri",   "lead": 111, "echo":  74, "accent": 107},
    {"name": "Sarod & Sitar",       "lead": 105, "echo": 104, "accent":  74},
    {"name": "Sitar & Violin",      "lead": 104, "echo":  40, "accent": 110},
    {"name": "Harmonium & Flute",   "lead":  20, "echo":  74, "accent": 104},
    {"name": "Sarangi & Santoor",   "lead": 110, "echo": 107, "accent":  74},
    {"name": "Veena & Bansuri",     "lead": 106, "echo":  74, "accent": 104},
    {"name": "Clarinet & Strings",  "lead":  71, "echo":  40, "accent": 110},
    {"name": "Santoor & Shehnai",   "lead": 107, "echo": 111, "accent":  74},
    {"name": "Bansuri & Sitar",     "lead":  74, "echo": 104, "accent": 107},
    {"name": "Violin & Bansuri",    "lead":  40, "echo":  74, "accent": 104},
    {"name": "Sitar & Sarangi",     "lead": 104, "echo": 110, "accent": 107},
    {"name": "Sarod & Harmonium",   "lead": 105, "echo":  20, "accent":  74},
    {"name": "Veena & Violin",      "lead": 106, "echo":  40, "accent":  74},
    {"name": "Shehnai & Sarangi",   "lead": 111, "echo": 110, "accent": 104},
    {"name": "Harmonium & Sitar",   "lead":  20, "echo": 104, "accent":  74},
    {"name": "Sarangi & Veena",     "lead": 110, "echo": 106, "accent":  74},
    {"name": "Santoor & Violin",    "lead": 107, "echo":  40, "accent": 111},
]

# ── Raag / root note / tempo variety ─────────────────────────────────────────
MUSIC_PARAMS = [
    {"raag": "Yaman",    "root": 60, "tempo": 1.0},
    {"raag": "Bhairav",  "root": 60, "tempo": 0.8},
    {"raag": "Bhupali",  "root": 62, "tempo": 1.2},
    {"raag": "Kafi",     "root": 59, "tempo": 0.9},
    {"raag": "Malkauns", "root": 60, "tempo": 0.7},
    {"raag": "Yaman",    "root": 64, "tempo": 1.1},
    {"raag": "Bhairav",  "root": 57, "tempo": 1.0},
    {"raag": "Bhupali",  "root": 60, "tempo": 0.85},
    {"raag": "Kafi",     "root": 62, "tempo": 1.3},
    {"raag": "Malkauns", "root": 65, "tempo": 0.75},
    {"raag": "Yaman",    "root": 67, "tempo": 1.15},
    {"raag": "Bhairav",  "root": 63, "tempo": 0.95},
    {"raag": "Bhupali",  "root": 58, "tempo": 1.05},
    {"raag": "Kafi",     "root": 61, "tempo": 0.8},
    {"raag": "Malkauns", "root": 60, "tempo": 1.1},
    {"raag": "Yaman",    "root": 55, "tempo": 0.9},
    {"raag": "Bhairav",  "root": 64, "tempo": 1.25},
    {"raag": "Bhupali",  "root": 69, "tempo": 0.7},
    {"raag": "Kafi",     "root": 60, "tempo": 1.0},
    {"raag": "Malkauns", "root": 63, "tempo": 0.85},
]

# ── Frequency range variety ───────────────────────────────────────────────────
FREQ_RANGES = [
    (240, 480), (200, 440), (280, 520), (220, 460), (260, 500),
    (240, 480), (300, 560), (200, 400), (240, 520), (260, 480),
    (240, 480), (220, 480), (280, 560), (240, 460), (200, 480),
    (260, 520), (240, 480), (220, 500), (280, 480), (240, 480),
]

# ── Helpers ───────────────────────────────────────────────────────────────────
def fetch_protein(bmrb_id):
    try:
        r = requests.get(f"{BASE_URL}/api/fetch/{bmrb_id}", timeout=30)
        if r.status_code == 200:
            return r.json()
        print(f"  HTTP {r.status_code}: {r.text[:120]}")
    except Exception as e:
        print(f"  Fetch error: {e}")
    return None

def sonify_protein(dataset, pdb_id, bmrb_id, inst, music, freq_range):
    payload = {
        "dataset":          dataset,
        "pdb_id":           pdb_id,
        "bmrb_id":          bmrb_id,
        "raag_name":        music["raag"],
        "root_note":        music["root"],
        "tempo_multiplier": music["tempo"],
        "lead_inst":        inst["lead"],
        "echo_inst":        inst["echo"],
        "accent_inst":      inst["accent"],
        "enable_drone":     True,
        "enable_tabla":     True,
        "freq_min":         freq_range[0],
        "freq_max":         freq_range[1],
        "spectrometer_mhz": 750.0,
    }
    try:
        r = requests.post(f"{BASE_URL}/api/sonify", json=payload, timeout=180)
        if r.status_code == 200:
            return r.json()
        print(f"  Sonify HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"  Sonify error: {e}")
    return None

# ── Main loop ─────────────────────────────────────────────────────────────────
print(f"\n{'='*65}")
print(f"  Batch generating music for {len(TARGETS)} proteins")
print(f"  Output root: {OUTPUT_ROOT}")
print(f"{'='*65}\n")

results_log = []

for idx, target in enumerate(TARGETS):
    pdb_id  = target["pdb_id"]
    bmrb_id = target["bmrb_id"]
    inst    = INSTRUMENT_PRESETS[idx]
    music   = MUSIC_PARAMS[idx]
    frange  = FREQ_RANGES[idx]

    print(f"[{idx+1:02d}/20] PDB={pdb_id}  BMRB={bmrb_id}")
    print(f"       Instruments : {inst['name']}")
    print(f"       Raag={music['raag']}  Root={music['root']}  Tempo*{music['tempo']}")
    print(f"       Freq range  : {frange[0]}-{frange[1]} Hz")

    t0   = time.time()
    data = fetch_protein(bmrb_id)

    if not data or not data.get("rows"):
        print(f"  No data for BMRB {bmrb_id}, skipping.\n")
        results_log.append({"index": idx+1, "pdb": pdb_id, "bmrb": bmrb_id,
                            "status": "fetch_failed"})
        continue

    n_res = len(data["rows"])
    print(f"       Residues    : {n_res}")

    result = sonify_protein(
        dataset    = data["rows"],
        pdb_id     = pdb_id,
        bmrb_id    = bmrb_id,
        inst       = inst,
        music      = music,
        freq_range = frange,
    )

    elapsed = round(time.time() - t0, 1)

    if result and result.get("status") == "success":
        audio_url = result.get("audio_url", "")
        midi_url  = result.get("midi_url",  "")
        dur       = result.get("result", {}).get("total_duration", 0)
        print(f"  Done in {elapsed}s  |  Duration: {dur}s")
        print(f"       WAV  -> {BASE_URL}{audio_url}")
        print(f"       MIDI -> {BASE_URL}{midi_url}\n")
        results_log.append({
            "index":       idx + 1,
            "pdb":         pdb_id,
            "bmrb":        bmrb_id,
            "instruments": inst["name"],
            "raag":        music["raag"],
            "root_note":   music["root"],
            "tempo_mult":  music["tempo"],
            "freq_min":    frange[0],
            "freq_max":    frange[1],
            "n_residues":  n_res,
            "duration_s":  dur,
            "audio_url":   f"{BASE_URL}{audio_url}",
            "midi_url":    f"{BASE_URL}{midi_url}",
            "status":      "ok",
        })
    else:
        print(f"  Sonification failed after {elapsed}s\n")
        results_log.append({"index": idx+1, "pdb": pdb_id, "bmrb": bmrb_id,
                            "status": "sonify_failed"})

    if idx < len(TARGETS) - 1:
        time.sleep(1)   # be polite to BMRB API

# ── Save summary log ──────────────────────────────────────────────────────────
log_path = os.path.join(OUTPUT_ROOT, "batch_log.json")
with open(log_path, "w") as f:
    json.dump(results_log, f, indent=2)

success_count = sum(1 for r in results_log if r.get("status") == "ok")
print(f"\n{'='*65}")
print(f"  Complete: {success_count}/{len(TARGETS)} proteins sonified successfully.")
print(f"  Log saved -> {log_path}")
print(f"{'='*65}\n")

print(f"{'#':>3}  {'PDB':>5}  {'BMRB':>6}  {'Instruments':<24}  {'Raag':<10}  {'Dur(s)':>7}  Status")
print("-" * 75)
for r in results_log:
    icon = "OK" if r.get("status") == "ok" else "FAIL"
    print(
        f"{r.get('index','-'):>3}  "
        f"{r.get('pdb','-'):>5}  "
        f"{r.get('bmrb','-'):>6}  "
        f"{r.get('instruments', r.get('status','-')):<24}  "
        f"{r.get('raag','-'):<10}  "
        f"{str(r.get('duration_s','-')):>7}  "
        f"{icon}"
    )
