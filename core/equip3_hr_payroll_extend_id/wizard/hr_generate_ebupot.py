# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
import xlwt
import base64
from io import BytesIO

class HrGenerateEbupotExcel(models.TransientModel):
    _name = "hr.generate.ebupot.excel"
    _description = "Generate e-Bupot Excel"

    excel_file = fields.Binary('Excel Report')
    file_name = fields.Char('Excel File')

class HrGenerateEbupot(models.TransientModel):
    _name = 'hr.generate.ebupot'
    _description = 'Generate e-Bupot'
	
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                    default=lambda self: self.env.company)
    ebupot_type = fields.Selection([('pph21','PPH21'),('pph26','PPH26')],
                                default='pph21', string='e-Bupot Type', required=True)
    year_id = fields.Many2one('hr.payslip.period', string='Year', domain="[('state','=','open')]", required=True)
    month_id = fields.Many2one('hr.payslip.period.line', string="Month", domain="[('period_id','=',year_id)]", required=True)
    ebupot_signer_id = fields.Many2one('hr.employee', string="e-Bupot's Signer", required=True)
    tax_withholding_date = fields.Date('Tax Withholding Date', default=fields.Date.today(), required=True)
    employee_ids = fields.Many2many('hr.employee', string='Employees', required=True)
     
    @api.onchange('employee_ids','year_id','month_id','company_id','ebupot_type')
    def _onchange_employee_ids(self):
        employees = []
        emp_payslip = []
        if self.year_id and self.month_id and self.company_id and self.ebupot_type:
            payslips = self.env['hr.payslip'].search([('state', '=', 'done'),
                                                      ('payslip_period_id', '=', self.year_id.id),
                                                      ('month', '=', self.month_id.id),
                                                      ('company_id', '=', self.company_id.id),
                                                      ('payslip_pesangon', '=', False),
                                                      
                                                      ])
            if payslips:
                for slip in payslips:
                    emp_payslip.append(slip.employee_id.id)
                    
            if self.ebupot_type == "pph21":
                for emp in self.env['hr.employee'].search([]).filtered(lambda x: not x.is_expatriate and x.company_id.id == self.env.company.id):
                    if emp.id in emp_payslip:
                        employees.append(emp.id)
            elif self.ebupot_type == "pph26":
                for emp in self.env['hr.employee'].search([]).filtered(lambda x: x.is_expatriate and x.company_id.id == self.env.company_id.id):
                    if emp.id in emp_payslip:
                        employees.append(emp.id)
        return {
            'domain': {'employee_ids': [('id', 'in', employees)]},
        }
	
    def action_generate(self):
        if not self.employee_ids:
            raise ValidationError(_('Please select employees!'))
        
        month_datetime = datetime.strptime(self.month_id.month, "%B")
        month_selected = month_datetime.month
        
        if self.ebupot_signer_id.have_npwp == "yes":
            penandatangan_menggunakan = "NPWP"
            npwp_penandatangan = str(self.ebupot_signer_id.npwp_no).replace('-', '').replace('.', '') if self.ebupot_signer_id.npwp_no else ''
            nik_penandatangan = ""
            filename = str(self.ebupot_signer_id.npwp_no).replace('-', '').replace('.', '') if self.ebupot_signer_id.npwp_no else ''
        else:
            penandatangan_menggunakan = "NIK"
            npwp_penandatangan = ""
            nik_penandatangan = str(self.ebupot_signer_id.identification_id).replace('-', '').replace('.', '') if self.ebupot_signer_id.identification_id else ''
            filename = str(self.ebupot_signer_id.identification_id).replace('-', '').replace('.', '') if self.ebupot_signer_id.identification_id else ''

        file_name = filename + '.xls'
        workbook = xlwt.Workbook(encoding="UTF-8")
        sheet_rekap = workbook.add_sheet('Rekap')
        for i_rekap in range(1, 6):
            sheet_rekap.col(i_rekap).width = int(25 * 150)
        sheet_pph21 = workbook.add_sheet('21')
        for i_pph21 in range(1, 19):
            sheet_pph21.col(i_pph21).width = int(25 * 210)
        sheet_pph26 = workbook.add_sheet('26')
        for i_pph26 in range(1, 14):
            sheet_pph26.col(i_pph26).width = int(25 * 210)
        
        cell_gray = xlwt.easyxf('font:height 300,bold True,color black; pattern: pattern solid, fore_colour gray25; align: horiz center; borders: top_color black, bottom_color black, right_color black, left_color black, left thick, right thick, top thick, bottom thick;')
        cell_gray2 = xlwt.easyxf('font:height 230,bold True,color black; pattern: pattern solid, fore_colour gray25; align: horiz center; borders: top_color black, bottom_color black, right_color black, left_color black, left thick, right thick, top thick, bottom thick;')
        cell_white = xlwt.easyxf('font:height 300,bold True,color black; pattern: pattern solid, fore_colour white; align: horiz center; borders: top_color black, bottom_color black, right_color black, left_color black, left thick, right thick, top thick, bottom thick;')
        top_green = xlwt.easyxf('pattern: pattern solid, fore_colour light_green')
        top_yellow = xlwt.easyxf('pattern: pattern solid, fore_colour yellow')
        header = xlwt.easyxf('font:height 210,bold True,color black; pattern: pattern solid, fore_colour ivory; align: horiz center, wrap True; borders: top_color black, bottom_color black, top thick, bottom thick;')
        header_yellow = xlwt.easyxf('font:height 210,bold True,color black; pattern: pattern solid, fore_colour yellow; align: horiz center, wrap True; borders: top_color black, bottom_color black, top thick, bottom thick;')
        header_blue = xlwt.easyxf('font:height 210,bold True,color black; pattern: pattern solid, fore_colour light_blue; align: horiz center, wrap True; borders: top_color black, bottom_color black, top thick, bottom thick;')
        formatdate = xlwt.easyxf('font:height 210; align: horiz left;', num_format_str='dd/MM/yyyy')
        
        jml_pph21 = 0
        jml_pph26 = 0
        datas_pph21 = []
        datas_pph26 = []
        if self.ebupot_type == "pph21":
            number = 1
            for emp in self.employee_ids.filtered(lambda x: not x.is_expatriate):
                if emp.have_npwp == "yes":
                    penerima_penghasilan = "NPWP"
                    npwp = str(emp.npwp_no).replace('-', '').replace('.', '') if emp.npwp_no else ''
                    nik = ""
                else:
                    penerima_penghasilan = "NIK"
                    npwp = ""
                    nik = str(emp.identification_id).replace('-', '').replace('.', '') if emp.identification_id else ''

                alamat_penerima_full = ""
                if emp.address_ids:
                    alamat_penerima = emp.address_ids.sorted(key=lambda x: x.id, reverse=False)[0]
                    if alamat_penerima:
                        if alamat_penerima.street:
                            alamat_penerima_full += alamat_penerima.street + " - "
                        if alamat_penerima.location:
                            alamat_penerima_full += alamat_penerima.location + " - "
                        if alamat_penerima.country_id:
                            alamat_penerima_full += alamat_penerima.country_id.name + " - "
                        if alamat_penerima.state_id:
                            alamat_penerima_full += alamat_penerima.state_id.name + " - "
                        if alamat_penerima.postal_code:
                            alamat_penerima_full += alamat_penerima.postal_code + " - "
                        if alamat_penerima.tel_number:
                            alamat_penerima_full += alamat_penerima.tel_number

                if emp.employee_tax_status == "pegawai_tetap":
                    kode_objek_pajak = "21-100-01"
                    pegawai_harian = "Tidak"
                elif emp.employee_tax_status == "pegawai_tidak_tetap":
                    kode_objek_pajak = "21-100-03"
                    pegawai_harian = "Ya"
                else:
                    kode_objek_pajak = ""
                    pegawai_harian = ""
                
                kode_ptkp = emp.ptkp_id.ptkp_name if emp.ptkp_id else ""

                payslip = self.env['hr.payslip'].search([('employee_id', '=', emp.id),('state', '=', 'done'),
                                                          ('payslip_period_id', '=', self.year_id.id),
                                                          ('month', '=', self.month_id.id),
                                                          ('payslip_pesangon', '=', False)], limit=1)
                
                previous_month_date = datetime.strptime(str(payslip.payslip_report_date), '%Y-%m-%d') - relativedelta(months=1)
                previous_month = previous_month_date.strftime("%B")
                self.env.cr.execute(
                    ''' select tax_period_length, tax_end_month, ter_bruto, ter_bruto_gross from hr_payslip WHERE employee_id = %s and month_name = '%s' AND year = '%s' and state not in ('draft','refund','cancel') ORDER BY id DESC LIMIT 1 ''' % (
                        emp.id, previous_month, self.month_id.year))
                previous_payslip = self.env.cr.dictfetchall()
                if previous_payslip:
                    if previous_payslip[0].get('tax_period_length') != previous_payslip[0].get('tax_end_month'):
                        previous_payslip_ter_bruto = previous_payslip[0].get('ter_bruto') if previous_payslip[0].get('ter_bruto') else 0
                        previous_payslip_ter_bruto_gross = previous_payslip[0].get('ter_bruto_gross') if previous_payslip[0].get('ter_bruto_gross') else 0
                    else:
                        previous_payslip_ter_bruto = 0
                        previous_payslip_ter_bruto_gross = 0
                else:
                    previous_payslip_ter_bruto = 0
                    previous_payslip_ter_bruto_gross = 0

                bruto = 0
                if emp.tax_calculation_method == "gross_up":
                    menggunakan_gross_up = "Ya"
                    if previous_payslip:
                        bruto = payslip.ter_bruto - previous_payslip_ter_bruto
                    else:
                        bruto = payslip.ter_bruto
                else:
                    menggunakan_gross_up = "Tidak"
                    if previous_payslip:
                        bruto = payslip.ter_bruto_gross - previous_payslip_ter_bruto_gross
                    else:
                        bruto = payslip.ter_bruto_gross
                
                datas_pph21.append({
                    'number': number,
                    'tanggal_pemotongan': self.tax_withholding_date,
                    'penerima_penghasilan': penerima_penghasilan,
                    'npwp': npwp,
                    'nik': nik,
                    'nama_penerima': emp.name,
                    'alamat_penerima': alamat_penerima_full,
                    'kode_objek_pajak': kode_objek_pajak,
                    'penandatangan_menggunakan': penandatangan_menggunakan,
                    'npwp_penandatangan': npwp_penandatangan,
                    'nik_penandatangan': nik_penandatangan,
                    'kode_ptkp': kode_ptkp,
                    'pegawai_harian': pegawai_harian,
                    'menggunakan_gross_up': menggunakan_gross_up,
                    'bruto': bruto,
                })
                number += 1
                jml_pph21 += 1
        elif self.ebupot_type == "pph26":
            number = 1
            for emp in self.employee_ids.filtered(lambda x: x.is_expatriate):
                tin = ""
                alamat_penerima_full = ""
                if emp.address_ids:
                    alamat_penerima = emp.address_ids.sorted(key=lambda x: x.id, reverse=False)[0]
                    if alamat_penerima:
                        if alamat_penerima.street:
                            alamat_penerima_full += alamat_penerima.street + " - "
                        if alamat_penerima.location:
                            alamat_penerima_full += alamat_penerima.location + " - "
                        if alamat_penerima.country_id:
                            alamat_penerima_full += alamat_penerima.country_id.name + " - "
                        if alamat_penerima.state_id:
                            alamat_penerima_full += alamat_penerima.state_id.name + " - "
                        if alamat_penerima.postal_code:
                            alamat_penerima_full += alamat_penerima.postal_code + " - "
                        if alamat_penerima.tel_number:
                            alamat_penerima_full += alamat_penerima.tel_number
                paspor_penerima = str(emp.passport_id).replace('-', '').replace('.', '') if emp.passport_id else ''
                if emp.country_domicile_code:
                    kode_negara = emp.country_domicile_code.name
                else:
                    kode_negara = ""

                payslip = self.env['hr.payslip'].search([('employee_id', '=', emp.id),('state', '=', 'done'),
                                                          ('payslip_period_id', '=', self.year_id.id),
                                                          ('month', '=', self.month_id.id),
                                                          ('payslip_pesangon', '=', False)], limit=1)
                
                previous_month_date = datetime.strptime(str(payslip.payslip_report_date), '%Y-%m-%d') - relativedelta(months=1)
                previous_month = previous_month_date.strftime("%B")
                self.env.cr.execute(
                    ''' select tax_period_length, tax_end_month, ter_bruto, ter_bruto_gross from hr_payslip WHERE employee_id = %s and month_name = '%s' AND year = '%s' and state not in ('draft','refund','cancel') ORDER BY id DESC LIMIT 1 ''' % (
                        emp.id, previous_month, self.month_id.year))
                previous_payslip = self.env.cr.dictfetchall()

                if previous_payslip:
                    if previous_payslip[0].get('tax_period_length') != previous_payslip[0].get('tax_end_month'):
                        previous_payslip_ter_bruto = previous_payslip[0].get('ter_bruto') if previous_payslip[0].get('ter_bruto') else 0
                        previous_payslip_ter_bruto_gross = previous_payslip[0].get('ter_bruto_gross') if previous_payslip[0].get('ter_bruto_gross') else 0
                    else:
                        previous_payslip_ter_bruto = 0
                        previous_payslip_ter_bruto_gross = 0
                else:
                    previous_payslip_ter_bruto = 0
                    previous_payslip_ter_bruto_gross = 0

                bruto = 0
                if emp.tax_calculation_method == "gross_up":
                    if previous_payslip:
                        bruto = payslip.ter_bruto - previous_payslip_ter_bruto
                    else:
                        bruto = payslip.ter_bruto
                else:
                    if previous_payslip:
                        bruto = payslip.ter_bruto_gross - previous_payslip_ter_bruto_gross
                    else:
                        bruto = payslip.ter_bruto_gross
                
                datas_pph26.append({
                    'number': number,
                    'tanggal_pemotongan': self.tax_withholding_date,
                    'tin': tin,
                    'nama_penerima': emp.name,
                    'alamat_penerima': alamat_penerima_full,
                    'paspor_penerima': paspor_penerima,
                    'kode_negara': kode_negara,
                    'penandatangan_menggunakan': penandatangan_menggunakan,
                    'npwp_penandatangan': npwp_penandatangan,
                    'nik_penandatangan': nik_penandatangan,
                    'bruto': bruto,
                })
                number += 1
                jml_pph26 += 1

        sheet_rekap.write_merge(1, 1, 1, 2, "Tahun Pajak", cell_gray)
        sheet_rekap.write(1, 3, self.month_id.year, cell_white)
        sheet_rekap.write_merge(1, 1, 4, 5, "Masa Pajak", cell_gray)
        sheet_rekap.write(1, 6, month_selected, cell_white)
        sheet_rekap.write_merge(2, 2, 1, 5, "Jumlah Bukti Potong PPh Pasal 21", cell_gray2)
        sheet_rekap.write(2, 6, jml_pph21, cell_white)
        sheet_rekap.write_merge(3, 3, 1, 5, "Jumlah Bukti Potong PPh Pasal 26", cell_gray2)
        sheet_rekap.write(3, 6, jml_pph26, cell_white)

        for col_pph21 in range(0, 15):
            sheet_pph21.write(0, col_pph21, "", top_green)
        for col_pph21 in range(15, 19):
            sheet_pph21.write(0, col_pph21, "", top_yellow)
        sheet_pph21.write(1, 0, "No", header)
        sheet_pph21.write(1, 1, "Tgl Pemotongan (dd/MM/yyyy)", header)
        sheet_pph21.write(1, 2, "Penerima Penghasilan? (NPWP/NIK)", header)
        sheet_pph21.write(1, 3, "NPWP (tanpa format/tanda baca)", header)
        sheet_pph21.write(1, 4, "NIK (tanpa format/tanda baca)", header)
        sheet_pph21.write(1, 5, "Nama Penerima Penghasilan Sesuai NIK", header)
        sheet_pph21.write(1, 6, "Alamat Penerima Penghasilan Sesuai NIK", header)
        sheet_pph21.write(1, 7, "Kode Objek Pajak", header)
        sheet_pph21.write(1, 8, "Penandatangan Menggunakan? (NPWP/NIK)", header)
        sheet_pph21.write(1, 9, "NPWP Penandatangan (tanpa format/tanda baca)", header)
        sheet_pph21.write(1, 10, "NIK Penandatangan (tanpa format/tanda baca)", header)
        sheet_pph21.write(1, 11, "Kode PTKP", header)
        sheet_pph21.write(1, 12, "Pegawai Harian? (Ya/Tidak)", header)
        sheet_pph21.write(1, 13, "Menggunakan Gross Up? (Ya/Tidak)", header)
        sheet_pph21.write(1, 14, "Penghasilan Bruto", header)
        sheet_pph21.write(1, 15, "Terdapat Akumulasi Penghasilan Bruto Sebelumnya? (Ya/Tidak)", header_yellow)
        sheet_pph21.write(1, 16, "Akumulasi Penghasilan Bruto Sebelumnya", header_yellow)
        sheet_pph21.write(1, 17, "Mendapatkan Fasilitas ? (N/SKB/DTP)", header_yellow)
        sheet_pph21.write(1, 18, "Nomor SKB/Nomor DTP", header_yellow)
        if datas_pph21:
            row_pph21 = 2
            for line in datas_pph21:
                sheet_pph21.write(row_pph21, 0, line.get('number'))
                sheet_pph21.write(row_pph21, 1, line.get('tanggal_pemotongan'), formatdate)
                sheet_pph21.write(row_pph21, 2, line.get('penerima_penghasilan'))
                sheet_pph21.write(row_pph21, 3, line.get('npwp'))
                sheet_pph21.write(row_pph21, 4, line.get('nik'))
                sheet_pph21.write(row_pph21, 5, line.get('nama_penerima'))
                sheet_pph21.write(row_pph21, 6, line.get('alamat_penerima'))
                sheet_pph21.write(row_pph21, 7, line.get('kode_objek_pajak'))
                sheet_pph21.write(row_pph21, 8, line.get('penandatangan_menggunakan'))
                sheet_pph21.write(row_pph21, 9, line.get('npwp_penandatangan'))
                sheet_pph21.write(row_pph21, 10, line.get('nik_penandatangan'))
                sheet_pph21.write(row_pph21, 11, line.get('kode_ptkp'))
                sheet_pph21.write(row_pph21, 12, line.get('pegawai_harian'))
                sheet_pph21.write(row_pph21, 13, line.get('menggunakan_gross_up'))
                sheet_pph21.write(row_pph21, 14, line.get('bruto'))
                row_pph21 += 1

        for col_pph26 in range(0, 14):
            sheet_pph26.write(0, col_pph26, "", top_green)
        sheet_pph26.write(1, 0, "No", header)
        sheet_pph26.write(1, 1, "Tgl Pemotongan (dd/MM/yyyy)", header)
        sheet_pph26.write(1, 2, "TIN (dengan format/tanda baca)", header)
        sheet_pph26.write(1, 3, "Nama Penerima Penghasilan", header)
        sheet_pph26.write(1, 4, "Alamat Penerima Penghasilan", header)
        sheet_pph26.write(1, 5, "No Paspor Penerima Penghasilan", header)
        sheet_pph26.write(1, 6, "Kode Negara", header)
        sheet_pph26.write(1, 7, "Penandatangan Menggunakan? (NPWP/NIK)", header)
        sheet_pph26.write(1, 8, "NPWP Penandatangan (tanpa format/tanda baca)", header)
        sheet_pph26.write(1, 9, "NIK Penandatangan (tanpa format/tanda baca)", header)
        sheet_pph26.write(1, 10, "Penghasilan Bruto", header)
        sheet_pph26.write(1, 11, "Mendapatkan Fasilitas ? (N/SKD)", header)
        sheet_pph26.write(1, 12, "Nomor Tanda Terima SKD", header_blue)
        sheet_pph26.write(1, 13, "Tarif SKD", header_blue)
        if datas_pph26:
            row_pph26 = 2
            for line in datas_pph26:
                sheet_pph26.write(row_pph26, 0, line.get('number'))
                sheet_pph26.write(row_pph26, 1, line.get('tanggal_pemotongan'), formatdate)
                sheet_pph26.write(row_pph26, 2, line.get('tin'))
                sheet_pph26.write(row_pph26, 3, line.get('nama_penerima'))
                sheet_pph26.write(row_pph26, 4, line.get('alamat_penerima'))
                sheet_pph26.write(row_pph26, 5, line.get('paspor_penerima'))
                sheet_pph26.write(row_pph26, 6, line.get('kode_negara'))
                sheet_pph26.write(row_pph26, 7, line.get('penandatangan_menggunakan'))
                sheet_pph26.write(row_pph26, 8, line.get('npwp_penandatangan'))
                sheet_pph26.write(row_pph26, 9, line.get('nik_penandatangan'))
                sheet_pph26.write(row_pph26, 10, line.get('bruto'))
                row_pph26 += 1

        fp = BytesIO()
        workbook.save(fp)
        ebupot_exist = self.env['hr.ebupot'].search([('company_id', '=', self.company_id.id),('year_id', '=', self.year_id.id),('month_id', '=', self.month_id.id),('ebupot_type','=', self.ebupot_type)], limit=1)
        if not ebupot_exist:
            self.env["hr.ebupot"].create({
                'company_id': self.company_id.id,
                'year_id': self.year_id.id,
                'month_id': self.month_id.id,
                'ebupot_type': self.ebupot_type,
                'attachment': base64.encodebytes(fp.getvalue()),
                'attachment_fname': file_name,
            })
        else:
            ebupot_exist.write({
                'attachment': base64.encodebytes(fp.getvalue()),
                'attachment_fname': file_name,
            })
        export_id = self.env['hr.generate.ebupot.excel'].create(
            {'excel_file': base64.encodebytes(fp.getvalue()), 'file_name': file_name})
        fp.close()
        return {
            'view_mode': 'form',
            'res_id': export_id.id,
            'name': 'Generate e-Bupot',
            'res_model': 'hr.generate.ebupot.excel',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }