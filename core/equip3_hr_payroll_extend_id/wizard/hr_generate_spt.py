# -*- coding: utf-8 -*-
import calendar
import base64
import math
from odoo import api, fields, models, _
from datetime import datetime
import time
from odoo.modules.module import get_resource_path
from odoo.exceptions import ValidationError

class HrGenerateSpt(models.TransientModel):
    _name = 'hr.generate.spt'

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
    
    # @api.model
    # def _employee_domain(self):
    #      domain = [('company_id','=',self.env.company.id)]
    #      return domain
     
    spt_type = fields.Selection([('spt_1721_a1_a2','1721 A1/A2'),('spt_masa','SPT Masa')],
                             default='spt_1721_a1_a2', string='SPT Type', required=True)
    year = fields.Selection(selection=lambda self: self._compute_year_selection(), string="Year", default="none", required=True)
    month = fields.Selection(selection=lambda self: self._compute_month_selection(), string="Month", default="none", required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company)
    employee_ids = fields.Many2many('hr.employee', string='Employees', required=True)

    def _get_default_dirjen_pajak(self):
        tmp_path = get_resource_path('equip3_hr_payroll_extend_id', 'static', 'src', 'img', 'logo_dirjen_pajak.png')
        return base64.b64encode(open(tmp_path, 'rb').read())

    logo_dirjen_pajak = fields.Binary(default=_get_default_dirjen_pajak, string="Logo DJP")

    @api.onchange('employee_ids','year','month')
    def _onchange_employee_ids(self):
        employees = []
        if self.year != 'none' and self.month != 'none':
            month_datetime = datetime.strptime(self.month, "%B")
            month_selected = month_datetime.month
            last_day_month = calendar.monthrange(int(self.year), month_selected)[1]
            month_selected = str('{:02d}'.format(month_selected))
            selected_month_start_date = self.year + '-' + month_selected + '-' + str('01')
            selected_month_start_date = datetime.strptime(selected_month_start_date, "%Y-%m-%d").date()
            selected_month_end_date = self.year + '-' + month_selected + '-' + str(last_day_month)
            selected_month_end_date = datetime.strptime(selected_month_end_date, "%Y-%m-%d").date()
            
            payslips = self.env['hr.payslip'].search([('state', '=', 'done'),
                                                        ('payslip_report_date', '>=', selected_month_start_date),
                                                        ('payslip_report_date', '<=', selected_month_end_date),
                                                        ('payslip_pesangon', '=', False),
                                                        ('company_id', '=', self.company_id.id),
                                                        ('employee_id.company_id','=',self.env.company.id)])
            if payslips:
                for slip in payslips:
                    employees.append(slip.employee_id.id)
        return {
            'domain': {'employee_ids': [('id', 'in', employees)]},
        }

    def action_generate(self):
        if self.spt_type == "spt_1721_a1_a2":
            if not self.employee_ids:
                raise ValidationError(_('Please select employee.'))

            spt_sequence = self.env['hr.spt.sequence'].search([('name', '=', self.year)], limit=1)
            if spt_sequence:
                sequence = spt_sequence.number_next
            else:
                sequence_dict = []
                sequence_dict.append({
                    'name': self.year
                })
                spt_sequence = self.env["hr.spt.sequence"].create(sequence_dict)
                sequence = spt_sequence.number_next

            for emp in self.employee_ids:
                month_datetime = datetime.strptime(self.month, "%B")
                month_selected = month_datetime.month
                last_day_month = calendar.monthrange(int(self.year), month_selected)[1]
                month_selected = str('{:02d}'.format(month_selected))
                selected_month_start_date = self.year + '-' + month_selected + '-' + str('01')
                selected_month_start_date = datetime.strptime(selected_month_start_date, "%Y-%m-%d").date()
                selected_month_end_date = self.year + '-' + month_selected + '-' + str(last_day_month)
                selected_month_end_date = datetime.strptime(selected_month_end_date, "%Y-%m-%d").date()

                my_spt = self.env['hr.my.spt'].search([('employee_id', '=', emp.id),('year', '=', self.year),('month', '=', self.month)], limit=1)

                payslips = self.env['hr.payslip'].search([('employee_id', '=', emp.id),('state', '=', 'done'),
                                                        ('payslip_report_date', '>=', selected_month_start_date),
                                                        ('payslip_report_date', '<=', selected_month_end_date),
                                                        ('payslip_pesangon', '=', False)])
                if my_spt:
                    sequence = my_spt.sequence

                if payslips:
                    datas = {
                        'employee_id': emp.id,
                        'month': self.month,
                        'year': self.year,
                        'sequence': sequence,
                        'logo_dirjen_pajak': self.logo_dirjen_pajak
                    }
                    if emp.employee_tax_category == "non_pns":
                        pdf = self.env.ref('equip3_hr_payroll_extend_id.action_report_spt_1721_a1')._render_qweb_pdf([emp.id], data=datas)
                    elif emp.employee_tax_category == "pns":
                        pdf = self.env.ref('equip3_hr_payroll_extend_id.action_report_spt_1721_a2')._render_qweb_pdf([emp.id], data=datas)

                    attachment = base64.b64encode(pdf[0])
                    if emp.employee_tax_category == "non_pns":
                        spt_type = self.env['hr.spt.type'].search([('code', '=', '1721_A1')], limit=1)
                    elif emp.employee_tax_category == "pns":
                        spt_type = self.env['hr.spt.type'].search([('code', '=', '1721_A2')], limit=1)

                    if not my_spt:
                        self.env["hr.my.spt"].create({
                            'employee_id': emp.id,
                            'year': self.year,
                            'month': self.month,
                            'kpp': emp.kpp_id.id or False,
                            'spt_type': spt_type.id,
                            'spt_type_name': spt_type.name,
                            'attachment': attachment,
                            'sequence': sequence
                        })
                        sequence = sequence + 1
                        spt_sequence.write({'number_next': sequence})
                    else:
                        my_spt.write({
                            'kpp': emp.kpp_id.id or False,
                            'spt_type': spt_type.id,
                            'spt_type_name': spt_type.name,
                            'attachment': attachment
                        })
        elif self.spt_type == "spt_masa":
            payslips = self.env['hr.payslip'].search([('company_id', '=', self.company_id.id),('state', '=', 'done'),
                                                    ('year', '=', self.year),
                                                    ('month_name', '=', self.month),
                                                    ('payslip_pesangon', '=', False)])
            if payslips:
                spt_masa = self.env['hr.spt.masa'].search([('company_id', '=', self.company_id.id),('year', '=', self.year),('month', '=', self.month)], limit=1)
                datas = {
                    'company_id': self.company_id.id,
                    'month': self.month,
                    'year': self.year,
                    'logo_dirjen_pajak': self.logo_dirjen_pajak
                }
                pdf = self.env.ref('equip3_hr_payroll_extend_id.action_report_spt_masa')._render_qweb_pdf([self.company_id.id], data=datas)
                attachment = base64.b64encode(pdf[0])
                spt_type = self.env['hr.spt.type'].search([('code', '=', 'SPT_MASA')], limit=1)
                if not spt_masa:
                    self.env["hr.spt.masa"].create({
                        'company_id': self.company_id.id,
                        'year': self.year,
                        'month': self.month,
                        'spt_type': spt_type.id,
                        'spt_type_name': spt_type.name,
                        'attachment': attachment,
                    })
                else:
                    spt_masa.write({
                        'spt_type': spt_type.id,
                        'spt_type_name': spt_type.name,
                        'attachment': attachment
                    })
            else:
                raise ValidationError(_('There is no Match Data on this Period and Company!'))
            
        return True

class HrGenerateSpt1721A1(models.AbstractModel):
    _name = 'report.equip3_hr_payroll_extend_id.report_spt_1721_a1'

    def round_down(self, n, decimals=0):
        multiplier = 10 ** decimals
        return math.floor(n * multiplier) / multiplier

    def _get_report_values(self, docids, data=None):
        logo_dirjen_pajak = data.get('logo_dirjen_pajak')
        employee = self.env['hr.employee'].browse(data.get('employee_id'))
        country_domicile_code = self.env['country.domicile.code'].search([('country_id', '=', employee.country_id.id)], limit=1)

        month_datetime = datetime.strptime(data.get('month'), "%B")
        selected_month_number = month_datetime.month
        last_day_month = calendar.monthrange(int(data.get('year')), selected_month_number)[1]
        month_selected = str('{:02d}'.format(selected_month_number))
        selected_month_end_date = data.get('year') + '-' + month_selected + '-' + str(last_day_month)
        selected_month_end_date = datetime.strptime(selected_month_end_date, "%Y-%m-%d").date()

        domain = [('state', '=', 'done'), ('payslip_pesangon', '=', False)]
        if data.get('employee_id'):
            domain.append(('employee_id', '=', data.get('employee_id')))
        if data.get('year'):
            domain.append(('year', '=', data.get('year')))
        if selected_month_end_date:
            domain.append(('payslip_report_date', '<=', selected_month_end_date))
        docs = self.env['hr.payslip'].search(domain)

        sequence = data.get('sequence')
        gaji_atau_tht = 0
        tunjangan_pph = 0
        tunjangan_lainnya = 0
        honorarium = 0
        premi_asuransi = 0
        penerimaan_natura = 0
        tantiem_bonus = 0
        biaya_jabatan = 0
        iuran_pensiun = 0
        penghasilan_neto_masa = 0
        pph_pasal_21_terhutang = 0
        pph_pasal_21_atas_pengh = 0
        pph_pasal_21_yang = 0

        first_month = docs[0].month_name
        last_month = docs.sorted('id', reverse=True)[0].month_name
        first_month_datetime = datetime.strptime(first_month, "%B")
        first_month_number = first_month_datetime.month
        last_month_datetime = datetime.strptime(last_month, "%B")
        last_month_number = last_month_datetime.month
        last_day_month_number = calendar.monthrange(int(data.get('year')), last_month_number)[1]

        for payslip in docs:
            for line in payslip.line_ids:
                for spt_cat in line.salary_rule_id.spt_category_ids:
                    if employee.employee_tax_category == "non_pns":
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

            biaya_jabatan += payslip.biaya_jab_month_reg + payslip.biaya_jab_irreguler
            jumlah_penghasilan_neto_setahun = payslip.peng_thn_reguler + payslip.peng_thn_irreguler
            pph_pasal_21_atas_pengh += payslip.pjk_bln_reguler + payslip.pjk_bln_irreguler
            penghasilan_neto_masa = payslip.neto_masa_sebelumnya
        jumlah_penghasilan_bruto = gaji_atau_tht + tunjangan_pph + tunjangan_lainnya + honorarium + premi_asuransi + penerimaan_natura + tantiem_bonus
        jumlah_pengurangan = biaya_jabatan + iuran_pensiun
        jumlah_penghasilan_neto = jumlah_penghasilan_bruto - jumlah_pengurangan
        jumlan_penghasilan_neto_untuk = jumlah_penghasilan_neto_setahun

        ptkp = employee.ptkp_id.ptkp_amount

        if jumlan_penghasilan_neto_untuk - ptkp <= 0:
            penghasilan_kena_pajak = 0
            pph_pasal_21_atas = 0
        else:
            penghasilan_kena_pajak = jumlan_penghasilan_neto_untuk - ptkp
            pph_pasal_21_atas = pph_pasal_21_atas_pengh

        pph_pasal_21_terhutang = pph_pasal_21_atas
        pph_pasal_21_dan_pph_26 = pph_pasal_21_atas

        ptkp_K = ''
        ptkp_TK = ''
        ptkp_HB = ''
        ptkp_name = employee.ptkp_id.ptkp_name if employee.ptkp_id else False
        if ptkp_name:
            if ptkp_name:
                if 'TK' in ptkp_name:
                    ptkp_TK = ptkp_name[3:]
                else:
                    if 'HB' in ptkp_name:
                        ptkp_HB = ptkp_name[3:]
                    if 'K' in ptkp_name:
                        ptkp_K = ptkp_name[2:]
        
        company_npwp = ''
        company_name = ''
        tax_cutter_npwp = ''
        tax_cutter_name = ''
        digital_signature = ''
        if employee.branch_id:
            company_npwp = employee.branch_id and employee.branch_id.branch_npwp or ''
            company_name = employee.branch_id and employee.branch_id.name or ''
            tax_cutter_npwp = employee.branch_id and employee.branch_id.tax_cutter_npwp or ''
            tax_cutter_name = employee.branch_id and employee.branch_id.tax_cutter_name.name or ''
            digital_signature = employee.branch_id and employee.branch_id.tax_cutter_name.digital_signature
        else:
            company_npwp = employee.company_id and employee.company_id.company_npwp or ''
            company_name = employee.company_id and employee.company_id.name or ''
            tax_cutter_npwp = employee.company_id and employee.company_id.tax_cutter_npwp or ''
            tax_cutter_name = employee.company_id and employee.company_id.tax_cutter_name.name or ''
            digital_signature = employee.company_id and employee.company_id.tax_cutter_name.digital_signature

        return {
            'doc_ids': docs.ids,
            'doc_model': 'hr.payslip',
            'docs': docs,
            'logo_dirjen_pajak': logo_dirjen_pajak,
            'print_selected_month': str('{:02d}'.format(selected_month_number)),
            'print_selected_year': str('{:02d}'.format(int(data.get('year')[-2:]))),
            'print_current_month': str('{:02d}'.format(datetime.now().date().month)),
            'print_current_year': str(datetime.now().year)[-2:],
            'sequence': str('{:07d}'.format(sequence)),
            'first_month_number': str('{:02d}'.format(first_month_number)),
            'last_day_month_number': str('{:02d}'.format(last_day_month_number)),
            'last_month_number': str('{:02d}'.format(last_month_number)),
            'company_npwp': company_npwp,
            'company_name': company_name,
            'employee_npwp': employee.npwp_no,
            'employee_identification_id': employee.identification_id or employee.passport_id or '',
            'employee_name': employee.name or '',
            'employee_address': employee.identity_address or '',
            'employee_gender': employee.gender,
            'pension': False,
            'ptkp_K': ptkp_K,
            'ptkp_TK': ptkp_TK,
            'ptkp_HB': ptkp_HB,
            'employee_job': employee.job_id and employee.job_id.name or '',
            'employee_country': employee.country_id.name,
            'country_domicile_code': country_domicile_code.name,
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
            'full_year': data.get('year'),
            'digital_signature': digital_signature,
            'datas': data
        }

class HrGenerateSpt1721A2(models.AbstractModel):
    _name = 'report.equip3_hr_payroll_extend_id.report_spt_1721_a2'

    def round_down(self, n, decimals=0):
        multiplier = 10 ** decimals
        return math.floor(n * multiplier) / multiplier

    def _get_report_values(self, docids, data=None):
        logo_dirjen_pajak = data.get('logo_dirjen_pajak')
        employee = self.env['hr.employee'].browse(data.get('employee_id'))
        country_domicile_code = self.env['country.domicile.code'].search([('country_id', '=', employee.country_id.id)], limit=1)

        month_datetime = datetime.strptime(data.get('month'), "%B")
        selected_month_number = month_datetime.month
        last_day_month = calendar.monthrange(int(data.get('year')), selected_month_number)[1]
        month_selected = str('{:02d}'.format(selected_month_number))
        selected_month_end_date = data.get('year') + '-' + month_selected + '-' + str(last_day_month)
        selected_month_end_date = datetime.strptime(selected_month_end_date, "%Y-%m-%d").date()

        domain = [('state', '=', 'done'), ('payslip_pesangon', '=', False)]
        if data.get('employee_id'):
            domain.append(('employee_id', '=', data.get('employee_id')))
        if data.get('year'):
            domain.append(('year', '=', data.get('year')))
        if selected_month_end_date:
            domain.append(('payslip_report_date', '<=', selected_month_end_date))
        docs = self.env['hr.payslip'].search(domain)

        sequence = data.get('sequence')
        gaji_pokok = 0
        tunjangan_istri = 0
        tunjangan_anak = 0
        tunjangan_perbaikan_penghasilan = 0
        tunjangan_struktural = 0
        tunjangan_beras = 0
        tunjangan_khusus = 0
        tunjangan_lainnya= 0
        penghasilan_tetap = 0
        biaya_jabatan = 0
        iuran_pensiun = 0
        penghasilan_neto_masa = 0
        pph_pasal_21_terhutang = 0
        pph_pasal_21_atas_pengh = 0
        pph_pasal_21_yang = 0

        first_month = docs[0].month_name
        last_month = docs.sorted('id', reverse=True)[0].month_name
        first_month_datetime = datetime.strptime(first_month, "%B")
        first_month_number = first_month_datetime.month
        last_month_datetime = datetime.strptime(last_month, "%B")
        last_month_number = last_month_datetime.month
        last_day_month_number = calendar.monthrange(int(data.get('year')), last_month_number)[1]

        for payslip in docs:
            for line in payslip.line_ids:
                for spt_cat in line.salary_rule_id.spt_category_ids:
                    if employee.employee_tax_category == "pns":
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
        jumlah_gaji = gaji_pokok + tunjangan_istri + tunjangan_anak
        jumlah_penghasilan_bruto = jumlah_gaji + tunjangan_perbaikan_penghasilan + tunjangan_struktural + tunjangan_beras + tunjangan_khusus + tunjangan_lainnya + penghasilan_tetap
        jumlah_pengurangan = biaya_jabatan + iuran_pensiun
        jumlah_penghasilan_neto = jumlah_penghasilan_bruto - jumlah_pengurangan
        jumlan_penghasilan_neto_untuk = jumlah_penghasilan_neto_setahun

        ptkp = employee.ptkp_id.ptkp_amount

        if jumlan_penghasilan_neto_untuk - ptkp <= 0:
            penghasilan_kena_pajak = 0
            pph_pasal_21_atas = 0
        else:
            penghasilan_kena_pajak = jumlan_penghasilan_neto_untuk - ptkp
            pph_pasal_21_atas = pph_pasal_21_atas_pengh

        pph_pasal_21_terhutang = pph_pasal_21_atas
        pph_pasal_21_dilunasi = pph_pasal_21_atas
        atas_gaji_tunjangan = 0
        atas_peghasilan_tetap = 0

        ptkp_K = ''
        ptkp_TK = ''
        ptkp_HB = ''
        ptkp_name = employee.ptkp_id.ptkp_name if employee.ptkp_id else False
        if ptkp_name:
            if ptkp_name:
                if 'TK' in ptkp_name:
                    ptkp_TK = ptkp_name[3:]
                else:
                    if 'HB' in ptkp_name:
                        ptkp_HB = ptkp_name[3:]
                    if 'K' in ptkp_name:
                        ptkp_K = ptkp_name[2:]

        company_npwp = ''
        company_name = ''
        tax_cutter_npwp = ''
        tax_cutter_name = ''
        digital_signature = ''
        if employee.branch_id:
            company_npwp = employee.branch_id and employee.branch_id.branch_npwp or ''
            company_name = employee.branch_id and employee.branch_id.name or ''
            tax_cutter_npwp = employee.branch_id and employee.branch_id.tax_cutter_npwp or ''
            tax_cutter_name = employee.branch_id and employee.branch_id.tax_cutter_name.name or ''
            digital_signature = employee.branch_id and employee.branch_id.tax_cutter_name.digital_signature
        else:
            company_npwp = employee.company_id and employee.company_id.company_npwp or ''
            company_name = employee.company_id and employee.company_id.name or ''
            tax_cutter_npwp = employee.company_id and employee.company_id.tax_cutter_npwp or ''
            tax_cutter_name = employee.company_id and employee.company_id.tax_cutter_name.name or ''
            digital_signature = employee.company_id and employee.company_id.tax_cutter_name.digital_signature
        
        return {
            'doc_ids': docs.ids,
            'doc_model': 'hr.payslip',
            'docs': docs,
            'logo_dirjen_pajak': logo_dirjen_pajak,
            'print_selected_month': str('{:02d}'.format(selected_month_number)),
            'print_selected_year': str('{:02d}'.format(int(data.get('year')[-2:]))),
            'print_current_month': str('{:02d}'.format(datetime.now().date().month)),
            'print_current_year': str(datetime.now().year)[-2:],
            'sequence': str('{:07d}'.format(sequence)),
            'first_month_number': str('{:02d}'.format(first_month_number)),
            'last_day_month_number': str('{:02d}'.format(last_day_month_number)),
            'last_month_number': str('{:02d}'.format(last_month_number)),
            'company_npwp': company_npwp,
            'company_name': company_name,
            'employee_nip': employee.sequence_code,
            'employee_npwp': employee.npwp_no,
            'employee_identification_id': employee.identification_id or employee.passport_id or '',
            'employee_name': employee.name or '',
            'employee_address': employee.identity_address or '',
            'employee_gender': employee.gender,
            'pension': False,
            'ptkp_K': ptkp_K,
            'ptkp_TK': ptkp_TK,
            'ptkp_HB': ptkp_HB,
            'employee_job': employee.job_id and employee.job_id.name or '',
            'employee_country': employee.country_id.name,
            'country_domicile_code': country_domicile_code.name,
            'gaji_pokok': gaji_pokok,
            'tunjangan_istri': tunjangan_istri,
            'tunjangan_anak': tunjangan_anak,
            'jumlah_gaji': jumlah_gaji,
            'tunjangan_perbaikan_penghasilan': tunjangan_perbaikan_penghasilan,
            'tunjangan_struktural': tunjangan_struktural,
            'tunjangan_beras': tunjangan_beras,
            'tunjangan_khusus': tunjangan_khusus,
            'tunjangan_lainnya': tunjangan_lainnya,
            'penghasilan_tetap': penghasilan_tetap,
            'jumlah_penghasilan_bruto': jumlah_penghasilan_bruto,
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
            'full_year': data.get('year'),
            'digital_signature': digital_signature,
            'datas': data
        }

class HrGenerateSptMasa(models.AbstractModel):
    _name = 'report.equip3_hr_payroll_extend_id.report_spt_masa'

    def round_down(self, n, decimals=0):
        multiplier = 10 ** decimals
        return math.floor(n * multiplier) / multiplier

    def _get_report_values(self, docids, data=None):
        logo_dirjen_pajak = data.get('logo_dirjen_pajak')
        company = self.env['res.company'].browse(data.get('company_id'))

        month_datetime = datetime.strptime(data.get('month'), "%B")
        selected_month_number = month_datetime.month

        domain = [('state', '=', 'done'), ('payslip_pesangon', '=', False)]
        if data.get('company_id'):
            domain.append(('company_id', '=', data.get('company_id')))
        if data.get('year'):
            domain.append(('year', '=', data.get('year')))
        if data.get('month'):
            domain.append(('month_name', '=', data.get('month')))
        docs = self.env['hr.payslip'].search(domain)

        jml_penerima_peg_tetap = 0
        jml_hasil_bruto_peg_tetap = 0
        jml_pajak_dipotong_peg_tetap = 0
        jml_penerima_peg_tidak_tetap = 0
        jml_hasil_bruto_peg_tidak_tetap = 0
        jml_pajak_dipotong_peg_tidak_tetap = 0
        for payslip in docs:
            if payslip.employee_id.employee_tax_status == "pegawai_tetap":
                jml_penerima_peg_tetap += 1
                jml_hasil_bruto_peg_tetap += (payslip.bruto + payslip.bruto_gross)
                jml_pajak_dipotong_peg_tetap += (payslip.pjk_bln_reguler + payslip.pjk_bln_reguler_gross + payslip.pjk_bln_irreguler + payslip.pjk_bln_irreguler_gross)
            elif payslip.employee_id.employee_tax_status == "pegawai_tidak_tetap":
                jml_penerima_peg_tidak_tetap += 1
                jml_hasil_bruto_peg_tidak_tetap += (payslip.bruto + payslip.bruto_gross)
                jml_pajak_dipotong_peg_tidak_tetap += (payslip.pjk_bln_reguler + payslip.pjk_bln_reguler_gross + payslip.pjk_bln_irreguler + payslip.pjk_bln_irreguler_gross)
        
        total_penerima_penghasilan = jml_penerima_peg_tetap + jml_penerima_peg_tidak_tetap
        total_penghasilan_bruto = jml_hasil_bruto_peg_tetap + jml_hasil_bruto_peg_tidak_tetap
        total_pajak_dipotong = jml_pajak_dipotong_peg_tetap + jml_pajak_dipotong_peg_tidak_tetap

        company_npwp = company.company_npwp or ''
        company_name = company.name or ''
        company_street = company.street or ''
        company_phone = company.phone or ''
        company_email = company.email or ''
        tax_cutter_npwp = company.tax_cutter_npwp or ''
        tax_cutter_name = company.tax_cutter_name.name or ''
        tax_cutter_digital_sign = company.tax_cutter_name.digital_signature

        return {
            'doc_ids': docs.ids,
            'doc_model': 'hr.payslip',
            'docs': docs,
            'logo_dirjen_pajak': logo_dirjen_pajak,
            'full_selected_year': data.get('year'),
            'print_selected_month': str('{:02d}'.format(selected_month_number)),
            'company_npwp': company_npwp,
            'company_name': company_name,
            'company_street': company_street,
            'company_phone': company_phone,
            'company_email': company_email,
            'jml_penerima_peg_tetap': jml_penerima_peg_tetap,
            'jml_hasil_bruto_peg_tetap': jml_hasil_bruto_peg_tetap,
            'jml_pajak_dipotong_peg_tetap': jml_pajak_dipotong_peg_tetap,
            'jml_penerima_peg_tidak_tetap': jml_penerima_peg_tidak_tetap,
            'jml_hasil_bruto_peg_tidak_tetap': jml_hasil_bruto_peg_tidak_tetap,
            'jml_pajak_dipotong_peg_tidak_tetap': jml_pajak_dipotong_peg_tidak_tetap,
            'total_penerima_penghasilan': total_penerima_penghasilan,
            'total_penghasilan_bruto': total_penghasilan_bruto,
            'total_pajak_dipotong': total_pajak_dipotong,
            'tax_cutter_npwp': tax_cutter_npwp,
            'tax_cutter_name': tax_cutter_name,
            'tax_cutter_digital_sign': tax_cutter_digital_sign,
            'datas': data
        }