"""
LLM Cache Layer with Semantic Matching

Implements intelligent caching for LLM queries using Redis with semantic similarity.
Supports both Redis LangCache REST API and DIY semantic caching.

Features:
- Semantic similarity matching (similar queries hit same cache)
- Automatic fallback (LangCache API → DIY Redis → No cache)
- TTL-based expiration (default: 1 hour)
- Metrics tracking (hit/miss rates, latency)
- Configurable similarity threshold (default: 0.95)

Usage:
    cache = CacheLayer(mode='auto')

    # Try to get cached response
    cached = await cache.get_cached_response(query)
    if cached:
        return cached  # Cache hit!

    # Cache miss - call LLM
    response = await call_llm(query)

    # Store in cache for future queries
    await cache.cache_response(query, response)
"""

import os
import json
import time
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import redis.asyncio as redis
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
REDIS_CACHE_TTL = int(os.getenv("REDIS_CACHE_TTL", "3600"))  # 1 hour default
CACHE_SIMILARITY_THRESHOLD = float(os.getenv("CACHE_SIMILARITY_THRESHOLD", "0.95"))
CACHE_MODE = os.getenv("CACHE_MODE", "auto")  # auto, langcache, diy, disabled

# Redis LangCache SDK (when available)
LANGCACHE_API_URL = os.getenv("LANGCACHE_API_URL", "")
LANGCACHE_CACHE_ID = os.getenv("LANGCACHE_CACHE_ID", "")
LANGCACHE_API_KEY = os.getenv("LANGCACHE_API_KEY", "")

# OpenAI for embeddings (DIY mode)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Filter detection patterns for conditional cache matching
# Queries with these patterns use exact matching to prevent filter collisions
FILTER_PATTERNS = [
    # Price filters (exact amounts and comparisons)
    r'\$\d+',                           # Explicit price: $50, $6, $100
    r'\d+\s*dollars?',                  # "50 dollars", "6 dollar"
    r'(under|below|less\s+than)\s*\$',  # "under $50", "below $6", "less than $100"
    r'(over|above|more\s+than)\s*\$',   # "over $50", "above $6", "more than $100"
    r'between\s*\$',                    # "between $10 and $50"
    r'(cheaper|less\s+expensive)',      # "cheaper than", "less expensive"
    r'(pricier|more\s+expensive)',      # "pricier than", "more expensive"

    # Stock status filters
    r'in\s+stock',                      # "in stock"
    r'out\s+of\s+stock',                # "out of stock"
    r'available',                       # "available"
    r'unavailable',                     # "unavailable"

    # Sale/discount filters
    r'on\s+sale',                       # "on sale"
    r'discounted',                      # "discounted"
    r'(sale|discount)\s+price',         # "sale price", "discount price"

    # Sorting keywords (price-based)
    r'cheapest',                        # "cheapest"
    r'most\s+expensive',                # "most expensive"
    r'lowest\s+price',                  # "lowest price"
    r'highest\s+price',                 # "highest price"
    r'sorted?\s+by\s+price',            # "sort by price", "sorted by price"

    # Temporal filters (date-based)
    r'latest',                          # "latest"
    r'newest',                          # "newest"
    r'recent',                          # "recent"
    r'new\s+arrivals?',                 # "new arrivals", "new arrival"
    r'just\s+(arrived|added)',          # "just arrived", "just added"

    # CRITICAL: Negatable attributes (JAI-2210)
    # "sterile" and "non-sterile" are semantically similar but mean OPPOSITE things
    # Must use exact matching to prevent "sterile gloves" hitting "non-sterile gloves" cache
    r'\bsterile\b',                     # "sterile gloves" (NOT "non-sterile")
    r'\bnon-?sterile\b',                # "non-sterile", "nonsterile"
    r'\blatex\b',                       # "latex gloves"
    r'\blatex-?free\b',                 # "latex-free", "latexfree"
    r'\bpowder-?free\b',                # "powder-free", "powderfree"
    r'\bpowdered\b',                    # "powdered gloves"
    r'\bcoated\b',                      # "coated slides"
    r'\buncoated\b',                    # "uncoated slides"
    r'\bfiltered\b',                    # "filtered tips"
    r'\bunfiltered\b',                  # "unfiltered tips"
]


class CacheMetrics:
    """Track cache performance metrics"""

    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.errors = 0
        self.total_hit_latency_ms = 0.0
        self.total_miss_latency_ms = 0.0
        self.started_at = datetime.now()

    def record_hit(self, latency_ms: float):
        self.hits += 1
        self.total_hit_latency_ms += latency_ms

    def record_miss(self, latency_ms: float):
        self.misses += 1
        self.total_miss_latency_ms += latency_ms

    def record_error(self):
        self.errors += 1

    def get_stats(self) -> Dict[str, Any]:
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0.0
        avg_hit_latency = (self.total_hit_latency_ms / self.hits) if self.hits > 0 else 0.0
        avg_miss_latency = (self.total_miss_latency_ms / self.misses) if self.misses > 0 else 0.0
        uptime = (datetime.now() - self.started_at).total_seconds()

        return {
            "hits": self.hits,
            "misses": self.misses,
            "errors": self.errors,
            "total_queries": total,
            "hit_rate_percent": round(hit_rate, 2),
            "avg_hit_latency_ms": round(avg_hit_latency, 2),
            "avg_miss_latency_ms": round(avg_miss_latency, 2),
            "uptime_seconds": round(uptime, 2),
            "queries_per_minute": round((total / uptime * 60), 2) if uptime > 0 else 0.0
        }


class CacheLayer:
    """
    Flexible LLM caching layer with semantic matching.

    Modes:
    - auto: Try LangCache API → DIY Redis → No cache (fallback chain)
    - langcache: Use Redis LangCache REST API only
    - diy: Use DIY semantic caching with Redis
    - disabled: No caching (passthrough)
    """

    def __init__(self, mode: Optional[str] = None):
        self.mode = mode if mode is not None else CACHE_MODE
        self.metrics = CacheMetrics()
        self.redis_client: Optional[redis.Redis] = None
        self.openai_client: Optional[AsyncOpenAI] = None
        self._initialized = False

        print(f"[CACHE] Initializing CacheLayer (mode: {self.mode})")

    async def initialize(self):
        """Initialize Redis and OpenAI clients (lazy initialization)"""
        if self._initialized:
            return

        try:
            if self.mode == "disabled":
                print("[CACHE] Caching disabled")
                self._initialized = True
                return

            # Initialize Redis client (needed for both modes)
            if self.mode in ["auto", "diy"]:
                try:
                    self.redis_client = await redis.from_url(
                        REDIS_URL,
                        encoding="utf-8",
                        decode_responses=True
                    )
                    # Test connection
                    await self.redis_client.ping()
                    print(f"[CACHE] Redis connected: {REDIS_URL}")
                except Exception as e:
                    print(f"[CACHE] Redis connection failed: {e}")
                    if self.mode == "diy":
                        # DIY mode requires Redis
                        raise
                    # Auto mode can fallback
                    self.redis_client = None

            # Initialize OpenAI client for embeddings (DIY mode)
            if self.mode in ["auto", "diy"] and self.redis_client:
                if OPENAI_API_KEY:
                    self.openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
                    print("[CACHE] OpenAI client initialized for embeddings")
                else:
                    print("[CACHE] No OpenAI API key - embeddings disabled")
                    if self.mode == "diy":
                        raise ValueError("DIY mode requires OPENAI_API_KEY for embeddings")

            # Check LangCache SDK availability (if in langcache or auto mode)
            if self.mode in ["auto", "langcache"]:
                if LANGCACHE_API_URL and LANGCACHE_CACHE_ID and LANGCACHE_API_KEY:
                    print(f"[CACHE] LangCache SDK configured: {LANGCACHE_API_URL}")
                else:
                    print("[CACHE] LangCache SDK not configured")
                    if self.mode == "langcache":
                        raise ValueError("LangCache mode requires LANGCACHE_API_URL, LANGCACHE_CACHE_ID, and LANGCACHE_API_KEY")

            self._initialized = True
            print(f"[CACHE] Initialization complete (mode: {self.mode})")

        except Exception as e:
            print(f"[CACHE] Initialization error: {e}")
            self.metrics.record_error()
            if self.mode != "auto":
                raise
            # Auto mode falls back to disabled
            self.mode = "disabled"
            self._initialized = True

    async def get_cached_response(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Try to get cached response for query using semantic matching.

        Returns:
            Cached response dict if found, None otherwise
        """
        if not self._initialized:
            await self.initialize()

        if self.mode == "disabled":
            return None

        start_time = time.time()

        try:
            # Try LangCache SDK first (if available)
            if self.mode in ["auto", "langcache"] and LANGCACHE_API_URL and LANGCACHE_CACHE_ID and LANGCACHE_API_KEY:
                cached = await self._get_from_langcache(query)
                if cached:
                    latency_ms = (time.time() - start_time) * 1000
                    self.metrics.record_hit(latency_ms)
                    print(f"[CACHE] ✅ HIT (LangCache SDK) - {latency_ms:.1f}ms")
                    return cached
                elif self.mode == "langcache":
                    # LangCache mode only - don't fallback
                    latency_ms = (time.time() - start_time) * 1000
                    self.metrics.record_miss(latency_ms)
                    print(f"[CACHE] ❌ MISS (LangCache SDK) - {latency_ms:.1f}ms")
                    return None

            # Try DIY Redis cache
            if self.mode in ["auto", "diy"] and self.redis_client and self.openai_client:
                cached = await self._get_from_diy_cache(query)
                if cached:
                    latency_ms = (time.time() - start_time) * 1000
                    self.metrics.record_hit(latency_ms)
                    print(f"[CACHE] ✅ HIT (DIY Redis) - {latency_ms:.1f}ms - similarity: {cached.get('_similarity', 'N/A')}")
                    return cached.get("response")
                else:
                    latency_ms = (time.time() - start_time) * 1000
                    self.metrics.record_miss(latency_ms)
                    print(f"[CACHE] ❌ MISS (DIY Redis) - {latency_ms:.1f}ms")
                    return None

            # No cache available
            latency_ms = (time.time() - start_time) * 1000
            self.metrics.record_miss(latency_ms)
            return None

        except Exception as e:
            print(f"[CACHE] Error getting cached response: {e}")
            self.metrics.record_error()
            return None

    async def cache_response(self, query: str, response: Dict[str, Any]):
        """
        Cache response for future queries.

        Args:
            query: User query
            response: LLM response to cache
        """
        if not self._initialized:
            await self.initialize()

        if self.mode == "disabled":
            return

        try:
            # Cache in LangCache SDK (if available)
            if self.mode in ["auto", "langcache"] and LANGCACHE_API_URL and LANGCACHE_CACHE_ID and LANGCACHE_API_KEY:
                await self._cache_in_langcache(query, response)

            # Cache in DIY Redis (if available)
            if self.mode in ["auto", "diy"] and self.redis_client and self.openai_client:
                await self._cache_in_diy(query, response)

        except Exception as e:
            print(f"[CACHE] Error caching response: {e}")
            self.metrics.record_error()

    async def _get_from_langcache(self, query: str) -> Optional[Dict[str, Any]]:
        """Get cached response from Redis LangCache using official SDK"""
        try:
            import asyncio
            import re
            from langcache import LangCache

            # Detect queries with filters using static patterns (defined at module level)
            # Filter queries use exact matching to prevent "$50" matching "$6"
            # Simple queries use semantic matching for better cache hits
            has_filters = any(re.search(pattern, query.lower()) for pattern in FILTER_PATTERNS)

            # Log which matching mode we're using
            if has_filters:
                print(f"[CACHE] Filter detected in query - using exact matching")
            else:
                print(f"[CACHE] No filters detected - using semantic matching")

            def _search_sync():
                """Synchronous search using SDK"""
                with LangCache(
                    server_url=LANGCACHE_API_URL,
                    cache_id=LANGCACHE_CACHE_ID,
                    api_key=LANGCACHE_API_KEY
                ) as lang_cache:
                    if has_filters:
                        # Filter query: use exact matching
                        # "gloves under $50" won't match "gloves under $6"
                        result = lang_cache.search(prompt=query, exact_match=True)
                    else:
                        # Simple query: use semantic matching
                        # "nitrile gloves" can match "nitrile glove" or "NBR gloves"
                        result = lang_cache.search(prompt=query)
                    return result

            # Run SDK call in thread pool (SDK is sync, we're async)
            result = await asyncio.to_thread(_search_sync)

            # SDK returns SearchResponse with 'data' attribute containing list of CacheEntry objects
            if result and hasattr(result, 'data') and result.data:
                # Response is stored as JSON string, parse it back to dict
                response_str = result.data[0].response

                # If response is a string, parse it as JSON
                if isinstance(response_str, str):
                    return json.loads(response_str)
                return response_str

            return None

        except Exception as e:
            print(f"[CACHE] LangCache SDK search error: {e}")
            return None

    async def _cache_in_langcache(self, query: str, response: Dict[str, Any]):
        """Cache response in Redis LangCache using official SDK"""
        try:
            import asyncio
            from langcache import LangCache

            def _set_sync():
                """Synchronous set using SDK"""
                with LangCache(
                    server_url=LANGCACHE_API_URL,
                    cache_id=LANGCACHE_CACHE_ID,
                    api_key=LANGCACHE_API_KEY
                ) as lang_cache:
                    # Convert response dict to JSON string for storage
                    response_str = json.dumps(response)

                    # SDK set() takes prompt and response
                    # ttlMillis is optional (None = no expiration)
                    ttl_ms = REDIS_CACHE_TTL * 1000 if REDIS_CACHE_TTL > 0 else None
                    result = lang_cache.set(
                        prompt=query,
                        response=response_str,
                        ttl_millis=ttl_ms
                    )
                    return result

            # Run SDK call in thread pool
            await asyncio.to_thread(_set_sync)
            print(f"[CACHE] Cached in LangCache SDK")

        except Exception as e:
            print(f"[CACHE] LangCache SDK caching error: {e}")

    async def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding for semantic matching"""
        try:
            response = await self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"[CACHE] Embedding generation error: {e}")
            raise

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        import math

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    async def _get_from_diy_cache(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Get cached response using DIY semantic matching.

        Process:
        1. Generate embedding for query
        2. Scan recent cache entries (last 1000)
        3. Calculate similarity with each
        4. Return best match if similarity >= threshold
        """
        try:
            # Generate embedding for query
            query_embedding = await self._get_embedding(query)

            # Get cache keys (use SCAN for production, KEYS for simplicity in dev)
            # Format: cache:llm:<query_hash>
            pattern = "cache:llm:*"
            keys = []

            # Use SCAN cursor to avoid blocking (production-safe)
            cursor = 0
            scan_count = 0
            while True:
                cursor, batch = await self.redis_client.scan(
                    cursor=cursor,
                    match=pattern,
                    count=100
                )
                keys.extend(batch)
                scan_count += 1

                if cursor == 0 or scan_count > 10:  # Limit to 1000 keys
                    break

            if not keys:
                return None

            # Find best matching cache entry
            best_match = None
            best_similarity = 0.0

            for key in keys:
                try:
                    # Get cached data
                    cached_json = await self.redis_client.get(key)
                    if not cached_json:
                        continue

                    cached_data = json.loads(cached_json)
                    cached_embedding = cached_data.get("embedding")

                    if not cached_embedding:
                        continue

                    # Calculate similarity
                    similarity = self._cosine_similarity(query_embedding, cached_embedding)

                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = cached_data

                except Exception as e:
                    # Skip invalid cache entries
                    continue

            # Return if similarity meets threshold
            if best_match and best_similarity >= CACHE_SIMILARITY_THRESHOLD:
                best_match["_similarity"] = round(best_similarity, 4)
                best_match["_cached_query"] = best_match.get("query")
                return best_match

            return None

        except Exception as e:
            print(f"[CACHE] DIY cache retrieval error: {e}")
            return None

    async def _cache_in_diy(self, query: str, response: Dict[str, Any]):
        """
        Cache response using DIY approach with semantic matching.

        Stores:
        - query: Original query
        - response: LLM response
        - embedding: Semantic embedding for similarity matching
        - timestamp: Cache creation time
        """
        try:
            # Generate embedding
            embedding = await self._get_embedding(query)

            # Create cache entry
            cache_data = {
                "query": query,
                "response": response,
                "embedding": embedding,
                "timestamp": datetime.now().isoformat(),
                "ttl": REDIS_CACHE_TTL
            }

            # Generate cache key (hash of query for uniqueness)
            query_hash = hashlib.sha256(query.encode()).hexdigest()[:16]
            cache_key = f"cache:llm:{query_hash}"

            # Store in Redis with TTL
            await self.redis_client.setex(
                cache_key,
                REDIS_CACHE_TTL,
                json.dumps(cache_data)
            )

            print(f"[CACHE] Cached in DIY Redis (key: {cache_key}, ttl: {REDIS_CACHE_TTL}s)")

        except Exception as e:
            print(f"[CACHE] DIY caching error: {e}")

    async def clear_cache(self):
        """Clear all cached entries"""
        if not self._initialized:
            await self.initialize()

        if self.redis_client:
            try:
                # Delete all cache keys
                pattern = "cache:llm:*"
                cursor = 0
                deleted = 0

                while True:
                    cursor, keys = await self.redis_client.scan(
                        cursor=cursor,
                        match=pattern,
                        count=100
                    )

                    if keys:
                        await self.redis_client.delete(*keys)
                        deleted += len(keys)

                    if cursor == 0:
                        break

                print(f"[CACHE] Cleared {deleted} cache entries")
                return deleted

            except Exception as e:
                print(f"[CACHE] Clear cache error: {e}")
                return 0

        return 0

    async def close(self):
        """Close connections"""
        if self.redis_client:
            await self.redis_client.close()
        print("[CACHE] Connections closed")


# Global cache instance (singleton pattern)
_cache_instance: Optional[CacheLayer] = None


def get_cache() -> CacheLayer:
    """Get or create global cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheLayer()
    return _cache_instance
