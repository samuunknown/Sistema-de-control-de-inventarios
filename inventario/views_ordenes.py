from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.forms import inlineformset_factory, modelform_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.views import View
from django.views.generic import DetailView, ListView

from .forms import EstiloBootstrap
from .models import Bodega, ItemCompra, ItemVenta, OrdenCompra, OrdenVenta, Producto
from .services import completar_venta, recibir_compra

ORDENES = {
    'compra': {
        'modelo': OrdenCompra, 'item': ItemCompra, 'ruta': 'compras',
        'titulo': 'Órdenes de compra', 'nuevo': 'Nueva orden de compra',
        'tercero': 'proveedor', 'tercero_label': 'Proveedor',
        'accion': 'Recibir mercancía', 'icono_accion': 'bi-box-arrow-in-down',
        'confirmar': '¿Recibir la mercancía? El stock de la bodega aumentará.',
        'exito': 'Mercancía recibida y stock actualizado.',
        'ejecutar': recibir_compra,
    },
    'venta': {
        'modelo': OrdenVenta, 'item': ItemVenta, 'ruta': 'ventas',
        'titulo': 'Órdenes de venta', 'nuevo': 'Nueva orden de venta',
        'tercero': 'cliente', 'tercero_label': 'Cliente',
        'accion': 'Completar venta', 'icono_accion': 'bi-check2-circle',
        'confirmar': '¿Completar la venta? El stock de la bodega disminuirá.',
        'exito': 'Venta completada y stock actualizado.',
        'ejecutar': completar_venta,
    },
}


class OrdenForm(EstiloBootstrap, forms.ModelForm):
    pass


class ItemForm(EstiloBootstrap, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        productos = Producto.objects.filter(activo=True)
        if self.instance.pk:
            productos = Producto.objects.filter(Q(activo=True) | Q(pk=self.instance.producto_id))
        self.fields['producto'].queryset = productos


def _contexto(prefijo, orden=None):
    cfg = ORDENES[prefijo]
    ctx = {
        'titulo': cfg['titulo'], 'nuevo': cfg['nuevo'],
        'tercero_label': cfg['tercero_label'],
        'accion': cfg['accion'], 'icono_accion': cfg['icono_accion'], 'confirmar': cfg['confirmar'],
        'url_lista': reverse(f'{prefijo}_lista'), 'url_crear': reverse(f'{prefijo}_crear'),
    }
    if orden is not None and orden.pk:
        ctx.update(
            tercero=getattr(orden, cfg['tercero']),
            url_detalle=reverse(f'{prefijo}_detalle', args=[orden.pk]),
            url_editar=reverse(f'{prefijo}_editar', args=[orden.pk]),
            url_accion=reverse(f'{prefijo}_accion', args=[orden.pk]),
            url_cancelar=reverse(f'{prefijo}_cancelar', args=[orden.pk]),
        )
    return ctx


class OrdenLista(LoginRequiredMixin, ListView):
    prefijo = None
    template_name = 'ordenes/lista.html'
    paginate_by = 15

    def get_queryset(self):
        cfg = ORDENES[self.prefijo]
        tercero = cfg['tercero']
        qs = (cfg['modelo'].objects
              .select_related(tercero, 'bodega', 'usuario')
              .prefetch_related('items'))
        q = self.request.GET.get('q', '').strip()
        estado = self.request.GET.get('estado', '')
        bodega = self.request.GET.get('bodega', '')
        if q:
            filtro = Q(**{f'{tercero}__nombre__icontains': q})
            if q.isdigit() and len(q) < 10:
                filtro |= Q(pk=int(q))
            qs = qs.filter(filtro)
        if estado in cfg['modelo'].Estado.values:
            qs = qs.filter(estado=estado)
        if bodega.isdigit():
            qs = qs.filter(bodega_id=bodega)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        cfg = ORDENES[self.prefijo]
        ctx.update(_contexto(self.prefijo))
        ctx['filas'] = [
            {
                'orden': o,
                'tercero': getattr(o, cfg['tercero']) or 'Mostrador',
                'url': reverse(f'{self.prefijo}_detalle', args=[o.pk]),
            }
            for o in ctx['page_obj']
        ]
        ctx['estados'] = cfg['modelo'].Estado.choices
        ctx['bodegas'] = Bodega.objects.all()
        ctx['q'] = self.request.GET.get('q', '')
        ctx['estado'] = self.request.GET.get('estado', '')
        ctx['bodega'] = self.request.GET.get('bodega', '')
        params = self.request.GET.copy()
        params.pop('page', None)
        ctx['querystring'] = params.urlencode()
        return ctx


class OrdenDetalle(LoginRequiredMixin, DetailView):
    prefijo = None
    template_name = 'ordenes/detalle.html'
    context_object_name = 'orden'

    def get_queryset(self):
        cfg = ORDENES[self.prefijo]
        return (cfg['modelo'].objects
                .select_related(cfg['tercero'], 'bodega', 'usuario')
                .prefetch_related('items__producto'))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(_contexto(self.prefijo, self.object))
        ctx['items'] = self.object.items.all()
        ctx['pendiente'] = self.object.estado == 'PENDIENTE'
        return ctx


class OrdenFormulario(LoginRequiredMixin, View):
    prefijo = None
    template_name = 'ordenes/form.html'

    def _orden(self, pk):
        modelo = ORDENES[self.prefijo]['modelo']
        return get_object_or_404(modelo, pk=pk) if pk else modelo()

    def _formularios(self, orden, datos=None):
        cfg = ORDENES[self.prefijo]
        FormOrden = modelform_factory(
            cfg['modelo'], form=OrdenForm, fields=[cfg['tercero'], 'bodega', 'observaciones'])
        FormItems = inlineformset_factory(
            cfg['modelo'], cfg['item'], form=ItemForm,
            fields=['producto', 'cantidad', 'precio_unitario'],
            localized_fields=('precio_unitario',),
            extra=0, min_num=1, validate_min=True, can_delete=True,
        )
        form = FormOrden(datos, instance=orden)
        form.fields['bodega'].queryset = Bodega.objects.filter(Q(activa=True) | Q(pk=orden.bodega_id))
        return form, FormItems(datos, instance=orden)

    def _render(self, request, orden, form, formset):
        ctx = _contexto(self.prefijo, orden)
        ctx.update(
            form=form, formset=formset,
            orden=orden if orden.pk else None,
            pagina=f'Editar {orden}' if orden.pk else ORDENES[self.prefijo]['nuevo'],
        )
        return render(request, self.template_name, ctx)

    def get(self, request, pk=None):
        orden = self._orden(pk)
        if pk and orden.estado != 'PENDIENTE':
            messages.error(request, 'Solo se pueden editar órdenes pendientes.')
            return redirect(f'{self.prefijo}_detalle', pk=pk)
        form, formset = self._formularios(orden)
        return self._render(request, orden, form, formset)

    def post(self, request, pk=None):
        orden = self._orden(pk)
        if pk and orden.estado != 'PENDIENTE':
            messages.error(request, 'Solo se pueden editar órdenes pendientes.')
            return redirect(f'{self.prefijo}_detalle', pk=pk)
        form, formset = self._formularios(orden, request.POST)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                orden = form.save(commit=False)
                if not orden.pk:
                    orden.usuario = request.user
                orden.save()
                formset.instance = orden
                formset.save()
            messages.success(request, f'{orden} guardada.')
            return redirect(f'{self.prefijo}_detalle', pk=orden.pk)
        return self._render(request, orden, form, formset)


class OrdenAccion(LoginRequiredMixin, View):
    """Recibir la mercancía (compra) o completar la venta."""
    prefijo = None

    def post(self, request, pk):
        cfg = ORDENES[self.prefijo]
        try:
            with transaction.atomic():
                orden = get_object_or_404(cfg['modelo'].objects.select_for_update(), pk=pk)
                cfg['ejecutar'](orden, request.user)
            messages.success(request, cfg['exito'])
        except ValidationError as e:
            messages.error(request, ' '.join(e.messages))
        return redirect(f'{self.prefijo}_detalle', pk=pk)


class OrdenCancelar(LoginRequiredMixin, View):
    prefijo = None

    def post(self, request, pk):
        modelo = ORDENES[self.prefijo]['modelo']
        with transaction.atomic():
            orden = get_object_or_404(modelo.objects.select_for_update(), pk=pk)
            if orden.estado == modelo.Estado.PENDIENTE:
                orden.estado = modelo.Estado.CANCELADA
                orden.save(update_fields=['estado'])
                messages.success(request, f'{orden} cancelada.')
            else:
                messages.error(request, 'Solo se pueden cancelar órdenes pendientes.')
        return redirect(f'{self.prefijo}_detalle', pk=pk)


def urls_ordenes():
    rutas = []
    for prefijo, cfg in ORDENES.items():
        base = cfg['ruta']
        rutas += [
            path(f'{base}/', OrdenLista.as_view(prefijo=prefijo), name=f'{prefijo}_lista'),
            path(f'{base}/nueva/', OrdenFormulario.as_view(prefijo=prefijo), name=f'{prefijo}_crear'),
            path(f'{base}/<int:pk>/', OrdenDetalle.as_view(prefijo=prefijo), name=f'{prefijo}_detalle'),
            path(f'{base}/<int:pk>/editar/', OrdenFormulario.as_view(prefijo=prefijo), name=f'{prefijo}_editar'),
            path(f'{base}/<int:pk>/accion/', OrdenAccion.as_view(prefijo=prefijo), name=f'{prefijo}_accion'),
            path(f'{base}/<int:pk>/cancelar/', OrdenCancelar.as_view(prefijo=prefijo), name=f'{prefijo}_cancelar'),
        ]
    return rutas