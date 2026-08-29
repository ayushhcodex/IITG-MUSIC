import uvicorn
import os
import gradio as gr
import gradio.routes
from backend_app import app as fastapi_app
from fastapi.responses import HTMLResponse, FileResponse

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

# Explicitly register endpoints for static assets on fastapi_app to override Gradio's SPA router
@fastapi_app.get("/", response_class=HTMLResponse)
@fastapi_app.get("/index.html", response_class=HTMLResponse)
def read_root():
    with open(os.path.join(STATIC_DIR, "index.html"), "r") as f:
        return HTMLResponse(content=f.read(), status_code=200)

@fastapi_app.get("/app.js")
def read_app_js():
    return FileResponse(os.path.join(STATIC_DIR, "app.js"))

@fastapi_app.get("/style.css")
def read_style_css():
    return FileResponse(os.path.join(STATIC_DIR, "style.css"))

@fastapi_app.get("/icon.png")
def read_icon_png():
    return FileResponse(os.path.join(STATIC_DIR, "icon.png"))

@fastapi_app.get("/favicon.ico")
def read_favicon():
    return FileResponse(os.path.join(STATIC_DIR, "icon.png"))

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
    
    api_routes = []
    static_route = None
    
    for route in fastapi_app.routes:
        # Identify the catch-all static files mount on /
        if hasattr(route, "name") and route.name == "static":
            static_route = route
        else:
            api_routes.append(route)
            
    # Prepend API and output routes so they take precedence over Gradio
    for route in api_routes:
        app.routes.insert(0, route)
        
    # Append the static catch-all mount to the very end so it acts as a fallback,
    # ensuring Gradio's internal routes (like /gradio_api/startup-events) match first.
    if static_route:
        app.routes.append(static_route)
        
    print("FastAPI routes successfully injected into Gradio app with prioritized fallback routing.")
    return app

gradio.routes.App.create_app = custom_create_app

# 3. Create a minimal Gradio Blocks app to trigger the ZeroGPU validation and redirect to our FastAPI app
with gr.Blocks() as demo:
    gr.HTML("<script>window.location.href = window.location.pathname + 'index.html' + window.location.search;</script>")
    gr.Markdown("# Redirecting to MrFold Music Studio...")
    btn = gr.Button("GPU Activator")
    btn.click(fn=dummy_gpu_fn)

if __name__ == "__main__":
    # Hugging Face sets PORT environment variable, defaults to 7860 for Spaces
    port = int(os.environ.get("PORT", 7860))
    print(f"Launching Gradio app on port {port}...")
    demo.launch(server_name="0.0.0.0", server_port=port)
