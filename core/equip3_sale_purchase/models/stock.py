from odoo import models, fields

class StockPickingInherit(models.Model):
    _inherit = 'stock.picking'

    is_dropship = fields.Boolean(string='Is Dropship', readonly=True)
    customer_partner_id = fields.Many2one(comodel_name='res.partner', string='Customer', readonly=True)