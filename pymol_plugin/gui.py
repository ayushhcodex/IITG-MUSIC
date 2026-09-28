import os
import urllib.request
import urllib.parse
import json
import csv
import ssl
from pymol.Qt import QtCore, QtWidgets
from pymol.Qt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QComboBox, QDoubleSpinBox, QMessageBox,
    QFileDialog, QGroupBox, QFormLayout
)
from pymol.Qt.QtCore import Qt, QThread, pyqtSignal
from pymol import cmd

# Local imports
from sync_player import SyncPlayer

DEFAULT_SERVER = "https://mantisa-mrfold1.hf.space"

class Worker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, base_url, endpoint, data=None, is_post=False):
        super().__init__()
        self.base_url = base_url.rstrip('/')
        self.endpoint = endpoint
        self.data = data
        self.is_post = is_post

    def run(self):
        ctx = ssl._create_unverified_context()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json'
        }
        
        # Build candidate endpoints list to support HF Space mounts, direct FastAPI, and legacy routes
        if self.endpoint.startswith("/fetch_online"):
            query_val = self.endpoint.split("query=")[-1]
            candidate_paths = [
                f"/gradio_api/custom/api/fetch/{query_val}",
                f"/api/fetch/{query_val}",
                f"/fetch_online?query={query_val}"
            ]
        elif self.endpoint.startswith("/sonify"):
            candidate_paths = [
                "/gradio_api/custom/api/sonify",
                "/api/sonify",
                "/sonify"
            ]
        else:
            candidate_paths = [self.endpoint]

        last_error = None
        for path in candidate_paths:
            url = f"{self.base_url}{path}"
            try:
                if self.is_post:
                    post_headers = dict(headers)
                    post_headers['Content-Type'] = 'application/json'
                    req = urllib.request.Request(url, data=json.dumps(self.data).encode('utf-8'), headers=post_headers)
                else:
                    req = urllib.request.Request(url, headers=headers)
                
                with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
                    content = response.read().decode('utf-8')
                    if content.startswith('{'):
                        result = json.loads(content)
                        self.finished.emit(result)
                        return
                    else:
                        last_error = f"Non-JSON response from {url}"
            except Exception as e:
                last_error = f"Failed {url}: {e}"

        self.error.emit(last_error or "Unable to connect to server endpoints.")


class CosmicRagaDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MrFold Music Studio — PyMOL")
        self.setMinimumWidth(440)
        
        self.current_dataset = None
        self.bmrb_id = ""
        self.timeline_data = None
        self.audio_path = None
        self.export_urls = {}
        
        self.player = SyncPlayer()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 0. Server Connection
        group_server = QGroupBox("⚡ Server Connection")
        form_server = QFormLayout()
        
        self.input_server = QLineEdit(DEFAULT_SERVER)
        btn_hf = QPushButton("🌐 HF Space")
        btn_local = QPushButton("💻 Local")
        btn_hf.clicked.connect(lambda: self.input_server.setText("https://mantisa-mrfold1.hf.space"))
        btn_local.clicked.connect(lambda: self.input_server.setText("http://127.0.0.1:8000"))
        
        row_server_btns = QHBoxLayout()
        row_server_btns.addWidget(self.input_server)
        row_server_btns.addWidget(btn_hf)
        row_server_btns.addWidget(btn_local)
        
        form_server.addRow("Server URL:", row_server_btns)
        group_server.setLayout(form_server)
        layout.addWidget(group_server)

        # 1. Data Source
        group_data = QGroupBox("1. Protein Data Source")
        form_data = QFormLayout()
        
        self.input_pdb = QLineEdit("1DMB")
        btn_fetch = QPushButton("⚡ Load Data & 3D")
        btn_fetch.setStyleSheet("background-color: #00f2fe; color: #07080d; font-weight: bold;")
        btn_fetch.clicked.connect(self.fetch_data)
        
        row_fetch = QHBoxLayout()
        row_fetch.addWidget(self.input_pdb)
        row_fetch.addWidget(btn_fetch)
        
        form_data.addRow("PDB / BMRB ID:", row_fetch)
        group_data.setLayout(form_data)
        layout.addWidget(group_data)
        
        # 2. Studio Customization
        group_studio = QGroupBox("2. Music Generation Studio")
        form_studio = QFormLayout()
        
        self.combo_raag = QComboBox()
        self.combo_raag.addItems(["Yaman", "Bhairav", "Bhupali", "Kafi", "Malkauns", "Khamaaz"])
        
        self.spin_spectro = QDoubleSpinBox()
        self.spin_spectro.setRange(100, 1500)
        self.spin_spectro.setValue(750.0)
        self.spin_spectro.setSuffix(" MHz")
        
        self.spin_tempo = QDoubleSpinBox()
        self.spin_tempo.setRange(0.25, 3.0)
        self.spin_tempo.setValue(1.0)
        self.spin_tempo.setSingleStep(0.25)
        
        form_studio.addRow("Raag Mood:", self.combo_raag)
        form_studio.addRow("Spectrometer:", self.spin_spectro)
        form_studio.addRow("Tempo Speed:", self.spin_tempo)
        
        btn_generate = QPushButton("🎼 Synthesize Music Stems")
        btn_generate.setStyleSheet("background-color: #f857a6; color: white; font-weight: bold; padding: 8px;")
        btn_generate.clicked.connect(self.generate_music)
        form_studio.addRow(btn_generate)
        
        group_studio.setLayout(form_studio)
        layout.addWidget(group_studio)
        
        # 3. Playback & Export
        group_play = QGroupBox("3. Synchronized Audio Playback")
        layout_play = QVBoxLayout()
        
        self.lbl_status = QLabel("Ready — Enter PDB/BMRB ID to start")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setStyleSheet("color: #00f2fe; font-weight: 600;")
        
        row_play = QHBoxLayout()
        self.btn_play = QPushButton("▶ Play Synced Audio")
        self.btn_play.setEnabled(False)
        self.btn_play.clicked.connect(self.toggle_play)
        
        self.btn_stop = QPushButton("⏹ Stop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_play)
        
        row_play.addWidget(self.btn_play)
        row_play.addWidget(self.btn_stop)
        
        row_export = QHBoxLayout()
        self.btn_export = QPushButton("💾 Download Artifacts (WAV/MIDI/CSV)")
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self.download_artifacts)
        row_export.addWidget(self.btn_export)
        
        layout_play.addWidget(self.lbl_status)
        layout_play.addLayout(row_play)
        layout_play.addLayout(row_export)
        group_play.setLayout(layout_play)
        
        layout.addWidget(group_play)
        self.setLayout(layout)

    def get_server_url(self):
        url = self.input_server.text().strip()
        if not url:
            url = DEFAULT_SERVER
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        return url.rstrip('/')

    def resolve_full_url(self, path):
        if not path:
            return ""
        if path.startswith("http://") or path.startswith("https://"):
            return path
        base = self.get_server_url()
        if path.startswith("/"):
            return f"{base}{path}"
        return f"{base}/{path}"

    def fetch_data(self):
        query = self.input_pdb.text().strip()
        if not query:
            QMessageBox.warning(self, "Error", "Please enter a PDB or BMRB ID.")
            return
            
        self.lbl_status.setText("Fetching dataset from server...")
        
        self.worker = Worker(self.get_server_url(), f"/fetch_online?query={query}")
        self.worker.finished.connect(self.on_fetch_success)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_fetch_success(self, res):
        if "error" in res:
            self.on_error(res["error"])
            return
            
        # Support both 'rows' (FastAPI schema) and 'dataset' (legacy schema)
        self.current_dataset = res.get("rows") or res.get("dataset") or []
        self.bmrb_id = res.get("bmrb_id", "")
        self.lbl_status.setText(f"Dataset loaded: {len(self.current_dataset)} residues.")
        
        # Load 3D molecular structure into PyMOL canvas
        pdb_id = self.input_pdb.text().strip().upper()
        if len(pdb_id) == 4:
            try:
                cmd.fetch(pdb_id, "protein", async_=0)
                cmd.hide("everything", "all")
                cmd.show("cartoon", "protein")
                cmd.color("white", "protein")
                cmd.zoom("protein")
            except Exception as e:
                print(f"[pymol] Structure fetch notice: {e}")

    def generate_music(self):
        if not self.current_dataset:
            QMessageBox.warning(self, "Error", "Please load a dataset first using 'Load Data & 3D'.")
            return
            
        self.lbl_status.setText("Synthesizing Raga sonification on server...")
        
        payload = {
            "dataset": self.current_dataset,
            "raag_name": self.combo_raag.currentText(),
            "root_note": 60,
            "tempo_multiplier": self.spin_tempo.value(),
            "spectrometer_mhz": self.spin_spectro.value(),
            "pdb_id": self.input_pdb.text().strip().upper(),
            "bmrb_id": self.bmrb_id
        }
        
        self.worker = Worker(self.get_server_url(), "/sonify", data=payload, is_post=True)
        self.worker.finished.connect(self.on_generate_success)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_generate_success(self, res):
        if "error" in res:
            self.on_error(res["error"])
            return
            
        self.timeline_data = res.get("timeline") or res.get("timeline_data") or []
        
        wav_url = self.resolve_full_url(res.get("audio_url") or res.get("wav_url"))
        mid_url = self.resolve_full_url(res.get("midi_url") or res.get("mid_url"))
        csv_url = self.resolve_full_url(res.get("csv_url") or res.get("timeline_url"))
        
        # Download WAV to temporary location for PyMOL audio playback
        import tempfile
        self.audio_path = os.path.join(tempfile.gettempdir(), "mrfold_raga_temp.wav")
        ctx = ssl._create_unverified_context()
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        
        try:
            req = urllib.request.Request(wav_url, headers=headers)
            with urllib.request.urlopen(req, context=ctx) as response, open(self.audio_path, 'wb') as out_file:
                out_file.write(response.read())

            self.lbl_status.setText("Synthesis complete! Ready for synced playback.")
            self.btn_play.setEnabled(True)
            self.btn_stop.setEnabled(True)
            self.btn_export.setEnabled(True)
            
            # Save download URLs for export
            self.export_urls = {
                "wav": wav_url,
                "mid": mid_url,
                "csv": csv_url
            }
        except Exception as e:
            self.on_error(f"Failed to download audio for playback: {e}")

    def on_error(self, err_msg):
        self.lbl_status.setText("Connection / Processing Error.")
        QMessageBox.critical(self, "Error", str(err_msg))

    def toggle_play(self):
        if self.player.is_playing:
            self.player.pause()
            self.btn_play.setText("▶ Resume")
        else:
            if self.player.is_paused:
                self.player.resume()
            else:
                self.player.load_and_play(self.audio_path, self.timeline_data)
            self.btn_play.setText("⏸ Pause")

    def stop_play(self):
        self.player.stop()
        self.btn_play.setText("▶ Play Synced Audio")

    def download_artifacts(self):
        out_dir = QFileDialog.getExistingDirectory(self, "Select Directory to Save Artifacts")
        if not out_dir:
            return
            
        ctx = ssl._create_unverified_context()
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}

        def download_file(url, target_path):
            if not url: return
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=ctx) as response, open(target_path, 'wb') as out_file:
                out_file.write(response.read())

        try:
            download_file(self.export_urls.get("wav"), os.path.join(out_dir, "music.wav"))
            download_file(self.export_urls.get("mid"), os.path.join(out_dir, "music.mid"))
            download_file(self.export_urls.get("csv"), os.path.join(out_dir, "timeline.csv"))
            QMessageBox.information(self, "Success", f"Artifacts successfully saved to:\n{out_dir}")
        except Exception as e:
            self.on_error(f"Failed to save artifacts: {e}")

def show_gui():
    dialog = CosmicRagaDialog()
    dialog.exec_()
