# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class ResUsers(models.Model):
    _inherit = 'res.users'
    
    @api.model
    def _signup_create_user(self, values):
        res = super(ResUsers, self)._signup_create_user(values)
        patient = self.env['hms.patient'].create({
            'partner_id': res.partner_id.id,
            'phone':values.get('phone'),
            'name':values.get('name')
        })
        return res

    def patient_relatives(self):
        return self.acs_patient_id and self.acs_patient_id.family_member_ids or False

