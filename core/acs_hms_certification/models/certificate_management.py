# -*- encoding: utf-8 -*-
from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError
import uuid


class CertificateManagement(models.Model):
    _name = 'certificate.management'
    _inherit = ['certificate.management', 'acs.qrcode.mixin', 'portal.mixin']

    patient_id = fields.Many2one('hms.patient', string='Patient', ondelete="restrict", 
        help="Patient whose certificate to be attached", tracking=True, 
        states={'done': [('readonly', True)]})
    physician_id = fields.Many2one('hms.physician',string='Doctor', ondelete="restrict", 
        help="Doctor who provided certificate to the patient", tracking=True, 
        states={'done': [('readonly', True)]})
    appointment_id = fields.Many2one('hms.appointment', string='Appointment', ondelete="restrict", 
        help="Patient Appointment", 
        states={'done': [('readonly', True)]})

    @api.onchange('patient_id')
    def onchange_patient_id(self):
        if self.patient_id:
            self.partner_id = self.patient_id.partner_id

    @api.onchange('physician_id')
    def onchange_physician_id(self):
        if self.physician_id:
            self.user_id = self.physician_id.user_id

    def _compute_access_url(self):
        super(CertificateManagement, self)._compute_access_url()
        for rec in self:
            rec.access_url = '/my/certificates/%s' % (rec.id)

    @api.model
    def create(self, values):
        res = super(CertificateManagement, self).create(values)
        res.unique_code = uuid.uuid4()
        return res


class ACSPatient(models.Model):
    _inherit = 'hms.patient' 

    def _rec_count(self):
        rec = super(ACSPatient, self)._rec_count()
        for rec in self:
            rec.certificate_count = len(rec.sudo().certificate_ids)

    certificate_ids = fields.One2many('certificate.management', 'patient_id', string='Certificates', groups="acs_certification.group_certificate_manager")
    certificate_count = fields.Integer(compute='_rec_count', string='# Certificates')

    def action_open_certificate(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_certification.action_certificate_management")
        action['domain'] = [('patient_id','=',self.id)]
        action['context'] = {'default_patient_id': self.id}
        return action


class HmsAppointment(models.Model):
    _inherit = 'hms.appointment' 

    def _certificate_count(self):
        for rec in self:
            rec.certificate_count = len(rec.sudo().certificate_ids)

    certificate_ids = fields.One2many('certificate.management', 'appointment_id', string='Certificates', groups="acs_certification.group_certificate_manager")
    certificate_count = fields.Integer(compute='_certificate_count', string='# Certificates')

    def action_open_certificate(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_certification.action_certificate_management")
        action['domain'] = [('appointment_id','=',self.id)]
        action['context'] = {
            'default_appointment_id': self.id,
            'default_patient_id': self.patient_id and self.patient_id.id or False,
            'default_physician_id': self.physician_id and self.physician_id.id or False,
        }
        return action

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: