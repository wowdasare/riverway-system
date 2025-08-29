# Chatbot Email Escalation System

This document describes the email escalation functionality implemented for the Riverway Chatbot system.

## Overview

The chatbot automatically sends email notifications when customers need to be escalated to human agents. This ensures no customer inquiry goes unnoticed and provides a seamless transition from automated to human support.

## Email Configuration

The system is configured to send emails through Gmail SMTP:

- **Host**: smtp.gmail.com
- **Port**: 465 (SSL)
- **Email**: info.riverwayco@gmail.com
- **Backend**: Custom SSLEmailBackend (bypasses SSL verification for development)

## Escalation Triggers

Emails are automatically sent when the chatbot detects:

1. Customer complaints or dissatisfaction
2. Multiple failed attempts to help the customer
3. Explicit requests for human assistance
4. Keywords indicating frustration: "complaint", "complain", "dissatisfied", "unhappy", "frustrated", "speak to human", etc.

## Email Content

Each escalation email includes:

- **Subject**: "Chatbot Escalation - Customer Needs Assistance"
- **Customer Details**: Name (if provided), session ID, timestamp
- **Full Conversation History**: Complete chat transcript
- **Context**: Reason for escalation and customer sentiment
- **Session Information**: Session duration and message count

## Technical Implementation

### Files Modified

1. **chatbot/views.py**: Added escalation logic and email sending functionality
2. **chatbot/nlp_engine.py**: Enhanced to detect escalation scenarios
3. **riverway/settings.py**: Email configuration
4. **chatbot/email_backend.py**: Custom SSL backend for development

### Key Functions

```python
def send_escalation_email(user_name, conversation_history, session_id):
    # Sends detailed escalation email with full context
    
def should_escalate(self, message, context):
    # Determines if conversation should be escalated
```

## Testing

The system has been tested with various escalation scenarios:
- Direct complaints
- Frustration expressions
- Human agent requests
- Failed product inquiries

## Monitoring

Escalation emails are sent to: **info.riverwayco@gmail.com**

Staff should monitor this email for urgent customer inquiries requiring human intervention.

## Development Notes

- Uses custom SSLEmailBackend to handle macOS SSL certificate issues
- All conversation history is preserved in escalation emails
- System maintains session context across escalations
- Email timeout set to 30 seconds for reliability