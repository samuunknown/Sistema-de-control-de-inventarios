from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.forms import modelform_factory
from django.urls import path, reverse
from django.views.generic import CreateView, ListView, UpdateView

from .forms import EstiloBootstrap
from .models import Bodega, Categoria, Cliente, Proveedor

# Cada catálogo se describe aquí; el resto del código es común a todos.
CATALOGOS = {
    'bodega': {
        'modelo': Bodega, 'ruta': 'bodegas', 'titulo': 'Bodegas', 'nuevo': 'Nueva bodega',
        'campos': ['nombre', 'direccion', 'activa'],
        'columnas': [('Nombre', 'nombre'), ('Dirección', 'direccion'), ('Activa', 'activa')],
        'busqueda': ['nombre', 'direccion'],
    },
    'categoria': {
        'modelo': Categoria, 'ruta': 'categorias', 'titulo': 'Categorías', 'nuevo': 'Nueva categoría',
        'campos': ['nombre', 'descripcion'],
        'columnas': [('Nombre', 'nombre'), ('Descripción', 'descripcion')],
        'busqueda': ['nombre', 'descripcion'],
    },
    'proveedor': {
        'modelo': Proveedor, 'ruta': 'proveedores', 'titulo': 'Proveedores', 'nuevo': 'Nuevo proveedor',
        'campos': ['nombre', 'nit', 'telefono', 'email'],
        'columnas': [('Nombre', 'nombre'), ('NIT', 'nit'), ('Teléfono', 'telefono'), ('Correo', 'email')],
        'busqueda': ['nombre', 'nit', 'email'],
    },
    'cliente': {
        'modelo': Cliente, 'ruta': 'clientes', 'titulo': 'Clientes', 'nuevo': 'Nuevo cliente',
        'campos': ['nombre', 'documento', 'telefono', 'email'],
        'columnas': [('Nombre', 'nombre'), ('Documento', 'documento'), ('Teléfono', 'telefono'), ('Correo', 'email')],
        'busqueda': ['nombre', 'documento', 'email'],
    },
}


class CatalogoForm(EstiloBootstrap, forms.ModelForm):
    pass


class CatalogoLista(LoginRequiredMixin, ListView):
    prefijo = None
    template_name = 'catalogos/lista.html'
    paginate_by = 15

    @property
    def config(self):
        return CATALOGOS[self.prefijo]

    def get_queryset(self):
        qs = self.config['modelo'].objects.all()
        q = self.request.GET.get('q', '').strip()
        if q:
            filtro = Q()
            for campo in self.config['busqueda']:
                filtro |= Q(**{f'{campo}__icontains': q})
            qs = qs.filter(filtro)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        columnas = self.config['columnas']
        ctx['titulo'] = self.config['titulo']
        ctx['nuevo'] = self.config['nuevo']
        ctx['encabezados'] = [nombre for nombre, _ in columnas]
        ctx['filas'] = [
            ([getattr(obj, attr) for _, attr in columnas], reverse(f'{self.prefijo}_editar', args=[obj.pk]))
            for obj in ctx['page_obj']
        ]
        ctx['url_crear'] = reverse(f'{self.prefijo}_crear')
        ctx['q'] = self.request.GET.get('q', '')
        params = self.request.GET.copy()
        params.pop('page', None)
        ctx['querystring'] = params.urlencode()
        return ctx


class CatalogoBase(LoginRequiredMixin):
    prefijo = None
    template_name = 'catalogos/form.html'

    @property
    def config(self):
        return CATALOGOS[self.prefijo]

    def get_queryset(self):
        return self.config['modelo'].objects.all()

    def get_form_class(self):
        return modelform_factory(self.config['modelo'], form=CatalogoForm, fields=self.config['campos'])

    def get_success_url(self):
        return reverse(f'{self.prefijo}_lista')

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        messages.success(self.request, f'Guardado: «{self.object}».')
        return respuesta

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = self.get_titulo()
        ctx['url_lista'] = reverse(f'{self.prefijo}_lista')
        ctx['volver'] = self.config['titulo']
        return ctx


class CatalogoCrear(CatalogoBase, CreateView):
    def get_titulo(self):
        return self.config['nuevo']


class CatalogoEditar(CatalogoBase, UpdateView):
    def get_titulo(self):
        return f'Editar: {self.object}'


def urls_catalogos():
    rutas = []
    for prefijo, cfg in CATALOGOS.items():
        base = cfg['ruta']
        rutas += [
            path(f'{base}/', CatalogoLista.as_view(prefijo=prefijo), name=f'{prefijo}_lista'),
            path(f'{base}/nuevo/', CatalogoCrear.as_view(prefijo=prefijo), name=f'{prefijo}_crear'),
            path(f'{base}/<int:pk>/editar/', CatalogoEditar.as_view(prefijo=prefijo), name=f'{prefijo}_editar'),
        ]
    return rutas