import json
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from redis.exceptions import ConnectionError as RedisConnectionError


class TestCacheConnection(unittest.TestCase):
    def setUp(self):
        # Clear module cache so imports reload config
        if 'cache' in sys.modules:
            del sys.modules['cache']

    def tearDown(self):
        if 'cache' in sys.modules:
            del sys.modules['cache']

    @patch('redis.sentinel.Sentinel')
    @patch.dict('os.environ', {
        'REDIS_SENTINELS': 'sentinel-service:26379',
        'REDIS_PASSWORD': 'testpassword',
        'REDIS_MASTER_NAME': 'mymaster'
    })
    def test_sentinel_initialization(self, mock_sentinel):
        mock_sentinel_instance = MagicMock()
        mock_sentinel.return_value = mock_sentinel_instance
        
        import cache
        
        mock_sentinel.assert_called_once_with(
            [('sentinel-service', 26379)],
            socket_timeout=0.2,
            socket_connect_timeout=0.2,
            password='testpassword',
            sentinel_kwargs={'password': 'testpassword'}
        )
        
        mock_sentinel_instance.master_for.assert_called_once_with(
            'mymaster',
            socket_timeout=0.2,
            socket_connect_timeout=0.2,
            password='testpassword'
        )
        self.assertEqual(cache.redis_client, mock_sentinel_instance.master_for.return_value)

    @patch('redis.Redis')
    @patch.dict('os.environ', {
        'REDIS_HOST': 'localhost',
        'REDIS_PORT': '6379',
        'REDIS_PASSWORD': 'fallbackpassword'
    })
    def test_standalone_fallback(self, mock_redis):
        with patch.dict('os.environ', {'REDIS_SENTINELS': ''}):
            import cache
            mock_redis.assert_called_once_with(
                host='localhost',
                port=6379,
                password='fallbackpassword',
                socket_timeout=0.2,
                socket_connect_timeout=0.2,
            )
            self.assertEqual(cache.redis_client, mock_redis.return_value)


class TestCartCacheRoutes(unittest.IsolatedAsyncioTestCase):
    @patch('routes.cart.redis_client')
    @patch('routes.cart.carts_collection')
    async def test_load_items_cache_hit(self, mock_collection, mock_redis_client):
        # Mock Redis returning cached cart items
        mock_redis_client.get.return_value = b'[{"sku": "item1", "quantity": 2}]'
        
        from routes.cart import load_items
        result = await load_items("user_123")
        
        self.assertEqual(result, [{"sku": "item1", "quantity": 2}])
        mock_redis_client.get.assert_called_once_with("cart:user_123")
        mock_collection.find_one.assert_not_called()

    @patch('routes.cart.redis_client')
    @patch('routes.cart.carts_collection')
    async def test_load_items_cache_miss(self, mock_collection, mock_redis_client):
        # Cache miss (returns None)
        mock_redis_client.get.return_value = None
        # Database returns document
        mock_collection.find_one = AsyncMock(return_value={"user_id": "user_123", "items": [{"sku": "item2", "quantity": 1}]})
        
        from routes.cart import load_items
        result = await load_items("user_123")
        
        self.assertEqual(result, [{"sku": "item2", "quantity": 1}])
        mock_redis_client.get.assert_called_once_with("cart:user_123")
        mock_collection.find_one.assert_called_once_with({"user_id": "user_123"})
        mock_redis_client.set.assert_called_once_with("cart:user_123", json.dumps([{"sku": "item2", "quantity": 1}]), ex=86400)

    @patch('routes.cart.redis_client')
    @patch('routes.cart.carts_collection')
    async def test_load_items_falls_back_when_cache_is_unavailable(
        self, mock_collection, mock_redis_client
    ):
        mock_redis_client.get.side_effect = RedisConnectionError("Redis unavailable")
        mock_redis_client.set.side_effect = RedisConnectionError("Redis unavailable")
        items = [{"sku": "item4", "quantity": 3}]
        mock_collection.find_one = AsyncMock(
            return_value={"user_id": "user_123", "items": items}
        )

        from routes.cart import load_items

        result = await load_items("user_123")

        self.assertEqual(result, items)
        mock_collection.find_one.assert_awaited_once_with({"user_id": "user_123"})
        mock_redis_client.set.assert_called_once_with(
            "cart:user_123", json.dumps(items), ex=86400
        )

    @patch('routes.cart.redis_client')
    @patch('routes.cart.carts_collection')
    async def test_save_items(self, mock_collection, mock_redis_client):
        # Mock MongoDB update call
        mock_collection.update_one = AsyncMock()
        
        from routes.cart import save_items
        items = [{"sku": "item3", "quantity": 5}]
        await save_items("user_123", items)
        
        # Verify both Mongo and Redis are updated
        mock_collection.update_one.assert_called_once()
        mock_redis_client.set.assert_called_once_with("cart:user_123", json.dumps(items), ex=86400)
