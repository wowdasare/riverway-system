from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Product, Category, Cart, CartItem, Order, OrderItem
from .forms import CustomUserCreationForm, CustomAuthenticationForm
import json


def home(request):
    featured_products = Product.objects.filter(is_active=True)[:8]
    categories = Category.objects.all()[:6]
    cart = get_cart(request)
    return render(request, 'store/home.html', {
        'featured_products': featured_products,
        'categories': categories,
        'cart': cart
    })


def product_list(request):
    products = Product.objects.filter(is_active=True)
    categories = Category.objects.all()
    
    search_query = request.GET.get('search', '')
    category_id = request.GET.get('category', '')
    sort_by = request.GET.get('sort', 'featured')
    
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    if category_id:
        products = products.filter(category_id=category_id)
    
    # Apply sorting
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'name_az':
        products = products.order_by('name')
    elif sort_by == 'name_za':
        products = products.order_by('-name')
    else:  # featured (default)
        products = products.order_by('-created_at')
    
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    cart = get_cart(request)
    
    return render(request, 'store/product_list.html', {
        'page_obj': page_obj,
        'categories': categories,
        'search_query': search_query,
        'selected_category': category_id,
        'sort_by': sort_by,
        'cart': cart
    })


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    related_products = Product.objects.filter(
        category=product.category, is_active=True
    ).exclude(pk=pk)[:4]
    cart = get_cart(request)
    
    return render(request, 'store/product_detail.html', {
        'product': product,
        'related_products': related_products,
        'cart': cart
    })


def get_cart(request):
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)
    return cart


def add_to_cart(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, pk=product_id)
        
        try:
            quantity = int(request.POST.get('quantity', 1))
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
        except (ValueError, TypeError):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid quantity specified!'
                })
            messages.error(request, 'Invalid quantity specified!')
            return redirect('store:product_detail', pk=product_id)
        
        # Check if product is in stock
        if not product.is_in_stock:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': f'{product.name} is currently out of stock!'
                })
            messages.error(request, f'{product.name} is currently out of stock!')
            return redirect('store:product_detail', pk=product_id)
        
        # Check if requested quantity is available
        cart = get_cart(request)
        existing_cart_item = CartItem.objects.filter(cart=cart, product=product).first()
        current_quantity = existing_cart_item.quantity if existing_cart_item else 0
        
        if current_quantity + quantity > product.stock_quantity:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': f'Only {product.stock_quantity} items available in stock!'
                })
            messages.error(request, f'Only {product.stock_quantity} items available in stock!')
            return redirect('store:product_detail', pk=product_id)
        
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart, product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        # Check for AJAX request using headers instead of deprecated is_ajax()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'cart_total': cart.get_total_items()
            })
        
        messages.success(request, f'{product.name} added to cart!')
        return redirect('store:product_detail', pk=product_id)
    
    return redirect('store:product_list')


def cart_view(request):
    cart = get_cart(request)
    return render(request, 'store/cart.html', {'cart': cart})


def update_cart_item(request, item_id):
    if request.method == 'POST':
        cart_item = get_object_or_404(CartItem, pk=item_id)
        quantity = int(request.POST.get('quantity', 1))
        
        if quantity <= 0:
            cart_item.delete()
        else:
            cart_item.quantity = quantity
            cart_item.save()
        
        return redirect('store:cart')
    
    return redirect('store:cart')


def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, pk=item_id)
    cart_item.delete()
    messages.success(request, 'Item removed from cart!')
    return redirect('store:cart')


@login_required
def checkout(request):
    cart = get_cart(request)
    if not cart.items.exists():
        messages.error(request, 'Your cart is empty!')
        return redirect('store:cart')
    
    if request.method == 'POST':
        order = Order.objects.create(
            user=request.user,
            email=request.POST.get('email'),
            phone=request.POST.get('phone'),
            shipping_address=request.POST.get('shipping_address'),
            billing_address=request.POST.get('billing_address'),
            total_amount=cart.get_total_price()
        )
        
        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )
        
        cart.items.all().delete()
        messages.success(request, f'Order #{order.id} placed successfully!')
        return redirect('store:order_confirmation', order_id=order.id)
    
    return render(request, 'store/checkout.html', {'cart': cart})


@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    return render(request, 'store/order_confirmation.html', {'order': order})


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'store/order_history.html', {'orders': orders})


def user_login(request):
    if request.user.is_authenticated:
        return redirect('store:home')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                next_url = request.GET.get('next', 'store:home')
                welcome_name = user.get_full_name() if user.get_full_name() else user.username
                messages.success(request, f'🎉 Welcome back, {welcome_name}! You have been successfully logged in.')
                return redirect(next_url)
            else:
                messages.error(request, '❌ Invalid login credentials. Please check your username and password.')
        else:
            # Handle form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'❌ {error}')
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'store/auth/login.html', {'form': form})


def user_register(request):
    if request.user.is_authenticated:
        return redirect('store:home')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            
            # Automatically log in the user after registration
            authenticated_user = authenticate(username=username, password=password)
            if authenticated_user is not None:
                login(request, authenticated_user)
                full_name = user.get_full_name() if user.get_full_name() else username
                messages.success(request, f'🎉 Welcome to Riverway, {full_name}! Your account has been created and you are now logged in.')
                return redirect('store:home')
            else:
                # Fallback if auto-login fails
                full_name = user.get_full_name() if user.get_full_name() else username
                messages.success(request, f'🎉 Welcome to Riverway, {full_name}! Your account has been created successfully. Please log in to get started.')
                return redirect('store:login')
        else:
            # Handle form errors with detailed messages
            for field, errors in form.errors.items():
                field_name = form[field].label if hasattr(form[field], 'label') else field.replace('_', ' ').title()
                for error in errors:
                    messages.error(request, f'❌ {field_name}: {error}')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'store/auth/register.html', {'form': form})


@login_required
def user_logout(request):
    user_name = request.user.get_full_name() if request.user.get_full_name() else request.user.username
    logout(request)
    messages.success(request, f'👋 Goodbye, {user_name}! You have been successfully logged out. Come back soon!')
    return redirect('store:home')


def user_profile(request):
    return render(request, 'store/auth/profile.html')
