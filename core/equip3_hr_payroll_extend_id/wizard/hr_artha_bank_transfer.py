# -*- coding: utf-8 -*-
import calendar
import math
from odoo import api, fields, models, _
from datetime import datetime
import time
from odoo.exceptions import ValidationError
import tempfile
import xlwt
import base64
from io import BytesIO

class HrArthaBankTransferAttachment(models.TransientModel):
    _name = "hr.artha.bank.transfer.attachment"
    _description = "Artha Graha Bank Transfer Attachment"

    attachment_file = fields.Binary('Attachment File')
    file_name = fields.Char('File Name')

class HrArthaBankTransfer(models.TransientModel):
    _name = 'hr.artha.bank.transfer'

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, readonly=True)
    corporate_id = fields.Char('Company ID', default=lambda self: self.env.user.company_id.corporate_id, readonly=True)
    year_id = fields.Many2one('hr.payslip.period', string='Year', domain="[('state','=','open')]", required=True)
    month_id = fields.Many2one('hr.payslip.period.line', string="Month", domain="[('period_id','=',year_id)]", required=True)
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
        datas = []
        for emp in self.employee_ids:
            payslips = self.env['hr.payslip'].search([('employee_id', '=', emp.id), ('state', '=', 'done'),
                                                      ('payslip_period_id', '=', self.year_id.id),
                                                      ('month', '=', self.month_id.id),
                                                      ('payslip_pesangon', '=', False)])
            employee_id = emp.sequence_code
            employee_name = emp.name
            bank_name = ""
            account_name = ""
            account_number = ""
            if emp.bank_ids:
                bank_id = emp.bank_ids.filtered(lambda r: r.is_used == True)
                if bank_id:
                    bank_name = bank_id[0].name.name
                    account_name = bank_id[0].acc_holder
                    account_number = bank_id[0].acc_number
            
            salary = 0
            if payslips:
                for payslip in payslips:
                    for line in payslip.line_ids:
                        if line.salary_rule_id.code == "THP":
                            salary += line.total

                employees = {
                    'employee_id': employee_id,
                    'employee_name': employee_name,
                    'bank_name': bank_name,
                    'account_name': account_name,
                    'account_number': account_number,
                    'salary': salary
                }
                datas.append(employees)
        if datas:
            file_name = 'Artha Graha Bank Transfer - ' + str(self.month_id.month[:3]) + str(self.month_id.year) + '.xls'
            workbook = xlwt.Workbook(encoding="UTF-8")
            format1 = xlwt.easyxf('font:height 200; align: horiz left;')
            format2 = xlwt.easyxf('font:height 200,bold True; align: horiz left;')
            sheet = workbook.add_sheet('Artha Bank Transfer')
            sheet.col(1).width = int(25 * 250)
            sheet.col(2).width = int(25 * 250)
            sheet.col(3).width = int(25 * 250)
            sheet.col(4).width = int(25 * 250)
            sheet.col(5).width = int(25 * 250)
            sheet.col(6).width = int(25 * 250)
            sheet.write(0, 0, "No", format1)
            sheet.write(0, 1, "Employee ID", format1)
            sheet.write(0, 2, "Name", format1)
            sheet.write(0, 3, "Bank Name", format1)
            sheet.write(0, 4, "Account Name", format1)
            sheet.write(0, 5, "Account No.", format1)
            sheet.write(0, 6, "Salary", format1)

            row = 1
            counter = 1
            grand_total = 0
            for line in datas:
                sheet.write(row, 0, counter, format1)
                sheet.write(row, 1, line.get('employee_id'), format1)
                sheet.write(row, 2, line.get('employee_name'), format1)
                sheet.write(row, 3, line.get('bank_name'), format1)
                sheet.write(row, 4, line.get('account_name'), format1)
                sheet.write(row, 5, line.get('account_number'), format1)
                sheet.write(row, 6, "{:0,.2f}".format(line.get('salary')), format1)
                row += 1
                counter += 1
                grand_total += line.get('salary')
            sheet.write(row, 5, "Grand Total", format2)
            sheet.write(row, 6, "{:0,.2f}".format(grand_total), format2)

            fp = BytesIO()
            workbook.save(fp)
            export_id = self.env['hr.artha.bank.transfer.attachment'].create(
                {'attachment_file': base64.encodebytes(fp.getvalue()), 'file_name': file_name})
            fp.close()
            return {
                'view_mode': 'form',
                'res_id': export_id.id,
                'name': 'Artha Graha Bank Transfer',
                'res_model': 'hr.artha.bank.transfer.attachment',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'target': 'new',
            }
        else:
            raise ValidationError(_('There is no Data.'))