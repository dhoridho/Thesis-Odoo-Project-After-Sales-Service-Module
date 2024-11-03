# -*- coding: utf-8 -*-

from odoo import api, fields, models ,_
from odoo.exceptions import UserError
from datetime import datetime

import time
import json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.tools import format_datetime


class ACSPatient(models.Model):
    _inherit = 'hms.patient'

    def _rec_count(self):
        rec = super(ACSPatient, self)._rec_count()
        Prescription = self.env['prescription.order']
        Treatment = self.env['hms.treatment']
        for rec in self:
            rec.prescription_count = Prescription.search_count([('patient_id','=',rec.id)])
            rec.treatment_count = Treatment.search_count([('patient_id','=',rec.id)])
            rec.appointment_count = len(rec.appointment_ids)
            rec.evaluation_count = len(rec.evaluation_ids)

    def _acs_get_attachemnts(self):
        attachments = super(ACSPatient, self)._acs_get_attachemnts()
        attachments += self.appointment_ids.mapped('attachment_ids')
        return attachments

    @api.model
    def _get_service_id(self):
        registration_product = False
        if self.env.user.company_id.patient_registration_product_id:
            registration_product = self.env.user.company_id.patient_registration_product_id.id
        return registration_product

    def _get_last_evaluation(self):
        for rec in self:
            evaluation_ids = rec.evaluation_ids.filtered(lambda x: x.state=='done')
                   
            if evaluation_ids:
                rec.last_evaluation_id = evaluation_ids[0].id if evaluation_ids else False
            else:
                rec.last_evaluation_id = False

    @api.depends('grpah_data_filter')
    def _patient_evaluation_graph_data(self):
        for rec in self:
            today = fields.Datetime.now()
            domain = [('patient_id','=',rec.id)]
            if rec.grpah_data_filter=='today':
                domain += [('date', '>=', today.strftime('%Y-%m-%d 00:00:00')),('date', '<=', today.strftime('%Y-%m-%d 23:59:59'))]
            if rec.grpah_data_filter=='week':
                domain += [('date', '>=', (today + relativedelta(weeks=-1,days=1,weekday=0))), ('date', '<=', (fields.Datetime.today() + relativedelta(weekday=6)))]
            if rec.grpah_data_filter=='month':
                domain += [('date','<',(today+relativedelta(months=1)).strftime('%Y-%m-01')), ('date','>=',time.strftime('%Y-%m-01'))]

            records = self.env['acs.patient.evaluation'].search(domain, order="date")

            rec.patient_weight_line_graph = json.dumps(rec.patient_evaluation_line_graph_datas('weight', records, 'Weight'))
            rec.patient_height_line_graph = json.dumps(rec.patient_evaluation_line_graph_datas('height', records, 'Height'))
            rec.patient_temp_line_graph = json.dumps(rec.patient_evaluation_line_graph_datas('temp', records, 'Temprature'))
            rec.patient_hr_line_graph = json.dumps(rec.patient_evaluation_line_graph_datas('hr', records, 'Hear Rate'))
            rec.patient_rr_line_graph = json.dumps(rec.patient_evaluation_line_graph_datas('rr', records, 'RR'))
            rec.patient_systolic_bp_line_graph = json.dumps(rec.patient_evaluation_line_graph_datas('systolic_bp', records, 'Systolic BP'))
            rec.patient_diastolic_bp_line_graph = json.dumps(rec.patient_evaluation_line_graph_datas('diastolic_bp', records, 'Diastolic BP'))
            rec.patient_spo2_line_graph = json.dumps(rec.patient_evaluation_line_graph_datas('spo2', records, 'SpO2'))

    def patient_evaluation_line_graph_datas(self, field_name, records, rec_name):
        patient_data = []
        for record in records:
            formated_date = format_datetime(self.env, record.date, tz=(self.env.user.tz or "UTC"))
            patient_data.append({'x': formated_date, 'y':record[field_name], 'name': 'Patient %s' % rec_name})

        [patient_graph_title, patient_graph_key] = ['Child %s Growth Chart' % rec_name, _('Patient %s Chart' % rec_name)]
        return [
            {'values': patient_data, 'title': patient_graph_title, 'key': patient_graph_key, 'area': False, 'color': 'green'}
        ]

    ref_doctor_ids = fields.Many2many('res.partner', 'rel_doc_pat', 'doc_id', 
        'patient_id', 'Referring Doctors', domain=[('is_referring_doctor','=',True)])

    #Diseases
    medical_history = fields.Text(string="Past Medical History")
    patient_diseases_ids = fields.One2many('hms.patient.disease', 'patient_id', string='Diseases')

    #Family Form Tab
    genetic_risks_ids = fields.One2many('hms.patient.genetic.risk', 'patient_id', 'Genetic Risks')
    family_history_ids = fields.One2many('hms.patient.family.diseases', 'patient_id', 'Family Diseases History')
    department_ids = fields.Many2many('hr.department', 'patint_department_rel','patient_id', 'department_id',
        domain=[('patient_department', '=', True)], string='Departments')

    medication_ids = fields.One2many('hms.patient.medication', 'patient_id', string='Medications')
    ethnic_group_id = fields.Many2one('acs.ethnicity', string='Ethnic group')
    cod = fields.Many2one('hms.diseases', string='Cause of Death')
    family_member_ids = fields.One2many('acs.family.member', 'patient_id', string='Family')

    prescription_count = fields.Integer(compute='_rec_count', string='# Prescriptions')
    treatment_count = fields.Integer(compute='_rec_count', string='# Treatments')
    appointment_count = fields.Integer(compute='_rec_count', string='# Appointments')
    appointment_ids = fields.One2many('hms.appointment', 'patient_id', 'Appointments')
    medical_alert_ids = fields.Many2many('acs.medical.alert', 'patient_medical_alert_rel','patient_id', 'alert_id',
        string='Medical Alerts')
    registration_product_id = fields.Many2one('product.product', default=_get_service_id, string="Registration Service")
    invoice_id = fields.Many2one("account.move","Registration Invoice", copy=False)

    evaluation_count = fields.Integer(compute='_rec_count', string='# Evaluations')
    evaluation_ids = fields.One2many('acs.patient.evaluation', 'patient_id', 'Evaluations')

    last_evaluation_id = fields.Many2one("acs.patient.evaluation", string="Last Appointment", compute=_get_last_evaluation, readonly=True)
    weight = fields.Float(related="last_evaluation_id.weight", string='Weight', help="Weight in KG", readonly=True)
    height = fields.Float(related="last_evaluation_id.height", string='Height', help="Height in cm", readonly=True)
    temp = fields.Float(related="last_evaluation_id.temp", string='Temp', readonly=True)
    hr = fields.Float(related="last_evaluation_id.hr", string='HR', help="Heart Rate", readonly=True)
    rr = fields.Float(related="last_evaluation_id.rr", string='RR', readonly=True, help='Respiratory Rate')
    systolic_bp = fields.Float(related="last_evaluation_id.systolic_bp", string="Systolic BP")
    diastolic_bp = fields.Float(related="last_evaluation_id.diastolic_bp", string="Diastolic BP")
    spo2 = fields.Float(related="last_evaluation_id.spo2", string='SpO2', readonly=True, 
        help='Oxygen Saturation, percentage of oxygen bound to hemoglobin')
    rbs = fields.Integer(related="last_evaluation_id.rbs", string='RBS', readonly=True, 
        help='Random blood sugar measures blood glucose regardless of when you last ate.')

    bmi = fields.Float(related="last_evaluation_id.bmi", string='Body Mass Index', readonly=True)
    bmi_state = fields.Selection(related="last_evaluation_id.bmi_state", string='BMI State', readonly=True)

    grpah_data_filter = fields.Selection([
            ('today','Today'),
            ('week','This Week'),
            ('month','This Month'),
            ('year','This Year'),
            ('all','All'),
        ], "Grpah Filter Type", default="month")
    patient_weight_line_graph = fields.Text(compute='_patient_evaluation_graph_data')
    patient_height_line_graph = fields.Text(compute='_patient_evaluation_graph_data')
    patient_temp_line_graph = fields.Text(compute='_patient_evaluation_graph_data')
    patient_hr_line_graph = fields.Text(compute='_patient_evaluation_graph_data')
    patient_rr_line_graph = fields.Text(compute='_patient_evaluation_graph_data')
    patient_systolic_bp_line_graph = fields.Text(compute='_patient_evaluation_graph_data')
    patient_diastolic_bp_line_graph = fields.Text(compute='_patient_evaluation_graph_data')
    patient_spo2_line_graph = fields.Text(compute='_patient_evaluation_graph_data')

    acs_weight_name = fields.Char(related="last_evaluation_id.acs_weight_name", string='Patient Weight unit of measure label')
    acs_height_name = fields.Char(related="last_evaluation_id.acs_height_name", string='Patient Height unit of measure label')
    acs_temp_name = fields.Char(related="last_evaluation_id.acs_temp_name", string='Patient Temp unit of measure label')
    acs_spo2_name = fields.Char(related="last_evaluation_id.acs_spo2_name", string='Patient SpO2 unit of measure label')
    acs_rbs_name = fields.Char(related="last_evaluation_id.acs_rbs_name", string='Patient RBS unit of measure label')


    def today_data(self):
        self.sudo().grpah_data_filter = 'today'

    def week_data(self):
        self.sudo().grpah_data_filter = 'week'

    def month_data(self):
        self.sudo().grpah_data_filter = 'month'

    def year_data(self):
        self.sudo().grpah_data_filter = 'year'

    def all_data(self):
        self.sudo().grpah_data_filter = 'all'

    def show_weight_chart(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms.action_patient_evaluation_graph_1")
        action['domain'] = [('id', '=', self.id)]
        return action

    def create_invoice(self):
        product_id = self.registration_product_id or self.env.user.company_id.patient_registration_product_id
        if not product_id:
            raise UserError(_("Please Configure Registration Product in Configuration first."))

        invoice = self.acs_create_invoice(partner=self.partner_id, patient=self, product_data=[{'product_id': product_id}], inv_data={'hospital_invoice_type': 'patient'})
        self.invoice_id = invoice.id

    def action_appointment(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms.action_appointment")
        action['domain'] = [('patient_id','=',self.id)]
        action['context'] = {'default_patient_id': self.id, 'default_physician_id': self.primary_doctor.id}
        return action

    def action_prescription(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms.act_open_hms_prescription_order_view")
        action['domain'] = [('patient_id','=',self.id)]
        action['context'] = {'default_patient_id': self.id, 'default_physician_id': self.primary_doctor.id}
        return action

    def action_treatment(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms.acs_action_form_hospital_treatment")
        action['domain'] = [('patient_id','=',self.id)]
        action['context'] = {'default_patient_id': self.id, 'default_physician_id': self.primary_doctor.id}
        return action

    def action_evaluation(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms.action_acs_patient_evaluation")
        action['domain'] = [('patient_id','=',self.id)]
        action['context'] = {'default_patient_id': self.id, 'default_physician_id': self.primary_doctor.id}
        return action


class ACSFamilyMember(models.Model):
    _name = 'acs.family.member'
    _description= 'Family Member'

    related_patient_id = fields.Many2one('hms.patient', string='Family Member', help='Family Member Name', required=True)    
    patient_id = fields.Many2one('hms.patient', string='Patient')
    relation_id = fields.Many2one('acs.family.relation', string='Relation', required=True)
    inverse_relation_id = fields.Many2one("acs.family.member", string="Inverse Relation")

    def create(self, values):
        res = super(ACSFamilyMember, self).create(values)
        if not res.inverse_relation_id and res.relation_id.inverse_relation_id:
            inverse_relation_id = self.create({
                'inverse_relation_id': res.id,
                'relation_id': res.relation_id.inverse_relation_id.id,
                'patient_id': res.related_patient_id.id,
                'related_patient_id': res.patient_id.id,
            })
            res.inverse_relation_id = inverse_relation_id.id
        return res

    def unlink(self):
        inverse_relation_id = self.mapped('inverse_relation_id')
        res = super(ACSFamilyMember, self).unlink()
        if inverse_relation_id:
            inverse_relation_id.unlink()
        return res

    def write(self, values):
        res = super(ACSFamilyMember, self).write(values)
        if 'patient_id' in values or 'related_patient_id' in values :
            raise UserError(_("Please Delete Exiting relateion and create new!"))

        if 'relation_id' in values:
            for rec in self:
                if rec.inverse_relation_id and rec.relation_id.inverse_relation_id and rec.relation_id.inverse_relation_id!=rec.inverse_relation_id.relation_id:
                    rec.inverse_relation_id.relation_id = rec.relation_id.inverse_relation_id.id
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: