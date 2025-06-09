from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from .models import Game, Genre, Platform, NewsArticle, Order, OrderItem # Make sure models are imported

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user) # Log the user in directly after registration
            messages.success(request, _('Registration successful. You are now logged in.'))
            return redirect('/') # Redirect to a home page, adjust as needed
        else:
            for field in form:
                for error in field.errors:
                    messages.error(request, f"{field.label}: {error}")
            # If form is invalid, re-render the page with the form and errors
            # messages.error(request, 'Registration failed. Please correct the errors below.')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

def home(request):
    featured_games = Game.objects.filter(stock__gt=0).order_by('-release_date', '?')[:4] # Example: 4 random recent in-stock games
    latest_news = NewsArticle.objects.all().order_by('-publication_date')[:3] # 3 latest news
    context = {
        'featured_games': featured_games,
        'latest_news': latest_news
    }
    return render(request, 'store/home.html', context)

def game_list(request):
    games = Game.objects.all().order_by('-release_date') # Fetch all games, newest first
    platforms = Platform.objects.all()
    genres = Genre.objects.all()

    # Basic filtering (can be expanded later)
    platform_filter = request.GET.get('platform')
    genre_filter = request.GET.get('genre')

    if platform_filter:
        games = games.filter(platform__name=platform_filter)
    if genre_filter:
        games = games.filter(genres__name=genre_filter)

    return render(request, 'store/game_list.html', {
        'games': games,
        'platforms': platforms,
        'genres': genres,
        'selected_platform': platform_filter,
        'selected_genre': genre_filter
    })

def game_detail(request, game_id):
    game = Game.objects.get(pk=game_id) # Fetch specific game by ID
    return render(request, 'store/game_detail.html', {'game': game})

def news_list(request):
    articles = NewsArticle.objects.all().order_by('-publication_date') # Fetch all articles, newest first
    return render(request, 'store/news_list.html', {'articles': articles})

def news_detail(request, article_id):
    article = NewsArticle.objects.get(pk=article_id) # Fetch specific article by ID
    return render(request, 'store/news_detail.html', {'article': article})


# Helper function to get the cart from session
def get_cart(request):
    cart = request.session.get('cart', {})
    return cart

# Helper function to save the cart to session
def save_cart(request, cart):
    request.session['cart'] = cart
    request.session.modified = True

@require_POST # Ensures this view can only be accessed via POST
def add_to_cart(request, game_id):
    cart = get_cart(request)
    game = get_object_or_404(Game, id=game_id)
    game_id_str = str(game_id) # Session keys must be strings

    quantity = int(request.POST.get('quantity', 1)) # Get quantity from POST, default to 1

    if game_id_str in cart:
        # If game is already in cart, update its quantity if stock allows
        # For simplicity now, let's assume adding means incrementing by 'quantity' or setting it.
        # A more robust implementation would check against game.stock here.
        cart[game_id_str]['quantity'] = cart[game_id_str].get('quantity', 0) + quantity
    else:
        # If game is not in cart, add it
        if game.stock > 0 : # Basic check
            cart[game_id_str] = {'quantity': quantity, 'price': str(game.price), 'title': game.title, 'platform': game.platform.name}
        else:
            messages.error(request, _("{game_title} is out of stock.").format(game_title=game.title))
            # Decide where to redirect if out of stock - maybe back to product page or game list
            return redirect(request.META.get('HTTP_REFERER', 'store:game_list'))


    # Ensure quantity does not exceed stock
    if game.stock < cart[game_id_str]['quantity']:
        messages.warning(request, _("Reduced quantity for {game_title} due to limited stock ({stock} available).").format(game_title=game.title, stock=game.stock))
        cart[game_id_str]['quantity'] = game.stock

    if cart[game_id_str]['quantity'] <= 0: # If quantity becomes zero or less, remove item
        del cart[game_id_str]
        messages.info(request, _("{game_title} removed from cart.").format(game_title=game.title))
    else:
        messages.success(request, _("{quantity} of {game_title} added/updated in your cart.").format(quantity=quantity, game_title=game.title))

    save_cart(request, cart)
    return redirect(request.META.get('HTTP_REFERER', 'store:cart_detail')) # Redirect to cart page or previous page


@require_POST
def remove_from_cart(request, game_id):
    cart = get_cart(request)
    game_id_str = str(game_id)

    if game_id_str in cart:
        del cart[game_id_str]
        messages.success(request, _("Item removed from your cart."))
    else:
        messages.info(request, _("Item not found in your cart."))

    save_cart(request, cart)
    return redirect('store:cart_detail')

@require_POST
def update_cart(request, game_id):
    cart = get_cart(request)
    game = get_object_or_404(Game, id=game_id)
    game_id_str = str(game_id)

    quantity = int(request.POST.get('quantity', 0))

    if game_id_str in cart:
        if quantity > 0:
            if quantity > game.stock:
                messages.warning(request, _("Cannot set quantity for {game_title} to {quantity}. Only {stock} available. Quantity set to {stock}.").format(game_title=game.title, quantity=quantity, stock=game.stock))
                cart[game_id_str]['quantity'] = game.stock
            else:
                cart[game_id_str]['quantity'] = quantity
                messages.success(request, _("Quantity for {game_title} updated to {quantity}.").format(game_title=game.title, quantity=quantity))
        else: # Quantity is 0 or less, so remove the item
            del cart[game_id_str]
            messages.success(request, _("{game_title} removed from cart.").format(game_title=game.title))
    else:
        messages.info(request, _("Item not found in your cart to update."))

    save_cart(request, cart)
    return redirect('store:cart_detail')


def cart_detail(request):
    cart = get_cart(request)
    cart_items_processed = []
    total_cart_price = 0

    for game_id_str, item_data in cart.items():
        game = get_object_or_404(Game, id=int(game_id_str)) # Fetch game object for up-to-date info if needed (e.g. image_url)
        quantity = item_data['quantity']
        price = float(item_data['price']) # Price stored when added to cart
        total_item_price = quantity * price
        total_cart_price += total_item_price
        cart_items_processed.append({
            'id': game_id_str,
            'game_obj': game, # Pass the actual game object for template flexibility
            'title': item_data['title'],
            'platform': item_data['platform'],
            'quantity': quantity,
            'price': price,
            'total_item_price': total_item_price,
            'cover_image_url': game.cover_image_url # Get current image URL
        })

    return render(request, 'store/cart_detail.html', {
        'cart_items': cart_items_processed,
        'total_cart_price': total_cart_price
    })

@login_required
def checkout(request):
    cart = get_cart(request)
    if not cart:
        messages.error(request, _("Your cart is empty. Please add items before checking out."))
        return redirect('store:cart_detail')

    # Calculate total for display on checkout page (could also be passed from cart_detail if preferred)
    current_total_cart_price = 0
    checkout_items_summary = []
    for game_id_str, item_data in cart.items():
        # It's good to re-fetch game to ensure price or stock hasn't changed critically,
        # but for this step, we'll use price from cart.
        # A more robust system would validate prices and stock here.
        game = get_object_or_404(Game, id=int(game_id_str))
        quantity = item_data['quantity']

        if quantity > game.stock:
            messages.error(request, _("Sorry, the quantity for {game_title} exceeds available stock ({stock}). Please update your cart.").format(game_title=game.title, stock=game.stock))
            return redirect('store:cart_detail')

        price = float(item_data['price'])
        current_total_cart_price += quantity * price
        checkout_items_summary.append({
            'title': game.title,
            'quantity': quantity,
            'price': price,
            'total_item_price': quantity * price
        })


    if request.method == 'POST':
        try:
            with transaction.atomic(): # Ensure all database operations are atomic
                order = Order.objects.create(user=request.user)

                for game_id_str, item_data in cart.items():
                    game = get_object_or_404(Game, id=int(game_id_str))
                    quantity = item_data['quantity']
                    price_at_purchase = float(item_data['price']) # Use price stored in cart

                    if quantity <= 0: # Should not happen if cart logic is correct
                        continue

                    if game.stock < quantity:
                        # This is a critical check, even if checked before.
                        # transaction.atomic will roll back previous saves if this fails.
                        raise ValueError(f"Insufficient stock for {game.title} at final checkout.")

                    OrderItem.objects.create(
                        order=order,
                        game=game,
                        quantity=quantity,
                        price_at_purchase=price_at_purchase
                    )

                    # Decrement stock
                    game.stock -= quantity
                    game.save()

                # Clear the cart from session
                request.session['cart'] = {}
                request.session.modified = True

                messages.success(request, _("Your order has been placed successfully!"))
                return redirect('store:order_success', order_id=order.id)

        except ValueError as e: # Catch stock error specifically
            messages.error(request, str(e)) # This error comes from a raise with f-string, already formatted. For custom error, use _().
            return redirect('store:cart_detail') # Redirect to cart to resolve stock issue
        except Exception as e:
            messages.error(request, _("An unexpected error occurred: {error_message}. Please try again.").format(error_message=str(e)))
            # Log the error e for admin review
            return redirect('store:checkout') # Or some other error page

    return render(request, 'store/checkout.html', {
        'cart_items': checkout_items_summary, # For display on checkout page
        'total_cart_price': current_total_cart_price
    })

@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user) # Ensure user owns the order
    return render(request, 'store/order_success.html', {'order': order})
