from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
from odoo.exceptions import ValidationError
from pytz import timezone
import json


# Labour usage for progress history wizard
class ProgressHistoryLabourUsage(models.Model):
    _inherit = 'progress.history.labour.usage'

    def _compute_time_left(self):
        for rec in self:
            if not rec.is_add_progress:
                if rec.custom_project_progress == 'timesheet':
                    duration = rec.progress_history_id.current_total_duration
                    time_left = 0
                    if rec.uom_id.name == 'Days':
                        budgeted_duration = rec.temp_time_left * rec.project_task_id.project_id.working_hour_hours * 60
                        time_left += (
                                                 budgeted_duration - duration) / 60 / rec.project_task_id.project_id.working_hour_hours
                    elif rec.uom_id.name == 'Hours':
                        budgeted_duration = rec.temp_time_left * 60
                        time_left += (budgeted_duration - duration) / 60

                    rec.time = time_left
                    rec.temp_time_left = time_left
            else:
                rec.time = rec.temp_time_left

            return super(ProgressHistoryLabourUsage, rec)._compute_time_left()


