from django.db import migrations


def crear_bodega_principal(apps, schema_editor):
    Bodega = apps.get_model('inventario', 'Bodega')
    Producto = apps.get_model('inventario', 'Producto')
    StockBodega = apps.get_model('inventario', 'StockBodega')
    Movimiento = apps.get_model('inventario', 'Movimiento')
    OrdenCompra = apps.get_model('inventario', 'OrdenCompra')
    OrdenVenta = apps.get_model('inventario', 'OrdenVenta')

    principal, _ = Bodega.objects.get_or_create(nombre='Bodega principal')
    for p in Producto.objects.all():
        StockBodega.objects.get_or_create(
            producto=p, bodega=principal, defaults={'cantidad': p.stock_actual}
        )
    Movimiento.objects.filter(bodega__isnull=True).update(bodega=principal)
    OrdenCompra.objects.filter(bodega__isnull=True).update(bodega=principal)
    OrdenVenta.objects.filter(bodega__isnull=True).update(bodega=principal)


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0005_bodega_movimiento_bodega_ordencompra_bodega_and_more'),
    ]

    operations = [
        migrations.RunPython(crear_bodega_principal, migrations.RunPython.noop),
    ]

