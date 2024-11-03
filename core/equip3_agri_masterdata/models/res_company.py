from odoo import models, fields, api, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    crop_default_uom_id = fields.Many2one('uom.uom', string='Area Unit of Measure')
