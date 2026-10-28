from django.contrib.auth.decorators import login_required
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.utils import timezone

from .models import ItemVenta, Movimiento, OrdenVenta, Producto
from datetime import date, timedelta

from django.http import Http404, HttpResponse

from . import reportes
from .exportar import a_excel, a_pdf

SUBTOTAL = ExpressionWrapper(
    F('cantidad') * F('precio_unitario'),
    output_field=DecimalField(max_digits=14, decimal_places=0),
)


@login_required
def dashboard(request):
    ahora = timezone.localtime()
    inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    desde = (ahora - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)

    productos = Producto.objects.filter(activo=True)
    ventas = ItemVenta.objects.filter(orden__estado=OrdenVenta.Estado.COMPLETADA)

    valor_inventario = productos.aggregate(
        total=Sum(ExpressionWrapper(
            F('stock_actual') * F('precio_compra'),
            output_field=DecimalField(max_digits=16, decimal_places=0),
        ))
    )['total'] or 0

    ventas_mes = ventas.filter(orden__fecha__gte=inicio_mes).aggregate(total=Sum(SUBTOTAL))['total'] or 0

    stock_bajo = productos.filter(stock_actual__lte=F('stock_minimo')).order_by('stock_actual')

    # Ventas por día (últimos 7 días, rellenando los días sin ventas con 0)
    por_dia = (
        ventas.filter(orden__fecha__gte=desde)
        .annotate(dia=TruncDate('orden__fecha'))
        .values('dia')
        .annotate(total=Sum(SUBTOTAL))
        .order_by('dia')
    )
    datos = {fila['dia']: int(fila['total']) for fila in por_dia}
    dias = [desde.date() + timedelta(days=i) for i in range(7)]
    grafica_ventas = {
        'labels': [d.strftime('%d/%m') for d in dias],
        'valores': [datos.get(d, 0) for d in dias],
    }

    # Top 5 productos más vendidos (por unidades)
    top = (
        ventas.values('producto__nombre')
        .annotate(unidades=Sum('cantidad'))
        .order_by('-unidades')[:5]
    )
    grafica_top = {
        'labels': [fila['producto__nombre'] for fila in top],
        'valores': [fila['unidades'] for fila in top],
    }

    contexto = {
        'total_productos': productos.count(),
        'valor_inventario': valor_inventario,
        'ventas_mes': ventas_mes,
        'stock_bajo_count': stock_bajo.count(),
        'stock_bajo': stock_bajo[:5],
        'ultimos_movimientos': Movimiento.objects.select_related('producto', 'usuario')[:8],
        'grafica_ventas': grafica_ventas,
        'grafica_top': grafica_top,
    }
    return render(request, 'dashboard.html', contexto)

REPORTES = {
    'inventario': reportes.inventario,
    'stock-bajo': reportes.stock_bajo,
    'ventas': reportes.ventas,
}


@login_required
def reportes_home(request):
    hoy = timezone.localdate()
    return render(request, 'reportes.html', {
        'desde': hoy.replace(day=1).isoformat(),
        'hasta': hoy.isoformat(),
    })


@login_required
def reporte_exportar(request, tipo, formato):
    if tipo not in REPORTES or formato not in ('excel', 'pdf'):
        raise Http404

    hoy = timezone.localdate()
    try:
        desde = date.fromisoformat(request.GET.get('desde', ''))
        hasta = date.fromisoformat(request.GET.get('hasta', ''))
    except ValueError:
        desde, hasta = hoy.replace(day=1), hoy

    titulo, encabezados, filas = REPORTES[tipo](desde, hasta)

    if formato == 'excel':
        contenido = a_excel(titulo, encabezados, filas)
        tipo_mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        extension = 'xlsx'
    else:
        contenido = a_pdf(titulo, encabezados, filas)
        tipo_mime = 'application/pdf'
        extension = 'pdf'

    respuesta = HttpResponse(contenido, content_type=tipo_mime)
    respuesta['Content-Disposition'] = f'attachment; filename="{tipo}-{hoy:%Y%m%d}.{extension}"'
    return respuesta
