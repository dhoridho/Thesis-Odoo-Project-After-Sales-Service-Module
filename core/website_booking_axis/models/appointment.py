# -*- coding: utf-8 -*-

from odoo import models, fields, api


class appointment_booking(models.Model):
    _name = 'appointment'
    _description = 'appointment'

    customer = fields.Many2one('res.partner', string='Customer')
    appointment_group_id = fields.Many2one('appointment.group', string='Appointment Group')
    appoint_person_id = fields.Many2one('res.partner', string='Appointees')
    time_slot = fields.Many2one('appointment.timeslot', string='Time Slot')
    appoint_date = fields.Date(string="Appointment Date")
    source = fields.Many2one('appointment.source', string='Source')
    create_date = fields.Datetime(string='Create Date')
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')
    product_id = fields.Many2one('product.product', string='Product')
    description = fields.Text()
    price_unit = fields.Float()
    tax_id = fields.Many2many('account.tax', string='Tax')
    price_subtotal = fields.Float(string='Subtotal')
    address_id = fields.Char(string='Address')
    email_id = fields.Char(string='Email')
    mobile_number = fields.Char(string='Mobile Number')

class Partner(models.Model):
    _inherit = 'res.partner'

    last_name = fields.Char(string='Last name',required=True)
    appointment_group_ids = fields.Many2many('appointment.group')
    title = fields.Many2one('res.partner.title', string='Title')
    appointment_charge = fields.Float(string='Appointment Charge')
    appoint_product_id = fields.Many2one('product.template', string='Appointee Product')
    work_exp = fields.Char(string='Work Experience')
    specialist = fields.Char(string='Specialist')
    slot_ids = fields.Many2many('calendar.appointment.slot')
    appointment_type = fields.Many2one('calendar.appointment.type', string="Appointment Type")
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict', required=True)
    start_datetime = fields.Datetime(string="Appointment Date")
    @api.onchange('appointment_type')
    def _onchange_parnter(self):
        partner = self.env['calendar.appointment.type'].sudo().search([('name','=',self.appointment_type.name)])
        self.slot_ids = partner.slot_ids

    def calendar_verify_availability(self, date_start, date_end):
        """ verify availability of the partner(s) between 2 datetimes on their calendar
        """
        if bool(self.env['calendar.event'].search_count([
            ('partner_ids', 'in', self.ids),
            '|', '&', ('start_datetime', '<', fields.Datetime.to_string(date_end)),
                      ('stop_datetime', '>', fields.Datetime.to_string(date_start)),
                 '&', ('allday', '=', True),
                      '|', ('start_date', '=', fields.Date.to_string(date_end)),
                           ('start_date', '=', fields.Date.to_string(date_start))])):
            return False
        return True
