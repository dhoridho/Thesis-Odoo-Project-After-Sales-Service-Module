# -*- encoding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
from odoo.tools import format_datetime


class HmsAppointment(models.Model):
    _name = 'hms.appointment'
    _inherit = ['hms.appointment','acs.whatsapp.mixin']

    def appointment_confirm(self):
        res = super(HmsAppointment, self).appointment_confirm()
        for rec in self:
            if rec.company_id.sudo().wa_appointment_reg_message and rec.patient_id and rec.patient_id.mobile:
                msg_exp = rec.company_id.sudo().wa_appointment_reg_message
                try:
                    msg = eval(msg_exp, {'object': rec, 
                        'format_datetime': lambda dt, tz=False, dt_format=False, lang_code=False: format_datetime(self.env, dt, tz, dt_format, lang_code)
                    })
                except:
                    raise UserError(_("Configured Message fromat is wrong please contact administrator correct it first."))
                self.send_whatsapp(msg, rec.patient_id.partner_id.mobile, rec.patient_id.partner_id)
        return res

    def whatsapp_chat_history(self):
        if not (self.patient_id and self.patient_id.mobile):
            raise UserError(_("No Mobile no linked with Record."))     
        return self.acs_whatsapp_chat_history(self.patient_id.partner_id, self.patient_id.mobile)


class HmsPatient(models.Model):
    _name = 'hms.patient'
    _inherit = ['hms.patient','acs.whatsapp.mixin']

    @api.model
    def create(self, vals):
        res = super(HmsPatient, self).create(vals)
        company_id = res.sudo().company_id or self.env.user.sudo().company_id
        if company_id.wa_patient_reg_message:
            if res.mobile:
                msg_exp = company_id.wa_patient_reg_message
                try:
                    msg = eval(msg_exp, {'object': res, 
                        'format_datetime': lambda dt, tz=False, dt_format=False, lang_code=False: format_datetime(self.env, dt, tz, dt_format, lang_code)
                    })
                except:
                    raise UserError(_("Configured Message fromat is wrong please contact administrator correct it first."))
                self.send_whatsapp(msg, res.partner_id.mobile, res.partner_id)
        return res

    def whatsapp_chat_history(self):
        if not self.mobile:
            raise UserError(_("No Mobile no linked with Record."))     
        return self.acs_whatsapp_chat_history(self.partner_id, self.mobile)


class AcsCreateWAMsg(models.TransientModel):
    _inherit = 'acs.send.whatsapp'

    @api.model
    def default_get(self,fields):
        context = self._context or {}
        res = super(AcsCreateWAMsg, self).default_get(fields)
        if context.get('active_model')=='hms.patient':
            patient = self.env['hms.patient'].browse(context.get('active_ids', []))
            res.update({
                'partner_id': patient.partner_id.id,
                'mobile': patient.mobile,
            })

        if context.get('active_model')=='hms.appointment':
            appointment = self.env['hms.appointment'].browse(context.get('active_ids', []))
            if not appointment.patient_id:
                raise UserError(_("No Patient linked with Record."))
            res.update({
                'partner_id': appointment.patient_id.partner_id.id,
                'mobile': appointment.patient_id.mobile,
            })
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: