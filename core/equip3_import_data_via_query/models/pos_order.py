from odoo import api, fields, models

class POS_Order(models.Model):
    _inherit = 'pos.order'

    import_reference = fields.Char(string="Import Reference")

    def onchange_amount_all(self):
        for order in self:
            currency = order.pricelist_id.currency_id
            order.amount_paid = sum(payment.amount for payment in order.payment_ids)
            order.amount_return = sum(payment.amount < 0 and payment.amount or 0 for payment in order.payment_ids)
            order.amount_tax = currency.round(
                sum(self._amount_line_tax(line, order.fiscal_position_id) for line in order.lines))
            amount_untaxed = currency.round(sum(line.price_subtotal for line in order.lines))
            order.amount_total = order.amount_tax + amount_untaxed
POS_Order()