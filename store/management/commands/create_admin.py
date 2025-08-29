from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Create admin superuser'

    def handle(self, *args, **options):
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'info.riverwayco@gmail.com', 'admin123')
            self.stdout.write(
                self.style.SUCCESS('Admin user created successfully!')
            )
            self.stdout.write('Username: admin')
            self.stdout.write('Password: admin123')
        else:
            self.stdout.write(
                self.style.WARNING('Admin user already exists!')
            )