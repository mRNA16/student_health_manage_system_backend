from django.core.cache import cache

def invalidate_health_cache(user_id):
    """Invalidate health summary and analysis cache for a user."""
    # Invalidate health summary for different time ranges
    for range_str in ['7d', '30d', '90d']:
        cache.delete(f'health_summary_{user_id}_{range_str}')
    
    # Invalidate analysis results if we decide to cache them later
    # cache.delete(f'analysis_results_{user_id}')

def invalidate_friend_cache(user_id):
    """Invalidate friend-related cache for a user."""
    cache.delete(f'friend_list_{user_id}')
    cache.delete(f'friend_requests_received_{user_id}')
    cache.delete(f'friend_requests_sent_{user_id}')
