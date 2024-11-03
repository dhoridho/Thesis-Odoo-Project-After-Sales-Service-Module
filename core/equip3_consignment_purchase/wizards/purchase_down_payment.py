from odoo import models, fields, api, _

class PurchaseDownPayment(models.TransientModel):
    _inherit = 'purchase.down.payment'

    down_payment_by = fields.Selection(selection_add=[
        ('bill', 'Bill Base on sold Quantity')
    ])

    down_payment_by_ordered = fields.Selection(selection='_get_customer_type')
    
    def _get_customer_type(self):
        context = dict(self.env.context) or {}
        purchase_id = self.env['purchase.order'].browse(context.get('active_ids'))
        if purchase_id.is_consignment:
            return [('dont_deduct_down_payment', 'Billable lines'),
                    ('percentage', 'Advance payment (percentage)'),
                    ('fixed', 'Advance payment (fixed amount)'),
                    ('bill', 'Bill Base on sold Quantity')]
        else:
            return [('dont_deduct_down_payment', 'Billable lines'),
                    ('percentage', 'Advance payment (percentage)'),
                    ('fixed', 'Advance payment (fixed amount)')]