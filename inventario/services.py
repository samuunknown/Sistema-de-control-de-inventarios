from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Movimiento, OrdenCompra, OrdenVenta, Producto


@transaction.atomic
def aplicar_movimiento(mov):
    # Bloquea la fila del producto para que dos operaciones simultáneas no se pisen
    producto = Producto.objects.select_for_update().get(pk=mov.producto_id)

    if mov.tipo == Movimiento.Tipo.ENTRADA:
        nuevo = producto.stock_actual + mov.cantidad
    elif mov.tipo == Movimiento.Tipo.SALIDA:
        if mov.cantidad > producto.stock_actual:
            raise ValidationError(f'Stock insuficiente: hay {producto.stock_actual} unidades.')
        nuevo = producto.stock_actual - mov.cantidad
    else:  # AJUSTE: la cantidad es el stock real
        nuevo = mov.cantidad

    producto.stock_actual = nuevo
    producto.save(update_fields=['stock_actual', 'actualizado'])

    mov.stock_resultante = nuevo
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
            producto=item.producto, tipo=Movimiento.Tipo.ENTRADA,
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
            producto=item.producto, tipo=Movimiento.Tipo.SALIDA,
            cantidad=item.cantidad, motivo=f'Venta #{orden.pk}', usuario=usuario,
        ))
    orden.estado = OrdenVenta.Estado.COMPLETADA
    orden.save(update_fields=['estado'])