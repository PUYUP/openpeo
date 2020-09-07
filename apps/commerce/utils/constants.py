from django.utils.translation import gettext_lazy as _

# generals
DELIVER = 'deliver'
REJECTED = 'rejected'
CANCELED = 'canceled'

PENDING = 'pending'
CONFIRMED = 'confirmed'
PAYED = 'payed'
DONE = 'done'
ORDER_STATUS = (
    (PENDING, _(u"Tertunda")),
    (CONFIRMED, _(u"Terkonfirmasi")),
    (PAYED, _(u"Lunas")),
    (DELIVER, _(u"Diantar")),
    (REJECTED, _("Ditolak")),
    (CANCELED, _("Dibatalkan")),
    (DONE, _(u"Selesai")),
)


NEW = 'new'
ACCEPTED = 'accepted'
PAYMENT_CONFIRMATION = 'payment_confirmation'
PAYMENT_CONFIRMED = 'payment_confirmed'
NOTIFICATION_TYPES = (
    (NEW, _("Pesanan Baru")),
    (ACCEPTED, _("Diterima")),
    (REJECTED, _("Ditolak")),
    (CANCELED, _("Dibatalkan")),
    (PAYMENT_CONFIRMATION, _("Payment Confirmation")),
    (PAYMENT_CONFIRMED, _("Payment Confirmed")),
    (DONE, _(u"Selesai")),
)
