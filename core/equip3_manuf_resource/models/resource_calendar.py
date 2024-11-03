from odoo import models, fields, api, _
from odoo.addons.resource.models.resource import Intervals, HOURS_PER_DAY
from pytz import timezone, utc
from collections import defaultdict


def datetime_to_string(dt):
    """ Convert the given datetime (converted in UTC) to a string value. """
    return fields.Datetime.to_string(dt.astimezone(utc))


def string_to_datetime(value):
    """ Convert the given string value to a datetime in UTC. """
    return utc.localize(fields.Datetime.from_string(value))


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    calendar_type = fields.Selection(selection=[
        ('default', 'Default'),
        ('mrp', 'Production')
    ], default='default', string='Calendar Type')
    mrp_company_id = fields.Many2one('res.company', string='MRP Company')
    source_calendar_id = fields.Many2one('resource.calendar', string='MRP Source Calendar')

    @api.model
    def default_get(self, fields):
        res = super(ResourceCalendar, self).default_get(fields)
        if 'calendar_type' in res and res['calendar_type'] == 'mrp':
            source_calendar = self.browse(res.get('source_calendar_id', False))

            if source_calendar:
                res.update(source_calendar._get_vals_from_source())

        return res

    @api.onchange('calendar_type', 'mrp_company_id')
    def _onchange_calendar_type(self):
        if self.calendar_type == 'mrp':
            self.company_id = self.mrp_company_id.id

    @api.onchange('calendar_type', 'source_calendar_id')
    def _onchange_source_calendar(self):
        if self.calendar_type == 'mrp':
            self.update(self.source_calendar_id._get_vals_from_source())

    def _get_vals_from_source(self):
        self.ensure_one()

        attendance_vals = [(5,)]
        for attendance in self.attendance_ids:
            if attendance.break_from > attendance.hour_from:
                attendance_vals += [(0, 0, {
                    'name': attendance.name, 
                    'dayofweek': attendance.dayofweek, 
                    'hour_from': attendance.hour_from, 
                    'hour_to': attendance.break_from, 
                    'day_period': attendance.day_period
                })]

            if attendance.hour_to > attendance.break_to:
                attendance_vals += [(0, 0, {
                    'name': attendance.name, 
                    'dayofweek': attendance.dayofweek, 
                    'hour_from': max(attendance.break_to, attendance.hour_from), 
                    'hour_to': attendance.hour_to, 
                    'day_period': attendance.day_period
                })]

        global_leave_vals = [(5,)]
        for leave in self.global_leave_ids:
            global_leave_vals += [(0, 0, leave._copy_leave_vals())]

        group = defaultdict(lambda: 0)
        for item in attendance_vals:
            if item[0] != 0:
                continue
            vals = item[-1]
            group[vals['dayofweek']] += vals['hour_to'] - vals['hour_from']

        hours_per_day = HOURS_PER_DAY
        if group:
            hours_per_day = sum(group.values()) / len(group)

        return {
            'attendance_ids': attendance_vals,
            'global_leave_ids': global_leave_vals,
            'hours_per_day': hours_per_day,
            'tz': self.tz
        }

    def _leave_intervals_batch(self, start_dt, end_dt, resources=None, domain=None, tz=None):
        """ Return the leave intervals in the given datetime range.
            The returned intervals are expressed in specified tz or in the calendar's timezone.
        """
        resources = self.env['resource.resource'] if not resources else resources
        assert start_dt.tzinfo and end_dt.tzinfo
        self.ensure_one()

        # for the computation, express all datetimes in UTC
        resources_list = list(resources) + [self.env['resource.resource']]
        resource_ids = [r.id for r in resources_list]
        if domain is None:
            domain = [('time_type', '=', 'leave')]
        domain = domain + [
            ('calendar_id', '=', self.id),
            ('resource_id', 'in', resource_ids),
            ('date_from', '<=', datetime_to_string(end_dt)),
            ('date_to', '>=', datetime_to_string(start_dt)),
        ]

        # retrieve leave intervals in (start_dt, end_dt)
        result = defaultdict(lambda: [])
        tz_dates = {}
        for leave in self.env['resource.calendar.leaves'].search(domain):
            for resource in resources_list:
                if leave.resource_id.id not in [False, resource.id]:
                    continue
                tz = tz if tz else timezone((resource or self).tz)
                if (tz, start_dt) in tz_dates:
                    start = tz_dates[(tz, start_dt)]
                else:
                    start = start_dt.astimezone(tz)
                    tz_dates[(tz, start_dt)] = start
                if (tz, end_dt) in tz_dates:
                    end = tz_dates[(tz, end_dt)]
                else:
                    end = end_dt.astimezone(tz)
                    tz_dates[(tz, end_dt)] = end
                try:
                    dt0 = string_to_datetime(leave.datetime_from).astimezone(tz)
                    dt1 = string_to_datetime(leave.datetime_to).astimezone(tz)
                except AttributeError:
                    dt0 = string_to_datetime(leave.date_from).astimezone(tz)
                    dt1 = string_to_datetime(leave.date_to).astimezone(tz)
                result[resource.id].append((max(start, dt0), min(end, dt1), leave))

        return {r.id: Intervals(result[r.id]) for r in resources_list}


class ResourceCalendarLeaves(models.Model):
    _inherit = 'resource.calendar.leaves'

    datetime_from = fields.Datetime(string='Datetime From')
    datetime_to = fields.Datetime(string='Datetime To')

    @api.model
    def create(self, vals):
        if not vals.get('datetime_from'):
            vals['datetime_from'] = vals.get('date_from', False)
        if not vals.get('datetime_to'):
            vals['datetime_to'] = vals.get('date_to', False)
        return super(ResourceCalendarLeaves, self).create(vals)
