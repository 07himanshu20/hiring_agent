import time
from django.core.cache import cache
from django.http import JsonResponse
from django.conf import settings

class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limit_requests = 100  # requests
        self.rate_limit_window = 3600  # 1 hour in seconds

    def __call__(self, request):
        # Skip rate limiting for admin, static files, and critical proctoring endpoints
        if (request.path.startswith('/admin/') or 
            request.path.startswith('/static/') or
            '/check-screen-sharing/' in request.path or
            '/process-frame/' in request.path):
            return self.get_response(request)
        
        # Get client IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            client_ip = x_forwarded_for.split(',')[0]
        else:
            client_ip = request.META.get('REMOTE_ADDR')
        
        # Rate limiting key
        cache_key = f"rate_limit_{client_ip}"
        
        # Get current request count
        requests = cache.get(cache_key, [])
        current_time = time.time()
        
        # Remove requests outside the time window
        requests = [req_time for req_time in requests if current_time - req_time < self.rate_limit_window]
        
        # Check if rate limit exceeded
        if len(requests) >= self.rate_limit_requests:
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'message': f'Maximum {self.rate_limit_requests} requests per hour allowed'
            }, status=429)
        
        # Add current request
        requests.append(current_time)
        cache.set(cache_key, requests, self.rate_limit_window)
        
        # Add rate limit headers
        response = self.get_response(request)
        response['X-RateLimit-Limit'] = self.rate_limit_requests
        response['X-RateLimit-Remaining'] = self.rate_limit_requests - len(requests)
        
        return response