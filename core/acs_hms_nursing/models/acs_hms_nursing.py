#-*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class acsnursewardround(models.Model):
    _name = 'acs.nurse.ward.round'
    _description = "Nurse Ward round"

    READONLY_STATES = {'done': [('readonly', True)]}

    name = fields.Char(string='Round Number', states=READONLY_STATES, readonly=True)
    nurse_id = fields.Many2one('hr.employee', string='Nurse', default=lambda self: self.env.user.employee_id.id, states=READONLY_STATES, required=True)
    patient_id = fields.Many2one('hms.patient', string='Patient', related='hospitalization_id.patient_id', states=READONLY_STATES, store=True)
    date = fields.Datetime('Date', default=fields.Datetime.now, states=READONLY_STATES, required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')], default='draft', states=READONLY_STATES, string='State')
    hospitalization_id = fields.Many2one('acs.hospitalization', states=READONLY_STATES, string='Hospitalization')

    evaluation_id = fields.Many2one('acs.patient.evaluation', string='Evaluation', states=READONLY_STATES)
    weight = fields.Float(related="evaluation_id.weight", string='Weight', help="Weight in KG", states=READONLY_STATES)
    height = fields.Float(related="evaluation_id.height", string='Height', help="Height in cm", states=READONLY_STATES)
    temp = fields.Float(related="evaluation_id.temp", string='Temp', states=READONLY_STATES)
    hr = fields.Float(related="evaluation_id.hr", string='HR', help="Heart Rate", states=READONLY_STATES)
    rr = fields.Float(related="evaluation_id.rr", string='RR', states=READONLY_STATES, help='Respiratory Rate')
    systolic_bp = fields.Float(related="evaluation_id.systolic_bp", string="Systolic BP", states=READONLY_STATES)
    diastolic_bp = fields.Float(related="evaluation_id.diastolic_bp", string="Diastolic BP", states=READONLY_STATES)
    spo2 = fields.Float(related="evaluation_id.spo2", string='SpO2', states=READONLY_STATES, 
        help='Oxygen Saturation, percentage of oxygen bound to hemoglobin')
    bmi = fields.Float(related="evaluation_id.bmi", string='Body Mass Index', store=True)
    bmi_state = fields.Selection(related="evaluation_id.bmi_state", string='BMI State', store=True)

    # The Patients of rounding
    pain = fields.Boolean (string = 'Pain', states=READONLY_STATES, help="Check if the patient is in pain")
    pain_level = fields.Integer(string='Pain Level', states=READONLY_STATES, help="Enter the pain level, from 1 to 10")
    position = fields.Boolean(string='Position', states=READONLY_STATES, 
        help="Check if the patient needs to be repositioned or is unconfortable")
    potty = fields.Boolean(string='Potty', states=READONLY_STATES, 
        help="Check if the patient needs to urinate / defecate")
    proximity = fields.Boolean(string='Proximity', states=READONLY_STATES, 
        help="Check if personal items, water, alarm, ... are not in easy reach")
    pump = fields.Boolean(string='Pump', states=READONLY_STATES, 
        help="Check if there is any issues with the pumps - IVs ... ")
    personal_needs = fields.Boolean(string='Personal Needs', states=READONLY_STATES, 
        help="Check if the patient requests anything")

    # Diuresis
    diuresis = fields.Integer(string='Diuresis', states=READONLY_STATES, help="volume in ml")
    urinary_catheter = fields.Boolean(string='Urinary Catheter', states=READONLY_STATES)

    #Glycemia
    glycemia = fields.Integer(string='Glycemia', states=READONLY_STATES, help="Blood Glucose level")
    depression = fields.Boolean(string='Depression', states=READONLY_STATES, help="Check this if the "
        "patient shows signs of depression")
    evolution = fields.Selection([
        ('improving', 'Improving'),
        ('worsening', 'Worsening')], string='Evolution', states=READONLY_STATES, help="Check your judgement of current"
        "patient condition", default='improving', required=True)
    round_summary = fields.Text(string='Round Summary', states=READONLY_STATES)
    warning = fields.Boolean(string='Warning', states=READONLY_STATES, help="Check this box to alert the "
        "supervisor about this patient rounding. A warning icon will be shown in the rounding list")

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('acs.nurse.ward.round') or 'New'
        record = super(acsnursewardround, self).create(vals)
        return record

    def action_done(self):
        self.state = "done"

    def action_create_evaluation(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms.action_acs_patient_evaluation_popup")
        action['domain'] = [('patient_id','=',self.patient_id.id)]
        action['context'] = {'default_patient_id': self.patient_id.id, 'default_hospitalization_id': self.hospitalization_id.id, 'nurse_ward_round': self.id}
        return action

    @api.onchange('evaluation_id')
    def onchange_evalutaion(self):
        if self.evaluation_id:
            self.date = self.evaluation_id.date