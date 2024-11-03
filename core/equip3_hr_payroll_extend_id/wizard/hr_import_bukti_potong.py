# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import ValidationError, Warning
import logging
import tempfile
import binascii
import datetime

_logger = logging.getLogger(__name__)

try:
    import xlrd
except ImportError:
    _logger.debug('Cannot `import xlrd`.')

class HrImportBuktiPotong(models.TransientModel):
    _name = "hr.import.bukti.potong"
    _description = 'Import 1721'

    tipe_bukti_potong = fields.Many2one('hr.spt.type', string="Tipe Bukti Potong", required=True)
    import_file = fields.Binary(string="Import File", required=True)
    import_name = fields.Char('Import Name', size=64)

    def import_action(self):
        import_name_extension = self.import_name.split('.')[1]
        if import_name_extension not in ['xls', 'xlsx']:
            raise ValidationError('The upload file is using the wrong format. Please upload your file in xlsx or xls format.')
        
        fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        fp.write(binascii.a2b_base64(self.import_file))
        fp.seek(0)
        workbook = xlrd.open_workbook(fp.name)
        sheet = workbook.sheet_by_index(0)
        keys = sheet.row_values(0)
        xls_reader = [sheet.row_values(i) for i in range(1, sheet.nrows)]

        vals = []
        if self.tipe_bukti_potong and self.tipe_bukti_potong.code == "1721_A1":
            # tipe_bukti_potong = self.env['hr.spt.type'].search([('code','=',self.tipe_bukti_potong)], limit=1)
            tipe_bukti_potong = self.tipe_bukti_potong

            for row in xls_reader:
                line = dict(zip(keys, row))

                if line.get('NIK'):
                    employee_obj = self.env['hr.employee'].search([('identification_id','=',str(int(line.get('NIK')))),('active','=',True)], limit=1)
                    if not employee_obj:
                        raise ValidationError(('NIK/Identification No %s not found') % (str(int(line.get('NIK')))))
                    else:
                        employee = employee_obj
                        nik = str(int(line.get('NIK')))
                else:
                    nik = ""

                if line.get('Masa Pajak'):
                    masa_pajak = str(int(line.get('Masa Pajak')))
                else:
                    masa_pajak = ""
                
                if line.get('Tahun Pajak'):
                    tahun_pajak_vals = str(int(line.get('Tahun Pajak')))
                    tahun_pajak = tahun_pajak_vals.strip()
                else:
                    tahun_pajak = ""
                
                if line.get('Pembetulan'):
                    pembetulan = str(int(line.get('Pembetulan')))
                else:
                    pembetulan = ""
                
                if line.get('Nomor Bukti Potong'):
                    nomor_bukti_potong = str(line.get('Nomor Bukti Potong'))
                else:
                    nomor_bukti_potong = ""
                
                if line.get('Masa Perolehan Awal'):
                    masa_perolehan_awal = str(int(line.get('Masa Perolehan Awal')))
                else:
                    masa_perolehan_awal = ""
                
                if line.get('Masa Perolehan Akhir'):
                    masa_perolehan_akhir = str(int(line.get('Masa Perolehan Akhir')))
                else:
                    masa_perolehan_akhir = ""
                
                if line.get('NPWP'):
                    npwp = str(int(line.get('NPWP')))
                else:
                    npwp = ""
                
                if line.get('Alamat'):
                    alamat = line.get('Alamat')
                else:
                    alamat = ""
                
                if line.get('Jenis Kelamin'):
                    jenis_kelamin = line.get('Jenis Kelamin')
                else:
                    jenis_kelamin = ""
                
                if line.get('Status PTKP'):
                    status_ptkp = line.get('Status PTKP')
                else:
                    status_ptkp = ""
                
                if line.get('Jumlah Tanggungan'):
                    jumlah_tanggungan = str(int(line.get('Jumlah Tanggungan')))
                else:
                    jumlah_tanggungan = ""
                
                if line.get('Nama Jabatan'):
                    nama_jabatan = line.get('Nama Jabatan')
                else:
                    nama_jabatan = ""
                
                if line.get('WP Luar Negeri'):
                    wp_luar_negeri = line.get('WP Luar Negeri')
                else:
                    wp_luar_negeri = ""
                
                if line.get('Kode Negara'):
                    kode_negara = line.get('Kode Negara')
                else:
                    kode_negara = ""
                
                if line.get('Kode Pajak'):
                    kode_pajak = str(line.get('Kode Pajak'))
                else:
                    kode_pajak = ""
                
                if line.get('Jumlah 1'):
                    jumlah_1 = float(line.get('Jumlah 1'))
                else:
                    jumlah_1 = 0.0
                
                if line.get('Jumlah 2'):
                    jumlah_2 = float(line.get('Jumlah 2'))
                else:
                    jumlah_2 = 0.0
                
                if line.get('Jumlah 3'):
                    jumlah_3 = float(line.get('Jumlah 3'))
                else:
                    jumlah_3 = 0.0
                
                if line.get('Jumlah 4'):
                    jumlah_4 = float(line.get('Jumlah 4'))
                else:
                    jumlah_4 = 0.0
                
                if line.get('Jumlah 5'):
                    jumlah_5 = float(line.get('Jumlah 5'))
                else:
                    jumlah_5 = 0.0
                
                if line.get('Jumlah 6'):
                    jumlah_6 = float(line.get('Jumlah 6'))
                else:
                    jumlah_6 = 0.0
                
                if line.get('Jumlah 7'):
                    jumlah_7 = float(line.get('Jumlah 7'))
                else:
                    jumlah_7 = 0.0
                
                if line.get('Jumlah 8'):
                    jumlah_8 = float(line.get('Jumlah 8'))
                else:
                    jumlah_8 = 0.0
                
                if line.get('Jumlah 9'):
                    jumlah_9 = float(line.get('Jumlah 9'))
                else:
                    jumlah_9 = 0.0
                
                if line.get('Jumlah 10'):
                    jumlah_10 = float(line.get('Jumlah 10'))
                else:
                    jumlah_10 = 0.0
                
                if line.get('Jumlah 11'):
                    jumlah_11 = float(line.get('Jumlah 11'))
                else:
                    jumlah_11 = 0.0
                
                if line.get('Jumlah 12'):
                    jumlah_12 = float(line.get('Jumlah 12'))
                else:
                    jumlah_12 = 0.0
                
                if line.get('Jumlah 13'):
                    jumlah_13 = float(line.get('Jumlah 13'))
                else:
                    jumlah_13 = 0.0
                
                if line.get('Jumlah 14'):
                    jumlah_14 = float(line.get('Jumlah 14'))
                else:
                    jumlah_14 = 0.0
                
                if line.get('Jumlah 15'):
                    jumlah_15 = float(line.get('Jumlah 15'))
                else:
                    jumlah_15 = 0.0
                
                if line.get('Jumlah 16'):
                    jumlah_16 = float(line.get('Jumlah 16'))
                else:
                    jumlah_16 = 0.0
                
                if line.get('Jumlah 17'):
                    jumlah_17 = float(line.get('Jumlah 17'))
                else:
                    jumlah_17 = 0.0
                
                if line.get('Jumlah 18'):
                    jumlah_18 = float(line.get('Jumlah 18'))
                else:
                    jumlah_18 = 0.0
                
                if line.get('Jumlah 19'):
                    jumlah_19 = float(line.get('Jumlah 19'))
                else:
                    jumlah_19 = 0.0
                
                if line.get('Jumlah 20'):
                    jumlah_20 = float(line.get('Jumlah 20'))
                else:
                    jumlah_20 = 0.0
                
                if line.get('Status Pindah'):
                    status_pindah = line.get('Status Pindah')
                else:
                    status_pindah = ""
                
                if line.get('NPWP Pemotong'):
                    npwp_pemotong = str(int(line.get('NPWP Pemotong')))
                else:
                    npwp_pemotong = ""
                
                if line.get('Nama Pemotong'):
                    nama_pemotong = line.get('Nama Pemotong')
                else:
                    nama_pemotong = ""
                
                if line.get('Tanggal Bukti Potong'):
                    tanggal_bukti_potong_vals = xlrd.xldate_as_tuple(line.get('Tanggal Bukti Potong'), workbook.datemode)
                    tanggal_bukti_potong = str(tanggal_bukti_potong_vals[0])+'-'+str(tanggal_bukti_potong_vals[1])+'-'+str(tanggal_bukti_potong_vals[2])
                else:
                    tanggal_bukti_potong = ""
                
                data = {
                    'tipe_bukti_potong': tipe_bukti_potong.id,
                    'masa_pajak': masa_pajak,
                    'tahun_pajak': tahun_pajak,
                    'pembetulan': pembetulan,
                    'nomor_bukti_potong': nomor_bukti_potong,
                    'masa_perolehan_awal': masa_perolehan_awal,
                    'masa_perolehan_akhir': masa_perolehan_akhir,
                    'npwp': npwp,
                    'nik': nik,
                    'employee_id': employee.id,
                    'alamat': alamat,
                    'jenis_kelamin': jenis_kelamin,
                    'status_ptkp': status_ptkp,
                    'jumlah_tanggungan': jumlah_tanggungan,
                    'nama_jabatan': nama_jabatan,
                    'wp_luar_negeri': wp_luar_negeri,
                    'kode_negara': kode_negara,
                    'kode_pajak': kode_pajak,
                    'jumlah_1': jumlah_1,
                    'jumlah_2': jumlah_2,
                    'jumlah_3': jumlah_3,
                    'jumlah_4': jumlah_4,
                    'jumlah_5': jumlah_5,
                    'jumlah_6': jumlah_6,
                    'jumlah_7': jumlah_7,
                    'jumlah_8': jumlah_8,
                    'jumlah_9': jumlah_9,
                    'jumlah_10': jumlah_10,
                    'jumlah_11': jumlah_11,
                    'jumlah_12': jumlah_12,
                    'jumlah_13': jumlah_13,
                    'jumlah_14': jumlah_14,
                    'jumlah_15': jumlah_15,
                    'jumlah_16': jumlah_16,
                    'jumlah_17': jumlah_17,
                    'jumlah_18': jumlah_18,
                    'jumlah_19': jumlah_19,
                    'jumlah_20': jumlah_20,
                    'status_pindah': status_pindah,
                    'npwp_pemotong': npwp_pemotong,
                    'nama_pemotong': nama_pemotong,
                    'tanggal_bukti_potong': tanggal_bukti_potong,
                }
                vals += [data]
        elif self.tipe_bukti_potong and self.tipe_bukti_potong.code == "1721_A2":
            tipe_bukti_potong = self.tipe_bukti_potong

            for row in xls_reader:
                line = dict(zip(keys, row))

                if line.get('NIK'):
                    employee_obj = self.env['hr.employee'].search([('identification_id','=',str(int(line.get('NIK')))),('active','=',True)], limit=1)
                    if not employee_obj:
                        raise ValidationError(('NIK/Identification No %s not found') % (str(int(line.get('NIK')))))
                    else:
                        employee = employee_obj
                        nik = str(int(line.get('NIK')))
                else:
                    nik = ""

                if line.get('Masa Pajak'):
                    masa_pajak = str(int(line.get('Masa Pajak')))
                else:
                    masa_pajak = ""
                
                if line.get('Tahun Pajak'):
                    tahun_pajak_vals = str(int(line.get('Tahun Pajak')))
                    tahun_pajak = tahun_pajak_vals.strip()
                else:
                    tahun_pajak = ""
                
                if line.get('Pembetulan'):
                    pembetulan = str(int(line.get('Pembetulan')))
                else:
                    pembetulan = ""
                
                if line.get('Nomor Bukti Potong'):
                    nomor_bukti_potong = str(line.get('Nomor Bukti Potong'))
                else:
                    nomor_bukti_potong = ""
                
                if line.get('Masa Perolehan Awal'):
                    masa_perolehan_awal = str(int(line.get('Masa Perolehan Awal')))
                else:
                    masa_perolehan_awal = ""
                
                if line.get('Masa Perolehan Akhir'):
                    masa_perolehan_akhir = str(int(line.get('Masa Perolehan Akhir')))
                else:
                    masa_perolehan_akhir = ""
                
                if line.get('NPWP'):
                    npwp = str(int(line.get('NPWP')))
                else:
                    npwp = ""
                
                if line.get('NIP'):
                    nip = str(int(line.get('NIP')))
                else:
                    nip = ""
                
                if line.get('Pangkat'):
                    pangkat = str(line.get('Pangkat'))
                else:
                    pangkat = ""
                
                if line.get('Golongan'):
                    golongan = str(line.get('Golongan'))
                else:
                    golongan = ""
                
                if line.get('Alamat'):
                    alamat = line.get('Alamat')
                else:
                    alamat = ""
                
                if line.get('Jenis Kelamin'):
                    jenis_kelamin = line.get('Jenis Kelamin')
                else:
                    jenis_kelamin = ""
                
                if line.get('Status PTKP'):
                    status_ptkp = line.get('Status PTKP')
                else:
                    status_ptkp = ""
                
                if line.get('Jumlah Tanggungan'):
                    jumlah_tanggungan = str(int(line.get('Jumlah Tanggungan')))
                else:
                    jumlah_tanggungan = ""
                
                if line.get('Nama Jabatan'):
                    nama_jabatan = line.get('Nama Jabatan')
                else:
                    nama_jabatan = ""
                
                if line.get('Kode Pajak'):
                    kode_pajak = line.get('Kode Pajak')
                else:
                    kode_pajak = ""
                
                if line.get('Jumlah 1'):
                    jumlah_1 = float(line.get('Jumlah 1'))
                else:
                    jumlah_1 = 0.0
                
                if line.get('Jumlah 2'):
                    jumlah_2 = float(line.get('Jumlah 2'))
                else:
                    jumlah_2 = 0.0
                
                if line.get('Jumlah 3'):
                    jumlah_3 = float(line.get('Jumlah 3'))
                else:
                    jumlah_3 = 0.0
                
                if line.get('Jumlah 4'):
                    jumlah_4 = float(line.get('Jumlah 4'))
                else:
                    jumlah_4 = 0.0
                
                if line.get('Jumlah 5'):
                    jumlah_5 = float(line.get('Jumlah 5'))
                else:
                    jumlah_5 = 0.0
                
                if line.get('Jumlah 6'):
                    jumlah_6 = float(line.get('Jumlah 6'))
                else:
                    jumlah_6 = 0.0
                
                if line.get('Jumlah 7'):
                    jumlah_7 = float(line.get('Jumlah 7'))
                else:
                    jumlah_7 = 0.0
                
                if line.get('Jumlah 8'):
                    jumlah_8 = float(line.get('Jumlah 8'))
                else:
                    jumlah_8 = 0.0
                
                if line.get('Jumlah 9'):
                    jumlah_9 = float(line.get('Jumlah 9'))
                else:
                    jumlah_9 = 0.0
                
                if line.get('Jumlah 10'):
                    jumlah_10 = float(line.get('Jumlah 10'))
                else:
                    jumlah_10 = 0.0
                
                if line.get('Jumlah 11'):
                    jumlah_11 = float(line.get('Jumlah 11'))
                else:
                    jumlah_11 = 0.0
                
                if line.get('Jumlah 12'):
                    jumlah_12 = float(line.get('Jumlah 12'))
                else:
                    jumlah_12 = 0.0
                
                if line.get('Jumlah 13'):
                    jumlah_13 = float(line.get('Jumlah 13'))
                else:
                    jumlah_13 = 0.0
                
                if line.get('Jumlah 14'):
                    jumlah_14 = float(line.get('Jumlah 14'))
                else:
                    jumlah_14 = 0.0
                
                if line.get('Jumlah 15'):
                    jumlah_15 = float(line.get('Jumlah 15'))
                else:
                    jumlah_15 = 0.0
                
                if line.get('Jumlah 16'):
                    jumlah_16 = float(line.get('Jumlah 16'))
                else:
                    jumlah_16 = 0.0
                
                if line.get('Jumlah 17'):
                    jumlah_17 = float(line.get('Jumlah 17'))
                else:
                    jumlah_17 = 0.0
                
                if line.get('Jumlah 18'):
                    jumlah_18 = float(line.get('Jumlah 18'))
                else:
                    jumlah_18 = 0.0
                
                if line.get('Jumlah 19'):
                    jumlah_19 = float(line.get('Jumlah 19'))
                else:
                    jumlah_19 = 0.0
                
                if line.get('Jumlah 20'):
                    jumlah_20 = float(line.get('Jumlah 20'))
                else:
                    jumlah_20 = 0.0
                
                if line.get('Jumlah 21'):
                    jumlah_21 = float(line.get('Jumlah 21'))
                else:
                    jumlah_21 = 0.0
                
                if line.get('Jumlah 22'):
                    jumlah_22 = float(line.get('Jumlah 22'))
                else:
                    jumlah_22 = 0.0
                
                if line.get('Jumlah 23'):
                    jumlah_23 = float(line.get('Jumlah 23'))
                else:
                    jumlah_23 = 0.0
                
                if line.get('Jumlah 23a'):
                    jumlah_23a = float(line.get('Jumlah 23a'))
                else:
                    jumlah_23a = 0.0
                
                if line.get('Jumlah 23b'):
                    jumlah_23b = float(line.get('Jumlah 23b'))
                else:
                    jumlah_23b = 0.0
                
                if line.get('Status Pindah'):
                    status_pindah = line.get('Status Pindah')
                else:
                    status_pindah = ""
                
                if line.get('NPWP Pemotong'):
                    npwp_pemotong = str(int(line.get('NPWP Pemotong')))
                else:
                    npwp_pemotong = ""
                
                if line.get('Nama Pemotong'):
                    nama_pemotong = line.get('Nama Pemotong')
                else:
                    nama_pemotong = ""
                
                if line.get('Tanggal Bukti Potong'):
                    tanggal_bukti_potong_vals = xlrd.xldate_as_tuple(line.get('Tanggal Bukti Potong'), workbook.datemode)
                    tanggal_bukti_potong = str(tanggal_bukti_potong_vals[0])+'-'+str(tanggal_bukti_potong_vals[1])+'-'+str(tanggal_bukti_potong_vals[2])
                else:
                    tanggal_bukti_potong = ""
                
                if line.get('Instansi Pemotong'):
                    instansi_pemotong = line.get('Instansi Pemotong')
                else:
                    instansi_pemotong = ""
                
                if line.get('NIP Pemotong'):
                    nip_pemotong = str(int(line.get('NIP Pemotong')))
                else:
                    nip_pemotong = ""
                
                data = {
                    'tipe_bukti_potong': tipe_bukti_potong.id,
                    'masa_pajak': masa_pajak,
                    'tahun_pajak': tahun_pajak,
                    'pembetulan': pembetulan,
                    'nomor_bukti_potong': nomor_bukti_potong,
                    'masa_perolehan_awal': masa_perolehan_awal,
                    'masa_perolehan_akhir': masa_perolehan_akhir,
                    'npwp': npwp,
                    'nip': nip,
                    'nik': nik,
                    'employee_id': employee.id,
                    'pangkat': pangkat,
                    'golongan': golongan,
                    'alamat': alamat,
                    'jenis_kelamin': jenis_kelamin,
                    'status_ptkp': status_ptkp,
                    'jumlah_tanggungan': jumlah_tanggungan,
                    'nama_jabatan': nama_jabatan,
                    'kode_pajak': kode_pajak,
                    'jumlah_1': jumlah_1,
                    'jumlah_2': jumlah_2,
                    'jumlah_3': jumlah_3,
                    'jumlah_4': jumlah_4,
                    'jumlah_5': jumlah_5,
                    'jumlah_6': jumlah_6,
                    'jumlah_7': jumlah_7,
                    'jumlah_8': jumlah_8,
                    'jumlah_9': jumlah_9,
                    'jumlah_10': jumlah_10,
                    'jumlah_11': jumlah_11,
                    'jumlah_12': jumlah_12,
                    'jumlah_13': jumlah_13,
                    'jumlah_14': jumlah_14,
                    'jumlah_15': jumlah_15,
                    'jumlah_16': jumlah_16,
                    'jumlah_17': jumlah_17,
                    'jumlah_18': jumlah_18,
                    'jumlah_19': jumlah_19,
                    'jumlah_20': jumlah_20,
                    'jumlah_21': jumlah_21,
                    'jumlah_22': jumlah_22,
                    'jumlah_23': jumlah_23,
                    'jumlah_23a': jumlah_23a,
                    'jumlah_23b': jumlah_23b,
                    'status_pindah': status_pindah,
                    'npwp_pemotong': npwp_pemotong,
                    'nama_pemotong': nama_pemotong,
                    'tanggal_bukti_potong': tanggal_bukti_potong,
                    'instansi_pemotong': instansi_pemotong,
                    'nip_pemotong': nip_pemotong,
                }
                vals += [data]
        for rec in vals:
            check_bukti_potong = self.env['hr.bukti.potong'].search([('employee_id','=',rec['employee_id']),('tahun_pajak','=',rec['tahun_pajak'])])
            if not check_bukti_potong:
                self.env['hr.bukti.potong'].create(rec)
        
        return {
                'name': _('Bukti Potong 1721 A1/A2'),
                'domain': [],
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'hr.bukti.potong',
                'view_id': False,
                'views': [(self.env.ref('equip3_hr_payroll_extend_id.view_hr_bukti_potong_tree').id, 'tree'),(self.env.ref('equip3_hr_payroll_extend_id.view_hr_bukti_potong_form').id, 'form')],
                'type': 'ir.actions.act_window'
               }
                