#-*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HmsAppointment(models.Model):
    _inherit = 'hms.appointment'

    video_call_id = fields.Many2one('acs.video.call', string='Video Call', states={'cancel': [('readonly', True)], 'done': [('readonly', True)]})
    video_call_link = fields.Char(related="video_call_id.meeting_link", string="Video Call Link", readonly=True)

    def create_video_call(self):
        video_call = self.env['acs.video.call'].create({
            'user_id': self.env.user.id,
            'partner_ids': [(6,0,[self.patient_id.partner_id.id, self.physician_id.partner_id.id])],
            'subject': _('Video Consultation for Appointment ') + self.name,
            'date': self.date,
            'state': 'planned',
            'password': self.name,
            'appointment_id': self.id,
        })
        self.video_call_id = video_call.id

    def consultation_done(self):
        if self.video_call_id:
            self.video_call_id.action_done()
        return super(HmsAppointment, self).consultation_done()

    def get_partner_ids(self):
        partner_ids = ','.join(map(lambda x: str(x.id), [self.patient_id.partner_id,self.physician_id.partner_id]))
        return partner_ids

    def action_send_invitaion(self):
        '''
        This function opens a window to compose an email, with the template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('acs_hms_video_call', 'acs_video_call_invitaion')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = {
            'default_model': 'hms.appointment',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'force_email': True
        }
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

