from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    dedicated_material_consumption = fields.Boolean(related='company_id.dedicated_material_consumption', readonly=False)
