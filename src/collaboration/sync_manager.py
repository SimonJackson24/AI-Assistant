from typing import Dict, List, Any, Optional, Set
import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .conflict_resolver import ConflictResolver, Conflict
from .conflict_messages import ConflictMessageGenerator
from .version_control import VersionControlManager
from ..database.schema_manager import DatabaseManager
from ..core.base_models import BaseModel
from ..monitoring.metrics import MetricsTracker

@dataclass
class SyncOperation:
    operation_type: str  # 'insert', 'delete', 'modify'
    path: str
    content: Optional[str]
    position: Optional[int]
    user_id: str
    timestamp: float
    version: int

@dataclass
class SyncState:
    version: int
    operations: List[SyncOperation]
    users: Set[str]
    locked_files: Dict[str, str]  # path -> user_id
    recent_operations: Dict[str, List[SyncOperation]]  # path -> recent ops

class SyncManager:
    def __init__(self, repo_path: str, db_url: str):
        self.state = SyncState(
            version=0,
            operations=[],
            users=set(),
            locked_files={},
            recent_operations={}
        )
        self.metrics = MetricsTracker()
        self.operation_queue = asyncio.Queue()
        self.subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self.conflict_resolver = ConflictResolver()
        self.message_generator = ConflictMessageGenerator()
        self.vc_manager = VersionControlManager(repo_path)
        self.db_manager = DatabaseManager(db_url)
        self.recent_ops_limit = 10
        self.pending_operations: Dict[str, List[SyncOperation]] = {}  # user_id -> operations
        
    async def start(self):
        """Start the sync manager"""
        self.running = True
        await self.db_manager.init_db()
        asyncio.create_task(self._process_operations())
        
    async def stop(self):
        """Stop the sync manager"""
        self.running = False
        
    async def connect_user(self, user_id: str):
        """Register a new user connection"""
        self.state.users.add(user_id)
        self.subscribers[user_id] = set()
        self.pending_operations[user_id] = []
        # Create user branch
        await self.vc_manager.create_branch_for_user(user_id)
        await self.db_manager.update_user_activity(user_id)
        await self._broadcast_user_event('connected', user_id)
        
    async def disconnect_user(self, user_id: str):
        """Handle user disconnection"""
        # Commit any pending changes
        if user_id in self.pending_operations and self.pending_operations[user_id]:
            await self._commit_user_changes(user_id)
        self.state.users.remove(user_id)
        self._release_user_locks(user_id)
        del self.pending_operations[user_id]
        await self._broadcast_user_event('disconnected', user_id)
        
    async def subscribe(self, user_id: str, path: str) -> asyncio.Queue:
        """Subscribe to updates for a specific file"""
        queue = asyncio.Queue()
        if path not in self.subscribers:
            self.subscribers[path] = set()
        self.subscribers[path].add(queue)
        return queue
        
    async def unsubscribe(self, path: str, queue: asyncio.Queue):
        """Unsubscribe from file updates"""
        if path in self.subscribers:
            self.subscribers[path].remove(queue)
            
    async def push_operation(self, operation: SyncOperation):
        """Push a new sync operation"""
        try:
            # Validate operation
            if not self._validate_operation(operation):
                raise ValueError("Invalid operation")
                
            # Check file lock
            if not self._can_modify_file(operation.path, operation.user_id):
                raise PermissionError("File is locked by another user")
                
            # Check for conflicts
            recent_ops = self.state.recent_operations.get(operation.path, [])
            conflict = await self.conflict_resolver.check_conflict(operation, recent_ops)
            
            if conflict:
                # Try to resolve conflict
                resolution = await self.conflict_resolver.resolve_conflict(conflict)
                if resolution:
                    operation = resolution
                else:
                    # Cannot auto-resolve, notify users
                    await self._broadcast_conflict(conflict)
                    return
                
            # Add to queue
            await self.operation_queue.put(operation)
            # Add to pending operations
            self.pending_operations[operation.user_id].append(operation)
            
            # Record in database
            await self.db_manager.record_operation(
                operation_type=operation.operation_type,
                path=operation.path,
                user_id=operation.user_id,
                content=operation.content,
                position=operation.position,
                version=operation.version
            )
            
            # Update metrics
            self.metrics.record('sync_operation_pushed', {
                'type': operation.operation_type,
                'user': operation.user_id,
                'path': operation.path
            })
            
        except Exception as e:
            self.metrics.record_error('sync_operation_error', str(e))
            raise
            
    async def acquire_lock(self, path: str, user_id: str) -> bool:
        """Attempt to acquire a lock on a file"""
        if path in self.state.locked_files:
            return False
            
        self.state.locked_files[path] = user_id
        await self._broadcast_lock_event('acquired', path, user_id)
        return True
        
    async def release_lock(self, path: str, user_id: str) -> bool:
        """Release a lock on a file"""
        if self.state.locked_files.get(path) != user_id:
            return False
            
        del self.state.locked_files[path]
        await self._broadcast_lock_event('released', path, user_id)
        return True
        
    async def _process_operations(self):
        """Process queued operations"""
        while self.running:
            try:
                operation = await self.operation_queue.get()
                
                # Apply operation
                self._apply_operation(operation)
                
                # Update recent operations
                self._update_recent_operations(operation)
                
                # Broadcast to subscribers
                await self._broadcast_operation(operation)
                
                # Update version
                self.state.version += 1
                operation.version = self.state.version
                
                # Record metrics
                self.metrics.record('sync_operation_processed', {
                    'type': operation.operation_type,
                    'version': operation.version
                })
                
            except Exception as e:
                self.metrics.record_error('sync_processing_error', str(e))
                
    def _apply_operation(self, operation: SyncOperation):
        """Apply an operation to the sync state"""
        if operation.operation_type == 'insert':
            # Handle insert
            pass
        elif operation.operation_type == 'delete':
            # Handle delete
            pass
        elif operation.operation_type == 'modify':
            # Handle modify
            pass
            
    async def _broadcast_operation(self, operation: SyncOperation):
        """Broadcast operation to subscribers"""
        if operation.path in self.subscribers:
            for queue in self.subscribers[operation.path]:
                await queue.put(operation)
                
    def _validate_operation(self, operation: SyncOperation) -> bool:
        """Validate a sync operation"""
        # Check operation type
        if operation.operation_type not in {'insert', 'delete', 'modify'}:
            return False
            
        # Check path exists
        if not Path(operation.path).exists():
            return False
            
        # Check user is connected
        if operation.user_id not in self.state.users:
            return False
            
        return True
        
    def _can_modify_file(self, path: str, user_id: str) -> bool:
        """Check if user can modify a file"""
        if path not in self.state.locked_files:
            return True
        return self.state.locked_files[path] == user_id
        
    def _release_user_locks(self, user_id: str):
        """Release all locks held by a user"""
        paths_to_release = [
            path for path, lock_holder in self.state.locked_files.items()
            if lock_holder == user_id
        ]
        for path in paths_to_release:
            del self.state.locked_files[path]
            
    async def _broadcast_user_event(self, event_type: str, user_id: str):
        """Broadcast user connection/disconnection events"""
        event = {
            'type': f'user_{event_type}',
            'user_id': user_id,
            'timestamp': datetime.now().timestamp()
        }
        # Broadcast to all connected users
        for user in self.state.users:
            if user in self.subscribers:
                for queue in self.subscribers[user]:
                    await queue.put(event)
                    
    async def _broadcast_lock_event(self, event_type: str, path: str, user_id: str):
        """Broadcast lock acquisition/release events"""
        event = {
            'type': f'lock_{event_type}',
            'path': path,
            'user_id': user_id,
            'timestamp': datetime.now().timestamp()
        }
        # Broadcast to subscribers of the file
        if path in self.subscribers:
            for queue in self.subscribers[path]:
                await queue.put(event) 
                
    def _update_recent_operations(self, operation: SyncOperation):
        """Update recent operations for a file"""
        if operation.path not in self.state.recent_operations:
            self.state.recent_operations[operation.path] = []
            
        recent = self.state.recent_operations[operation.path]
        recent.append(operation)
        
        # Keep only recent operations
        if len(recent) > self.recent_ops_limit:
            recent.pop(0)
            
    async def _broadcast_conflict(self, conflict: Conflict):
        """Broadcast conflict to affected users"""
        message = self.message_generator.generate_message(conflict)
        
        # Record conflict in database
        db_conflict = await self.db_manager.record_conflict(
            path=conflict.operations[0].path,
            operations=[op.version for op in conflict.operations]
        )
        
        event = {
            'type': 'conflict',
            'path': conflict.operations[0].path,
            'users': conflict.users,
            'timestamp': conflict.timestamp,
            'message': {
                'title': message.title,
                'description': message.description,
                'severity': message.severity,
                'actions': message.actions
            },
            'conflict_id': db_conflict.id,
            'metadata': message.metadata
        }
        
        for user_id in conflict.users:
            if user_id in self.subscribers:
                for queue in self.subscribers[user_id]:
                    await queue.put(event) 
                    
    async def _commit_user_changes(self, user_id: str):
        """Commit pending changes for a user"""
        operations = self.pending_operations[user_id]
        if not operations:
            return
            
        try:
            # Stage changes
            if await self.vc_manager.stage_changes(operations):
                # Create commit message
                message = self._create_commit_message(operations)
                # Commit changes
                commit_hash = await self.vc_manager.commit_changes(
                    message=message,
                    author=user_id,
                    branch=f"user/{user_id}"
                )
                
                if commit_hash:
                    # Clear pending operations
                    self.pending_operations[user_id] = []
                    
                    # Broadcast commit event
                    await self._broadcast_commit_event(user_id, commit_hash, operations)
                    
        except Exception as e:
            self.metrics.record_error('commit_error', str(e))
            
    def _create_commit_message(self, operations: List[SyncOperation]) -> str:
        """Create a commit message from operations"""
        if len(operations) == 1:
            op = operations[0]
            return f"{op.operation_type.capitalize()}: {Path(op.path).name}"
            
        counts = {}
        for op in operations:
            counts[op.operation_type] = counts.get(op.operation_type, 0) + 1
            
        message_parts = [
            f"{op_type}: {count} files"
            for op_type, count in counts.items()
        ]
        return " | ".join(message_parts)
        
    async def _broadcast_commit_event(self, user_id: str, 
                                    commit_hash: str,
                                    operations: List[SyncOperation]):
        """Broadcast commit event to subscribers"""
        event = {
            'type': 'commit',
            'user_id': user_id,
            'commit_hash': commit_hash,
            'timestamp': datetime.now().timestamp(),
            'files': [op.path for op in operations]
        }
        
        # Broadcast to all users
        for user in self.state.users:
            if user in self.subscribers:
                for queue in self.subscribers[user]:
                    await queue.put(event) 