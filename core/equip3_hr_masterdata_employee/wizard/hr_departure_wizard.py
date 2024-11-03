# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import date

class HrDepartureWizard(models.TransientModel):
    _inherit = 'hr.departure.wizard'

    def action_register_departure(self):
        super(HrDepartureWizard, self).action_register_departure()
        if self.departure_reason == "resigned":
            if self.departure_date <= date.today():
                running_contract = self.env['hr.contract'].search([('employee_id','=',self.employee_id.id),('state','=','open')],limit=1)
                if running_contract:
                    running_contract.state = "close"