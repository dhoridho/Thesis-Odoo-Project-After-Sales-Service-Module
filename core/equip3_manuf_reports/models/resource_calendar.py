from odoo import models, api


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    def cycle_attendances(self, dt):
        self.ensure_one()
        attendances = sorted(self.attendance_ids, 
            key=lambda a: (
                (
                    (int(a.dayofweek) - dt.weekday() + 1) if int(a.dayofweek) >= dt.weekday() 
                    else 8 - dt.weekday() + int(a.dayofweek)
                ) * 100
            ) + a.hour_from
            )
        for i, att in enumerate(attendances):
            if int(att.dayofweek) == dt.weekday() and  att.hour_from <= dt.hour <= att.hour_to:
                break
        attendances = attendances[i:] + attendances[:i]
        return attendances
