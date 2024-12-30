from typing import Dict, Any, List, Optional
import asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import logging
import time
from .query_optimizer import QueryOptimizer

logger = logging.getLogger(__name__)

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = sa.Column(sa.String, primary_key=True)
    name = sa.Column(sa.String)
    email = sa.Column(sa.String)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)
    last_active = sa.Column(sa.DateTime)

class Session(Base):
    __tablename__ = 'sessions'
    
    id = sa.Column(sa.String, primary_key=True)
    user_id = sa.Column(sa.String, sa.ForeignKey('users.id'))
    started_at = sa.Column(sa.DateTime, default=datetime.utcnow)
    ended_at = sa.Column(sa.DateTime, nullable=True)
    ip_address = sa.Column(sa.String)

class Operation(Base):
    __tablename__ = 'operations'
    
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    type = sa.Column(sa.String)  # 'insert', 'delete', 'modify'
    path = sa.Column(sa.String)
    content = sa.Column(sa.Text, nullable=True)
    position = sa.Column(sa.Integer, nullable=True)
    user_id = sa.Column(sa.String, sa.ForeignKey('users.id'))
    timestamp = sa.Column(sa.DateTime, default=datetime.utcnow)
    version = sa.Column(sa.Integer)
    commit_hash = sa.Column(sa.String, nullable=True)

class Conflict(Base):
    __tablename__ = 'conflicts'
    
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    path = sa.Column(sa.String)
    resolved = sa.Column(sa.Boolean, default=False)
    resolution_type = sa.Column(sa.String, nullable=True)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)
    resolved_at = sa.Column(sa.DateTime, nullable=True)

class ConflictOperation(Base):
    __tablename__ = 'conflict_operations'
    
    conflict_id = sa.Column(sa.Integer, sa.ForeignKey('conflicts.id'), primary_key=True)
    operation_id = sa.Column(sa.Integer, sa.ForeignKey('operations.id'), primary_key=True)

class Metric(Base):
    __tablename__ = 'metrics'
    
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    name = sa.Column(sa.String)
    value = sa.Column(sa.Float)
    metadata = sa.Column(sa.JSON)
    timestamp = sa.Column(sa.DateTime, default=datetime.utcnow)

class DatabaseManager:
    def __init__(self, connection_url: str):
        self.engine = create_async_engine(connection_url)
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        self.metrics = MetricsTracker()
        self.query_optimizer = QueryOptimizer()
        
    async def init_db(self):
        """Initialize database schema"""
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                
        except Exception as e:
            self.metrics.record_error('db_init_error', str(e))
            raise
            
    async def get_session(self) -> AsyncSession:
        """Get database session"""
        return self.SessionLocal()
        
    async def record_operation(self, 
                             operation_type: str,
                             path: str,
                             user_id: str,
                             content: Optional[str] = None,
                             position: Optional[int] = None,
                             version: int = 0,
                             commit_hash: Optional[str] = None) -> Operation:
        """Record a new operation"""
        try:
            async with self.get_session() as session:
                operation = Operation(
                    type=operation_type,
                    path=path,
                    content=content,
                    position=position,
                    user_id=user_id,
                    version=version,
                    commit_hash=commit_hash
                )
                session.add(operation)
                await session.commit()
                return operation
                
        except Exception as e:
            self.metrics.record_error('db_operation_error', str(e))
            raise
            
    async def record_conflict(self, 
                            path: str,
                            operations: List[int]) -> Conflict:
        """Record a new conflict"""
        try:
            async with self.get_session() as session:
                conflict = Conflict(path=path)
                session.add(conflict)
                await session.flush()
                
                # Link operations to conflict
                for op_id in operations:
                    conflict_op = ConflictOperation(
                        conflict_id=conflict.id,
                        operation_id=op_id
                    )
                    session.add(conflict_op)
                    
                await session.commit()
                return conflict
                
        except Exception as e:
            self.metrics.record_error('db_conflict_error', str(e))
            raise
            
    async def update_user_activity(self, user_id: str):
        """Update user's last active timestamp"""
        try:
            async with self.get_session() as session:
                user = await session.get(User, user_id)
                if user:
                    user.last_active = datetime.utcnow()
                    await session.commit()
                    
        except Exception as e:
            self.metrics.record_error('db_user_update_error', str(e))
            
    async def get_user_operations(self, 
                                user_id: str,
                                limit: int = 100) -> List[Operation]:
        """Get recent operations for a user"""
        try:
            async with self.get_session() as session:
                query = sa.select(Operation)\
                    .where(Operation.user_id == user_id)\
                    .order_by(Operation.timestamp.desc())\
                    .limit(limit)
                    
                result = await session.execute(query)
                return result.scalars().all()
                
        except Exception as e:
            self.metrics.record_error('db_query_error', str(e))
            return []
            
    async def get_file_operations(self, 
                                path: str,
                                limit: int = 100) -> List[Operation]:
        """Get recent operations for a file"""
        try:
            async with self.get_session() as session:
                query = sa.select(Operation)\
                    .where(Operation.path == path)\
                    .order_by(Operation.timestamp.desc())\
                    .limit(limit)
                    
                result = await session.execute(query)
                return result.scalars().all()
                
        except Exception as e:
            self.metrics.record_error('db_query_error', str(e))
            return []
            
    async def get_unresolved_conflicts(self) -> List[Conflict]:
        """Get all unresolved conflicts"""
        try:
            async with self.get_session() as session:
                query = sa.select(Conflict)\
                    .where(Conflict.resolved == False)
                    
                result = await session.execute(query)
                return result.scalars().all()
                
        except Exception as e:
            self.metrics.record_error('db_query_error', str(e))
            return []
            
    async def execute_query(self, query: str, params: Optional[Dict] = None) -> Any:
        """Execute an optimized query"""
        start_time = time.time()
        
        # Generate query hash for caching
        query_hash = hash(f"{query}:{str(params)}")
        
        # Check cache
        cached_result = await self.query_optimizer.cache.get(query_hash)
        if cached_result is not None:
            await self.metrics.increment("cache.hits")
            return cached_result
            
        # Optimize query
        optimized_query = await self.query_optimizer.analyze_query(query, params)
        
        try:
            # Execute query (implement actual database execution)
            result = await self._execute_raw_query(optimized_query, params)
            
            # Record execution stats
            execution_time = time.time() - start_time
            await self.query_optimizer.record_execution(
                query_hash,
                execution_time,
                len(result) if hasattr(result, '__len__') else 0
            )
            
            # Cache result
            await self.query_optimizer.cache.set(query_hash, result, execution_time)
            
            return result
            
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            raise 