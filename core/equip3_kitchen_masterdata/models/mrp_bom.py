from odoo import models, fields


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    equip_bom_type = fields.Selection(
        selection_add=[('kitchen', 'Central Kitchen')])
