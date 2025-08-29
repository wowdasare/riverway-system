from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Count, Sum, Q, Avg
from django.core.paginator import Paginator
from django.http import JsonResponse
from store.models import Product, Category, Order, OrderItem
from chatbot.models import ChatSession, FAQ, BusinessHours, CompanyInfo, ChatMessage, ChatFeedback
from django.utils import timezone
from datetime import datetime, timedelta
import json


@staff_member_required
def dashboard_home(request):
    """Admin dashboard home with key metrics"""
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Calculate key metrics
    total_products = Product.objects.filter(is_active=True).count()
    total_orders = Order.objects.count()
    total_revenue = Order.objects.aggregate(total=Sum('total_amount'))['total'] or 0
    recent_orders = Order.objects.filter(created_at__date=today).count()
    
    # Weekly stats
    weekly_orders = Order.objects.filter(created_at__date__gte=week_ago).count()
    weekly_revenue = Order.objects.filter(created_at__date__gte=week_ago).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Low stock products
    low_stock_products = Product.objects.filter(stock_quantity__lte=10, is_active=True)[:5]
    
    # Recent products
    recent_products = Product.objects.filter(is_active=True).order_by('-created_at')[:6]
    
    # Top categories with product counts
    top_categories = Category.objects.annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    ).order_by('-product_count')[:6]
    
    # Total categories count
    total_categories = Category.objects.count()
    
    # Recent orders
    recent_orders_list = Order.objects.select_related('user').order_by('-created_at')[:5]
    
    # Chat sessions today
    chat_sessions_today = ChatSession.objects.filter(created_at__date=today).count()
    
    # Enhanced Analytics Data
    # Product distribution by category (for pie chart)
    category_distribution = list(Category.objects.annotate(
        product_count=Count('products', filter=Q(products__is_active=True)),
        revenue=Sum('products__orderitem__price', filter=Q(products__orderitem__order__status='delivered'))
    ).filter(product_count__gt=0).values('name', 'product_count', 'revenue'))
    
    # Order status distribution (for pie chart)
    order_status_data = list(Order.objects.values('status').annotate(count=Count('id')))
    
    # Revenue by month (last 6 months)
    six_months_ago = today - timedelta(days=180)
    monthly_revenue = []
    for i in range(6):
        month_start = six_months_ago + timedelta(days=30*i)
        month_end = month_start + timedelta(days=30)
        revenue = Order.objects.filter(
            created_at__date__range=[month_start, month_end],
            status='delivered'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        monthly_revenue.append({
            'month': month_start.strftime('%b %Y'),
            'revenue': float(revenue)
        })
    
    # Top selling products
    top_products = Product.objects.annotate(
        total_sold=Sum('orderitem__quantity', filter=Q(orderitem__order__status='delivered'))
    ).filter(total_sold__gt=0).order_by('-total_sold')[:5]
    
    # Chatbot analytics
    total_chat_sessions = ChatSession.objects.count()
    escalated_chats = ChatSession.objects.filter(is_escalated=True).count()
    chat_satisfaction = ChatFeedback.objects.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0
    
    # Recent chat activity (last 7 days)
    chat_activity = []
    for i in range(7):
        day = today - timedelta(days=6-i)
        sessions = ChatSession.objects.filter(created_at__date=day).count()
        chat_activity.append({
            'date': day.strftime('%m/%d'),
            'sessions': sessions
        })
    
    # Most common intents from chatbot
    common_intents = list(ChatMessage.objects.exclude(intent='').values('intent').annotate(
        count=Count('id')
    ).order_by('-count')[:5])
    
    context = {
        'total_products': total_products,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'recent_orders_count': recent_orders,
        'weekly_orders': weekly_orders,
        'weekly_revenue': weekly_revenue,
        'low_stock_products': low_stock_products,
        'recent_products': recent_products,
        'top_categories': top_categories,
        'total_categories': total_categories,
        'recent_orders_list': recent_orders_list,
        'chat_sessions_today': chat_sessions_today,
        
        # Enhanced Analytics
        'category_distribution': json.dumps(category_distribution, cls=DjangoJSONEncoder),
        'order_status_data': json.dumps(order_status_data),
        'monthly_revenue': json.dumps(monthly_revenue),
        'top_products': top_products,
        'total_chat_sessions': total_chat_sessions,
        'escalated_chats': escalated_chats,
        'chat_satisfaction': round(chat_satisfaction, 1),
        'chat_activity': json.dumps(chat_activity),
        'common_intents': json.dumps(common_intents),
    }
    
    return render(request, 'admin_dashboard/home.html', context)


@staff_member_required
def product_list(request):
    """List all products with search and filter"""
    products = Product.objects.select_related('category').order_by('-created_at')
    categories = Category.objects.all()
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(sku__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Filter by category
    category_id = request.GET.get('category', '')
    if category_id:
        products = products.filter(category_id=category_id)
    
    # Filter by status
    status = request.GET.get('status', '')
    if status == 'active':
        products = products.filter(is_active=True)
    elif status == 'inactive':
        products = products.filter(is_active=False)
    elif status == 'low_stock':
        products = products.filter(stock_quantity__lte=10)
    
    # Pagination
    paginator = Paginator(products, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'search_query': search_query,
        'selected_category': category_id,
        'selected_status': status,
    }
    
    return render(request, 'admin_dashboard/product_list.html', context)


@staff_member_required
def product_create(request):
    """Create a new product"""
    if request.method == 'POST':
        try:
            product = Product.objects.create(
                name=request.POST.get('name'),
                category_id=request.POST.get('category'),
                description=request.POST.get('description'),
                price=request.POST.get('price'),
                unit=request.POST.get('unit'),
                sku=request.POST.get('sku'),
                stock_quantity=request.POST.get('stock_quantity', 0),
                is_active=request.POST.get('is_active') == 'on'
            )
            
            if request.FILES.get('image'):
                product.image = request.FILES['image']
                product.save()
            
            messages.success(request, f'Product "{product.name}" created successfully!')
            return redirect('admin_dashboard:product_list')
        except Exception as e:
            messages.error(request, f'Error creating product: {str(e)}')
    
    categories = Category.objects.all()
    return render(request, 'admin_dashboard/product_form.html', {'categories': categories})


@staff_member_required
def product_edit(request, pk):
    """Edit an existing product"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        try:
            product.name = request.POST.get('name')
            product.category_id = request.POST.get('category')
            product.description = request.POST.get('description')
            product.price = request.POST.get('price')
            product.unit = request.POST.get('unit')
            product.sku = request.POST.get('sku')
            product.stock_quantity = request.POST.get('stock_quantity', 0)
            product.is_active = request.POST.get('is_active') == 'on'
            
            if request.FILES.get('image'):
                product.image = request.FILES['image']
            
            product.save()
            messages.success(request, f'Product "{product.name}" updated successfully!')
            return redirect('admin_dashboard:product_list')
        except Exception as e:
            messages.error(request, f'Error updating product: {str(e)}')
    
    categories = Category.objects.all()
    return render(request, 'admin_dashboard/product_form.html', {
        'product': product,
        'categories': categories
    })


@staff_member_required
def product_delete(request, pk):
    """Delete a product"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        product_name = product.name
        product.delete()
        messages.success(request, f'Product "{product_name}" deleted successfully!')
        return redirect('admin_dashboard:product_list')
    
    return render(request, 'admin_dashboard/product_confirm_delete.html', {'product': product})


@staff_member_required
def order_list(request):
    """List all orders"""
    orders = Order.objects.select_related('user').order_by('-created_at')
    
    # Filter by status
    status = request.GET.get('status', '')
    if status:
        orders = orders.filter(status=status)
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        orders = orders.filter(
            Q(id__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(user__username__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'selected_status': status,
        'search_query': search_query,
        'status_choices': Order.STATUS_CHOICES,
    }
    
    return render(request, 'admin_dashboard/order_list.html', context)


@staff_member_required
def order_detail(request, pk):
    """View order details"""
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), pk=pk)
    
    if request.method == 'POST':
        # Update order status
        new_status = request.POST.get('status')
        if new_status and new_status != order.status:
            order.status = new_status
            order.save()
            messages.success(request, f'Order status updated to {order.get_status_display()}')
    
    return render(request, 'admin_dashboard/order_detail.html', {
        'order': order,
        'status_choices': Order.STATUS_CHOICES,
    })


@staff_member_required
def category_list(request):
    """List all categories"""
    categories = Category.objects.annotate(product_count=Count('products')).order_by('name')
    return render(request, 'admin_dashboard/category_list.html', {'categories': categories})


@staff_member_required
def category_create(request):
    """Create a new category"""
    if request.method == 'POST':
        try:
            category = Category.objects.create(
                name=request.POST.get('name'),
                description=request.POST.get('description', '')
            )
            
            if request.FILES.get('image'):
                category.image = request.FILES['image']
                category.save()
            
            messages.success(request, f'Category "{category.name}" created successfully!')
            return redirect('admin_dashboard:category_list')
        except Exception as e:
            messages.error(request, f'Error creating category: {str(e)}')
    
    return render(request, 'admin_dashboard/category_form.html')


@staff_member_required
def category_edit(request, pk):
    """Edit a category"""
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        try:
            category.name = request.POST.get('name')
            category.description = request.POST.get('description', '')
            
            if request.FILES.get('image'):
                category.image = request.FILES['image']
            
            category.save()
            messages.success(request, f'Category "{category.name}" updated successfully!')
            return redirect('admin_dashboard:category_list')
        except Exception as e:
            messages.error(request, f'Error updating category: {str(e)}')
    
    return render(request, 'admin_dashboard/category_form.html', {'category': category})


@staff_member_required
def chatbot_settings(request):
    """Manage chatbot settings and FAQ configuration"""
    faqs = FAQ.objects.all().order_by('-created_at')
    business_hours = BusinessHours.objects.all()
    company_info = CompanyInfo.objects.first()
    
    # Default company info if none exists
    if not company_info:
        company_info = CompanyInfo(
            name='Riverway Company Limited',
            address='Accra, Ghana',
            phone='',
            email='info@riverway.com',
            website='',
            description='Your trusted partner for hardware, automotive, and construction supplies since 2006. We provide quality products at affordable prices with excellent customer service.'
        )
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_faq':
            question = request.POST.get('question', '').strip()
            answer = request.POST.get('answer', '').strip()
            category = request.POST.get('category', '').strip()
            
            if question and answer:
                FAQ.objects.create(
                    question=question,
                    answer=answer,
                    category=category,
                    is_active=request.POST.get('is_active') == 'on'
                )
                messages.success(request, f'FAQ "{question[:50]}..." added successfully!')
            else:
                messages.error(request, 'Question and answer are required.')
        
        elif action == 'delete_faq':
            faq_id = request.POST.get('faq_id')
            try:
                faq = FAQ.objects.get(id=faq_id)
                messages.success(request, f'FAQ "{faq.question[:30]}..." deleted successfully!')
                faq.delete()
            except FAQ.DoesNotExist:
                messages.error(request, 'FAQ not found.')
        
        elif action == 'toggle_faq':
            faq_id = request.POST.get('faq_id')
            try:
                faq = FAQ.objects.get(id=faq_id)
                faq.is_active = not faq.is_active
                faq.save()
                status = 'activated' if faq.is_active else 'deactivated'
                messages.success(request, f'FAQ "{faq.question[:30]}..." {status} successfully!')
            except FAQ.DoesNotExist:
                messages.error(request, 'FAQ not found.')
        
        elif action == 'update_company_info':
            name = request.POST.get('name', '').strip()
            address = request.POST.get('address', '').strip()
            phone = request.POST.get('phone', '').strip()
            email = request.POST.get('email', '').strip()
            website = request.POST.get('website', '').strip()
            description = request.POST.get('description', '').strip()
            
            if name:
                company_info_obj = CompanyInfo.objects.first()
                if company_info_obj:
                    company_info_obj.name = name
                    company_info_obj.address = address
                    company_info_obj.phone = phone
                    company_info_obj.email = email
                    company_info_obj.website = website
                    company_info_obj.description = description
                    company_info_obj.save()
                else:
                    CompanyInfo.objects.create(
                        name=name,
                        address=address,
                        phone=phone,
                        email=email,
                        website=website,
                        description=description
                    )
                messages.success(request, 'Company information updated successfully!')
            else:
                messages.error(request, 'Company name is required.')
        
        elif action == 'bulk_add_faqs':
            # Add default FAQs for Riverway
            default_faqs = [
                {
                    'question': 'What products do you sell?',
                    'answer': 'We offer a wide range of products including automotive supplies, construction materials, hardware tools, paints, batteries, tyres, and roofing materials. Visit our product catalog to see our full inventory.',
                    'category': 'Products'
                },
                {
                    'question': 'What are your business hours?',
                    'answer': 'We are open Monday to Saturday from 8:00 AM to 6:00 PM, and Sundays from 10:00 AM to 4:00 PM. For urgent needs, you can contact us through our 24/7 chatbot.',
                    'category': 'Business Hours'
                },
                {
                    'question': 'How can I place an order?',
                    'answer': 'You can place orders through our website by adding items to your cart and proceeding to checkout. You can also visit our physical store or contact us directly for assistance.',
                    'category': 'Orders'
                },
                {
                    'question': 'Do you offer delivery services?',
                    'answer': 'Yes, we offer delivery services within Accra and surrounding areas. Delivery fees and times vary based on location and order size. Contact us for specific delivery information.',
                    'category': 'Delivery'
                },
                {
                    'question': 'What payment methods do you accept?',
                    'answer': 'We accept cash, mobile money (MTN Mobile Money, AirtelTigo Money), bank transfers, and major credit/debit cards. Payment is required before delivery or pickup.',
                    'category': 'Payment'
                },
                {
                    'question': 'Do you offer bulk discounts?',
                    'answer': 'Yes, we offer competitive bulk pricing for large orders. Contact us with your requirements and we will provide a customized quote with special pricing.',
                    'category': 'Pricing'
                },
                {
                    'question': 'How can I check product availability?',
                    'answer': 'Product availability is shown on our website. You can also ask our chatbot about specific items or contact us directly. Stock levels are updated regularly.',
                    'category': 'Inventory'
                }
            ]
            
            added_count = 0
            for faq_data in default_faqs:
                # Check if FAQ with similar question already exists
                if not FAQ.objects.filter(question__icontains=faq_data['question'][:20]).exists():
                    FAQ.objects.create(
                        question=faq_data['question'],
                        answer=faq_data['answer'],
                        category=faq_data['category'],
                        is_active=True
                    )
                    added_count += 1
            
            if added_count > 0:
                messages.success(request, f'Added {added_count} default FAQs successfully!')
            else:
                messages.info(request, 'All default FAQs already exist.')
        
        return redirect('admin_dashboard:chatbot_settings')
    
    # FAQ statistics
    total_faqs = faqs.count()
    active_faqs = faqs.filter(is_active=True).count()
    faq_categories = faqs.values('category').annotate(count=Count('id')).exclude(category='')
    
    context = {
        'faqs': faqs,
        'business_hours': business_hours,
        'company_info': company_info,
        'total_faqs': total_faqs,
        'active_faqs': active_faqs,
        'faq_categories': faq_categories,
    }
    
    return render(request, 'admin_dashboard/chatbot_settings.html', context)


@staff_member_required
def analytics_api(request):
    """API endpoint for dashboard analytics data"""
    today = timezone.now().date()
    
    # Sales analytics
    daily_sales = []
    for i in range(30):
        day = today - timedelta(days=29-i)
        sales = Order.objects.filter(
            created_at__date=day,
            status='delivered'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        daily_sales.append({
            'date': day.strftime('%Y-%m-%d'),
            'sales': float(sales)
        })
    
    # Product performance
    product_performance = list(Product.objects.annotate(
        total_revenue=Sum('orderitem__price', filter=Q(orderitem__order__status='delivered')),
        total_sold=Sum('orderitem__quantity', filter=Q(orderitem__order__status='delivered'))
    ).filter(total_revenue__gt=0).order_by('-total_revenue')[:10].values(
        'name', 'total_revenue', 'total_sold', 'stock_quantity'
    ))
    
    # Customer insights
    customer_data = {
        'total_customers': Order.objects.values('user').distinct().count(),
        'repeat_customers': Order.objects.values('user').annotate(
            order_count=Count('id')
        ).filter(order_count__gt=1).count(),
    }
    
    # Chatbot performance
    chatbot_data = {
        'total_sessions': ChatSession.objects.count(),
        'escalation_rate': round(
            (ChatSession.objects.filter(is_escalated=True).count() / 
             max(ChatSession.objects.count(), 1)) * 100, 1
        ),
        'avg_satisfaction': round(
            ChatFeedback.objects.aggregate(avg=Avg('rating'))['avg'] or 0, 1
        ),
        'intent_distribution': list(ChatMessage.objects.exclude(intent='').values('intent').annotate(
            count=Count('id')
        ).order_by('-count')[:8])
    }
    
    return JsonResponse({
        'daily_sales': daily_sales,
        'product_performance': product_performance,
        'customer_data': customer_data,
        'chatbot_data': chatbot_data,
    })


@staff_member_required
def chatbot_analytics(request):
    """Dedicated chatbot analytics page with detailed insights"""
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Basic chatbot metrics
    total_sessions = ChatSession.objects.count()
    weekly_sessions = ChatSession.objects.filter(created_at__date__gte=week_ago).count()
    escalated_sessions = ChatSession.objects.filter(is_escalated=True).count()
    escalation_rate = round((escalated_sessions / max(total_sessions, 1)) * 100, 1)
    
    # Satisfaction metrics
    avg_satisfaction = ChatFeedback.objects.aggregate(avg=Avg('rating'))['avg'] or 0
    total_feedback = ChatFeedback.objects.count()
    
    # Channel distribution
    channel_stats = list(ChatSession.objects.values('channel').annotate(
        count=Count('id')
    ).order_by('-count'))
    
    # Intent analysis
    intent_stats = list(ChatMessage.objects.exclude(intent='').values('intent').annotate(
        count=Count('id')
    ).order_by('-count')[:10])
    
    # Hourly activity pattern (for heatmap)
    hourly_activity = []
    for hour in range(24):
        sessions = ChatSession.objects.filter(created_at__hour=hour).count()
        hourly_activity.append({
            'hour': f"{hour:02d}:00",
            'sessions': sessions
        })
    
    # Daily activity for last 30 days
    daily_activity = []
    for i in range(30):
        day = today - timedelta(days=29-i)
        sessions = ChatSession.objects.filter(created_at__date=day).count()
        escalated = ChatSession.objects.filter(
            created_at__date=day, is_escalated=True
        ).count()
        daily_activity.append({
            'date': day.strftime('%Y-%m-%d'),
            'sessions': sessions,
            'escalated': escalated,
            'success_rate': round(((sessions - escalated) / max(sessions, 1)) * 100, 1)
        })
    
    # Top FAQs
    top_faqs = FAQ.objects.filter(is_active=True).order_by('-view_count')[:10]
    
    # Resolution time analysis
    avg_response_time = ChatMessage.objects.filter(
        message_type='bot',
        response_time__isnull=False
    ).aggregate(avg=Avg('response_time'))['avg'] or 0
    
    # Recent escalations
    recent_escalations = ChatSession.objects.filter(
        is_escalated=True
    ).select_related('user').order_by('-created_at')[:10]
    
    context = {
        'total_sessions': total_sessions,
        'weekly_sessions': weekly_sessions,
        'escalated_sessions': escalated_sessions,
        'escalation_rate': escalation_rate,
        'avg_satisfaction': round(avg_satisfaction, 1),
        'total_feedback': total_feedback,
        'channel_stats': json.dumps(channel_stats),
        'intent_stats': json.dumps(intent_stats),
        'hourly_activity': json.dumps(hourly_activity),
        'daily_activity': json.dumps(daily_activity),
        'top_faqs': top_faqs,
        'avg_response_time': round(avg_response_time, 2),
        'recent_escalations': recent_escalations,
    }
    
    return render(request, 'admin_dashboard/chatbot_analytics.html', context)


@staff_member_required
def export_data(request):
    """Export dashboard data to CSV"""
    import csv
    from django.http import HttpResponse
    from datetime import datetime
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="dashboard_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    
    # Products data
    writer.writerow(['=== PRODUCTS DATA ==='])
    writer.writerow(['Name', 'Category', 'Price', 'Stock', 'SKU', 'Active'])
    for product in Product.objects.select_related('category').all():
        writer.writerow([
            product.name,
            product.category.name,
            product.price,
            product.stock_quantity,
            product.sku,
            'Yes' if product.is_active else 'No'
        ])
    
    writer.writerow([])  # Empty row
    
    # Orders data
    writer.writerow(['=== ORDERS DATA ==='])
    writer.writerow(['Order ID', 'Customer', 'Total Amount', 'Status', 'Date'])
    for order in Order.objects.select_related('user').all():
        writer.writerow([
            order.id,
            order.user.username if order.user else order.email,
            order.total_amount,
            order.get_status_display(),
            order.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    writer.writerow([])  # Empty row
    
    # Chatbot data
    writer.writerow(['=== CHATBOT DATA ==='])
    writer.writerow(['Session ID', 'User', 'Channel', 'Messages Count', 'Escalated', 'Date'])
    for session in ChatSession.objects.select_related('user').all()[:100]:  # Last 100 sessions
        message_count = session.messages.count()
        writer.writerow([
            session.session_id,
            session.user.username if session.user else 'Guest',
            session.channel,
            message_count,
            'Yes' if session.is_escalated else 'No',
            session.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    return response


@staff_member_required
def generate_report(request):
    """Generate comprehensive business report"""
    from django.http import HttpResponse
    from django.template.loader import render_to_string
    from datetime import datetime, timedelta
    import json
    
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Gather comprehensive data
    total_products = Product.objects.filter(is_active=True).count()
    total_orders = Order.objects.count()
    total_revenue = Order.objects.filter(status='delivered').aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    weekly_orders = Order.objects.filter(created_at__date__gte=week_ago).count()
    weekly_revenue = Order.objects.filter(
        created_at__date__gte=week_ago, status='delivered'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Top products
    top_products = Product.objects.annotate(
        total_sold=Sum('orderitem__quantity', filter=Q(orderitem__order__status='delivered'))
    ).filter(total_sold__gt=0).order_by('-total_sold')[:5]
    
    # Category performance
    category_performance = Category.objects.annotate(
        product_count=Count('products', filter=Q(products__is_active=True)),
        total_revenue=Sum('products__orderitem__price', 
                         filter=Q(products__orderitem__order__status='delivered'))
    ).order_by('-product_count')
    
    # Chatbot stats
    total_chat_sessions = ChatSession.objects.count()
    weekly_chat_sessions = ChatSession.objects.filter(created_at__date__gte=week_ago).count()
    escalated_chats = ChatSession.objects.filter(is_escalated=True).count()
    escalation_rate = round((escalated_chats / max(total_chat_sessions, 1)) * 100, 1)
    
    # Low stock alerts
    low_stock_products = Product.objects.filter(
        stock_quantity__lte=10, is_active=True
    ).order_by('stock_quantity')[:10]
    
    context = {
        'report_date': datetime.now(),
        'period': 'Last 30 Days',
        'total_products': total_products,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'weekly_orders': weekly_orders,
        'weekly_revenue': weekly_revenue,
        'top_products': top_products,
        'category_performance': category_performance,
        'total_chat_sessions': total_chat_sessions,
        'weekly_chat_sessions': weekly_chat_sessions,
        'escalation_rate': escalation_rate,
        'low_stock_products': low_stock_products,
    }
    
    # Generate HTML report
    html_content = render_to_string('admin_dashboard/business_report.html', context)
    
    response = HttpResponse(html_content, content_type='text/html')
    response['Content-Disposition'] = f'attachment; filename="business_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html"'
    
    return response
