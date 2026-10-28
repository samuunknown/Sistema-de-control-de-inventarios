from django.contrib import admin
from django import forms

from .models import Categoria, Movimiento, Producto
from .services import aplicar_movimiento

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = '__all__'
        localized_fields = ('precio_compra', 'precio_venta')

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    form = ProductoForm
    list_display = ('nombre', 'categoria', 'precio_venta', 'stock_actual', 'stock_minimo', 'activo')
    list_filter = ('categoria', 'activo')
    search_fields = ('nombre', 'codigo_barras')
    readonly_fields = ('stock_actual',)


@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'producto', 'tipo', 'cantidad', 'stock_resultante', 'usuario')
    list_filter = ('tipo', 'fecha')
    search_fields = ('producto__nombre', 'motivo')
    readonly_fields = ('stock_resultante', 'usuario', 'fecha')

    def has_change_permission(self, request, obj=None):
        return False  # un movimiento no se edita

    def has_delete_permission(self, request, obj=None):
        return False  # ni se borra: es el historial

    def save_model(self, request, obj, form, change):
        obj.usuario = request.user
        aplicar_movimiento(obj)


