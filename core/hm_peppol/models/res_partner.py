
from odoo import models, fields, api

class res_partner(models.Model):
    _inherit = 'res.partner'

    peppol_id = fields.Char('PEPPOL ID')
    is_peppol = fields.Boolean('PEPPOL Group', default=False)

