from odoo import api, fields, models


class MaintenanceType(models.Model):
    _name = 'maintenance.type'
    _description = 'Maintenance Type'

    name = fields.Char(string='Type Name', required=True, copy=False)
    
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'The name must be unique!'),
    ]
