from odoo import api, models, fields


class ConfirmationDownPaymentPurchase(models.TransientModel):
    _inherit = 'confirm.downpayment.purchase'

