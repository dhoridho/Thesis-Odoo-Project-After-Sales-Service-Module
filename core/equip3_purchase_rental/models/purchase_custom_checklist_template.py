
from odoo import api, fields, models, _


class PurchaseCustomChecklistTemplate(models.Model):
    _inherit = 'purchase.custom.checklist.template'
    
    order = fields.Selection(selection_add=[
                    ('rental_order', 'Rental Orders')
                ])
