from django.utils.translation import gettext_lazy as _


PENDING = 'pending'
CONFIRMED = 'confirmed'
PAYED = 'payed'
DELIVER = 'deliver'
DONE = 'done'
ORDER_STATUS = (
    (PENDING, _(u"Tertunda")),
    (CONFIRMED, _(u"Terkonfirmasi")),
    (PAYED, _(u"Lunas")),
    (DELIVER, _(u"Diantar")),
    (DONE, _(u"Selesai")),
)
