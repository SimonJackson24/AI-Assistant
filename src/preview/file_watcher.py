import asyncio
from pathlib import Path
from typing import Set, Callable, Awaitable, Dict
from watchfiles import awatch, Change
import hashlib

class FileWatcher:
    def __init__(self):
        self.watched_paths: Set[Path] = set()
        self._stop_event = asyncio.Event()
        self._file_hashes: Dict[str, str] = {}
        self._handlers: Dict[str, Callable[[str, str], Awaitable[None]]] = {}
        
    def add_path(self, path: str):
        """Add a path to watch"""
        self.watched_paths.add(Path(path))
        
    def add_handler(self, extension: str, handler: Callable[[str, str], Awaitable[None]]):
        """Add a handler for specific file extensions"""
        self._handlers[extension] = handler
        
    async def start(self):
        """Start watching for file changes"""
        try:
            async for changes in awatch(*self.watched_paths):
                if self._stop_event.is_set():
                    break
                    
                for change_type, file_path in changes:
                    if change_type in {Change.added, Change.modified}:
                        await self._handle_file_change(file_path)
        except Exception as e:
            print(f"Error in file watcher: {e}")
            
    def stop(self):
        """Stop watching for changes"""
        self._stop_event.set()
        
    async def _handle_file_change(self, file_path: str):
        """Handle file changes"""
        path = Path(file_path)
        
        # Skip if file doesn't exist or is temporary
        if not path.exists() or path.name.startswith('.'):
            return
            
        # Get file hash
        new_hash = await self._get_file_hash(file_path)
        if new_hash == self._file_hashes.get(file_path):
            return
            
        self._file_hashes[file_path] = new_hash
        
        # Get handler for file extension
        handler = self._handlers.get(path.suffix)
        if handler:
            try:
                content = await self._read_file(file_path)
                await handler(file_path, content)
            except Exception as e:
                print(f"Error handling file {file_path}: {e}")
                
    async def _get_file_hash(self, file_path: str) -> str:
        """Get SHA256 hash of file contents"""
        content = await self._read_file(file_path)
        return hashlib.sha256(content.encode()).hexdigest()
        
    @staticmethod
    async def _read_file(file_path: str) -> str:
        """Read file contents asynchronously"""
        async with asyncio.Lock():
            with open(file_path, 'r') as f:
                return f.read() 