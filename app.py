# ── 1. ZeroGPU MUST be imported at the very top before anything else ─────────
try:
    import spaces
    @spaces.GPU
    def dummy_gpu_fn(x=None):
        return x or "ZeroGPU Active"
    print("[app.py] Hugging Face ZeroGPU environment detected.")
except (ImportError, Exception):
    def dummy_gpu_fn(x=None):
        return x or "CPU Mode"

import os
import uvicorn
import gradio as gr
from backend_app import app as fastapi_app

# ── 2. Minimal Gradio interface to satisfy ZeroGPU validation ─────────────────
with gr.Blocks(title="MrFold Music Studio") as demo:
    _inp = gr.Textbox(visible=False)
    _out = gr.Textbox(visible=False)
    _btn = gr.Button("ZeroGPU Activator", visible=False)
    _btn.click(fn=dummy_gpu_fn, inputs=_inp, outputs=_out)

# ── 3. Clean integration: Mount Gradio onto our FastAPI application ───────────
# Preserves FastAPI at the root ("/") while registering Gradio at "/gradio"
app = gr.mount_gradio_app(fastapi_app, demo, path="/gradio")

# ── 4. Entrypoint ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    print(f"[app.py] Launching MrFold Music Studio on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
