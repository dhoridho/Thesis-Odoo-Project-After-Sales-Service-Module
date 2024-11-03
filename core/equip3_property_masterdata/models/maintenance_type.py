from odoo import models, fields, api

class PropertyMaintenanceType(models.Model):
    _name = 'property.maintenance.type'
    _description = 'Maintenance Type'

    name = fields.Char(string='Name', required=True)
    operation_type = fields.Selection(string='Operation Type', selection=[('service', 'Service'), ('repair', 'Repair'),], required=True)
