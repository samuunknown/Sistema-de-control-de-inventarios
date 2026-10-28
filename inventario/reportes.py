from django.db.models import F
from django.utils import timezone

from .models import ItemVenta, OrdenVenta, Producto


def inventario(desde, hasta):
    productos = Producto.objects.filter(activo=True).select_related('categoria')
    encabezados = ['Código de barras', 'Producto', 'Categoría', 'Stock', 'Costo unit.', 'Valor']
    filas = [
        [p.codigo_barras or '', p.nombre, p.categoria.nombre, p.stock_actual,
         int(p.precio_compra), int(p.stock_actual * p.precio_compra)]
        for p in productos
    ]
    filas.append(['', 'TOTAL', '', sum(f[3] for f in filas), '', sum(f[5] for f in filas)])
    return 'Inventario valorizado', encabezados, filas


def stock_bajo(desde, hasta):
    productos = (Producto.objects.filter(activo=True, stock_actual__lte=F('stock_minimo'))
                 .select_related('categoria').order_by('stock_actual'))
    encabezados = ['Producto', 'Categoría', 'Stock', 'Mínimo', 'Diferencia']
    filas = [
        [p.nombre, p.categoria.nombre, p.stock_actual, p.stock_minimo, p.stock_minimo - p.stock_actual]
        for p in productos
    ]
    return 'Productos con stock bajo', encabezados, filas


def ventas(desde, hasta):
    items = (ItemVenta.objects
             .filter(orden__estado=OrdenVenta.Estado.COMPLETADA,
                     orden__fecha__date__gte=desde, orden__fecha__date__lte=hasta)
             .select_related('orden__cliente', 'producto')
             .order_by('orden__fecha'))
    encabezados = ['Fecha', 'Venta', 'Cliente', 'Producto', 'Cantidad', 'Precio unit.', 'Subtotal']
    filas = [
        [timezone.localtime(i.orden.fecha).strftime('%Y-%m-%d %H:%M'), f'#{i.orden_id}',
         str(i.orden.cliente or 'Mostrador'), i.producto.nombre, i.cantidad,
         int(i.precio_unitario), int(i.subtotal)]
        for i in items
    ]
    filas.append(['', '', '', 'TOTAL', sum(f[4] for f in filas), '', sum(f[6] for f in filas)])
    return f'Ventas del {desde:%d/%m/%Y} al {hasta:%d/%m/%Y}', encabezados, filas