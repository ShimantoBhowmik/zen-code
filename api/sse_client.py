"""
Server-Sent Events (SSE) Client for real-time CLI updates
Handles streaming updates and communication with the FastAPI backend
"""

import asyncio
import json
from typing import Dict, Any, Callable, Optional
import httpx
from rich.console import Console

console = Console()

class SSEClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = None
        self.is_connected = False
        
    async def connect(self, session_id: str, on_message: Callable[[Dict[str, Any]], None]):
        """
        Connect to the SSE endpoint and listen for messages
        """
        try:
            self.client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
            
            url = f"{self.base_url}/events/{session_id}"
            
            async with self.client.stream('GET', url) as response:
                if response.status_code != 200:
                    raise Exception(f"Failed to connect to SSE: {response.status_code}")
                
                self.is_connected = True
                console.print(f"🔗 Connected to real-time updates (Session: {session_id})")
                
                # Process incoming messages
                async for line in response.aiter_lines():
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])  # Remove 'data: ' prefix
                            await self._handle_message(data, on_message)
                        except json.JSONDecodeError:
                            # Handle plain text messages
                            await self._handle_message({'type': 'message', 'data': line[6:]}, on_message)
                    elif line.startswith('event: '):
                        # Handle event type (for future use)
                        pass
                        
        except Exception as e:
            console.print(f"❌ SSE connection error: {str(e)}")
            raise e
        finally:
            self.is_connected = False
            if self.client:
                await self.client.aclose()
    
    async def _handle_message(self, message: Dict[str, Any], callback: Callable[[Dict[str, Any]], None]):
        """Handle incoming SSE message"""
        try:
            if callback:
                callback(message)
            else:
                # Default message handler
                self._default_message_handler(message)
                
        except Exception as e:
            console.print(f"❌ Error handling message: {str(e)}")
    
    def _default_message_handler(self, message: Dict[str, Any]):
        """Default message handler for SSE messages"""
        msg_type = message.get('type', 'unknown')
        data = message.get('data', {})
        
        if msg_type == 'status':
            status = data.get('status', 'unknown')
            description = data.get('description', '')
            
            if status == 'success':
                console.print(f"✅ {description}")
            elif status == 'error':
                console.print(f"❌ {description}")
            elif status == 'info':
                console.print(f"ℹ️  {description}")
            elif status == 'warning':
                console.print(f"⚠️  {description}")
            else:
                console.print(f"🔄 {description}")
                
        elif msg_type == 'progress':
            step = data.get('step', '')
            current = data.get('current', 0)
            total = data.get('total', 0)
            
            if total > 0:
                percentage = (current / total) * 100
                console.print(f"📊 {step}: {current}/{total} ({percentage:.1f}%)")
            else:
                console.print(f"🔄 {step}")
                
        elif msg_type == 'code_change':
            file_path = data.get('file_path', 'unknown')
            action = data.get('action', 'modified')
            console.print(f"📝 {action.title()}: {file_path}")
            
        elif msg_type == 'git_operation':
            operation = data.get('operation', 'unknown')
            result = data.get('result', '')
            console.print(f"🌿 Git {operation}: {result}")
            
        elif msg_type == 'ai_response':
            model = data.get('model', 'unknown')
            tokens = data.get('tokens', 0)
            console.print(f"🤖 AI Response from {model} ({tokens} tokens)")
            
        elif msg_type == 'error':
            error_msg = data.get('message', 'Unknown error')
            details = data.get('details', '')
            console.print(f"❌ Error: {error_msg}")
            if details:
                console.print(f"   Details: {details}")
                
        else:
            # Fallback for unknown message types
            console.print(f"📨 {message}")
    
    async def send_command(self, session_id: str, command: str, params: Dict[str, Any] = None):
        """
        Send a command to the SSE server
        """
        try:
            if not self.client:
                self.client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))
            
            url = f"{self.base_url}/command/{session_id}"
            payload = {
                "command": command,
                "params": params or {}
            }
            
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            console.print(f"❌ Failed to send command: {str(e)}")
            raise e
    
    async def create_session(self) -> str:
        """
        Create a new SSE session
        """
        try:
            if not self.client:
                self.client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))
            
            url = f"{self.base_url}/sessions"
            response = await self.client.post(url)
            response.raise_for_status()
            
            session_data = response.json()
            session_id = session_data.get('session_id')
            
            if not session_id:
                raise Exception("No session ID returned from server")
            
            return session_id
            
        except Exception as e:
            console.print(f"❌ Failed to create session: {str(e)}")
            raise e
    
    async def close_session(self, session_id: str):
        """
        Close an SSE session
        """
        try:
            if not self.client:
                return
            
            url = f"{self.base_url}/sessions/{session_id}"
            await self.client.delete(url)
            
        except Exception as e:
            console.print(f"⚠️  Warning: Failed to close session: {str(e)}")
    
    async def disconnect(self):
        """
        Disconnect from the SSE server
        """
        self.is_connected = False
        if self.client:
            try:
                await self.client.aclose()
            except:
                pass
            self.client = None

# Utility functions for CLI integration

async def run_with_sse_updates(session_id: str, process_func: Callable, *args, **kwargs):
    """
    Run a process function with SSE updates
    """
    sse_client = SSEClient()
    
    try:
        # Start SSE connection in background
        sse_task = asyncio.create_task(
            sse_client.connect(session_id, None)  # Use default handler
        )
        
        # Give SSE a moment to connect
        await asyncio.sleep(0.5)
        
        # Run the main process
        result = await process_func(*args, **kwargs)
        
        # Cancel SSE task
        sse_task.cancel()
        
        return result
        
    except Exception as e:
        raise e
    finally:
        await sse_client.disconnect()

def create_message_handler(progress_callback: Optional[Callable] = None):
    """
    Create a custom message handler for SSE messages
    """
    def handler(message: Dict[str, Any]):
        msg_type = message.get('type', 'unknown')
        
        # Call progress callback if provided
        if progress_callback:
            progress_callback(message)
        
        # Handle specific message types
        if msg_type == 'status':
            data = message.get('data', {})
            status = data.get('status', 'info')
            description = data.get('description', '')
            
            if status == 'success':
                console.print(f"✅ {description}")
            elif status == 'error':
                console.print(f"❌ {description}")
            elif status == 'warning':
                console.print(f"⚠️  {description}")
            else:
                console.print(f"ℹ️  {description}")
                
        elif msg_type == 'step_complete':
            data = message.get('data', {})
            step_name = data.get('step', 'Unknown step')
            console.print(f"✅ {step_name} completed")
            
        elif msg_type == 'step_start':
            data = message.get('data', {})
            step_name = data.get('step', 'Unknown step')
            console.print(f"🔄 Starting {step_name}...")
    
    return handler
