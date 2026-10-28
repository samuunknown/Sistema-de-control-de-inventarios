from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Movimiento, Producto


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