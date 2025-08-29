import re
import difflib
from datetime import datetime, time
from typing import Dict, List, Tuple, Optional
from django.utils import timezone
from .models import FAQ, Intent, BusinessHours, CompanyInfo, ChatbotSettings
from store.models import Product, Category
import logging

logger = logging.getLogger(__name__)


class NLPEngine:
    def __init__(self):
        self.intent_patterns = {
            'greeting': [
                r'\b(hello|hi|hey|good\s+(morning|afternoon|evening)|greetings)\b',
                r'\b(how\s+are\s+you|what\'s\s+up)\b'
            ],
            'business_hours': [
                r'\b(hours|open|close|when\s+open|operating\s+hours|business\s+hours)\b',
                r'\b(what\s+time|when\s+do\s+you)\b.*\b(open|close)\b'
            ],
            'location': [
                r'\b(where|location|address|directions|find\s+you)\b',
                r'\b(how\s+to\s+get|where\s+are\s+you\s+located)\b'
            ],
            'services': [
                r'\b(services|what\s+do\s+you\s+do|what\s+do\s+you\s+offer)\b',
                r'\b(construction|building|renovation|repair)\b'
            ],
            'products': [
                r'\b(products|product|items|materials|inventory|stock|catalog|what\s+do\s+you\s+sell)\b',
                r'\b(cement|concrete|steel|lumber|pipes|tiles|paint|paints|tools|hardware|supplies)\b',
                r'\b(show\s+me|display|list|available)\b.*\b(products|items)\b',
                r'\b(do\s+you\s+have|do\s+you\s+sell|looking\s+for|need|want)\b',
                r'\b(hammer|screws|nails|wrench|drill|saw|pliers|wire|cable|cables)\b',
                r'\b(automotive|battery|oil|tyre|tyres|lights|electrical)\b',
                r'\b(pvc|pipe|fittings|kit|stanley|claw|philips|head|screwdriver|adjustable|galvanized|extension|cord|michelin|shell|helix|brake|pad)\b',
                r'\b(emulsion|brush|dulux|weathershield|primer|sealer|led|bulb|switch|outlet|fluorescent|tube)\b',
                r'^(paint|paints|tools|hammer|screws|nails|cement|steel|lumber|tiles|pipes|wire|cables|lights|battery|oil|tyres|hardware|supplies|electrical|automotive|pliers|drill|saw|pvc|kit|fittings)$'
            ],
            'pricing': [
                r'\b(price|cost|pricing|how\s+much|rates|quote|estimate)\b',
                r'\b(expensive|cheap|affordable|budget)\b'
            ],
            'contact': [
                r'\b(contact|phone|email|call|reach)\b',
                r'\b(get\s+in\s+touch|contact\s+information)\b'
            ],
            'complaint': [
                r'\b(complaint|problem|issue|wrong|error|bad|terrible|awful)\b',
                r'\b(dissatisfied|unhappy|disappointed|frustrated)\b'
            ],
            'booking': [
                r'\b(book|schedule|appointment|reservation|arrange)\b',
                r'\b(when\s+can\s+you|available\s+time)\b'
            ],
            'order_tracking': [
                r'\b(order|track|delivery|shipment|status)\b',
                r'\b(where\s+is\s+my|when\s+will\s+my)\b'
            ],
            'availability': [
                r'\b(available|availability|in\s+stock|stock|inventory)\b',
                r'\b(do\s+you\s+have|is\s+there|can\s+i\s+get)\b',
                r'\b(have\s+you\s+got|got\s+any|carry)\b'
            ],
            'price_inquiry': [
                r'\b(price|cost|pricing|how\s+much|rates|quote|estimate|expensive|cheap|affordable)\b',
                r'\b(what\s+does\s+it\s+cost|how\s+much\s+does)\b'
            ],
            'goodbye': [
                r'\b(bye|goodbye|see\s+you|farewell)\b',
                r'\b(that\'s\s+all|no\s+more\s+questions)\b'
            ],
            'acknowledgment': [
                r'^(okay|ok|thanks|thank\s+you|alright|got\s+it|understood|fine|good|nice)$',
                r'\b(thanks|thank\s+you|appreciate|grateful)\b',
                r'^(yes|yeah|yep|sure|correct|right)$'
            ],
            'negative_acknowledgment': [
                r'^(no|nah|nope|not\s+really|never\s+mind|forget\s+it)$',
                r'\b(no\s+thanks|not\s+interested|maybe\s+later)\b'
            ]
        }
        
        # Common non-hardware product categories that people might ask about
        self.non_hardware_categories = {
            'beauty': ['pomade', 'shampoo', 'lotion', 'cream', 'soap', 'perfume', 'cosmetics', 'makeup'],
            'food': ['rice', 'bread', 'milk', 'sugar', 'oil', 'flour', 'meat', 'fish', 'vegetables'],
            'clothing': ['shirt', 'pants', 'shoes', 'dress', 'jacket', 'hat', 'socks'],
            'electronics': ['phone', 'laptop', 'tv', 'computer', 'tablet', 'headphones'],
            'medicine': ['pills', 'tablets', 'medicine', 'drugs', 'bandage', 'antiseptic'],
            'books': ['book', 'magazine', 'newspaper', 'novel', 'textbook']
        }
        
        self.sentiment_patterns = {
            'positive': [
                r'\b(great|excellent|good|amazing|wonderful|fantastic|perfect|awesome)\b',
                r'\b(love|like|satisfied|happy|pleased)\b'
            ],
            'negative': [
                r'\b(bad|terrible|awful|horrible|worst|hate|disappointed|frustrated)\b',
                r'\b(problem|issue|wrong|error|broken|failed)\b'
            ],
            'neutral': [
                r'\b(okay|ok|fine|alright|average)\b'
            ]
        }

    def extract_intent(self, message: str) -> Tuple[str, float]:
        """Extract intent from user message with confidence score"""
        message_lower = message.lower()
        best_intent = 'unknown'
        best_confidence = 0.0
        
        for intent, patterns in self.intent_patterns.items():
            confidence = 0.0
            for pattern in patterns:
                matches = re.findall(pattern, message_lower)
                if matches:
                    confidence += len(matches) * 0.3
            
            # Normalize confidence
            confidence = min(confidence, 1.0)
            
            if confidence > best_confidence:
                best_confidence = confidence
                best_intent = intent
        
        return best_intent, best_confidence

    def extract_sentiment(self, message: str) -> str:
        """Extract sentiment from user message"""
        message_lower = message.lower()
        sentiment_scores = {'positive': 0, 'negative': 0, 'neutral': 0}
        
        for sentiment, patterns in self.sentiment_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, message_lower)
                sentiment_scores[sentiment] += len(matches)
        
        if sentiment_scores['negative'] > sentiment_scores['positive']:
            return 'negative'
        elif sentiment_scores['positive'] > sentiment_scores['negative']:
            return 'positive'
        else:
            return 'neutral'
    
    def detect_non_hardware_product(self, message: str) -> tuple:
        """Detect if user is asking for non-hardware products and return category and product"""
        try:
            message_lower = message.lower()
            
            for category, products in self.non_hardware_categories.items():
                for product in products:
                    if product in message_lower:
                        return category, product
            return None, None
        except Exception as e:
            logger.error(f"Error in detect_non_hardware_product: {e}")
            return None, None
    
    def _generate_non_hardware_response(self, category: str, product: str) -> dict:
        """Generate response for non-hardware product queries"""
        try:
            # Get some alternative suggestions from our actual products
            popular_products = Product.objects.filter(is_active=True, stock_quantity__gt=0).order_by('-stock_quantity')[:4]
            product_list = list(popular_products.values(
                'id', 'name', 'price', 'image', 'description', 'unit', 'stock_quantity'
            ))
            
            # Add image URLs
            for prod in product_list:
                if prod['image']:
                    prod['image_url'] = f"/media/{prod['image']}"
                else:
                    prod['image_url'] = None
            
            category_messages = {
                'beauty': f"I understand you're looking for {product}, but we specialize in hardware and building supplies. We don't carry beauty products like {product}.",
                'food': f"I see you're asking about {product}. We're a hardware store, so we don't sell food items like {product}.",
                'clothing': f"You mentioned {product}, but we focus on hardware and building materials rather than clothing items.",
                'electronics': f"While {product} sounds useful, we specialize in hardware supplies rather than electronics.",
                'medicine': f"I understand you need {product}, but we're a hardware store and don't carry medical supplies.",
                'books': f"You asked about {product}, but we focus on hardware and building materials rather than books."
            }
            
            base_message = category_messages.get(category, f"We don't carry {product} as we specialize in hardware and building supplies.")
            
            message = f"{base_message}\n\nHowever, here are some of our popular products that might interest you, or I can help you find what you need for your project:"
            
            return {
                'message': message,
                'products': product_list
            }
        
        except Exception as e:
            logger.error(f"Error in _generate_non_hardware_response: {e}")
            return {
                'message': f"I understand you're looking for {product}, but we specialize in hardware and building supplies. Please let me know what specific hardware items you need!",
                'products': []
            }
    
    def _try_aggressive_product_search(self, message: str, entities: dict) -> dict:
        """Try aggressive product search for unknown intents"""
        try:
            message_lower = message.lower().strip()
            
            # Keywords that suggest user is asking about products
            product_indicators = ['do you have', 'sell', 'available', 'stock', 'buy', 'need', 'looking for', 
                                 'want', 'get', 'find', 'price', 'cost', 'how much']
            
            # Common single-word product categories/items that should trigger product search
            single_word_products = ['paint', 'paints', 'tools', 'hammer', 'screws', 'nails', 'cement', 'steel', 
                                   'lumber', 'tiles', 'pipes', 'wire', 'cables', 'lights', 'battery', 'oil', 
                                   'tyres', 'hardware', 'supplies', 'electrical', 'automotive', 'pliers', 'drill', 'saw',
                                   'pvc', 'kit', 'fittings', 'stanley', 'claw', 'philips', 'screwdriver', 'wrench',
                                   'cord', 'extension', 'michelin', 'shell', 'helix', 'brake', 'pad', 'emulsion',
                                   'brush', 'dulux', 'weathershield', 'primer', 'sealer', 'led', 'bulb']
            
            # Check if message contains product-related keywords OR is a single word product
            has_product_indicator = (any(indicator in message_lower for indicator in product_indicators) or 
                                   message_lower in single_word_products or
                                   any(word in message_lower for word in single_word_products))
            
            if not has_product_indicator:
                return None
                
            from django.db.models import Q
            
            # Extract all meaningful words (excluding common words)
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'do', 'does', 'did', 'have', 'has', 'had', 'will', 'would', 'could', 'should', 'you', 'i', 'we', 'they', 'he', 'she', 'it'}
            words = [word.strip('.,?!') for word in message_lower.split() if len(word) > 2 and word not in stop_words]
            
            if not words:
                return None
                
            # Search products using all meaningful words
            products = Product.objects.filter(is_active=True)
            query = Q()
            
            for word in words:
                if len(word) > 2:  # Only search meaningful terms
                    query |= Q(name__icontains=word)
                    query |= Q(description__icontains=word)
                    query |= Q(category__name__icontains=word)
            
            found_products = products.filter(query).distinct().order_by('-stock_quantity', 'name')[:6]
            
            if found_products.exists():
                product_list = list(found_products.values(
                    'id', 'name', 'price', 'image', 'description', 'unit', 'stock_quantity'
                ))
                
                # Add image URLs
                for product in product_list:
                    if product['image']:
                        product['image_url'] = f"/media/{product['image']}"
                    else:
                        product['image_url'] = None
                
                return {
                    'message': f"I found some products that might match what you're looking for:",
                    'products': product_list,
                    'suggested_actions': ['get_quote', 'check_availability', 'contact_sales']
                }
            
            return None
        
        except Exception as e:
            logger.error(f"Error in aggressive product search: {e}")
            return None

    def find_best_faq_match(self, message: str, threshold: float = 0.7) -> Optional[FAQ]:
        """Find the best FAQ match using fuzzy matching"""
        message_lower = message.lower()
        faqs = FAQ.objects.filter(is_active=True)
        
        best_match = None
        best_score = 0.0
        
        for faq in faqs:
            # Check question similarity
            question_score = difflib.SequenceMatcher(
                None, message_lower, faq.question.lower()
            ).ratio()
            
            # Check keywords similarity
            if faq.keywords:
                keywords = [kw.strip().lower() for kw in faq.keywords.split(',')]
                keyword_score = 0.0
                for keyword in keywords:
                    if keyword in message_lower:
                        keyword_score += 0.5
                keyword_score = min(keyword_score, 1.0)
            else:
                keyword_score = 0.0
            
            # Combined score
            combined_score = max(question_score, keyword_score)
            
            if combined_score > best_score and combined_score >= threshold:
                best_score = combined_score
                best_match = faq
        
        return best_match

    def extract_entities(self, message: str) -> Dict[str, List[str]]:
        """Extract entities from user message"""
        entities = {
            'phone_numbers': [],
            'emails': [],
            'dates': [],
            'times': [],
            'locations': [],
            'products': [],
            'prices': [],
            'quantities': []
        }
        
        # Phone numbers
        phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'
        entities['phone_numbers'] = re.findall(phone_pattern, message)
        
        # Email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        entities['emails'] = re.findall(email_pattern, message)
        
        # Simple date patterns
        date_patterns = [
            r'\b(today|tomorrow|yesterday)\b',
            r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            r'\b\d{1,2}\/\d{1,2}\/\d{4}\b',
            r'\b\d{1,2}-\d{1,2}-\d{4}\b'
        ]
        
        for pattern in date_patterns:
            entities['dates'].extend(re.findall(pattern, message, re.IGNORECASE))
        
        # Time patterns
        time_pattern = r'\b\d{1,2}:\d{2}(?:\s?(?:AM|PM))?\b'
        entities['times'] = re.findall(time_pattern, message, re.IGNORECASE)
        
        # Enhanced product-related entities
        product_keywords = {
            'cement': ['cement', 'portland', 'concrete'],
            'steel': ['steel', 'rebar', 'reinforcement', 'iron'],
            'lumber': ['lumber', 'wood', 'timber', 'plywood'],
            'pipes': ['pipe', 'pipes', 'plumbing', 'pvc', 'copper', 'fittings'],
            'tiles': ['tile', 'tiles', 'ceramic', 'porcelain'],
            'paint': ['paint', 'primer', 'coating', 'emulsion', 'dulux', 'weathershield'],
            'tools': ['tools', 'hammer', 'drill', 'saw', 'stanley', 'claw', 'screwdriver', 'wrench'],
            'brick': ['brick', 'bricks', 'masonry'],
            'sand': ['sand', 'aggregate'],
            'gravel': ['gravel', 'stone', 'aggregate'],
            'automotive': ['car', 'battery', 'tyre', 'oil', 'shell', 'helix', 'michelin', 'brake', 'pad', 'filter'],
            'electrical': ['led', 'bulb', 'light', 'switch', 'outlet', 'cord', 'extension', 'fluorescent'],
            'kit': ['kit', 'set', 'fittings', 'collection']
        }
        
        for main_keyword, variants in product_keywords.items():
            for variant in variants:
                if variant.lower() in message.lower():
                    entities['products'].append(main_keyword)
                    break
        
        # Price-related patterns
        price_pattern = r'\$\d+(?:\.\d{2})?|\d+\s*(?:dollars?|bucks?)'
        entities['prices'] = re.findall(price_pattern, message, re.IGNORECASE)
        
        # Quantity patterns
        quantity_pattern = r'\d+\s*(?:pieces?|bags?|tons?|yards?|gallons?|rolls?|sheets?)'
        entities['quantities'] = re.findall(quantity_pattern, message, re.IGNORECASE)
        
        return entities


class ChatbotEngine:
    def __init__(self):
        self.nlp = NLPEngine()
        self.failed_attempts = {}  # Track failed attempts per session
        
    def get_business_hours_response(self) -> str:
        """Generate business hours response"""
        try:
            hours = BusinessHours.objects.all().order_by('id')
            if not hours.exists():
                return "Please contact us for our business hours information."
            
            response = "Our business hours are:\n"
            for hour in hours:
                if hour.is_closed:
                    response += f"• {hour.day.capitalize()}: Closed\n"
                else:
                    response += f"• {hour.day.capitalize()}: {hour.open_time.strftime('%I:%M %p')} - {hour.close_time.strftime('%I:%M %p')}\n"
            
            return response.strip()
        except Exception as e:
            logger.error(f"Error getting business hours: {e}")
            return "Please contact us for our business hours information."
    
    def get_product_info_response(self, message: str, entities: dict) -> dict:
        """Generate product information response"""
        try:
            # First check if user is asking for non-hardware products
            category, product = self.nlp.detect_non_hardware_product(message)
            if category and product:
                return self.nlp._generate_non_hardware_response(category, product)
            
            # Extract product keywords from entities and message
            product_keywords = entities.get('products', [])
            message_lower = message.lower()
            
            # Search for products based on keywords and message content
            products = Product.objects.filter(is_active=True)
            
                # Enhanced keyword matching with better algorithm
            search_terms = self._extract_search_terms(message_lower)
            
            if product_keywords or search_terms:
                from django.db.models import Q
                query = Q()
                
                # Create prioritized search with better relevance scoring
                all_search_terms = product_keywords + search_terms
                
                # First try exact matches in product names
                exact_matches = products.filter(
                    name__icontains=' '.join(search_terms)
                ).distinct() if len(search_terms) > 1 else Product.objects.none()
                
                # Then try individual term matches
                query = Q()
                for keyword in product_keywords:
                    query |= Q(name__icontains=keyword) | Q(description__icontains=keyword)
                    query |= Q(category__name__icontains=keyword)
                
                for term in search_terms:
                    if len(term) > 2:  # Only search terms longer than 2 characters
                        query |= Q(name__icontains=term) | Q(description__icontains=term)
                        query |= Q(category__name__icontains=term)
                        query |= Q(specifications__icontains=term)
                
                term_matches = products.filter(query).distinct()
                
                # Combine results with exact matches first
                from django.db.models import Case, When, Value, IntegerField
                
                # Create relevance scoring
                relevance_cases = []
                for i, term in enumerate(all_search_terms):
                    if len(term) > 2:
                        relevance_cases.append(
                            When(name__icontains=term, then=Value(100 - i * 5))
                        )
                        relevance_cases.append(
                            When(description__icontains=term, then=Value(50 - i * 2))
                        )
                
                products = term_matches.annotate(
                    relevance=Case(
                        *relevance_cases,
                        default=Value(0),
                        output_field=IntegerField()
                    )
                ).order_by('-relevance', '-stock_quantity', 'name')
                
                # Combine exact matches with term matches
                if exact_matches.exists():
                    exact_list = list(exact_matches)
                    term_list = [p for p in products if p not in exact_list]
                    products = exact_list + term_list
                else:
                    products = list(products)
            else:
                # General product inquiry - show popular/featured products intelligently
                # Prioritize high-stock, recently updated, and popular items
                products = products.filter(stock_quantity__gt=0).order_by('-stock_quantity', '-updated_at', 'name')[:8]
            
            # Convert products to list if it's a queryset
            if hasattr(products, 'exists') and hasattr(products, 'values'):
                products_list = list(products)
            else:
                products_list = products if isinstance(products, list) else list(products)
                
            if not products_list:
                popular_products = Product.objects.filter(is_active=True, stock_quantity__gt=0).order_by('-stock_quantity')[:6]
                if not popular_products.exists():
                    return {
                        'message': "I apologize, but I couldn't find any specific products matching your query right now. Our inventory might be updating. However, I'd be happy to help you in other ways:\n\n• Contact our sales team directly for current product information\n• Browse our most popular products\n• Get a custom quote for your specific needs\n\nWould you like me to connect you with our sales team?",
                        'products': []
                    }
                popular_list = list(popular_products.values(
                    'id', 'name', 'price', 'image', 'description', 'unit', 'stock_quantity'
                ))
                # Add image URLs
                for product in popular_list:
                    if product['image']:
                        product['image_url'] = f"/media/{product['image']}"
                    else:
                        product['image_url'] = None
                
                return {
                    'message': "I couldn't find exactly what you mentioned, but here are some of our most popular products that might interest you:",
                    'products': popular_list
                }
            
            # Convert product objects to dictionary format
            product_list = []
            for product in products_list:
                product_dict = {
                    'id': product.id,
                    'name': product.name,
                    'price': float(product.price),
                    'image': product.image.name if product.image else None,
                    'description': product.description,
                    'unit': product.unit,
                    'stock_quantity': product.stock_quantity
                }
                product_list.append(product_dict)
            
            # Add image URLs to products
            for product in product_list:
                if product['image']:
                    product['image_url'] = f"/media/{product['image']}"
                else:
                    product['image_url'] = None
            
            if len(product_list) == 1:
                product = product_list[0]
                stock_status = "In Stock" if product['stock_quantity'] > 0 else "Out of Stock"
                
                # Check if this is a specific product inquiry (like Portland cement)
                if 'portland' in message_lower and 'cement' in product['name'].lower():
                    message = f"**Yes, we have Portland cement!** Here are the details:\n\n"
                else:
                    message = f"Perfect! I found exactly what you're looking for.\n\n"
                    
                message += f"**{product['name']}**\n\n"
                message += f"**Price:** ₵{product['price']:.2f} per {product['unit']}\n"
                message += f"**Availability:** {stock_status}"
                if product['stock_quantity'] > 0:
                    if product['stock_quantity'] <= 5:
                        message += f" - HURRY! Only {product['stock_quantity']} left in stock!\n\n"
                    else:
                        message += f" ({product['stock_quantity']} units available)\n\n"
                else:
                    message += " - Let me know if you'd like to see similar alternatives!\n\n"
                message += f"**Product Details:** {product['description']}\n\n"
                if product['image_url']:
                    message += f"[View Product Image]({product['image_url']})\n\n"
                if product['stock_quantity'] > 0:
                    message += "Would you like more information, similar products, or a personalized quote?"
            else:
                message = f"Great news! I found {len(product_list)} excellent options for you:\n\n"
                for i, product in enumerate(product_list[:4], 1):
                    stock_indicator = "[IN STOCK]" if product['stock_quantity'] > 0 else "[OUT OF STOCK]"
                    stock_note = ""
                    if product['stock_quantity'] > 0:
                        if product['stock_quantity'] <= 5:
                            stock_note = " - LIMITED QUANTITY!"
                        elif product['stock_quantity'] > 50:
                            stock_note = " - HIGH AVAILABILITY"
                    message += f"**{i}. {product['name']}** {stock_indicator}{stock_note}\n"
                    message += f"    Price: ₵{product['price']:.2f} per {product['unit']}\n\n"
                if len(product_list) > 4:
                    message += f"Plus {len(product_list) - 4} more items available! Click on any product below to see details, or ask me about specific items."
            
            return {
                'message': message,
                'products': product_list[:6]  # Limit to 6 for display
            }
            
        except Exception as e:
            logger.error(f"Error getting product info: {e}")
            return {
                'message': "I'm having trouble accessing our product catalog right now. Please contact us directly for product information.",
                'products': []
            }
    
    def _extract_search_terms(self, message_lower: str) -> list:
        """Extract search terms from message with enhanced filtering"""
        # Remove common words that don't help with product search
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 
                     'i', 'me', 'my', 'you', 'your', 'it', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 
                     'has', 'had', 'do', 'does', 'did', 'can', 'could', 'should', 'would', 'will', 'shall',
                     'what', 'where', 'when', 'why', 'how', 'show', 'tell', 'give', 'get', 'need', 'want',
                     'looking', 'search', 'find', 'about', 'some', 'any', 'more', 'like', 'just', 'see'}
        
        # Enhanced word extraction with better patterns
        words = re.findall(r'\b\w{3,}\b', message_lower)
        
        # Filter out stop words and add construction-specific terms priority
        construction_terms = {'cement', 'concrete', 'steel', 'lumber', 'wood', 'brick', 'tile', 'paint', 'pipe', 'tool'}
        
        filtered_words = []
        for word in words:
            if word not in stop_words:
                if word in construction_terms:
                    filtered_words.insert(0, word)  # Prioritize construction terms
                else:
                    filtered_words.append(word)
        
        return filtered_words[:10]  # Limit to top 10 most relevant terms
    
    def get_company_info_response(self, intent: str) -> str:
        """Generate company information response based on intent"""
        try:
            company = CompanyInfo.objects.first()
            if not company:
                return "Please contact us for more information."
            
            if intent == 'location':
                return f"We're located at: {company.address}\n\nPhone: {company.phone}\nEmail: {company.email}"
            elif intent == 'services':
                return f"We offer the following services:\n{company.services}\n\nFor more details, please contact us at {company.phone}"
            elif intent == 'contact':
                return f"You can reach us:\n\n📞 Phone: {company.phone}\n📧 Email: {company.email}\n📍 Address: {company.address}"
            elif intent == 'pricing':
                if company.pricing_info:
                    return f"{company.pricing_info}\n\nFor a detailed quote, please contact us at {company.phone}"
                else:
                    return "Please contact us for pricing information and quotes at {company.phone}"
            else:
                return f"{company.description}\n\nContact us at {company.phone} for more information."
        except Exception as e:
            logger.error(f"Error getting company info: {e}")
            return "Please contact us for more information."
    
    def is_business_hours(self) -> bool:
        """Check if current time is within business hours"""
        try:
            now = timezone.now()
            current_day = now.strftime('%A').lower()
            current_time = now.time()
            
            business_hour = BusinessHours.objects.filter(day=current_day).first()
            if not business_hour or business_hour.is_closed:
                return False
            
            return business_hour.open_time <= current_time <= business_hour.close_time
        except Exception as e:
            logger.error(f"Error checking business hours: {e}")
            return True  # Default to open if error

    def generate_response(self, message: str, session_id: str, user_context=None, chat_history=None) -> Dict[str, any]:
        """Generate chatbot response for user message"""
        try:
            # Extract intent and entities with context awareness
            message_lower = message.lower()
            intent, confidence = self.nlp.extract_intent(message)
            sentiment = self.nlp.extract_sentiment(message)
            entities = self.nlp.extract_entities(message)
            
            # Analyze chat history for context
            context_info = self._analyze_chat_context(chat_history or []) if chat_history else {}
            
            # Check if this is a product-specific query first
            should_check_products_first = (intent in ['products', 'availability', 'price_inquiry'] or 
                                         any(entities.get('products', [])) or
                                         any(keyword in message_lower for keyword in ['do you have', 'sell', 'available', 'stock', 'buy', 'need', 'looking for', 'want', 'get', 'find', 'price', 'cost', 'how much', 'cement', 'steel', 'lumber', 'brick', 'paint', 'tile', 'hammer', 'screw', 'nail']))
            
            # Try to find FAQ match (but skip for product queries)
            faq_match = None if should_check_products_first else self.nlp.find_best_faq_match(message)
            
            response_data = {
                'message': '',
                'intent': intent,
                'confidence': confidence,
                'sentiment': sentiment,
                'entities': entities,
                'should_escalate': False,
                'escalation_reason': '',
                'suggested_actions': []
            }
            
            # Handle FAQ matches
            if faq_match:
                faq_match.view_count += 1
                faq_match.save()
                response_data['message'] = faq_match.answer
                return response_data
            
            # Handle specific intents
            if intent == 'greeting':
                settings = ChatbotSettings.objects.first()
                welcome_msg = settings.welcome_message if settings else "Welcome to Riverway Company! I'm here to help you find the perfect products and answer any questions you have."
                
                # Handle different user types
                if user_context and user_context.get('is_authenticated'):
                    username = user_context.get('username', 'there')
                    welcome_msg = f"Hello {username}! " + welcome_msg
                    response_data['greeting_type'] = 'returning_user'
                elif user_context and user_context.get('is_guest'):
                    if user_context.get('has_name'):
                        # Guest with name
                        guest_name = user_context.get('username')
                        welcome_msg = f"Hello {guest_name}! " + welcome_msg
                        response_data['greeting_type'] = 'returning_guest'
                    else:
                        # Guest without name - ask for name
                        welcome_msg = "Hi there. How can I help you today?"
                        response_data['greeting_type'] = 'new_guest'
                        response_data['collecting_name'] = True
                else:
                    response_data['greeting_type'] = 'new_user'
                
                response_data['message'] = welcome_msg
                
            elif intent == 'business_hours':
                response_data['message'] = self.get_business_hours_response()
                
            elif intent == 'products':
                product_info = self.get_product_info_response(message, entities)
                response_data['message'] = product_info['message']
                response_data['products'] = product_info.get('products', [])
                
            elif intent in ['location', 'services', 'contact', 'pricing']:
                response_data['message'] = self.get_company_info_response(intent)
                
            elif intent == 'complaint':
                response_data['message'] = "I sincerely apologize for any inconvenience you've experienced. Let me immediately connect you with one of our customer service representatives who will personally address your concern and work to resolve this issue promptly."
                response_data['should_escalate'] = True
                response_data['escalation_reason'] = 'Customer complaint requiring immediate human attention'
                
            elif intent == 'booking':
                if self.is_business_hours():
                    response_data['message'] = "I'd be happy to help you schedule an appointment. Let me connect you with our booking specialist."
                    response_data['should_escalate'] = True
                    response_data['escalation_reason'] = 'Booking request requiring human assistance'
                else:
                    settings = ChatbotSettings.objects.first()
                    hours_msg = settings.working_hours_message if settings else "We're currently outside business hours. Your message will be answered when we return."
                    response_data['message'] = hours_msg
                    
            elif intent == 'availability':
                # Check if specific product mentioned
                if entities.get('products'):
                    product_info = self.get_product_info_response(message, entities)
                    response_data['message'] = "Let me check our current inventory for you.\n\n" + product_info['message']
                    response_data['products'] = product_info.get('products', [])
                else:
                    response_data['message'] = "I'd be happy to check product availability for you. What specific construction material or product are you looking for? I can provide real-time stock information, pricing, and delivery options."
                    response_data['suggested_actions'] = ['show_popular_products', 'browse_categories', 'ask_human_help']
                    
            elif intent == 'price_inquiry':
                # Check if specific product mentioned
                if entities.get('products'):
                    product_info = self.get_product_info_response(message, entities)
                    response_data['message'] = "Here's our current pricing information:\n\n" + product_info['message']
                    response_data['products'] = product_info.get('products', [])
                else:
                    response_data['message'] = "I can provide detailed pricing for all our products. What specific products are you interested in? I can also help you get bulk pricing or project quotes if you need larger quantities."
                    response_data['suggested_actions'] = ['browse_products', 'get_bulk_quote', 'contact_sales']
                    
            elif intent == 'order_tracking':
                if user_context and user_context.get('is_authenticated'):
                    username = user_context.get('username', 'there')
                    response_data['message'] = f"Hi {username}, I'd be happy to help you track your order. Please provide your order number, and I'll get you the latest status update. Alternatively, I can connect you directly with our customer service team."
                else:
                    response_data['message'] = "I can help you track your order. Please provide your order number, or I can connect you with our customer service team who can assist you with order tracking and delivery information."
                response_data['suggested_actions'] = ['contact_support', 'request_order_number']
                
            elif intent == 'goodbye':
                if user_context and user_context.get('is_authenticated'):
                    username = user_context.get('username', 'there')
                    response_data['message'] = f"Thank you {username} for choosing Riverway Company! Have a wonderful day, and please don't hesitate to contact us anytime for your hardware and building supply needs."
                else:
                    response_data['message'] = "Thank you for choosing Riverway Company! Have a wonderful day, and please don't hesitate to contact us anytime for your hardware and building supply needs."
                    
            elif intent == 'acknowledgment':
                acknowledgment_responses = [
                    "You're welcome! Is there anything else I can help you with?",
                    "I'm glad I could help! Feel free to ask if you have any other questions.",
                    "Great! Let me know if you need assistance with anything else.",
                    "Perfect! I'm here if you need any more information about our products or services.",
                    "Excellent! Don't hesitate to reach out if you have any other questions."
                ]
                response_data['message'] = acknowledgment_responses[hash(message) % len(acknowledgment_responses)]
                response_data['suggested_actions'] = ['browse_products', 'ask_question', 'contact_sales']
                
            elif intent == 'negative_acknowledgment':
                negative_responses = [
                    "No problem at all! Feel free to browse our products or ask any questions when you're ready.",
                    "That's perfectly fine! I'm here whenever you need assistance with our hardware and building supplies.",
                    "Understood! Take your time, and let me know if you change your mind or need help with anything else."
                ]
                response_data['message'] = negative_responses[hash(message) % len(negative_responses)]
                response_data['suggested_actions'] = ['browse_products', 'check_hours', 'contact_info']
                
            else:
                # Check if this might be a name response from a guest user
                if (user_context and user_context.get('is_guest') and not user_context.get('has_name') and
                    self._is_likely_name(message)):
                    # Extract the name
                    extracted_name = self._extract_name_from_message(message)
                    if extracted_name:
                        response_data['guest_name_collected'] = extracted_name
                        response_data['message'] = f"Nice to meet you, {extracted_name}! How can I help you today?"
                        response_data['intent'] = 'name_collection'
                        return response_data
                
                # Handle unknown intent - try product search before giving generic responses
                # First try aggressive product search for any keywords
                product_response = self.nlp._try_aggressive_product_search(message, entities)
                if product_response:
                    response_data.update(product_response)
                else:
                    # Check for escalation only if no products found
                    if session_id not in self.failed_attempts:
                        self.failed_attempts[session_id] = 0
                    
                    self.failed_attempts[session_id] += 1
                    
                    settings = ChatbotSettings.objects.first()
                    threshold = settings.escalation_threshold if settings else 3
                    
                    if self.failed_attempts[session_id] >= threshold:
                        fallback_msg = settings.fallback_message if settings else "I'm sorry, I didn't understand. Let me connect you with a human agent."
                        response_data['message'] = fallback_msg
                        response_data['should_escalate'] = True
                        response_data['escalation_reason'] = f'Multiple failed attempts ({self.failed_attempts[session_id]})'
                    else:
                        response_data['message'] = "I want to make sure I give you the most helpful information possible. Could you please rephrase your question or be more specific? I can assist you with our products, pricing, availability, services, business hours, location, or any other questions about Riverway Company."
            
            # Add context-aware suggestions
            if not response_data['suggested_actions']:
                response_data['suggested_actions'] = self._get_suggested_actions(intent)
            
            # Enhanced personalization for all responses
            if user_context and intent in ['products', 'services', 'pricing']:
                username = user_context.get('username', '')
                if username and username.lower() not in response_data['message'].lower():
                    if user_context.get('is_authenticated'):
                        response_data['message'] = f"Hi {username}, " + response_data['message'].lower()
                    elif user_context.get('is_guest') and user_context.get('has_name'):
                        response_data['message'] = f"Hi {username}, " + response_data['message'].lower()
            
            return response_data
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                'message': "I'm experiencing technical difficulties. Please try again or contact us directly.",
                'intent': 'error',
                'confidence': 0.0,
                'should_escalate': True,
                'escalation_reason': 'Technical error in chatbot engine'
            }
    
    def _get_suggested_actions(self, intent: str) -> List[str]:
        """Get suggested actions based on intent"""
        suggestions = {
            'greeting': ['ask_services', 'ask_hours', 'ask_location'],
            'services': ['get_quote', 'book_appointment', 'ask_pricing'],
            'products': ['show_more_products', 'get_quote', 'check_availability'],
            'availability': ['show_more_products', 'check_availability', 'ask_human_help'],
            'price_inquiry': ['show_more_products', 'get_quote', 'call_company'],
            'pricing': ['get_quote', 'book_consultation'],
            'location': ['get_directions', 'call_company'],
            'contact': ['call_company', 'send_email'],
            'unknown': ['ask_human_help', 'browse_faq']
        }
        return suggestions.get(intent, [])
    
    def _analyze_chat_context(self, chat_history: list) -> dict:
        """Analyze chat history for context and patterns"""
        context = {
            'previous_products_asked': [],
            'previous_intents': [],
            'conversation_stage': 'initial',
            'user_needs': []
        }
        
        for msg in chat_history[-5:]:  # Last 5 messages
            if msg['type'] == 'user':
                # Extract products mentioned
                entities = self.nlp.extract_entities(msg['content'])
                context['previous_products_asked'].extend(entities.get('products', []))
                
                # Track intents
                if msg.get('intent'):
                    context['previous_intents'].append(msg['intent'])
        
        # Determine conversation stage
        if len(chat_history) > 5:
            context['conversation_stage'] = 'engaged'
        elif any(intent in ['products', 'pricing'] for intent in context['previous_intents']):
            context['conversation_stage'] = 'shopping'
        
        return context
    
    def _is_likely_name(self, message: str) -> bool:
        """Determine if message likely contains a person's name"""
        message_lower = message.lower().strip()
        
        # Patterns that suggest a name response
        name_patterns = [
            r'^(my name is|i am|i\'m|call me|it\'s|its)\s+([a-zA-Z]+)',
            r'^([a-zA-Z]+)$',  # Single word (likely a first name)
            r'^([a-zA-Z]+\s+[a-zA-Z]+)$',  # Two words (likely first and last name)
            r'^(hi|hello|hey),?\s+(i\'m|i am|my name is)\s+([a-zA-Z]+)',
        ]
        
        for pattern in name_patterns:
            if re.search(pattern, message_lower):
                return True
        
        # Check if it's a short message with only letters (likely a name)
        if len(message.split()) <= 2 and message.replace(' ', '').isalpha():
            return True
            
        return False
    
    def _extract_name_from_message(self, message: str) -> str:
        """Extract the name from a message"""
        message = message.strip()
        message_lower = message.lower()
        
        # Try different patterns to extract name
        patterns = [
            r'(?:my name is|i am|i\'m|call me|it\'s|its)\s+([a-zA-Z\s]+)',
            r'(?:hi|hello|hey),?\s+(?:i\'m|i am|my name is)\s+([a-zA-Z\s]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message_lower)
            if match:
                name = match.group(1).strip()
                # Capitalize first letter of each word
                return ' '.join(word.capitalize() for word in name.split())
        
        # If no pattern matches, treat the whole message as name (if it looks like one)
        if message.replace(' ', '').isalpha() and len(message.split()) <= 2:
            return ' '.join(word.capitalize() for word in message.split())
        
        return ""

    def reset_session_attempts(self, session_id: str):
        """Reset failed attempts for a session"""
        if session_id in self.failed_attempts:
            del self.failed_attempts[session_id]