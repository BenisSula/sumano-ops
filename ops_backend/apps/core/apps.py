from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = 'Core'

    def ready(self):
        """Import signal handlers when the app is ready."""
        try:
            import apps.core.signals  # noqa F401
        except ImportError:
            pass
