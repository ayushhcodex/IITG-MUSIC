import os
import gradio as gr
import gradio.routes
from backend_app import app as fastapi_app

# ── 1. ZeroGPU stub ──────────────────────────────────────────────────────────
try:
    import spaces
    @spaces.GPU
    def dummy_gpu_fn():
        pass
    print("Hugging Face ZeroGPU environment detected.")
except ImportError:
    def dummy_gpu_fn():
        pass

# ── 2. Patch Gradio's ASGI app to expose /api and /outputs ───────────────────
# Gradio 5/6 SSR runs a Node.js proxy at :7860 that forwards /api/* requests
# to the Python Gradio server at :7861.  We mount our FastAPI sub-application
# at /api inside Gradio's Python ASGI app so those routes are reachable
# publicly at mantisa-mrfold1.hf.space/api/*.
#
# We do NOT use a catch-all Mount("/", ...) — that intercepts Gradio internals.
_original_create_app = gradio.routes.App.create_app

def _patched_create_app(*args, **kwargs):
    """Wrap Gradio's create_app to inject our FastAPI sub-apps."""
    gradio_asgi = _original_create_app(*args, **kwargs)

    try:
        from fastapi.staticfiles import StaticFiles
        OUTPUTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
        os.makedirs(OUTPUTS_DIR, exist_ok=True)

        # Mount our FastAPI (which exposes /api/* routes) at /api inside Gradio's ASGI app
        gradio_asgi.mount("/api", fastapi_app, name="mrfold_api")
        # Mount outputs so audio/MIDI/CSV downloads work at /outputs/*
        gradio_asgi.mount(
            "/outputs",
            StaticFiles(directory=OUTPUTS_DIR, check_dir=False),
            name="mrfold_outputs",
        )
        print("[app.py] ✓ Mounted /api and /outputs into Gradio's Python ASGI app.")
    except Exception as e:
        print(f"[app.py] WARNING: Failed to mount sub-apps: {e}")

    return gradio_asgi

# Replace the classmethod — store the original then reassign as a plain function
gradio.routes.App.create_app = classmethod(_patched_create_app)

# ── 3. Build Gradio UI with full-page iframe ──────────────────────────────────
# The iframe src="/api/" loads our FastAPI app's static/index.html.
# All fetch() calls in app.js use /api/* absolute paths, which resolve
# correctly from inside the iframe to <origin>/api/* = our FastAPI mount.
with gr.Blocks(title="MrFold Music Studio") as demo:
    # Hidden ZeroGPU activator — required by HF ZeroGPU validation
    _btn = gr.Button("ZeroGPU Activator", visible=False)
    _btn.click(fn=dummy_gpu_fn)

    gr.HTML(
        """
        <style>
          .gradio-container { padding: 0 !important; max-width: 100% !important; }
          footer { display: none !important; }
        </style>
        <iframe
          src="/api/"
          style="width:100%; height:96vh; border:none; display:block;"
          allow="autoplay"
          title="MrFold Music Studio"
        ></iframe>
        """,
    )

# ── 4. Launch ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    demo.launch()
else:
    # HF Gradio runner imports app.py as a module
    demo.launch(prevent_thread_lock=True)
