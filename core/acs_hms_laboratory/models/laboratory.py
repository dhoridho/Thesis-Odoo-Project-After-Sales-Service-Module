# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AcsLaboratoryRequest(models.Model):
    _inherit = 'acs.laboratory.request'
    
    STATES = {'requested': [('readonly', True)], 'accepted': [('readonly', True)], 'in_progress': [('readonly', True)], 'cancel': [('readonly', True)], 'done': [('readonly', True)]}

    appointment_id = fields.Many2one('hms.appointment', string='Appointment', ondelete='restrict', states=STATES)
    hospitalization_id = fields.Many2one('acs.hospitalization', string='Hospitalization', ondelete='restrict', states=STATES)
    treatment_id = fields.Many2one('hms.treatment', string='Treatment', ondelete='restrict', states=STATES)

    def prepare_test_result_data(self, line, patient):
        res = super(AcsLaboratoryRequest, self).prepare_test_result_data(line, patient)
        res['appointment_id'] = self.appointment_id and self.appointment_id.id or False
        res['hospitalization_id'] = self.hospitalization_id and self.hospitalization_id.id or False
        return res


class PatientLabTest(models.Model):
    _inherit = "patient.laboratory.test"

    STATES = {'cancel': [('readonly', True)], 'done': [('readonly', True)]}

    hospitalization_id = fields.Many2one('acs.hospitalization', string='Hospitalization', ondelete='restrict', states=STATES)
    print_in_discharge = fields.Boolean("Print in Discharge Report")
    appointment_id = fields.Many2one('hms.appointment', string='Appointment', ondelete='restrict', states=STATES)
    treatment_id = fields.Many2one('hms.treatment', string='Treatment', ondelete='restrict', states=STATES)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: