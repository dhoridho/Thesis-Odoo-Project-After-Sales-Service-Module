# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class HrContract(models.Model):
    _inherit = 'hr.contract'

    outsource_id = fields.Many2one('hr.recruitment.outsource.master', string="Outsource")

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        res = super(HrContract, self)._onchange_employee_id()
        if self.employee_id:
            applicant = self.env['hr.applicant'].search([('emp_id','=',self.employee_id.id)],limit=1)
            if applicant:
                self.outsource_id = applicant.outsource_id
            else:
                self.outsource_id = False
        return res