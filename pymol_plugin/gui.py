import os
import urllib.request
import urllib.parse
import json
import csv
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

API_BASE = "http://127.0.0.1:8000"

class Worker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, endpoint, data=None, is_post=False):
        super().__init__()
        self.endpoint = endpoint
        self.data = data
        self.is_post = is_post

    def run(self):
        try:
            url = f"{API_BASE}{self.endpoint}"
            if self.is_post:
                req = urllib.request.Request(url, data=json.dumps(self.data).encode('utf-8'),
                                             headers={'Content-Type': 'application/json'})
                response = urllib.request.urlopen(req)
            else:
                response = urllib.request.urlopen(url)
            
            result = json.loads(response.read().decode('utf-8'))
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class CosmicRagaDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MrFold Music Studio - PyMOL")
        self.setMinimumWidth(400)
        
        self.current_dataset = None
        self.bmrb_id = ""
        self.timeline_data = None
        self.audio_path = None
        
        self.player = SyncPlayer()
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 1. Data Source
        group_data = QGroupBox("1. Protein Data Source")
        form_data = QFormLayout()
        
        self.input_pdb = QLineEdit("1DMB")
        btn_fetch = QPushButton("⚡ Load Online")
        btn_fetch.clicked.connect(self.fetch_data)
        
        row_fetch = QHBoxLayout()
        row_fetch.addWidget(self.input_pdb)
        row_fetch.addWidget(btn_fetch)
        
        form_data.addRow("PDB / BMRB ID:", row_fetch)
        group_data.setLayout(form_data)
        layout.addWidget(group_data)
        
        # 2. Studio Customization
        group_studio = QGroupBox("2. Raga Customization Studio")
        form_studio = QFormLayout()
        
        self.combo_raag = QComboBox()
        self.combo_raag.addItems(["Yaman", "Bhairav", "Bhupali", "Kafi", "Malkauns"])
        
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
        
        btn_generate = QPushButton("🎼 Generate Music")
        btn_generate.setStyleSheet("background-color: #f857a6; color: white; font-weight: bold; padding: 8px;")
        btn_generate.clicked.connect(self.generate_music)
        form_studio.addRow(btn_generate)
        
        group_studio.setLayout(form_studio)
        layout.addWidget(group_studio)
        
        # 3. Playback & Export
        group_play = QGroupBox("3. Synchronized Playback")
        layout_play = QVBoxLayout()
        
        self.lbl_status = QLabel("Ready")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        
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
        self.btn_export = QPushButton("💾 Download Artifacts")
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self.download_artifacts)
        row_export.addWidget(self.btn_export)
        
        layout_play.addWidget(self.lbl_status)
        layout_play.addLayout(row_play)
        layout_play.addLayout(row_export)
        group_play.setLayout(layout_play)
        
        layout.addWidget(group_play)
        self.setLayout(layout)

    def fetch_data(self):
        query = self.input_pdb.text().strip()
        if not query:
            QMessageBox.warning(self, "Error", "Please enter a PDB or BMRB ID.")
            return
            
        self.lbl_status.setText("Fetching dataset from backend...")
        
        self.worker = Worker(f"/fetch_online?query={query}")
        self.worker.finished.connect(self.on_fetch_success)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_fetch_success(self, res):
        if "error" in res:
            self.on_error(res["error"])
            return
            
        self.current_dataset = res.get("dataset", [])
        self.bmrb_id = res.get("bmrb_id", "")
        self.lbl_status.setText(f"Dataset loaded: {len(self.current_dataset)} residues.")
        
        pdb_id = self.input_pdb.text().strip().upper()
        if len(pdb_id) == 4:
            cmd.fetch(pdb_id, "protein", async_=0)
            cmd.hide("everything", "all")
            cmd.show("cartoon", "protein")
            cmd.color("white", "protein")
            cmd.zoom("protein")

    def generate_music(self):
        if not self.current_dataset:
            QMessageBox.warning(self, "Error", "Please load a dataset first.")
            return
            
        self.lbl_status.setText("Generating music on backend...")
        
        payload = {
            "dataset": self.current_dataset,
            "raag_name": self.combo_raag.currentText(),
            "root_note": 60,
            "tempo_multiplier": self.spin_tempo.value(),
            "spectrometer_mhz": self.spin_spectro.value(),
            "pdb_id": self.input_pdb.text().strip().upper(),
            "bmrb_id": self.bmrb_id
        }
        
        self.worker = Worker("/sonify", data=payload, is_post=True)
        self.worker.finished.connect(self.on_generate_success)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_generate_success(self, res):
        if "error" in res:
            self.on_error(res["error"])
            return
            
        self.timeline_data = res.get("timeline", [])
        
        wav_url = f"{API_BASE}{res['wav_url']}"
        mid_url = f"{API_BASE}{res['mid_url']}"
        csv_url = f"{API_BASE}{res['csv_url']}"
        
        # Download WAV to a temp file for playback
        import tempfile
        self.audio_path = os.path.join(tempfile.gettempdir(), "cosmic_raga_temp.wav")
        try:
            urllib.request.urlretrieve(wav_url, self.audio_path)
            self.lbl_status.setText("Generation complete! Ready to play.")
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
        self.lbl_status.setText("Error occurred.")
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
            
        try:
            urllib.request.urlretrieve(self.export_urls["wav"], os.path.join(out_dir, "music.wav"))
            urllib.request.urlretrieve(self.export_urls["mid"], os.path.join(out_dir, "music.mid"))
            urllib.request.urlretrieve(self.export_urls["csv"], os.path.join(out_dir, "timeline.csv"))
            QMessageBox.information(self, "Success", f"Artifacts saved to {out_dir}")
        except Exception as e:
            self.on_error(f"Failed to save artifacts: {e}")

def show_gui():
    dialog = CosmicRagaDialog()
    dialog.exec_()
