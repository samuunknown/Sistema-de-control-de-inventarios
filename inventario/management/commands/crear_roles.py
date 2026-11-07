from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


def perms(app, *modelos, acciones=('view',)):
    return [(app, f'{accion}_{modelo}') for modelo in modelos for accion in acciones]


ROLES = {
    'Administrador': (
        perms('inventario', 'producto', 'movimiento', 'bodega', 'categoria', 'proveedor',
              'cliente', 'ordencompra', 'ordenventa', acciones=('view', 'add', 'change'))
        + [('inventario', 'ver_reportes')]
        + perms('auth', 'user', acciones=('view', 'add', 'change'))
    ),
    'Bodeguero': (
        perms('inventario', 'producto', 'categoria', 'proveedor', 'ordencompra',
              acciones=('view', 'add', 'change'))
        + perms('inventario', 'movimiento', acciones=('view', 'add'))
        + perms('inventario', 'bodega', 'cliente', 'ordenventa', acciones=('view',))
        + [('inventario', 'ver_reportes')]
    ),
    'Vendedor': (
        perms('inventario', 'producto', 'bodega', 'movimiento', acciones=('view',))
        + perms('inventario', 'cliente', 'ordenventa', acciones=('view', 'add', 'change'))
    ),
}


class Command(BaseCommand):
    help = 'Crea o actualiza los roles (grupos) y sus permisos.'

    def handle(self, *args, **options):
        for nombre, lista in ROLES.items():
            grupo, _ = Group.objects.get_or_create(name=nombre)
            permisos = [
                Permission.objects.get(content_type__app_label=app, codename=codigo)
                for app, codigo in lista
            ]
            grupo.permissions.set(permisos)
            self.stdout.write(self.style.SUCCESS(f'{nombre}: {len(permisos)} permisos'))