# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class DeathRegister(models.Model):
    _name = "patient.death.register"
    _description = "Patient Death Register"

    STATES = {'done': [('readonly', True)]}

    name = fields.Char('Name', readonly=True, copy=False)
    date_of_death = fields.Date(string='Date of Death', states=STATES, required=True)
    hospitalizaion_id = fields.Many2one('acs.hospitalization', string='Hospitalization', states=STATES)
    patient_id = fields.Many2one('hms.patient', string="Patient", states=STATES, required=True)
    patient_age = fields.Char(related="patient_id.age", store=True, string="Age", readonly=True)
    patient_gender = fields.Selection(related="patient_id.gender", store=True, string='Gender', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')], string='Status', required=True, readonly=True, copy=False, default='draft')
    physician_id = fields.Many2one('hms.physician', ondelete='restrict', string='Physician', index=True, states=STATES)
    reason = fields.Text (string='Death Reason', states=STATES, required=True)
    extra_info = fields.Text (string='Remarks', states=STATES)
    company_id = fields.Many2one('res.company', ondelete='restrict', 
        string='Hospital',default=lambda self: self.env.user.company_id.id) 

    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].next_by_code('patient.death.register') or 'New Birth'
        return super(DeathRegister, self).create(values)

    def unlink(self):
        for data in self:
            if data.state in ['done']:
                raise UserError(('You can not delete record in done state'))
        return super(DeathRegister, self).unlink()

    def action_done(self):
        self.state = 'done'
        self.patient_id.death_register_id = self.id
        self.patient_id.date_of_death = self.date_of_death
        if self.hospitalizaion_id:
            self.hospitalizaion_id.death_register_id = self.id
        self.patient_id.active = False

    def action_draft(self):
        self.state = 'draft'

    @api.onchange('hospitalizaion_id')   
    def onchange_hospitalizaion(self):
        if self.hospitalizaion_id:
            self.patient_id = self.hospitalizaion_id.patient_id.id

    @api.onchange('patient_id')   
    def onchange_patient_id(self):
        if self.patient_id:
            self.patient_age = self.patient_id.age

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:   