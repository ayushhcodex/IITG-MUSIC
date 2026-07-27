import threading
import time
import sys
import os
import uvicorn
import webview
from backend_app import app

# Ensure Homebrew and standard local bins are in PATH for macOS app bundle
os.environ["PATH"] += os.pathsep + "/usr/local/bin" + os.pathsep + "/opt/homebrew/bin"

def run_server():
    """Run the FastAPI server in a background thread."""
    # We use uvicorn to run the FastAPI app on a local port.
    # We use port 8555 to avoid conflicts with other local dev servers.
    uvicorn.run(app, host="127.0.0.1", port=8555, log_level="error")

if __name__ == '__main__':
    # Start the local web server in a daemon thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Wait a brief moment to ensure the server starts before the window tries to load it
    time.sleep(1)

    # Create the native desktop window pointing to the local server
    window = webview.create_window(
        title="MrFold Music - Molecular Sonification",
        url="http://127.0.0.1:8555",
        width=1280,
        height=800,
        min_size=(800, 600)
    )
    
    # Start the webview application loop
    webview.start()
    
    # Exiting the webview loop will end the script, 
    # and daemon threads (our server) will automatically terminate.
    sys.exit(0)
