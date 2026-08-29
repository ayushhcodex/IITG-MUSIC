import uvicorn
import os
from backend_app import app

# Defensively add a dummy @spaces.GPU function to satisfy Hugging Face ZeroGPU validation
try:
    import spaces
    @spaces.GPU
    def dummy_gpu_fn():
        pass
    print("ZeroGPU environment detected and configured.")
except ImportError:
    pass

if __name__ == "__main__":
    # Hugging Face sets PORT environment variable, defaults to 7860 for Spaces
    port = int(os.environ.get("PORT", 7860))
    print(f"Starting MrFold Music FastAPI Server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
