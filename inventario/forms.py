from django import forms
from .models import Bodega, Movimiento, Producto
from django.contrib.auth import password_validation
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError


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



class UsuarioForm(EstiloBootstrap, forms.ModelForm):
    rol = forms.ModelChoiceField(queryset=Group.objects.order_by('name'), label='Rol')
    password1 = forms.CharField(
        label='Contraseña', required=False, widget=forms.PasswordInput,
        help_text='Mínimo 8 caracteres. Al editar, déjala vacía para mantener la actual.',
    )
    password2 = forms.CharField(label='Confirmar contraseña', required=False, widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
        labels = {
            'username': 'Usuario', 'first_name': 'Nombre', 'last_name': 'Apellido',
            'email': 'Correo', 'is_active': 'Usuario activo',
        }

    def __init__(self, *args, solicitante=None, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            grupo = self.instance.groups.first()
            if grupo:
                self.initial['rol'] = grupo.pk
            if self.instance.is_superuser:
                self.fields['rol'].required = False
            if solicitante and self.instance.pk == solicitante.pk:
                # Evita que alguien se desactive o se quite el rol a sí mismo
                self.fields['is_active'].disabled = True
                self.fields['rol'].disabled = True

    def clean(self):
        datos = super().clean()
        p1, p2 = datos.get('password1'), datos.get('password2')
        if not self.instance.pk and not p1:
            self.add_error('password1', 'La contraseña es obligatoria.')
        if p1 or p2:
            if p1 != p2:
                self.add_error('password2', 'Las contraseñas no coinciden.')
            else:
                try:
                    password_validation.validate_password(p1, self.instance)
                except ValidationError as e:
                    self.add_error('password1', e)
        return datos

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if self.cleaned_data.get('password1'):
            usuario.set_password(self.cleaned_data['password1'])
        usuario.save()
        rol = self.cleaned_data.get('rol')
        usuario.groups.set([rol] if rol else [])
        return usuario