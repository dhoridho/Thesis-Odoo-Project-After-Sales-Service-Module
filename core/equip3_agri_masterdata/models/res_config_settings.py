from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    crop_default_uom_id = fields.Many2one('uom.uom', related='company_id.crop_default_uom_id', readonly=False)
