from django.apps import AppConfig


class LavourainteligenteConfig(AppConfig):
    name = 'lavouraInteligente'

    def ready(self):
        from . import signals  # noqa: F401
