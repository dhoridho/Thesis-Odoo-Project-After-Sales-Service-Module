from odoo import _, api, fields, models
from datetime import datetime
from odoo.exceptions import ValidationError


class HashmicroResCountryInherit(models.Model):
    _inherit = 'res.country.state'
    minimum_wage = fields.Float("Minimum Wage")