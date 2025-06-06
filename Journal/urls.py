from django.contrib import admin
from django.urls import path, include
from django.conf.urls import handler404
from accounts import views  # Импортируем views из приложения accounts

# Указываем полный путь к view-функции в формате 'приложение.views.функция'
handler404 = 'accounts.views.custom_404_view'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
]
