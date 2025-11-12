from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.cache import never_cache


@require_GET
@never_cache
def health_check(request):
    """
    Health check endpoint for load balancers and monitoring systems.
    Returns JSON response with application status.
    """
    return JsonResponse({
        'status': 'healthy',
        'timestamp': '2025-01-01T00:00:00Z',  # Should be dynamic in real implementation
        'version': '1.0.0'
    })