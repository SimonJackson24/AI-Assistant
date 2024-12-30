from typing import Dict, Any, List, Optional, Set
import logging
import time
from dataclasses import dataclass
import asyncio
from collections import OrderedDict
from src.monitoring.metrics import MetricsCollector

logger = logging.getLogger(__name__)

@dataclass
class QueryStats:
    """Statistics for a single query"""
    query_hash: str
    execution_count: int = 0
    total_time: float = 0.0
    avg_time: float = 0.0
    last_executed: float = 0.0
    rows_affected: int = 0

@dataclass
class QueryCacheConfig:
    enabled: bool = True
    max_size: int = 1000
    ttl: int = 3600  # 1 hour
    min_exec_time: float = 0.1  # Only cache queries that take longer than 100ms

class QueryCache:
    """LRU cache for query results"""
    
    def __init__(self, config: QueryCacheConfig):
        self.config = config
        self._cache = OrderedDict()
        self._stats: Dict[str, QueryStats] = {}
        
    async def get(self, query_hash: str) -> Optional[Any]:
        """Get cached query result"""
        if not self.config.enabled:
            return None
            
        if query_hash in self._cache:
            result, timestamp = self._cache[query_hash]
            if time.time() - timestamp <= self.config.ttl:
                # Move to end (most recently used)
                self._cache.move_to_end(query_hash)
                return result
            else:
                # Expired
                del self._cache[query_hash]
        return None
        
    async def set(self, query_hash: str, result: Any, execution_time: float):
        """Cache query result if it meets criteria"""
        if not self.config.enabled or execution_time < self.config.min_exec_time:
            return
            
        self._cache[query_hash] = (result, time.time())
        if len(self._cache) > self.config.max_size:
            self._cache.popitem(first=True)  # Remove oldest

class QueryOptimizer:
    """Optimizes database queries for better performance"""
    
    def __init__(self):
        self.metrics = MetricsCollector()
        self.cache = QueryCache(QueryCacheConfig())
        self._slow_query_threshold = 1.0  # 1 second
        self._query_stats: Dict[str, QueryStats] = {}
        self._table_stats: Dict[str, Dict[str, Any]] = {}
        self._suggested_indexes: Set[str] = set()
        
    async def analyze_query(self, query: str, params: Optional[Dict] = None) -> str:
        """Analyze and optimize a query"""
        # Basic query optimization rules
        query = query.strip()
        
        # Convert to lowercase for consistent analysis
        query_lower = query.lower()
        
        # Check for common anti-patterns
        if "select *" in query_lower:
            logger.warning("Consider specifying columns instead of SELECT *")
            
        if "like '%..." in query_lower:
            logger.warning("Leading wildcard LIKE patterns prevent index usage")
            
        if " or " in query_lower:
            logger.warning("OR conditions might prevent index usage")
            
        # Suggest indexes based on WHERE clauses
        await self._analyze_for_indexes(query)
        
        return query
        
    async def record_execution(self, query_hash: str, execution_time: float, rows_affected: int):
        """Record query execution statistics"""
        if query_hash not in self._query_stats:
            self._query_stats[query_hash] = QueryStats(query_hash)
            
        stats = self._query_stats[query_hash]
        stats.execution_count += 1
        stats.total_time += execution_time
        stats.avg_time = stats.total_time / stats.execution_count
        stats.last_executed = time.time()
        stats.rows_affected = rows_affected
        
        # Record metrics
        await self.metrics.record_metrics("query_performance", {
            "execution_time": execution_time,
            "rows_affected": rows_affected
        })
        
        # Check for slow queries
        if execution_time > self._slow_query_threshold:
            logger.warning(f"Slow query detected (took {execution_time:.2f}s): {query_hash}")
            
    async def _analyze_for_indexes(self, query: str):
        """Analyze query for potential index improvements"""
        # Extract table and column names from WHERE clauses
        tables_columns = self._extract_where_columns(query)
        
        for table, columns in tables_columns.items():
            for column in columns:
                index_name = f"idx_{table}_{column}"
                if index_name not in self._suggested_indexes:
                    self._suggested_indexes.add(index_name)
                    logger.info(f"Suggested index: CREATE INDEX {index_name} ON {table}({column})")
                    
    def _extract_where_columns(self, query: str) -> Dict[str, List[str]]:
        """Extract table and column names from WHERE clauses"""
        # Implement actual SQL parsing here
        # This is a simplified example
        return {}
        
    async def get_optimization_report(self) -> Dict[str, Any]:
        """Generate query optimization report"""
        slow_queries = [
            stats for stats in self._query_stats.values()
            if stats.avg_time > self._slow_query_threshold
        ]
        
        return {
            "total_queries_analyzed": len(self._query_stats),
            "slow_queries": len(slow_queries),
            "suggested_indexes": list(self._suggested_indexes),
            "cache_stats": {
                "size": len(self.cache._cache),
                "hit_rate": await self.metrics.get_rate("cache.hits", "cache.misses")
            }
        } 