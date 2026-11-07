import json
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .models import Bodega, Movimiento, Producto
from .services import aplicar_movimiento


def _datos_producto(producto):
    return {
        'id': producto.pk,
        'nombre': producto.nombre,
        'codigo': producto.codigo_barras,
        'categoria': producto.categoria.nombre,
        'precio_venta': int(producto.precio_venta),
        'stock_total': producto.stock_actual,
        'stock_minimo': producto.stock_minimo,
        'activo': producto.activo,
        'stocks': [
            {'bodega': s.bodega.nombre, 'cantidad': s.cantidad}
            for s in producto.stocks.select_related('bodega')
        ],
        'url_editar': reverse('producto_editar', args=[producto.pk]),
    }


@login_required
def escanear(request):
    return render(request, 'escaner/escanear.html', {
        'bodegas': Bodega.objects.filter(activa=True),
        'tipos': Movimiento.Tipo.choices,
    })


@login_required
def buscar_codigo(request):
    codigo = request.GET.get('codigo', '').strip()
    producto = None
    if codigo:
        producto = Producto.objects.select_related('categoria').filter(codigo_barras=codigo).first()
    if not producto:
        return JsonResponse({
            'encontrado': False,
            'codigo': codigo,
            'url_crear': reverse('producto_crear') + '?' + urlencode({'codigo': codigo}),
        })
    return JsonResponse({'encontrado': True, 'producto': _datos_producto(producto)})


@login_required
@require_POST
def movimiento_rapido(request):
    try:
        datos = json.loads(request.body)
        producto = Producto.objects.select_related('categoria').get(pk=datos['producto'])
        bodega = Bodega.objects.get(pk=datos['bodega'], activa=True)
        tipo = datos['tipo']
        cantidad = int(datos['cantidad'])
    except (ValueError, KeyError, TypeError, Producto.DoesNotExist, Bodega.DoesNotExist):
        return JsonResponse({'ok': False, 'error': 'Datos incompletos o inválidos.'}, status=400)

    if tipo not in Movimiento.Tipo.values:
        return JsonResponse({'ok': False, 'error': 'Tipo de movimiento inválido.'}, status=400)

    mov = Movimiento(producto=producto, bodega=bodega, tipo=tipo, cantidad=cantidad,
                     motivo='Registro por escáner', usuario=request.user)
    try:
        mov.full_clean(exclude=['usuario', 'stock_resultante'])  # valida cantidad y stock disponible
        aplicar_movimiento(mov)
    except ValidationError as e:
        return JsonResponse({'ok': False, 'error': ' '.join(e.messages)}, status=400)

    producto.refresh_from_db()
    return JsonResponse({'ok': True, 'producto': _datos_producto(producto)})