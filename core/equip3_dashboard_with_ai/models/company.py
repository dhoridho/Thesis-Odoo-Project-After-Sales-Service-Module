from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ResCompany(models.Model):
    _inherit = 'res.company'

    izi_lab_api_key = fields.Char('AI API Key')


class IZILabAPIKeyWizard(models.TransientModel):
    _inherit = 'izi.lab.api.key.wizard'
    _description = 'AI Lab API Key Wizard'

    izi_lab_api_key = fields.Char('AI API Key')

