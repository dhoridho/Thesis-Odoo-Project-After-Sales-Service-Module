# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools, _

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    @api.model
    def create(self, vals):
        payslip = super(HrPayslip, self).create(vals)
        payslip_period = self.payslip_period_id
        payslip_month = self.month
        
        baris_payslip_period = 0
        for rec in payslip_period.payslip_period_ids:
            baris_payslip_period += 1
            if rec.year == payslip_month.year and rec.month == payslip_month.month:
                break
        
        overtime_period_id = -1
        baris_overtime_period = 0
        for rec in payslip_period.overtime_period_ids:
            baris_overtime_period += 1
            if baris_overtime_period == baris_payslip_period:
                overtime_period_id = rec.id
                break

        overtime_period = payslip_period.overtime_period
        overtime_period_obj = payslip_period.overtime_period_ids.browse(overtime_period_id)
        if overtime_period == "hr_years":
            if overtime_period_obj:
                ovt_obj = self.env['hr.overtime.actual.line'].search(
                    [('employee_id', '=', payslip.employee_id.id), ('state', '=', 'approved'), ('applied_to','=','payslip'), 
                    ('date', '>=', overtime_period_obj.start_period),('date', '<=', overtime_period_obj.end_period)])
            else:
                ovt_obj = self.env['hr.overtime.actual.line'].search([('id', '=', -1)])
        else:
            ovt_obj = self.env['hr.overtime.actual.line'].search(
                [('employee_id', '=', payslip.employee_id.id), ('state', '=', 'approved'), ('applied_to','=','payslip'), 
                ('date', '>=', payslip.date_from),('date', '<=', payslip.date_to)])
        total_overtime_day = 0.0
        total_overtime_hour = 0.0
        total_overtime_amount = 0.0
        total_meal_allowance = 0.0
        if ovt_obj:
            for ovt in ovt_obj:
                total_overtime_day += 1
                total_overtime_hour += ovt.actual_hours
                total_overtime_amount += ovt.amount
                total_meal_allowance += ovt.meal_allowance

            for rec in payslip.input_line_ids:
                if rec.code == 'OVT':
                    rec.amount = total_overtime_amount
                if rec.code == 'OVT_MEAL':
                    rec.amount = total_meal_allowance

            for rec in payslip.worked_days_line_ids:
                if rec.code == 'OVERTIME':
                    rec.number_of_days = total_overtime_day
                    rec.number_of_hours = total_overtime_hour
        return payslip

    @api.onchange('employee_id', 'date_from', 'date_to')
    def onchange_employee(self):
        res = super(HrPayslip, self).onchange_employee()
        if (not self.employee_id) or (not self.date_from) or (not self.date_to):
            return

        employee = self.employee_id
        date_from = self.date_from
        date_to = self.date_to
        contract_ids = []

        contract_ids = self.get_contract(self.employee_id, self.date_from, self.date_to)
        if not contract_ids:
            self.contract_id = False
            return
        else:
            self.contract_id = self.env['hr.contract'].browse(contract_ids[0])

        if self.contract_id:
            contract_ids = self.contract_id.ids
        contracts = self.env['hr.contract'].browse(contract_ids)

        payslip_period = self.payslip_period_id
        payslip_month = self.month

        baris_payslip_period = 0
        for rec in payslip_period.payslip_period_ids:
            baris_payslip_period += 1
            if rec.year == payslip_month.year and rec.month == payslip_month.month:
                break
        
        overtime_period_obj = self.env['payslip.overtime.period.line']
        baris_overtime_period = 0
        for rec in payslip_period.overtime_period_ids:
            baris_overtime_period += 1
            if baris_overtime_period == baris_payslip_period:
                overtime_period_obj = payslip_period.overtime_period_ids.browse(rec.id)
                break
        
        overtime_period = payslip_period.overtime_period
        if overtime_period == "hr_years":
            if overtime_period_obj:
                ovt_obj = self.env['hr.overtime.actual.line'].search(
                    [('employee_id', '=', self.employee_id.id), ('state', '=', 'approved'), ('applied_to','=','payslip'), ('date','>=',overtime_period_obj.start_period), ('date','<=',overtime_period_obj.end_period)])
            else:
                ovt_obj = self.env['hr.overtime.actual.line'].search([('id', '=', -1)])
        else:
            ovt_obj = self.env['hr.overtime.actual.line'].search(
                [('employee_id', '=', self.employee_id.id), ('state', '=', 'approved'), ('applied_to','=','payslip'), ('date','>=',self.date_from), ('date','<=',self.date_to)])
        total_overtime_day = 0.0
        total_overtime_hour = 0.0
        total_overtime_amount = 0.0
        total_meal_allowance = 0.0

        if ovt_obj:
            for ovt in ovt_obj:
                total_overtime_day += 1
                total_overtime_hour += ovt.actual_hours
                total_overtime_amount += ovt.amount
                total_meal_allowance += ovt.meal_allowance

            other_input_entries_overtime = []
            for contract in contracts:
                input_data = {
                    'name': 'Overtime',
                    'code': 'OVT',
                    'amount': total_overtime_amount,
                    'contract_id': contract.id,
                }
                other_input_entries_overtime += [input_data]

                input_meal = {
                    'name': 'Overtime Meal',
                    'code': 'OVT_MEAL',
                    'amount': total_meal_allowance,
                    'contract_id': contract.id,
                }
                other_input_entries_overtime += [input_meal]

            input_overtime_lines = self.input_line_ids.browse([])
            for r in other_input_entries_overtime:
                input_overtime_lines += input_overtime_lines.new(r)
            self.input_line_ids += input_overtime_lines

            for rec in self.worked_days_line_ids:
                if rec.code == 'OVERTIME':
                    rec.number_of_days = total_overtime_day
                    rec.number_of_hours = total_overtime_hour

        return res

    def confirm_compute_sheet(self):
        ovt_obj = self.env['hr.overtime.actual.line'].search(
        [('employee_id', '=', self.employee_id.id),('state', '=', 'to_approve'),('date','>=',self.date_from),('date','<=',self.date_to)])
        if ovt_obj:
            res = {
                'type': 'ir.actions.act_window',
                'res_model': 'payslip.compute.sheet.wizard',
                'view_type': 'form',
                'view_mode': 'form',
                'name':"Confirmation Message",
                'target': 'new',
                'context':{'default_payslip_id':self.id},
            }
        else:
            res = super(HrPayslip, self).compute_sheet()
        return res