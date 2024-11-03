
from odoo import api, fields, models, _


class ApprovalMatrixPurchaseRequest(models.Model):
    _inherit = 'approval.matrix.purchase.request'
    
    order_type = fields.Selection(selection_add=[
                    ('assets_order', 'Assets Order')
                ])
