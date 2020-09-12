from django.contrib import admin

from utils.generals import get_model

# Register your models here.
Bank = get_model('commerce', 'Bank')
PaymentBank = get_model('commerce', 'PaymentBank')
DeliveryAddress = get_model('commerce', 'DeliveryAddress')
Product = get_model('commerce', 'Product')
ProductAttachment = get_model('commerce', 'ProductAttachment')
Cart = get_model('commerce', 'Cart')
CartItem = get_model('commerce', 'CartItem')
Chat = get_model('commerce', 'Chat')
ChatMessage = get_model('commerce' ,'ChatMessage')
ChatAttachment = get_model('commerce', 'ChatAttachment')
WishList = get_model('commerce', 'WishList')
Order = get_model('commerce', 'Order')
OrderItem = get_model('commerce', 'OrderItem')
Notification = get_model('commerce', 'Notification')


# extend Product
class ProductAttachmentInline(admin.StackedInline):
    model = ProductAttachment


class ProductExtend(admin.ModelAdmin):
    model = Product
    inlines = [ProductAttachmentInline,]


# extend Cart
class CartItemInline(admin.StackedInline):
    model = CartItem


class CartExtend(admin.ModelAdmin):
    model = Cart
    inlines = [CartItemInline,]


# extend Order
class OrderItemInline(admin.StackedInline):
    model = OrderItem


class OrderExtend(admin.ModelAdmin):
    model = Order
    inlines = [OrderItemInline,]


admin.site.register(Bank)
admin.site.register(PaymentBank)
admin.site.register(DeliveryAddress)
admin.site.register(Product, ProductExtend)
admin.site.register(ProductAttachment)
admin.site.register(Cart, CartExtend)
admin.site.register(CartItem)
admin.site.register(Chat)
admin.site.register(ChatMessage)
admin.site.register(ChatAttachment)
admin.site.register(WishList)
admin.site.register(Order, OrderExtend)
admin.site.register(Notification)
