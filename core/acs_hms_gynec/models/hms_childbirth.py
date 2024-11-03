# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class AcsChildBirth(models.Model):
    _name = "acs.child.birth"
    _description = "Child Birth"

    STATES = {'done': [('readonly', True)]}

    name = fields.Char('Name of Children', readonly=True, copy=False)
    hospitalizaion_id = fields.Many2one('acs.hospitalization', string='Hospitalization', states=STATES)
    patient_id = fields.Many2one('hms.patient', string="Mother Name", states=STATES)
    age = fields.Char(related='patient_id.age',string="Age", readonly=True)
    father_name = fields.Char(related='patient_id.husband_name', string="Father's Name", readonly=True)
    father_edu = fields.Char(related='patient_id.husband_edu',string="Father's Education", readonly=True)
    father_business = fields.Char(related='patient_id.husband_business',string="Father's Business", readonly=True)
    patient_education = fields.Char(related='patient_id.education',string="Patient Education", readonly=True)
    mother_hb = fields.Float(related='patient_id.hb',string="Mother Hemoglobin Count", readonly=True)
    mother_blood_group = fields.Selection(related='patient_id.blood_group', string='Mother Blood Group', readonly=True)
    blood_group = fields.Selection([
        ('A+', 'A+'),('A-', 'A-'),
        ('B+', 'B+'),('B-', 'B-'),
        ('AB+', 'AB+'),('AB-', 'AB-'),
        ('O+', 'O+'),('O-', 'O-')], string='Blood Group', states=STATES)
    parity = fields.Integer(string="Parity", states=STATES)
    male = fields.Integer(string="Male", states=STATES)
    female = fields.Integer(string="Female", states=STATES)
    delivery_type = fields.Selection ([
            ('normal', 'Normal'),
            ('cesarean', 'Cesarean'),
            ], string='Type of Delivery', states=STATES)
    gender = fields.Selection ([
            ('male','Male'),
            ('female','Female'),
            ], string='Gender', index=True, states=STATES, required=True)
    birth_date = fields.Datetime(string='Date of birth', states=STATES, required=True)
    birth_place = fields.Char("Birth Place")
    birth_weight = fields.Float(string='Birth Weight', states=STATES, required=True)
    extra_info = fields.Text (string='Remarks', states=STATES)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')],
        string='Status', required=True, readonly=True, copy=False,default='draft')
    physician_id = fields.Many2one('hms.physician', ondelete='restrict', string='Physician', index=True, states=STATES)
    hb = fields.Float(string="Hemoglobin Count", states=STATES)
    company_id = fields.Many2one('res.company', ondelete='restrict', 
        string='Hospital',default=lambda self: self.env.user.company_id.id)

    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].next_by_code('acs.child.birth') or 'New Birth'
        return super(AcsChildBirth, self).create(values)

    def unlink(self):
        for data in self:
            if data.state in ['done']:
                raise UserError(('You can not delete record in done state'))
        return super(AcsChildBirth, self).unlink()

    def action_done(self):
        self.state = 'done'

    def action_draft(self):
        self.state = 'draft'

    @api.onchange('hospitalizaion_id')   
    def onchange_hospitalizaion(self):
        if self.hospitalizaion_id:
            self.patient_id = self.hospitalizaion_id.patient_id.id
            self.physician_id = self.hospitalizaion_id.physician_id.id

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: