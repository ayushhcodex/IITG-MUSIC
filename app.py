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

# 2. Monkey-patch Gradio's FastAPI application creator to mount our FastAPI app as a fallback Mount
original_create_app = gradio.routes.App.create_app

def custom_create_app(*args, **kwargs):
    app = original_create_app(*args, **kwargs)
    
    # Mount our backend FastAPI app at the end of the routing table as a fallback.
    # This ensures Gradio handles its own routes (e.g. startup checks, styling) first,
    # and all other routes (like /index.html, /api/sonify, /outputs/...) fall through to our FastAPI app.
    from starlette.routing import Mount
    app.routes.append(Mount("/", fastapi_app, name="fastapi_fallback"))
    
    print("FastAPI fallback successfully mounted to Gradio App.")
    return app

gradio.routes.App.create_app = custom_create_app

# 3. Create a clean Gradio Blocks app that hosts our web studio inside a same-origin iframe
with gr.Blocks() as demo:
    # Hidden button to satisfy Hugging Face ZeroGPU's check for a GPU-decorated function bound to an event
    btn = gr.Button("ZeroGPU Activator", visible=False)
    btn.click(fn=dummy_gpu_fn)
    
    # Embed the FastAPI application directly in an iframe pointing to our mounted /index.html path.
    # Because it is served from the same domain, it works seamlessly with zero CORS issues.
    gr.HTML('<iframe src="/index.html" style="width:100%; height:950px; border:none; border-radius:8px;"></iframe>')

if __name__ == "__main__":
    # Hugging Face sets PORT environment variable, defaults to 7860 for Spaces
    port = int(os.environ.get("PORT", 7860))
    print(f"Launching Gradio app on port {port}...")
    demo.launch(server_name="0.0.0.0", server_port=port)
