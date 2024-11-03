from odoo import api, fields, models

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    import_reference = fields.Char(string="Import Reference")
    purchase_id = fields.Many2one('purchase.order', related='move_lines.purchase_line_id.order_id',
        string="Purchase Orders", readonly=True, store=True)