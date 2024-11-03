from odoo import _, api, fields, models


class SchoolHrContract(models.Model):
    _inherit = "hr.contract"

    rate_per_hour = fields.Monetary('Rate Per Hour')
    rate_per_class = fields.Monetary('Rate Per Classes')
    
