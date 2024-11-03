
from odoo import api, fields, models, _


class ApprovalMatrixDirectPurchase(models.Model):
    _inherit = 'approval.matrix.direct.purchase'
    
    order_type = fields.Selection(
                    selection_add=[
                    ('assets_order', 'Assets Order')
                ])
