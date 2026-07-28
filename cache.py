import os
import redis
from redis.sentinel import Sentinel

# Configurable parameters
REDIS_SENTINELS = os.environ.get("REDIS_SENTINELS")  # e.g., "sentinel-0:26379,sentinel-1:26379"
REDIS_MASTER_NAME = os.environ.get("REDIS_MASTER_NAME", "mymaster")
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD")
REDIS_SOCKET_TIMEOUT = float(os.environ.get("REDIS_SOCKET_TIMEOUT", "0.2"))

redis_client = None

if REDIS_SENTINELS:
    # Build Sentinel list
    sentinel_hosts = []
    for s in REDIS_SENTINELS.split(","):
        s = s.strip()
        if not s:
            continue
        if ":" in s:
            host, port = s.split(":")
            sentinel_hosts.append((host, int(port)))
        else:
            sentinel_hosts.append((s, 26379))
            
    if sentinel_hosts:
        # Connect to Sentinel pool
        sentinel = Sentinel(
            sentinel_hosts, 
            socket_timeout=REDIS_SOCKET_TIMEOUT, 
            password=REDIS_PASSWORD
        )
        # Resolve the active master node dynamically
        redis_client = sentinel.master_for(
            REDIS_MASTER_NAME, 
            socket_timeout=REDIS_SOCKET_TIMEOUT, 
            password=REDIS_PASSWORD
        )
        
if redis_client is None:
    # Standalone fallback for local compose development
    redis_client = redis.Redis(
        host=os.environ.get("REDIS_HOST", "localhost"),
        port=int(os.environ.get("REDIS_PORT", 6379)),
        password=REDIS_PASSWORD,
        socket_timeout=REDIS_SOCKET_TIMEOUT
    )
