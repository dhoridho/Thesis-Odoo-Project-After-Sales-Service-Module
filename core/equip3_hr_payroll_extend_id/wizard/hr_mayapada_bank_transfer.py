# -*- coding: utf-8 -*-
import calendar
from odoo import api, fields, models, _
from datetime import datetime
import time
from odoo.exceptions import ValidationError
import tempfile
import csv
import base64
from io import BytesIO

class HrMayapadaBankTransfer(models.TransientModel):
    _name = 'hr.mayapada.bank.transfer'

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, readonly=True)
    corporate_id = fields.Char('Company ID', default=lambda self: self.env.user.company_id.corporate_id, readonly=True)
    year_id = fields.Many2one('hr.payslip.period', string='Year', domain="[('state','=','open')]", required=True)
    month_id = fields.Many2one('hr.payslip.period.line', string="Month", domain="[('period_id','=',year_id)]", required=True)
    transaction_date = fields.Date('Transaction Date', default=datetime.today(), required=True)
    company_bank_account = fields.Many2one('res.partner.bank', string='Company Bank Account', required=True)
    remarks = fields.Char('Remarks', required=True)
    employee_ids = fields.Many2many('hr.employee', string='Employees', required=True)

    @api.onchange("company_id")
    def _onchange_company_id(self):
        domain = {'domain': {'company_bank_account': [('partner_id', '=', self.company_id.partner_id.id)]}}
        return domain

    @api.onchange('month_id')
    def onchange_month_id(self):
        self.employee_ids = [(5,0,0)]
        if (not self.month_id):
            return

        self.remarks = _('Gaji %s %s') % (self.month_id.month, self.month_id.year)
    
    @api.onchange('year_id')
    def _onchange_year_id(self):
        if self.year_id:
            self.month_id = False

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

    def action_print_csv(self):
        if not self.employee_ids:
            raise ValidationError(_('Please select employee.'))

        corporate_id = self.corporate_id.replace('/', '') if self.corporate_id else ''
        remarks = self.remarks
        transaction_date = self.transaction_date.strftime('%d%m%Y')
        company_bank_account = self.company_bank_account.acc_number if self.company_bank_account else ''

        datas = []
        jumlah_karyawan = 0
        total_salary = 0
        for emp in self.employee_ids:
            payslips = self.env['hr.payslip'].search([('employee_id', '=', emp.id), ('state', '=', 'done'),
                                                      ('payslip_period_id', '=', self.year_id.id),
                                                      ('month', '=', self.month_id.id),
                                                      ('payslip_pesangon', '=', False)])

            employee_id = emp.sequence_code if emp.sequence_code else ''
            employee_name = emp.name
            account_number = ""
            nilai_gaji = 0
            if emp.bank_ids:
                bank_id = emp.bank_ids.filtered(lambda r: r.is_used == True)
                if bank_id:
                    account_number = bank_id[0].acc_number
            if payslips:
                currency = ''
                for payslip in payslips:
                    currency = payslip.currency_id.name if payslip.currency_id else ''
                    for line in payslip.line_ids:
                        if line.salary_rule_id.category_id.code == "NET":
                            nilai_gaji += line.total
                jumlah_karyawan += 1
                total_salary += nilai_gaji
                datas.append({
                    'employee_id': employee_id,
                    'account_number': str(account_number),
                    'employee_name': employee_name,
                    'nilai_gaji': str(int(nilai_gaji))
                })
        if datas:
            file_name = 'Mayapada Bank Transfer - ' + str(self.month_id.month[:3]) + str(self.month_id.year) + '.csv'
            file_path = tempfile.mktemp(suffix='.csv')
            with open(file_path, mode='w') as file:
                writer = csv.writer(file, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                writer.writerow(['00', corporate_id, remarks] + [''] * 334)
                for line in datas:
                    writer.writerow(['01', 'IT', 'Payroll With Bii', 'ID', transaction_date] + [''] * 2 +
                                    [line.get('employee_id'), 'Reff 01', remarks, 'IDR', line.get('nilai_gaji'),
                                     'N', 'IDR', company_bank_account, line.get('account_number')] + [''] * 2 +
                                    ['Y', line.get('employee_name')] + [''] * 11 + ['ID'] + [''] * 69 + ['Payroll 01',
                                    remarks] + [''] * 6 + ['01'] + [''] * 227)
                writer.writerow(['99', jumlah_karyawan, int(total_salary)] + [''] * 334)
            with open(file_path, 'r', encoding="utf-8") as f2:
                data = str.encode(f2.read(), 'utf-8')
            export_id = self.env['hr.mayapada.bank.transfer.attachment'].create(
                {'attachment_file': base64.encodebytes(data), 'file_name': file_name})
            return {
                'view_mode': 'form',
                'res_id': export_id.id,
                'name': 'Mayapada Bank Transfer',
                'res_model': 'hr.mayapada.bank.transfer.attachment',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'target': 'new',
            }
        else:
            raise ValidationError(_('There is no Data.'))