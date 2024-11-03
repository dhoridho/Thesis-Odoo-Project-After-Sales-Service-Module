from odoo import models,  fields, api, _
from datetime import datetime, date, timedelta
from odoo.exceptions import ValidationError


class CustomerLineInherit(models.Model):
    _inherit = 'customer.line'

    catering_id = fields.Many2one(comodel_name='catering.order', string='Catering Order')


class CateringMenuPlanner(models.Model):
    _inherit = 'catering.menu.planner'

    @api.constrains('from_date','to_date')
    def check_date(self):
        for rec in self:
            if rec.from_date > rec.to_date:
                raise ValidationError("Can't make menu planner if 'To Date' is earlier than 'From Date'")