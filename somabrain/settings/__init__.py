"""Environment-based settings loader."""
import os

ENVIRONMENT = os.environ.get('DJANGO_ENV', 'development')

if ENVIRONMENT == 'production':
    from .production import *  # noqa
elif ENVIRONMENT == 'staging':
    from .staging import *  # noqa
else:
    from .development import *  # noqa

__all__ = ['ENVIRONMENT']
