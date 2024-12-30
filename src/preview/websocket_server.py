import asyncio
import json
from typing import Dict, Set, Any
import websockets
from websockets.server import WebSocketServerProtocol
from dataclasses import dataclass, asdict
from ..monitoring.metrics import MetricsTracker

@dataclass
class PreviewState:
    file_path: str
    content: str
    cursor_position: Dict[str, int]
    scroll_position: int
    active_users: int

class PreviewWebSocketServer:
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.state: Dict[str, PreviewState] = {}
        self.metrics = MetricsTracker()
        
    async def start(self):
        """Start the WebSocket server"""
        async with websockets.serve(self._handle_client, self.host, self.port):
            await asyncio.Future()  # run forever
            
    async def _handle_client(self, websocket: WebSocketServerProtocol):
        """Handle individual client connections"""
        try:
            await self._register(websocket)
            async for message in websocket:
                await self._process_message(websocket, message)
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            await self._unregister(websocket)
            
    async def _register(self, websocket: WebSocketServerProtocol):
        """Register new client"""
        self.clients.add(websocket)
        # Send current state to new client
        await websocket.send(json.dumps({
            "type": "init",
            "data": {path: asdict(state) for path, state in self.state.items()}
        }))
        
    async def _unregister(self, websocket: WebSocketServerProtocol):
        """Unregister client"""
        self.clients.remove(websocket)
        
    async def _process_message(self, websocket: WebSocketServerProtocol, message: str):
        """Process incoming messages"""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            handlers = {
                "update": self._handle_update,
                "cursor": self._handle_cursor,
                "scroll": self._handle_scroll
            }
            
            handler = handlers.get(message_type)
            if handler:
                await handler(websocket, data)
            else:
                print(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            print(f"Invalid JSON received: {message}")
            
    async def _handle_update(self, websocket: WebSocketServerProtocol, data: Dict[str, Any]):
        """Handle file update messages"""
        file_path = data.get("file")
        content = data.get("content")
        
        if file_path and content:
            self.state[file_path] = PreviewState(
                file_path=file_path,
                content=content,
                cursor_position={"line": 0, "column": 0},
                scroll_position=0,
                active_users=len(self.clients)
            )
            
            # Broadcast update to all clients except sender
            await self._broadcast({
                "type": "update",
                "data": asdict(self.state[file_path])
            }, exclude={websocket})
            
    async def _broadcast(self, message: Dict[str, Any], exclude: Set[WebSocketServerProtocol] = None):
        """Broadcast message to all clients except those in exclude set"""
        if exclude is None:
            exclude = set()
            
        message_str = json.dumps(message)
        await asyncio.gather(
            *(client.send(message_str) 
              for client in self.clients 
              if client not in exclude)
        ) 