# -*- encoding: utf-8 -*-
from odoo import api, fields, models,_
from datetime import datetime
from datetime import timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT,DEFAULT_SERVER_DATE_FORMAT


class Appointment(models.Model):
    _inherit = 'hms.appointment'

    @api.depends('date')
    def _get_schedule_date(self):
        for rec in self:
            rec.schedule_date = rec.date.date()

    READONLY_STATES = {'cancel': [('readonly', True)], 'done': [('readonly', True)]}
    schedule_date = fields.Date(string='Schedule Date', compute="_get_schedule_date", store=True, states=READONLY_STATES)
    schedule_slot_id = fields.Many2one('appointment.schedule.slot.lines', string = 'Schedule Slot', states=READONLY_STATES)
    booked_online = fields.Boolean('Booked Online', states=READONLY_STATES)

    @api.model
    def clear_appointment_cron(self):
        if self.env.user.company_id.allowed_booking_payment:
            appointments = self.search([('booked_online','=', True),('invoice_id.state','!=','paid'),('state','=','draft')])
            for appointment in appointments:
                #cancel appointment after 20 minute if not paid
                create_time = appointment.create_date + timedelta(minutes=20)
                if create_time <= datetime.now():
                    appointment.invoice_id.action_invoice_cancel()
                    appointment.state = 'cancel'

    #To Avoid code duplication in mobile api.
    def get_slot_data(self, physician_id, department_id, date=False, schedule_type="appointment"):
        if date:
            domain = [('slot_date','=', date)]
        else:
            last_date = fields.Date.today() + timedelta(days=self.env.user.sudo().company_id.allowed_booking_online_days)
            domain = [('slot_date','>=',fields.Date.today()),('slot_date','<=',last_date)]
        
        if physician_id:
            domain += [('physician_id', '=', int(physician_id))]
        if department_id:
            domain += [('department_id', '=', int(department_id))]

        domain += [('schedule_id.schedule_type', '=', schedule_type)]
        slots = self.env['appointment.schedule.slot'].sudo().search(domain)
        slot_data = {}
        for slot in slots:
            slot_lines = slot.slot_ids.filtered(lambda r: r.rem_limit >=1)
            slot_lines_data = []
            for sl in slot_lines:
                slot_lines_data.append({
                    'id': sl.id,
                    'name': sl.name,
                })

            slot_data[slot.id] = {
                'date': slot.slot_date, 
                'id': slot.id, 
                'physician_id': slot.physician_id.id,
                'physician_name': slot.physician_id and slot.physician_id.name or '',
                'slots': slot_lines,
                'slots_data': slot_lines_data,
                'fees': slot.schedule_id.appointment_price,
                'show_fees': slot.schedule_id.show_fee_on_booking,
            }
        return slot_data


class HrDepartment(models.Model):
    _inherit = "hr.department"

    allowed_online_booking = fields.Boolean("Allowed Online Booking", default=False)
    basic_info = fields.Char("Basic Info", help="Publish on Website")
    image = fields.Binary(string='Image')
    allow_home_appointment = fields.Boolean("Allowed Home Visit Booking", default=False)
    show_fee_on_booking = fields.Boolean("Show Fees", default=False)


class HmsPhysician(models.Model):
    _inherit = "hms.physician"

    allowed_online_booking = fields.Boolean("Allowed Online Booking", default=False)
    basic_info = fields.Char("Basic Info", help="Publish on Website")
    allow_home_appointment = fields.Boolean("Allowed Home Visit Booking", default=False)
    show_fee_on_booking = fields.Boolean("Show Fees", default=False)
