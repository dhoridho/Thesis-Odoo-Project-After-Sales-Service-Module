
from odoo import api, fields, models, _


class ApprovalMatrixPurchaseOrder(models.Model):
    _inherit = 'approval.matrix.purchase.order'
    
    order_type = fields.Selection(
                    selection_add=[
                    ('assets_order', 'Assets Order')
                ])
