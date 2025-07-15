"""
Cache service for performance optimization
"""
import json
import logging
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta

import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.exceptions import CacheError

logger = logging.getLogger(__name__)
settings = get_settings()


class CacheService:
    """Intelligent cache service with multi-layer caching"""
    
    def __init__(self):
        self.redis: Optional[Redis] = None
        self.local_cache: Dict[str, Any] = {}
        self.local_cache_ttl: Dict[str, datetime] = {}
        self.max_local_cache_size = 1000
        
    async def init_redis(self):
        """Initialize Redis connection"""
        try:
            self.redis = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Redis connection failed: {str(e)}")
            self.redis = None
    
    async def close_redis(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache (local first, then Redis)"""
        try:
            # Check local cache first
            if key in self.local_cache:
                if key in self.local_cache_ttl:
                    if datetime.utcnow() < self.local_cache_ttl[key]:
                        return self.local_cache[key]
                    else:
                        # Expired, remove from local cache
                        del self.local_cache[key]
                        del self.local_cache_ttl[key]
                else:
                    return self.local_cache[key]
            
            # Check Redis cache
            if self.redis:
                cached_value = await self.redis.get(key)
                if cached_value:
                    try:
                        value = json.loads(cached_value)
                        # Cache in local for faster access
                        self._set_local_cache(key, value, ttl=300)  # 5 minutes local cache
                        return value
                    except json.JSONDecodeError:
                        return cached_value
            
            return None
            
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {str(e)}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache (both local and Redis)"""
        try:
            # Set in local cache
            self._set_local_cache(key, value, ttl or settings.CACHE_TTL)
            
            # Set in Redis
            if self.redis:
                if ttl:
                    await self.redis.setex(key, ttl, json.dumps(value, default=str))
                else:
                    await self.redis.set(key, json.dumps(value, default=str))
                return True
            
            return True  # Local cache set successfully
            
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            # Delete from local cache
            if key in self.local_cache:
                del self.local_cache[key]
            if key in self.local_cache_ttl:
                del self.local_cache_ttl[key]
            
            # Delete from Redis
            if self.redis:
                await self.redis.delete(key)
            
            return True
            
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {str(e)}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern"""
        try:
            deleted_count = 0
            
            # Clear from local cache
            keys_to_delete = []
            for key in self.local_cache.keys():
                if self._match_pattern(key, pattern):
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                del self.local_cache[key]
                if key in self.local_cache_ttl:
                    del self.local_cache_ttl[key]
                deleted_count += 1
            
            # Clear from Redis
            if self.redis:
                keys = await self.redis.keys(pattern)
                if keys:
                    await self.redis.delete(*keys)
                    deleted_count += len(keys)
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Cache clear pattern error for pattern {pattern}: {str(e)}")
            return 0
    
    def _set_local_cache(self, key: str, value: Any, ttl: int):
        """Set value in local cache"""
        # Clean up if cache is too large
        if len(self.local_cache) >= self.max_local_cache_size:
            self._cleanup_local_cache()
        
        self.local_cache[key] = value
        self.local_cache_ttl[key] = datetime.utcnow() + timedelta(seconds=ttl)
    
    def _cleanup_local_cache(self):
        """Clean up expired entries from local cache"""
        now = datetime.utcnow()
        expired_keys = []
        
        for key, expiry in self.local_cache_ttl.items():
            if now >= expiry:
                expired_keys.append(key)
        
        for key in expired_keys:
            if key in self.local_cache:
                del self.local_cache[key]
            del self.local_cache_ttl[key]
        
        # If still too large, remove oldest entries
        if len(self.local_cache) >= self.max_local_cache_size:
            # Remove 20% of entries
            remove_count = int(self.max_local_cache_size * 0.2)
            keys_to_remove = list(self.local_cache.keys())[:remove_count]
            
            for key in keys_to_remove:
                del self.local_cache[key]
                if key in self.local_cache_ttl:
                    del self.local_cache_ttl[key]
    
    def _match_pattern(self, key: str, pattern: str) -> bool:
        """Simple pattern matching (supports * wildcard)"""
        import re
        pattern = pattern.replace('*', '.*')
        return re.match(pattern, key) is not None
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = {
            "local_cache_size": len(self.local_cache),
            "local_cache_ttl_size": len(self.local_cache_ttl),
            "redis_connected": self.redis is not None
        }
        
        if self.redis:
            try:
                info = await self.redis.info()
                stats["redis_memory"] = info.get("used_memory_human", "N/A")
                stats["redis_keys"] = info.get("db0", {}).get("keys", 0)
            except Exception as e:
                logger.error(f"Error getting Redis stats: {str(e)}")
        
        return stats


class TemplateCache:
    """Specialized cache for templates"""
    
    def __init__(self, cache_service: CacheService):
        self.cache_service = cache_service
        self.cache_prefix = "template:"
        self.default_ttl = settings.TEMPLATE_CACHE_TTL
    
    async def get_template(self, resource_type_id: int, template_type: str) -> Optional[str]:
        """Get cached template"""
        cache_key = f"{self.cache_prefix}{resource_type_id}:{template_type}"
        return await self.cache_service.get(cache_key)
    
    async def set_template(self, resource_type_id: int, template_type: str, template: str) -> bool:
        """Cache template"""
        cache_key = f"{self.cache_prefix}{resource_type_id}:{template_type}"
        return await self.cache_service.set(cache_key, template, self.default_ttl)
    
    async def invalidate_resource_templates(self, resource_type_id: int) -> int:
        """Invalidate all templates for a resource type"""
        pattern = f"{self.cache_prefix}{resource_type_id}:*"
        return await self.cache_service.clear_pattern(pattern)
    
    async def invalidate_all_templates(self) -> int:
        """Invalidate all cached templates"""
        pattern = f"{self.cache_prefix}*"
        return await self.cache_service.clear_pattern(pattern)


class DocumentationCache:
    """Specialized cache for documentation"""
    
    def __init__(self, cache_service: CacheService):
        self.cache_service = cache_service
        self.cache_prefix = "docs:"
        self.default_ttl = 7200  # 2 hours
    
    async def get_resource_docs(self, provider: str, resource_type: str) -> Optional[Dict[str, Any]]:
        """Get cached resource documentation"""
        cache_key = f"{self.cache_prefix}{provider}:{resource_type}"
        return await self.cache_service.get(cache_key)
    
    async def set_resource_docs(self, provider: str, resource_type: str, docs: Dict[str, Any]) -> bool:
        """Cache resource documentation"""
        cache_key = f"{self.cache_prefix}{provider}:{resource_type}"
        return await self.cache_service.set(cache_key, docs, self.default_ttl)
    
    async def invalidate_provider_docs(self, provider: str) -> int:
        """Invalidate all documentation for a provider"""
        pattern = f"{self.cache_prefix}{provider}:*"
        return await self.cache_service.clear_pattern(pattern)


class GenerationCache:
    """Specialized cache for generation results"""
    
    def __init__(self, cache_service: CacheService):
        self.cache_service = cache_service
        self.cache_prefix = "generation:"
        self.default_ttl = 1800  # 30 minutes
    
    async def get_generation_result(self, request_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached generation result"""
        cache_key = f"{self.cache_prefix}{request_hash}"
        return await self.cache_service.get(cache_key)
    
    async def set_generation_result(self, request_hash: str, result: Dict[str, Any]) -> bool:
        """Cache generation result"""
        cache_key = f"{self.cache_prefix}{request_hash}"
        return await self.cache_service.set(cache_key, result, self.default_ttl)
    
    def generate_request_hash(self, request: Dict[str, Any]) -> str:
        """Generate hash for request caching"""
        import hashlib
        request_str = json.dumps(request, sort_keys=True)
        return hashlib.md5(request_str.encode()).hexdigest()


# Global cache service instance
cache_service = CacheService()
template_cache = TemplateCache(cache_service)
documentation_cache = DocumentationCache(cache_service)
generation_cache = GenerationCache(cache_service)