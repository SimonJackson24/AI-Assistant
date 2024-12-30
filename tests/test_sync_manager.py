import pytest
import asyncio
from datetime import datetime
from pathlib import Path

from src.collaboration.sync_manager import SyncManager, SyncOperation, SyncState

@pytest.fixture
def sync_manager():
    return SyncManager()

@pytest.fixture
def test_operation():
    return SyncOperation(
        operation_type='modify',
        path='test/file.py',
        content='new content',
        position=0,
        user_id='test_user',
        timestamp=datetime.now().timestamp(),
        version=-1
    )

class TestSyncManager:
    @pytest.mark.asyncio
    async def test_user_connection(self, sync_manager):
        await sync_manager.connect_user('test_user')
        assert 'test_user' in sync_manager.state.users
        assert 'test_user' in sync_manager.subscribers
        
        await sync_manager.disconnect_user('test_user')
        assert 'test_user' not in sync_manager.state.users
        assert 'test_user' not in sync_manager.subscribers
        
    @pytest.mark.asyncio
    async def test_file_subscription(self, sync_manager):
        await sync_manager.connect_user('test_user')
        queue = await sync_manager.subscribe('test_user', 'test/file.py')
        
        assert isinstance(queue, asyncio.Queue)
        assert 'test/file.py' in sync_manager.subscribers
        
        await sync_manager.unsubscribe('test/file.py', queue)
        assert not sync_manager.subscribers['test/file.py']
        
    @pytest.mark.asyncio
    async def test_file_locking(self, sync_manager):
        await sync_manager.connect_user('user1')
        await sync_manager.connect_user('user2')
        
        # User1 acquires lock
        success = await sync_manager.acquire_lock('test/file.py', 'user1')
        assert success
        assert sync_manager.state.locked_files['test/file.py'] == 'user1'
        
        # User2 tries to acquire same lock
        success = await sync_manager.acquire_lock('test/file.py', 'user2')
        assert not success
        
        # User1 releases lock
        success = await sync_manager.release_lock('test/file.py', 'user1')
        assert success
        assert 'test/file.py' not in sync_manager.state.locked_files
        
    @pytest.mark.asyncio
    async def test_operation_processing(self, sync_manager, test_operation, tmp_path):
        # Create test file
        test_file = tmp_path / "file.py"
        test_file.write_text("original content")
        test_operation.path = str(test_file)
        
        await sync_manager.start()
        await sync_manager.connect_user('test_user')
        
        # Subscribe to updates
        queue = await sync_manager.subscribe('test_user', str(test_file))
        
        # Push operation
        await sync_manager.push_operation(test_operation)
        
        # Wait for operation to be processed
        update = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert isinstance(update, SyncOperation)
        assert update.version > 0
        assert update.operation_type == 'modify'
        
        await sync_manager.stop()
        
    @pytest.mark.asyncio
    async def test_error_handling(self, sync_manager, test_operation):
        # Test invalid operation
        test_operation.operation_type = 'invalid'
        with pytest.raises(ValueError):
            await sync_manager.push_operation(test_operation)
            
        # Test operation on locked file
        test_operation.operation_type = 'modify'
        await sync_manager.acquire_lock(test_operation.path, 'other_user')
        with pytest.raises(PermissionError):
            await sync_manager.push_operation(test_operation) 