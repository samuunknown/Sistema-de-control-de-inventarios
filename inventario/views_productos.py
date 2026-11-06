from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProductoCrearForm, ProductoForm
from .models import Bodega, Categoria, Movimiento, Producto
from .services import aplicar_movimiento


@login_required
def producto_lista(request):
    q = request.GET.get('q', '').strip()
    categoria = request.GET.get('categoria', '')
    bodega = request.GET.get('bodega', '')
    estado = request.GET.get('estado', '')

    productos = Producto.objects.select_related('categoria').prefetch_related('stocks__bodega')

    if estado == 'inactivos':
        productos = productos.filter(activo=False)
    else:
        productos = productos.filter(activo=True)
        if estado == 'bajo':
            productos = productos.filter(stock_actual__lte=F('stock_minimo'))
        elif estado == 'agotado':
            productos = productos.filter(stock_actual=0)

    if q:
        productos = productos.filter(Q(nombre__icontains=q) | Q(codigo_barras__icontains=q))
    if categoria.isdigit():
        productos = productos.filter(categoria_id=categoria)

    # Con una bodega elegida se muestra el stock de esa bodega; si no, el total
    if bodega.isdigit():
        productos = productos.annotate(stock_mostrado=Coalesce(
            Sum('stocks__cantidad', filter=Q(stocks__bodega_id=bodega)), Value(0)))
    else:
        productos = productos.annotate(stock_mostrado=F('stock_actual'))

    page = Paginator(productos, 15).get_page(request.GET.get('page'))

    params = request.GET.copy()
    params.pop('page', None)

    return render(request, 'productos/lista.html', {
        'page': page,
        'q': q, 'categoria': categoria, 'bodega': bodega, 'estado': estado,
        'categorias': Categoria.objects.all(),
        'bodegas': Bodega.objects.filter(activa=True),
        'querystring': params.urlencode(),
    })


@login_required
def producto_crear(request):
    form = ProductoCrearForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            producto = form.save()
            cantidad = form.cleaned_data.get('stock_inicial') or 0
            if cantidad > 0:
                aplicar_movimiento(Movimiento(
                    producto=producto, bodega=form.cleaned_data['bodega'],
                    tipo=Movimiento.Tipo.ENTRADA, cantidad=cantidad,
                    motivo='Stock inicial', usuario=request.user,
                ))
        messages.success(request, f'Producto «{producto.nombre}» creado.')
        return redirect('producto_lista')
    return render(request, 'productos/form.html', {'form': form, 'titulo': 'Nuevo producto'})


@login_required
def producto_editar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    form = ProductoForm(request.POST or None, instance=producto)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Producto «{producto.nombre}» actualizado.')
        return redirect('producto_lista')
    return render(request, 'productos/form.html', {
        'form': form,
        'producto': producto,
        'stocks': producto.stocks.select_related('bodega'),
        'titulo': f'Editar {producto.nombre}',
    })