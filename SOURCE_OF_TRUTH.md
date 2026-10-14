# MrFold Music Studio — System Architecture & Source of Truth

> **Version**: 1.1.0  
> **Last Verified**: October 2026  
> **Status**: Production Stable (`main` @ tag `v1.1.0`)  
> **Active Development**: `exp` branch  

---

## 1. Git Branching & Release Model

| Branch | Purpose | Deployment Target | Protection |
| :--- | :--- | :--- | :--- |
| **`main`** | **Production Stable** | Hugging Face Spaces (`mantisa/mrfold1`), GitHub `main` | **Locked**. Never commit directly. Only fast-forward merge from `exp` after production testing. |
| **`exp`** | **Active Development** | Local development (`localhost:7860`), GitHub `exp` | Default working branch for all new features, bug fixes, and experiments. |

### Release Tags:
- `v1.0.0` / `V1.0.1`: Initial releases.
- `v1.1.0`: Stable release with native ZeroGPU launcher, fullscreen Raga controls, 3D Mol viewer offline caching, and isolated vendor prefixes.

---

## 2. Infrastructure & Deployment Constraints

### 2.1 Hugging Face Billing & Hardware Tiers (Critical Assumption)
1. **`cpu-basic` is PRO-Gated**:
   - Hugging Face API returns `HTTP 402 Payment Required: Without a PRO subscription, you can't downgrade this Space to cpu-basic`.
   - Creating new Gradio or Docker spaces on free `cpu-basic` is disabled for non-pro community accounts.
2. **ZeroGPU (`zero-a10g`) is Free for Community Spaces**:
   - `mantisa/mrfold1` is allocated `zero-a10g`.
   - ZeroGPU dynamically provisions GPU slices when needed and costs \$0.00 for community spaces.

### 2.2 Hugging Face ZeroGPU Startup Rules
To run successfully under ZeroGPU without triggering `RuntimeError: No @spaces.GPU function detected during startup`:
1. **Module-Scope Import**: `import spaces` must happen at the module level in `app.py`.
2. **Component Registration**: At least one `@spaces.GPU` function must be defined and bound to a Gradio component event (e.g. `_btn.click(fn=dummy_gpu_fn, inputs=_inp, outputs=_out)`).
3. **No Direct `uvicorn.run`**: In `sdk: gradio`, Hugging Face's container uses an internal Node.js/SvelteKit SSR supervisor that occupies port `7860`. Calling `uvicorn.run(..., port=7860)` directly in `app.py` results in `[Errno 98] Address already in use`, terminating the container before ZeroGPU can register.
4. **Native `demo.launch()`**: `app.py` must call `demo.launch()` so Gradio communicates directly with Hugging Face's internal proxy.

---

## 3. Reverse Proxy & API Routing Architecture

```
                                  [ User Browser ]
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 │                                               │
      (Production HF Space)                                (Localhost)
                 │                                               │
                 ▼                                               ▼
     https://...hf.space/                             http://127.0.0.1:7860/
                 │                                               │
        [Node.js / SvelteKit]                             [FastAPI Directly]
        (Listening on :7860)                               (backend_app:app)
                 │                                               │
                 ▼                                               ▼
         [Python Gradio]                                  Serves static/
        (Runs demo.launch)                                and /api/* directly
                 │
                 ▼ (Mounted via _patched_create_app)
        /gradio_api/custom/
                 │
                 ├── /                 ──> static/index.html (via iframe)
                 ├── /api/*            ──> FastAPI Endpoints
                 ├── /outputs/*        ──> Generated Audio/MIDI/CSV
                 └── static assets     ──> CSS / JS / 3Dmol
```

### 3.1 Path Prefix Handling (`static/app.js`)
- `API_PREFIX` is dynamically computed at runtime:
  ```javascript
  const API_PREFIX = window.location.pathname.includes("/gradio_api/custom") ? "/gradio_api/custom" : "";
  ```
- A global `window.fetch` interceptor automatically prepends `API_PREFIX` to any outgoing `/api/*` and `/outputs/*` URLs:
  ```javascript
  function resolveUrl(url) {
    if (!url || typeof url !== "string") return url;
    if (url.startsWith("http") || url.startsWith("blob:") || url.startsWith("data:")) return url;
    if (API_PREFIX && url.startsWith(API_PREFIX)) return url;
    if (url.startsWith("/api/") || url.startsWith("/outputs/")) {
      return `${API_PREFIX}${url}`;
    }
    return url;
  }
  ```
- **Consequence**: The frontend works completely identically on `localhost:7860` (where `API_PREFIX = ""`) and on Hugging Face Spaces (where `API_PREFIX = "/gradio_api/custom"`).

---

## 4. Backend Endpoints & Data Model

| Endpoint | Method | Input | Output | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `/api/presets` | `GET` | — | JSON map | Returns pre-configured PDB/BMRB showcase proteins. |
| `/api/fetch/{identifier}` | `GET` | `pdb_id` or `bmrb_id` | JSON dataset | Fetches chemical shift tables via BMRB API or local mapping. |
| `/api/pdb/{pdb_id}` | `GET` | 4-letter PDB code | Raw `.pdb` / `.cif` text | Serves 3D atomic coordinates with local disk cache fallback (`pdb_cache/`). |
| `/api/upload_csv` | `POST` | CSV file multipart | JSON dataset | Ingests user-supplied experimental chemical shift CSV. |
| `/api/sonify` | `POST` | JSON sonification config | JSON with audio paths | Runs Raga sonification, generates MIDI, renders WAV stems via FluidSynth, and mixes final audio. |
| `/outputs/{run_id}/{file}` | `GET` | Path | Binary (audio/midi/csv) | Serves synthesized audio stems, final mix, and MIDI. |
| `/gradio_api/startup-events` | `GET` | — | `{"is_running": true}` | Intercepts Gradio health check to prevent 404 startup failure. |

---

## 5. Sonification Engine & Native Dependencies

1. **FluidSynth & SoundFonts**:
   - System packages required: `fluidsynth`, `fluid-soundfont-gm`, `libsndfile1`, `ffmpeg`.
   - Specified in [`packages.txt`](packages.txt) for Hugging Face Spaces, and in [`Dockerfile`](Dockerfile) for Docker/Render deployments.
   - Default SoundFont bundled in repository root: `TimGM6mb.sf2`.
   - Fallback sequence in `sonicfold_nmr/sonify.py`:
     1. Local `TimGM6mb.sf2` in repo root.
     2. System paths (`/usr/share/sounds/sf2/FluidR3_GM.sf2`, `/usr/share/soundfonts/default.sf2`, etc.).
2. **Indian Classical Music (Ragas)**:
   - Supported Ragas: *Yaman*, *Bhairav*, *Bhupali*, *Kafi*, *Malkauns*, *Khamaaz*.
   - Chemical shift ranges ($^1\text{H}$ and $^{15}\text{N}$) are mapped to Sa-Re-Ga-Ma scale degrees using logarithmic frequency spacing.
   - Tension calculation: Secondary structure ($\alpha$-helix, $\beta$-sheet, random coil) modulates note velocity, duration, and distortion level.

---

## 6. Frontend & Fullscreen Design Rules

1. **Vendor Prefix Separation**:
   - CSS rules for fullscreen pseudo-classes MUST be declared separately, not combined with commas:
     ```css
     /* Correct */
     :fullscreen #fullscreen-raga-options { ... }
     :-webkit-full-screen #fullscreen-raga-options { ... }
     :-moz-full-screen #fullscreen-raga-options { ... }

     /* NEVER combine in one selector — browsers drop the entire rule if one prefix is unrecognized */
     ```
2. **Cache Busting**:
   - Update query parameters in `static/index.html` on UI changes:
     `<link rel="stylesheet" href="style.css?v=11">`
     `<script src="app.js?v=11"></script>`
3. **3D Molecular Visualization**:
   - Uses `3Dmol.js` (`static/3Dmol-min.js`).
   - Prioritizes local `/api/pdb/{pdb_id}` cache so molecular structures render immediately without waiting for RCSB network queries.

---

## 7. How to Run Locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run local FastAPI server (works out-of-the-box on CPU)
python3 -m uvicorn backend_app:app --host 127.0.0.1 --port 7860

# 3. Open in browser
http://127.0.0.1:7860
```

---

## 8. How to Deploy Updates Safely

1. Always work and test on branch **`exp`**.
2. Test changes locally on `http://127.0.0.1:7860`.
3. Push to `exp` branch on GitHub:
   ```bash
   git push origin exp
   ```
4. When verified and ready for production:
   ```bash
   git checkout main
   git merge exp --ff-only
   git tag -a vX.Y.Z -m "Release vX.Y.Z description"
   git push origin main --tags
   git push hf main --tags
   git checkout exp
   ```
