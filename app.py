import uvicorn
import os
import gradio as gr
import gradio.routes
from backend_app import app as fastapi_app

# 1. Define the dummy spaces.GPU function that Hugging Face ZeroGPU requires at startup
try:
    import spaces
    @spaces.GPU
    def dummy_gpu_fn():
        pass
    print("Hugging Face ZeroGPU environment detected.")
except ImportError:
    def dummy_gpu_fn():
        pass

# 2. Monkey-patch Gradio's FastAPI application creator to inject our FastAPI app routes
original_create_app = gradio.routes.App.create_app

def custom_create_app(*args, **kwargs):
    app = original_create_app(*args, **kwargs)
    
    # Print routes for container log debugging
    print("--- Original Gradio Routes ---")
    for idx, r in enumerate(app.routes):
        print(f"{idx:02d}: {getattr(r, 'path', 'No Path')} ({type(r).__name__})")
        
    # Find the EXACT root-level SPA catch-all in Gradio's route list.
    # Deliberately avoid matching sub-path wildcards like /gradio_api/{api_name:path}
    # or /run/{api_name} — those must remain handled by Gradio BEFORE our Mount.
    # We only intercept Gradio's final root catch-all ("/" or "/{path:path}").
    target_idx = len(app.routes)
    for idx, route in enumerate(app.routes):
        path = getattr(route, "path", "")
        # Match only the absolute root-level catch-all patterns
        if path in ("/", "/{path:path}"):
            target_idx = idx
            break

    # Insert our FastAPI app as a fallback Mount right before Gradio's root catch-all.
    # Gradio's explicit routes (/gradio_api/*, /run/*, /upload, etc.) stay BEFORE our
    # Mount and are matched first by Starlette. Our Mount only handles what falls through.
    from starlette.routing import Mount
    app.routes.insert(target_idx, Mount("/", fastapi_app, name="fastapi_fallback"))

    print(f"FastAPI fallback successfully inserted at index {target_idx} of Gradio routing table.")

    print("--- Injected Gradio Routes ---")
    for idx, r in enumerate(app.routes):
        print(f"{idx:02d}: {getattr(r, 'path', 'No Path')} ({type(r).__name__})")

    return app

gradio.routes.App.create_app = custom_create_app

# 3. Create a clean Gradio Blocks app to trigger the ZeroGPU validation
with gr.Blocks() as demo:
    # Hidden button to satisfy Hugging Face ZeroGPU's check for a GPU-decorated function bound to an event
    btn = gr.Button("ZeroGPU Activator", visible=False)
    btn.click(fn=dummy_gpu_fn)

    # Direct message in case the fallback Mount is bypassed (should not happen)
    gr.Markdown("# MrFold Music Studio is loading...")

# 4. Launch — do NOT hardcode server_port or server_name.
# Gradio 5 on HF Spaces uses SSR mode: Node proxy at :7860, Python at :7861.
# Forcing server_port=7860 on the Python process conflicts with the Node proxy
# and causes the /gradio_api/startup-events check to return 404.
# Let HF Spaces / Gradio manage port binding via its own environment variables.
if __name__ == "__main__":
    print("Launching Gradio app (HF Spaces manages port via env)...")
    demo.launch()
else:
    # HF Gradio runner imports app.py as a module — launch() must be called at module level.
    print("[HF runner] Launching Gradio app (module-level import)...")
    demo.launch(prevent_thread_lock=True)
