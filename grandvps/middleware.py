import time
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    """Middleware to log request details for monitoring"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Log request start
        start_time = time.time()
        request.start_time = start_time

        # Get response
        response = self.get_response(request)

        # Calculate duration
        duration = time.time() - start_time

        # Log request details
        user = getattr(request, 'user', None)
        user_id = user.id if user and user.is_authenticated else 'anonymous'

        logger.info(
            f'Request: {request.method} {request.path} '
            f'User: {user_id} '
            f'Status: {response.status_code} '
            f'Duration: {duration:.3f}s '
            f'IP: {self.get_client_ip(request)} '
            f'User-Agent: {request.META.get("HTTP_USER_AGENT", "")[:100]}'
        )

        # Add performance header
        response['X-Response-Time'] = f'{duration:.3f}s'

        return response

    def get_client_ip(self, request):
        """Get the client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class HealthCheckMiddleware:
    """Middleware to handle health check requests"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == '/health/':
            from django.http import JsonResponse
            import psutil
            import os

            # Basic health checks
            health_data = {
                'status': 'healthy',
                'timestamp': time.time(),
                'version': getattr(settings, 'VERSION', '1.0.0'),
                'environment': getattr(settings, 'ENVIRONMENT', 'production'),
                'checks': {
                    'database': self.check_database(),
                    'redis': self.check_redis(),
                    'disk_space': self.check_disk_space(),
                    'memory': self.check_memory(),
                }
            }

            # Determine overall status
            if any(not check.get('status', True) for check in health_data['checks'].values()):
                health_data['status'] = 'unhealthy'

            status_code = 200 if health_data['status'] == 'healthy' else 503
            return JsonResponse(health_data, status=status_code)

        return self.get_response(request)

    def check_database(self):
        """Check database connectivity"""
        try:
            from django.db import connection
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            return {'status': True, 'message': 'Database connection OK'}
        except Exception as e:
            return {'status': False, 'message': f'Database error: {str(e)}'}

    def check_redis(self):
        """Check Redis connectivity"""
        try:
            from django.core.cache import cache
            cache.set('health_check', 'ok', 10)
            result = cache.get('health_check')
            if result == 'ok':
                return {'status': True, 'message': 'Redis connection OK'}
            else:
                return {'status': False, 'message': 'Redis cache not working'}
        except Exception as e:
            return {'status': False, 'message': f'Redis error: {str(e)}'}

    def check_disk_space(self):
        """Check disk space availability"""
        try:
            stat = os.statvfs('/')
            free_space_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
            if free_space_gb > 1:  # At least 1GB free
                return {'status': True, 'message': '.1f'}
            else:
                return {'status': False, 'message': '.1f'}
        except Exception as e:
            return {'status': False, 'message': f'Disk check error: {str(e)}'}

    def check_memory(self):
        """Check memory usage"""
        try:
            memory = psutil.virtual_memory()
            if memory.percent < 90:  # Less than 90% usage
                return {'status': True, 'message': '.1f'}
            else:
                return {'status': False, 'message': '.1f'}
        except Exception as e:
            return {'status': False, 'message': f'Memory check error: {str(e)}'}