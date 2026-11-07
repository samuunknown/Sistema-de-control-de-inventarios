from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, Permission
from django.db.models import Count, Value
from django.db.models.functions import Concat
from django.shortcuts import get_object_or_404, redirect, render

MODULOS = [
    ('Productos', 'inventario', 'producto'),
    ('Movimientos', 'inventario', 'movimiento'),
    ('Bodegas', 'inventario', 'bodega'),
    ('Categorías', 'inventario', 'categoria'),
    ('Proveedores', 'inventario', 'proveedor'),
    ('Clientes', 'inventario', 'cliente'),
    ('Órdenes de compra', 'inventario', 'ordencompra'),
    ('Órdenes de venta', 'inventario', 'ordenventa'),
    ('Usuarios', 'auth', 'user'),
]
ACCIONES = [('view', 'Ver'), ('add', 'Crear'), ('change', 'Editar')]
REPORTES = 'inventario.ver_reportes'

DESCRIPCIONES = {
    'Administrador': 'Acceso total, incluidos los usuarios y los reportes.',
    'Bodeguero': 'Maneja productos, compras, proveedores, movimientos y reportes.',
    'Vendedor': 'Consulta el inventario y gestiona clientes y ventas.',
}


@login_required
def rol_lista(request):
    roles = Group.objects.annotate(
        n_usuarios=Count('user', distinct=True),
        n_permisos=Count('permissions', distinct=True),
    ).order_by('name')
    return render(request, 'roles/lista.html', {
        'filas': [(rol, DESCRIPCIONES.get(rol.name, '')) for rol in roles],
    })


@login_required
def rol_editar(request, pk):
    grupo = get_object_or_404(Group, pk=pk)
    bloqueado = grupo.name == 'Administrador'

    if request.method == 'POST' and not bloqueado:
        validos = {f'{app}.{accion}_{modelo}' for _, app, modelo in MODULOS for accion, _ in ACCIONES}
        validos.add(REPORTES)
        elegidos = set(request.POST.getlist('permiso')) & validos
        permisos = (Permission.objects
                    .annotate(clave=Concat('content_type__app_label', Value('.'), 'codename'))
                    .filter(clave__in=elegidos))
        grupo.permissions.set(permisos)
        messages.success(request, f'Permisos del rol «{grupo.name}» actualizados.')
        return redirect('rol_lista')

    actuales = {
        f'{p.content_type.app_label}.{p.codename}'
        for p in grupo.permissions.select_related('content_type')
    }
    filas = []
    for nombre, app, modelo in MODULOS:
        celdas = []
        for accion, _ in ACCIONES:
            clave = f'{app}.{accion}_{modelo}'
            celdas.append({'clave': clave, 'marcado': clave in actuales})
        filas.append({'nombre': nombre, 'celdas': celdas})
    filas.append({
        'nombre': 'Reportes',
        'celdas': [{'clave': REPORTES, 'marcado': REPORTES in actuales}, None, None],
    })

    return render(request, 'roles/form.html', {
        'grupo': grupo,
        'bloqueado': bloqueado,
        'filas': filas,
        'etiquetas': [etiqueta for _, etiqueta in ACCIONES],
        'descripcion': DESCRIPCIONES.get(grupo.name, ''),
    })