from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import time
from chatbot.models import (
    BusinessHours, CompanyInfo, FAQ, Intent, ChatbotSettings
)


class Command(BaseCommand):
    help = 'Setup initial chatbot data'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up Riverway Chatbot...'))

        # Create or update business hours
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        business_hours = {
            'monday': (time(7, 0), time(18, 0)),
            'tuesday': (time(7, 0), time(18, 0)),
            'wednesday': (time(7, 0), time(18, 0)),
            'thursday': (time(7, 0), time(18, 0)),
            'friday': (time(7, 0), time(18, 0)),
            'saturday': (time(8, 0), time(16, 0)),
            'sunday': (None, None)  # Closed
        }

        for day in days:
            hours_data = business_hours[day]
            if hours_data[0] is None:  # Closed day
                BusinessHours.objects.update_or_create(
                    day=day,
                    defaults={
                        'is_closed': True,
                        'open_time': None,
                        'close_time': None
                    }
                )
            else:
                BusinessHours.objects.update_or_create(
                    day=day,
                    defaults={
                        'is_closed': False,
                        'open_time': hours_data[0],
                        'close_time': hours_data[1]
                    }
                )

        self.stdout.write('✓ Business hours configured')

        # Create or update company info
        CompanyInfo.objects.update_or_create(
            id=1,
            defaults={
                'name': 'Riverway Company Limited',
                'address': 'Accra Technical University, Barnes Road, Tudu, Accra',
                'phone': '+233 55 845 9119',
                'email': 'info.riverwayco@gmail.com',
                'website': 'https://www.riverwayco.com',
                'description': 'Riverway Company Limited is your trusted partner in construction and building materials. We provide high-quality materials, expert advice, and exceptional service to contractors, builders, and DIY enthusiasts.',
                'services': '''• Hardware Products Supply
• Concrete & Masonry Products
• Lumber & Wood Products
• Hardware & Fasteners
• Tools & Equipment Rental
• Delivery Services
• Project Planning Assistance
• Volume Discounts for Contractors''',
                'pricing_info': '''We offer competitive pricing on all our products with:
• Volume discounts for large orders
• Contractor pricing available
• Free delivery on orders over $500
• Price matching on equivalent products
• Special rates for repeat customers

Contact us for detailed quotes and current pricing.'''
            }
        )

        self.stdout.write('✓ Company information configured')

        # Create intents
        intents_data = [
            {
                'name': 'greeting',
                'description': 'User greetings and conversation starters',
                'keywords': 'hello, hi, hey, good morning, good afternoon, good evening, greetings',
                'response_template': 'Hello! Welcome to Riverway Company Limited. How can I help you today?'
            },
            {
                'name': 'business_hours',
                'description': 'Questions about business hours and operating times',
                'keywords': 'hours, open, close, when, time, operating hours, business hours',
                'response_template': 'Our business hours are Monday-Friday 7:00 AM - 6:00 PM, Saturday 8:00 AM - 4:00 PM, and closed on Sunday.'
            },
            {
                'name': 'location',
                'description': 'Questions about company location and address',
                'keywords': 'where, location, address, directions, find you, located',
                'response_template': 'We are located at Accra Technical University, Barnes Road, Tudu, Accra. You can find us easily with GPS navigation.'
            },
            {
                'name': 'services',
                'description': 'Questions about services and products offered',
                'keywords': 'services, products, what do you do, construction, materials, supplies',
                'response_template': 'We offer hardware products, automotive supplies, paints & coatings, lighting & electrical products, tools, equipment rental, and delivery services.'
            },
            {
                'name': 'pricing',
                'description': 'Questions about pricing and quotes',
                'keywords': 'price, cost, pricing, how much, rates, quote, estimate, expensive, cheap',
                'response_template': 'We offer competitive pricing with volume discounts. Contact us for detailed quotes and current pricing on specific products.'
            },
            {
                'name': 'contact',
                'description': 'Requests for contact information',
                'keywords': 'contact, phone, email, call, reach, get in touch',
                'response_template': 'You can reach us at +233 55 845 9119, email us at info.riverwayco@gmail.com, or visit us at Accra Technical University, Barnes Road, Tudu, Accra.'
            },
            {
                'name': 'complaint',
                'description': 'Customer complaints and issues',
                'keywords': 'complaint, problem, issue, wrong, error, bad, terrible, dissatisfied, unhappy',
                'response_template': 'I apologize for any inconvenience. Let me connect you with our customer service team to resolve this issue.'
            },
            {
                'name': 'booking',
                'description': 'Appointment scheduling and bookings',
                'keywords': 'book, schedule, appointment, reservation, arrange, when can you',
                'response_template': 'I can help you schedule an appointment. Let me connect you with our scheduling team.'
            },
            {
                'name': 'order_tracking',
                'description': 'Order status and tracking inquiries',
                'keywords': 'order, track, delivery, shipment, status, where is my',
                'response_template': 'I can help you track your order. Please provide your order number or let me connect you with our order department.'
            }
        ]

        for intent_data in intents_data:
            Intent.objects.update_or_create(
                name=intent_data['name'],
                defaults=intent_data
            )

        self.stdout.write('✓ Intents configured')

        # Create FAQs
        faqs_data = [
            {
                'question': 'What are your business hours?',
                'answer': 'We are open Monday through Friday from 7:00 AM to 6:00 PM, and Saturday from 8:00 AM to 4:00 PM. We are closed on Sundays.',
                'category': 'location',
                'keywords': 'hours, open, close, time, when, operating, business hours'
            },
            {
                'question': 'Where are you located?',
                'answer': 'We are located at Accra Technical University, Barnes Road, Tudu, Accra. We have ample parking and easy loading access for your convenience.',
                'category': 'location',
                'keywords': 'location, address, where, directions, find, located'
            },
            {
                'question': 'Do you offer delivery services?',
                'answer': 'Yes! We offer local delivery within 50 miles. Delivery is free on orders over $500. Same-day and scheduled delivery options are available.',
                'category': 'services',
                'keywords': 'delivery, deliver, shipping, transport, free delivery'
            },
            {
                'question': 'Do you have contractor discounts?',
                'answer': 'Yes, we offer special contractor pricing and volume discounts. Please bring your contractor license or business registration to set up an account.',
                'category': 'pricing',
                'keywords': 'contractor, discount, wholesale, bulk, volume, business account'
            },
            {
                'question': 'Can you help with project planning?',
                'answer': 'Absolutely! Our experienced staff can help with material takeoffs, quantity calculations, and project planning. We offer free consultations for projects.',
                'category': 'services',
                'keywords': 'project planning, consultation, takeoff, calculate, help, advice'
            },
            {
                'question': 'Do you rent tools and equipment?',
                'answer': 'Yes, we have a full range of construction tools and equipment available for rent by the day, week, or month. Call us for availability and rates.',
                'category': 'services',
                'keywords': 'rent, rental, tools, equipment, borrow, lease'
            },
            {
                'question': 'How can I get a quote?',
                'answer': 'You can get a quote by calling us at +233 55 845 9119, emailing info.riverwayco@gmail.com, or visiting our store. We provide detailed quotes for all projects.',
                'category': 'pricing',
                'keywords': 'quote, estimate, pricing, price, cost, how much'
            },
            {
                'question': 'Do you match prices?',
                'answer': 'Yes, we offer price matching on equivalent products from authorized dealers. Bring us the competitor\'s current advertised price and we\'ll match it.',
                'category': 'pricing',
                'keywords': 'price match, competitive, lowest price, beat price, match'
            },
            {
                'question': 'What payment methods do you accept?',
                'answer': 'We accept cash, all major credit cards, debit cards, checks, and offer financing options for larger purchases. We also provide NET 30 terms for established business accounts.',
                'category': 'general',
                'keywords': 'payment, pay, credit card, cash, check, financing, terms'
            },
            {
                'question': 'Do you have an online catalog?',
                'answer': 'Yes, you can browse our products online at www.riverwayco.com. For the most current inventory and pricing, we recommend calling or visiting our store.',
                'category': 'general',
                'keywords': 'catalog, online, website, browse, products, inventory'
            }
        ]

        for faq_data in faqs_data:
            FAQ.objects.update_or_create(
                question=faq_data['question'],
                defaults=faq_data
            )

        self.stdout.write('✓ FAQs configured')

        # Create chatbot settings
        ChatbotSettings.objects.update_or_create(
            id=1,
            defaults={
                'welcome_message': 'Welcome to Riverway Company!\nHow can I help you today?',
                'fallback_message': 'I am not sure I understand that question. Let me connect you with one of our knowledgeable team members who can help you better.',
                'escalation_threshold': 3,
                'response_delay': 1.0,
                'working_hours_message': 'Thank you for contacting Riverway Company. We are currently outside our business hours (Monday-Friday 7:00 AM - 6:00 PM, Saturday 8:00 AM - 4:00 PM). Your message is important to us, and we\'ll respond when we return. For urgent matters, please call +233 55 845 9119.',
                'max_session_duration': 3600,
                'enable_analytics': True,
                'enable_feedback': True,
                'enable_notifications': True
            }
        )

        self.stdout.write('✓ Chatbot settings configured')

        self.stdout.write(
            self.style.SUCCESS(
                '\n🎉 Riverway Chatbot setup complete!\n'
                '\nNext steps:\n'
                '1. Visit /admin/ to customize settings and add more FAQs\n'
                '2. Access the chatbot at /chatbot/widget/\n'
                '3. Add the embedded widget to your website templates\n'
                '4. Monitor analytics and user feedback in the admin panel\n'
            )
        )