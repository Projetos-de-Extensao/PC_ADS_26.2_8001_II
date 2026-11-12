import os

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Deploy: collectstatic, migrate, superusuário via variáveis de ambiente e seed opcional."

    def handle(self, *args, **options):
        call_command("collectstatic", interactive=False, verbosity=0)
        call_command("migrate", interactive=False)
        call_command("configurar_perfis", verbosity=0)

        usuario = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        senha = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        if usuario and senha:
            User = get_user_model()
            if not User.objects.filter(username=usuario).exists():
                User.objects.create_superuser(usuario, os.environ.get("DJANGO_SUPERUSER_EMAIL", ""), senha)
                self.stdout.write(f"Superusuário '{usuario}' criado.")

        if os.environ.get("SEED", "0") == "1":
            call_command("seed")
