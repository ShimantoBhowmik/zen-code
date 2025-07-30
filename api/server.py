"""
FastAPI Server for Server-Sent Events (SSE)
Provides real-time streaming updates for the CLI
"""

import asyncio
import json
import uuid
from typing import Dict, Any, Set
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Backspace CLI SSE Server", version="1.0.0")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state management
active_sessions: Dict[str, Dict[str, Any]] = {}
session_queues: Dict[str, asyncio.Queue] = {}

class SessionCreate(BaseModel):
    """Model for session creation"""
    name: str = "default"
    metadata: Dict[str, Any] = {}

class CommandRequest(BaseModel):
    """Model for command requests"""
    command: str
    params: Dict[str, Any] = {}

class SSEMessage(BaseModel):
    """Model for SSE messages"""
    type: str
    data: Dict[str, Any]
    timestamp: datetime = None
    
    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now()
        super().__init__(**data)

@app.post("/sessions")
async def create_session(session_data: SessionCreate = None):
    """Create a new SSE session"""
    session_id = str(uuid.uuid4())
    
    active_sessions[session_id] = {
        "created_at": datetime.now(),
        "name": session_data.name if session_data else "default",
        "metadata": session_data.metadata if session_data else {},
        "status": "active"
    }
    
    # Create message queue for this session
    session_queues[session_id] = asyncio.Queue()
    
    return {"session_id": session_id, "status": "created"}

@app.delete("/sessions/{session_id}")
async def close_session(session_id: str):
    """Close an SSE session"""
    if session_id in active_sessions:
        active_sessions[session_id]["status"] = "closed"
        
        # Send close message to queue
        if session_id in session_queues:
            await session_queues[session_id].put(
                SSEMessage(type="session_closed", data={"session_id": session_id})
            )
        
        return {"status": "closed"}
    
    return {"error": "Session not found"}, 404

@app.get("/events/{session_id}")
async def stream_events(session_id: str):
    """Stream SSE events for a session"""
    if session_id not in active_sessions:
        return {"error": "Session not found"}, 404
    
    async def event_generator():
        try:
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'data': {'session_id': session_id}})}\n\n"
            
            # Get the queue for this session
            queue = session_queues.get(session_id)
            if not queue:
                yield f"data: {json.dumps({'type': 'error', 'data': {'message': 'Session queue not found'}})}\n\n"
                return
            
            # Stream messages from the queue
            while active_sessions.get(session_id, {}).get("status") == "active":
                try:
                    # Wait for message with timeout
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    
                    # Convert message to SSE format
                    message_data = {
                        "type": message.type,
                        "data": message.data,
                        "timestamp": message.timestamp.isoformat()
                    }
                    
                    yield f"data: {json.dumps(message_data)}\n\n"
                    
                    # Check if this is a close message
                    if message.type == "session_closed":
                        break
                        
                except asyncio.TimeoutError:
                    # Send heartbeat
                    yield f"data: {json.dumps({'type': 'heartbeat', 'data': {'timestamp': datetime.now().isoformat()}})}\n\n"
                    
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': str(e)}})}\n\n"
        finally:
            # Cleanup
            if session_id in session_queues:
                del session_queues[session_id]
            if session_id in active_sessions:
                active_sessions[session_id]["status"] = "closed"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )

@app.post("/events/{session_id}")
async def send_event(session_id: str, message: SSEMessage):
    """Send an event to a specific session"""
    if session_id not in active_sessions:
        return {"error": "Session not found"}, 404
    
    if session_id not in session_queues:
        return {"error": "Session queue not found"}, 404
    
    # Add message to queue
    await session_queues[session_id].put(message)
    
    return {"status": "sent"}

@app.post("/command/{session_id}")
async def handle_command(session_id: str, command_request: CommandRequest, background_tasks: BackgroundTasks):
    """Handle commands and trigger background processes"""
    if session_id not in active_sessions:
        return {"error": "Session not found"}, 404
    
    # Add command processing to background tasks
    background_tasks.add_task(
        process_command,
        session_id,
        command_request.command,
        command_request.params
    )
    
    return {"status": "command_received", "command": command_request.command}

async def process_command(session_id: str, command: str, params: Dict[str, Any]):
    """Process commands in the background"""
    try:
        # Send command start message
        await send_message(session_id, "command_start", {
            "command": command,
            "params": params
        })
        
        if command == "clone_repo":
            await handle_clone_repo(session_id, params)
        elif command == "analyze_code":
            await handle_analyze_code(session_id, params)
        elif command == "generate_changes":
            await handle_generate_changes(session_id, params)
        elif command == "apply_changes":
            await handle_apply_changes(session_id, params)
        elif command == "create_pr":
            await handle_create_pr(session_id, params)
        else:
            await send_message(session_id, "error", {
                "message": f"Unknown command: {command}"
            })
            return
        
        # Send command completion message
        await send_message(session_id, "command_complete", {
            "command": command
        })
        
    except Exception as e:
        await send_message(session_id, "error", {
            "message": f"Command failed: {str(e)}",
            "command": command
        })

async def handle_clone_repo(session_id: str, params: Dict[str, Any]):
    """Handle repository cloning"""
    repo_url = params.get("repo_url")
    if not repo_url:
        await send_message(session_id, "error", {"message": "repo_url required"})
        return
    
    await send_message(session_id, "status", {
        "status": "info",
        "description": f"Cloning repository: {repo_url}"
    })
    
    # Simulate cloning process
    await asyncio.sleep(2)
    
    await send_message(session_id, "status", {
        "status": "success",
        "description": "Repository cloned successfully"
    })

async def handle_analyze_code(session_id: str, params: Dict[str, Any]):
    """Handle code analysis"""
    await send_message(session_id, "status", {
        "status": "info",
        "description": "AI agent analyzing codebase..."
    })
    
    # Simulate analysis
    await asyncio.sleep(3)
    
    await send_message(session_id, "ai_response", {
        "model": params.get("model", "codellama"),
        "tokens": 150,
        "analysis": "Codebase analysis complete"
    })
    
    await send_message(session_id, "status", {
        "status": "success",
        "description": "Codebase analysis complete"
    })

async def handle_generate_changes(session_id: str, params: Dict[str, Any]):
    """Handle code change generation"""
    await send_message(session_id, "status", {
        "status": "info",
        "description": "Generating code changes..."
    })
    
    # Simulate generation
    await asyncio.sleep(4)
    
    await send_message(session_id, "ai_response", {
        "model": params.get("model", "codellama"),
        "tokens": 300,
        "changes_generated": 3
    })
    
    await send_message(session_id, "status", {
        "status": "success",
        "description": "Code changes generated"
    })

async def handle_apply_changes(session_id: str, params: Dict[str, Any]):
    """Handle applying changes"""
    changes = params.get("changes", [])
    
    for i, change in enumerate(changes, 1):
        await send_message(session_id, "progress", {
            "step": "Applying changes",
            "current": i,
            "total": len(changes)
        })
        
        await send_message(session_id, "code_change", {
            "file_path": change.get("file_path", "unknown"),
            "action": change.get("action", "modified")
        })
        
        await asyncio.sleep(0.5)
    
    await send_message(session_id, "status", {
        "status": "success",
        "description": "All changes applied successfully"
    })

async def handle_create_pr(session_id: str, params: Dict[str, Any]):
    """Handle PR creation"""
    await send_message(session_id, "status", {
        "status": "info",
        "description": "Creating branch and committing changes..."
    })
    
    await asyncio.sleep(2)
    
    await send_message(session_id, "git_operation", {
        "operation": "branch_create",
        "result": f"Created branch: {params.get('branch', 'ai-changes')}"
    })
    
    await send_message(session_id, "git_operation", {
        "operation": "commit",
        "result": "Changes committed"
    })
    
    await asyncio.sleep(1)
    
    await send_message(session_id, "status", {
        "status": "info",
        "description": "Creating pull request..."
    })
    
    await asyncio.sleep(2)
    
    pr_url = f"https://github.com/{params.get('owner', 'user')}/{params.get('repo', 'repo')}/pull/123"
    
    await send_message(session_id, "status", {
        "status": "success",
        "description": f"Pull request created: {pr_url}"
    })

async def send_message(session_id: str, message_type: str, data: Dict[str, Any]):
    """Helper function to send messages to a session"""
    if session_id in session_queues:
        message = SSEMessage(type=message_type, data=data)
        await session_queues[session_id].put(message)

@app.get("/sessions")
async def list_sessions():
    """List all active sessions"""
    return {
        "sessions": [
            {
                "session_id": sid,
                "status": session_data["status"],
                "created_at": session_data["created_at"].isoformat(),
                "name": session_data["name"]
            }
            for sid, session_data in active_sessions.items()
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "active_sessions": len(active_sessions),
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
