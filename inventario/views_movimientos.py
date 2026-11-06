from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import redirect, render

from .forms import MovimientoForm, TrasladoForm
from .models import Bodega, Movimiento
from .services import aplicar_movimiento, trasladar


def _fecha(texto):
    try:
        return date.fromisoformat(texto)
    except ValueError:
        return None


@login_required
def movimiento_lista(request):
    q = request.GET.get('q', '').strip()
    tipo = request.GET.get('tipo', '')
    bodega = request.GET.get('bodega', '')
    desde = request.GET.get('desde', '')
    hasta = request.GET.get('hasta', '')

    movimientos = Movimiento.objects.select_related('producto', 'bodega', 'usuario')

    if q:
        movimientos = movimientos.filter(
            Q(producto__nombre__icontains=q) | Q(producto__codigo_barras__icontains=q) | Q(motivo__icontains=q)
        )
    if tipo in Movimiento.Tipo.values:
        movimientos = movimientos.filter(tipo=tipo)
    if bodega.isdigit():
        movimientos = movimientos.filter(bodega_id=bodega)
    if _fecha(desde):
        movimientos = movimientos.filter(fecha__date__gte=_fecha(desde))
    if _fecha(hasta):
        movimientos = movimientos.filter(fecha__date__lte=_fecha(hasta))

    page = Paginator(movimientos, 20).get_page(request.GET.get('page'))

    params = request.GET.copy()
    params.pop('page', None)

    return render(request, 'movimientos/lista.html', {
        'page': page,
        'q': q, 'tipo': tipo, 'bodega': bodega, 'desde': desde, 'hasta': hasta,
        'tipos': Movimiento.Tipo.choices,
        'bodegas': Bodega.objects.filter(activa=True),
        'querystring': params.urlencode(),
    })


@login_required
def movimiento_crear(request):
    form = MovimientoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        mov = form.save(commit=False)
        mov.usuario = request.user
        try:
            aplicar_movimiento(mov)
        except ValidationError as e:
            form.add_error(None, e.message)
        else:
            messages.success(
                request,
                f'Movimiento registrado: {mov.get_tipo_display()} · {mov.producto} · {mov.cantidad} en {mov.bodega}.',
            )
            return redirect('movimiento_lista')
    return render(request, 'movimientos/form.html', {
        'form': form, 'titulo': 'Nuevo movimiento', 'es_movimiento': True,
    })


@login_required
def movimiento_traslado(request):
    form = TrasladoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        try:
            trasladar(d['producto'], d['origen'], d['destino'], d['cantidad'], request.user, d['motivo'])
        except ValidationError as e:
            form.add_error(None, e.message)
        else:
            messages.success(
                request,
                f'Traslado realizado: {d["cantidad"]} × {d["producto"]} de {d["origen"]} a {d["destino"]}.',
            )
            return redirect('movimiento_lista')
    return render(request, 'movimientos/form.html', {'form': form, 'titulo': 'Traslado entre bodegas'})