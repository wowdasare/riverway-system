from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Reset admin superuser credentials'

    def handle(self, *args, **options):
        try:
            # Delete existing admin if exists
            if User.objects.filter(username='admin').exists():
                User.objects.filter(username='admin').delete()
                self.stdout.write('Existing admin user deleted.')
            
            # Create new admin user
            User.objects.create_superuser('admin', 'info.riverwayco@gmail.com', 'admin123')
            self.stdout.write(
                self.style.SUCCESS('✅ Admin user created successfully!')
            )
            self.stdout.write('🔐 Login Credentials:')
            self.stdout.write('   Username: admin')
            self.stdout.write('   Password: admin123')
            self.stdout.write('🌐 Access URLs:')
            self.stdout.write('   Admin Dashboard: http://localhost:8000/dashboard/')
            self.stdout.write('   Main Store: http://localhost:8000/')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating admin user: {str(e)}')
            )