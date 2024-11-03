from odoo import models, fields, api


class ChecksheetDimensions(models.Model):
    _name = 'checksheet.dimensions'
    _description = 'Checksheet Dimensions'

    name = fields.Char('Dimensions')


