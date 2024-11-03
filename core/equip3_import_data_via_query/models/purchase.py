from odoo import api, fields, models

class purchase_order(models.Model):
    _inherit = 'purchase.order'

    import_reference = fields.Char(string="Import Reference")

purchase_order()