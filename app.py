import os
import uvicorn
from backend_app import app as fastapi_app

# ── 1. ZeroGPU stub (detects HF ZeroGPU environment) ──────────────────────────
try:
    import spaces
    @spaces.GPU
    def dummy_gpu_fn():
        return "ZeroGPU Active"
    print("[app.py] Hugging Face ZeroGPU environment detected.")
except ImportError:
    def dummy_gpu_fn():
        return "CPU Mode"

import gradio as gr

# ── 2. Minimal Gradio interface to satisfy ZeroGPU validation ─────────────────
with gr.Blocks(title="MrFold Music Studio") as demo:
    _btn = gr.Button("ZeroGPU Activator", visible=False)
    _btn.click(fn=dummy_gpu_fn)

# ── 3. Clean integration: Mount Gradio onto our FastAPI application ───────────
# This preserves FastAPI at the root:
# - "/" serves static/index.html (the full MrFold Music UI directly, no iframe!)
# - "/api/*" endpoints and "/outputs/*" work directly without any proxy hacks
# - "/gradio" hosts the Gradio interface to satisfy HF ZeroGPU requirements
app = gr.mount_gradio_app(fastapi_app, demo, path="/gradio")

# ── 4. Entrypoint ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    print(f"[app.py] Launching MrFold Music Studio on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
