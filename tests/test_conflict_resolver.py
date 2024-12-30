import pytest
from datetime import datetime
from typing import List

from src.collaboration.conflict_resolver import ConflictResolver, Conflict
from src.collaboration.sync_manager import SyncOperation

@pytest.fixture
def resolver():
    return ConflictResolver()

@pytest.fixture
def base_operation():
    return SyncOperation(
        operation_type='modify',
        path='test/file.py',
        content='original content',
        position=0,
        user_id='user1',
        timestamp=datetime.now().timestamp(),
        version=1
    )

class TestConflictResolver:
    @pytest.mark.asyncio
    async def test_modify_conflict_detection(self, resolver, base_operation):
        # Create conflicting operation
        conflicting_op = SyncOperation(
            operation_type='modify',
            path='test/file.py',
            content='modified content',
            position=0,
            user_id='user2',
            timestamp=datetime.now().timestamp(),
            version=1
        )
        
        # Check for conflict
        conflict = await resolver.check_conflict(conflicting_op, [base_operation])
        
        assert conflict is not None
        assert len(conflict.operations) == 2
        assert conflict.users == ['user2', 'user1']
        assert not conflict.resolved
        
    @pytest.mark.asyncio
    async def test_delete_conflict_detection(self, resolver, base_operation):
        delete_op = SyncOperation(
            operation_type='delete',
            path='test/file.py',
            content=None,
            position=None,
            user_id='user2',
            timestamp=datetime.now().timestamp(),
            version=1
        )
        
        conflict = await resolver.check_conflict(delete_op, [base_operation])
        
        assert conflict is not None
        assert len(conflict.operations) == 2
        assert 'delete' in [op.operation_type for op in conflict.operations]
        
    @pytest.mark.asyncio
    async def test_insert_conflict_detection(self, resolver):
        insert1 = SyncOperation(
            operation_type='insert',
            path='test/file.py',
            content='new content 1',
            position=10,
            user_id='user1',
            timestamp=datetime.now().timestamp(),
            version=1
        )
        
        insert2 = SyncOperation(
            operation_type='insert',
            path='test/file.py',
            content='new content 2',
            position=11,
            user_id='user2',
            timestamp=datetime.now().timestamp(),
            version=1
        )
        
        conflict = await resolver.check_conflict(insert2, [insert1])
        
        assert conflict is not None
        assert len(conflict.operations) == 2
        
    @pytest.mark.asyncio
    async def test_modify_conflict_resolution(self, resolver):
        op1 = SyncOperation(
            operation_type='modify',
            path='test/file.py',
            content='first modification',
            position=0,
            user_id='user1',
            timestamp=datetime.now().timestamp(),
            version=1
        )
        
        op2 = SyncOperation(
            operation_type='modify',
            path='test/file.py',
            content='second modification',
            position=0,
            user_id='user2',
            timestamp=datetime.now().timestamp() + 1,
            version=2
        )
        
        conflict = Conflict(
            operations=[op2, op1],
            users=['user1', 'user2'],
            timestamp=datetime.now().timestamp()
        )
        
        resolution = await resolver.resolve_conflict(conflict)
        
        assert resolution is not None
        assert resolution.operation_type == 'modify'
        assert resolution.user_id == 'system'
        assert resolution.content is not None
        
    @pytest.mark.asyncio
    async def test_delete_conflict_resolution(self, resolver):
        modify_op = SyncOperation(
            operation_type='modify',
            path='test/file.py',
            content='modified content',
            position=0,
            user_id='user1',
            timestamp=datetime.now().timestamp(),
            version=1
        )
        
        delete_op = SyncOperation(
            operation_type='delete',
            path='test/file.py',
            content=None,
            position=None,
            user_id='user2',
            timestamp=datetime.now().timestamp(),
            version=2
        )
        
        conflict = Conflict(
            operations=[delete_op, modify_op],
            users=['user1', 'user2'],
            timestamp=datetime.now().timestamp()
        )
        
        resolution = await resolver.resolve_conflict(conflict)
        
        assert resolution is not None
        assert resolution.operation_type == 'delete'
        
    @pytest.mark.asyncio
    async def test_insert_conflict_resolution(self, resolver):
        insert1 = SyncOperation(
            operation_type='insert',
            path='test/file.py',
            content='first insert',
            position=10,
            user_id='user1',
            timestamp=datetime.now().timestamp(),
            version=1
        )
        
        insert2 = SyncOperation(
            operation_type='insert',
            path='test/file.py',
            content='second insert',
            position=10,
            user_id='user2',
            timestamp=datetime.now().timestamp(),
            version=2
        )
        
        conflict = Conflict(
            operations=[insert2, insert1],
            users=['user1', 'user2'],
            timestamp=datetime.now().timestamp()
        )
        
        resolution = await resolver.resolve_conflict(conflict)
        
        assert resolution is not None
        assert resolution.operation_type == 'insert'
        assert resolution.content == 'first insertsecond insert'
        assert resolution.position == 10 

    @pytest.mark.asyncio
    async def test_overlapping_modifications(self, resolver):
        """Test handling of overlapping text modifications"""
        original = SyncOperation(
            operation_type='modify',
            path='test/file.py',
            content='def hello_world():\n    print("hello")\n',
            position=0,
            user_id='user1',
            timestamp=datetime.now().timestamp(),
            version=1
        )
        
        mod1 = SyncOperation(
            operation_type='modify',
            path='test/file.py',
            content='def hello_world():\n    print("hello world")\n',
            position=0,
            user_id='user2',
            timestamp=datetime.now().timestamp() + 1,
            version=2
        )
        
        mod2 = SyncOperation(
            operation_type='modify',
            path='test/file.py',
            content='async def hello_world():\n    print("hello")\n',
            position=0,
            user_id='user3',
            timestamp=datetime.now().timestamp() + 2,
            version=3
        )
        
        conflict = Conflict(
            operations=[mod2, mod1, original],
            users=['user1', 'user2', 'user3'],
            timestamp=datetime.now().timestamp()
        )
        
        resolution = await resolver.resolve_conflict(conflict)
        
        assert resolution is not None
        assert resolution.operation_type == 'modify'
        assert 'async' in resolution.content
        assert 'world' in resolution.content
        
    @pytest.mark.asyncio
    async def test_concurrent_insertions(self, resolver):
        """Test handling of concurrent insertions at same position"""
        base = SyncOperation(
            operation_type='modify',
            path='test/file.py',
            content='def process_data():\n    data = []\n',
            position=0,
            user_id='user1',
            timestamp=datetime.now().timestamp(),
            version=1
        )
        
        insert1 = SyncOperation(
            operation_type='insert',
            path='test/file.py',
            content='    # Process input data\n',
            position=23,  # After first line
            user_id='user2',
            timestamp=datetime.now().timestamp() + 1,
            version=2
        )
        
        insert2 = SyncOperation(
            operation_type='insert',
            path='test/file.py',
            content='    # Initialize data list\n',
            position=23,  # Same position
            user_id='user3',
            timestamp=datetime.now().timestamp() + 2,
            version=3
        )
        
        conflict = Conflict(
            operations=[insert2, insert1],
            users=['user2', 'user3'],
            timestamp=datetime.now().timestamp()
        )
        
        resolution = await resolver.resolve_conflict(conflict)
        
        assert resolution is not None
        assert resolution.operation_type == 'insert'
        assert 'Process input' in resolution.content
        assert 'Initialize data' in resolution.content
        
    @pytest.mark.asyncio
    async def test_delete_with_modifications(self, resolver):
        """Test handling delete operation with pending modifications"""
        base = SyncOperation(
            operation_type='modify',
            path='test/file.py',
            content='class TestCase:\n    def test_feature(self):\n        pass\n',
            position=0,
            user_id='user1',
            timestamp=datetime.now().timestamp(),
            version=1
        )
        
        modify = SyncOperation(
            operation_type='modify',
            path='test/file.py',
            content='class TestCase:\n    def test_feature(self):\n        self.assertTrue(True)\n',
            position=0,
            user_id='user2',
            timestamp=datetime.now().timestamp() + 1,
            version=2
        )
        
        delete = SyncOperation(
            operation_type='delete',
            path='test/file.py',
            content=None,
            position=None,
            user_id='user3',
            timestamp=datetime.now().timestamp() + 2,
            version=3
        )
        
        conflict = Conflict(
            operations=[delete, modify, base],
            users=['user1', 'user2', 'user3'],
            timestamp=datetime.now().timestamp()
        )
        
        resolution = await resolver.resolve_conflict(conflict)
        
        assert resolution is not None
        assert resolution.operation_type == 'delete'
        
    @pytest.mark.asyncio
    async def test_non_conflicting_operations(self, resolver):
        """Test operations that shouldn't conflict"""
        op1 = SyncOperation(
            operation_type='modify',
            path='test/file.py',
            content='def func1():\n    pass\n',
            position=0,
            user_id='user1',
            timestamp=datetime.now().timestamp(),
            version=1
        )
        
        op2 = SyncOperation(
            operation_type='modify',
            path='test/file.py',
            content='def func2():\n    pass\n',
            position=100,  # Different position
            user_id='user2',
            timestamp=datetime.now().timestamp(),
            version=2
        )
        
        conflict = await resolver.check_conflict(op2, [op1])
        assert conflict is None 