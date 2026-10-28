from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db import models

from .models import (Bodega, Categoria, Cliente, ItemCompra, ItemVenta, Movimiento,
                     OrdenCompra, OrdenVenta, Producto, Proveedor, StockBodega)
from .services import aplicar_movimiento, completar_venta, recibir_compra

# Permite escribir precios con puntos de miles (40.000)
LOCALIZAR = {models.DecimalField: {'localize': True}}

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = '__all__'
        localized_fields = ('precio_compra', 'precio_venta')

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)


@admin.register(Bodega)
class BodegaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'direccion', 'activa')
    search_fields = ('nombre',)


class StockInline(admin.TabularInline):
    model = StockBodega
    extra = 0
    readonly_fields = ('bodega', 'cantidad')
    verbose_name_plural = 'Stock por bodega'

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    form = ProductoForm
    inlines = [StockInline]
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


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'nit', 'telefono', 'email')
    search_fields = ('nombre', 'nit')


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'documento', 'telefono', 'email')
    search_fields = ('nombre', 'documento')


class ItemCompraInline(admin.TabularInline):
    model = ItemCompra
    extra = 1
    formfield_overrides = LOCALIZAR


class ItemVentaInline(admin.TabularInline):
    model = ItemVenta
    extra = 1
    formfield_overrides = LOCALIZAR


def formato_pesos(valor):
    return f'$ {valor:,.0f}'.replace(',', '.')


@admin.register(OrdenCompra)
class OrdenCompraAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'proveedor', 'fecha', 'estado', 'total_pesos', 'usuario')
    list_filter = ('estado', 'fecha')
    readonly_fields = ('estado', 'usuario', 'fecha')
    inlines = [ItemCompraInline]
    actions = ['recibir', 'cancelar']

    @admin.display(description='Total')
    def total_pesos(self, obj):
        return formato_pesos(obj.total)

    def has_change_permission(self, request, obj=None):
        return obj is None or obj.estado == OrdenCompra.Estado.PENDIENTE

    def save_model(self, request, obj, form, change):
        if not change:
            obj.usuario = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description='Recibir mercancía (suma al stock)')
    def recibir(self, request, queryset):
        for orden in queryset:
            try:
                recibir_compra(orden, request.user)
                self.message_user(request, f'{orden} recibida.')
            except ValidationError as e:
                self.message_user(request, f'{orden}: {e.message}', level=messages.ERROR)

    @admin.action(description='Cancelar órdenes pendientes')
    def cancelar(self, request, queryset):
        queryset.filter(estado=OrdenCompra.Estado.PENDIENTE).update(estado=OrdenCompra.Estado.CANCELADA)


@admin.register(OrdenVenta)
class OrdenVentaAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'cliente', 'fecha', 'estado', 'total_pesos', 'usuario')
    list_filter = ('estado', 'fecha')
    readonly_fields = ('estado', 'usuario', 'fecha')
    inlines = [ItemVentaInline]
    actions = ['completar', 'cancelar']

    @admin.display(description='Total')
    def total_pesos(self, obj):
        return formato_pesos(obj.total)

    def has_change_permission(self, request, obj=None):
        return obj is None or obj.estado == OrdenVenta.Estado.PENDIENTE

    def save_model(self, request, obj, form, change):
        if not change:
            obj.usuario = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description='Completar venta (descuenta del stock)')
    def completar(self, request, queryset):
        for orden in queryset:
            try:
                completar_venta(orden, request.user)
                self.message_user(request, f'{orden} completada.')
            except ValidationError as e:
                self.message_user(request, f'{orden}: {e.message}', level=messages.ERROR)

    @admin.action(description='Cancelar órdenes pendientes')
    def cancelar(self, request, queryset):
        queryset.filter(estado=OrdenVenta.Estado.PENDIENTE).update(estado=OrdenVenta.Estado.CANCELADA)


