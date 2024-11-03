
from odoo import models, fields, api

class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'

    is_rename = fields.Boolean('Is Rename')
