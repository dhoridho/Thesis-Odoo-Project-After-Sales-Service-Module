
from odoo import models, fields, api

class product_uom(models.Model):
    _inherit = 'uom.uom'

    note = fields.Char('Note ')
    note_detail = fields.Char('Note Detail')
    uom_code = fields.Char(string='UoM Code', help='Code List refer to https://www.peppolguide.sg/billing/codelist/UNECERec20/', )