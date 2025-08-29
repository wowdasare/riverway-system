from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    # Main chatbot API
    path('api/', views.chatbot_api, name='api'),
    
    # Feedback system
    path('feedback/', views.submit_feedback, name='submit_feedback'),
    
    # Chat history
    path('history/<str:session_id>/', views.chat_history, name='chat_history'),
    
    # Widget
    path('widget/', views.chatbot_widget, name='widget'),
    
    # Multi-channel webhooks
    path('webhook/whatsapp/', views.webhook_whatsapp, name='webhook_whatsapp'),
    path('webhook/messenger/', views.webhook_messenger, name='webhook_messenger'),
    
    # Analytics
    path('analytics/', views.analytics_data, name='analytics'),
    
    # Contact Support
    path('contact-support/', views.contact_support, name='contact_support'),
]