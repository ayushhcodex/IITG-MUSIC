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
    
    # Prepend our FastAPI routes so they handle requests first (on / and /api)
    for route in fastapi_app.routes:
        app.routes.insert(0, route)
        
    print("FastAPI routes successfully injected into Gradio app.")
    return app

gradio.routes.App.create_app = custom_create_app

# 3. Create a minimal Gradio Blocks app to trigger the ZeroGPU validation
with gr.Blocks() as demo:
    gr.Markdown("# MrFold Music Studio Helper")
    btn = gr.Button("GPU Activator")
    btn.click(fn=dummy_gpu_fn)

if __name__ == "__main__":
    # Hugging Face sets PORT environment variable, defaults to 7860 for Spaces
    port = int(os.environ.get("PORT", 7860))
    print(f"Launching Gradio app on port {port}...")
    demo.launch(server_name="0.0.0.0", server_port=port)
