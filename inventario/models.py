from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'categorías'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='productos')
    codigo_barras = models.CharField(max_length=50, unique=True, null=True, blank=True)
    precio_compra = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    precio_venta = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    stock_actual = models.PositiveIntegerField(default=0)
    stock_minimo = models.PositiveIntegerField(default=5)
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    @property
    def stock_bajo(self):
        return self.stock_actual <= self.stock_minimo
# Create your models here.


class Movimiento(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = 'ENTRADA', 'Entrada'
        SALIDA = 'SALIDA', 'Salida'
        AJUSTE = 'AJUSTE', 'Ajuste (conteo físico)'

    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='movimientos')
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    cantidad = models.PositiveIntegerField(help_text='En un ajuste, es el stock real contado.')
    stock_resultante = models.PositiveIntegerField(editable=False)
    motivo = models.CharField(max_length=200, blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.tipo} {self.cantidad} - {self.producto}'

    def clean(self):
        if self.cantidad == 0 and self.tipo != self.Tipo.AJUSTE:
            raise ValidationError('La cantidad debe ser mayor que 0.')
        if self.tipo == self.Tipo.SALIDA and self.producto_id and self.cantidad:
            if self.cantidad > self.producto.stock_actual:
                raise ValidationError(
                    f'Stock insuficiente: {self.producto.nombre} tiene {self.producto.stock_actual} unidades.'
                )
