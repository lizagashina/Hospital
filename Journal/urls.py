from django.contrib import admin
from django.urls import path, include
from django.conf.urls import handler404
from accounts import views

handler404 = 'accounts.views.custom_404_view'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
]
