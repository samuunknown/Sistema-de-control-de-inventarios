from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from inventario.views import dashboard, reporte_exportar, reportes_home

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", dashboard, name="dashboard"),
    path('reportes/', reportes_home, name='reportes'),
    path('reportes/<str:tipo>/<str:formato>/', reporte_exportar, name='reporte_exportar'),
]