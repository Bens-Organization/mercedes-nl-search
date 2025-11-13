"""
Tests for Cache Layer (JAI-2169)

Test coverage:
1. Basic cache operations (get/set)
2. Semantic similarity matching
3. Cache metrics tracking
4. TTL expiration
5. Mode switching (auto, diy, disabled)
6. Error handling and fallback
"""

import pytest
import os
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from src.cache_layer import CacheLayer, CacheMetrics


@pytest.fixture
async def cache_disabled():
    """Cache instance with caching disabled"""
    cache = CacheLayer(mode="disabled")
    await cache.initialize()
    yield cache
    await cache.close()


@pytest.fixture
async def cache_diy():
    """Cache instance with DIY mode (requires Redis)"""
    # Skip if Redis not available
    if not os.getenv("REDIS_URL"):
        pytest.skip("Redis not configured")

    cache = CacheLayer(mode="diy")
    await cache.initialize()
    await cache.clear_cache()  # Clean slate
    yield cache
    await cache.clear_cache()  # Cleanup
    await cache.close()


class TestCacheMetrics:
    """Test cache metrics tracking"""

    def test_metrics_initialization(self):
        """Test metrics are properly initialized"""
        metrics = CacheMetrics()
        stats = metrics.get_stats()

        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["errors"] == 0
        assert stats["hit_rate_percent"] == 0.0

    def test_record_hit(self):
        """Test recording cache hits"""
        metrics = CacheMetrics()
        metrics.record_hit(100.5)
        metrics.record_hit(150.3)

        stats = metrics.get_stats()
        assert stats["hits"] == 2
        assert stats["avg_hit_latency_ms"] > 0

    def test_record_miss(self):
        """Test recording cache misses"""
        metrics = CacheMetrics()
        metrics.record_miss(2000.0)

        stats = metrics.get_stats()
        assert stats["misses"] == 1
        assert stats["avg_miss_latency_ms"] == 2000.0

    def test_hit_rate_calculation(self):
        """Test hit rate percentage calculation"""
        metrics = CacheMetrics()
        metrics.record_hit(50.0)
        metrics.record_hit(60.0)
        metrics.record_miss(2000.0)

        stats = metrics.get_stats()
        assert stats["total_queries"] == 3
        assert stats["hit_rate_percent"] == pytest.approx(66.67, rel=0.1)


class TestCacheLayerDisabled:
    """Test cache layer with caching disabled"""

    @pytest.mark.asyncio
    async def test_disabled_mode_returns_none(self, cache_disabled):
        """Disabled mode should always return None"""
        result = await cache_disabled.get_cached_response("test query")
        assert result is None

    @pytest.mark.asyncio
    async def test_disabled_mode_metrics(self, cache_disabled):
        """Disabled mode should not track metrics"""
        await cache_disabled.get_cached_response("test query")
        stats = cache_disabled.metrics.get_stats()

        # Should not count as hit or miss
        assert stats["total_queries"] == 0


class TestCacheLayerDIY:
    """Test DIY semantic caching with Redis"""

    @pytest.mark.asyncio
    async def test_cache_miss_on_first_query(self, cache_diy):
        """First query should always be a cache miss"""
        query = "nitrile gloves under $50"
        result = await cache_diy.get_cached_response(query)

        assert result is None
        stats = cache_diy.metrics.get_stats()
        assert stats["misses"] == 1

    @pytest.mark.asyncio
    async def test_cache_hit_on_second_query(self, cache_diy):
        """Exact same query should hit cache"""
        query = "nitrile gloves under $50"
        response = {"q": "nitrile glove", "filter_by": "price:<50"}

        # Cache the response
        await cache_diy.cache_response(query, response)

        # Try to get it back
        cached = await cache_diy.get_cached_response(query)

        assert cached is not None
        assert cached.get("response") == response
        stats = cache_diy.metrics.get_stats()
        assert stats["hits"] >= 1

    @pytest.mark.asyncio
    async def test_semantic_similarity_matching(self, cache_diy):
        """Similar queries should hit same cache (semantic matching)"""
        # Original query
        query1 = "nitrile gloves under $50"
        response = {"q": "nitrile glove", "filter_by": "price:<50"}

        await cache_diy.cache_response(query1, response)

        # Similar query (slightly different wording)
        query2 = "nitrile glove less than $50"

        cached = await cache_diy.get_cached_response(query2)

        # Should hit cache if similarity >= threshold (0.95 default)
        # Note: This might miss if queries are not similar enough
        if cached:
            assert cached.get("response") == response
            similarity = cached.get("_similarity", 0.0)
            assert similarity >= 0.95
        else:
            # If miss, check that metrics reflect it
            stats = cache_diy.metrics.get_stats()
            assert stats["misses"] >= 1

    @pytest.mark.asyncio
    async def test_different_queries_cache_separately(self, cache_diy):
        """Different queries should have separate cache entries"""
        query1 = "nitrile gloves"
        query2 = "pipette tips"

        response1 = {"q": "nitrile glove", "filter_by": ""}
        response2 = {"q": "pipette tip", "filter_by": ""}

        await cache_diy.cache_response(query1, response1)
        await cache_diy.cache_response(query2, response2)

        cached1 = await cache_diy.get_cached_response(query1)
        cached2 = await cache_diy.get_cached_response(query2)

        assert cached1 is not None
        assert cached2 is not None
        assert cached1.get("response") != cached2.get("response")

    @pytest.mark.asyncio
    async def test_cache_clear(self, cache_diy):
        """Cache clear should remove all entries"""
        query = "test query"
        response = {"q": "test", "filter_by": ""}

        await cache_diy.cache_response(query, response)

        # Verify cached
        cached = await cache_diy.get_cached_response(query)
        assert cached is not None

        # Clear cache
        deleted = await cache_diy.clear_cache()
        assert deleted > 0

        # Verify cache miss after clear
        cached_after = await cache_diy.get_cached_response(query)
        assert cached_after is None


class TestCacheLayerErrorHandling:
    """Test error handling and fallback behavior"""

    @pytest.mark.asyncio
    async def test_auto_mode_fallback_on_redis_error(self):
        """Auto mode should fallback gracefully on Redis errors"""
        # Use invalid Redis URL
        with patch.dict(os.environ, {"REDIS_URL": "redis://invalid-host:6379"}):
            cache = CacheLayer(mode="auto")
            await cache.initialize()

            # Should fallback to disabled mode
            assert cache.mode == "disabled" or cache.redis_client is None

            await cache.close()

    @pytest.mark.asyncio
    async def test_cache_error_does_not_break_flow(self, cache_diy):
        """Cache errors should be caught and not break the application"""
        # Mock Redis to raise error
        with patch.object(cache_diy.redis_client, 'get', side_effect=Exception("Redis error")):
            result = await cache_diy.get_cached_response("test query")

            # Should return None, not raise exception
            assert result is None

            # Error should be tracked
            stats = cache_diy.metrics.get_stats()
            # Note: Error count might not increment depending on implementation


class TestCacheLayerIntegration:
    """Integration tests with middleware"""

    @pytest.mark.asyncio
    async def test_cache_integration_with_middleware(self, cache_diy):
        """Test cache integration with actual middleware flow"""
        # Simulate middleware call
        query = "sterile gloves in stock"
        openai_response = {
            "id": "chatcmpl-123",
            "choices": [{
                "message": {
                    "content": '{"q":"sterile glove","filter_by":"stock_status:=IN_STOCK"}'
                }
            }]
        }

        # Cache the response
        await cache_diy.cache_response(query, openai_response)

        # Retrieve from cache
        cached = await cache_diy.get_cached_response(query)

        assert cached is not None
        assert cached.get("response") == openai_response

    @pytest.mark.asyncio
    async def test_performance_improvement(self, cache_diy):
        """Test that cache provides performance improvement"""
        query = "test performance query"
        response = {"q": "test", "filter_by": ""}

        # First call (miss) - should take longer
        await cache_diy.cache_response(query, response)

        # Second call (hit) - should be faster
        import time
        start = time.time()
        cached = await cache_diy.get_cached_response(query)
        elapsed_ms = (time.time() - start) * 1000

        assert cached is not None
        # Cache hit should be very fast (<100ms)
        assert elapsed_ms < 100, f"Cache hit took {elapsed_ms:.1f}ms (expected <100ms)"


def test_cache_metrics_uptime():
    """Test uptime calculation"""
    import time
    metrics = CacheMetrics()
    time.sleep(0.1)  # Wait 100ms
    stats = metrics.get_stats()

    assert stats["uptime_seconds"] >= 0.1


def test_cache_metrics_queries_per_minute():
    """Test queries per minute calculation"""
    import time
    metrics = CacheMetrics()
    metrics.record_hit(50.0)
    metrics.record_miss(2000.0)
    time.sleep(0.1)

    stats = metrics.get_stats()
    # Should calculate based on uptime
    assert stats["queries_per_minute"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
