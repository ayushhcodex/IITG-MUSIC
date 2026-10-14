# ── 1. ZeroGPU stub (MUST be at the top level for HF ZeroGPU detector) ────────
try:
    import spaces
    @spaces.GPU
    def dummy_gpu_fn(x=None):
        return x or "ZeroGPU Active"
    print("[app.py] Hugging Face ZeroGPU environment detected.")
except Exception as _e:
    def dummy_gpu_fn(x=None):
        return x or "CPU Mode"
    print(f"[app.py] Running in standard mode: {_e}")

import os
import gradio as gr
import gradio.routes
from backend_app import app as fastapi_app

# ── 2. Patch Gradio's ASGI app to mount our FastAPI backend under /gradio_api ─
# Gradio SSR runs a Node.js proxy at :7860 that forwards /gradio_api/*
# and /run/* requests directly to Python at :7861.
#
# We mount our FastAPI sub-application under the /gradio_api/custom namespace.
# SvelteKit/Node proxy automatically forwards these requests, allowing the
# iframe and frontend fetch calls to reach our FastAPI routes.
_original_create_app = gradio.routes.App.create_app

def _patched_create_app(cls, *args, **kwargs):
    gradio_asgi = _original_create_app(*args, **kwargs)
    try:
        gradio_asgi.mount("/gradio_api/custom", fastapi_app, name="mrfold_custom")
        print("[app.py] ✓ Successfully mounted FastAPI app at /gradio_api/custom.")
    except Exception as e:
        print(f"[app.py] WARNING: Failed to mount FastAPI app: {e}")
    return gradio_asgi

gradio.routes.App.create_app = classmethod(_patched_create_app)

# ── 3. Build Gradio UI with full-page iframe ──────────────────────────────────
gradio_css = """
body, html {
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
  background-color: #07080d !important;
  width: 100vw !important;
  height: 100vh !important;
}
.gradio-container, .gradio-container > .main, .gradio-container .contain, div.gradio-container {
  max-width: 100% !important;
  width: 100vw !important;
  margin: 0 !important;
  padding: 0 !important;
  height: 100vh !important;
  border: none !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  background: #07080d !important;
}
iframe {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  border: none !important;
  margin: 0 !important;
  padding: 0 !important;
  z-index: 999999 !important;
}
"""

with gr.Blocks(title="MrFold Music Studio", fill_width=True, fill_height=True, css=gradio_css) as demo:
    # Hidden ZeroGPU activator — required by HF ZeroGPU startup scanner
    _inp = gr.Textbox(visible=False)
    _out = gr.Textbox(visible=False)
    _btn = gr.Button("ZeroGPU Activator", visible=False)
    _btn.click(fn=dummy_gpu_fn, inputs=_inp, outputs=_out)

    gr.HTML(
        """
        <style>
          html, body, .gradio-container, .main, .contain, #root, gradio-app {
            padding: 0 !important;
            margin: 0 !important;
            max-width: 100% !important;
            width: 100vw !important;
            height: 100vh !important;
            background: #07080d !important;
            overflow: hidden !important;
          }
          footer, header, nav { display: none !important; }
          iframe {
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            width: 100vw !important;
            height: 100vh !important;
            border: none !important;
            margin: 0 !important;
            padding: 0 !important;
            z-index: 999999 !important;
          }
        </style>
        <iframe
          src="/gradio_api/custom/"
          style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; border: none; margin: 0; padding: 0; z-index: 999999;"
          allow="autoplay"
          title="MrFold Music Studio"
        ></iframe>
        """,
    )

# ── 4. Launch natively via Gradio ─────────────────────────────────────────────
# Do NOT call uvicorn.run() manually here — on Hugging Face Spaces (and ZeroGPU),
# the Gradio runner or Node proxy manages port 7860. demo.launch() lets Gradio
# negotiate the port and register its lifecycle hooks seamlessly with ZeroGPU.
if __name__ == "__main__":
    demo.launch()
else:
    demo.launch(prevent_thread_lock=True)
