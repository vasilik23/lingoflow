"""Prevent browser and shared caches from retaining authentication forms."""


class AuthFormCacheMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path_info.rstrip("/") in {"/login", "/register"}:
            response["Cache-Control"] = "private, no-store"
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"
        return response
