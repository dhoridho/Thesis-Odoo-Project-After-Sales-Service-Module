# -*- coding: utf-8 -*-
import calendar
import math
from odoo import api, fields, models, _
from datetime import datetime
import time
from odoo.exceptions import ValidationError
import xlwt
import csv
import base64
import tempfile
from io import BytesIO

class HrSptReport1721I(models.TransientModel):
    _name = 'hr.spt.report.1721_i'

    def _compute_year_selection(self):
        year_list = []
        current_year = int(time.strftime('%Y'))
        # year_list = range(current_year, current_year - 11, -1)

        year_range = range(2015, current_year + 1)
        for year in reversed(year_range):
            year_list.append((str(year), str(year)))
        return year_list

    def _compute_month_selection(self):
        month_list = []
        for x in range(1, 13):
            month_list.append((str(calendar.month_name[x]), str(calendar.month_name[x])))
        return month_list
    
    @api.model
    def _employee_domain(self):
        domain =  [('company_id','=',self.env.company.id)]
        return domain

    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
								 default=lambda self: self.env.company)
    year = fields.Selection(selection=lambda self: self._compute_year_selection(), string="Year", default="none",
                            required=True)
    month = fields.Selection(selection=lambda self: self._compute_month_selection(), string="Month", default="none",
                             required=True)
    branch_id = fields.Many2one("res.branch", string="Branch", domain="[('company_id', '=', company_id)]")
    employee_ids = fields.Many2many('hr.employee', string='Employees', required=True,domain=_employee_domain)

    def round_down(self, n, decimals=0):
        multiplier = 10 ** decimals
        return math.floor(n * multiplier) / multiplier
    
    @api.onchange('branch_id')
    def _onchange_branch(self):
        if self.branch_id:
            return {'domain': {'employee_ids': [('company_id','=',self.company_id.id),('branch_id','=',self.branch_id.id)]}}
        else:
            return {'domain': {'employee_ids': [('company_id','=',self.company_id.id)]}}

    def action_print_csv(self):
        if not self.employee_ids:
            raise ValidationError(_('Please select employee.'))

        datas = []
        for emp in self.employee_ids:
            month_datetime = datetime.strptime(self.month, "%B")
            selected_month_number = month_datetime.month
            last_day_month = calendar.monthrange(int(self.year), selected_month_number)[1]
            month_selected = str('{:02d}'.format(selected_month_number))
            selected_month_start_date = self.year + '-' + month_selected + '-' + str('01')
            selected_month_start_date = datetime.strptime(selected_month_start_date, "%Y-%m-%d").date()
            selected_month_end_date = self.year + '-' + month_selected + '-' + str(last_day_month)
            selected_month_end_date = datetime.strptime(selected_month_end_date, "%Y-%m-%d").date()

            payslips = self.env['hr.payslip'].search([('employee_id', '=', emp.id), ('state', '=', 'done'),
                                                      ('payslip_report_date', '>=', selected_month_start_date),
                                                      ('payslip_report_date', '<=', selected_month_end_date),
                                                      ('payslip_pesangon', '=', False)])

            npwp_no = str(emp.npwp_no).replace('-', '') if emp.npwp_no else ''
            country_domicile_code = self.env['country.domicile.code'].search([('country_id', '=', emp.country_id.id)],
                                                                             limit=1)
            ptkp = emp.ptkp_id.ptkp_amount if emp.ptkp_id else 0

            if payslips:
                income_reguler = 0
                income_irreguler = 0
                pph_reguler = 0
                pph_irreguler = 0
                for payslip in payslips:
                    for line in payslip.income_reguler_ids:
                        income_reguler += line.amount
                    for line in payslip.income_irreguler_ids:
                        income_irreguler += line.amount
                    for line in payslip.line_ids:
                        if line.salary_rule_id.code == "PPH21_REG":
                            pph_reguler += line.total
                        if line.salary_rule_id.code == "PPH21_IRREG":
                            pph_irreguler += line.total

                jumlah_bruto = income_reguler + income_irreguler
                jumlah_pph = pph_reguler + pph_irreguler

                # if jumlah_pph > 0:
                datas.append({
                    'masa_pajak': selected_month_number,
                    'tahun_pajak': self.year,
                    'pembetulan': "0",
                    'npwp': npwp_no,
                    'employee_name': emp.name,
                    'kode_pajak': '21-100-01',
                    'jumlah_bruto': jumlah_bruto,
                    'jumlah_pph': jumlah_pph,
                    'kode_negara': country_domicile_code.name or '',
                })

        if datas:
            file_name = '1721_I_' + str(month_datetime.strftime("%b")) + str(self.year) + '.csv'
            file_path = tempfile.mktemp(suffix='.csv')
            with open(file_path, mode='w') as file:
                writer = csv.writer(file, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                writer.writerow(['Masa Pajak', 'Tahun Pajak', 'Pembetulan', 'NPWP', 'Nama', 'Kode Pajak', 'Jumlah Bruto',
                                 'Jumlah PPH', 'Kode Negara'])
                for line in datas:
                    val1 = line.get('masa_pajak')
                    val2 = line.get('tahun_pajak')
                    val3 = line.get('pembetulan')
                    val4 = line.get('npwp').replace('.', '')
                    val5 = line.get('employee_name')
                    val6 = line.get('kode_pajak')
                    val7 = str(int(line.get('jumlah_bruto')))
                    val8 = str(int(line.get('jumlah_pph')))
                    val9 = line.get('country_domicile_code')
                    writer.writerow([val1, val2, val3, val4, val5, val6, val7, val8, val9])
            with open(file_path, 'r', encoding="utf-8") as f2:
                data = str.encode(f2.read(), 'utf-8')
            export_id = self.env['hr.spt.report.1721_i.attachment'].create(
                {'attachment_file': base64.encodebytes(data), 'file_name': file_name})
            return {
                'view_mode': 'form',
                'res_id': export_id.id,
                'name': '1721 I',
                'res_model': 'hr.spt.report.1721_i.attachment',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'target': 'new',
            }
        else:
            raise ValidationError(_('There is no Data.'))