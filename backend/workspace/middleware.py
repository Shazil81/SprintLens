"""Private API responses, request correlation and deliberately minimal structured logs."""
import json
import logging
import time
import uuid
from django.utils.cache import patch_vary_headers

logger = logging.getLogger('sprintlens.api')


class ApiLogFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({name:getattr(record,name,None) for name in ['request_id','method','route','status','duration_ms']})


class ApiResponseMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith('/api/'):
            return self.get_response(request)
        request.request_id = str(uuid.uuid4())
        started = time.monotonic()
        response = self.get_response(request)
        response['X-Request-ID'] = request.request_id
        response['Cache-Control'] = 'private, no-store, max-age=0'
        response['CDN-Cache-Control'] = 'no-store'
        response['Vercel-CDN-Cache-Control'] = 'no-store'
        patch_vary_headers(response, ['Cookie','Origin'])
        route = getattr(getattr(request,'resolver_match',None),'route','unmatched')
        logger.info('api.response',extra={'request_id':request.request_id,'method':request.method,
            'route':route,'status':response.status_code,'duration_ms':round((time.monotonic()-started)*1000,2)})
        return response
