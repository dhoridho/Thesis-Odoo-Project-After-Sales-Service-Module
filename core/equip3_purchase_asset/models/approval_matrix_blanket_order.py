
from odoo import api, fields, models, _


class ApprovalMatrixBlanketOrder(models.Model):
    _inherit = 'approval.matrix.blanket.order'
    
    order_type = fields.Selection(
                    selection_add=[
                    ('assets_order', 'Assets Order')
                ])
