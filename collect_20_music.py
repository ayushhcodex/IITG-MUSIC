"""
collect_20_music.py
===================
• Generates music for 20 PDB/BMRB proteins (via localhost:8080 API)
• Copies each WAV + MIDI into  music_collection_20/
• Names files descriptively:   01_1UJX_BMRB10104_Santoor_Yaman.wav
• Writes                       music_collection_20/README.md
• Writes                       music_collection_20/index.html  (pretty browser view)
• Writes                       music_collection_20/data.json   (machine-readable)

Run (server must already be running on :8080):
    python3 collect_20_music.py
"""

import os, json, shutil, time, requests, pandas as pd
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
BASE_URL       = "http://localhost:8080"
PROJECT_DIR    = os.path.dirname(os.path.abspath(__file__))
COLLECTION_DIR = os.path.join(PROJECT_DIR, "music_collection_20")
CSV_100        = os.path.join(PROJECT_DIR, "100 pdb with chemmical shift values .csv")

os.makedirs(COLLECTION_DIR, exist_ok=True)

# ── 20 proteins ───────────────────────────────────────────────────────────────
df100   = pd.read_csv(CSV_100)
TARGETS = [
    {"pdb_id": str(r["pdb_id"]).strip().upper(),
     "bmrb_id": str(int(r["bmrb_id"])).strip()}
    for _, r in df100.head(20).iterrows()
]

# ── Instrument palette ────────────────────────────────────────────────────────
INSTRUMENTS = [
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

MUSIC_PARAMS = [
    {"raag": "Yaman",    "root": 60, "tempo": 1.00},
    {"raag": "Bhairav",  "root": 60, "tempo": 0.80},
    {"raag": "Bhupali",  "root": 62, "tempo": 1.20},
    {"raag": "Kafi",     "root": 59, "tempo": 0.90},
    {"raag": "Malkauns", "root": 60, "tempo": 0.70},
    {"raag": "Yaman",    "root": 64, "tempo": 1.10},
    {"raag": "Bhairav",  "root": 57, "tempo": 1.00},
    {"raag": "Bhupali",  "root": 60, "tempo": 0.85},
    {"raag": "Kafi",     "root": 62, "tempo": 1.30},
    {"raag": "Malkauns", "root": 65, "tempo": 0.75},
    {"raag": "Yaman",    "root": 67, "tempo": 1.15},
    {"raag": "Bhairav",  "root": 63, "tempo": 0.95},
    {"raag": "Bhupali",  "root": 58, "tempo": 1.05},
    {"raag": "Kafi",     "root": 61, "tempo": 0.80},
    {"raag": "Malkauns", "root": 60, "tempo": 1.10},
    {"raag": "Yaman",    "root": 55, "tempo": 0.90},
    {"raag": "Bhairav",  "root": 64, "tempo": 1.25},
    {"raag": "Bhupali",  "root": 69, "tempo": 0.70},
    {"raag": "Kafi",     "root": 60, "tempo": 1.00},
    {"raag": "Malkauns", "root": 63, "tempo": 0.85},
]

FREQ_RANGES = [
    (240,480),(200,440),(280,520),(220,460),(260,500),
    (240,480),(300,560),(200,400),(240,520),(260,480),
    (240,480),(220,480),(280,560),(240,460),(200,480),
    (260,520),(240,480),(220,500),(280,480),(240,480),
]

NOTE_NAMES = {55:"G3",57:"A3",58:"Bb3",59:"B3",60:"C4",61:"C#4",
              62:"D4",63:"Eb4",64:"E4",65:"F4",67:"G4",69:"A4"}

# ── API helpers ───────────────────────────────────────────────────────────────
def fetch(bmrb_id):
    try:
        r = requests.get(f"{BASE_URL}/api/fetch/{bmrb_id}", timeout=30)
        if r.status_code == 200:
            return r.json()
        print(f"    HTTP {r.status_code}")
    except Exception as e:
        print(f"    Fetch error: {e}")
    return None

def sonify(dataset, pdb, bmrb, inst, mp, fr):
    payload = {
        "dataset": dataset, "pdb_id": pdb, "bmrb_id": bmrb,
        "raag_name": mp["raag"], "root_note": mp["root"],
        "tempo_multiplier": mp["tempo"],
        "lead_inst": inst["lead"], "echo_inst": inst["echo"],
        "accent_inst": inst["accent"],
        "enable_drone": True, "enable_tabla": True,
        "freq_min": fr[0], "freq_max": fr[1],
        "spectrometer_mhz": 750.0,
    }
    try:
        r = requests.post(f"{BASE_URL}/api/sonify", json=payload, timeout=180)
        if r.status_code == 200:
            return r.json()
        print(f"    Sonify HTTP {r.status_code}")
    except Exception as e:
        print(f"    Sonify error: {e}")
    return None

def safe_name(s):
    return s.replace(" & ", "_").replace(" ", "_").replace("/", "-")

# ── Main ──────────────────────────────────────────────────────────────────────
print(f"\n{'='*65}")
print(f"  Generating & collecting 20 protein music files")
print(f"  Collection: {COLLECTION_DIR}")
print(f"{'='*65}\n")

records = []
generated_on = datetime.now().strftime("%Y-%m-%d")

for i, tgt in enumerate(TARGETS):
    pdb   = tgt["pdb_id"]
    bmrb  = tgt["bmrb_id"]
    inst  = INSTRUMENTS[i]
    mp    = MUSIC_PARAMS[i]
    fr    = FREQ_RANGES[i]
    n     = i + 1
    root_name = NOTE_NAMES.get(mp["root"], str(mp["root"]))

    print(f"[{n:02d}/20] {pdb} / BMRB {bmrb}")
    print(f"        Instruments : {inst['name']}")
    print(f"        Raag={mp['raag']}  Root={root_name}  Tempo×{mp['tempo']}")

    t0   = time.time()
    data = fetch(bmrb)
    if not data or not data.get("rows"):
        print(f"    No BMRB data — skipped\n")
        records.append({"index": n, "pdb": pdb, "bmrb": bmrb, "status": "fetch_failed"})
        continue

    nres = len(data["rows"])
    res  = sonify(data["rows"], pdb, bmrb, inst, mp, fr)
    elapsed = round(time.time() - t0, 1)

    if not res or res.get("status") != "success":
        print(f"    Sonify failed ({elapsed}s)\n")
        records.append({"index": n, "pdb": pdb, "bmrb": bmrb, "status": "sonify_failed"})
        continue

    dur = res.get("result", {}).get("total_duration", 0)

    # Build the descriptive base name
    inst_slug = safe_name(inst["name"])
    base = f"{n:02d}_{pdb}_BMRB{bmrb}_{inst_slug}_{mp['raag']}"

    # ── Resolve source paths from server URL ─────────────────────────────────
    # The server returns URL-prefixed paths like /outputs/.../music.wav
    # We map those to local filesystem paths.
    audio_url = res.get("audio_url", "")   # e.g. /outputs/1UJX_BMRB10104/run_.../music.wav
    midi_url  = res.get("midi_url",  "")

    src_wav = os.path.join(PROJECT_DIR, audio_url.lstrip("/").replace("/", os.sep))
    src_mid = os.path.join(PROJECT_DIR, midi_url.lstrip("/").replace("/", os.sep))

    dst_wav = os.path.join(COLLECTION_DIR, base + ".wav")
    dst_mid = os.path.join(COLLECTION_DIR, base + ".mid")

    copied_wav = copied_mid = False
    if os.path.exists(src_wav):
        shutil.copy2(src_wav, dst_wav)
        copied_wav = True
    if os.path.exists(src_mid):
        shutil.copy2(src_mid, dst_mid)
        copied_mid = True

    print(f"    Done {elapsed}s | {nres} residues | {dur}s audio")
    print(f"    WAV  -> {base}.wav  {'(copied)' if copied_wav else '(MISSING)'}")
    print(f"    MIDI -> {base}.mid  {'(copied)' if copied_mid else '(MISSING)'}\n")

    records.append({
        "index":          n,
        "status":         "ok",
        "pdb_id":         pdb,
        "bmrb_id":        bmrb,
        "protein_title":  data.get("title", f"PDB {pdb}"),
        "n_residues":     nres,
        "duration_s":     dur,
        "instruments":    inst["name"],
        "lead_program":   inst["lead"],
        "echo_program":   inst["echo"],
        "accent_program": inst["accent"],
        "raag":           mp["raag"],
        "root_note":      root_name,
        "root_midi":      mp["root"],
        "tempo_mult":     mp["tempo"],
        "freq_min":       fr[0],
        "freq_max":       fr[1],
        "wav_file":       base + ".wav" if copied_wav else None,
        "mid_file":       base + ".mid" if copied_mid else None,
        "generated_on":   generated_on,
    })

    if i < len(TARGETS) - 1:
        time.sleep(1)

# ── data.json ─────────────────────────────────────────────────────────────────
data_path = os.path.join(COLLECTION_DIR, "data.json")
with open(data_path, "w") as f:
    json.dump(records, f, indent=2)

# ── README.md ─────────────────────────────────────────────────────────────────
ok = [r for r in records if r.get("status") == "ok"]
readme_lines = [
    f"# MrFold Music Collection — {generated_on}",
    "",
    f"**{len(ok)} / 20 proteins sonified successfully.**",
    "",
    "Each WAV file is a unique Indian Classical sonification of an NMR protein structure.",
    "The MIDI file contains the full multi-stem score (santoor / bansuri / sitar / tabla / tanpura).",
    "",
    "## File naming convention",
    "",
    "```",
    "NN_<PDB>_BMRB<BMRB>_<Lead>_<Echo>_<Raag>.wav",
    "```",
    "",
    "## Track listing",
    "",
    "| # | File | Protein | Residues | Instruments | Raag | Root | Tempo | Duration |",
    "|---|------|---------|----------|-------------|------|------|-------|----------|",
]
for r in records:
    if r.get("status") != "ok":
        readme_lines.append(
            f"| {r['index']:02d} | — | {r['pdb_id']} / BMRB {r['bmrb_id']} | — | "
            f"— | — | — | — | ❌ fetch/sonify failed |"
        )
        continue
    fname = r["wav_file"] or "—"
    readme_lines.append(
        f"| {r['index']:02d} | `{fname}` | {r['protein_title']} "
        f"| {r['n_residues']} | {r['instruments']} | {r['raag']} "
        f"| {r['root_note']} | ×{r['tempo_mult']} | {r['duration_s']}s |"
    )

readme_lines += [
    "",
    "## Methodology",
    "",
    "1. NMR ¹H and ¹⁵N chemical shifts fetched from BMRB API",
    "2. Secondary structure assigned from RCSB PDB HELIX/SHEET records",
    "3. `Final_Freq = √(H_ppm × 750 MHz × N_ppm × 75 MHz)` — geometric mean",
    "4. Frequencies log-exp scaled to musical range (freq_min – freq_max Hz)",
    "5. Notes quantized to the chosen Raag scale (Sa Re Ga Ma Pa Dha Ni)",
    "6. Multi-track MIDI rendered to WAV via FluidSynth + TimGM6mb.sf2",
    "7. Stems mixed with tension-scaled distortion (structural variance → dynamics)",
    "",
    "## Reproducibility",
    "",
    "Output is 100% deterministic for a given protein:",
    "- Random seed = SHA-256(amino acid sequence) — identical for all users",
    "- Secondary structure = parsed from RCSB PDB, not estimated",
    "",
    f"Generated by MrFold Music (SonicFold NMR) on {generated_on}",
]

readme_path = os.path.join(COLLECTION_DIR, "README.md")
with open(readme_path, "w") as f:
    f.write("\n".join(readme_lines))

# ── index.html ────────────────────────────────────────────────────────────────
rows_html = ""
for r in records:
    if r.get("status") != "ok":
        rows_html += f"""
        <tr class="fail">
          <td>{r['index']:02d}</td>
          <td colspan="8">{r['pdb_id']} / BMRB {r['bmrb_id']} — <span class="tag fail-tag">failed</span></td>
        </tr>"""
        continue

    wav_link = (f'<a class="dl-btn wav" href="{r["wav_file"]}" download>⬇ WAV</a>'
                if r["wav_file"] else "—")
    mid_link = (f'<a class="dl-btn mid" href="{r["mid_file"]}" download>⬇ MIDI</a>'
                if r["mid_file"] else "—")

    inst_parts = r["instruments"].split(" & ")
    lead_pill  = f'<span class="pill lead">{inst_parts[0]}</span>'
    echo_pill  = f'<span class="pill echo">{inst_parts[1]}</span>' if len(inst_parts) > 1 else ""

    rows_html += f"""
        <tr>
          <td class="num">{r['index']:02d}</td>
          <td><strong>{r['pdb_id']}</strong><br><small>BMRB {r['bmrb_id']}</small></td>
          <td class="title">{r['protein_title']}</td>
          <td class="center">{r['n_residues']}</td>
          <td>{lead_pill}{echo_pill}</td>
          <td><span class="raag">{r['raag']}</span></td>
          <td class="center">{r['root_note']}</td>
          <td class="center">×{r['tempo_mult']}</td>
          <td class="center">{r['duration_s']}s</td>
          <td>{wav_link} {mid_link}</td>
        </tr>"""

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MrFold Music Collection — {generated_on}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg:       #0d0f1a;
      --surface:  #161929;
      --border:   #252840;
      --accent:   #7c6fff;
      --accent2:  #ff6b9d;
      --text:     #e8eaf6;
      --muted:    #7b82a8;
      --lead-bg:  #1e1b4b;
      --echo-bg:  #1a2e1a;
      --raag-bg:  #1e2d3d;
      --success:  #4caf78;
      --fail:     #ef5350;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: 'Inter', sans-serif;
      min-height: 100vh;
      padding: 40px 24px;
    }}
    header {{
      text-align: center;
      margin-bottom: 48px;
    }}
    header h1 {{
      font-size: 2.4rem;
      font-weight: 700;
      background: linear-gradient(135deg, var(--accent), var(--accent2));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin-bottom: 8px;
    }}
    header p {{ color: var(--muted); font-size: 0.95rem; }}
    .stats {{
      display: flex;
      gap: 16px;
      justify-content: center;
      flex-wrap: wrap;
      margin-bottom: 40px;
    }}
    .stat-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 20px 32px;
      text-align: center;
    }}
    .stat-card .val {{
      font-size: 2rem;
      font-weight: 700;
      color: var(--accent);
    }}
    .stat-card .lbl {{
      font-size: 0.8rem;
      color: var(--muted);
      margin-top: 4px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .table-wrap {{
      overflow-x: auto;
      border-radius: 16px;
      border: 1px solid var(--border);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--surface);
      font-size: 0.88rem;
    }}
    thead tr {{
      background: linear-gradient(90deg, #1a1d35, #1d1a35);
    }}
    th {{
      padding: 14px 16px;
      font-size: 0.72rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      white-space: nowrap;
      text-align: left;
      border-bottom: 1px solid var(--border);
    }}
    td {{
      padding: 12px 16px;
      border-bottom: 1px solid var(--border);
      vertical-align: middle;
    }}
    tr:last-child td {{ border-bottom: none; }}
    tr:hover td {{ background: rgba(124,111,255,0.04); }}
    tr.fail td {{ opacity: 0.5; }}
    .num {{ font-family: 'JetBrains Mono', monospace; color: var(--muted); text-align: center; }}
    .center {{ text-align: center; }}
    .title {{ max-width: 220px; font-size: 0.82rem; color: var(--muted); }}
    .title strong {{ color: var(--text); }}
    .pill {{
      display: inline-block;
      border-radius: 6px;
      padding: 3px 8px;
      font-size: 0.75rem;
      font-weight: 500;
      margin: 2px 2px 2px 0;
      white-space: nowrap;
    }}
    .pill.lead {{ background: var(--lead-bg); color: #a5b4fc; border: 1px solid #3730a3; }}
    .pill.echo {{ background: var(--echo-bg); color: #86efac; border: 1px solid #166534; }}
    .raag {{
      display: inline-block;
      background: var(--raag-bg);
      border: 1px solid #164e63;
      color: #7dd3fc;
      border-radius: 6px;
      padding: 3px 10px;
      font-size: 0.78rem;
      font-weight: 600;
    }}
    .dl-btn {{
      display: inline-block;
      border-radius: 6px;
      padding: 5px 10px;
      font-size: 0.75rem;
      font-weight: 600;
      text-decoration: none;
      margin: 2px;
      transition: opacity 0.2s;
    }}
    .dl-btn:hover {{ opacity: 0.8; }}
    .dl-btn.wav {{ background: #312e81; color: #c7d2fe; border: 1px solid #4338ca; }}
    .dl-btn.mid {{ background: #14532d; color: #bbf7d0; border: 1px solid #16a34a; }}
    .tag {{
      display: inline-block;
      border-radius: 4px;
      padding: 2px 8px;
      font-size: 0.72rem;
      font-weight: 600;
    }}
    .fail-tag {{ background: #450a0a; color: var(--fail); }}
    footer {{
      text-align: center;
      margin-top: 48px;
      color: var(--muted);
      font-size: 0.82rem;
    }}
    footer a {{ color: var(--accent); text-decoration: none; }}
  </style>
</head>
<body>
  <header>
    <h1>🎵 MrFold Music Collection</h1>
    <p>Indian Classical Sonifications of NMR Protein Structures &nbsp;·&nbsp; Generated {generated_on}</p>
  </header>

  <div class="stats">
    <div class="stat-card">
      <div class="val">{len(ok)}</div>
      <div class="lbl">Proteins Sonified</div>
    </div>
    <div class="stat-card">
      <div class="val">5</div>
      <div class="lbl">Raags Used</div>
    </div>
    <div class="stat-card">
      <div class="val">10</div>
      <div class="lbl">Unique Instruments</div>
    </div>
    <div class="stat-card">
      <div class="val">{sum(r.get('duration_s',0) for r in ok)}s</div>
      <div class="lbl">Total Audio</div>
    </div>
  </div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>PDB / BMRB</th>
          <th>Protein</th>
          <th>Residues</th>
          <th>Instruments</th>
          <th>Raag</th>
          <th>Root</th>
          <th>Tempo</th>
          <th>Duration</th>
          <th>Download</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>
  </div>

  <footer>
    <p>All outputs are deterministic — same protein always produces identical music for every user.</p>
    <p style="margin-top:8px">Seed = SHA-256(amino acid sequence) &nbsp;·&nbsp; Structure from RCSB PDB &nbsp;·&nbsp; SoundFont: TimGM6mb.sf2</p>
  </footer>
</body>
</html>"""

html_path = os.path.join(COLLECTION_DIR, "index.html")
with open(html_path, "w") as f:
    f.write(html)

# ── Final summary ─────────────────────────────────────────────────────────────
print(f"\n{'='*65}")
print(f"  {len(ok)}/20 proteins collected successfully")
print(f"  Folder  : {COLLECTION_DIR}")
print(f"  Index   : {COLLECTION_DIR}/index.html")
print(f"  Data    : {COLLECTION_DIR}/data.json")
print(f"  Readme  : {COLLECTION_DIR}/README.md")
print(f"{'='*65}\n")

print(f"{'#':>3}  {'PDB':>5}  {'BMRB':>6}  {'WAV File':<52}  {'Dur':>5}")
print("-" * 80)
for r in records:
    if r.get("status") == "ok":
        print(f"{r['index']:>3}  {r['pdb_id']:>5}  {r['bmrb_id']:>6}  "
              f"{r.get('wav_file','—'):<52}  {r['duration_s']:>5}s")
    else:
        print(f"{r['index']:>3}  {r['pdb_id']:>5}  {r['bmrb_id']:>6}  {'— FAILED —':<52}")

print(f"\nOpen in browser:  open \"{html_path}\"")
