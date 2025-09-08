from django.contrib import admin
from .models import Platform, Genre, Game, NewsArticle, Order, OrderItem

# Customized Admin for Game
class GameAdmin(admin.ModelAdmin):
    list_display = ('title', 'platform', 'price', 'stock', 'release_date')
    list_filter = ('platform', 'genres', 'release_date')
    search_fields = ('title', 'description')
    filter_horizontal = ('genres',) # Better widget for ManyToManyToMany

# Customized Admin for NewsArticle
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'publication_date', 'created_at')
    list_filter = ('publication_date', 'author')
    search_fields = ('title', 'content')
    raw_id_fields = ('author',) # Useful if many users

# Inline for OrderItem within Order
class OrderItemInline(admin.TabularInline): # or admin.StackedInline
    model = OrderItem
    raw_id_fields = ('game',) # Easier to select game by ID if many games
    extra = 0 # Number of empty forms to display
    readonly_fields = ('price_at_purchase',) # Price shouldn't be changed after order

# Customized Admin for Order
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'ordered_date', 'is_completed', 'total_price_admin') # Using the property
    list_filter = ('is_completed', 'ordered_date')
    search_fields = ('user__username', 'id')
    inlines = [OrderItemInline]
    readonly_fields = ('ordered_date', 'created_at', 'user') # Also make user readonly after creation

    def total_price_admin(self, obj):
        return f"${obj.total_price:.2f}" # Format total_price property
    total_price_admin.short_description = 'Total Price'


admin.site.register(Platform)
admin.site.register(Genre)
admin.site.register(Game, GameAdmin)
admin.site.register(NewsArticle, NewsArticleAdmin)
admin.site.register(Order, OrderAdmin)
# OrderItem is typically managed via OrderAdmin's inlines, so direct registration is often commented out.
# If you need to manage OrderItems directly for some reason, you can uncomment the line below.
# admin.site.register(OrderItem)
