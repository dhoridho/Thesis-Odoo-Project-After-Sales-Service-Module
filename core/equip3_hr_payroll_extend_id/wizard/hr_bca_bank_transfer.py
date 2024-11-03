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

class HrBcaBankTransfer(models.TransientModel):
    _name = 'hr.bca.bank.transfer'

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, readonly=True)
    corporate_id = fields.Char('Company ID', default=lambda self: self.env.user.company_id.corporate_id, readonly=True)
    year_id = fields.Many2one('hr.payslip.period', string='Year', domain="[('state','=','open')]", required=True)
    month_id = fields.Many2one('hr.payslip.period.line', string="Month", domain="[('period_id','=',year_id)]", required=True)
    effective_transfer_date = fields.Date('Effective Transfer Date')
    company_bank_account = fields.Many2one('res.partner.bank', string='Company Bank Account')
    transfer_after_work_days = fields.Boolean('Transfer After Work Days')
    output_type = fields.Selection([("excel", "Excel"),
                              ("txt", "Txt")
                              ], string='Output Type', default="excel", required=True)
    employee_ids = fields.Many2many('hr.employee', string='Employees', required=True)

    @api.onchange("company_id")
    def _onchange_company_id(self):
        domain = {'domain': {'company_bank_account': [('partner_id', '=', self.company_id.partner_id.id)]}}
        return domain

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
        if self.output_type == "excel":
            return self.action_print_xls()
        elif self.output_type == "txt":
            return self.action_print_txt()

    def action_print_xls(self):
        if not self.employee_ids:
            raise ValidationError(_('Please select employee.'))

        company_name = self.env.company.name
        company_city = self.env.company.city or ''
        now = datetime.now().strftime("%d %b %Y %H:%M:%S")

        datas_dict = {}
        for emp in self.employee_ids:
            payslips = self.env['hr.payslip'].search([('employee_id', '=', emp.id), ('state', '=', 'done'),
                                                      ('payslip_period_id', '=', self.year_id.id),
                                                      ('month', '=', self.month_id.id),
                                                      ('payslip_pesangon', '=', False)])

            work_location = emp.location_id.name
            employee_id = emp.sequence_code
            employee_name = emp.name
            account_name = ""
            bank_name = ""
            account_number = ""
            nilai_gaji = 0
            if emp.bank_ids:
                bank_id = emp.bank_ids.filtered(lambda r: r.is_used == True)
                if bank_id:
                    account_name = bank_id[0].acc_holder
                    bank_name = bank_id[0].name.name
                    account_number = bank_id[0].acc_number
            if payslips:
                for payslip in payslips:
                    for line in payslip.line_ids:
                        if line.salary_rule_id.category_id.code == "NET":
                            nilai_gaji += line.total
                employees = {
                    'employee_id': employee_id,
                    'employee_name': employee_name,
                    'account_name': account_name,
                    'bank_name': bank_name,
                    'account_number': account_number,
                    'nilai_gaji': nilai_gaji
                }
                if not datas_dict.get(work_location, False):
                    datas_dict[work_location] = [employees]
                else:
                    datas_dict[work_location].append(employees)
        if datas_dict:
            file_name = 'BCA Bank Transfer - ' + str(self.month_id.month[:3]) + str(self.month_id.year) + '.xls'
            workbook = xlwt.Workbook(encoding="UTF-8")
            format1 = xlwt.easyxf('font:height 200; align: horiz left;')
            sheet = workbook.add_sheet('BCA Bank Transfer')
            sheet.col(0).width = int(25 * 250)
            sheet.col(1).width = int(25 * 250)
            sheet.col(2).width = int(25 * 250)
            sheet.col(3).width = int(25 * 200)
            sheet.col(4).width = int(25 * 250)
            sheet.col(5).width = int(25 * 250)
            sheet.write(0, 0, "Employee ID", format1)
            sheet.write(0, 1, "Name", format1)
            sheet.write(0, 2, "Account Name", format1)
            sheet.write(0, 3, "Bank", format1)
            sheet.write(0, 4, "Account No.", format1)
            sheet.write(0, 5, "Amount", format1)
            sheet.write(1, 0, "BCA", format1)

            row = 2
            grand_total = 0

            for location, employee in datas_dict.items():
                sheet.write(row, 0, location, format1)
                row += 1
                total = 0
                for rec in employee:
                    sheet.write(row, 0, rec["employee_id"], format1)
                    sheet.write(row, 1, rec["employee_name"], format1)
                    sheet.write(row, 2, rec["account_name"], format1)
                    sheet.write(row, 3, rec["bank_name"], format1)
                    sheet.write(row, 4, rec["account_number"], format1)
                    sheet.write(row, 5, "{:0,.2f}".format(rec["nilai_gaji"]), format1)
                    row += 1
                    total += rec["nilai_gaji"]
                sheet.write(row, 3, "Total", format1)
                sheet.write(row, 4, location, format1)
                sheet.write(row, 5, "{:0,.2f}".format(total), format1)
                row += 1
                grand_total += total

            row += 1
            sheet.write(row, 3, "Grand Total :", format1)
            sheet.write(row, 5, "{:0,.2f}".format(grand_total), format1)
            row += 2
            sheet.write(row, 0, company_city + ", " + str(now), format1)
            sheet.write(row, 4, "VERIFIED BY :", format1)
            row += 1
            sheet.write(row, 4, company_name, format1)

            fp = BytesIO()
            workbook.save(fp)
            export_id = self.env['hr.bca.bank.transfer.attachment'].create(
                {'attachment_file': base64.encodebytes(fp.getvalue()), 'file_name': file_name})
            fp.close()
            return {
                'view_mode': 'form',
                'res_id': export_id.id,
                'name': 'BCA Bank Transfer',
                'res_model': 'hr.bca.bank.transfer.attachment',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'target': 'new',
            }
        else:
            raise ValidationError(_('There is no Data.'))

    def action_print_txt(self):
        if not self.employee_ids:
            raise ValidationError(_('Please select employee.'))

        dummy1 = "00000000000"
        corporate_id = self.corporate_id.replace('/', '') if self.corporate_id else ''
        effective_transfer = datetime.strptime(str(self.effective_transfer_date), '%Y-%m-%d')
        effective_transfer_date = effective_transfer.strftime("%d")
        effective_transfer_month = effective_transfer.strftime("%m")
        effective_transfer_year = effective_transfer.strftime("%Y")
        dummy2 = "01"
        company_bank_account = self.company_bank_account.acc_number if self.company_bank_account else ' '
        non_bca = "0"
        if self.transfer_after_work_days:
            transfer_after_work_days = "1"
        else:
            transfer_after_work_days = "0"
        dummy3 = "MF"

        datas = []
        jumlah_karyawan = 0
        total_salary = 0
        for emp in self.employee_ids:
            payslips = self.env['hr.payslip'].search([('employee_id', '=', emp.id), ('state', '=', 'done'),
                                                      ('payslip_period_id', '=', self.year_id.id),
                                                      ('month', '=', self.month_id.id),
                                                      ('payslip_pesangon', '=', False)])
            employee_id = emp.sequence_code if emp.sequence_code else ' '
            employee_name = emp.name if emp.name else ' '
            department_name = emp.department_id.name if emp.department_id else ' '
            account_number = " "
            nilai_gaji = 0
            if emp.bank_ids:
                bank_id = emp.bank_ids.filtered(lambda r: r.is_used == True)[0]
                if bank_id:
                    account_number = bank_id.acc_number
            if payslips:
                for payslip in payslips:
                    for line in payslip.line_ids:
                        if line.salary_rule_id.category_id.code == "NET":
                            nilai_gaji += line.total
                jumlah_karyawan += 1
                total_salary += nilai_gaji

                datas.append({
                    'static': "0",
                    'account_number': account_number,
                    'nilai_gaji': int(nilai_gaji),
                    'employee_id': employee_id,
                    'employee_name': employee_name,
                    'department_name': department_name
                })
        if datas:
            file_name = 'BCA Bank Transfer - ' + str(self.month_id.month[:3]) + str(self.month_id.year) + '.txt'
            file_path = tempfile.mktemp(suffix='.txt')
            with open(file_path, mode='w') as file:
                file.write(
                    dummy1 + corporate_id + effective_transfer_date + dummy2 + company_bank_account + non_bca + transfer_after_work_days + dummy3 + str('{:05d}'.format(jumlah_karyawan)) + '{:014d}'.format(int(total_salary)) + ".00" + effective_transfer_month + effective_transfer_year)
                file.write("\n")
                for line in datas:
                    file.write(line.get('static') + line.get('account_number') + str('{:015d}'.format(line.get('nilai_gaji'))) + line.get('employee_id')+ line.get('employee_name')+ line.get('department_name'))
                    file.write("\n")

            with open(file_path, 'r', encoding="utf-8") as file2:
                data = str.encode(file2.read(), 'utf-8')
            export_id = self.env['hr.bca.bank.transfer.attachment'].create(
                {'attachment_file': base64.encodebytes(data), 'file_name': file_name})
            return {
                'view_mode': 'form',
                'res_id': export_id.id,
                'name': 'BCA Bank Transfer',
                'res_model': 'hr.bca.bank.transfer.attachment',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'target': 'new',
            }
        else:
            raise ValidationError(_('There is no Data.'))