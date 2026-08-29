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
# Gradio 5 SSR runs a Node.js proxy at :7860 (public) that forwards requests
# to the Python Gradio server at :7861.  The Node proxy forwards /api/* and
# /run/* to Python.  We mount our FastAPI sub-application at /api inside
# Gradio's Python ASGI app so those routes are reachable from the public URL.
#
# We do NOT use a catch-all Mount("/", ...) — that intercepts Gradio internals.
# Instead we mount ONLY /api and /outputs as named sub-apps.
_original_create_app = gradio.routes.App.create_app

@classmethod  # type: ignore[misc]
def _patched_create_app(cls, *args, **kwargs):
    gradio_asgi = _original_create_app.__func__(cls, *args, **kwargs)

    try:
        from fastapi.staticfiles import StaticFiles
        OUTPUTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
        os.makedirs(OUTPUTS_DIR, exist_ok=True)

        # Mount our FastAPI (which exposes /api/* routes) at /api
        gradio_asgi.mount("/api", fastapi_app, name="mrfold_api")
        # Mount outputs separately so audio/MIDI downloads work
        gradio_asgi.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR, check_dir=False), name="mrfold_outputs")
        print("[app.py] ✓ Mounted /api and /outputs into Gradio's Python ASGI app.")
    except Exception as e:
        print(f"[app.py] WARNING: Failed to mount sub-apps: {e}")

    return gradio_asgi

gradio.routes.App.create_app = _patched_create_app

# ── 3. Build Gradio UI with full-page iframe ──────────────────────────────────
# The iframe src="/api/" loads our FastAPI app's HTML frontend.
# Since FastAPI mounts StaticFiles at "/" inside the /api mount, "/api/"
# serves static/index.html.  All fetch() calls in app.js use relative paths
# like /api/presets — these work correctly when the page is at /api/.
# Audio/MIDI files are at /outputs/... which is also mounted on the same origin.
with gr.Blocks(
    title="MrFold Music Studio",
    css="""
    #mrfold-wrapper { padding: 0; margin: 0; }
    #mrfold-wrapper > .block { padding: 0 !important; }
    .gradio-container { padding: 0 !important; max-width: 100% !important; }
    footer { display: none !important; }
    """,
) as demo:
    # Hidden ZeroGPU activator — required by HF ZeroGPU validation
    _btn = gr.Button("ZeroGPU Activator", visible=False)
    _btn.click(fn=dummy_gpu_fn)

    gr.HTML(
        """
        <iframe
          src="/api/"
          style="width:100%; height:96vh; border:none; display:block;"
          allow="autoplay"
          title="MrFold Music Studio"
        ></iframe>
        """,
        elem_id="mrfold-wrapper",
    )

# ── 4. Launch ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    demo.launch()
else:
    # HF Gradio runner imports app.py as a module
    demo.launch(prevent_thread_lock=True)
