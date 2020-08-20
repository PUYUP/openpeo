from django.contrib import admin

from utils.generals import get_model

# Register your models here.
Bank = get_model('commerce', 'Bank')
PaymentBank = get_model('commerce', 'PaymentBank')
DeliveryAddress = get_model('commerce', 'DeliveryAddress')
Product = get_model('commerce', 'Product')
ProductAttachment = get_model('commerce', 'ProductAttachment')
Order = get_model('commerce', 'Order')
OrderItem = get_model('commerce', 'OrderItem')
Chat = get_model('commerce', 'Chat')
ChatAttachment = get_model('commerce', 'ChatAttachment')


# extend Product
class ProductAttachmentInline(admin.StackedInline):
    model = ProductAttachment


class ProductExtend(admin.ModelAdmin):
    model = Product
    inlines = [ProductAttachmentInline,]


# extend Order
class OrderItemInline(admin.StackedInline):
    model = OrderItem


class OrderExtend(admin.ModelAdmin):
    model = Order
    inlines = [OrderItemInline,]


# extend Chat
class ChatAttachmentInline(admin.StackedInline):
    model = ChatAttachment


class ChatExtend(admin.ModelAdmin):
    model = Chat
    inlines = [ChatAttachmentInline,]


admin.site.register(Bank)
admin.site.register(PaymentBank)
admin.site.register(DeliveryAddress)
admin.site.register(Product, ProductExtend)
admin.site.register(ProductAttachment)
admin.site.register(Order, OrderExtend)
admin.site.register(OrderItem)
admin.site.register(Chat, ChatExtend)
admin.site.register(ChatAttachment)
