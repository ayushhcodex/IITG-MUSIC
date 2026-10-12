# ── 1. ZeroGPU stub (MUST BE AT THE VERY TOP OF THE FILE) ────────────────────
try:
    import spaces
    @spaces.GPU
    def dummy_gpu_fn():
        pass
    print("[app.py] Hugging Face ZeroGPU environment detected.")
except ImportError:
    def dummy_gpu_fn():
        pass

import os
import gradio as gr
from backend_app import app as fastapi_app

# ── 2. Minimal Gradio interface to satisfy ZeroGPU validation ─────────────────
with gr.Blocks(title="MrFold Music Studio") as demo:
    _btn = gr.Button("ZeroGPU Activator", visible=False)
    _btn.click(fn=dummy_gpu_fn)

# ── 3. Clean integration: Mount Gradio onto the existing FastAPI application ──
# This preserves FastAPI at the root:
# - "/" serves static/index.html (the full MrFold Music UI directly, no iframe!)
# - "/api/*" and "/outputs/*" work directly without any proxy/iframe hacks
# - "/gradio" hosts the Gradio interface to satisfy HF ZeroGPU requirements
app = gr.mount_gradio_app(fastapi_app, demo, path="/gradio")

# ── 4. Entrypoint ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    print(f"[app.py] Launching combined FastAPI + Gradio server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
