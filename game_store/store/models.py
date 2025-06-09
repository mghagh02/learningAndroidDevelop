from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Platform(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Game(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE, related_name='games')
    genres = models.ManyToManyField(Genre, related_name='games')
    stock = models.PositiveIntegerField(default=0)
    release_date = models.DateField()
    cover_image_url = models.URLField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.platform.name})"

class NewsArticle(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    publication_date = models.DateTimeField(default=timezone.now)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True) # Or models.CASCADE if author is mandatory and deleting user deletes their articles
    image_url = models.URLField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-publication_date']

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    ordered_date = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)
    # total_price will be calculated dynamically or stored upon completion
    # For now, we can add a method to calculate it.
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"

    @property
    def total_price(self):
        return sum(item.total_item_price for item in self.items.all())

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    game = models.ForeignKey(Game, on_delete=models.PROTECT) # PROTECT so we don't delete games that are part of an order
    quantity = models.PositiveIntegerField(default=1)
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2) # Price of the game when the order was made
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.quantity} of {self.game.title} in Order {self.order.id}"

    @property
    def total_item_price(self):
        return self.quantity * self.price_at_purchase
