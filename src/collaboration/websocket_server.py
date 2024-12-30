import asyncio
import json
import logging
from typing import Dict, Set, Optional
import websockets
from dataclasses import asdict
from datetime import datetime

from .sync_manager import SyncManager, SyncOperation

logger = logging.getLogger(__name__)

class CollaborationServer:
    def __init__(self, host: str = 'localhost', port: int = 8765):
        self.host = host
        self.port = port
        self.sync_manager = SyncManager()
        self.connections: Dict[str, Set[websockets.WebSocketServerProtocol]] = {}
        
    async def start(self):
        """Start the collaboration server"""
        await self.sync_manager.start()
        server = await websockets.serve(
            self._handle_connection,
            self.host,
            self.port
        )
        logger.info(f"Collaboration server started on ws://{self.host}:{self.port}")
        await server.wait_closed()
        
    async def _handle_connection(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """Handle new WebSocket connections"""
        try:
            # Authenticate user
            auth_message = await websocket.recv()
            auth_data = json.loads(auth_message)
            user_id = auth_data['user_id']
            
            # Register connection
            if user_id not in self.connections:
                self.connections[user_id] = set()
            self.connections[user_id].add(websocket)
            
            # Connect to sync manager
            await self.sync_manager.connect_user(user_id)
            
            try:
                async for message in websocket:
                    await self._handle_message(user_id, message)
            finally:
                # Cleanup on disconnect
                self.connections[user_id].remove(websocket)
                if not self.connections[user_id]:
                    del self.connections[user_id]
                await self.sync_manager.disconnect_user(user_id)
                
        except Exception as e:
            logger.error(f"WebSocket error: {str(e)}")
            
    async def _handle_message(self, user_id: str, message: str):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            message_type = data['type']
            
            if message_type == 'operation':
                # Handle sync operation
                operation = SyncOperation(
                    operation_type=data['operation_type'],
                    path=data['path'],
                    content=data.get('content'),
                    position=data.get('position'),
                    user_id=user_id,
                    timestamp=datetime.now().timestamp(),
                    version=-1  # Will be set by sync manager
                )
                await self.sync_manager.push_operation(operation)
                
            elif message_type == 'subscribe':
                # Handle file subscription
                path = data['path']
                queue = await self.sync_manager.subscribe(user_id, path)
                asyncio.create_task(
                    self._forward_updates(user_id, queue)
                )
                
            elif message_type == 'lock':
                # Handle lock request
                path = data['path']
                action = data['action']  # 'acquire' or 'release'
                
                if action == 'acquire':
                    success = await self.sync_manager.acquire_lock(path, user_id)
                else:
                    success = await self.sync_manager.release_lock(path, user_id)
                    
                await self._send_to_user(user_id, {
                    'type': 'lock_response',
                    'path': path,
                    'action': action,
                    'success': success
                })
                
        except Exception as e:
            logger.error(f"Message handling error: {str(e)}")
            
    async def _forward_updates(self, user_id: str, queue: asyncio.Queue):
        """Forward updates from sync manager to WebSocket"""
        try:
            while True:
                update = await queue.get()
                if isinstance(update, SyncOperation):
                    message = {
                        'type': 'operation',
                        **asdict(update)
                    }
                else:
                    message = update
                    
                await self._send_to_user(user_id, message)
                
        except Exception as e:
            logger.error(f"Update forwarding error: {str(e)}")
            
    async def _send_to_user(self, user_id: str, message: Dict):
        """Send message to all connections of a user"""
        if user_id in self.connections:
            message_str = json.dumps(message)
            for websocket in self.connections[user_id]:
                try:
                    await websocket.send(message_str)
                except websockets.exceptions.ConnectionClosed:
                    continue 