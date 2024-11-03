
from odoo import api, fields, models, _


class PurchaseRequisition(models.Model):
	_inherit = 'purchase.requisition'
	
	vendor_id = fields.Many2one('res.partner', string="Vendor", domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")