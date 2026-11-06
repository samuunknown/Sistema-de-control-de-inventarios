from django import forms

from .models import Bodega, Movimiento, Producto


class EstiloBootstrap:
    """Aplica las clases de Bootstrap a todos los campos del formulario."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            if isinstance(campo.widget, forms.CheckboxInput):
                campo.widget.attrs['class'] = 'form-check-input'
            elif isinstance(campo.widget, forms.Select):
                campo.widget.attrs['class'] = 'form-select'
            else:
                campo.widget.attrs['class'] = 'form-control'


class ProductoForm(EstiloBootstrap, forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'categoria', 'codigo_barras', 'descripcion',
                  'precio_compra', 'precio_venta', 'stock_minimo', 'activo']
        localized_fields = ('precio_compra', 'precio_venta')
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 3})}


class ProductoCrearForm(ProductoForm):
    stock_inicial = forms.IntegerField(
        min_value=0, required=False, label='Stock inicial',
        help_text='Opcional. Se registra como una entrada.',
    )
    bodega = forms.ModelChoiceField(
        queryset=Bodega.objects.filter(activa=True), required=False,
        label='Bodega del stock inicial',
    )

    def clean(self):
        datos = super().clean()
        if (datos.get('stock_inicial') or 0) > 0 and not datos.get('bodega'):
            self.add_error('bodega', 'Elige la bodega donde está ese stock.')
        return datos


class MovimientoForm(EstiloBootstrap, forms.ModelForm):
    class Meta:
        model = Movimiento
        fields = ['tipo', 'producto', 'bodega', 'cantidad', 'motivo']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['producto'].queryset = Producto.objects.filter(activo=True)
        self.fields['bodega'].queryset = Bodega.objects.filter(activa=True)


class TrasladoForm(EstiloBootstrap, forms.Form):
    producto = forms.ModelChoiceField(queryset=Producto.objects.filter(activo=True))
    origen = forms.ModelChoiceField(queryset=Bodega.objects.filter(activa=True), label='Bodega de origen')
    destino = forms.ModelChoiceField(queryset=Bodega.objects.filter(activa=True), label='Bodega de destino')
    cantidad = forms.IntegerField(min_value=1)
    motivo = forms.CharField(max_length=150, required=False)

    def clean(self):
        datos = super().clean()
        origen, destino = datos.get('origen'), datos.get('destino')
        if origen and destino and origen == destino:
            self.add_error('destino', 'La bodega de destino debe ser distinta a la de origen.')
        return datos