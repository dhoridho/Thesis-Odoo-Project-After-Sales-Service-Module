# -*- encoding: utf-8 -*-
from odoo import models, fields, api,_
from datetime import date, datetime, timedelta as td
from odoo.exceptions import UserError

class AcsCreateVaccinations(models.TransientModel):
    _name = "acs.plan.vaccinations"
    _description = "Transfer Accommodation"

    patient_id = fields.Many2one ('hms.patient','Patient', required=True)
    vaccination_on_birthday = fields.Boolean('Schedule on birthday')
    vaccination_group_id = fields.Many2one('vaccination.group',string='Vaccination Group', ondelete="restrict")

    @api.model
    def default_get(self,fields):
        context = self._context or {}
        res = super(AcsCreateVaccinations, self).default_get(fields)
        patient = self.env['hms.patient'].browse(context.get('active_ids', []))
        res.update({
            'patient_id': patient.id,
        })
        return res

    def create_vaccinations(self):
        Vaccination = self.env['acs.vaccination']
        base_date = fields.Date.from_string(fields.Date.today())
        if self.vaccination_on_birthday:
            if not self.patient_id.birthday:
                raise UserError(_('Please set Date Of Birth first.'))
            base_date = fields.Date.from_string(self.patient_id.birthday)

        for line in self.vaccination_group_id.group_line:
            days = line.date_due_day
            Vaccination.create({
                'product_id': line.product_id.id,
                'patient_id': self.patient_id.id, 
                'due_date': (base_date+ td(days=days)),
                'state': 'scheduled',
            })
        return {'type': 'ir.actions.act_window_close'}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
