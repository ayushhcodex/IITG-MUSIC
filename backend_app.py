import os
import json
import uuid
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
import requests
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import sonify

app = FastAPI(title="Cosmic Raga: Molecular Sonification Webtool")

# ──────────────────────────────────────────────────────────────────────────────
# Load the 100-PDB chemical shift lookup table at startup.
# File: "100 pdb with chemmical shift values .csv"
# Columns: pdb_id, bmrb_id, proton_1H_shift_count, nitrogen_15N_shift_count, total_H_N_shifts
# This gives us a pdb_id ↔ bmrb_id mapping so all 100 entries are routable
# without hitting the RCSB API every time.
# ──────────────────────────────────────────────────────────────────────────────
_PDB100_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "100 pdb with chemmical shift values .csv")

PDB_TO_BMRB: Dict[str, str] = {}   # pdb_id (upper) → bmrb_id (str)
BMRB_TO_PDB: Dict[str, str] = {}   # bmrb_id (str)  → pdb_id (upper)

try:
    _df100 = pd.read_csv(_PDB100_CSV)
    for _, _row in _df100.iterrows():
        _pdb  = str(_row["pdb_id"]).strip().upper()
        _bmrb = str(int(_row["bmrb_id"])).strip()
        if _pdb and _bmrb:
            PDB_TO_BMRB[_pdb]  = _bmrb
            BMRB_TO_PDB[_bmrb] = _pdb
    print(f"[startup] Loaded {len(PDB_TO_BMRB)} PDB↔BMRB mappings from local CSV.")
except Exception as _e:
    print(f"[startup] WARNING: Could not load 100-PDB CSV: {_e}")

# Ensure outputs directory exists
OUTPUTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(STATIC_DIR, exist_ok=True)

# Mount outputs for downloading audio, MIDI, CSV
app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")

class SonifyRequest(BaseModel):
    dataset: List[Dict[str, Any]]
    raag_name: str = "Yaman"
    root_note: int = 60
    tempo_multiplier: float = 1.0
    lead_inst: int = 107
    echo_inst: int = 74
    accent_inst: int = 104
    enable_drone: bool = True
    enable_tabla: bool = True
    pdb_id: str = "1DMB"
    bmrb_id: str = ""        # filled by frontend from the fetch response
    spectrometer_mhz: float = 750.0


# ──────────────────────────────────────────────────────────────────────────────
# Helper: create the per-protein run directory and return (dir_path, url_prefix)
#
# Folder layout:
#   outputs/
#     {PDB}_BMRB{BMRB}/            ← protein root (one per protein)
#       dataset.csv                  ← latest input dataset (overwritten each run)
#       run_YYYYMMDD_HHMMSS/        ← one subfolder per pipeline run
#         input.csv                  ← exact data fed into sonify this run
#         timeline.csv               ← note-by-note output (sequence, svara, time…)
#         music.mid
#         music.wav
#         run_info.json              ← raag, root_note, tempo, timestamp, etc.
# ──────────────────────────────────────────────────────────────────────────────
def make_protein_run_dir(pdb_id: str, bmrb_id: str):
    """Return (run_dir_abs_path, url_prefix_relative_to_/outputs/)."""
    import datetime
    pdb_clean  = pdb_id.strip().upper()  if pdb_id  else "UNKNOWN"
    bmrb_clean = bmrb_id.strip()         if bmrb_id else ""

    # If we know the BMRB ID (either passed in or from our local lookup), use it
    if not bmrb_clean:
        bmrb_clean = PDB_TO_BMRB.get(pdb_clean, "")

    # Protein folder name:  1UJX_BMRB10104  or just  1UJX  if BMRB unknown
    protein_folder = f"{pdb_clean}_BMRB{bmrb_clean}" if bmrb_clean else pdb_clean
    protein_dir    = os.path.join(OUTPUTS_DIR, protein_folder)
    os.makedirs(protein_dir, exist_ok=True)

    # Run subfolder: run_20260721_133856
    ts      = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(protein_dir, f"run_{ts}")
    os.makedirs(run_dir, exist_ok=True)

    url_prefix = f"/outputs/{protein_folder}/run_{ts}"
    return run_dir, protein_dir, url_prefix, protein_folder

KNOWN_SPECTROMETER_MHZ = {
    "34058": 700.0, "34308": 800.0, "36179": 600.0, "36180": 800.0,
    "36185": 600.0, "50007": 500.0, "50027": 600.0, "50088": 950.0,
    "50114": 950.0, "50202": 700.0, "50218": 700.0, "50219": 700.0,
    "50263": 600.0, "50264": 600.0, "50265": 600.0
}

PRESETS = {
    "25237": {
        "title": "Maltose Binding Protein (MBP)",
        "bmrb_id": "25237",
        "pdb_id": "1DMB",
        "description": "Large multi-domain periplasmic binding protein with prominent Alpha Helices and Beta Sheets.",
        "file": None
    },
    "27859": {
        "title": "Human Carbonic Anhydrase II",
        "pdb_id": "1CA2",
        "description": "Essential human zinc metalloenzyme with extensive Beta-Sheet central core.",
        "file": None
    },
    "34308": {
        "title": "Human Carbonic Anhydrase II (Native)",
        "pdb_id": "6HD2",
        "description": "Active-site conformational dynamics of carbonic anhydrase under native conditions.",
        "file": None
    }
}

@app.get("/api/presets")
def get_presets():
    return {"presets": PRESETS}

def get_pdb_ss_map(pdb_code: str) -> Dict[int, str]:
    if not pdb_code or len(pdb_code) != 4:
        return {}
    ss_map = {}
    try:
        url = f"https://files.rcsb.org/download/{pdb_code.upper()}.pdb"
        r = requests.get(url, timeout=6)
        if r.status_code == 200:
            for line in r.text.splitlines():
                if line.startswith("HELIX"):
                    try:
                        start_seq = int(line[21:25].strip())
                        end_seq = int(line[33:37].strip())
                        for s in range(start_seq, end_seq + 1):
                            ss_map[s] = "Alpha helix"
                    except ValueError:
                        pass
                elif line.startswith("SHEET"):
                    try:
                        start_seq = int(line[22:26].strip())
                        end_seq = int(line[33:37].strip())
                        for s in range(start_seq, end_seq + 1):
                            ss_map[s] = "Beta sheet"
                    except ValueError:
                        pass
    except Exception as e:
        print(f"Failed fetching PDB ss_map for {pdb_code}: {e}")
    return ss_map

def fetch_real_bmrb_data(bmrb_id: str) -> Optional[Dict[str, Any]]:
    try:
        url = f"https://api.bmrb.io/v2/entry/{bmrb_id}?format=json"
        r = requests.get(url, timeout=12)
        if r.status_code != 200:
            return None
        data = r.json()
        entry_dict = data.get(str(bmrb_id))
        if not entry_dict and isinstance(data, dict) and len(data) > 0:
            entry_dict = list(data.values())[0]
        if not entry_dict or not isinstance(entry_dict, dict):
            return None
            
        saveframes = entry_dict.get("saveframes", [])
        
        # 1. Extract PDB ID
        pdb_id = None
        for sf in saveframes:
            for loop in sf.get("loops", []):
                cat = loop.get("category", "")
                tags = loop.get("tags", [])
                if cat == "_Related_entries" and "Database_name" in tags and "Database_accession_code" in tags:
                    db_idx = tags.index("Database_name")
                    code_idx = tags.index("Database_accession_code")
                    for row in loop.get("data", []):
                        if len(row) > max(db_idx, code_idx) and str(row[db_idx]).strip().upper() == "PDB":
                            cand = str(row[code_idx]).strip().upper()
                            if len(cand) == 4 and cand != ".":
                                pdb_id = cand
                                break
                elif cat == "_Entity_db_link" and "Database_code" in tags and "Accession_code" in tags:
                    db_idx = tags.index("Database_code")
                    code_idx = tags.index("Accession_code")
                    for row in loop.get("data", []):
                        if len(row) > max(db_idx, code_idx) and str(row[db_idx]).strip().upper() == "PDB":
                            cand = str(row[code_idx]).strip().upper()
                            if len(cand) == 4 and cand != "." and not pdb_id:
                                pdb_id = cand
                                break
            if pdb_id:
                break
                
        # Fallback check for presets
        if not pdb_id and str(bmrb_id) in PRESETS:
            pdb_id = PRESETS[str(bmrb_id)]["pdb_id"]
            
        # 2. Extract title
        title = f"BMRB Entry {bmrb_id}"
        if str(bmrb_id) in PRESETS:
            title = PRESETS[str(bmrb_id)]["title"]
        else:
            for sf in saveframes:
                if sf.get("category") == "entry_information":
                    for tag_pair in sf.get("tags", []):
                        if len(tag_pair) == 2 and tag_pair[0] == "Title" and tag_pair[1] != ".":
                            title = str(tag_pair[1]).strip().split("\n")[0]
                            break
                            
        # 3. Extract assigned chemical shifts (_Atom_chem_shift)
        residue_shifts = {}
        for sf in saveframes:
            if sf.get("category") == "assigned_chemical_shifts" or str(sf.get("name", "")).startswith("chemical_shift_set"):
                for loop in sf.get("loops", []):
                    if loop.get("category") == "_Atom_chem_shift":
                        tags = loop.get("tags", [])
                        seq_idx = tags.index("Seq_ID") if "Seq_ID" in tags else (tags.index("Comp_index_ID") if "Comp_index_ID" in tags else -1)
                        comp_idx = tags.index("Comp_ID") if "Comp_ID" in tags else -1
                        atom_idx = tags.index("Atom_ID") if "Atom_ID" in tags else -1
                        val_idx = tags.index("Val") if "Val" in tags else -1
                        
                        if seq_idx != -1 and comp_idx != -1 and atom_idx != -1 and val_idx != -1:
                            for row in loop.get("data", []):
                                if len(row) > max(seq_idx, comp_idx, atom_idx, val_idx):
                                    try:
                                        seq_num = int(row[seq_idx])
                                        val = float(row[val_idx])
                                        aa = str(row[comp_idx]).strip().upper()
                                        atom = str(row[atom_idx]).strip().upper()
                                        
                                        if seq_num not in residue_shifts:
                                            residue_shifts[seq_num] = {"seq": seq_num, "aa": aa, "H": [], "N": [], "CA": [], "CB": []}
                                        if atom in ["H", "HN", "H1"]:
                                            residue_shifts[seq_num]["H"].append(val)
                                        elif atom == "N":
                                            residue_shifts[seq_num]["N"].append(val)
                                        elif atom == "CA":
                                            residue_shifts[seq_num]["CA"].append(val)
                                        elif atom == "CB":
                                            residue_shifts[seq_num]["CB"].append(val)
                                    except (ValueError, TypeError):
                                        continue
                                        
        if not residue_shifts:
            return None
            
        ss_map = get_pdb_ss_map(pdb_id or "")
        
        # Get true spectrometer frequency if known, else default to 750 MHz
        spec_mhz = KNOWN_SPECTROMETER_MHZ.get(str(bmrb_id), 750.0)
        
        rows = []
        for seq_num in sorted(residue_shifts.keys()):
            res = residue_shifts[seq_num]
            aa = res["aa"]
            h_vals = res["H"]
            n_vals = res["N"]
            
            if h_vals and n_vals:
                h_ppm = float(np.mean(h_vals))
                n_ppm = float(np.mean(n_vals))
            elif h_vals:
                h_ppm = float(np.mean(h_vals))
                n_ppm = 118.0
            elif n_vals:
                h_ppm = 8.0
                n_ppm = float(np.mean(n_vals))
            else:
                h_ppm = 8.0
                n_ppm = 118.0
                
            # Pre-compute Final_Freq using the true known spectrometer MHz.
            h_hz = h_ppm * spec_mhz
            n_hz = n_ppm * (spec_mhz / 10.0)
            final_freq = round(float(np.sqrt(h_hz * n_hz)), 2)
            
            if seq_num in ss_map:
                struct = ss_map[seq_num]
            else:
                ca_vals = res["CA"]
                cb_vals = res["CB"]
                if ca_vals and cb_vals:
                    diff = float(np.mean(ca_vals)) - float(np.mean(cb_vals))
                    if diff > 20.0:
                        struct = "Alpha helix"
                    elif diff < 14.0:
                        struct = "Beta sheet"
                    else:
                        struct = "Random coil"
                else:
                    struct = "Random coil"
                    
            rows.append({
                "sequence": seq_num,
                "chem_comp_ID": aa,
                "h_ppm": round(h_ppm, 4),    # raw 1H chemical shift (ppm)
                "n_ppm": round(n_ppm, 4),    # raw 15N chemical shift (ppm)
                "Final_Freq": final_freq,    # calculated at true spectrometer MHz
                "Secondary Structure": struct
            })
            
        auto_csv = os.path.join(OUTPUTS_DIR, f"{bmrb_id}_dataset.csv")
        pd.DataFrame(rows).to_csv(auto_csv, index=False)
        
        return {
            "status": "success",
            "pdb_id": pdb_id or (PRESETS[str(bmrb_id)]["pdb_id"] if str(bmrb_id) in PRESETS else ""),
            "bmrb_id": str(bmrb_id),
            "title": f"{title} (BMRB {bmrb_id}" + (f" / PDB {pdb_id})" if pdb_id else ")"),
            "rows": rows,
            "csv_url": f"/outputs/{bmrb_id}_dataset.csv"
        }
    except Exception as e:
        print(f"Error fetching real BMRB data for {bmrb_id}: {e}")
        return None

@app.get("/api/fetch/{identifier}")
def fetch_protein_data(identifier: str):
    identifier_clean = identifier.strip().upper()

    # ── STEP 1: Fast path — BMRB 6188 / PDB 1ST7 (local CSV) ─────────────────
    if identifier_clean in ["6188", "1ST7"]:
        csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "6188_simulated_hsqc_backbone_example_music.csv")
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            rows = []
            for idx, row in df.iterrows():
                # Store raw PPM values so the sonify endpoint can recompute
                # Final_Freq at the user's actual spectrometer frequency.
                h_ppm = float(row.get("X_shift", 8.0))   # 1H chemical shift in ppm
                n_ppm = float(row.get("Y_shift", 118.0))  # 15N chemical shift in ppm
                # Default Final_Freq at 750 MHz for display; overwritten at sonify time
                final_freq_750 = round(float(np.sqrt(h_ppm * 750.0 * n_ppm * 75.0)), 2)
                rows.append({
                    "sequence": int(row.get("sequence", idx + 1)),
                    "chem_comp_ID": str(row.get("chem_comp_ID", "ALA")),
                    "h_ppm": round(h_ppm, 4),
                    "n_ppm": round(n_ppm, 4),
                    "Final_Freq": final_freq_750,
                    "Secondary Structure": "Alpha helix" if idx % 3 == 0 else (
                        "Beta sheet" if idx % 3 == 1 else "Random coil")
                })
            auto_csv = os.path.join(OUTPUTS_DIR, "6188_dataset.csv")
            pd.DataFrame(rows).to_csv(auto_csv, index=False)
            pd.DataFrame(rows).to_csv(os.path.join(OUTPUTS_DIR, "1ST7_dataset.csv"), index=False)
            return {
                "status": "success",
                "pdb_id": "1ST7",
                "bmrb_id": "6188",
                "title": "Yeast ACBP (BMRB 6188 / PDB 1ST7)",
                "rows": rows,
                "csv_url": "/outputs/6188_dataset.csv"
            }

    # ── STEP 1.5: Fast path for known perfectly-cleaned Backbone CSVs ──────────
    if identifier_clean in KNOWN_SPECTROMETER_MHZ:
        csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "backbone_csv_downloaded",
                                f"{identifier_clean}_simulated_hsqc_backbone.csv")
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            spec_mhz = KNOWN_SPECTROMETER_MHZ[identifier_clean]
            rows = []
            for idx, row in df.iterrows():
                h_ppm = float(row.get("X_shift", 8.0))
                n_ppm = float(row.get("Y_shift", 118.0))
                
                h_hz = h_ppm * spec_mhz
                n_hz = n_ppm * (spec_mhz / 10.0)
                final_freq = round(float(np.sqrt(h_hz * n_hz)), 2)
                
                rows.append({
                    "sequence": int(row.get("sequence", idx + 1)),
                    "chem_comp_ID": str(row.get("chem_comp_ID", "ALA")),
                    "h_ppm": round(h_ppm, 4),
                    "n_ppm": round(n_ppm, 4),
                    "Final_Freq": final_freq,
                    "Secondary Structure": "Alpha helix" if idx % 3 == 0 else (
                        "Beta sheet" if idx % 3 == 1 else "Random coil")
                })
            auto_csv = os.path.join(OUTPUTS_DIR, f"{identifier_clean}_dataset.csv")
            pd.DataFrame(rows).to_csv(auto_csv, index=False)
            
            # Find PDB ID if it's a preset
            pdb_id = PRESETS.get(identifier_clean, {}).get("pdb_id", "")
            title = f"BMRB {identifier_clean} (Local Backbone)"
            if identifier_clean in PRESETS:
                title = f"{PRESETS[identifier_clean]['title']} (BMRB {identifier_clean} / PDB {pdb_id})"
                
            return {
                "status": "success",
                "pdb_id": pdb_id,
                "bmrb_id": identifier_clean,
                "title": title,
                "spectrometer_mhz": spec_mhz,
                "rows": rows,
                "csv_url": f"/outputs/{identifier_clean}_dataset.csv"
            }

    # ── STEP 2: Check hard-coded presets (bmrb_id or pdb_id) ─────────────────
    for bmrb_key, preset_data in PRESETS.items():
        if identifier_clean == bmrb_key or identifier_clean == preset_data["pdb_id"]:
            res = fetch_real_bmrb_data(bmrb_key)
            if res and res.get("status") == "success":
                res["pdb_id"] = preset_data["pdb_id"]
                res["title"] = (f"{preset_data['title']} "
                                f"(BMRB {bmrb_key} / PDB {preset_data['pdb_id']})")
                return res

    # ── STEP 3: Digits-only BMRB ID ───────────────────────────────────────────
    if identifier_clean.isdigit():
        # Check if this BMRB ID is in our 100-PDB lookup table
        known_pdb = BMRB_TO_PDB.get(identifier_clean, "")
        res = fetch_real_bmrb_data(identifier_clean)
        if res and res.get("status") == "success":
            # Attach the PDB ID from our local lookup if the API didn't find one
            if not res.get("pdb_id") and known_pdb:
                res["pdb_id"] = known_pdb
                # Write a PDB-named copy so fetch-by-pdb also finds cached data
                pdb_csv = os.path.join(OUTPUTS_DIR, f"{known_pdb}_dataset.csv")
                pd.DataFrame(res["rows"]).to_csv(pdb_csv, index=False)
            return res
        else:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": (f"No assigned NMR chemical shift data available "
                                f"in BMRB for entry ID '{identifier_clean}'.")
                }
            )

    # ── STEP 4: 4-character PDB ID ────────────────────────────────────────────
    if len(identifier_clean) == 4:
        # Check our local 100-PDB lookup table FIRST (avoids an RCSB API call)
        if identifier_clean in PDB_TO_BMRB:
            linked_bmrb = PDB_TO_BMRB[identifier_clean]
            # Check for an already-cached dataset in outputs/
            cached_csv = os.path.join(OUTPUTS_DIR, f"{linked_bmrb}_dataset.csv")
            pdb_cached_csv = os.path.join(OUTPUTS_DIR, f"{identifier_clean}_dataset.csv")
            # Prefer PDB-named cache, then BMRB-named cache
            use_cache = pdb_cached_csv if os.path.exists(pdb_cached_csv) else (
                        cached_csv      if os.path.exists(cached_csv)     else None)
            if use_cache:
                df_cache = pd.read_csv(use_cache)
                rows = []
                for idx, row in df_cache.iterrows():
                    freq = None
                    for col in ['Final_Freq', 'Effective', 'final_freq']:
                        if col in row and pd.notnull(row[col]):
                            freq = float(row[col])
                            break
                    if freq is None:
                        freq = 7500.0
                    struct = str(row.get("Secondary Structure",
                                 row.get("secondary_structure", "Random coil")))
                    row_dict = {
                        "sequence":            int(row.get("sequence", idx + 1)),
                        "chem_comp_ID":        str(row.get("chem_comp_ID", "ALA")),
                        "Final_Freq":          round(freq, 2),
                        "Secondary Structure": struct
                    }
                    # Preserve raw PPM columns if the cache has them — the sonify
                    # endpoint needs these to recompute Final_Freq at the user's
                    # chosen spectrometer frequency.
                    if "h_ppm" in row and pd.notnull(row["h_ppm"]):
                        row_dict["h_ppm"] = float(row["h_ppm"])
                    if "n_ppm" in row and pd.notnull(row["n_ppm"]):
                        row_dict["n_ppm"] = float(row["n_ppm"])
                    rows.append(row_dict)
                # Overwrite both named CSVs so they are always in sync
                df_out = pd.DataFrame(rows)
                df_out.to_csv(pdb_cached_csv, index=False)
                df_out.to_csv(cached_csv,      index=False)
                return {
                    "status":   "success",
                    "pdb_id":   identifier_clean,
                    "bmrb_id":  linked_bmrb,
                    "title":    f"PDB {identifier_clean} (BMRB {linked_bmrb})",
                    "spectrometer_mhz": KNOWN_SPECTROMETER_MHZ.get(str(linked_bmrb), 750.0),
                    "rows":     rows,
                    "csv_url":  f"/outputs/{identifier_clean}_dataset.csv"
                }
            # No cache → fetch from BMRB using the known BMRB ID
            res = fetch_real_bmrb_data(linked_bmrb)
            if res and res.get("status") == "success":
                res["pdb_id"] = identifier_clean
                res["title"]  = f"PDB {identifier_clean} (BMRB {linked_bmrb})"
                # Write a PDB-named copy as well
                pdb_csv_path = os.path.join(OUTPUTS_DIR, f"{identifier_clean}_dataset.csv")
                pd.DataFrame(res["rows"]).to_csv(pdb_csv_path, index=False)
                res["csv_url"] = f"/outputs/{identifier_clean}_dataset.csv"
                return res

        # Not in local lookup — fall back to RCSB PDB API
        try:
            r = requests.get(
                f"https://data.rcsb.org/rest/v1/core/entry/{identifier_clean}",
                timeout=25
            )
            if r.status_code == 200:
                rcsb_data = r.json()
                ext_refs  = rcsb_data.get("rcsb_external_references", [])
                for ref in ext_refs:
                    if ref.get("type", "").upper() == "BMRB" and ref.get("id"):
                        linked_bmrb = str(ref["id"]).strip()
                        if linked_bmrb.isdigit():
                            res = fetch_real_bmrb_data(linked_bmrb)
                            if res and res.get("status") == "success":
                                res["pdb_id"] = identifier_clean
                                res["title"]  = (
                                    f"{rcsb_data.get('struct', {}).get('title', f'PDB {identifier_clean}')}"
                                    f" (BMRB {linked_bmrb} / PDB {identifier_clean})"
                                )
                                # Cache PDB-named CSV too
                                pdb_csv_path = os.path.join(OUTPUTS_DIR,
                                                            f"{identifier_clean}_dataset.csv")
                                pd.DataFrame(res["rows"]).to_csv(pdb_csv_path, index=False)
                                res["csv_url"] = f"/outputs/{identifier_clean}_dataset.csv"
                                # Update local lookup for future calls
                                PDB_TO_BMRB[identifier_clean] = linked_bmrb
                                BMRB_TO_PDB[linked_bmrb]      = identifier_clean
                                return res
        except requests.exceptions.Timeout:
            print(f"Timeout checking RCSB PDB API for {identifier_clean}")
            return JSONResponse(
                status_code=504,
                content={
                    "status":  "error",
                    "message": (f"Connection to the RCSB PDB database timed out. "
                                f"Please try loading '{identifier_clean}' again.")
                }
            )
        except Exception as e:
            print(f"Error checking RCSB PDB API for {identifier_clean}: {e}")

        return JSONResponse(
            status_code=404,
            content={
                "status":  "error",
                "message": (f"No BMRB NMR chemical shift data available for PDB ID "
                            f"'{identifier_clean}'. This PDB structure does not have "
                            f"deposited NMR chemical shift assignments linked in BMRB. "
                            f"Please enter an NMR-assigned PDB ID (e.g. 1ST7, 1DMB, 1CA2, 2MV0), "
                            f"a BMRB ID (e.g. 6188, 25237), or upload your own CSV dataset.")
            }
        )

    return JSONResponse(
        status_code=400,
        content={
            "status":  "error",
            "message": (f"Invalid ID format '{identifier}'. "
                        f"Please enter a valid 4-character PDB ID or numeric BMRB ID.")
        }
    )

@app.post("/api/upload_csv")
async def upload_csv(
    file: UploadFile = File(...),
    pdb_id: str = Form("1DMB"),
    is_raw_ppm: str = Form("false")
):
    try:
        content = await file.read()
        temp_file = os.path.join(OUTPUTS_DIR, f"uploaded_{uuid.uuid4().hex[:6]}.csv")
        with open(temp_file, "wb") as f:
            f.write(content)
            
        df = pd.read_csv(temp_file)
        
        # ── Auto-detect and compute Final_Freq from raw PPM columns ──────────
        # This runs regardless of the is_raw_ppm checkbox so users never get
        # stuck with the 7500 fallback just because they forgot to tick the box.
        has_xy = "X_shift" in df.columns and "Y_shift" in df.columns
        has_hz  = "H_Hz"   in df.columns and "N_Hz"   in df.columns

        if has_xy and "Final_Freq" not in df.columns:
            # X_shift = 1H ppm, Y_shift = 15N ppm  (standard HSQC axis labels)
            # Store raw PPM so the sonify endpoint can rescale by spectrometer_mhz
            df["h_ppm"] = df["X_shift"]
            df["n_ppm"] = df["Y_shift"]
            # Default Final_Freq at 750 MHz — overwritten at sonify time
            df["Final_Freq"] = np.round(
                np.sqrt(df["X_shift"] * 750.0 * df["Y_shift"] * 75.0), 2
            )
        elif has_hz and "Final_Freq" not in df.columns:
            # Already in Hz units — compute geometric mean directly
            df["Final_Freq"] = np.round(np.sqrt(df["H_Hz"] * df["N_Hz"]), 2)

        rows = []
        for idx, row in df.iterrows():
            freq = None
            for col in ['Final_Freq', 'Effective', 'final_freq', 'frequency', 'Freq']:
                if col in row and pd.notnull(row[col]):
                    freq = float(row[col])
                    break
            if freq is None:
                freq = 7500.0
                
            struct = "Random coil"
            for col in ['Secondary Structure', 'secondary_structure', 'Secondary_Structure', 'Structure', 'ss']:
                if col in row and pd.notnull(row[col]):
                    struct = str(row[col])
                    break

            row_dict = {
                "sequence":            int(row.get("sequence", idx + 1)),
                "chem_comp_ID":        str(row.get("chem_comp_ID", "ALA")),
                "Final_Freq":          round(float(freq), 2),
                "Secondary Structure": struct
            }
            # Preserve raw PPM columns so sonify endpoint can rescale by spectrometer_mhz
            if "h_ppm" in row and pd.notnull(row["h_ppm"]):
                row_dict["h_ppm"] = float(row["h_ppm"])
            if "n_ppm" in row and pd.notnull(row["n_ppm"]):
                row_dict["n_ppm"] = float(row["n_ppm"])
            rows.append(row_dict)
            
        clean_pdb = pdb_id.strip().upper() if pdb_id and len(pdb_id.strip()) == 4 else "1DMB"
        return {
            "status": "success",
            "title": file.filename,
            "pdb_id": clean_pdb,
            "rows": rows,
            "csv_url": f"/outputs/{os.path.basename(temp_file)}"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/sonify")
def create_sonification(req: SonifyRequest):
    import datetime, shutil
    if not req.dataset:
        raise HTTPException(status_code=400, detail="Dataset is empty")

    # ── Create per-protein run directory ──────────────────────────────────────
    # Every run for the same protein lands in its own timestamped subfolder so
    # nothing is ever overwritten and all runs are preserved for comparison.
    run_dir, protein_dir, url_prefix, protein_folder = make_protein_run_dir(
        pdb_id=req.pdb_id, bmrb_id=req.bmrb_id
    )

    # Paths inside the run folder
    input_csv_path = os.path.join(run_dir, "input.csv")
    mid_path       = os.path.join(run_dir, "music.mid")
    wav_path       = os.path.join(run_dir, "music.wav")
    timeline_path  = os.path.join(run_dir, "timeline.csv")
    info_path      = os.path.join(run_dir, "run_info.json")

    # ── Save the input dataset that goes into sonify ──────────────────────────
    df_input = pd.DataFrame(req.dataset)

    # Recompute Final_Freq from raw PPM values if available, using the
    # user's actual spectrometer frequency.  This is the correct fix for
    # the pipeline bug where Final_Freq was always computed at 750 MHz at
    # fetch time, then incorrectly linearly-scaled at sonify time.
    spec_mhz = req.spectrometer_mhz if req.spectrometer_mhz else 750.0
    if "h_ppm" in df_input.columns and "n_ppm" in df_input.columns:
        h_mhz = spec_mhz          # 1H field in MHz
        n_mhz = spec_mhz / 10.0   # 15N field ≈ 1/10 of 1H (gyromagnetic ratio)
        df_input["Final_Freq"] = np.round(
            np.sqrt(df_input["h_ppm"] * h_mhz * df_input["n_ppm"] * n_mhz), 2
        )
    elif spec_mhz != 750.0:
        # Fallback: if raw PPM not present (e.g. manually uploaded CSV without
        # h_ppm/n_ppm columns), apply a ratio correction as an approximation.
        # sqrt(h_hz * n_hz) scales as sqrt(mhz_ratio^2) = mhz_ratio linearly.
        scale_factor = spec_mhz / 750.0
        for col in ['Final_Freq', 'Effective', 'final_freq', 'frequency', 'Freq']:
            if col in df_input.columns:
                df_input[col] = (df_input[col] * scale_factor).round(2)
                break

    df_input.to_csv(input_csv_path, index=False)

    # ── Also keep the flat-outputs files (backward compat with old download links)
    run_id   = uuid.uuid4().hex[:8]
    flat_csv = os.path.join(OUTPUTS_DIR, f"run_{run_id}.csv")
    flat_mid = os.path.join(OUTPUTS_DIR, f"music_{run_id}.mid")
    flat_wav = os.path.join(OUTPUTS_DIR, f"music_{run_id}.wav")
    df_input.to_csv(flat_csv, index=False)

    # ── Run the sonification (writes MIDI + WAV into the run folder) ──────────
    result = sonify.sonify_bmrb(
        csv_path=input_csv_path,
        output_mid_path=mid_path,
        output_wav_path=wav_path,
        raag_name=req.raag_name,
        root_note=req.root_note,
        tempo_multiplier=req.tempo_multiplier,
        lead_inst=req.lead_inst,
        echo_inst=req.echo_inst,
        accent_inst=req.accent_inst,
        enable_drone=req.enable_drone,
        enable_tabla=req.enable_tabla
    )

    # ── Save timeline CSV inside the run folder ───────────────────────────────
    timeline_df = pd.DataFrame(result.get("timeline", []))
    freq_csv_path = os.path.join(run_dir, "final_frequencies.csv")
    if not timeline_df.empty:
        timeline_df.to_csv(timeline_path, index=False)

        # ── Save final_frequencies.csv ────────────────────────────────────────
        # This is the key scientific record: one row per residue showing EXACTLY
        # how the NMR chemical shift frequency (Final_Freq_Hz) was converted into
        # a musical note (Scaled_Freq_Hz → MIDI_Note → Svara in the chosen Raag).
        # Column mapping follows Aarohan's rules exactly:
        #   Final_Freq_Hz  = sqrt(H_Hz × N_Hz)  [geometric mean of HSQC shifts]
        #   Scaled_Freq_Hz = log-exp scaled to 240–480 Hz  [sonify.scale_log_exp]
        #   MIDI_Note      = 69 + 12 × log2(Scaled_Freq / 440)
        #   Svara          = nearest Raag note (Sa Re Ga Ma Pa Dha Ni)
        freq_df = pd.DataFrame({
            "sequence":          timeline_df["sequence"],
            "amino_acid":        timeline_df["amino_acid"],
            "secondary_structure": timeline_df["secondary_structure"],
            "Final_Freq_Hz":     timeline_df["final_freq"],   # raw NMR freq → pitch driver
            "Scaled_Freq_Hz":    timeline_df["scaled_freq"],  # 240–480 Hz musical range
            "MIDI_Note":         timeline_df["midi_note"],
            "Svara":             timeline_df["svara"],
            "time_sec":          timeline_df["time"],
            "duration_beats":    timeline_df["duration"],
        })
        freq_df.to_csv(freq_csv_path, index=False)

    # ── Save run metadata JSON ────────────────────────────────────────────────
    # Resolve BMRB ID: use what the frontend sent, or look up from local table
    clean_pdb  = req.pdb_id.strip().upper()  if req.pdb_id  else ""
    clean_bmrb = req.bmrb_id.strip()         if req.bmrb_id else ""
    if not clean_bmrb and clean_pdb:
        clean_bmrb = PDB_TO_BMRB.get(clean_pdb, "")

    run_info = {
        "pdb_id":           clean_pdb,
        "bmrb_id":          clean_bmrb,
        "protein_folder":   protein_folder,
        "raag":             req.raag_name,
        "root_note":        req.root_note,
        "tempo_multiplier": req.tempo_multiplier,
        "lead_instrument":  req.lead_inst,
        "echo_instrument":  req.echo_inst,
        "enable_drone":     req.enable_drone,
        "enable_tabla":     req.enable_tabla,
        "timestamp":        datetime.datetime.now().isoformat(timespec="seconds"),
        "total_residues":   result.get("total_residues", 0),
        "total_duration_s": result.get("total_duration", 0),
        "run_folder":       os.path.basename(run_dir)
    }
    with open(info_path, "w") as f:
        json.dump(run_info, f, indent=2)

    # ── Update the protein-level dataset.csv (always = latest run's input) ────
    protein_dataset_csv = os.path.join(protein_dir, "dataset.csv")
    df_input.to_csv(protein_dataset_csv, index=False)

    # ── Copy files to flat outputs/ for backward-compat download links ────────
    shutil.copy2(mid_path, flat_mid)
    shutil.copy2(wav_path, flat_wav)

    # ── Also update legacy named CSVs in flat outputs/ ────────────────────────
    # IMPORTANT: write df_input (the scientific dataset with chem_comp_ID, h_ppm,
    # n_ppm, Final_Freq, Secondary Structure) — NOT timeline_df (music output).
    # Writing timeline_df here was corrupting the cache: chem_comp_ID was lost
    # (all residues became "ALA"), h_ppm/n_ppm were lost (spectrometer scaling
    # broke on reload), and the downloaded CSV contained music data not NMR data.
    if clean_pdb and len(clean_pdb) == 4:
        df_input.to_csv(os.path.join(OUTPUTS_DIR, f"{clean_pdb}_dataset.csv"), index=False)
        if clean_bmrb:
            df_input.to_csv(os.path.join(OUTPUTS_DIR, f"{clean_bmrb}_dataset.csv"), index=False)

    print(f"[sonify] Run saved → {run_dir}")

    return {
        "status":           "success",
        "audio_url":        f"{url_prefix}/music.wav",
        "midi_url":         f"{url_prefix}/music.mid",
        "csv_url":          f"{url_prefix}/input.csv",
        "timeline_url":     f"{url_prefix}/timeline.csv",
        "final_freq_url":   f"{url_prefix}/final_frequencies.csv",
        "info_url":         f"{url_prefix}/run_info.json",
        "protein_folder":   protein_folder,
        "run_folder":       os.path.basename(run_dir),
        "pdb_id":           req.pdb_id,
        "result":           result
    }

# Serve static app
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    print("Launching Cosmic Raga Server on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
