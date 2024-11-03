# -*- coding: utf-8 -*-
import calendar
from odoo import api, fields, models, _
from datetime import datetime
import time
from odoo.exceptions import ValidationError
import xlwt
import base64
from io import BytesIO

class HrHsbcBankTransferAttachment(models.TransientModel):
    _name = "hr.hsbc.bank.transfer.attachment"
    _description = "HSBC Bank Transfer Attachment"

    attachment_file = fields.Binary('Attachment File')
    file_name = fields.Char('File Name')

class HrHsbcBankTransfer(models.TransientModel):
    _name = 'hr.hsbc.bank.transfer'
    _description = "HSBC Bank Transfer"

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, readonly=True)
    corporate_id = fields.Char('Company ID', default=lambda self: self.env.user.company_id.corporate_id, readonly=True)
    year_id = fields.Many2one('hr.payslip.period', string='Year', domain="[('state','=','open')]", required=True)
    month_id = fields.Many2one('hr.payslip.period.line', string="Month", domain="[('period_id','=',year_id)]", required=True)
    debit_acc_number = fields.Char('Debit Account Number', required=True)
    value_date = fields.Date('Value Date', required=True)
    payment_set_code = fields.Selection([("HN1", "HN1"),
                                         ("HN2", "HN2"),
                                         ("HN3", "HN3")
                                         ], string='Payment Set Code', required=True)
    reg_reporting = fields.Selection([("/SKN/11", "/SKN/11"),
                                      ("/SKN/12", "/SKN/12"),
                                      ("/SKN/21", "/SKN/21"),
                                      ("/SKN/22", "/SKN/22"),
                                      ("/SKN/31", "/SKN/31"),
                                      ("/SKN/32", "/SKN/32")
                                      ], string='Regulatory Reporting 2', required=True)
    employee_ids = fields.Many2many('hr.employee', string='Employees', required=True)

    @api.onchange('year_id')
    def _onchange_year_id(self):
        if self.year_id:
            self.month_id = False
    
    @api.onchange('month_id')
    def _onchange_month_id(self):
        self.employee_ids = [(5,0,0)]

    @api.onchange('employee_ids','year_id','month_id','company_id')
    def _onchange_employee_ids(self):
        employees = []
        if self.year_id and self.month_id and self.company_id:
            payslips = self.env['hr.payslip'].search([('state', '=', 'done'),
                                                      ('payslip_period_id', '=', self.year_id.id),
                                                      ('month', '=', self.month_id.id),
                                                      ('company_id', '=', self.company_id.id),
                                                      ('payslip_pesangon', '=', False)])
            if payslips:
                for slip in payslips:
                    employees.append(slip.employee_id.id)
        return {
            'domain': {'employee_ids': [('id', 'in', employees)]},
        }
    
    def action_print(self):
        return self.action_print_xls()

    def action_print_xls(self):
        if not self.employee_ids:
            raise ValidationError(_('Please select employee.'))
        
        debit_acc_number = self.debit_acc_number
        value_date = self.value_date.strftime('%Y%m%d')
        payment_set_code = self.payment_set_code
        reg_reporting = self.reg_reporting

        datas = []
        for emp in self.employee_ids:
            payslips = self.env['hr.payslip'].search([('employee_id', '=', emp.id), ('state', '=', 'done'),
                                                      ('payslip_period_id', '=', self.year_id.id),
                                                      ('month', '=', self.month_id.id),
                                                      ('payslip_pesangon', '=', False)])
            employee_name = emp.name
            bank_code = ""
            account_number = ""
            if emp.bank_ids:
                bank_id = emp.bank_ids.filtered(lambda r: r.is_used == True)
                if bank_id:
                    bank_code = bank_id[0].name.code
                    account_number = bank_id[0].acc_number
            
            salary = 0
            payslip_ref = ""
            if payslips:
                for payslip in payslips:
                    for line in payslip.line_ids:
                        if line.salary_rule_id.code == "THP":
                            salary += line.total
                    if payslip.payslip_run_id:
                        payslip_ref = payslip.payslip_run_id.name
            
            employees = {
                'employee_name': employee_name,
                'bank_code': bank_code,
                'account_number': account_number,
                'salary': salary,
                'payslip_ref': payslip_ref
            }
            datas.append(employees)
        if datas:
            file_name = 'HSBC Bank Transfer - ' + str(self.month_id.month[:3]) + str(self.month_id.year) + '.xls'
            workbook = xlwt.Workbook(encoding="UTF-8")
            format_green1 = xlwt.easyxf('font:height 200,bold True; align: horiz left; alignment: wrap True; pattern: pattern solid, fore_colour lime; borders: top_color black, bottom_color black, right_color black, left_color black, left thin, right thin, top thin, bottom thin;')
            format_green2 = xlwt.easyxf('font:height 200,bold True; align: horiz center, vert center; alignment: wrap True; pattern: pattern solid, fore_colour lime; borders: top_color black, bottom_color black, right_color black, left_color black, left thin, right thin, top thin, bottom thin;')
            text_top = xlwt.easyxf('font:height 200; align: horiz left;')
            format_yellow1 = xlwt.easyxf('font:height 200,bold True; align: horiz left; alignment: wrap True; pattern: pattern solid, fore_colour yellow; borders: top_color black, bottom_color black, right_color black, left_color black, left thin, right thin, top thin, bottom thin;')
            format_yellow2 = xlwt.easyxf('font:height 200,bold True; align: horiz center, vert center; alignment: wrap True; pattern: pattern solid, fore_colour yellow; borders: top_color black, bottom_color black, right_color black, left_color black, left thin, right thin, top thin, bottom thin;')
            text_row = xlwt.easyxf('font:height 200; align: horiz left; borders: top_color black, bottom_color black, right_color black, left_color black, left thin, right thin, top thin, bottom thin;')
            amount = xlwt.easyxf('font:height 200; align: horiz right; borders: top_color black, bottom_color black, right_color black, left_color black, left thin, right thin, top thin, bottom thin;')
            sheet = workbook.add_sheet('HSBC Bank Transfer')
            sheet.col(0).width = int(25 * 300)
            sheet.col(1).width = int(25 * 300)
            sheet.col(2).width = int(25 * 300)
            sheet.col(3).width = int(25 * 300)
            sheet.col(4).width = int(25 * 300)
            sheet.col(5).width = int(25 * 300)
            sheet.col(6).width = int(25 * 300)
            sheet.col(7).width = int(25 * 300)
            sheet.col(8).width = int(25 * 300)
            sheet.col(9).width = int(25 * 300)
            sheet.col(10).width = int(25 * 300)
            sheet.col(11).width = int(25 * 300)
            sheet.col(12).width = int(25 * 300)
            sheet.col(13).width = int(25 * 300)
            sheet.col(14).width = int(25 * 300)
            sheet.col(15).width = int(25 * 300)
            sheet.col(16).width = int(25 * 300)
            sheet.write(0, 0, "Debit Account Number\n(12 characters)", format_green1)
            sheet.write(0, 1, debit_acc_number, text_top)
            sheet.write(1, 0, "Value Date (YYYYMMDD)", format_green1)
            sheet.write(1, 1, value_date, text_top)
            sheet.write(2, 0, "Payment Set Code\n(3 characters)", format_green1)
            sheet.write(2, 1, payment_set_code, text_top)
            sheet.write(3, 0, "Beneficiary Name\n(70 characters)", format_green1)
            sheet.write(3, 1, "Amount\n(14 characters)", format_green1)
            sheet.write(3, 2, "Beneficiary Bank Code\n(12 characters)", format_green1)
            sheet.write(3, 3, "Beneficiary account number\n(20 characters)", format_green1)
            sheet.write(3, 4, "Beneficiary Reference\n(12 characters)", format_yellow1)
            sheet.write(3, 5, "Email Advice Recepient 1", format_yellow2)
            sheet.write(3, 6, "Email Advice Recepient 2", format_yellow2)
            sheet.write(3, 7, "Email Advice Recepient 3", format_yellow2)
            sheet.write(3, 8, "Email Advice Recepient 4", format_yellow2)
            sheet.write(3, 9, "Email Advice Recepient 5", format_yellow2)
            sheet.write(3, 10, "Email Advice Recepient 6", format_yellow2)
            sheet.write(3, 11, "Free Text", format_yellow2)
            sheet.write(3, 12, "Regulatory Reporting 1", format_yellow2)
            sheet.write(3, 13, "Regulatory Reporting 2", format_green2)
            sheet.write(3, 14, "Regulatory Reporting 3", format_yellow2)
            sheet.write(3, 15, "Currency\n(3 ISO characters)", format_yellow2)
            sheet.write(3, 16, "Customer Reference\n(12 characters)", format_yellow2)

            row = 4
            for line in datas:
                sheet.write(row, 0, line.get('employee_name'), text_row)
                sheet.write(row, 1, int(line.get('salary')), amount)
                sheet.write(row, 2, line.get('bank_code'), text_row)
                sheet.write(row, 3, line.get('account_number'), text_row)
                sheet.write(row, 4, line.get('payslip_ref'), text_row)
                sheet.write(row, 5, "", text_row)
                sheet.write(row, 6, "", text_row)
                sheet.write(row, 7, "", text_row)
                sheet.write(row, 8, "", text_row)
                sheet.write(row, 9, "", text_row)
                sheet.write(row, 10, "", text_row)
                sheet.write(row, 11, "", text_row)
                sheet.write(row, 12, "", text_row)
                sheet.write(row, 13, reg_reporting, text_row)
                sheet.write(row, 14, "", text_row)
                sheet.write(row, 15, "", text_row)
                sheet.write(row, 16, "", text_row)
                row += 1
            
            fp = BytesIO()
            workbook.save(fp)
            export_id = self.env['hr.hsbc.bank.transfer.attachment'].create(
                {'attachment_file': base64.encodebytes(fp.getvalue()), 'file_name': file_name})
            fp.close()
            return {
                'view_mode': 'form',
                'res_id': export_id.id,
                'name': 'HSBC Bank Transfer',
                'res_model': 'hr.hsbc.bank.transfer.attachment',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'target': 'new',
            }
        else:
            raise ValidationError(_('There is no Data.'))
