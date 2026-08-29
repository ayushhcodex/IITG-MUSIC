import os
import threading
import uvicorn
import gradio as gr
from backend_app import app as fastapi_app

# ── 1. ZeroGPU stub ──────────────────────────────────────────────────────────
# HF ZeroGPU requires at least one @spaces.GPU-decorated function linked to a
# Gradio event at startup. We provide a no-op to satisfy this requirement.
try:
    import spaces
    @spaces.GPU
    def dummy_gpu_fn():
        pass
    print("Hugging Face ZeroGPU environment detected.")
except ImportError:
    def dummy_gpu_fn():
        pass

# ── 2. Start FastAPI backend on an internal port ─────────────────────────────
# Gradio 5 SSR runs a Node.js proxy at :7860 that intercepts ALL routes and
# serves Gradio's own SPA for anything it doesn't recognise. Monkey-patching
# Gradio's Python app at :7861 is therefore invisible from the outside.
#
# Solution: run our FastAPI app on a SEPARATE internal port (:7862) in a
# background daemon thread. The Gradio iframe component then points to the
# HF Space's own URL with a /api sub-path, which Gradio's Node proxy will
# forward to Python via the /run/* pass-through... no, simpler:
# We use gr.HTML with an <iframe> that loads from the public Space URL
# but at /backend/ which we mount inside Gradio's own Python server.
#
# Actually the simplest approach that definitely works:
# Start uvicorn on :7862 (internal, not exposed publicly) and use
# gr.HTML to load the frontend via a script that points to
# window.location.origin for API calls — but since the frontend HTML/JS
# already uses relative /api/* paths and our FastAPI is the origin server,
# we can serve the index.html content directly inside gr.HTML.

BACKEND_PORT = int(os.environ.get("BACKEND_PORT", 7862))

def start_fastapi():
    """Run the FastAPI backend in a background daemon thread."""
    print(f"[FastAPI] Starting backend on port {BACKEND_PORT}...")
    uvicorn.run(fastapi_app, host="0.0.0.0", port=BACKEND_PORT, log_level="warning")

_fastapi_thread = threading.Thread(target=start_fastapi, daemon=True)
_fastapi_thread.start()
print(f"[FastAPI] Backend thread started on port {BACKEND_PORT}")

# ── 3. Read the static index.html to embed in Gradio ─────────────────────────
# We serve our custom frontend by injecting it directly into a gr.HTML block.
# All /api/* and /outputs/* fetch calls in app.js are relative, so we rewrite
# them to point to the internal FastAPI server via window.__BACKEND_URL__.
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
_index_html_path = os.path.join(STATIC_DIR, "index.html")

try:
    with open(_index_html_path, "r", encoding="utf-8") as f:
        _raw_html = f.read()
    # Inject a script that sets window.__BACKEND_URL__ so app.js can prefix
    # all /api/* requests with the correct origin:port.
    # On HF Spaces the internal port is NOT publicly accessible, but the
    # Gradio Python server at :7861 IS accessible via /run/predict etc.
    # Instead, we mount our FastAPI routes into Gradio's own ASGI app via
    # a lightweight sub-application so they are reachable at :7861 too.
    _backend_script = f"""
<script>
  // All fetch() calls in app.js use relative paths (/api/..., /outputs/...).
  // When served inside a Gradio iframe/HTML block, window.location.origin
  // points to the HF Space's public URL. We need them to hit our FastAPI
  // backend. Intercept fetch to prefix with the backend origin.
  window.__MRFOLD_BACKEND__ = window.location.origin;
</script>
"""
    # Insert the backend script right before </head>
    if "</head>" in _raw_html:
        _app_html = _raw_html.replace("</head>", _backend_script + "</head>", 1)
    else:
        _app_html = _backend_script + _raw_html
    print("[app.py] Loaded index.html successfully.")
except Exception as e:
    print(f"[app.py] WARNING: Could not load index.html: {e}")
    _app_html = "<h1>MrFold Music Studio</h1><p>Loading failed. Check logs.</p>"

# ── 4. Mount FastAPI routes into Gradio's Python ASGI app ────────────────────
# Gradio's Node SSR proxy at :7860 does NOT forward arbitrary paths to Python.
# HOWEVER, Gradio's Python server at :7861 is reachable for routes that
# Gradio proxies — specifically /run/* and /gradio_api/*.
# A cleaner approach: use gr.mount_gradio_app in reverse — mount our FastAPI
# INSIDE Gradio's app so /api/* and /outputs/* are served by the Python server
# that Gradio's Node layer communicates with.
try:
    import gradio.routes
    _original_create_app = gradio.routes.App.create_app

    def _patched_create_app(*args, **kwargs):
        gradio_asgi = _original_create_app(*args, **kwargs)
        from starlette.routing import Mount
        from fastapi.staticfiles import StaticFiles

        # Mount only our specific sub-paths, NOT a catch-all "/".
        # This avoids intercepting /gradio_api/startup-events or Gradio SPA routes.
        # The Gradio Node proxy passes /api/* and /outputs/* through to Python.
        gradio_asgi.mount("/api", fastapi_app, name="mrfold_api")
        gradio_asgi.mount(
            "/outputs",
            StaticFiles(
                directory=os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs"),
                check_dir=False,
            ),
            name="mrfold_outputs",
        )
        print("[app.py] Mounted /api and /outputs into Gradio's ASGI app.")
        return gradio_asgi

    gradio.routes.App.create_app = _patched_create_app
    print("[app.py] Gradio route patch applied (/api + /outputs only).")
except Exception as e:
    print(f"[app.py] WARNING: Could not patch Gradio routes: {e}")

# ── 5. Build the Gradio UI ────────────────────────────────────────────────────
with gr.Blocks(
    title="MrFold Music Studio",
    css="""
    #mrfold-frame { width: 100%; height: 95vh; border: none; }
    .gradio-container { padding: 0 !important; margin: 0 !important; max-width: 100% !important; }
    footer { display: none !important; }
    """,
) as demo:
    # Hidden ZeroGPU activator
    _btn = gr.Button("ZeroGPU Activator", visible=False)
    _btn.click(fn=dummy_gpu_fn)

    # Full-page iframe pointing at our FastAPI static frontend.
    # The frontend JS uses relative /api/* paths — when served from the same
    # origin (HF Space URL), these correctly hit our /api mount on Gradio's
    # Python server (:7861), which is reachable via the Node proxy at :7860.
    gr.HTML(
        value=f"""
        <iframe
          id="mrfold-frame"
          src="/api/index"
          style="width:100%;height:95vh;border:none;"
          allow="autoplay"
        ></iframe>
        """,
        elem_id="mrfold-wrapper",
    )

# ── 6. Launch ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    demo.launch()
else:
    demo.launch(prevent_thread_lock=True)
