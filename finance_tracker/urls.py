from django.contrib import admin
from django.urls import path, include
from finances import views as finance_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Django's built-in login/logout system
    path('accounts/', include('django.contrib.auth.urls')), 
    
    # OUR CUSTOM REGISTRATION SCREEN
    path('accounts/register/', finance_views.register, name='register'),
    
    # All your finance app routes
    path('', include('finances.urls')),
]