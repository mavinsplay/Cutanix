import os

from django.core.wsgi import get_wsgi_application

__all__ = ["application"]

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", "cutanix.settings"
)

application = get_wsgi_application()
