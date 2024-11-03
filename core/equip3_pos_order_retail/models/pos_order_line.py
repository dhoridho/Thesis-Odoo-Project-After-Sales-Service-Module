from odoo import api, fields, models, _

class PosOrderLine(models.Model):
	_inherit = "pos.order.line"

	item_state = fields.Selection([('ordered', 'Ordered'),('cancelled', 'Cancelled')],
        string='Item State',
        required=1,
        default='ordered'
    )