import pytest
import asyncio
from pathlib import Path
import websockets
import json
from src.preview.websocket_server import PreviewWebSocketServer
from src.preview.file_watcher import FileWatcher
from src.preview.renderer import PreviewRenderer

@pytest.fixture
async def websocket_server():
    server = PreviewWebSocketServer(host="localhost", port=8765)
    asyncio.create_task(server.start())
    await asyncio.sleep(0.1)  # Wait for server to start
    yield server
    # Cleanup
    for client in server.clients:
        await client.close()

@pytest.fixture
def file_watcher():
    watcher = FileWatcher()
    yield watcher
    watcher.stop()

@pytest.fixture
def preview_renderer():
    return PreviewRenderer()

@pytest.mark.asyncio
async def test_websocket_connection(websocket_server):
    async with websockets.connect('ws://localhost:8765') as websocket:
        assert websocket_server.clients

@pytest.mark.asyncio
async def test_file_update(websocket_server):
    async with websockets.connect('ws://localhost:8765') as websocket:
        test_data = {
            'type': 'update',
            'file': 'test.py',
            'content': 'print("Hello, World!")'
        }
        await websocket.send(json.dumps(test_data))
        
        response = await websocket.recv()
        data = json.loads(response)
        assert data['type'] == 'update'
        assert 'test.py' in websocket_server.state

@pytest.mark.asyncio
async def test_file_watcher(file_watcher, tmp_path):
    test_file = tmp_path / "test.py"
    test_content = 'print("Test")'
    
    # Create test file
    test_file.write_text(test_content)
    
    # Setup handler
    async def handler(path: str, content: str):
        assert content == test_content
    
    file_watcher.add_path(str(tmp_path))
    file_watcher.add_handler('.py', handler)
    
    # Start watching
    watch_task = asyncio.create_task(file_watcher.start())
    await asyncio.sleep(0.1)
    
    # Modify file
    test_file.write_text(test_content + "\n")
    await asyncio.sleep(0.1)
    
    file_watcher.stop()
    await watch_task

@pytest.mark.asyncio
async def test_preview_renderer(preview_renderer):
    test_content = 'print("Test")'
    result = await preview_renderer.render_preview('test.py', test_content)
    
    assert result['status'] == 'success'
    assert 'preview' in result
    assert 'metadata' in result 