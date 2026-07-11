from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

__all__ = []


@require_GET
@csrf_exempt
def serve_index(request):
    return render(request, "cutanix/base.html")
