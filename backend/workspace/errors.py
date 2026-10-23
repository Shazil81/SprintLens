"""JSON errors for production API paths that fail outside the REST framework views."""
from django.http import JsonResponse


def bad_request(request, exception):
    return JsonResponse({'detail':'Invalid request.'},status=400)


def forbidden(request, exception):
    return JsonResponse({'detail':'Access denied.'},status=403)


def not_found(request, exception):
    return JsonResponse({'detail':'Endpoint not found.'},status=404)


def server_error(request):
    return JsonResponse({'detail':'The server could not complete the request.'},status=500)
