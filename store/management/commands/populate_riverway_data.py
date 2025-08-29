from django.core.management.base import BaseCommand
from django.db import transaction
from store.models import Category, Product


class Command(BaseCommand):
    help = 'Populate database with Riverway Company Limited products and categories'

    def handle(self, *args, **options):
        with transaction.atomic():
            # Clear existing data
            self.stdout.write(self.style.WARNING('Clearing existing products and categories...'))
            Product.objects.all().delete()
            Category.objects.all().delete()
            
            # Create categories
            self.stdout.write(self.style.SUCCESS('Creating categories...'))
            categories = [
                {
                    'name': 'Hardware Products',
                    'description': 'Tools, fasteners, electrical supplies, and construction hardware'
                },
                {
                    'name': 'Automotive Supplies',
                    'description': 'Tyres, lubricants, automotive parts, and car accessories'
                },
                {
                    'name': 'Paints & Coatings',
                    'description': 'Interior and exterior paints, primers, and protective coatings'
                },
                {
                    'name': 'Lighting & Electrical',
                    'description': 'LED lights, electrical fixtures, and The-Lights-Shop products'
                },
            ]
            
            category_objects = []
            for cat_data in categories:
                category = Category.objects.create(**cat_data)
                category_objects.append(category)
                self.stdout.write(f"Created category: {category.name}")
            
            # Create products
            self.stdout.write(self.style.SUCCESS('Creating products...'))
            
            # Hardware Products
            hardware_products = [
                {
                    'name': 'Stanley Claw Hammer 16oz',
                    'description': 'Professional grade claw hammer with comfortable grip handle. Perfect for construction and carpentry work.',
                    'price': 45.00,
                    'unit': 'piece',
                    'sku': 'HW-HAM-001',
                    'stock_quantity': 25,
                    'specifications': {'weight': '16oz', 'material': 'Steel head with wooden handle', 'brand': 'Stanley'}
                },
                {
                    'name': 'Phillips Head Screwdriver Set',
                    'description': '5-piece Phillips head screwdriver set with magnetic tips and ergonomic handles.',
                    'price': 35.00,
                    'unit': 'piece',
                    'sku': 'HW-SCR-001',
                    'stock_quantity': 40,
                    'specifications': {'pieces': '5', 'sizes': 'PH0, PH1, PH2, PH3, PH4', 'brand': 'Craftsman'}
                },
                {
                    'name': 'Adjustable Wrench 10-inch',
                    'description': 'Heavy-duty adjustable wrench with chrome finish. Jaw capacity up to 1-1/4 inch.',
                    'price': 28.50,
                    'unit': 'piece',
                    'sku': 'HW-WRE-001',
                    'stock_quantity': 30,
                    'specifications': {'length': '10 inches', 'jaw_capacity': '1-1/4 inch', 'finish': 'Chrome'}
                },
                {
                    'name': 'Galvanized Steel Nails 3-inch',
                    'description': 'High-quality galvanized steel nails for outdoor construction projects.',
                    'price': 15.75,
                    'unit': 'bag',
                    'sku': 'HW-NAI-001',
                    'stock_quantity': 100,
                    'specifications': {'length': '3 inches', 'material': 'Galvanized steel', 'quantity_per_bag': '5kg'}
                },
                {
                    'name': 'Electrical Extension Cord 20ft',
                    'description': 'Heavy-duty outdoor extension cord with weatherproof connectors.',
                    'price': 42.00,
                    'unit': 'piece',
                    'sku': 'HW-ELE-001',
                    'stock_quantity': 15,
                    'specifications': {'length': '20 feet', 'rating': '15A/125V', 'type': 'SJTW 12/3'}
                },
                {
                    'name': 'PVC Pipe Fittings Kit',
                    'description': 'Complete PVC pipe fittings kit for plumbing installations.',
                    'price': 65.00,
                    'unit': 'piece',
                    'sku': 'HW-PVC-001',
                    'stock_quantity': 20,
                    'specifications': {'sizes': 'Multiple sizes included', 'material': 'PVC', 'pieces': '25'}
                }
            ]
            
            # Automotive Supplies
            automotive_products = [
                {
                    'name': 'Michelin Car Tyre 185/65R15',
                    'description': 'Premium quality Michelin tyre with excellent grip and durability.',
                    'price': 450.00,
                    'unit': 'piece',
                    'sku': 'AU-TYR-001',
                    'stock_quantity': 12,
                    'specifications': {'size': '185/65R15', 'brand': 'Michelin', 'type': 'Radial', 'load_index': '88H'}
                },
                {
                    'name': 'Shell Helix Ultra Engine Oil 5W-30',
                    'description': 'Fully synthetic engine oil for superior engine protection and performance.',
                    'price': 85.00,
                    'unit': 'gallon',
                    'sku': 'AU-OIL-001',
                    'stock_quantity': 50,
                    'specifications': {'viscosity': '5W-30', 'type': 'Fully Synthetic', 'volume': '4 liters', 'brand': 'Shell'}
                },
                {
                    'name': 'Car Battery 12V 70Ah',
                    'description': 'Maintenance-free car battery with 2-year warranty.',
                    'price': 320.00,
                    'unit': 'piece',
                    'sku': 'AU-BAT-001',
                    'stock_quantity': 8,
                    'specifications': {'voltage': '12V', 'capacity': '70Ah', 'type': 'Maintenance-free', 'warranty': '2 years'}
                },
                {
                    'name': 'Brake Pad Set - Front',
                    'description': 'High-quality ceramic brake pads for improved stopping power.',
                    'price': 125.00,
                    'unit': 'piece',
                    'sku': 'AU-BRA-001',
                    'stock_quantity': 20,
                    'specifications': {'position': 'Front', 'material': 'Ceramic', 'compatibility': 'Universal fit'}
                },
                {
                    'name': 'Car Air Filter',
                    'description': 'Premium air filter for improved engine performance and fuel efficiency.',
                    'price': 35.00,
                    'unit': 'piece',
                    'sku': 'AU-FIL-001',
                    'stock_quantity': 45,
                    'specifications': {'type': 'Paper element', 'efficiency': '99.5%', 'replacement_interval': '15,000km'}
                },
                {
                    'name': 'Windshield Washer Fluid',
                    'description': 'All-season windshield washer fluid with anti-freeze protection.',
                    'price': 18.50,
                    'unit': 'gallon',
                    'sku': 'AU-WAS-001',
                    'stock_quantity': 75,
                    'specifications': {'volume': '3.78L', 'temperature_rating': '-34°C', 'type': 'All-season'}
                }
            ]
            
            # Paints & Coatings
            paint_products = [
                {
                    'name': 'Dulux Weathershield Exterior Paint',
                    'description': 'Premium exterior paint with 15-year weather protection guarantee.',
                    'price': 180.00,
                    'unit': 'gallon',
                    'sku': 'PA-EXT-001',
                    'stock_quantity': 30,
                    'specifications': {'coverage': '35 sq meters per gallon', 'finish': 'Satin', 'protection': '15 years', 'brand': 'Dulux'}
                },
                {
                    'name': 'Interior Emulsion Paint - White',
                    'description': 'High-quality interior emulsion paint with smooth matt finish.',
                    'price': 95.00,
                    'unit': 'gallon',
                    'sku': 'PA-INT-001',
                    'stock_quantity': 40,
                    'specifications': {'color': 'Pure White', 'finish': 'Matt', 'coverage': '40 sq meters per gallon'}
                },
                {
                    'name': 'Metal Primer - Red Oxide',
                    'description': 'Anti-corrosive primer for metal surfaces preparation.',
                    'price': 65.00,
                    'unit': 'gallon',
                    'sku': 'PA-PRI-001',
                    'stock_quantity': 25,
                    'specifications': {'type': 'Red Oxide', 'application': 'Metal surfaces', 'drying_time': '4-6 hours'}
                },
                {
                    'name': 'Wood Stain - Mahogany',
                    'description': 'Premium wood stain for interior and exterior wood protection.',
                    'price': 72.00,
                    'unit': 'gallon',
                    'sku': 'PA-STA-001',
                    'stock_quantity': 20,
                    'specifications': {'color': 'Mahogany', 'type': 'Semi-transparent', 'protection': 'UV resistant'}
                },
                {
                    'name': 'Concrete Sealer',
                    'description': 'Waterproof concrete sealer for driveways and foundations.',
                    'price': 110.00,
                    'unit': 'gallon',
                    'sku': 'PA-SEA-001',
                    'stock_quantity': 15,
                    'specifications': {'application': 'Concrete surfaces', 'coverage': '25 sq meters per gallon', 'type': 'Acrylic-based'}
                },
                {
                    'name': 'Paint Brush Set Professional',
                    'description': '5-piece professional paint brush set with natural bristles.',
                    'price': 48.00,
                    'unit': 'piece',
                    'sku': 'PA-BRU-001',
                    'stock_quantity': 35,
                    'specifications': {'pieces': '5', 'sizes': '1", 2", 3", 4", angled', 'bristle_type': 'Natural'}
                }
            ]
            
            # Lighting & Electrical
            lighting_products = [
                {
                    'name': 'LED Bulb 12W Daylight',
                    'description': 'Energy-efficient LED bulb with 10-year lifespan. The-Lights-Shop premium quality.',
                    'price': 25.00,
                    'unit': 'piece',
                    'sku': 'LI-BUL-001',
                    'stock_quantity': 100,
                    'specifications': {'wattage': '12W', 'equivalent': '100W incandescent', 'color_temp': '6500K', 'lifespan': '25,000 hours'}
                },
                {
                    'name': 'Ceiling Fan with Light 52-inch',
                    'description': 'Modern ceiling fan with integrated LED lighting and remote control.',
                    'price': 285.00,
                    'unit': 'piece',
                    'sku': 'LI-FAN-001',
                    'stock_quantity': 8,
                    'specifications': {'diameter': '52 inches', 'speeds': '3', 'light': 'Integrated LED', 'remote': 'Included'}
                },
                {
                    'name': 'Outdoor Security Light Motion Sensor',
                    'description': 'Solar-powered security light with motion detection and adjustable settings.',
                    'price': 125.00,
                    'unit': 'piece',
                    'sku': 'LI-SEC-001',
                    'stock_quantity': 18,
                    'specifications': {'power': 'Solar', 'detection_range': '8 meters', 'brightness': '1000 lumens', 'waterproof': 'IP65'}
                },
                {
                    'name': 'Electrical Cable 2.5mm²',
                    'description': 'High-quality copper electrical cable for house wiring.',
                    'price': 8.50,
                    'unit': 'piece',
                    'sku': 'LI-CAB-001',
                    'stock_quantity': 200,
                    'specifications': {'size': '2.5mm²', 'material': 'Copper', 'insulation': 'PVC', 'length_per_roll': '100 meters'}
                },
                {
                    'name': 'Socket Outlet 3-Pin',
                    'description': 'Standard 3-pin socket outlet with safety shutters.',
                    'price': 15.00,
                    'unit': 'piece',
                    'sku': 'LI-SOC-001',
                    'stock_quantity': 80,
                    'specifications': {'type': '3-pin', 'rating': '13A', 'safety': 'Child-proof shutters', 'color': 'White'}
                },
                {
                    'name': 'LED Strip Light 5M RGB',
                    'description': 'Color-changing LED strip light with remote control and adhesive backing.',
                    'price': 65.00,
                    'unit': 'roll',
                    'sku': 'LI-STR-001',
                    'stock_quantity': 25,
                    'specifications': {'length': '5 meters', 'type': 'RGB color-changing', 'control': 'Remote included', 'voltage': '12V'}
                }
            ]
            
            # Add all products to database
            all_products = [
                (category_objects[0], hardware_products),
                (category_objects[1], automotive_products),
                (category_objects[2], paint_products),
                (category_objects[3], lighting_products),
            ]
            
            product_count = 0
            for category, products in all_products:
                for product_data in products:
                    product_data['category'] = category
                    product = Product.objects.create(**product_data)
                    product_count += 1
                    self.stdout.write(f"Created product: {product.name}")
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully populated database with {len(category_objects)} categories and {product_count} products for Riverway Company Limited'
                )
            )