from odoo import models, fields


class StockPicking(models.Model):
    _inherit = "stock.picking"

    is_from_repair_order = fields.Boolean("From Repair Order")
    is_from_import = fields.Boolean(string='Is From Import', default=False, copy=False)
