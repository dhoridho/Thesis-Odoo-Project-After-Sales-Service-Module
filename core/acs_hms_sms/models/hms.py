# -*- encoding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools.safe_eval import safe_eval
from odoo.tools import format_datetime

class HmsAppointment(models.Model):
    _name = 'hms.appointment'
    _inherit = ['hms.appointment','acs.sms.mixin']

    def appointment_confirm(self):
        res = super(HmsAppointment, self).appointment_confirm()
        for rec in self:
            if rec.sudo().company_id.appointment_registartion_sms and rec.patient_id and rec.patient_id.mobile:
                msg_exp = rec.sudo().company_id.appointment_registartion_sms
                msg = eval(msg_exp, {'object': rec, 
                    'format_datetime': lambda dt, tz=False, dt_format=False, lang_code=False: format_datetime(self.env, dt, tz, dt_format, lang_code)
                })
                self.create_sms(msg, rec.patient_id.partner_id.mobile, rec.patient_id.partner_id)
        return res


class HmsPatient(models.Model):
    _name = 'hms.patient'
    _inherit = ['hms.patient','acs.sms.mixin']

    @api.model
    def create(self, vals):
        res = super(HmsPatient, self).create(vals)
        company_id = res.sudo().company_id or self.env.user.sudo().company_id
        if company_id.patient_registartion_sms:
            if res.mobile:
                msg_exp = company_id.patient_registartion_sms
                msg = eval(msg_exp, {'object': res})
                self.create_sms(msg, res.partner_id.mobile, res.partner_id)
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: