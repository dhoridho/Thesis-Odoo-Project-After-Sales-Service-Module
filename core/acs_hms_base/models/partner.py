# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
from datetime import datetime


class ResPartner(models.Model):
    _inherit= "res.partner"

    @api.depends('birthday', 'date_of_death')
    def _get_age(self):
        for rec in self:
            age = ''
            if rec.birthday:
                end_data = rec.date_of_death or fields.Datetime.now()
                delta = relativedelta(end_data, rec.birthday)
                if delta.years <= 2:
                    age = str(delta.years) + _(" Year") + str(delta.months) + _(" Month ") + str(delta.days) + _(" Days")
                else:
                    age = str(delta.years) + _(" Year")
            rec.age = age

    name = fields.Char(tracking=True)
    code = fields.Char(string='Identification Code', default='/',
        help='Identifier provided by the Health Center.', copy=False, tracking=True)
    gender = fields.Selection([
        ('male', 'Male'), 
        ('female', 'Female'), 
        ('other', 'Other')], string='Gender', default='male', tracking=True)
    birthday = fields.Date(string='Date of Birth', tracking=True)
    date_of_death = fields.Date(string='Date of Death')
    age = fields.Char(string='Age', compute='_get_age')
    hospital_name = fields.Char()
    blood_group = fields.Selection([
        ('A+', 'A+'),('A-', 'A-'),
        ('B+', 'B+'),('B-', 'B-'),
        ('AB+', 'AB+'),('AB-', 'AB-'),
        ('O+', 'O+'),('O-', 'O-')], string='Blood Group')

    is_patient = fields.Boolean(compute='_is_patient', search='_patient_search',
        string='Is Patient', help="Check if customer is linked with patient.")
    acs_amount_due = fields.Monetary(compute='_compute_acs_amount_due')
    acs_patient_id = fields.Many2one('hms.patient', compute='_is_patient', string='Patient', readonly=True)

    def _compute_acs_amount_due(self):
        MoveLine = self.env['account.move.line']
        for record in self:
            amount_due = 0
            unreconciled_aml_ids = MoveLine.sudo().search([('reconciled', '=', False),
               ('account_id.deprecated', '=', False),
               ('account_id.internal_type', '=', 'receivable'),
               ('move_id.state', '=', 'posted'),
               ('partner_id', '=', record.id),
               ('company_id','=',self.env.company.id)])
            for aml in unreconciled_aml_ids:
                amount_due += aml.amount_residual
            record.acs_amount_due = amount_due

    def _is_patient(self):
        Patient = self.env['hms.patient'].sudo()
        for rec in self:
            patient = Patient.search([('partner_id', '=', rec.id)], limit=1)
            rec.acs_patient_id = patient.id if patient else False
            rec.is_patient = True if patient else False

    def _patient_search(self, operator, value):
        patients = self.env['hms.patient'].sudo().search([])
        return [('id', 'in', patients.mapped('partner_id').ids)]

    def create_patient(self):
        self.ensure_one()
        self.env['hms.patient'].create({
            'partner_id': self.id,
            'name': self.name,
        })

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: