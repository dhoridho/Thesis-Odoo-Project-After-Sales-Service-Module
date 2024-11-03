
from odoo import api, fields, models, _


class ApprovalMatrixDirectPurchase(models.Model):
    _inherit = 'approval.matrix.direct.purchase'
    
    order_type = fields.Selection(selection_add=[
                    ('rental_order', 'Rental Orders')
                ])
