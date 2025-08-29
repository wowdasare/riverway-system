from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Count
from django.core.mail import send_mail
from django.conf import settings
from .models import (
    ChatSession, ChatMessage, FAQ, BusinessHours, CompanyInfo, 
    ChatFeedback, EscalationQueue, Notification, ChatAnalytics, ChatbotSettings
)
from .nlp_engine import ChatbotEngine
from store.models import Product, Category
import json
import uuid
import re
import time as time_module
from datetime import datetime, time, timedelta
import logging

logger = logging.getLogger(__name__)

# Initialize chatbot engine
chatbot_engine = ChatbotEngine()


@csrf_exempt
@require_http_methods(["POST"])
def chatbot_api(request):
    """Main chatbot API endpoint"""
    start_time = time_module.time()
    
    try:
        data = json.loads(request.body)
        message = data.get('message', '').strip()
        channel = data.get('channel', 'website')
        user_phone = data.get('phone', '')
        user_email = data.get('email', '')
        
        if not message:
            return JsonResponse({
                'response': 'Please enter a message.',
                'status': 'error'
            })
        
        # Get or create chat session with better authentication handling
        session_id = request.session.get('chat_session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            request.session['chat_session_id'] = session_id
            request.session.set_expiry(7200)  # 2 hours session expiry
        
        # Get client IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        chat_session, created = ChatSession.objects.get_or_create(
            session_id=session_id,
            defaults={
                'user': request.user if hasattr(request, 'user') and request.user.is_authenticated else None,
                'channel': channel,
                'user_phone': user_phone,
                'user_email': user_email,
                'user_ip': ip
            }
        )
        
        # Update session with current user if they logged in during chat
        if hasattr(request, 'user') and request.user.is_authenticated and not chat_session.user:
            chat_session.user = request.user
            chat_session.save()
        
        # Save user message
        user_message = ChatMessage.objects.create(
            session=chat_session,
            message_type='user',
            content=message
        )
        
        # Generate bot response using NLP engine with enhanced context and chat history
        user_context = None
        chat_history = []
        
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_context = {
                'user': request.user,
                'username': request.user.first_name or request.user.username,
                'email': request.user.email,
                'is_authenticated': True
            }
        else:
            # Handle guest users - check if they've provided their name
            guest_name = request.session.get('guest_name', '')
            user_context = {
                'user': None,
                'username': guest_name,
                'email': '',
                'is_authenticated': False,
                'is_guest': True,
                'has_name': bool(guest_name)
            }
        
        # Get recent chat history for context (last 10 messages)
        recent_messages = ChatMessage.objects.filter(
            session=chat_session
        ).order_by('-timestamp')[:10]
        
        chat_history = [{
            'type': msg.message_type,
            'content': msg.content,
            'intent': msg.intent,
            'timestamp': msg.timestamp
        } for msg in reversed(recent_messages)]
        
        response_data = chatbot_engine.generate_response(
            message, 
            session_id, 
            user_context,
            chat_history
        )
        
        # Check if the bot collected the user's name and store it in session
        if response_data.get('guest_name_collected'):
            request.session['guest_name'] = response_data['guest_name_collected']
            request.session.save()
        
        # Calculate response time
        response_time = time_module.time() - start_time
        
        # Save bot response
        bot_message = ChatMessage.objects.create(
            session=chat_session,
            message_type='bot',
            content=response_data['message'],
            intent=response_data.get('intent', ''),
            confidence_score=response_data.get('confidence', 0.0),
            response_time=response_time
        )
        
        # Handle escalation if needed
        should_escalate = response_data.get('should_escalate', False)
        if should_escalate and not chat_session.is_escalated:
            escalate_to_human(chat_session, response_data.get('escalation_reason', ''))
        
        # Send notifications if configured
        if response_data.get('send_notification'):
            send_chat_notification(chat_session, response_data['message'])
        
        return JsonResponse({
            'response': response_data['message'],
            'intent': response_data.get('intent', ''),
            'confidence': response_data.get('confidence', 0.0),
            'suggested_actions': response_data.get('suggested_actions', []),
            'escalated': should_escalate,
            'session_id': session_id,
            'products': response_data.get('products', []),
            'user_authenticated': hasattr(request, 'user') and request.user.is_authenticated,
            'username': request.user.first_name or request.user.username if hasattr(request, 'user') and request.user.is_authenticated else None,
            'greeting_type': response_data.get('greeting_type', 'standard'),
            'personalized': hasattr(request, 'user') and request.user.is_authenticated,
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Chatbot API error: {e}")
        return JsonResponse({
            'response': 'Sorry, I encountered an error. Please try again or contact our support team.',
            'status': 'error'
        })


def escalate_to_human(chat_session, reason):
    """Handle escalation to human agent and send detailed email"""
    try:
        chat_session.is_escalated = True
        chat_session.escalation_reason = reason
        chat_session.status = 'escalated'
        chat_session.save()
        
        # Create escalation queue entry
        EscalationQueue.objects.create(
            session=chat_session,
            priority='medium',  # Default priority
            notes=reason
        )
        
        # Get conversation history for email
        messages = ChatMessage.objects.filter(session=chat_session).order_by('timestamp')
        conversation_history = []
        for msg in messages:
            timestamp = msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            conversation_history.append(f"[{timestamp}] {msg.message_type.upper()}: {msg.content}")
        
        # Prepare email content
        user_info = "Guest User"
        if chat_session.user:
            user_info = f"{chat_session.user.first_name} {chat_session.user.last_name} ({chat_session.user.email})"
        elif chat_session.user_email:
            user_info = f"Guest ({chat_session.user_email})"
        
        guest_name = getattr(chat_session, 'guest_name', 'Unknown')
        if hasattr(chat_session, 'session') and hasattr(chat_session.session, 'get'):
            # This would be the Django session, but we don't have direct access here
            # We'll use the session_id to indicate guest status
            pass
        
        email_subject = f"🚨 Chatbot Escalation Alert - Customer Needs Help"
        email_body = f"""
CHATBOT ESCALATION NOTIFICATION

A customer conversation has been escalated and requires human assistance.

SESSION DETAILS:
• Session ID: {chat_session.session_id}
• User: {user_info}
• Channel: {chat_session.channel.title()}
• Started: {chat_session.created_at.strftime('%Y-%m-%d %H:%M:%S')}
• Escalation Reason: {reason}

CONTACT INFORMATION:
• Phone: {chat_session.user_phone or 'Not provided'}
• Email: {chat_session.user_email or 'Not provided'}
• IP Address: {chat_session.user_ip or 'Unknown'}

💬 CONVERSATION HISTORY:
{chr(10).join(conversation_history) if conversation_history else 'No messages yet'}

🎯 NEXT ACTIONS:
1. Review the conversation above
2. Contact the customer if contact info is available
3. Follow up on their specific concerns
4. Mark as resolved in the admin panel when complete

⏰ This escalation was created at: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

---
Riverway Company Chatbot System
        """.strip()
        
        # Send email using Django's send_mail
        send_mail(
            subject=email_subject,
            message=email_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.CHATBOT_EMAIL],
            fail_silently=False,
        )
        
        logger.info(f"Chat session {chat_session.session_id} escalated and email sent to {settings.CHATBOT_EMAIL}")
        
        # Also create notification in database for backup
        create_notification(
            notification_type='escalation',
            channel='email',
            recipient=settings.CHATBOT_EMAIL,
            subject=email_subject,
            message=f'Chat escalated - {reason}',
            session=chat_session
        )
        
    except Exception as e:
        logger.error(f"Error escalating chat session or sending email: {e}")
        # Try to still create the escalation queue entry even if email fails
        try:
            EscalationQueue.objects.get_or_create(
                session=chat_session,
                defaults={'priority': 'high', 'notes': f'EMAIL FAILED: {reason}'}
            )
        except:
            pass


def send_chat_notification(chat_session, message):
    """Send chat notification"""
    try:
        settings = ChatbotSettings.objects.first()
        if not settings or not settings.enable_notifications:
            return
        
        recipient = chat_session.user_email or 'info.riverwayco@gmail.com'
        
        create_notification(
            notification_type='order_status',
            channel='email',
            recipient=recipient,
            subject='Riverway Chatbot Update',
            message=message,
            session=chat_session
        )
        
    except Exception as e:
        logger.error(f"Error sending chat notification: {e}")


def create_notification(notification_type, channel, recipient, subject, message, session=None, user=None):
    """Create a notification"""
    try:
        Notification.objects.create(
            user=user,
            session=session,
            notification_type=notification_type,
            channel=channel,
            recipient=recipient,
            subject=subject,
            message=message
        )
    except Exception as e:
        logger.error(f"Error creating notification: {e}")


@csrf_exempt
@require_http_methods(["POST"])
def submit_feedback(request):
    """Submit chat feedback"""
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        rating = data.get('rating')
        feedback_text = data.get('feedback', '')
        suggestions = data.get('suggestions', '')
        was_helpful = data.get('was_helpful')
        
        if not session_id or not rating:
            return JsonResponse({
                'status': 'error',
                'message': 'Session ID and rating are required'
            })
        
        chat_session = get_object_or_404(ChatSession, session_id=session_id)
        
        feedback, created = ChatFeedback.objects.get_or_create(
            session=chat_session,
            defaults={
                'rating': rating,
                'feedback_text': feedback_text,
                'suggestions': suggestions,
                'was_helpful': was_helpful
            }
        )
        
        if not created:
            feedback.rating = rating
            feedback.feedback_text = feedback_text
            feedback.suggestions = suggestions
            feedback.was_helpful = was_helpful
            feedback.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Thank you for your feedback!'
        })
        
    except Exception as e:
        logger.error(f"Feedback submission error: {e}")
        return JsonResponse({
            'status': 'error',
            'message': 'Failed to submit feedback'
        })


@require_http_methods(["GET"])
def chat_history(request, session_id):
    """Get chat history for a session"""
    try:
        chat_session = get_object_or_404(ChatSession, session_id=session_id)
        
        # Check if user has permission to view this chat
        if chat_session.user and chat_session.user != request.user:
            return JsonResponse({
                'status': 'error',
                'message': 'Permission denied'
            })
        
        messages = ChatMessage.objects.filter(session=chat_session).order_by('timestamp')
        
        messages_data = [{
            'id': msg.id,
            'type': msg.message_type,
            'content': msg.content,
            'timestamp': msg.timestamp.isoformat(),
            'intent': msg.intent,
            'confidence': msg.confidence_score
        } for msg in messages]
        
        return JsonResponse({
            'status': 'success',
            'session_id': session_id,
            'messages': messages_data,
            'session_info': {
                'created_at': chat_session.created_at.isoformat(),
                'channel': chat_session.channel,
                'status': chat_session.status,
                'is_escalated': chat_session.is_escalated
            }
        })
        
    except Exception as e:
        logger.error(f"Chat history error: {e}")
        return JsonResponse({
            'status': 'error',
            'message': 'Failed to retrieve chat history'
        })


@require_http_methods(["GET"])
def chatbot_widget(request):
    """Render chatbot widget"""
    settings = ChatbotSettings.objects.first()
    context = {
        'settings': settings,
        'session_id': request.session.get('chat_session_id', str(uuid.uuid4()))
    }
    return render(request, 'chatbot/widget.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def webhook_whatsapp(request):
    """WhatsApp webhook endpoint"""
    try:
        data = json.loads(request.body)
        # Process WhatsApp webhook
        # This would integrate with WhatsApp Business API
        
        phone_number = data.get('from', '')
        message = data.get('text', {}).get('body', '')
        
        if message and phone_number:
            # Create or get chat session for WhatsApp
            session_id = f"whatsapp_{phone_number}"
            
            chat_session, created = ChatSession.objects.get_or_create(
                session_id=session_id,
                defaults={
                    'channel': 'whatsapp',
                    'user_phone': phone_number,
                    'status': 'active'
                }
            )
            
            # Save user message
            ChatMessage.objects.create(
                session=chat_session,
                message_type='user',
                content=message
            )
            
            # Generate response with WhatsApp context
            user_context = {'phone': phone_number, 'channel': 'whatsapp'}
            response_data = chatbot_engine.generate_response(message, session_id, user_context)
            
            # Save bot response
            ChatMessage.objects.create(
                session=chat_session,
                message_type='bot',
                content=response_data['message'],
                intent=response_data.get('intent', ''),
                confidence_score=response_data.get('confidence', 0.0)
            )
            
            # Send WhatsApp response (would use WhatsApp API)
            # This is a placeholder - actual implementation would send via WhatsApp
            
            return JsonResponse({'status': 'success'})
        
        return JsonResponse({'status': 'no_message'})
        
    except Exception as e:
        logger.error(f"WhatsApp webhook error: {e}")
        return JsonResponse({'status': 'error'})


@csrf_exempt
@require_http_methods(["POST"])
def webhook_messenger(request):
    """Facebook Messenger webhook endpoint"""
    try:
        data = json.loads(request.body)
        # Process Messenger webhook
        # This would integrate with Facebook Messenger API
        
        entries = data.get('entry', [])
        for entry in entries:
            messaging = entry.get('messaging', [])
            for message_event in messaging:
                sender_id = message_event.get('sender', {}).get('id')
                message = message_event.get('message', {}).get('text', '')
                
                if message and sender_id:
                    # Create or get chat session for Messenger
                    session_id = f"messenger_{sender_id}"
                    
                    chat_session, created = ChatSession.objects.get_or_create(
                        session_id=session_id,
                        defaults={
                            'channel': 'messenger',
                            'status': 'active'
                        }
                    )
                    
                    # Save user message
                    ChatMessage.objects.create(
                        session=chat_session,
                        message_type='user',
                        content=message
                    )
                    
                    # Generate response with Messenger context
                    user_context = {'messenger_id': sender_id, 'channel': 'messenger'}
                    response_data = chatbot_engine.generate_response(message, session_id, user_context)
                    
                    # Save bot response
                    ChatMessage.objects.create(
                        session=chat_session,
                        message_type='bot',
                        content=response_data['message'],
                        intent=response_data.get('intent', ''),
                        confidence_score=response_data.get('confidence', 0.0)
                    )
                    
                    # Send Messenger response (would use Facebook API)
                    # This is a placeholder - actual implementation would send via Messenger
        
        return JsonResponse({'status': 'success'})
        
    except Exception as e:
        logger.error(f"Messenger webhook error: {e}")
        return JsonResponse({'status': 'error'})


@require_http_methods(["GET"])
def analytics_data(request):
    """Get chatbot analytics data"""
    try:
        # Check if user has permission (admin only)
        if not request.user.is_staff:
            return JsonResponse({
                'status': 'error',
                'message': 'Permission denied'
            })
        
        # Get date range from query parameters
        days = int(request.GET.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Basic metrics
        total_sessions = ChatSession.objects.filter(
            created_at__date__range=[start_date, end_date]
        ).count()
        
        escalated_sessions = ChatSession.objects.filter(
            created_at__date__range=[start_date, end_date],
            is_escalated=True
        ).count()
        
        # Average ratings
        avg_rating = ChatFeedback.objects.filter(
            created_at__date__range=[start_date, end_date]
        ).aggregate(Avg('rating'))['rating__avg'] or 0
        
        # Channel breakdown
        channel_stats = ChatSession.objects.filter(
            created_at__date__range=[start_date, end_date]
        ).values('channel').annotate(count=Count('id'))
        
        # Intent breakdown
        intent_stats = ChatMessage.objects.filter(
            timestamp__date__range=[start_date, end_date],
            message_type='bot',
            intent__isnull=False
        ).exclude(intent='').values('intent').annotate(count=Count('id'))[:10]
        
        # Average response time
        avg_response_time = ChatMessage.objects.filter(
            timestamp__date__range=[start_date, end_date],
            message_type='bot',
            response_time__isnull=False
        ).aggregate(Avg('response_time'))['response_time__avg'] or 0
        
        return JsonResponse({
            'status': 'success',
            'data': {
                'total_sessions': total_sessions,
                'escalated_sessions': escalated_sessions,
                'escalation_rate': round((escalated_sessions / total_sessions * 100) if total_sessions > 0 else 0, 2),
                'average_rating': round(avg_rating, 2),
                'average_response_time': round(avg_response_time, 3),
                'channel_stats': list(channel_stats),
                'intent_stats': list(intent_stats),
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Analytics data error: {e}")
        return JsonResponse({
            'status': 'error',
            'message': 'Failed to retrieve analytics data'
        })


@csrf_exempt
@require_http_methods(["POST"])
def contact_support(request):
    """Handle contact support form submissions"""
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        priority = data.get('priority', '').strip()
        description = data.get('description', '').strip()
        
        # Validate required fields
        if not all([name, email, priority, description]):
            return JsonResponse({
                'status': 'error',
                'message': 'All fields are required'
            })
        
        # Validate email format
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            return JsonResponse({
                'status': 'error',
                'message': 'Please enter a valid email address'
            })
        
        # Send professional email
        subject = f"Support Request - {priority} Priority"
        
        # Create professional email content
        email_content = f"""
Dear Support Team,

A new support request has been submitted through the website chatbot contact form.

CUSTOMER DETAILS:
Name: {name}
Email: {email}
Priority Level: {priority}

ISSUE DESCRIPTION:
{description}

REQUEST DETAILS:
Submitted: {timezone.now().strftime('%B %d, %Y at %I:%M %p UTC')}
Source: Website Chatbot Contact Form
Status: New Request

Please respond to the customer within 24 hours for standard requests, or immediately for high/critical priority issues.

Best regards,
Riverway Chatbot System
        """.strip()
        
        try:
            send_mail(
                subject=subject,
                message=email_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.CHATBOT_EMAIL],
                fail_silently=False,
            )
            
            logger.info(f"Contact support email sent for {email} - Priority: {priority}")
            
            return JsonResponse({
                'status': 'success',
                'message': 'Support request sent successfully'
            })
            
        except Exception as email_error:
            logger.error(f"Failed to send contact support email: {email_error}")
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to send support request. Please try again.'
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid request format'
        })
    except Exception as e:
        logger.error(f"Contact support error: {e}")
        return JsonResponse({
            'status': 'error',
            'message': 'An error occurred while processing your request'
        })
