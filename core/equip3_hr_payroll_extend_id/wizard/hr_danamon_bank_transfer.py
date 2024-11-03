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

class HrDanamonBankTransfer(models.TransientModel):
    _name = 'hr.danamon.bank.transfer'

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, readonly=True)
    corporate_id = fields.Char('Company ID', default=lambda self: self.env.user.company_id.corporate_id, readonly=True)
    year_id = fields.Many2one('hr.payslip.period', string='Year', domain="[('state','=','open')]", required=True)
    month_id = fields.Many2one('hr.payslip.period.line', string="Month", domain="[('period_id','=',year_id)]", required=True)
    bank_transfer_code = fields.Char('Bank Transfer Code', required=True)
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

        company_name = self.env.company.name
        company_city = self.env.company.city or ''
        remarks = self.remarks
        bank_transfer_code = self.bank_transfer_code
        company_bank_account = self.company_bank_account.acc_number if self.company_bank_account else ''

        datas = []
        sequence = 1
        for emp in self.employee_ids:
            payslips = self.env['hr.payslip'].search([('employee_id', '=', emp.id), ('state', '=', 'done'),
                                                      ('payslip_period_id', '=', self.year_id.id),
                                                      ('month', '=', self.month_id.id),
                                                      ('payslip_pesangon', '=', False)])

            employee_name = emp.name
            account_number = ""
            bank_unit = ""
            nilai_gaji = 0
            if emp.bank_ids:
                bank_id = emp.bank_ids.filtered(lambda r: r.is_used == True)
                if bank_id:
                    account_number = bank_id[0].acc_number
                    bank_unit = bank_id[0].bank_unit
            if payslips:
                currency = ''
                for payslip in payslips:
                    currency = payslip.currency_id.name if payslip.currency_id else ''
                    for line in payslip.line_ids:
                        if line.salary_rule_id.category_id.code == "NET":
                            nilai_gaji += line.total
                datas.append({
                    'company_bank_account': company_bank_account,
                    'bank_transfer_code': bank_transfer_code,
                    'remarks': remarks,
                    'account_number': str(account_number),
                    'employee_name': employee_name,
                    'currency': currency,
                    'bank_unit': bank_unit,
                    'sequence': str(sequence),
                    'nilai_gaji': str(int(nilai_gaji))
                })
                sequence += 1
        if datas:
            file_name = 'Danamon Bank Transfer - ' + str(self.month_id.month[:3]) + str(self.month_id.year) + '.csv'
            file_path = tempfile.mktemp(suffix='.csv')
            with open(file_path, mode='w') as file:
                writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                writer.writerow(['H', '', '', 'S', 'Y', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '',
                                 '', '', '', '', '', '', '', '', '', ''])
                for line in datas:
                    val1 = "D"
                    val2 = "LAC"
                    val3 = "1"
                    val4 = line.get('company_bank_account')
                    val5 = line.get('remarks')
                    val6 = ""
                    val7 = ""
                    val8 = line.get('bank_transfer_code')
                    val9 = ""
                    val10 = line.get('account_number')
                    val11 = line.get('employee_name')
                    val12 = line.get('currency')
                    val13 = line.get('bank_unit')
                    val14 = ""
                    val15 = ""
                    val16 = ""
                    val17 = ""
                    val18 = line.get('remarks')
                    val19 = line.get('sequence')
                    val20 = ""
                    val21 = ""
                    val22 = line.get('nilai_gaji')
                    val23 = ""
                    val24 = ""
                    val25 = "REM"
                    val26 = "S"
                    val27 = ""
                    val28 = ""
                    val29 = ""
                    val30 = ""
                    val31 = "Y"
                    writer.writerow([val1, val2, val3, val4, val5, val6, val7, val8, val9, val10, val11, val12, val13,
                                     val14, val15, val16, val17, val18, val19, val20, val21, val22, val23, val24, val25,
                                     val26, val27, val28, val29, val30, val31])
            with open(file_path, 'r', encoding="utf-8") as f2:
                data = str.encode(f2.read(), 'utf-8')
            export_id = self.env['hr.danamon.bank.transfer.attachment'].create(
                {'attachment_file': base64.encodebytes(data), 'file_name': file_name})
            return {
                'view_mode': 'form',
                'res_id': export_id.id,
                'name': 'Danamon Bank Transfer',
                'res_model': 'hr.danamon.bank.transfer.attachment',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'target': 'new',
            }
        else:
            raise ValidationError(_('There is no Data.'))