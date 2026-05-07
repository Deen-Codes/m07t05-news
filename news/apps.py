"""App config for the news app."""

from django.apps import AppConfig


class NewsConfig(AppConfig):
    """Loads signal handlers in ready()."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'news'
    verbose_name = 'News'

    def ready(self):
        """Import signals so the receivers register."""
        from news import signals  # noqa: F401
