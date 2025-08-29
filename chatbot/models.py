from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


class ChatSession(models.Model):
    CHANNEL_CHOICES = [
        ('website', 'Website Widget'),
        ('whatsapp', 'WhatsApp'),
        ('messenger', 'Facebook Messenger'),
        ('telegram', 'Telegram'),
        ('email', 'Email'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('escalated', 'Escalated to Human'),
        ('resolved', 'Resolved'),
        ('abandoned', 'Abandoned'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='website')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    is_escalated = models.BooleanField(default=False)
    escalation_reason = models.TextField(blank=True)
    escalated_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='escalated_chats')
    user_phone = models.CharField(max_length=20, blank=True)
    user_email = models.EmailField(blank=True)
    user_ip = models.GenericIPAddressField(null=True, blank=True)
    
    def __str__(self):
        return f"Chat {self.session_id} ({self.channel})"


class ChatMessage(models.Model):
    MESSAGE_TYPES = [
        ('user', 'User Message'),
        ('bot', 'Bot Response'),
        ('system', 'System Message'),
        ('agent', 'Human Agent'),
    ]
    
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    intent = models.CharField(max_length=100, blank=True)
    confidence_score = models.FloatField(null=True, blank=True)
    response_time = models.FloatField(null=True, blank=True, help_text="Response time in seconds")
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.message_type}: {self.content[:50]}..."


class Intent(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    keywords = models.TextField(help_text="Comma-separated keywords")
    response_template = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name


class FAQ(models.Model):
    CATEGORY_CHOICES = [
        ('general', 'General Information'),
        ('services', 'Services'),
        ('pricing', 'Pricing'),
        ('location', 'Location & Hours'),
        ('support', 'Support'),
        ('products', 'Products'),
        ('orders', 'Orders & Shipping'),
    ]
    
    question = models.CharField(max_length=300)
    answer = models.TextField()
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES, default='general')
    keywords = models.TextField(help_text="Comma-separated keywords for matching", blank=True)
    is_active = models.BooleanField(default=True)
    view_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.question


class ChatFeedback(models.Model):
    RATING_CHOICES = [
        (1, '1 - Very Poor'),
        (2, '2 - Poor'),
        (3, '3 - Average'),
        (4, '4 - Good'),
        (5, '5 - Excellent'),
    ]
    
    session = models.OneToOneField(ChatSession, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=RATING_CHOICES)
    feedback_text = models.TextField(blank=True)
    suggestions = models.TextField(blank=True)
    was_helpful = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Feedback for {self.session.session_id}: {self.rating}/5"


class EscalationQueue(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    session = models.OneToOneField(ChatSession, on_delete=models.CASCADE)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    assigned_agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_escalations')
    escalation_time = models.DateTimeField(auto_now_add=True)
    response_time = models.DateTimeField(null=True, blank=True)
    resolution_time = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    is_resolved = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Escalation {self.session.session_id} - {self.priority}"


class Notification(models.Model):
    TYPE_CHOICES = [
        ('booking_confirmation', 'Booking Confirmation'),
        ('order_status', 'Order Status Update'),
        ('promotional', 'Promotional'),
        ('reminder', 'Reminder'),
        ('escalation', 'Escalation Alert'),
    ]
    
    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
        ('whatsapp', 'WhatsApp'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('delivered', 'Delivered'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, null=True, blank=True)
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    recipient = models.CharField(max_length=255)
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    scheduled_time = models.DateTimeField(null=True, blank=True)
    sent_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.notification_type} to {self.recipient}"


class ChatAnalytics(models.Model):
    date = models.DateField()
    total_sessions = models.IntegerField(default=0)
    resolved_queries = models.IntegerField(default=0)
    escalated_queries = models.IntegerField(default=0)
    average_response_time = models.FloatField(default=0.0)
    average_session_duration = models.FloatField(default=0.0)
    user_satisfaction_score = models.FloatField(default=0.0)
    channel_website = models.IntegerField(default=0)
    channel_whatsapp = models.IntegerField(default=0)
    channel_messenger = models.IntegerField(default=0)
    most_common_intent = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('date',)
        verbose_name_plural = "Chat Analytics"
    
    def __str__(self):
        return f"Analytics for {self.date}"


class BusinessHours(models.Model):
    DAYS_OF_WEEK = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]
    
    day = models.CharField(max_length=10, choices=DAYS_OF_WEEK, unique=True)
    open_time = models.TimeField(null=True, blank=True)
    close_time = models.TimeField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)
    
    class Meta:
        verbose_name_plural = "Business Hours"
    
    def __str__(self):
        if self.is_closed:
            return f"{self.day.capitalize()}: Closed"
        return f"{self.day.capitalize()}: {self.open_time} - {self.close_time}"


class CompanyInfo(models.Model):
    name = models.CharField(max_length=200, default="Riverway Company Limited")
    address = models.TextField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    website = models.URLField(blank=True)
    description = models.TextField()
    services = models.TextField(help_text="List of services offered", default="Hardware products and supplies")
    pricing_info = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Company Information"
        verbose_name_plural = "Company Information"
    
    def __str__(self):
        return self.name


class ChatbotSettings(models.Model):
    welcome_message = models.TextField(default="Welcome to Riverway Company! How can I help you today?")
    fallback_message = models.TextField(default="I'm sorry, I didn't understand. Let me connect you with a human agent.")
    escalation_threshold = models.IntegerField(default=3, help_text="Number of unresolved attempts before escalation")
    response_delay = models.FloatField(default=1.0, help_text="Simulated typing delay in seconds")
    working_hours_message = models.TextField(default="We're currently outside business hours. Your message will be answered when we return.")
    max_session_duration = models.IntegerField(default=3600, help_text="Maximum session duration in seconds")
    enable_analytics = models.BooleanField(default=True)
    enable_feedback = models.BooleanField(default=True)
    enable_notifications = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Chatbot Settings"
        verbose_name_plural = "Chatbot Settings"
    
    def __str__(self):
        return "Chatbot Configuration"
