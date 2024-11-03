from odoo import models, fields


class PurchaseRequest(models.Model):
	_inherit = 'purchase.request'

	assembly_id = fields.Many2one('assembly.production.record', 'Assembly Production', copy=False)
	is_readonly_origin = fields.Boolean()
