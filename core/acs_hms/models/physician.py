# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Physician(models.Model):
    _inherit = 'hms.physician'

    def _phy_rec_count(self):
        Treatment = self.env['hms.treatment']
        Appointment = self.env['hms.appointment']
        Prescription = self.env['prescription.order']
        for record in self.with_context(active_test=False):
            record.treatment_count = Treatment.search_count([('physician_id', '=', record.id)])
            record.appointment_count = Appointment.search_count([('physician_id', '=', record.id)])
            record.prescription_count = Prescription.search_count([('physician_id', '=', record.id)])

    consultaion_service_id = fields.Many2one('product.product', ondelete='restrict', string='Consultation Service')
    followup_service_id = fields.Many2one('product.product', ondelete='restrict', string='Followup Service')
    appointment_duration = fields.Float('Default Consultation Duration', default=0.25)

    is_primary_surgeon = fields.Boolean(string='Primary Surgeon')
    signature = fields.Binary('Signature')
    hr_presence_state = fields.Selection(related='user_id.employee_id.hr_presence_state')
    appointment_ids = fields.One2many("hms.appointment", "physician_id", "Appointments")

    treatment_count = fields.Integer(compute='_phy_rec_count', string='# Treatments')
    appointment_count = fields.Integer(compute='_phy_rec_count', string='# Appointment')
    prescription_count = fields.Integer(compute='_phy_rec_count', string='# Prescriptions')

    def action_treatment(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms.acs_action_form_hospital_treatment")
        action['domain'] = [('physician_id','=',self.id)]
        action['context'] = {'default_physician_id': self.id}
        return action

    def action_appointment(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms.action_appointment")
        action['domain'] = [('physician_id','=',self.id)]
        action['context'] = {'default_physician_id': self.id}
        return action

    def action_prescription(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms.act_open_hms_prescription_order_view")
        action['domain'] = [('physician_id','=',self.id)]
        action['context'] = {'default_physician_id': self.id}
        return action

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: