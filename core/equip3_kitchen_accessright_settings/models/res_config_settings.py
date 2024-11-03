from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_central_kitchen_byproducts = fields.Boolean("Central Kitchen By-Products", implied_group='equip3_kitchen_accessright_settings.group_central_kitchen_byproducts')
