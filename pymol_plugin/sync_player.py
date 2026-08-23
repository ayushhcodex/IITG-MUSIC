import os
import subprocess
import time
from pymol.Qt.QtCore import QObject, QTimer, pyqtSignal, QThread
from pymol import cmd

class AudioThread(QThread):
    def __init__(self, audio_path):
        super().__init__()
        self.audio_path = audio_path
        self.process = None

    def run(self):
        # Use afplay on mac, fallback to other players if on linux/windows
        if os.name == 'posix':
            import platform
            if platform.system() == 'Darwin':
                self.process = subprocess.Popen(['afplay', self.audio_path])
            else:
                self.process = subprocess.Popen(['aplay', self.audio_path])
        else:
            # Windows fallback
            import winsound
            winsound.PlaySound(self.audio_path, winsound.SND_FILENAME)
            
        if self.process:
            self.process.wait()

    def stop(self):
        if self.process:
            self.process.terminate()

class SyncPlayer(QObject):
    def __init__(self):
        super().__init__()
        self.is_playing = False
        self.is_paused = False
        self.timeline = []
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_sync)
        self.audio_thread = None
        
        self.start_time = 0
        self.pause_time = 0
        self.current_idx = 0

    def load_and_play(self, audio_path, timeline_data):
        self.timeline = timeline_data
        self.current_idx = 0
        self.is_playing = True
        self.is_paused = False
        
        self.audio_thread = AudioThread(audio_path)
        self.audio_thread.start()
        
        self.start_time = time.time()
        self.timer.start(50) # 50ms polling

    def pause(self):
        if not self.is_playing: return
        self.is_playing = False
        self.is_paused = True
        self.timer.stop()
        if self.audio_thread:
            self.audio_thread.stop()
        self.pause_time = time.time() - self.start_time

    def resume(self):
        if not self.is_paused: return
        # Note: subprocess playback doesn't support easy resuming from specific timestamp.
        # For a robust implementation, we'd need pygame or QtMultimedia.
        # As a simplified workaround, we restart playback but jump the timer.
        # (Ideally we'd seek the audio).
        self.load_and_play(self.audio_thread.audio_path, self.timeline)

    def stop(self):
        self.is_playing = False
        self.is_paused = False
        self.timer.stop()
        if self.audio_thread:
            self.audio_thread.stop()
        
        # Reset PyMOL visuals
        cmd.color("white", "protein")

    def update_sync(self):
        if not self.is_playing or self.current_idx >= len(self.timeline):
            return
            
        elapsed = time.time() - self.start_time
        
        # Check next event
        next_event = self.timeline[self.current_idx]
        if elapsed >= next_event["time_sec"]:
            self.highlight_residue(next_event)
            self.current_idx += 1

    def highlight_residue(self, event):
        resi = event["sequence"]
        aa = event["amino_acid"]
        
        # PyMOL commands to highlight
        cmd.color("white", "protein")
        cmd.color("red", f"resi {resi}")
        
        # Optional: could show spheres for the active residue
        cmd.hide("spheres", "all")
        cmd.show("spheres", f"resi {resi}")
