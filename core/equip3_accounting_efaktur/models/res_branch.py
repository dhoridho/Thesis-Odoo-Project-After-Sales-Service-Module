from odoo import models, fields, api, _

class ResBranch(models.Model):
    _inherit = 'res.branch'

    npwp = fields.Char('NPWP')