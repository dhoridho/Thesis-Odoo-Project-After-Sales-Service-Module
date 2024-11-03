# -*- coding: utf-8 -*-
from odoo import api, fields, models,_
from datetime import datetime, date, timedelta
from odoo.exceptions import UserError

class OtBooking(models.Model):
    _name = 'acs.ot.booking'
    _description = "OT Booking"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def _get_end_date(self):
        return datetime.now() + timedelta(hours=2)

    STATES={'cancel': [('readonly', True)], 'confirm': [('readonly', True)]}

    name = fields.Char(string="Name", required=True, readonly=True, default='New', copy=False)
    patient_id = fields.Many2one('hms.patient', 'Patient', required="True", states=STATES)
    image_128 = fields.Binary(related='patient_id.image_128', string='Image', readonly=True)
    start_date = fields.Datetime('Start Date', default=fields.Datetime.now, states=STATES)
    end_date = fields.Datetime('End Date', default=_get_end_date, states=STATES)
    hospitalization_id = fields.Many2one('acs.hospitalization', string='Hospitalization', states=STATES)
    surgery_template_id = fields.Many2one('hms.surgery.template', string='Surgery Template', states=STATES)
    surgery_id = fields.Many2one('hms.surgery', string='Surgery', states=STATES, copy=False)
    note = fields.Text('Note', states=STATES)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('cancel', 'Canceled')], string='Status', default='draft')
    ot_id = fields.Many2one('acs.hospital.ot','Operation Theater', states=STATES, required=True)

    def unlink(self):
        for data in self:
            if data.state in ['confirm']:
                raise UserError(_('You can not delete record in confirmed state'))
        return super(OtBooking, self).unlink()

    def button_confirm(self):
        self.state = 'confirm'
        if not self.surgery_template_id:
            raise UserError(_('Please set Surgery First.'))
        self.name = self.env['ir.sequence'].next_by_code('acs.ot.booking') or ''
        self.surgery_id = self.env['hms.surgery'].create({
            'surgery_template_id': self.surgery_template_id.id,
            'patient_id': self.patient_id.id,
            'surgery_name': self.surgery_template_id.surgery_name,
            'surgery_product_id': self.surgery_template_id.surgery_product_id.id,
            'hospitalization_id': self.hospitalization_id and self.hospitalization_id.id or False,
            'hospital_ot': self.ot_id.id,
            'start_date': self.start_date,
            'end_date': self.end_date,
        })

    def button_cancel(self):
        self.state = 'cancel'

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: