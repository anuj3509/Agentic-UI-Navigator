#!/usr/bin/env python3
"""
FastAPI server to connect the frontend with the app.py backend.
Provides REST API and WebSocket support for real-time updates.
"""
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

# Import the main function from app.py
sys.path.insert(0, str(Path(__file__).parent))
from app import generate_guide, parse_question

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Agentic UI Navigator API")

# Add CORS middleware to allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    """Request model for query endpoint."""
    question: str


class QueryResponse(BaseModel):
    """Response model for query endpoint."""
    status: str
    message: str
    task_name: Optional[str] = None
    app_name: Optional[str] = None
    output_dir: Optional[str] = None
    screenshots: Optional[list] = None
    workflow_file: Optional[str] = None


# Store active WebSocket connections
active_connections: list[WebSocket] = []


class ConnectionManager:
    """Manage WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def send_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"Error sending message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections.copy():
            await self.send_message(message, connection)


manager = ConnectionManager()


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Agentic UI Navigator API", "status": "running"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    openai_key_set = bool(os.getenv("OPENAI_API_KEY"))
    return {
        "status": "healthy",
        "openai_key_configured": openai_key_set
    }


@app.post("/api/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """
    Process a user query and generate a guide.
    This is a long-running operation that may take several minutes.
    """
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="OpenAI API key not configured. Please set OPENAI_API_KEY in .env file"
        )
    
    try:
        # Broadcast initial status
        await manager.broadcast({
            "type": "status",
            "message": "Processing your query...",
            "stage": "parsing"
        })
        
        # Parse the question first to get metadata
        parsed = await parse_question(request.question)
        app_name = parsed.get("app_name", "unknown")
        task_name = parsed.get("task_name", "task")
        
        await manager.broadcast({
            "type": "status",
            "message": f"Starting task: {task_name} on {app_name}",
            "stage": "starting",
            "app_name": app_name,
            "task_name": task_name
        })
        
        # Generate the guide (this calls the main functionality)
        result = await generate_guide(request.question)
        
        # Build response
        if result and result.get("success"):
            # Get actual app_name and task from result (more reliable)
            actual_app_name = result.get("app_name", app_name)
            actual_task = result.get("task", task_name)
            
            # Use the dataset path from the result
            dataset_path = result.get("dataset_path")
            if dataset_path:
                # Ensure it's a Path object and relative to cwd
                task_dir = Path(dataset_path)
                if not task_dir.is_absolute():
                    task_dir = Path.cwd() / task_dir
            else:
                # Fallback: construct path
                dataset_dir = Path("dataset")
                app_dir = dataset_dir / actual_app_name.lower()
                task_dir = Path.cwd() / app_dir / actual_task.lower().replace(" ", "_")
            
            screenshots = []
            if task_dir.exists():
                screenshot_dir = task_dir / "screenshots"
                if screenshot_dir.exists():
                    screenshots = sorted([
                        str(f.relative_to(Path.cwd()))
                        for f in screenshot_dir.glob("*.png")
                    ])
            
            workflow_file = None
            workflow_path = task_dir / "workflow.md"
            if workflow_path.exists():
                workflow_file = str(workflow_path.relative_to(Path.cwd()))
            
            await manager.broadcast({
                "type": "complete",
                "message": "Guide generated successfully!",
                "task_name": actual_task,
                "app_name": actual_app_name,
                "output_dir": str(task_dir.relative_to(Path.cwd())),
                "screenshots": screenshots,
                "workflow_file": workflow_file
            })
            
            return QueryResponse(
                status="success",
                message="Guide generated successfully",
                task_name=actual_task,
                app_name=actual_app_name,
                output_dir=str(task_dir.relative_to(Path.cwd())),
                screenshots=screenshots,
                workflow_file=workflow_file
            )
        else:
            error_detail = "Failed to generate guide"
            if result and result.get("error"):
                error_detail = result.get("error")
            
            await manager.broadcast({
                "type": "error",
                "message": error_detail
            })
            
            raise HTTPException(status_code=500, detail=error_detail)
            
    except Exception as e:
        error_msg = str(e)
        await manager.broadcast({
            "type": "error",
            "message": f"Error: {error_msg}"
        })
        
        raise HTTPException(status_code=500, detail=error_msg)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates during guide generation.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and receive any client messages
            data = await websocket.receive_text()
            # Echo back for testing
            await websocket.send_json({"type": "echo", "message": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@app.get("/api/files/{file_path:path}")
async def get_file(file_path: str):
    """
    Serve generated files (screenshots, workflow markdown, etc.)
    """
    # Always treat as relative to current working directory
    full_path = Path.cwd() / file_path
    
    if not full_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    
    if not full_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")
    
    # Security check: ensure file is within the project directory
    try:
        full_path.resolve().relative_to(Path.cwd().resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail=f"Access denied to path outside project directory")
    
    return FileResponse(full_path)


@app.get("/api/workflow/{app_name}/{task_name}")
async def get_workflow(app_name: str, task_name: str):
    """
    Get the workflow markdown content for a specific task.
    """
    workflow_path = Path("dataset") / app_name.lower() / task_name.lower().replace(" ", "_") / "workflow.md"
    
    if not workflow_path.exists():
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    try:
        with open(workflow_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {"content": content, "path": str(workflow_path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download/workflow/{app_name}/{task_name}")
async def download_workflow(app_name: str, task_name: str):
    """
    Download the workflow markdown file.
    """
    workflow_path = Path("dataset") / app_name.lower() / task_name.lower().replace(" ", "_") / "workflow.md"
    
    if not workflow_path.exists():
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Create a safe filename
    safe_filename = f"{app_name}_{task_name}_guide.md".replace(" ", "_").lower()
    
    return FileResponse(
        workflow_path,
        media_type="text/markdown",
        filename=safe_filename
    )


if __name__ == "__main__":
    print("🚀 Starting Agentic UI Navigator Server...")
    print("📡 API: http://localhost:8000")
    print("📝 Docs: http://localhost:8000/docs")
    print("🔌 WebSocket: ws://localhost:8000/ws")
    print("\n⚠️  Make sure your .env file has OPENAI_API_KEY set!")
    
    # Configure logging to reduce noise
    import logging
    logging.getLogger("watchfiles.main").setLevel(logging.WARNING)
    
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

