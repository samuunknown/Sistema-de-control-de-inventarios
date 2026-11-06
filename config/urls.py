from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from inventario.views import dashboard, reporte_exportar, reportes_home
from inventario.views_productos import producto_crear, producto_editar, producto_lista
from inventario.views_movimientos import movimiento_crear, movimiento_lista, movimiento_traslado
from inventario.views_catalogos import urls_catalogos
from inventario.views_ordenes import urls_ordenes

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", dashboard, name="dashboard"),
    path('reportes/', reportes_home, name='reportes'),
    path('reportes/<str:tipo>/<str:formato>/', reporte_exportar, name='reporte_exportar'),
    path('productos/', producto_lista, name='producto_lista'),
    path('productos/nuevo/', producto_crear, name='producto_crear'),
    path('productos/<int:pk>/editar/', producto_editar, name='producto_editar'),
    path('movimientos/', movimiento_lista, name='movimiento_lista'),
    path('movimientos/nuevo/', movimiento_crear, name='movimiento_crear'),
    path('movimientos/traslado/', movimiento_traslado, name='movimiento_traslado'),
]

urlpatterns += urls_catalogos()
urlpatterns += urls_ordenes()