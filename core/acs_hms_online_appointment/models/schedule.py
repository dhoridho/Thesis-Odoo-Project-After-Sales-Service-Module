# -*- coding: utf-8 -*-

import datetime
from datetime import time, timedelta
from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare
from odoo.exceptions import UserError
import pytz
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT,DEFAULT_SERVER_DATE_FORMAT
import math
from pytz import timezone, utc
from odoo.tools.float_utils import float_round
from odoo.addons.base.models.res_partner import _tz_get

import logging
_logger = logging.getLogger(__name__)


def float_to_time(hours):
    """ Convert a number of hours into a time object. """
    if hours == 24.0:
        return time.max
    fractional, integral = math.modf(hours)
    int_fractional = int(float_round(60 * fractional, precision_digits=0))
    if int_fractional > 59:
        integral += 1
        int_fractional = 0
    return time(int(integral), int_fractional, 0)


class Appointmentschedule(models.Model):
    _name = "appointment.schedule"
    _description = "Appointment schedule"

    def _get_default_schedule_lines(self):
        return [
            (0, 0, {'name': _('Monday Morning'), 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
            (0, 0, {'name': _('Monday Evening'), 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
            (0, 0, {'name': _('Tuesday Morning'), 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
            (0, 0, {'name': _('Tuesday Evening'), 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
            (0, 0, {'name': _('Wednesday Morning'), 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
            (0, 0, {'name': _('Wednesday Evening'), 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
            (0, 0, {'name': _('Thursday Morning'), 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
            (0, 0, {'name': _('Thursday Evening'), 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
            (0, 0, {'name': _('Friday Morning'), 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
            (0, 0, {'name': _('Friday Evening'), 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'})
        ]

    def _get_booking_price(self):
        for rec in self:
            appointment_price = self.env.user.sudo().company_id.consultation_product_id and self.env.user.sudo().company_id.consultation_product_id.lst_price
            if rec.physician_id:
                appointment_price = rec.physician_id.consultaion_service_id and rec.physician_id.consultaion_service_id.lst_price
            elif rec.department_id:
                appointment_price = rec.department_id.consultaion_service_id and rec.department_id.consultaion_service_id.lst_price
            rec.appointment_price = appointment_price

    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', string='Company', 
        default=lambda self: self.env.user.company_id.id)
    schedule_lines = fields.One2many(
        'appointment.schedule.lines', 'schedule_id', string='schedule Lines',
        copy=True, default=_get_default_schedule_lines)
    appointment_tz = fields.Selection(
        _tz_get, string='Timezone', required=True, default=lambda self: self.env.user.tz,
        help="Timezone where appointment take place")
    department_id = fields.Many2one('hr.department', domain=[('patient_department', '=', True)])
    physician_id = fields.Many2one('hms.physician', string='Physician', index=True)
    active = fields.Boolean(string="Active", default=True)
    schedule_type = fields.Selection([('appointment','Appointment')], string="Schedule Type", default="appointment")
    show_fee_on_booking = fields.Boolean("Show Fees", default=False)
    appointment_price = fields.Float(compute="_get_booking_price", string="Appointment Fees")


class AppointmentscheduleLines(models.Model):
    _name = "appointment.schedule.lines"
    _description = "Appointment schedule Lines"
    _order = 'dayofweek, hour_from'



    name = fields.Char(required=True)
    dayofweek = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday')
        ], 'Day of Week', required=True, index=True, default='0')
    hour_from = fields.Float(string='Work from', required=True, index=True, help="Start and End time of working.")
    hour_to = fields.Float(string='Work to', required=True)
    day_period = fields.Selection([('morning', 'Morning'), ('afternoon', 'Afternoon')], required=True, default='morning')
    schedule_id = fields.Many2one("appointment.schedule", string="Appointment schedule", required=True, ondelete="cascade")
    show_fee_on_booking = fields.Boolean(related="schedule_id.show_fee_on_booking", string="Show Fees", default=False, store=True)


class AppointmentscheduleSlot(models.Model):
    _name = "appointment.schedule.slot"
    _description = "Appointment Schedule Slot"
    _rec_name = 'slot_date'

    slot_date = fields.Date(string='Slot Date')
    appointment_tz = fields.Selection(_tz_get, string='Timezone', required=True, default=lambda self: self.env.user.tz,
        help="Timezone where appointment take place")
    slot_ids = fields.One2many('appointment.schedule.slot.lines', 'slot_id', string="Slot Lines")
    department_id = fields.Many2one('hr.department', domain=[('patient_department', '=', True)])
    physician_id = fields.Many2one('hms.physician', string='Physician', index=True)
    schedule_id = fields.Many2one("appointment.schedule", string="Appointment schedule", required=True, ondelete="cascade")
    show_fee_on_booking = fields.Boolean(related="schedule_id.show_fee_on_booking", string="Show Fees", default=False, store=True)

    _sql_constraints = [('slot_date_unique', 'UNIQUE(slot_date, schedule_id)', 'Appointment slot must be unique!')]


    def _create_slot_interval(self, slot, start_dt, hour_from, hour_to, booking_slot_time):
        #assert start_dt.tzinfo
        combine = datetime.datetime.combine
        SlotLine = self.env['appointment.schedule.slot.lines']

        # express all dates and times in the resource's timezone
        tz = timezone(slot.appointment_tz or self.env.user.tz)

        start = start_dt #.date()
        #run_time = hour_from
        while (hour_from < hour_to):
            time_hour_from = float_to_time(hour_from)
            hour_from += booking_slot_time/60
            time_hour_to = float_to_time(hour_from)

            # hours are interpreted in the resource's timezone
            start_date = tz.localize(combine(start, time_hour_from)).astimezone(pytz.utc).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            end_date = tz.localize(combine(start, time_hour_to)).astimezone(pytz.utc).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

            SlotLine.create({
                'from_slot': start_date,
                'to_slot': end_date,
                'slot_id': slot.id,
            })

        return True

    @api.model
    def create_appointment_slot(self, slot_date, schedule):
        ScheduleLines = self.env['appointment.schedule.lines']
        booking_slot_time = self.env.user.sudo().company_id.booking_slot_time
        weekday = slot_date.weekday()
        slot = self.env['appointment.schedule.slot'].create({
            'slot_date': slot_date.strftime(DEFAULT_SERVER_DATE_FORMAT),
            'appointment_tz': schedule.appointment_tz,
            'schedule_id': schedule.id,
            'physician_id': schedule.physician_id and schedule.physician_id.id or False,
            'department_id': schedule.department_id and schedule.department_id.id or False,
        })
        for line in ScheduleLines.search([('schedule_id','=',schedule.id),('dayofweek','=',str(weekday))]):
            self._create_slot_interval(slot, slot_date, line.hour_from, line.hour_to, booking_slot_time)

    @api.model
    def weekly_slot_create_cron(self):
        ScheduleSlot = self.env['appointment.schedule.slot']
        # get day of next week
        next_slot = datetime.datetime.now().date() + datetime.timedelta(days=self.env.user.sudo().company_id.allowed_booking_per_slot)
        schedules = self.env['appointment.schedule'].search([])
        for schedule in schedules:
            slot_found = ScheduleSlot.search([('schedule_id','=',schedule.id), ('slot_date','=',next_slot.strftime(DEFAULT_SERVER_DATE_FORMAT))])
            if slot_found:
                _logger.warning('Appointment Slot exist for date %s.' % slot_found.slot_date)
            else:
                self.create_appointment_slot(next_slot, schedule)


class AppointmentscheduleSlotLines(models.Model):
    _name = "appointment.schedule.slot.lines"
    _description = "Appointment schedule Slot Lines"
    _order = 'from_slot'

    @api.depends('from_slot','to_slot')
    def _get_slot_name(self):
        for rec in self:
            name = ''
            if rec.id and rec.from_slot and rec.to_slot:
                tz_info = pytz.timezone(rec.slot_id.appointment_tz or self.env.user.tz or self.env.context.get('tz')  or 'UTC')
                from_slot = pytz.UTC.localize(rec.from_slot.replace(tzinfo=None), is_dst=False).astimezone(tz_info).replace(tzinfo=None)
                to_slot = pytz.UTC.localize(rec.to_slot.replace(tzinfo=None), is_dst=False).astimezone(tz_info).replace(tzinfo=None)
                name = from_slot.strftime("%H:%M") + ' - ' + to_slot.strftime("%H:%M")
            rec.name = name

    @api.depends('appointment_ids','appointment_ids.state')
    def _limit_count(self):
        for slot in self:
            slot.rem_limit = slot.limit - len(self.env['hms.appointment'].search([('schedule_slot_id','=',slot.id),('state','!=','canceled')]))

    name = fields.Char(string='name', compute='_get_slot_name')
    from_slot = fields.Datetime(string='Starting Slot')
    to_slot = fields.Datetime(string='End Slot')
    limit = fields.Integer(string='Limit', default=lambda self: self.env.user.company_id.allowed_booking_per_slot)
    rem_limit = fields.Integer(compute="_limit_count",string='Remaining Limit',store=True)
    slot_id = fields.Many2one('appointment.schedule.slot', string="Slot", ondelete="cascade")
    appointment_ids = fields.One2many('hms.appointment', 'schedule_slot_id', string="Appointment")
