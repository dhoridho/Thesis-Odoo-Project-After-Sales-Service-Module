# -*- coding: utf-8 -*-
import calendar
import base64
import math
from odoo import api, fields, models, _
from datetime import datetime
import time
from odoo.exceptions import ValidationError
import xlwt
import base64
from io import BytesIO

class HreportBpjsKesehatan(models.TransientModel):
    _name = 'hr.report.bpjs.kesehatan'

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

    year = fields.Selection(selection=lambda self: self._compute_year_selection(), string="Year", default="none",
                            required=True)
    month = fields.Selection(selection=lambda self: self._compute_month_selection(), string="Month", default="none",
                             required=True)
    employee_ids = fields.Many2many('hr.employee', string='Employees', required=True,domain=_employee_domain)

    def action_print_xls(self):
        if not self.employee_ids:
            raise ValidationError(_('Please select employee.'))

        datas = []
        for emp in self.employee_ids:
            month_datetime = datetime.strptime(self.month, "%B")
            month_selected = month_datetime.month
            last_day_month = calendar.monthrange(int(self.year), month_selected)[1]
            month_selected = str('{:02d}'.format(month_selected))
            selected_month_start_date = self.year + '-' + month_selected + '-' + str('01')
            selected_month_start_date = datetime.strptime(selected_month_start_date, "%Y-%m-%d").date()
            selected_month_end_date = self.year + '-' + month_selected + '-' + str(last_day_month)
            selected_month_end_date = datetime.strptime(selected_month_end_date, "%Y-%m-%d").date()

            if emp.bpjs_kesehatan_date:
                bpjs_kesehatan_date = datetime.strptime(str(emp.bpjs_kesehatan_date), "%Y-%m-%d").date()
                if selected_month_start_date >= bpjs_kesehatan_date.replace(day=1):
                    payslips = self.env['hr.payslip'].search([('employee_id', '=', emp.id), ('state', '=', 'done'),
                                                              ('payslip_report_date', '>=', selected_month_start_date),
                                                              ('payslip_report_date', '<=', selected_month_end_date),
                                                              ('payslip_pesangon', '=', False)])
                    gapok_pensiunan = 0
                    tunjangan_tetap = 0
                    iuran_perusahaan = 0
                    iuran_pegawai = 0
                    if payslips:
                        for payslip in payslips:
                            for line in payslip.line_ids:
                                if line.salary_rule_id.bpjs_kesehatan_report == "gapok_pensiunan":
                                    gapok_pensiunan += line.total
                                if line.salary_rule_id.bpjs_kesehatan_report == "tunjangan_tetap":
                                    tunjangan_tetap += line.total
                                if line.salary_rule_id.bpjs_kesehatan_report == "iuran_perusahaan":
                                    iuran_perusahaan += line.total
                                if line.salary_rule_id.bpjs_kesehatan_report == "iuran_pegawai":
                                    iuran_pegawai += line.total
                    total_gaji = gapok_pensiunan + tunjangan_tetap
                    bpjs_kesehatan_limit = float(self.env['ir.config_parameter'].sudo().get_param(
                        'equip3_hr_payroll_extend_id.bpjs_kesehatan_limit'))
                    if total_gaji >= bpjs_kesehatan_limit:
                        dasar_iuran = bpjs_kesehatan_limit
                    else:
                        dasar_iuran = total_gaji
                    total_iuran = iuran_perusahaan + iuran_pegawai
                    kelas_rawat = 1
                    datas.append({
                        'employee_name': emp.name,
                        'gapok_pensiunan': gapok_pensiunan,
                        'tunjangan_tetap': tunjangan_tetap,
                        'total_gaji': total_gaji,
                        'dasar_iuran': dasar_iuran,
                        'iuran_perusahaan': iuran_perusahaan,
                        'iuran_pegawai': iuran_pegawai,
                        'total_iuran': total_iuran,
                        'kelas_rawat': kelas_rawat
                    })
        if datas:
            file_name = 'Report BPJS Kesehatan-' + str(month_datetime.strftime("%b")) + str(self.year) + '.xls'
            workbook = xlwt.Workbook(encoding="UTF-8")
            format0 = xlwt.easyxf('font:height 300,bold True; align: horiz center')
            format1 = xlwt.easyxf('font:height 200,bold True,color white; pattern: pattern solid, fore_colour green; align: horiz center; borders: top_color black, bottom_color black, right_color black, left_color black, left thin, right thin, top thin, bottom thin;')
            format2 = xlwt.easyxf('font:height 200; align: horiz left; borders: top_color black, bottom_color black, right_color black, left_color black, left thin, right thin, top thin, bottom thin;')
            format3 = xlwt.easyxf('font:height 200; align: horiz right; borders: top_color black, bottom_color black, right_color black, left_color black, left thin, right thin, top thin, bottom thin;')
            format4 = xlwt.easyxf('font:height 200,bold True; align: horiz center; borders: top_color black, bottom_color black, right_color black, left_color black, left thin, right thin, top thin, bottom thin;')
            format5 = xlwt.easyxf('font:height 200,bold True; align: horiz right; borders: top_color black, bottom_color black, right_color black, left_color black, left thin, right thin, top thin, bottom thin;')
            format6 = xlwt.easyxf('font:height 200; align: horiz center; borders: top_color black, bottom_color black, right_color black, left_color black, left thin, right thin, top thin, bottom thin;')
            sheet = workbook.add_sheet('Report BPJS Kesehatan')
            sheet.col(1).width = int(25 * 230)
            sheet.col(2).width = int(25 * 200)
            sheet.col(3).width = int(25 * 200)
            sheet.col(4).width = int(25 * 230)
            sheet.col(5).width = int(25 * 230)
            sheet.col(6).width = int(25 * 200)
            sheet.col(7).width = int(25 * 200)
            sheet.col(8).width = int(25 * 200)
            sheet.col(9).width = int(25 * 200)
            sheet.write_merge(0, 0, 0, 9, 'Perhitungan Iuran BPJS', format0)
            sheet.write_merge(1, 3, 0, 0, 'NO', format1)
            sheet.write_merge(1, 1, 1, 5, 'Identitas Peserta', format1)
            sheet.write_merge(1, 2, 6, 8, 'Iuran BPJS Pegawai BUMN/BUMD/Swasta/Badan Lain', format1)
            sheet.write_merge(1, 3, 9, 9, 'Kelas Rawat', format1)
            sheet.write_merge(2, 3, 1, 1, 'Nama Lengkap', format1)
            sheet.write_merge(2, 2, 2, 5, 'Pegawai BUMN/BUMD/Swasta/Badan Lain', format1)
            sheet.write(3, 2, "Gapok/ Pensiunan", format1)
            sheet.write(3, 3, "Tunjangan Tetap", format1)
            sheet.write(3, 4, "Total Gaji", format1)
            sheet.write(3, 5, "Dasar Perhitungan Iuran", format1)
            sheet.write(3, 6, "Perusahaan (4%)", format1)
            sheet.write(3, 7, "Pegawai [1%]", format1)
            sheet.write(3, 8, "Total Iuran", format1)
            sheet.write(4, 0, "1", format1)
            sheet.write(4, 1, "2", format1)
            sheet.write(4, 2, "3", format1)
            sheet.write(4, 3, "4", format1)
            sheet.write(4, 4, "5 = 3+4", format1)
            sheet.write(4, 5, "6", format1)
            sheet.write(4, 6, "7 = 6*4%", format1)
            sheet.write(4, 7, "8 = 6*1%", format1)
            sheet.write(4, 8, "9 = 7+8", format1)
            sheet.write(4, 9, "10", format1)

            counter = 1
            row = 5
            jumlah_iuran_perusahaan = 0
            jumlah_iuran_pegawai = 0
            jumlah_total_iuran = 0

            for line in datas:
                sheet.write(row, 0, counter, format2)
                sheet.write(row, 1, line.get('employee_name'), format2)
                sheet.write(row, 2, "{:0,.2f}".format(line.get('gapok_pensiunan')), format3)
                sheet.write(row, 3, "{:0,.2f}".format(line.get('tunjangan_tetap')), format3)
                sheet.write(row, 4, "{:0,.2f}".format(line.get('total_gaji')), format3)
                sheet.write(row, 5, "{:0,.2f}".format(line.get('dasar_iuran')), format3)
                sheet.write(row, 6, "{:0,.2f}".format(line.get('iuran_perusahaan')), format3)
                sheet.write(row, 7, "{:0,.2f}".format(line.get('iuran_pegawai')), format3)
                sheet.write(row, 8, "{:0,.2f}".format(line.get('total_iuran')), format3)
                sheet.write(row, 9, int(line.get('kelas_rawat')), format6)
                row += 1
                counter += 1

                jumlah_iuran_perusahaan += line.get('iuran_perusahaan')
                jumlah_iuran_pegawai += line.get('iuran_pegawai')
                jumlah_total_iuran += line.get('total_iuran')

            sheet.write_merge(row, row, 0, 5, "Jumlah Seluruhnya", format4)
            sheet.write(row, 6, "{:0,.2f}".format(jumlah_iuran_perusahaan), format5)
            sheet.write(row, 7, "{:0,.2f}".format(jumlah_iuran_pegawai), format5)
            sheet.write(row, 8, "{:0,.2f}".format(jumlah_total_iuran), format5)
            sheet.write(row, 9, "", format5)

            fp = BytesIO()
            workbook.save(fp)
            export_id = self.env['hr.report.bpjs.kesehatan.excel'].create(
                {'excel_file': base64.encodebytes(fp.getvalue()), 'file_name': file_name})
            fp.close()
            return {
                'view_mode': 'form',
                'res_id': export_id.id,
                'name': 'BPJS Kesehatan Report',
                'res_model': 'hr.report.bpjs.kesehatan.excel',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'target': 'new',
            }
        else:
            raise ValidationError(_('There is no Data.'))
