# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.modules.module import get_module_path
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
import pytz
import tempfile
import csv
import base64
import openpyxl
from io import BytesIO

class HrBniBankTransferAttachment(models.TransientModel):
    _name = "hr.bni.bank.transfer.attachment"
    _description = "BNI Bank Transfer Attachment"

    attachment_file = fields.Binary('Attachment File')
    attachment_name = fields.Char('Attachment Name')

class HrBniBankTransfer(models.TransientModel):
    _name = 'hr.bni.bank.transfer'
    _description = 'BNI Bank Transfer'
	
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                    default=lambda self: self.env.company)
    partner_id = fields.Many2one(related='company_id.partner_id', string="Contact")
    output_type = fields.Selection([("excel", "Raw BNI Direct Excel"),
                                    ("csv", "CSV")
                                    ], string='Output Type', default='excel', required=True)
    year_id = fields.Many2one('hr.payslip.period', string='Year', domain="[('state','=','open')]", required=True)
    month_id = fields.Many2one('hr.payslip.period.line', string="Month", domain="[('period_id','=',year_id)]", required=True)
    debit_account_number = fields.Many2one('res.partner.bank', string='Debit Account Number', required=True, domain="[('partner_id','=',partner_id)]",
                                           help="Used to Define Debit Account used to BNI Direct Transfer. If not shown any selection, please check on related res.partner on Active Company, and check the Bank Accounts on Invoicing Section.")
    file_name = fields.Char('File Name', required=True)
    transaction_date = fields.Date('Transaction Date', default=fields.Date.today(), required=True)
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

    def action_generate(self):
        if not self.employee_ids:
            raise ValidationError(_('Please select employee.'))
        
        user_tz = self.env.user.tz or 'UTC'
        local_time = pytz.timezone(user_tz)
        file_name = self.file_name
        transaction_date = self.transaction_date.strftime("%Y%m%d")
        debit_account_number = self.debit_account_number.acc_number if self.debit_account_number else ""
        if self.output_type == "excel":
            date_now = datetime.strftime(datetime.now().astimezone(local_time), "%Y/%m/%d")
            time_now = datetime.strftime(datetime.now().astimezone(local_time), "%H:%M:%S")
            time_now_convert = time_now.replace(':','.')
            file_creation = date_now + '_' + time_now_convert
            datas_inhouse = []
            total_record_inhouse = 0
            total_amount_inhouse = 0
            datas_kliring = []
            total_record_kliring = 0
            total_amount_kliring = 0
            for emp in self.employee_ids:
                split_transfer = self.env['hr.split.bank.transfer'].search([('employee_id', '=', emp.id),('state','=','approved'),
                                                                            ('payslip_period_id', '=', self.year_id.id),
                                                                            ('month_id', '=', self.month_id.id)], limit=1)
                if split_transfer:
                    for split in split_transfer.split_bank_transfer_ids:
                        if split.name_of_bank_id == self.debit_account_number.bank_id:
                            datas_inhouse.append({
                                'rek_tujuan': str(split.acc_number),
                                'nama_penerima': str(split.acc_holder),
                                'amount': round(float(split.amount),2),
                            })
                            total_record_inhouse += 1
                            total_amount_inhouse += round(split.amount,2)
                        else:
                            datas_kliring.append({
                                'rek_tujuan': str(split.acc_number),
                                'nama_penerima': str(split.acc_holder),
                                'amount': round(float(split.amount),2),
                                'bank_tujuan': str(split.name_of_bank_id.name),
                            })
                            total_record_kliring += 1
                            total_amount_kliring += round(split.amount,2)
                else:
                    payslip = self.env['hr.payslip'].search([('employee_id', '=', emp.id),('state', '=', 'done'),
                                                            ('payslip_period_id', '=', self.year_id.id),
                                                            ('month', '=', self.month_id.id),
                                                            ('payslip_pesangon', '=', False)], limit=1)
                    if payslip:
                        emp_acc_number = ""
                        emp_bank_name = ""
                        emp_bank_account = False
                        emp_acc_holder = False
                        if emp.bank_ids:
                            bank_id = emp.bank_ids.filtered(lambda r: r.is_used == True)
                            if bank_id:
                                emp_acc_number = bank_id[0].acc_number
                                emp_bank_name = bank_id[0].name.name
                                emp_bank_account = bank_id[0].name
                                emp_acc_holder = bank_id[0].acc_holder
                            else:
                                bank_other_id = emp.bank_ids.filtered(lambda r: r.is_used == False)
                                emp_acc_number = bank_other_id[0].acc_number if bank_other_id else ""
                                emp_bank_name = bank_other_id[0].name.name if bank_other_id else ""
                                emp_bank_account = bank_other_id[0].name if bank_other_id else False
                                emp_acc_holder = bank_other_id[0].acc_holder if bank_other_id else ""
                        nilai_salary = 0
                        for slip in payslip:
                            for line in slip.line_ids:
                                if line.salary_rule_id.code == "THP":
                                    nilai_salary += line.total
                        if emp_bank_account == self.debit_account_number.bank_id:
                            datas_inhouse.append({
                                'rek_tujuan': str(emp_acc_number),
                                'nama_penerima': str(emp_acc_holder),
                                'amount': round(float(nilai_salary),2),
                            })
                            total_record_inhouse += 1
                            total_amount_inhouse += round(nilai_salary,2)
                        else:
                            datas_kliring.append({
                                'rek_tujuan': str(emp_acc_number),
                                'nama_penerima': str(emp_acc_holder),
                                'amount': round(float(nilai_salary),2),
                                'bank_tujuan': str(emp_bank_name),
                            })
                            total_record_kliring += 1
                            total_amount_kliring += round(nilai_salary,2)
            
            if datas_inhouse or datas_kliring:
                module_path = get_module_path('equip3_hr_payroll_extend_id')
                path =  module_path + '/static/src/file/BNIDIRECT - EXCEL TEMPLATE v1.8.1.xlsx'
                workbook = openpyxl.load_workbook(filename=path)
                sheet_inhouse = workbook["Inhouse"]
                if datas_inhouse:
                    sheet_inhouse['A6'] = file_creation
                    sheet_inhouse['C6'] = file_name
                    sheet_inhouse['A8'] = "P"
                    sheet_inhouse['B8'] = transaction_date
                    sheet_inhouse['C8'] = debit_account_number
                    sheet_inhouse['D8'] = total_record_inhouse
                    sheet_inhouse['E8'] = total_amount_inhouse
                    no = 10
                    for line in datas_inhouse:
                        sheet_inhouse['A'+str(no)] = line.get('rek_tujuan')
                        sheet_inhouse['B'+str(no)] = line.get('nama_penerima')
                        sheet_inhouse['C'+str(no)] = line.get('amount')
                        no+=1
                
                sheet_kliring = workbook["Kliring"]
                if datas_kliring:
                    sheet_kliring['A6'] = file_creation
                    sheet_kliring['C6'] = file_name
                    sheet_kliring['A8'] = "P"
                    sheet_kliring['B8'] = transaction_date
                    sheet_kliring['C8'] = debit_account_number
                    sheet_kliring['D8'] = total_record_kliring
                    sheet_kliring['E8'] = total_amount_kliring
                    no = 10
                    for line in datas_kliring:
                        sheet_kliring['A'+str(no)] = line.get('rek_tujuan')
                        sheet_kliring['B'+str(no)] = line.get('nama_penerima')
                        sheet_kliring['C'+str(no)] = line.get('amount')
                        sheet_kliring['H'+str(no)] = line.get('bank_tujuan')
                        no+=1

                fp = BytesIO()
                workbook.save(fp)
                export_id = self.env['hr.bni.bank.transfer.attachment'].create(
                    {'attachment_file': base64.encodebytes(fp.getvalue()), 'attachment_name': 'BNIDIRECT - EXCEL TEMPLATE v1.8.1.xlsx'})
                fp.close()
                return {
                    'view_mode': 'form',
                    'res_id': export_id.id,
                    'name': 'BNI Bank Transfer Attachment',
                    'res_model': 'hr.bni.bank.transfer.attachment',
                    'view_type': 'form',
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                }
            else:
                raise ValidationError(_('There is no Data.'))
        else:
            datetime_now = datetime.strftime(datetime.now().astimezone(local_time), "%d/%m/%Y %H:%M")
            jumlah_karyawan = 0
            total_salary = 0
            datas = []
            for emp in self.employee_ids:
                payslip = self.env['hr.payslip'].search([('employee_id', '=', emp.id),('state', '=', 'done'),
                                                        ('payslip_period_id', '=', self.year_id.id),
                                                        ('month', '=', self.month_id.id),
                                                        ('payslip_pesangon', '=', False)], limit=1)
                emp_acc_number = ""
                if emp.bank_ids:
                    bank_id = emp.bank_ids.filtered(lambda r: r.is_used == True)
                    if bank_id:
                        emp_acc_number = bank_id[0].acc_number
                    else:
                        bank_other_id = emp.bank_ids.filtered(lambda r: r.is_used == False)
                        emp_acc_number = bank_other_id[0].acc_number if bank_other_id else ""
                if emp.work_email:
                    have_work_email = "Y"
                    work_email = emp.work_email
                else:
                    have_work_email = "N"
                    work_email = ""
                nilai_salary = 0
                if payslip:
                    for slip in payslip:
                        for line in slip.line_ids:
                            if line.salary_rule_id.code == "THP":
                                nilai_salary += line.total
                    jumlah_karyawan += 1
                    total_salary += nilai_salary
                    datas.append({
                        'emp_acc_number': str(emp_acc_number),
                        'employee_name': emp.name,
                        'nilai_salary': str(int(nilai_salary)),
                        'have_work_email': have_work_email,
                        'work_email': work_email,
                    })
            if datas:
                attachment_name = file_name + '_IH_' + str(transaction_date) + '.csv'
                file_path = tempfile.mktemp(suffix='.csv')
                total_baris = 2
                with open(file_path, mode='w') as file:
                    writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                    writer.writerow(['P', transaction_date, debit_account_number, jumlah_karyawan, int(total_salary)] + [''] * 15)
                    for line in datas:
                        writer.writerow([line.get('emp_acc_number'), line.get('employee_name'), line.get('nilai_salary')] +
                                        [''] * 13 + [line.get('have_work_email'), line.get('work_email'), '', 'N'])
                        total_baris += 1
                
                ## baca baris pertama, preparing values
                with open(file_path, "r", encoding="utf-8") as infile:
                    reader = list(csv.reader(infile))
                    reader.insert(0, [datetime_now, total_baris, file_name] + [''] * 17)
                
                ## proses insert/write baris pertama
                with open(file_path, "w") as outfile:
                    writer_insert = csv.writer(outfile)
                    for line in reader:
                        writer_insert.writerow(line)
                
                with open(file_path, 'r', encoding="utf-8") as f2:
                    data = str.encode(f2.read(), 'utf-8')
                export_id = self.env['hr.bni.bank.transfer.attachment'].create(
                    {'attachment_file': base64.encodebytes(data), 'attachment_name': attachment_name})
                return {
                    'view_mode': 'form',
                    'res_id': export_id.id,
                    'name': 'BNI Bank Transfer Attachment',
                    'res_model': 'hr.bni.bank.transfer.attachment',
                    'view_type': 'form',
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                }
            else:
                raise ValidationError(_('There is no Data.'))
