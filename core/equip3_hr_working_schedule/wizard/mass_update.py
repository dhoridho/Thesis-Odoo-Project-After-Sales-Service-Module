from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import UserError, ValidationError


class mass_update_fixed(models.TransientModel):
    _name = 'mass.update.fixed'

    resource_id = fields.Many2one('resource.calendar', "Resource")
    name = fields.Char('Name')
    hour_from = fields.Float('Work From', required=True)
    hour_to = fields.Float('Work To', required=True)
    grace_time_for_late = fields.Float('Tolerance for Late', required=True)
    break_from = fields.Float('Break From', required=True)
    break_to = fields.Float('Break To', required=True)
    half_day = fields.Boolean('Allow Half Day', required=True)
    minimum_hours = fields.Float(string='Minimum Hours')

    def update_mass_fixed(self):
        active_id = self.env.context.get('active_ids')
        for resource in self.resource_id.browse(active_id):
            for mass in resource.attendance_ids:
                mass.hour_from = self.hour_from
                mass.hour_to = self.hour_to
                mass.grace_time_for_late = self.grace_time_for_late
                mass.break_from = self.break_from
                mass.break_to = self.break_to
                mass.half_day = self.half_day
                mass.minimum_hours = self.minimum_hours
