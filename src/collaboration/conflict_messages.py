from typing import Dict, Any
from dataclasses import dataclass
from datetime import datetime

from .conflict_resolver import Conflict
from .sync_manager import SyncOperation

@dataclass
class ConflictMessage:
    title: str
    description: str
    severity: str  # 'info', 'warning', 'error'
    actions: Dict[str, str]
    metadata: Dict[str, Any]

class ConflictMessageGenerator:
    def generate_message(self, conflict: Conflict) -> ConflictMessage:
        """Generate appropriate UI message for a conflict"""
        if len(conflict.operations) < 2:
            return self._create_generic_message(conflict)
            
        primary_op = conflict.operations[0]
        
        if primary_op.operation_type == 'modify':
            return self._create_modify_message(conflict)
        elif primary_op.operation_type == 'delete':
            return self._create_delete_message(conflict)
        elif primary_op.operation_type == 'insert':
            return self._create_insert_message(conflict)
        else:
            return self._create_generic_message(conflict)
            
    def _create_modify_message(self, conflict: Conflict) -> ConflictMessage:
        users = ', '.join(conflict.users[:-1]) + f" and {conflict.users[-1]}"
        return ConflictMessage(
            title="Conflicting Changes Detected",
            description=f"Multiple users ({users}) have made changes to this file. "
                       "The system will attempt to merge these changes automatically.",
            severity="warning",
            actions={
                "accept_merge": "Accept Merged Changes",
                "keep_mine": "Keep My Changes",
                "keep_theirs": "Keep Their Changes",
                "manual_resolve": "Resolve Manually"
            },
            metadata={
                "conflict_type": "modify",
                "users": conflict.users,
                "timestamp": conflict.timestamp,
                "file": conflict.operations[0].path
            }
        )
        
    def _create_delete_message(self, conflict: Conflict) -> ConflictMessage:
        deleting_user = next(
            op.user_id for op in conflict.operations 
            if op.operation_type == 'delete'
        )
        return ConflictMessage(
            title="File Deletion Conflict",
            description=f"User {deleting_user} is attempting to delete this file "
                       "while other users have pending changes.",
            severity="error",
            actions={
                "accept_delete": "Accept Deletion",
                "reject_delete": "Reject Deletion",
                "manual_resolve": "Resolve Manually"
            },
            metadata={
                "conflict_type": "delete",
                "deleting_user": deleting_user,
                "users": conflict.users,
                "timestamp": conflict.timestamp,
                "file": conflict.operations[0].path
            }
        )
        
    def _create_insert_message(self, conflict: Conflict) -> ConflictMessage:
        return ConflictMessage(
            title="Conflicting Insertions",
            description="Multiple users are attempting to insert content at the same location.",
            severity="warning",
            actions={
                "merge_sequential": "Insert Sequentially",
                "keep_mine": "Keep My Insert",
                "keep_theirs": "Keep Their Insert",
                "manual_resolve": "Resolve Manually"
            },
            metadata={
                "conflict_type": "insert",
                "users": conflict.users,
                "timestamp": conflict.timestamp,
                "file": conflict.operations[0].path
            }
        )
        
    def _create_generic_message(self, conflict: Conflict) -> ConflictMessage:
        return ConflictMessage(
            title="Conflict Detected",
            description="A conflict has been detected in the current operation.",
            severity="info",
            actions={
                "retry": "Retry Operation",
                "cancel": "Cancel Operation",
                "manual_resolve": "Resolve Manually"
            },
            metadata={
                "conflict_type": "generic",
                "users": conflict.users,
                "timestamp": conflict.timestamp,
                "file": conflict.operations[0].path
            }
        ) 