from django.core.exceptions import PermissionDenied


def _crud(prefijo, modelo):
    return {
        f'{prefijo}_lista': f'inventario.view_{modelo}',
        f'{prefijo}_detalle': f'inventario.view_{modelo}',
        f'{prefijo}_crear': f'inventario.add_{modelo}',
        f'{prefijo}_editar': f'inventario.change_{modelo}',
        f'{prefijo}_accion': f'inventario.change_{modelo}',
        f'{prefijo}_cancelar': f'inventario.change_{modelo}',
    }


# nombre de la ruta -> permiso que se exige
PERMISOS = {}
for _prefijo, _modelo in [
    ('producto', 'producto'), ('bodega', 'bodega'), ('categoria', 'categoria'),
    ('proveedor', 'proveedor'), ('cliente', 'cliente'),
    ('compra', 'ordencompra'), ('venta', 'ordenventa'),
]:
    PERMISOS.update(_crud(_prefijo, _modelo))

PERMISOS.update({
    'movimiento_lista': 'inventario.view_movimiento',
    'movimiento_crear': 'inventario.add_movimiento',
    'movimiento_traslado': 'inventario.add_movimiento',
    'escanear': 'inventario.view_producto',
    'escaner_buscar': 'inventario.view_producto',
    'escaner_movimiento': 'inventario.add_movimiento',
    'reportes': 'inventario.ver_reportes',
    'reporte_exportar': 'inventario.ver_reportes',
    'usuario_lista': 'auth.view_user',
    'usuario_crear': 'auth.add_user',
    'usuario_editar': 'auth.change_user',
    'rol_lista': 'auth.view_group',
    'rol_editar': 'auth.change_group',
})


class PermisosMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        ruta = request.resolver_match.url_name if request.resolver_match else None
        permiso = PERMISOS.get(ruta)
        if permiso and request.user.is_authenticated and not request.user.has_perm(permiso):
            raise PermissionDenied