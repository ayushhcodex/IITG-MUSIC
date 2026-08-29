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

# ── 2. Patch Gradio's ASGI app to expose our FastAPI app under /gradio_api ────
# Gradio 5/6 SSR runs a Node.js proxy at :7860 that forwards /gradio_api/*
# and /run/* requests directly to Python at :7861.
#
# We mount our FastAPI sub-application under the /gradio_api/custom namespace.
# Sveltekit Node proxy will automatically forward these requests, allowing the
# iframe and frontend fetch calls to reach our FastAPI routes.
_original_create_app = gradio.routes.App.create_app

def _patched_create_app(cls, *args, **kwargs):
    """Wrap Gradio's create_app to inject our FastAPI sub-apps.
    cls is explicitly captured so it is NOT forwarded in *args to the original
    bound method (which already has cls=App pre-bound). Without this, args[0]
    would be App instead of the Blocks instance, causing blocks.get_config_file()
    to fail with 'type object App has no attribute get_config_file'.
    """
    gradio_asgi = _original_create_app(*args, **kwargs)

    try:
        # Mount our FastAPI (which contains /api/* and /outputs/* sub-mounts)
        # at /gradio_api/custom inside Gradio's ASGI app.
        gradio_asgi.mount("/gradio_api/custom", fastapi_app, name="mrfold_custom")
        print("[app.py] ✓ Mounted FastAPI app at /gradio_api/custom.")
    except Exception as e:
        print(f"[app.py] WARNING: Failed to mount FastAPI app: {e}")

    return gradio_asgi

# Replace the classmethod — store the original then reassign as a plain function
gradio.routes.App.create_app = classmethod(_patched_create_app)

# ── 3. Build Gradio UI with full-page iframe ──────────────────────────────────
# The iframe src="/gradio_api/custom/" loads our FastAPI app's static/index.html.
# All fetch() calls in app.js use relative paths prefixed by API_PREFIX (/gradio_api/custom),
# ensuring they go through the Node proxy and hit the custom mount.
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
          src="/gradio_api/custom/"
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
