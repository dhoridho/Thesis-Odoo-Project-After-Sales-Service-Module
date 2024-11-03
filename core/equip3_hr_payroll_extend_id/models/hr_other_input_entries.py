# -*- coding: utf-8 -*-
import calendar
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class HrOtherInputs(models.Model):
    _name = 'hr.other.input.entries'
    _description = "HR Other Input Entries"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    employee = fields.Many2one('hr.employee', string='Employee', required=True)
    employee_id = fields.Char('Employee ID', readonly=True)
    contract_id = fields.Many2one('hr.contract', string='Contract Id', readonly=True)
    contract = fields.Char('Contract', readonly=True)
    other_input_id = fields.Many2one('hr.other.inputs', string='Other Input', required=True,
                                  domain="[('state','=','confirm'),('input_type','=','manual_entries')]")
    code = fields.Char('Code', readonly=True)
    input_type = fields.Char('Input Type', readonly=True)
    payslip_period_id = fields.Many2one('hr.payslip.period', string='Payslip Period', domain="[('state','=','open')]", required=True)
    month = fields.Many2one('hr.payslip.period.line', string="Month", domain="[('period_id','=',payslip_period_id)]",
                            required=True)
    periode_start_date = fields.Date("Period Start Date", readonly=True)
    periode_end_date = fields.Date("Period End Date", readonly=True)
    amount = fields.Float('Amount', required=True)

    @api.onchange('employee')
    def _onchange_employee(self):
        if self.employee:
            self.employee_id = self.employee.sequence_code
            contract_obj = self.env['hr.contract'].search(
                [('employee_id', '=', self.employee.id), ('state', '=', 'open')], limit=1)
            if contract_obj:
                for rec in contract_obj:
                    self.contract_id = rec.id
                    self.contract = rec.name

    @api.onchange('other_input_id')
    def _onchange_other_input_id(self):
        if self.other_input_id:
            self.code = self.other_input_id.code
            if self.other_input_id.input_type == 'manual_entries':
                self.input_type = 'Manual Entries'
            elif self.other_input_id.input_type == 'get_from_other_object':
                self.input_type = 'Get from Other Object'

    @api.onchange('month')
    def _onchange_month(self):
        for res in self:
            if res.payslip_period_id:
                if res.month:
                    period_line_obj = self.env['hr.payslip.period.line'].search(
                        [('id', '=', res.month.id)], limit=1)
                    if period_line_obj:
                        for rec in period_line_obj:
                            res.periode_start_date = rec.start_date
                            res.periode_end_date = rec.end_date
                    else:
                        res.periode_start_date = False
                        res.periode_end_date = False
