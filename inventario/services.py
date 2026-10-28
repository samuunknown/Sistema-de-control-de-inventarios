from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Movimiento, OrdenCompra, OrdenVenta, Producto, StockBodega


@transaction.atomic
def aplicar_movimiento(mov):
    # Bloquea el producto y su stock en esa bodega para evitar choques entre operaciones
    producto = Producto.objects.select_for_update().get(pk=mov.producto_id)
    stock, _ = StockBodega.objects.select_for_update().get_or_create(
        producto=producto, bodega_id=mov.bodega_id
    )

    if mov.tipo == Movimiento.Tipo.ENTRADA:
        nuevo = stock.cantidad + mov.cantidad
    elif mov.tipo == Movimiento.Tipo.SALIDA:
        if mov.cantidad > stock.cantidad:
            raise ValidationError(f'Stock insuficiente: hay {stock.cantidad} unidades en esa bodega.')
        nuevo = stock.cantidad - mov.cantidad
    else:  # AJUSTE: la cantidad es el stock real contado en esa bodega
        nuevo = mov.cantidad

    producto.stock_actual += nuevo - stock.cantidad   # el total del producto se mantiene al día
    stock.cantidad = nuevo
    stock.save(update_fields=['cantidad'])
    producto.save(update_fields=['stock_actual', 'actualizado'])

    mov.stock_resultante = nuevo   # ahora es el stock que quedó en esa bodega
    mov.save()
    return mov


@transaction.atomic
def recibir_compra(orden, usuario):
    if orden.estado != OrdenCompra.Estado.PENDIENTE:
        raise ValidationError('Solo se pueden recibir órdenes pendientes.')
    if not orden.items.exists():
        raise ValidationError('La orden no tiene productos.')

    for item in orden.items.select_related('producto'):
        aplicar_movimiento(Movimiento(
            producto=item.producto, bodega=orden.bodega, tipo=Movimiento.Tipo.ENTRADA,
            cantidad=item.cantidad, motivo=f'Compra #{orden.pk}', usuario=usuario,
        ))
    orden.estado = OrdenCompra.Estado.RECIBIDA
    orden.save(update_fields=['estado'])


@transaction.atomic
def completar_venta(orden, usuario):
    if orden.estado != OrdenVenta.Estado.PENDIENTE:
        raise ValidationError('Solo se pueden completar órdenes pendientes.')
    if not orden.items.exists():
        raise ValidationError('La orden no tiene productos.')

    for item in orden.items.select_related('producto'):
        aplicar_movimiento(Movimiento(
            producto=item.producto, bodega=orden.bodega, tipo=Movimiento.Tipo.SALIDA,
            cantidad=item.cantidad, motivo=f'Venta #{orden.pk}', usuario=usuario,
        ))
    orden.estado = OrdenVenta.Estado.COMPLETADA
    orden.save(update_fields=['estado'])