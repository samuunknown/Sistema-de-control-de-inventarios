from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.core.validators import MinValueValidator


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
    bodega = models.ForeignKey('Bodega', on_delete=models.PROTECT)
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
        if self.tipo == self.Tipo.SALIDA and self.producto_id and self.bodega_id and self.cantidad:
            disponible = (StockBodega.objects
                          .filter(producto=self.producto, bodega=self.bodega)
                          .values_list('cantidad', flat=True).first() or 0)
            if self.cantidad > disponible:
                raise ValidationError(
                    f'Stock insuficiente en {self.bodega}: {self.producto.nombre} tiene {disponible} unidades.'
                )


class Proveedor(models.Model):
    nombre = models.CharField(max_length=150)
    nit = models.CharField(max_length=30, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)

    class Meta:
        verbose_name_plural = 'proveedores'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Cliente(models.Model):
    nombre = models.CharField(max_length=150)
    documento = models.CharField(max_length=30, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class OrdenCompra(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        RECIBIDA = 'RECIBIDA', 'Recibida'
        CANCELADA = 'CANCELADA', 'Cancelada'

    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT)
    bodega = models.ForeignKey('Bodega', on_delete=models.PROTECT, help_text='Bodega donde se recibe la mercancía.')
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    observaciones = models.CharField(max_length=200, blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'orden de compra'
        verbose_name_plural = 'órdenes de compra'

    def __str__(self):
        return f'Compra #{self.pk}'

    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())


class ItemCompra(models.Model):
    orden = models.ForeignKey(OrdenCompra, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField(
        max_digits=12, decimal_places=0, default=0,
        help_text='Si lo dejas en 0 se usa el precio de compra del producto.',
    )

    def save(self, *args, **kwargs):
        if not self.precio_unitario:
            self.precio_unitario = self.producto.precio_compra
        super().save(*args, **kwargs)

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario


class OrdenVenta(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        COMPLETADA = 'COMPLETADA', 'Completada'
        CANCELADA = 'CANCELADA', 'Cancelada'

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, null=True, blank=True, help_text='Déjalo vacío para una venta de mostrador.')
    bodega = models.ForeignKey('Bodega', on_delete=models.PROTECT, help_text='Bodega de donde sale la mercancía.')
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    observaciones = models.CharField(max_length=200, blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'orden de venta'
        verbose_name_plural = 'órdenes de venta'

    def __str__(self):
        return f'Venta #{self.pk}'

    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())


class ItemVenta(models.Model):
    orden = models.ForeignKey(OrdenVenta, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField(
        max_digits=12, decimal_places=0, default=0,
        help_text='Si lo dejas en 0 se usa el precio de venta del producto.',
    )

    def save(self, *args, **kwargs):
        if not self.precio_unitario:
            self.precio_unitario = self.producto.precio_venta
        super().save(*args, **kwargs)

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario


class Bodega(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    direccion = models.CharField(max_length=200, blank=True)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class StockBodega(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='stocks')
    bodega = models.ForeignKey(Bodega, on_delete=models.CASCADE, related_name='stocks')
    cantidad = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'stock por bodega'
        verbose_name_plural = 'stock por bodega'
        constraints = [
            models.UniqueConstraint(fields=['producto', 'bodega'], name='stock_unico_por_bodega'),
        ]

    def __str__(self):
        return f'{self.producto} en {self.bodega}: {self.cantidad}'
