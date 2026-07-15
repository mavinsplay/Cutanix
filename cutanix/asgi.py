import os

import django
from django.core.asgi import get_asgi_application

__all__ = ["application"]

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cutanix.settings")
django.setup()

application = get_asgi_application()
