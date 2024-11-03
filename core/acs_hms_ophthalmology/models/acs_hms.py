#-*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ACSAppointment(models.Model):
    _inherit = 'hms.appointment'

    def action_view_ophthalmology(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_ophthalmology.action_acs_ophthalmology_evaluation")
        action['domain'] = [('appointment_id', '=', self.id)]
        action['context'] = {
            'default_appointment_id': self.id,
            'default_patient_id': self.patient_id.id
        }
        return action

    @api.model
    def default_get(self, fields):
        res = super(ACSAppointment, self).default_get(fields)
        if self._context.get('is_ophthalmology_appointment'):
            department = self.env['hr.department'].search([('department_type','=','ophthalmology')], limit=1)
            if department:
                res['department_id'] = department.id
        return res


class ACSPatient(models.Model):
    _inherit = "hms.patient"

    def _rec_count(self):
        rec = super(ACSPatient, self)._rec_count()
        for rec in self:
            rec.ophthalmology_count = len(rec.ophthalmology_ids)

    ophthalmology_ids = fields.One2many('acs.ophthalmology.evaluation', 'patient_id', string='Ophthalmology')
    ophthalmology_count = fields.Integer(compute='_rec_count', string='# Ophthalmology')

    def action_view_ophthalmology(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_ophthalmology.action_acs_ophthalmology_evaluation")
        action['domain'] = [('patient_id', '=', self.id)]
        action['context'] = {
            'default_patient_id': self.id
        }
        return action


class HrDepartment(models.Model): 
    _inherit = "hr.department"

    department_type = fields.Selection(selection_add=[('ophthalmology','Ophthalmology')])


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: