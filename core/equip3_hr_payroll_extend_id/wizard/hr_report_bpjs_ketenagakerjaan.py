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

class HreportBpjsKetenagakerjaan(models.TransientModel):
    _name = 'hr.report.bpjs.ketenagakerjaan'

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
        npp = self.env.company.company_registry or ''
        company_name = self.env.company.name
        company_city = self.env.company.city or ''
        company_work_unit = self.env.company.work_unit

        today = datetime.today().date()
        month_datetime = datetime.strptime(self.month, "%B")
        month_selected_number = month_datetime.month
        last_day_month = calendar.monthrange(int(self.year), month_selected_number)[1]
        month_selected = str('{:02d}'.format(month_selected_number))
        selected_month_start_date = self.year + '-' + month_selected + '-' + str('01')
        selected_month_start_date = datetime.strptime(selected_month_start_date, "%Y-%m-%d").date()
        selected_month_end_date = self.year + '-' + month_selected + '-' + str(last_day_month)
        selected_month_end_date = datetime.strptime(selected_month_end_date, "%Y-%m-%d").date()

        for emp in self.employee_ids:

            if emp.bpjs_ketenagakerjaan_date:
                bpjs_ketenagakerjaan_date = datetime.strptime(str(emp.bpjs_ketenagakerjaan_date), "%Y-%m-%d").date()
                if selected_month_start_date >= bpjs_ketenagakerjaan_date.replace(day=1):
                    payslips = self.env['hr.payslip'].search([('employee_id', '=', emp.id), ('state', '=', 'done'),
                                                              ('payslip_report_date', '>=', selected_month_start_date),
                                                              ('payslip_report_date', '<=', selected_month_end_date),
                                                              ('payslip_pesangon', '=', False)])
                    upah = 0
                    rapel = 0
                    iuran_jkk = 0
                    iuran_jkm = 0
                    iuran_jht_pemberi_kerja = 0
                    iuran_jht_pekerja = 0
                    iuran_jp_pemberi_kerja = 0
                    iuran_jp_pekerja = 0
                    if payslips:
                        for payslip in payslips:
                            for line in payslip.line_ids:
                                if line.salary_rule_id.bpjs_ketenagakerjaan_report == "upah":
                                    upah += line.total
                                if line.salary_rule_id.bpjs_ketenagakerjaan_report == "rapel":
                                    rapel += line.total
                                if line.salary_rule_id.bpjs_ketenagakerjaan_report == "iuran_jkk":
                                    iuran_jkk += line.total
                                if line.salary_rule_id.bpjs_ketenagakerjaan_report == "iuran_jkm":
                                    iuran_jkm += line.total
                                if line.salary_rule_id.bpjs_ketenagakerjaan_report == "iuran_jht_pemberi_kerja":
                                    iuran_jht_pemberi_kerja += line.total
                                if line.salary_rule_id.bpjs_ketenagakerjaan_report == "iuran_jht_pekerja":
                                    iuran_jht_pekerja += line.total
                                if line.salary_rule_id.bpjs_ketenagakerjaan_report == "iuran_jp_pemberi_kerja":
                                    iuran_jp_pemberi_kerja += line.total
                                if line.salary_rule_id.bpjs_ketenagakerjaan_report == "iuran_jp_pekerja":
                                    iuran_jp_pekerja += line.total

                    total = upah + rapel
                    jumlah_iuran = iuran_jkk + iuran_jkm + iuran_jht_pemberi_kerja + iuran_jht_pekerja + iuran_jp_pemberi_kerja + iuran_jp_pekerja
                    datas.append({
                        'nomor_peserta': emp.bpjs_ketenagakerjaan_no,
                        'employee_identification_id': emp.identification_id or emp.passport_id or '',
                        'nama_pekerja': emp.name,
                        'tanggal_lahir': emp.birthday,
                        'upah': upah,
                        'rapel': rapel,
                        'total': total,
                        'iuran_jkk': iuran_jkk,
                        'iuran_jkm': iuran_jkm,
                        'iuran_jht_pemberi_kerja': iuran_jht_pemberi_kerja,
                        'iuran_jht_pekerja': iuran_jht_pekerja,
                        'iuran_jp_pemberi_kerja': iuran_jp_pemberi_kerja,
                        'iuran_jp_pekerja': iuran_jp_pekerja,
                        'jumlah_iuran': jumlah_iuran
                    })
        if datas:
            file_name = 'Report BPJS Ketenagakerjaan-' + str(month_datetime.strftime("%b")) + str(self.year) + '.xls'
            workbook = xlwt.Workbook(encoding="UTF-8")
            format0 = xlwt.easyxf('font:height 300,bold True; align: horiz center;')
            format1 = xlwt.easyxf('font:height 250,bold True; align: horiz center, vert center; alignment: wrap True; borders: top_color black, bottom_color black, right_color black, left_color black, left thin, right thin, top thin, bottom thin;')
            format2 = xlwt.easyxf('font:height 200; align: horiz left;')
            format3 = xlwt.easyxf('font:height 200,bold True; align: horiz left; borders: bottom_color black, right_color black, left_color black, left thin, right thin, bottom thin;')
            format4 = xlwt.easyxf('font:height 200; align: horiz center; borders: bottom_color black, right_color black, left_color black, left thin, right thin, bottom thin;')
            format5 = xlwt.easyxf('font:height 150; align: horiz left;')
            format6 = xlwt.easyxf('font:height 180,bold True,color white; pattern: pattern solid, fore_colour green; align: horiz center; borders: top_color black, bottom_color black, right_color black, left_color black, left thin, right thin, top thin, bottom thin;')
            format6a = xlwt.easyxf('font:height 200,bold True,color white; pattern: pattern solid, fore_colour green; align: horiz left; borders: top_color black, bottom_color black, right_color black, left_color black, left thin, right thin, top thin, bottom thin;')
            format6b = xlwt.easyxf('font:height 180,bold True,color white; pattern: pattern solid, fore_colour green; align: horiz center; alignment: wrap True; borders: top_color black, bottom_color black, right_color black, left_color black, left thin, right thin, top thin, bottom thin;')
            format7 = xlwt.easyxf('font:height 200; align: horiz left; borders: top_color black, bottom_color black, right_color black, left_color black, left thin, right thin, top thin, bottom thin;')
            format8 = xlwt.easyxf('font:height 200; align: horiz right; borders: top_color black, bottom_color black, right_color black, left_color black, left thin, right thin, top thin, bottom thin;')
            format9 = xlwt.easyxf('font:height 175; align: horiz left; borders: bottom_color black, bottom thin;')
            format11 = xlwt.easyxf('font:height 200; align: horiz center; borders: top_color black, bottom_color black, right_color black, left_color black, left thin, right thin, top thin, bottom thin;')
            formatdate1 = xlwt.easyxf('font:height 200; align: horiz left; borders: top_color black, bottom_color black, right_color black, left_color black, left thin, right thin, top thin, bottom thin;', num_format_str='dd mmm yyyy')
            formatdate2 = xlwt.easyxf('font:height 200; align: horiz left; borders: bottom_color black, bottom thin;', num_format_str='dd mmm yyyy')
            sheet = workbook.add_sheet('BPJS Ketenagakerjaan Report')
            for i in range(0, 98):
                sheet.col(i).width = int(256 * 3)
            sheet.write_merge(1, 4, 24, 76, 'LAPORAN RINCIAN IURAN PEKERJA', format0)
            sheet.write_merge(1, 4, 87, 95, 'Formulir 2\nBPJS Ketenagakerjaaan', format1)
            sheet.write_merge(7, 7, 1, 8, 'NPP', format2)
            sheet.write_merge(7, 7, 12, 60, 'Nama Pemberi Kerja/Wadah/Mitra', format2)
            sheet.write_merge(7, 7, 62, 82, 'Nama Unit Kerja / Kesatuan', format2)
            sheet.write_merge(7, 7, 88, 94, 'Periode Laporan', format2)
            sheet.write_merge(8, 8, 1, 8, npp, format3)
            sheet.write_merge(8, 8, 12, 60, company_name, format3)
            sheet.write_merge(8, 8, 62, 82, company_work_unit, format3)
            sheet.write_merge(8, 8, 88, 89, month_selected_number, format4)
            sheet.write_merge(8, 8, 91, 94, self.year, format4)
            sheet.write_merge(9, 9, 88, 89, 'bulan', format5)
            sheet.write_merge(9, 9, 91, 94, 'tahun', format5)
            sheet.write_merge(11, 12, 0, 1, 'No', format6)
            sheet.write_merge(11, 12, 2, 7, 'Nomor Peserta', format6)
            sheet.write_merge(11, 12, 8, 16, 'Nomor Induk Kependudukan\n(NIK)/Paspor (bagi TK Asing)', format6b)
            sheet.write_merge(11, 12, 17, 31, 'Nama Pekerja', format6)
            sheet.write_merge(11, 12, 32, 37, 'Tanggal Lahir', format6)
            sheet.write_merge(11, 12, 38, 43, 'Upah\n(Rp)', format6b)
            sheet.write_merge(11, 12, 44, 49, 'Rapel\n(Rp)', format6b)
            sheet.write_merge(11, 12, 50, 55, 'Total\n(Upah + Rapel)\n(Rp)', format6b)
            sheet.write_merge(11, 12, 56, 61, 'Iuran JKK (Rp)\n(.....%)**', format6b)
            sheet.write_merge(11, 12, 62, 67, 'Iuran JKM (Rp)\n(0.3%)', format6b)
            sheet.write_merge(11, 11, 68, 79, 'Iuran JHT (Rp)', format6)
            sheet.write_merge(12, 12, 68, 73, 'Pemberi Kerja (3.7%)', format6)
            sheet.write_merge(12, 12, 74, 79, 'Pekerja (2%)', format6)
            sheet.write_merge(11, 11, 80, 91, 'Iuran JP (Rp)', format6)
            sheet.write_merge(12, 12, 80, 85, 'Pemberi Kerja (2%)', format6)
            sheet.write_merge(12, 12, 86, 91, 'Pekerja (1%)', format6)
            sheet.write_merge(11, 12, 92, 97, 'Jumlah Iuran (Rp)', format6)
            sheet.write_merge(13, 13, 0, 1, 'a', format11)
            sheet.write_merge(13, 13, 2, 7, 'b', format11)
            sheet.write_merge(13, 13, 8, 16, 'c', format11)
            sheet.write_merge(13, 13, 17, 31, 'd', format11)
            sheet.write_merge(13, 13, 32, 37, 'e', format11)
            sheet.write_merge(13, 13, 38, 43, 'f', format11)
            sheet.write_merge(13, 13, 44, 49, 'g', format11)
            sheet.write_merge(13, 13, 50, 55, 'h = f + g', format11)
            sheet.write_merge(13, 13, 56, 61, 'i', format11)
            sheet.write_merge(13, 13, 62, 67, 'j', format11)
            sheet.write_merge(13, 13, 68, 73, 'k', format11)
            sheet.write_merge(13, 13, 74, 79, 'l', format11)
            sheet.write_merge(13, 13, 80, 85, 'm', format11)
            sheet.write_merge(13, 13, 86, 91, 'n', format11)
            sheet.write_merge(13, 13, 92, 97, 'o=i+j+k+l+m+n', format11)

            counter = 1
            row = 14
            jumlah_upah = 0
            jumlah_rapel = 0
            jumlah_total = 0
            jumlah_iuran_jkk = 0
            jumlah_iuran_jkm = 0
            jumlah_iuran_jht_pemberi_kerja = 0
            jumlah_iuran_jht_pekerja = 0
            jumlah_iuran_jp_pemberi_kerja = 0
            jumlah_iuran_jp_pekerja = 0
            total_jumlah_iuran = 0

            for line in datas:
                sheet.write_merge(row, row, 0, 1, counter, format11)
                sheet.write_merge(row, row, 2, 7, line.get('nomor_peserta'), format7)
                sheet.write_merge(row, row, 8, 16, line.get('employee_identification_id'), format7)
                sheet.write_merge(row, row, 17, 31, line.get('nama_pekerja'), format7)
                sheet.write_merge(row, row, 32, 37, line.get('tanggal_lahir'), formatdate1)
                sheet.write_merge(row, row, 38, 43, "{:0,.2f}".format(line.get('upah')), format8)
                sheet.write_merge(row, row, 44, 49, "{:0,.2f}".format(line.get('rapel')), format8)
                sheet.write_merge(row, row, 50, 55, "{:0,.2f}".format(line.get('total')), format8)
                sheet.write_merge(row, row, 56, 61, "{:0,.2f}".format(line.get('iuran_jkk')), format8)
                sheet.write_merge(row, row, 62, 67, "{:0,.2f}".format(line.get('iuran_jkm')), format8)
                sheet.write_merge(row, row, 68, 73, "{:0,.2f}".format(line.get('iuran_jht_pemberi_kerja')), format8)
                sheet.write_merge(row, row, 74, 79, "{:0,.2f}".format(line.get('iuran_jht_pekerja')), format8)
                sheet.write_merge(row, row, 80, 85, "{:0,.2f}".format(line.get('iuran_jp_pemberi_kerja')), format8)
                sheet.write_merge(row, row, 86, 91, "{:0,.2f}".format(line.get('iuran_jp_pekerja')), format8)
                sheet.write_merge(row, row, 92, 97, "{:0,.2f}".format(line.get('jumlah_iuran')), format8)
                row += 1
                counter += 1

                jumlah_upah += line.get('upah')
                jumlah_rapel += line.get('rapel')
                jumlah_total += line.get('total')
                jumlah_iuran_jkk += line.get('iuran_jkk')
                jumlah_iuran_jkm += line.get('iuran_jkm')
                jumlah_iuran_jht_pemberi_kerja += line.get('iuran_jht_pemberi_kerja')
                jumlah_iuran_jht_pekerja += line.get('iuran_jht_pekerja')
                jumlah_iuran_jp_pemberi_kerja += line.get('iuran_jp_pemberi_kerja')
                jumlah_iuran_jp_pekerja += line.get('iuran_jp_pekerja')
                total_jumlah_iuran += line.get('jumlah_iuran')

            sheet.write_merge(row, row, 0, 37, "Total Seluruhnya", format6)
            sheet.write_merge(row, row, 38, 43, "{:0,.2f}".format(jumlah_upah), format8)
            sheet.write_merge(row, row, 44, 49, "{:0,.2f}".format(jumlah_rapel), format8)
            sheet.write_merge(row, row, 50, 55, "{:0,.2f}".format(jumlah_total), format8)
            sheet.write_merge(row, row, 56, 61, "{:0,.2f}".format(jumlah_iuran_jkk), format8)
            sheet.write_merge(row, row, 62, 67, "{:0,.2f}".format(jumlah_iuran_jkm), format8)
            sheet.write_merge(row, row, 68, 73, "{:0,.2f}".format(jumlah_iuran_jht_pemberi_kerja), format8)
            sheet.write_merge(row, row, 74, 79, "{:0,.2f}".format(jumlah_iuran_jht_pekerja), format8)
            sheet.write_merge(row, row, 80, 85, "{:0,.2f}".format(jumlah_iuran_jp_pemberi_kerja), format8)
            sheet.write_merge(row, row, 86, 91, "{:0,.2f}".format(jumlah_iuran_jp_pekerja), format8)
            sheet.write_merge(row, row, 92, 97, "{:0,.2f}".format(total_jumlah_iuran), format8)
            row += 1
            sheet.write_merge(row, row, 32, 91, "Kompensasi Kekurangan atau Kelebihan Iuran untuk Bulan atau Tahun sebelumnya", format6a)
            sheet.write_merge(row, row, 92, 97, "", format8)
            row += 1
            sheet.write_merge(row, row, 32, 91, "Denda", format6a)
            sheet.write_merge(row, row, 92, 97, "", format8)
            row += 7
            sheet.write_merge(row, row, 1, 5, "Keterangan", format5)
            row += 1
            sheet.write_merge(row, row, 1, 2, "*)", format5)
            sheet.write_merge(row, row, 3, 75, "Isian formulir ini dapat disampaikan kepada BPJS Ketenagakerjaaan dalam bentuk media elektronik (softcopy) ataupun hasil cetakan dari sistem penggajian perusahaan peserta yang bersangkutan, dengan aturan / format yang sesuai dengan ketentuan BPJS Ketenagakerjaaan.", format5)
            row += 1
            sheet.write_merge(row, row, 3, 75, "Apabila jumlah pekerja melebihi kolom diatas, maka dapat dijadikan lampiran berikutnya.", format5)
            sheet.write_merge(row, row, 76, 84, company_city, format9)
            sheet.write_merge(row, row, 86, 90, today, formatdate2)
            row += 1
            sheet.write_merge(row, row, 1, 2, "**)", format5)
            sheet.write_merge(row, row, 3, 75, "Diisi sesuai dengan tingkat resiko lingkungan kerja.", format5)
            row += 1
            sheet.write_merge(row, row, 1, 75, "Tanda tangan tidak diwajibkan untuk pendaftaran secara elektronik/digital.", format5)
            row += 4
            sheet.write_merge(row, row, 76, 97, "(Nama dan Tanda Tangan Pimpinan/Penanggungjawab Badan Usaha/Instansi/Asosiasi/Mitra)", format5)
            row += 1
            sheet.write_merge(row, row, 76, 97, "Jabatan: ", format5)


            fp = BytesIO()
            workbook.save(fp)
            export_id = self.env['hr.report.bpjs.ketenagakerjaan.excel'].create(
                {'excel_file': base64.encodebytes(fp.getvalue()), 'file_name': file_name})
            fp.close()
            return {
                'view_mode': 'form',
                'res_id': export_id.id,
                'name': 'BPJS Ketenagakerjaan Report',
                'res_model': 'hr.report.bpjs.ketenagakerjaan.excel',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'target': 'new',
            }
        else:
            raise ValidationError(_('There is no Data.'))
