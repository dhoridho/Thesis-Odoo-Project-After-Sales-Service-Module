from odoo import _, api, fields, models
from datetime import date, datetime

class SchoolEquipment(models.Model):
    _name = 'school.equipment'
    _description = 'School Equipment'
    _order = "create_date desc"

    name = fields.Char(string="Name", required=True)
    active = fields.Boolean(string="Active")
    color = fields.Integer('Color Index', help='Index of color')
