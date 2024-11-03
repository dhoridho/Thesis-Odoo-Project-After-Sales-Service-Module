# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta

class AcsPatientEvaluation(models.Model):
    _name = 'acs.patient.evaluation'
    _description = "Patient Evaluation"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "id desc"

    @api.depends('height', 'weight')
    def get_bmi_data(self):
        for rec in self:
            bmi = 0
            bmi_state = False
            if rec.height and rec.weight:
                try:
                    bmi = float(rec.weight) / ((float(rec.height) / 100) ** 2)
                except:
                    bmi = 0

                bmi_state = 'normal'
                if bmi < 18.5:
                    bmi_state = 'low_weight'
                elif 25 < bmi < 30:
                    bmi_state = 'over_weight'
                elif bmi > 30:
                    bmi_state = 'obesity'
            rec.bmi = bmi
            rec.bmi_state = bmi_state

    @api.depends('patient_id', 'patient_id.birthday', 'date')
    def get_patient_age(self):
        for rec in self:
            age = ''
            if rec.patient_id.birthday:
                end_data = rec.date or fields.Datetime.now()
                delta = relativedelta(end_data, rec.patient_id.birthday)
                if delta.years <= 2:
                    age = str(delta.years) + _(" Year") + str(delta.months) + _(" Month ") + str(delta.days) + _(" Days")
                else:
                    age = str(delta.years) + _(" Year")
            rec.age = age

    READONLY_STATES = {'cancel': [('readonly', True)], 'done': [('readonly', True)]}

    name = fields.Char(readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='State', default='draft', required=True, copy=False, states=READONLY_STATES)
    date = fields.Datetime(string='Date', default=fields.Datetime.now, states=READONLY_STATES)

    patient_id = fields.Many2one('hms.patient', ondelete='restrict',  string='Patient',
        required=True, index=True, states=READONLY_STATES)
    image_128 = fields.Binary(related='patient_id.image_128',string='Image', readonly=True)
    age = fields.Char(compute="get_patient_age", string='Age', store=True,
        help="Computed patient age at the moment of the evaluation")
    physician_id = fields.Many2one('hms.physician', ondelete='restrict', string='Physician', 
        index=True, states=READONLY_STATES)

    weight = fields.Float(string='Weight', help="Weight in KG", states=READONLY_STATES)
    height = fields.Float(string='Height', help="Height in cm", states=READONLY_STATES)
    temp = fields.Float(string='Temp', states=READONLY_STATES)
    hr = fields.Float(string='HR', help="Heart Rate", states=READONLY_STATES)
    rr = fields.Float(string='RR', states=READONLY_STATES, help='Respiratory Rate')
    systolic_bp = fields.Float("Systolic BP", states=READONLY_STATES)
    diastolic_bp = fields.Float("Diastolic BP", states=READONLY_STATES)
    spo2 = fields.Float(string='SpO2', states=READONLY_STATES, 
        help='Oxygen Saturation, percentage of oxygen bound to hemoglobin')
    rbs = fields.Integer('RBS', help="Random blood sugar measures blood glucose regardless of when you last ate.")

    #ACS: odoo15 remove blove field which are there just for backup
    temp_old = fields.Char(string='OLD Temp', states=READONLY_STATES)
    hr_old = fields.Char(string='OLD HR', help="Heart Rate", states=READONLY_STATES)
    rr_old = fields.Char(string='OLD RR', states=READONLY_STATES, help='Respiratory Rate')
    systolic_bp_old = fields.Char("OLD Systolic BP", states=READONLY_STATES)
    diastolic_bp_old = fields.Char("OLD Diastolic BP", states=READONLY_STATES)
    spo2_old = fields.Char(string='OLD SpO2', states=READONLY_STATES, 
        help='Oxygen Saturation, percentage of oxygen bound to hemoglobin')

    bmi = fields.Float(compute="get_bmi_data", string='Body Mass Index', store=True)
    bmi_state = fields.Selection([
        ('low_weight', 'Low Weight'), 
        ('normal', 'Normal'),
        ('over_weight', 'Over Weight'), 
        ('obesity', 'Obesity')], compute="get_bmi_data", string='BMI State', store=True)
    company_id = fields.Many2one('res.company', ondelete='restrict', states=READONLY_STATES,
        string='Hospital', default=lambda self: self.env.user.company_id.id)

    appointment_id = fields.Many2one('hms.appointment', string='Appointment', states=READONLY_STATES)

    acs_weight_name = fields.Char(string='Patient Weight unit of measure label', compute='_compute_uom_name')
    acs_height_name = fields.Char(string='Patient Height unit of measure label', compute='_compute_uom_name')
    acs_temp_name = fields.Char(string='Patient Temp unit of measure label', compute='_compute_uom_name')
    acs_spo2_name = fields.Char(string='Patient SpO2 unit of measure label', compute='_compute_uom_name')
    acs_rbs_name = fields.Char(string='Patient RBS unit of measure label', compute='_compute_uom_name')

    @api.model
    def _compute_uom_name(self):
        parameter = self.env['ir.config_parameter']
        for rec in self:
            weight_uom = parameter.sudo().get_param('acs_hms.acs_patient_weight_uom')
            rec.acs_weight_name = weight_uom or 'Kg'
            height_uom = parameter.sudo().get_param('acs_hms.acs_patient_height_uom')
            rec.acs_height_name = height_uom or 'Cm'
            temp_uom = parameter.sudo().get_param('acs_hms.acs_patient_temp_uom')
            rec.acs_temp_name = temp_uom or '°C'
            spo2_uom = parameter.sudo().get_param('acs_hms.acs_patient_spo2_uom')
            rec.acs_spo2_name = spo2_uom or '%'
            rbs_uom = parameter.sudo().get_param('acs_hms.acs_patient_rbs_uom')
            rec.acs_rbs_name = rbs_uom or 'mg/dl'

    @api.model
    def create(self, values):
        if not values.get('name'):
            values['name'] = self.env['ir.sequence'].next_by_code('acs.patient.evaluation') or 'New Appointment'
        return super(AcsPatientEvaluation, self).create(values)

    def unlink(self):
        for data in self:
            if data.state in ['done']:
                raise UserError(_('You can not delete record in done state'))
        return super(AcsPatientEvaluation, self).unlink()

    def action_draft(self):
        self.state = 'draft'

    def action_done(self):
        self.state = 'done'

    def action_cancel(self):
        self.state = 'cancel'

    def create_evaluation(self):
        pass

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: