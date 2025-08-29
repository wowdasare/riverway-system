from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    
    # Products
    path('products/', views.product_list, name='product_list'),
    path('products/create/', views.product_create, name='product_create'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    
    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    
    # Orders
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),
    
    # Chatbot settings
    path('chatbot/', views.chatbot_settings, name='chatbot_settings'),
    path('chatbot/analytics/', views.chatbot_analytics, name='chatbot_analytics'),
    
    # Analytics API
    path('api/analytics/', views.analytics_api, name='analytics_api'),
    
    # Export and Reports
    path('export/', views.export_data, name='export_data'),
    path('report/', views.generate_report, name='generate_report'),
]