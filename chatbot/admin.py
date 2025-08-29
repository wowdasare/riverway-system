from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Avg
from .models import (
    ChatSession, ChatMessage, FAQ, BusinessHours, CompanyInfo,
    ChatFeedback, EscalationQueue, Notification, ChatAnalytics, 
    ChatbotSettings, Intent
)


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'channel', 'user', 'status', 'created_at', 'is_escalated', 'message_count')
    list_filter = ('channel', 'status', 'is_escalated', 'created_at')
    search_fields = ('session_id', 'user__username', 'user_email', 'user_phone')
    readonly_fields = ('created_at', 'updated_at', 'session_id')
    
    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = 'Messages'
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            msg_count=Count('messages')
        )


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    readonly_fields = ('timestamp', 'intent', 'confidence_score', 'response_time')
    extra = 0


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'message_type', 'intent', 'confidence_score', 'content_preview', 'timestamp')
    list_filter = ('message_type', 'intent', 'timestamp')
    search_fields = ('content', 'session__session_id')
    readonly_fields = ('timestamp', 'response_time')
    
    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'


@admin.register(Intent)
class IntentAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'is_active', 'usage_count', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description', 'keywords')
    
    def usage_count(self, obj):
        return ChatMessage.objects.filter(intent=obj.name).count()
    usage_count.short_description = 'Usage Count'


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'category', 'is_active', 'view_count', 'created_at')
    list_filter = ('category', 'is_active', 'created_at')
    search_fields = ('question', 'answer', 'keywords')
    readonly_fields = ('view_count', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('question', 'answer', 'category', 'is_active')
        }),
        ('SEO & Matching', {
            'fields': ('keywords',),
            'description': 'Add comma-separated keywords to help match user queries'
        }),
        ('Statistics', {
            'fields': ('view_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(ChatFeedback)
class ChatFeedbackAdmin(admin.ModelAdmin):
    list_display = ('session', 'rating', 'was_helpful', 'created_at')
    list_filter = ('rating', 'was_helpful', 'created_at')
    search_fields = ('session__session_id', 'feedback_text')
    readonly_fields = ('created_at',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('session')


@admin.register(EscalationQueue)
class EscalationQueueAdmin(admin.ModelAdmin):
    list_display = ('session', 'priority', 'assigned_agent', 'escalation_time', 'is_resolved')
    list_filter = ('priority', 'is_resolved', 'escalation_time')
    search_fields = ('session__session_id', 'notes')
    readonly_fields = ('escalation_time',)
    
    actions = ['assign_to_me', 'mark_resolved']
    
    def assign_to_me(self, request, queryset):
        updated = queryset.update(assigned_agent=request.user)
        self.message_user(request, f'{updated} escalations assigned to you.')
    assign_to_me.short_description = "Assign selected escalations to me"
    
    def mark_resolved(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(is_resolved=True, resolution_time=timezone.now())
        self.message_user(request, f'{updated} escalations marked as resolved.')
    mark_resolved.short_description = "Mark selected escalations as resolved"


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('notification_type', 'channel', 'recipient', 'status', 'created_at')
    list_filter = ('notification_type', 'channel', 'status', 'created_at')
    search_fields = ('recipient', 'subject', 'message')
    readonly_fields = ('created_at', 'sent_time')


@admin.register(ChatAnalytics)
class ChatAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('date', 'total_sessions', 'resolved_queries', 'escalated_queries', 'escalation_rate', 'average_rating')
    list_filter = ('date',)
    readonly_fields = ('date', 'created_at')
    
    def escalation_rate(self, obj):
        if obj.total_sessions > 0:
            rate = (obj.escalated_queries / obj.total_sessions) * 100
            color = 'red' if rate > 20 else 'orange' if rate > 10 else 'green'
            return format_html('<span style="color: {};">{:.1f}%</span>', color, rate)
        return '0%'
    escalation_rate.short_description = 'Escalation Rate'
    
    def average_rating(self, obj):
        if obj.user_satisfaction_score > 0:
            color = 'green' if obj.user_satisfaction_score >= 4 else 'orange' if obj.user_satisfaction_score >= 3 else 'red'
            return format_html('<span style="color: {};">{:.1f}/5</span>', color, obj.user_satisfaction_score)
        return 'N/A'
    average_rating.short_description = 'Avg Rating'


@admin.register(BusinessHours)
class BusinessHoursAdmin(admin.ModelAdmin):
    list_display = ('day', 'open_time', 'close_time', 'is_closed', 'formatted_hours')
    list_filter = ('is_closed',)
    
    def formatted_hours(self, obj):
        if obj.is_closed:
            return format_html('<span style="color: red;">Closed</span>')
        elif obj.open_time and obj.close_time:
            return f"{obj.open_time.strftime('%I:%M %p')} - {obj.close_time.strftime('%I:%M %p')}"
        return 'Not Set'
    formatted_hours.short_description = 'Hours'


@admin.register(CompanyInfo)
class CompanyInfoAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'website')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description')
        }),
        ('Contact Details', {
            'fields': ('address', 'phone', 'email', 'website')
        }),
        ('Business Information', {
            'fields': ('services', 'pricing_info')
        })
    )
    
    def has_add_permission(self, request):
        return not CompanyInfo.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ChatbotSettings)
class ChatbotSettingsAdmin(admin.ModelAdmin):
    list_display = ('welcome_message_preview', 'escalation_threshold', 'enable_analytics', 'enable_feedback')
    
    fieldsets = (
        ('Messages', {
            'fields': ('welcome_message', 'fallback_message', 'working_hours_message')
        }),
        ('Behavior Settings', {
            'fields': ('escalation_threshold', 'response_delay', 'max_session_duration')
        }),
        ('Feature Toggles', {
            'fields': ('enable_analytics', 'enable_feedback', 'enable_notifications')
        })
    )
    
    def welcome_message_preview(self, obj):
        return obj.welcome_message[:50] + "..." if len(obj.welcome_message) > 50 else obj.welcome_message
    welcome_message_preview.short_description = 'Welcome Message'
    
    def has_add_permission(self, request):
        return not ChatbotSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False


# Customize admin site
admin.site.site_header = "Riverway Chatbot Administration"
admin.site.site_title = "Riverway Chatbot Admin"
admin.site.index_title = "Chatbot Management Dashboard"
