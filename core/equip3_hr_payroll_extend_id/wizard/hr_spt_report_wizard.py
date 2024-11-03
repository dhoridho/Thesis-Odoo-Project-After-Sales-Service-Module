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

class HrSptReport(models.TransientModel):
    _name = 'hr.spt.report'

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

    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
								 default=lambda self: self.env.company)
    year = fields.Selection(selection=lambda self: self._compute_year_selection(), string="Year", default="none",
                            required=True)
    month = fields.Selection(selection=lambda self: self._compute_month_selection(), string="Month", default="none",
                             required=True)
    spt_type = fields.Many2one('hr.spt.type', string="SPT Type", required=True)
    branch_id = fields.Many2one("res.branch", string="Branch", domain="[('company_id', '=', company_id)]")
    employee_ids = fields.Many2many('hr.employee', string='Employees', required=True)

    @api.onchange('spt_type','branch_id')
    def _onchange_spt_type(self):
        if self.spt_type and self.spt_type.code == "1721_A1":
            if self.branch_id:
                return {'domain': {'employee_ids': [('company_id','=',self.company_id.id),('employee_tax_category', '=', 'non_pns'),('branch_id','=',self.branch_id.id)]}}
            return {'domain': {'employee_ids': [('company_id','=',self.company_id.id),('employee_tax_category', '=', 'non_pns')]}}
        elif self.spt_type and self.spt_type.code == "1721_A2":
            if self.branch_id:
                return {'domain': {'employee_ids': [('company_id','=',self.company_id.id),('employee_tax_category', '=', 'pns'),('branch_id','=',self.branch_id.id)]}}
            return {'domain': {'employee_ids': [('company_id','=',self.company_id.id),('employee_tax_category', '=', 'pns')]}}
        else:
            return {'domain': {'employee_ids': [('id', '=', -1),('company_id','=',self.company_id.id)]}}

    def round_down(self, n, decimals=0):
        multiplier = 10 ** decimals
        return math.floor(n * multiplier) / multiplier

    def action_print_excel(self):
        if not self.employee_ids:
            raise ValidationError(_('Please select employee.'))

        datas_a1 = []
        datas_a2 = []
        for emp in self.employee_ids:
            month_datetime = datetime.strptime(self.month, "%B")
            selected_month_number = month_datetime.month
            last_day_month = calendar.monthrange(int(self.year), selected_month_number)[1]
            month_selected = str('{:02d}'.format(selected_month_number))
            selected_month_start_date = self.year + '-' + month_selected + '-' + str('01')
            selected_month_start_date = datetime.strptime(selected_month_start_date, "%Y-%m-%d").date()
            selected_month_end_date = self.year + '-' + month_selected + '-' + str(last_day_month)
            selected_month_end_date = datetime.strptime(selected_month_end_date, "%Y-%m-%d").date()

            my_spt = self.env['hr.my.spt'].search(
                [('employee_id', '=', emp.id), ('year', '=', self.year), ('month', '=', self.month)], limit=1)

            if my_spt:
                sequence = my_spt.sequence
                payslips = self.env['hr.payslip'].search([('employee_id', '=', emp.id), ('state', '=', 'done'),
                                                          ('year', '=', self.year),
                                                          ('payslip_report_date', '<=', selected_month_end_date),
                                                          ('payslip_pesangon', '=', False)])

                gaji_atau_tht = 0
                tunjangan_pph = 0
                tunjangan_lainnya = 0
                honorarium = 0
                premi_asuransi = 0
                penerimaan_natura = 0
                tantiem_bonus = 0
                biaya_jabatan = 0
                iuran_pensiun = 0
                # komponen pns
                gaji_pokok = 0
                tunjangan_istri = 0
                tunjangan_anak = 0
                tunjangan_perbaikan_penghasilan = 0
                tunjangan_struktural = 0
                tunjangan_beras = 0
                tunjangan_khusus = 0
                tunjangan_lainnya = 0
                penghasilan_tetap = 0
                biaya_jabatan = 0
                iuran_pensiun = 0

                penghasilan_neto_masa = 0
                pph_pasal_21_terhutang = 0
                pph_pasal_21_atas_pengh = 0
                pph_pasal_21_yang = 0

                first_month = payslips[0].month_name
                last_month = payslips.sorted('id', reverse=True)[0].month_name
                first_month_datetime = datetime.strptime(first_month, "%B")
                first_month_number = first_month_datetime.month
                last_month_datetime = datetime.strptime(last_month, "%B")
                last_month_number = last_month_datetime.month
                last_day_month_number = calendar.monthrange(int(self.year), last_month_number)[1]

                for payslip in payslips:
                    for line in payslip.line_ids:
                        for spt_cat in line.salary_rule_id.spt_category_ids:
                            if emp.employee_tax_category == "non_pns":
                                if spt_cat.name == "GAJI/PENSIUN ATAU THT/JHT" and spt_cat.spt_type.code == "1721_A1":
                                    gaji_atau_tht += line.total
                                if spt_cat.name == "TUNJANGAN PPh" and spt_cat.spt_type.code == "1721_A1":
                                    tunjangan_pph += line.total
                                if spt_cat.name == "TUNJANGAN LAINNYA, UANG LEMBUR DAN SEBAGAINYA" and spt_cat.spt_type.code == "1721_A1":
                                    tunjangan_lainnya += line.total
                                if spt_cat.name == "HONORARIUM DAN IMBALAN LAIN SEJENISNYA" and spt_cat.spt_type.code == "1721_A1":
                                    honorarium += line.total
                                if spt_cat.name == "PREMI ASURANSI YANG DIBAYAR PEMBERI KERJA" and spt_cat.spt_type.code == "1721_A1":
                                    premi_asuransi += line.total
                                if spt_cat.name == "PENERIMAAN DALAM BENTUK NATURA DAN KENIKMATAN LAINNYA YANG DIKENAKAN PEMOTONGAN PPh PASAL 21" and spt_cat.spt_type.code == "1721_A1":
                                    penerimaan_natura += line.total
                                if spt_cat.name == "TANTIEM, BONUS, GRATIFIKASI, JASA PRODUKSI DAN THR" and spt_cat.spt_type.code == "1721_A1":
                                    tantiem_bonus += line.total
                                if spt_cat.name == "IURAN PENSIUN ATAU IURAN THT/JHT" and spt_cat.spt_type.code == "1721_A1":
                                    iuran_pensiun += line.total
                            elif emp.employee_tax_category == "pns":
                                if spt_cat.name == "GAJI POKOK/PENSIUN" and spt_cat.spt_type.code == "1721_A2":
                                    gaji_pokok += line.total
                                if spt_cat.name == "TUNJANGAN ISTERI" and spt_cat.spt_type.code == "1721_A2":
                                    tunjangan_istri += line.total
                                if spt_cat.name == "TUNJANGAN ANAK" and spt_cat.spt_type.code == "1721_A2":
                                    tunjangan_anak += line.total
                                if spt_cat.name == "TUNJANGAN PERBAIKAN PENGHASILAN" and spt_cat.spt_type.code == "1721_A2":
                                    tunjangan_perbaikan_penghasilan += line.total
                                if spt_cat.name == "TUNJANGAN STRUKTURAL/FUNGSIONAL" and spt_cat.spt_type.code == "1721_A2":
                                    tunjangan_struktural += line.total
                                if spt_cat.name == "TUNJANGAN BERAS" and spt_cat.spt_type.code == "1721_A2":
                                    tunjangan_beras += line.total
                                if spt_cat.name == "TUNJANGAN KHUSUS" and spt_cat.spt_type.code == "1721_A2":
                                    tunjangan_khusus += line.total
                                if spt_cat.name == "TUNJANGAN LAIN-LAIN" and spt_cat.spt_type.code == "1721_A2":
                                    tunjangan_lainnya += line.total
                                if spt_cat.name == "PENGHASILAN TETAP DAN TERATUR LAINNYA YANG PEMBAYARANNYA TERPISAH DARI PEMBAYARAN GAJI" and spt_cat.spt_type.code == "1721_A2":
                                    penghasilan_tetap += line.total
                                if spt_cat.name == "IURAN PENSIUN ATAU IURAN THT" and spt_cat.spt_type.code == "1721_A2":
                                    iuran_pensiun += line.total
                    biaya_jabatan += payslip.biaya_jab_month_reg + payslip.biaya_jab_irreguler
                    jumlah_penghasilan_neto_setahun = payslip.peng_thn_reguler + payslip.peng_thn_irreguler
                    pph_pasal_21_atas_pengh += payslip.pjk_bln_reguler + payslip.pjk_bln_irreguler
                    penghasilan_neto_masa = payslip.neto_masa_sebelumnya
                jumlah_gaji_pns = gaji_pokok + tunjangan_istri + tunjangan_anak
                jumlah_penghasilan_bruto_pns = jumlah_gaji_pns + tunjangan_perbaikan_penghasilan + tunjangan_struktural + tunjangan_beras + tunjangan_khusus + tunjangan_lainnya + penghasilan_tetap
                jumlah_penghasilan_bruto = gaji_atau_tht + tunjangan_pph + tunjangan_lainnya + honorarium + premi_asuransi + penerimaan_natura + tantiem_bonus
                jumlah_pengurangan = biaya_jabatan + iuran_pensiun
                jumlah_penghasilan_neto = jumlah_penghasilan_bruto - jumlah_pengurangan
                jumlan_penghasilan_neto_untuk = jumlah_penghasilan_neto_setahun

                ptkp = emp.ptkp_id.ptkp_amount

                if jumlan_penghasilan_neto_untuk - ptkp <= 0:
                    penghasilan_kena_pajak = 0
                    pph_pasal_21_atas = 0
                else:
                    penghasilan_kena_pajak = jumlan_penghasilan_neto_untuk - ptkp
                    pph_pasal_21_atas = pph_pasal_21_atas_pengh

                pph_pasal_21_terhutang = pph_pasal_21_atas
                pph_pasal_21_dan_pph_26 = pph_pasal_21_atas
                #komponen pns
                pph_pasal_21_dilunasi = pph_pasal_21_atas
                atas_gaji_tunjangan = 0
                atas_peghasilan_tetap = 0

                status_ptkp = ''
                jumlah_tanggungan = ''
                ptkp_name = emp.ptkp_id.ptkp_name if emp.ptkp_id else ''
                if ptkp_name:
                    if ptkp_name:
                        if 'TK' in ptkp_name:
                            status_ptkp = "TK"
                            jumlah_tanggungan = ptkp_name[3:]
                        else:
                            if 'HB' in ptkp_name:
                                status_ptkp = "HB"
                                jumlah_tanggungan = ptkp_name[3:]
                            if 'K' in ptkp_name:
                                status_ptkp = "K"
                                jumlah_tanggungan = ptkp_name[2:]
                else:
                    status_ptkp = ""
                    jumlah_tanggungan = ""

                country_domicile_code = self.env['country.domicile.code'].search([('country_id', '=', emp.country_id.id)], limit=1)

                if not emp.gender:
                    raise ValidationError(_("Employee %s (%s) doesnt set gender yet !") % (emp.name,emp.sequence_code))
                
                if emp.gender == "male":
                    employee_gender = "M"
                elif emp.gender == "female":
                    employee_gender = "F"

                if emp.country_id.name != "Indonesia":
                    employee_luar_negeri = "Y"
                else:
                    employee_luar_negeri = "N"

                if emp.employee_tax_category == "non_pns":
                    company_npwp = ''
                    company_name = ''
                    tax_cutter_npwp = ''
                    tax_cutter_name = ''
                    if emp.branch_id:
                        company_npwp = emp.branch_id and emp.branch_id.branch_npwp or ''
                        company_name = emp.branch_id and emp.branch_id.name or ''
                        tax_cutter_npwp = emp.branch_id and str(emp.branch_id.tax_cutter_npwp).replace('-', '') or ''
                        tax_cutter_name = emp.branch_id and emp.branch_id.tax_cutter_name.name or ''
                    else:
                        company_npwp = emp.company_id and emp.company_id.company_npwp or ''
                        company_name = emp.company_id and emp.company_id.name or ''
                        tax_cutter_npwp = emp.company_id and str(emp.company_id.tax_cutter_npwp).replace('-', '') or ''
                        tax_cutter_name = emp.company_id and emp.company_id.tax_cutter_name.name or ''
                    datas_a1.append({
                        'tahun_pajak': self.year,
                        'print_selected_month': str('{:02d}'.format(selected_month_number)),
                        'print_selected_year': str('{:02d}'.format(int(self.year[-2:]))),
                        'print_current_month': str('{:02d}'.format(datetime.now().date().month)),
                        'print_current_year': str(datetime.now().year)[-2:],
                        'sequence': str('{:07d}'.format(sequence)),
                        'first_month_number': str('{:02d}'.format(first_month_number)),
                        'last_day_month_number': str('{:02d}'.format(last_day_month_number)),
                        'last_month_number': str('{:02d}'.format(last_month_number)),
                        'company_npwp': company_npwp,
                        'company_name': company_name,
                        'employee_npwp': str(emp.npwp_no).replace('-', ''),
                        'employee_identification_id': emp.identification_id or emp.passport_id or '',
                        'employee_name': emp.name or '',
                        'employee_address': emp.identity_address or '',
                        'employee_gender': employee_gender,
                        'pension': '',
                        'status_ptkp': status_ptkp,
                        'jumlah_tanggungan': jumlah_tanggungan,
                        'employee_job': emp.job_id and emp.job_id.name or '',
                        'employee_country': emp.country_id.name,
                        'employee_luar_negeri': employee_luar_negeri,
                        'country_domicile_code': country_domicile_code.name or '',
                        'gaji_atau_tht': gaji_atau_tht,
                        'tunjangan_pph': tunjangan_pph,
                        'tunjangan_lainnya': tunjangan_lainnya,
                        'honorarium': honorarium,
                        'premi_asuransi': premi_asuransi,
                        'penerimaan_natura': penerimaan_natura,
                        'tantiem_bonus': tantiem_bonus,
                        'jumlah_penghasilan_bruto': jumlah_penghasilan_bruto,
                        'biaya_jabatan': round(biaya_jabatan),
                        'iuran_pensiun': round(iuran_pensiun),
                        'jumlah_pengurangan': jumlah_pengurangan,
                        'jumlah_penghasilan_neto': jumlah_penghasilan_neto,
                        'penghasilan_neto_masa': penghasilan_neto_masa,
                        'jumlan_penghasilan_neto_untuk': jumlan_penghasilan_neto_untuk,
                        'ptkp': ptkp,
                        'penghasilan_kena_pajak': self.round_down(penghasilan_kena_pajak, -3),
                        'pph_pasal_21_atas': round(pph_pasal_21_atas),
                        'pph_pasal_21_yang': round(pph_pasal_21_yang),
                        'pph_pasal_21_terhutang': round(pph_pasal_21_terhutang),
                        'pph_pasal_21_dan_pph_26': round(pph_pasal_21_dan_pph_26),
                        'company_taxcutter_npwp': tax_cutter_npwp,
                        'company_taxcutter_name': tax_cutter_name,
                    })
                elif emp.employee_tax_category == "pns":
                    company_npwp = ''
                    company_name = ''
                    tax_cutter_npwp = ''
                    tax_cutter_name = ''
                    if emp.branch_id:
                        company_npwp = emp.branch_id and emp.branch_id.branch_npwp or ''
                        company_name = emp.branch_id and emp.branch_id.name or ''
                        tax_cutter_npwp = emp.branch_id and str(emp.branch_id.tax_cutter_npwp).replace('-', '') or ''
                        tax_cutter_name = emp.branch_id and emp.branch_id.tax_cutter_name.name or ''
                    else:
                        company_npwp = emp.company_id and emp.company_id.company_npwp or ''
                        company_name = emp.company_id and emp.company_id.name or ''
                        tax_cutter_npwp = emp.company_id and str(emp.company_id.tax_cutter_npwp).replace('-', '') or ''
                        tax_cutter_name = emp.company_id and emp.company_id.tax_cutter_name.name or ''
                    datas_a2.append({
                        'tahun_pajak': self.year,
                        'print_selected_month': str('{:02d}'.format(selected_month_number)),
                        'print_selected_year': str('{:02d}'.format(int(self.year[-2:]))),
                        'print_current_month': str('{:02d}'.format(datetime.now().date().month)),
                        'print_current_year': str(datetime.now().year)[-2:],
                        'sequence': str('{:07d}'.format(sequence)),
                        'first_month_number': str('{:02d}'.format(first_month_number)),
                        'last_day_month_number': str('{:02d}'.format(last_day_month_number)),
                        'last_month_number': str('{:02d}'.format(last_month_number)),
                        'company_npwp': company_npwp,
                        'company_name': company_name,
                        'employee_nip': emp.sequence_code,
                        'employee_npwp': str(emp.npwp_no).replace('-', ''),
                        'employee_identification_id': emp.identification_id or emp.passport_id or '',
                        'employee_name': emp.name or '',
                        'employee_address': emp.identity_address or '',
                        'employee_gender': employee_gender,
                        'pension': '',
                        'status_ptkp': status_ptkp,
                        'jumlah_tanggungan': jumlah_tanggungan,
                        'employee_job': emp.job_id and emp.job_id.name or '',
                        'employee_country': emp.country_id.name,
                        'country_domicile_code': country_domicile_code.name,
                        'gaji_pokok': gaji_pokok,
                        'tunjangan_istri': tunjangan_istri,
                        'tunjangan_anak': tunjangan_anak,
                        'jumlah_gaji': jumlah_gaji_pns,
                        'tunjangan_perbaikan_penghasilan': tunjangan_perbaikan_penghasilan,
                        'tunjangan_struktural': tunjangan_struktural,
                        'tunjangan_beras': tunjangan_beras,
                        'tunjangan_khusus': tunjangan_khusus,
                        'tunjangan_lainnya': tunjangan_lainnya,
                        'penghasilan_tetap': penghasilan_tetap,
                        'jumlah_penghasilan_bruto': jumlah_penghasilan_bruto_pns,
                        'biaya_jabatan': biaya_jabatan,
                        'iuran_pensiun': iuran_pensiun,
                        'jumlah_pengurangan': jumlah_pengurangan,
                        'jumlah_penghasilan_neto': jumlah_penghasilan_neto,
                        'penghasilan_neto_masa': penghasilan_neto_masa,
                        'jumlan_penghasilan_neto_untuk': jumlan_penghasilan_neto_untuk,
                        'ptkp': ptkp,
                        'penghasilan_kena_pajak': self.round_down(penghasilan_kena_pajak, -3),
                        'pph_pasal_21_atas': round(pph_pasal_21_atas),
                        'pph_pasal_21_yang': round(pph_pasal_21_yang),
                        'pph_pasal_21_terhutang': round(pph_pasal_21_terhutang),
                        'pph_pasal_21_dilunasi': round(pph_pasal_21_dilunasi),
                        'atas_gaji_tunjangan': round(atas_gaji_tunjangan),
                        'atas_peghasilan_tetap': round(atas_peghasilan_tetap),
                        'company_taxcutter_npwp': tax_cutter_npwp,
                        'company_taxcutter_name': tax_cutter_name,
                    })

        if datas_a1:
            file_name = '1721_bp_A1.csv'
            file_path = tempfile.mktemp(suffix='.csv')
            with open(file_path, mode='w') as file:
                writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                writer.writerow(['Masa Pajak', 'Tahun Pajak', 'Pembetulan', 'Nomor Bukti Potong', 'Masa Perolehan Awal',
                                 'Masa Perolehan Akhir', 'NPWP', 'NIK', 'Nama', 'Alamat', 'Jenis Kelamin', 'Status PTKP',
                                 'Jumlah Tanggungan', 'Nama Jabatan', 'WP Luar Negeri', 'Kode Negara', 'Kode Pajak',
                                 'Jumlah 1', 'Jumlah 2', 'Jumlah 3', 'Jumlah 4', 'Jumlah 5', 'Jumlah 6', 'Jumlah 7',
                                 'Jumlah 8', 'Jumlah 9', 'Jumlah 10', 'Jumlah 11', 'Jumlah 12', 'Jumlah 13', 'Jumlah 14',
                                 'Jumlah 15', 'Jumlah 16', 'Jumlah 17', 'Jumlah 18', 'Jumlah 19', 'Jumlah 20',
                                 'Status Pindah', 'NPWP Pemotong', 'Nama Pemotong', 'Tanggal Bukti Potong'])
                for line in datas_a1:
                    val1 = line.get('last_month_number')
                    val2 = line.get('tahun_pajak')
                    val3 = "0"
                    val4 = "1.1-" + line.get('print_selected_month') + "." + line.get('print_selected_year') + "-" + line.get('sequence')
                    val5 = line.get('first_month_number')
                    val6 = line.get('last_month_number')
                    val7 = line.get('employee_npwp').replace('.', '')
                    val8 = line.get('employee_identification_id')
                    val9 = line.get('employee_name')
                    val10 = line.get('employee_address')
                    val11 = line.get('employee_gender')
                    val12 = line.get('status_ptkp')
                    val13 = line.get('jumlah_tanggungan')
                    val14 = line.get('employee_job')
                    val15 = line.get('employee_luar_negeri')
                    val16 = line.get('country_domicile_code')
                    val17 = "21-100-01"
                    val18 = str(int(line.get('gaji_atau_tht')))
                    val19 = str(int(line.get('tunjangan_pph')))
                    val20 = str(int(line.get('tunjangan_lainnya')))
                    val21 = str(int(line.get('honorarium')))
                    val22 = str(int(line.get('premi_asuransi')))
                    val23 = str(int(line.get('penerimaan_natura')))
                    val24 = str(int(line.get('tantiem_bonus')))
                    val25 = str(int(line.get('jumlah_penghasilan_bruto')))
                    val26 = str(int(line.get('biaya_jabatan')))
                    val27 = str(int(line.get('iuran_pensiun')))
                    val28 = str(int(line.get('jumlah_pengurangan')))
                    val29 = str(int(line.get('jumlah_penghasilan_neto')))
                    val30 = str(int(line.get('penghasilan_neto_masa')))
                    val31 = str(int(line.get('jumlan_penghasilan_neto_untuk')))
                    val32 = str(int(line.get('ptkp')))
                    val33 = str(int(line.get('penghasilan_kena_pajak')))
                    val34 = str(line.get('pph_pasal_21_atas'))
                    val35 = str(line.get('pph_pasal_21_yang'))
                    val36 = str(line.get('pph_pasal_21_terhutang'))
                    val37 = str(line.get('pph_pasal_21_dan_pph_26'))
                    val38 = ""
                    val39 = line.get('company_taxcutter_npwp').replace('.', '') or ""
                    val40 = line.get('company_taxcutter_name')
                    val41 = line.get('last_day_month_number') + "/" + line.get('last_month_number') + "/" + line.get('tahun_pajak')
                    writer.writerow([val1, val2, val3, val4, val5, val6, val7, val8, val9, val10, val11, val12, val13,
                                     val14, val15, val16, val17, val18, val19, val20, val21, val22, val23, val24, val25, val26,
                                     val27, val28, val29, val30, val31, val32, val33, val34, val35, val36, val37, val38, val39,
                                     val40, val41])
            with open(file_path, 'r', encoding="utf-8") as f2:
                data = str.encode(f2.read(), 'utf-8')
            export_id = self.env['hr.spt.report.excel'].create(
                {'excel_file': base64.encodebytes(data), 'file_name': file_name})
            return {
                'view_mode': 'form',
                'res_id': export_id.id,
                'name': '1721 A1 / A2',
                'res_model': 'hr.spt.report.excel',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'target': 'new',
            }
        elif datas_a2:
            file_name = '1721_bp_A2.csv'
            file_path = tempfile.mktemp(suffix='.csv')
            with open(file_path, mode='w') as file:
                writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                writer.writerow(['Masa Pajak', 'Tahun Pajak', 'Pembetulan', 'Nomor Bukti Potong', 'Masa Perolehan Awal',
                                 'Masa Perolehan Akhir', 'NPWP', 'NIP', 'Nama', 'Pangkat', 'Golongan', 'Alamat',
                                 'Jenis Kelamin', 'NIK', 'Status PTKP', 'Jumlah Tanggungan', 'Nama Jabatan',
                                 'Kode Pajak', 'Jumlah 1', 'Jumlah 2', 'Jumlah 3', 'Jumlah 4', 'Jumlah 5', 'Jumlah 6',
                                 'Jumlah 7', 'Jumlah 8', 'Jumlah 9', 'Jumlah 10', 'Jumlah 11', 'Jumlah 12', 'Jumlah 13',
                                 'Jumlah 14', 'Jumlah 15', 'Jumlah 16', 'Jumlah 17', 'Jumlah 18', 'Jumlah 19',
                                 'Jumlah 20', 'Jumlah 21', 'Jumlah 22', 'Jumlah 23', 'Jumlah 23a', 'Jumlah 23b',
                                 'Status Pindah', 'NPWP Pemotong', 'Nama Pemotong', 'Tanggal Bukti Potong',
                                 'Instansi Pemotong', 'NIP Pemotong'])
                for line in datas_a2:
                    val1 = line.get('last_month_number')
                    val2 = line.get('tahun_pajak')
                    val3 = "0"
                    val4 = "1.1-" + line.get('print_selected_month') + "." + line.get('print_selected_year') + "-" + line.get('sequence')
                    val5 = line.get('first_month_number')
                    val6 = line.get('last_month_number')
                    val7 = line.get('employee_npwp').replace('.', '') or ''
                    val8 = line.get('employee_nip')
                    val9 = line.get('employee_name')
                    val10 = ""
                    val11 = ""
                    val12 = line.get('employee_address')
                    val13 = line.get('employee_gender')
                    val14 = line.get('employee_identification_id')
                    val15 = line.get('status_ptkp')
                    val16 = line.get('jumlah_tanggungan')
                    val17 = line.get('employee_job')
                    val18 = "21-100-01"
                    val19 = str(int(line.get('gaji_pokok')))
                    val20 = str(int(line.get('tunjangan_istri')))
                    val21 = str(int(line.get('tunjangan_anak')))
                    val22 = str(int(line.get('jumlah_gaji')))
                    val23 = str(int(line.get('tunjangan_perbaikan_penghasilan')))
                    val24 = str(int(line.get('tunjangan_struktural')))
                    val25 = str(int(line.get('tunjangan_beras')))
                    val26 = str(int(line.get('tunjangan_khusus')))
                    val27 = str(int(line.get('tunjangan_lainnya')))
                    val28 = str(int(line.get('penghasilan_tetap')))
                    val29 = str(int(line.get('jumlah_penghasilan_bruto')))
                    val30 = str(int(line.get('biaya_jabatan')))
                    val31 = str(int(line.get('iuran_pensiun')))
                    val32 = str(int(line.get('jumlah_pengurangan')))
                    val33 = str(int(line.get('jumlah_penghasilan_neto')))
                    val34 = str(int(line.get('penghasilan_neto_masa')))
                    val35 = str(int(line.get('jumlan_penghasilan_neto_untuk')))
                    val36 = str(int(line.get('ptkp')))
                    val37 = str(int(line.get('penghasilan_kena_pajak')))
                    val38 = str(line.get('pph_pasal_21_atas'))
                    val39 = str(line.get('pph_pasal_21_yang'))
                    val40 = str(line.get('pph_pasal_21_terhutang'))
                    val41 = str(line.get('pph_pasal_21_dilunasi'))
                    val42 = str(line.get('atas_gaji_tunjangan'))
                    val43 = str(line.get('atas_peghasilan_tetap'))
                    val44 = ""
                    val45 = ""
                    val46 = ""
                    val47 = line.get('last_day_month_number') + "/" + line.get('last_month_number') + "/" + line.get('tahun_pajak')
                    val48 = ""
                    val49 = ""
                    writer.writerow([val1, val2, val3, val4, val5, val6, val7, val8, val9, val10, val11, val12, val13,
                                     val14, val15, val16, val17, val18, val19, val20, val21, val22, val23, val24, val25,
                                     val26, val27, val28, val29, val30, val31, val32, val33, val34, val35, val36, val37,
                                     val38, val39, val40, val41, val42, val43, val44, val45, val46, val47, val48, val49])

            with open(file_path, 'r', encoding="utf-8") as f2:
                data = str.encode(f2.read(), 'utf-8')
            export_id = self.env['hr.spt.report.excel'].create(
                {'excel_file': base64.encodebytes(data), 'file_name': file_name})
            return {
                'view_mode': 'form',
                'res_id': export_id.id,
                'name': '1721 A1 / A2',
                'res_model': 'hr.spt.report.excel',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'target': 'new',
            }
        else:
            raise ValidationError(_('There is no Data.'))