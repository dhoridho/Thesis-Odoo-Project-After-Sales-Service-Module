# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def get_installment_loan(self, payslip, date_from, date_to):
        payslip_rec = self.sudo().browse(payslip)[0]
        amount = 0.0
        loan_installment = self.env['loan.installment.details'].sudo().search([('employee_id','=',payslip_rec.employee_id.id),('loan_state','=','disburse'),('loan_repayment_method','=','payroll')])
        for rec in loan_installment:
            if rec.full_loan_payment_id:
                if rec.full_loan_payment_id.state == 'approve':
                    if rec.full_loan_payment_id.payment_date >= date_from and rec.full_loan_payment_id.payment_date <= date_to:
                        amount += rec.total
                        rec.payslip_id = payslip_rec.id
                else:
                    rec.payslip_id = False
            else:
                if rec.deduction_based_period == "date_from":
                    if rec.date_from >= date_from and rec.date_from <= date_to:
                        amount = rec.total
                        rec.payslip_id = payslip_rec.id
                elif rec.deduction_based_period == "date_to":
                    if rec.date_to >= date_from and rec.date_to <= date_to:
                        amount = rec.total
                        rec.payslip_id = payslip_rec.id
        return amount

    def get_loan(self, payslip, date_from, date_to):
        payslip_rec = self.sudo().browse(payslip)[0]
        amount = 0.0
        loan = self.env['employee.loan.details'].sudo().search([('employee_id','=',payslip_rec.employee_id.id),('state','=','approved'),('disburse_method','=','payroll')])
        for rec in loan:
            if rec.date_disb:
                if rec.date_disb >= date_from and rec.date_disb <= date_to:
                    amount = rec.principal_amount
                    rec.payslip_id = payslip_rec.id
        return amount