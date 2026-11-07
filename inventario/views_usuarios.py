from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import UsuarioForm


@login_required
def usuario_lista(request):
    q = request.GET.get('q', '').strip()
    usuarios = User.objects.prefetch_related('groups').order_by('username')
    if q:
        usuarios = usuarios.filter(
            Q(username__icontains=q) | Q(first_name__icontains=q)
            | Q(last_name__icontains=q) | Q(email__icontains=q)
        )
    page = Paginator(usuarios, 15).get_page(request.GET.get('page'))
    params = request.GET.copy()
    params.pop('page', None)
    return render(request, 'usuarios/lista.html', {
        'page': page, 'q': q, 'querystring': params.urlencode(),
    })


@login_required
def usuario_crear(request):
    form = UsuarioForm(request.POST or None, solicitante=request.user)
    if request.method == 'POST' and form.is_valid():
        usuario = form.save()
        messages.success(request, f'Usuario «{usuario.username}» creado.')
        return redirect('usuario_lista')
    return render(request, 'usuarios/form.html', {'form': form, 'titulo': 'Nuevo usuario'})


@login_required
def usuario_editar(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    if usuario.is_superuser and not request.user.is_superuser:
        raise PermissionDenied  # solo un superusuario puede tocar a otro superusuario
    form = UsuarioForm(request.POST or None, instance=usuario, solicitante=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Usuario «{usuario.username}» actualizado.')
        return redirect('usuario_lista')
    return render(request, 'usuarios/form.html', {
        'form': form, 'titulo': f'Editar: {usuario.username}', 'usuario_editado': usuario,
    })