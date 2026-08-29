import uvicorn
import os
from backend_app import app as fastapi_app

# Defensively mount Gradio to satisfy Hugging Face ZeroGPU validation checks
try:
    import gradio as gr
    
    try:
        import spaces
        @spaces.GPU
        def dummy_gpu_fn():
            pass
        print("Hugging Face ZeroGPU environment detected.")
    except ImportError:
        def dummy_gpu_fn():
            pass

    with gr.Blocks() as demo:
        gr.Markdown("# MrFold Music Studio backend helper")
        btn = gr.Button("Activate GPU")
        btn.click(fn=dummy_gpu_fn)

    app = gr.mount_gradio_app(fastapi_app, demo, path="/helper")
except ImportError:
    print("Gradio not installed. Falling back to pure FastAPI.")
    app = fastapi_app

if __name__ == "__main__":
    # Hugging Face sets PORT environment variable, defaults to 7860 for Spaces
    port = int(os.environ.get("PORT", 7860))
    print(f"Starting MrFold Music Server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
