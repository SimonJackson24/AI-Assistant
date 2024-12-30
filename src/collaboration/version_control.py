from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import asyncio
import git
from pathlib import Path
from datetime import datetime

from ..monitoring.metrics import MetricsTracker
from .sync_manager import SyncOperation

@dataclass
class CommitInfo:
    hash: str
    author: str
    message: str
    timestamp: float
    changes: Dict[str, str]  # path -> change_type ('A', 'M', 'D')
    branch: str

class VersionControlManager:
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.repo = git.Repo(repo_path)
        self.metrics = MetricsTracker()
        self.lock = asyncio.Lock()
        
    async def stage_changes(self, operations: List[SyncOperation]) -> bool:
        """Stage changes from sync operations"""
        try:
            async with self.lock:
                for op in operations:
                    file_path = Path(op.path)
                    if op.operation_type == 'delete':
                        self.repo.index.remove(str(file_path))
                    else:
                        self.repo.index.add(str(file_path))
                        
                return True
                
        except Exception as e:
            self.metrics.record_error('git_stage_error', str(e))
            return False
            
    async def commit_changes(self, 
                           message: str, 
                           author: str, 
                           branch: Optional[str] = None) -> Optional[str]:
        """Commit staged changes"""
        try:
            async with self.lock:
                if branch:
                    current = self.repo.active_branch.name
                    if branch != current:
                        await self.switch_branch(branch)
                        
                # Create commit
                commit = self.repo.index.commit(
                    message,
                    author=git.Actor(author, f"{author}@example.com")
                )
                
                self.metrics.record('git_commit', {
                    'hash': commit.hexsha,
                    'author': author,
                    'branch': branch or self.repo.active_branch.name
                })
                
                return commit.hexsha
                
        except Exception as e:
            self.metrics.record_error('git_commit_error', str(e))
            return None
            
    async def switch_branch(self, branch_name: str, create: bool = False) -> bool:
        """Switch to a different branch"""
        try:
            async with self.lock:
                if create and branch_name not in self.repo.heads:
                    self.repo.create_head(branch_name)
                    
                self.repo.heads[branch_name].checkout()
                return True
                
        except Exception as e:
            self.metrics.record_error('git_branch_error', str(e))
            return False
            
    async def get_file_history(self, file_path: str, 
                             max_entries: int = 10) -> List[CommitInfo]:
        """Get commit history for a file"""
        try:
            commits = []
            file_path = Path(file_path)
            
            for commit in self.repo.iter_commits(paths=str(file_path)):
                if len(commits) >= max_entries:
                    break
                    
                # Get change type
                changes = {}
                for parent in commit.parents:
                    diff = parent.diff(commit, paths=str(file_path))
                    for d in diff:
                        changes[str(Path(d.a_path))] = d.change_type
                        
                commits.append(CommitInfo(
                    hash=commit.hexsha,
                    author=commit.author.name,
                    message=commit.message,
                    timestamp=commit.committed_date,
                    changes=changes,
                    branch=self._get_branch_for_commit(commit)
                ))
                
            return commits
            
        except Exception as e:
            self.metrics.record_error('git_history_error', str(e))
            return []
            
    async def create_branch_for_user(self, user_id: str) -> bool:
        """Create a user-specific branch"""
        branch_name = f"user/{user_id}"
        return await self.switch_branch(branch_name, create=True)
        
    async def merge_user_changes(self, user_id: str, 
                               target_branch: str = "main") -> bool:
        """Merge user branch into target branch"""
        try:
            async with self.lock:
                user_branch = f"user/{user_id}"
                if user_branch not in self.repo.heads:
                    return False
                    
                # Switch to target branch
                await self.switch_branch(target_branch)
                
                # Merge user branch
                self.repo.git.merge(user_branch)
                
                self.metrics.record('git_merge', {
                    'user': user_id,
                    'source': user_branch,
                    'target': target_branch
                })
                
                return True
                
        except git.GitCommandError as e:
            self.metrics.record_error('git_merge_error', str(e))
            return False
            
    def _get_branch_for_commit(self, commit) -> str:
        """Get branch name for a commit"""
        for head in self.repo.heads:
            if commit in self.repo.iter_commits(head):
                return head.name
        return "unknown" 