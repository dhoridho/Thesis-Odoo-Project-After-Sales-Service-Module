
from odoo import models, fields, api

class res_company(models.Model):
    _inherit = 'res.company'

    base_uri = fields.Char('Base URI')
    api_version = fields.Char('API Version')
    api_key = fields.Char('API Key')
    api_secret = fields.Char('API Secret')
    email_to = fields.Many2one(comodel_name="res.partner", string="Email To", required=False, )
    # name_loa_form = fields.Char(string='Form')
    # image_loa_form= fields.Binary('PEPPOL LOA Form')


