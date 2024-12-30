from fastapi import FastAPI
from src.interface.ui_manager import UIManager, UIConfig
from src.interface.routes import router

# Create UI Manager
config = UIConfig(
    api_version="v1",
    enable_docs=True,
    enable_metrics=True,
    cors_origins=["http://localhost:3000"]
)
ui_manager = UIManager(config)

# Register routes
ui_manager.app.include_router(router, prefix="/api/v1")
ui_manager.register_routes()

# Get FastAPI application
app = ui_manager.app 