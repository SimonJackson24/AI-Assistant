from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import difflib
from datetime import datetime

from ..monitoring.metrics import MetricsTracker
from .sync_manager import SyncOperation

@dataclass
class Conflict:
    operations: List[SyncOperation]
    users: List[str]
    timestamp: float
    resolved: bool = False
    resolution: Optional[SyncOperation] = None

class ConflictResolver:
    def __init__(self):
        self.metrics = MetricsTracker()
        self.conflicts: Dict[str, List[Conflict]] = {}
        self.resolution_strategies = {
            'modify': self._resolve_modify_conflict,
            'delete': self._resolve_delete_conflict,
            'insert': self._resolve_insert_conflict
        }
        
    async def check_conflict(self, operation: SyncOperation, 
                           recent_operations: List[SyncOperation]) -> Optional[Conflict]:
        """Check if operation conflicts with recent operations"""
        try:
            conflicts = []
            
            for recent in recent_operations:
                if self._operations_conflict(operation, recent):
                    conflicts.append(recent)
                    
            if conflicts:
                conflict = Conflict(
                    operations=[operation] + conflicts,
                    users=list(set(op.user_id for op in conflicts + [operation])),
                    timestamp=datetime.now().timestamp()
                )
                
                if operation.path not in self.conflicts:
                    self.conflicts[operation.path] = []
                self.conflicts[operation.path].append(conflict)
                
                return conflict
                
            return None
            
        except Exception as e:
            self.metrics.record_error('conflict_check_error', str(e))
            return None
            
    async def resolve_conflict(self, conflict: Conflict) -> Optional[SyncOperation]:
        """Attempt to automatically resolve a conflict"""
        try:
            if len(conflict.operations) < 2:
                return conflict.operations[0]
                
            # Get primary operation (most recent)
            primary = conflict.operations[0]
            
            # Get resolution strategy
            strategy = self.resolution_strategies.get(primary.operation_type)
            if not strategy:
                return None
                
            # Attempt resolution
            resolution = await strategy(conflict.operations)
            if resolution:
                conflict.resolved = True
                conflict.resolution = resolution
                
            return resolution
            
        except Exception as e:
            self.metrics.record_error('conflict_resolution_error', str(e))
            return None
            
    def _operations_conflict(self, op1: SyncOperation, op2: SyncOperation) -> bool:
        """Determine if two operations conflict"""
        # Same file
        if op1.path != op2.path:
            return False
            
        # Different users
        if op1.user_id == op2.user_id:
            return False
            
        # Check for overlapping modifications
        if op1.operation_type == 'modify' and op2.operation_type == 'modify':
            return self._modifications_overlap(op1, op2)
            
        # Delete conflicts with anything
        if 'delete' in (op1.operation_type, op2.operation_type):
            return True
            
        # Insert operations might conflict
        if op1.operation_type == 'insert' and op2.operation_type == 'insert':
            return abs(op1.position - op2.position) < 2
            
        return False
        
    async def _resolve_modify_conflict(self, operations: List[SyncOperation]) -> Optional[SyncOperation]:
        """Resolve conflict between modify operations"""
        try:
            # Sort by timestamp
            sorted_ops = sorted(operations, key=lambda x: x.timestamp)
            base_content = sorted_ops[0].content
            
            # Apply diff3 merge
            merger = difflib.Differ()
            merged_content = self._merge_changes(
                base_content,
                [op.content for op in sorted_ops[1:]]
            )
            
            if merged_content:
                return SyncOperation(
                    operation_type='modify',
                    path=operations[0].path,
                    content=merged_content,
                    position=None,
                    user_id='system',
                    timestamp=datetime.now().timestamp(),
                    version=-1
                )
                
            return None
            
        except Exception as e:
            self.metrics.record_error('modify_resolution_error', str(e))
            return None
            
    async def _resolve_delete_conflict(self, operations: List[SyncOperation]) -> Optional[SyncOperation]:
        """Resolve conflict involving delete operations"""
        # Delete always wins
        delete_op = next(op for op in operations if op.operation_type == 'delete')
        return delete_op
        
    async def _resolve_insert_conflict(self, operations: List[SyncOperation]) -> Optional[SyncOperation]:
        """Resolve conflict between insert operations"""
        try:
            # Sort by position
            sorted_ops = sorted(operations, key=lambda x: x.position)
            
            # Adjust positions to prevent overlap
            current_pos = sorted_ops[0].position
            merged_content = ""
            
            for op in sorted_ops:
                if op.position <= current_pos:
                    op.position = current_pos + 1
                merged_content += op.content
                current_pos = op.position + len(op.content)
                
            return SyncOperation(
                operation_type='insert',
                path=operations[0].path,
                content=merged_content,
                position=sorted_ops[0].position,
                user_id='system',
                timestamp=datetime.now().timestamp(),
                version=-1
            )
            
        except Exception as e:
            self.metrics.record_error('insert_resolution_error', str(e))
            return None
            
    def _merge_changes(self, base: str, changes: List[str]) -> Optional[str]:
        """Merge multiple changes using diff3"""
        try:
            # Convert strings to lines
            base_lines = base.splitlines(True)
            change_lines = [c.splitlines(True) for c in changes]
            
            # Create differ
            d = difflib.Differ()
            
            # Merge each change sequentially
            current = base_lines
            for change in change_lines:
                diff = list(d.compare(current, change))
                current = [l[2:] for l in diff if l.startswith('  ') or l.startswith('+ ')]
                
            return ''.join(current)
            
        except Exception:
            return None 