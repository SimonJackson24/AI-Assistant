import pytest
import asyncio
import json
import websockets
from unittest.mock import Mock, patch

from src.collaboration.websocket_server import CollaborationServer
from src.collaboration.sync_manager import SyncOperation

@pytest.fixture
async def server():
    server = CollaborationServer('localhost', 8765)
    await server.sync_manager.start()
    return server

@pytest.fixture
async def websocket():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        yield websocket

class TestCollaborationServer:
    @pytest.mark.asyncio
    async def test_connection_handling(self, server):
        # Mock websocket
        mock_ws = Mock()
        mock_ws.recv.return_value = json.dumps({
            'user_id': 'test_user'
        })
        
        # Test connection handling
        await server._handle_connection(mock_ws, '/')
        assert 'test_user' in server.connections
        assert mock_ws in server.connections['test_user']
        
    @pytest.mark.asyncio
    async def test_message_handling(self, server):
        # Test operation message
        operation_msg = {
            'type': 'operation',
            'operation_type': 'modify',
            'path': 'test/file.py',
            'content': 'new content'
        }
        
        await server._handle_message('test_user', json.dumps(operation_msg))
        
        # Verify operation was pushed to sync manager
        assert server.sync_manager.operation_queue.qsize() > 0
        
    @pytest.mark.asyncio
    async def test_subscription_handling(self, server):
        # Test subscription message
        sub_msg = {
            'type': 'subscribe',
            'path': 'test/file.py'
        }
        
        await server._handle_message('test_user', json.dumps(sub_msg))
        
        # Verify subscription was created
        assert 'test/file.py' in server.sync_manager.subscribers
        
    @pytest.mark.asyncio
    async def test_lock_handling(self, server):
        # Test lock acquisition
        lock_msg = {
            'type': 'lock',
            'action': 'acquire',
            'path': 'test/file.py'
        }
        
        await server._handle_message('test_user', json.dumps(lock_msg))
        
        # Verify lock was acquired
        assert server.sync_manager.state.locked_files['test/file.py'] == 'test_user'
        
    @pytest.mark.asyncio
    async def test_update_forwarding(self, server):
        # Create test queue and operation
        queue = asyncio.Queue()
        operation = SyncOperation(
            operation_type='modify',
            path='test/file.py',
            content='content',
            position=0,
            user_id='test_user',
            timestamp=0,
            version=1
        )
        
        # Add operation to queue
        await queue.put(operation)
        
        # Mock send_to_user
        mock_send = Mock()
        server._send_to_user = mock_send
        
        # Test forwarding
        await server._forward_updates('test_user', queue)
        
        # Verify message was forwarded
        mock_send.assert_called_once() 