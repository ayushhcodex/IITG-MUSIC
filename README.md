# MrFold Music Studio - Molecular Sonification

MrFold Music Studio is a web and desktop tool that translates protein secondary structure and chemical shift data (BMRB / PDB) into Indian Classical Music (Ragas). 

It dynamically maps chemical shift frequencies to notes in different classical Ragas (such as Yaman, Bhairav, Bhupali, Kafi, and Malkauns) and synthesizes multi-track MIDI files into high-quality audio stems using **FluidSynth** and the **TimGM6mb SoundFont**.

---

## Features
- **Protein to Music Translation**: Input a PDB or BMRB ID, or upload your own CSV data, and listen to the sonified protein structure.
- **Raga Customization**: Adjust Raag mood, spectrometer frequency (MHz), and tempo speed.
- **Visual Integration**: Comes with a PyMOL plugin that allows researchers to visualize protein structures in 3D, animated in sync with the generated audio.
- **Multi-platform**: Runs as a web service, a local desktop application, or a PyMOL plugin.

---

## 1. Web Deployment (Render)

The easiest way to make this app accessible to everyone is deploying it to **Render** using the pre-configured Docker setup.

### How it works:
FluidSynth is a C-based system dependency that cannot be installed via `pip`. Using a custom **Docker container** solves this by installing the FluidSynth C libraries directly on the virtual host.

### Setup Instructions:
1. Push this repository to your GitHub/GitLab account.
2. Go to [Render](https://render.com/), click **New +**, and select **Web Service**.
3. Link your repository.
4. Render will automatically detect the `Dockerfile` and configure the service environment as **Docker**.
5. Click **Deploy Web Service**.

### Custom Domain Configuration:
1. In your Render service page, go to **Settings** > **Custom Domains**.
2. Click **Add Custom Domain** and enter your domain name (e.g., `music.mrfold.com`).
3. Set up the DNS records at your domain registrar (GoDaddy, Cloudflare, etc.) using the CNAME or A records provided by Render.

---

## 2. Desktop App (Local Offline Use)

You can run the application locally as a native window using `pywebview`.

### Running Locally:
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Ensure you have FluidSynth installed on your local system:
   - **macOS**: `brew install fluidsynth`
   - **Linux**: `sudo apt-get install fluidsynth`
   - **Windows**: Download FluidSynth binaries and add them to your system `PATH`.
3. Launch the desktop application:
   ```bash
   python desktop.py
   ```

### Bundling with PyInstaller:
To package the app into a standalone `.exe` or `.app` bundle that contains FluidSynth out-of-the-box (so users don't need to install anything):
1. Run the PyInstaller command:
   ```bash
   pyinstaller "MrFold Music.spec"
   ```
2. The standalone bundle will be generated under `dist/MrFold Music/`.

---

## 3. PyMOL Plugin

The [`pymol_plugin/`](./pymol_plugin) folder contains a plugin that integrates MrFold Music into the PyMOL 3D viewer.

### Setup:
1. Zip the `pymol_plugin` directory.
2. In PyMOL, go to **Plugin** > **Plugin Manager** > **Install New Plugin** and upload the zip file.
3. Configure the `API_BASE` in [`pymol_plugin/gui.py`](./pymol_plugin/gui.py) to point to your hosted Render URL (e.g., `https://your-domain.com`) to offload the audio synthesis to your server.
