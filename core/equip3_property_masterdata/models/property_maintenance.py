from odoo import models, fields, api

class PropertyMaintanance(models.Model):
    _inherit = 'property.maintanance'

    maintenance_type_id = fields.Many2one(comodel_name='property.maintenance.type', string='Maintenance Type', required=True)
    