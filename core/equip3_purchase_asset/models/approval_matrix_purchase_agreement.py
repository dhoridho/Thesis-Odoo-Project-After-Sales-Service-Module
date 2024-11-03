
from odoo import api, fields, models, _


class PurchaseAgreementApprovalMatrix(models.Model):
    _inherit = 'purchase.agreement.approval.matrix'
    
    order_type = fields.Selection(
                    selection_add=[
                    ('assets_order', 'Assets Order')
                ])
