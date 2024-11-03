from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    stock_scale_url = fields.Char(string='Scale URL', config_parameter='equip3_inventory_scale.scale_url')
    stock_scale_precision = fields.Integer(string='Scale Precision', config_parameter='equip3_inventory_scale.scale_precision', default=2)
