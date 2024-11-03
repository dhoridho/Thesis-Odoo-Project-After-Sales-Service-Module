# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import date, datetime, time
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta

class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    def confirm_compute_sheet(self):
        [data] = self.read()
        active_id = self.env.context.get('active_id')
        if active_id:
            [run_data] = self.env['hr.payslip.run'].browse(active_id).read(['date_start', 'date_end', 'credit_note', 'payslip_period_id', 'month'])
        payslip_period = self.env['hr.payslip.period'].search(
            [('id', '=', run_data.get('payslip_period_id')[0])], limit=1)
        month = self.env['hr.payslip.period.line'].search(
            [('id', '=', run_data.get('month')[0])], limit=1)
        from_date = run_data.get('date_start')
        to_date = run_data.get('date_end')
        credit_note = run_data.get('credit_note')
        if not data['employee_ids']:
            raise UserError(_("You must select employee(s) to generate payslip(s)."))
        ovt_obj = self.env['hr.overtime.actual.line'].search(
        [('employee_id', 'in', data['employee_ids']),('state', '=', 'to_approve'),('date','>=',from_date),('date','<=',to_date)])
        if ovt_obj:
            res = {
                'type': 'ir.actions.act_window',
                'res_model': 'payslip.compute.sheet.wizard',
                'view_type': 'form',
                'view_mode': 'form',
                'name':"Confirmation Message",
                'target': 'new',
                'context':{'default_employee_ids': data['employee_ids'],
                            'default_is_batch': True,
                            'default_payslip_period': payslip_period.id,
                            'default_month': month.id,
                            'default_date_start': from_date,
                            'default_date_end': to_date,
                            'default_credit_note': credit_note,
                            'default_batch_active_id': active_id},
            }
        else:
            res = super(HrPayslipEmployees, self).compute_sheet()
        return res