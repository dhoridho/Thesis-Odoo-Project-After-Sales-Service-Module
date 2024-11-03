from odoo import api, fields, models, _

class HREmployeeChangeRequest(models.Model):
    _inherit = 'hr.employee.change.request'

    ## Citizenship ##
    country_domicile_code = fields.Many2one('country.domicile.code', string='Country Domicile Code')
    ## BPJS Information ##
    bpjs_ketenagakerjaan_no = fields.Char('BPJS Ketenagakerjaan No')
    bpjs_ketenagakerjaan_date = fields.Date('BPJS Ketenagakerjaan Date')
    bpjs_kesehatan_no = fields.Char('BPJS Kesehatan No')
    bpjs_kesehatan_date = fields.Date('BPJS Kesehatan Date')
    ## Tax Information ##
    is_expatriate = fields.Boolean('Is Expatriate', default=False)
    expatriate_tax = fields.Selection(
        [('pph21', 'PPh 21'), ('pph26', 'PPh 26')], string='Expatriate Tax')
    is_tax_treaty = fields.Boolean('Is Tax Treaty', default=False)
    have_npwp = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], default='yes', string='Have NPWP ?')
    npwp_no = fields.Char(string="NPWP No")
    employee_tax_category = fields.Selection(
        [('non_pns', 'Non PNS'), ('pns', 'PNS')], default='non_pns', string='Employee Tax Category')
    employee_tax_status = fields.Selection(
        [('pegawai_tetap', 'Pegawai Tetap'), ('pegawai_tidak_tetap', 'Pegawai Tidak Tetap / Harian Lepas')],
        string='Employee Tax Status')
    tax_calculation_method = fields.Selection(related='employee_id.tax_calculation_method', string='Tax Calculation Method')
    ptkp_id = fields.Many2one('hr.tax.ptkp', string="PTKP")
    kpp_id = fields.Many2one('hr.tax.kpp', string="KPP")

    @api.onchange('country_id')
    def _onchange_country_id(self):
        for res in self:
            country = self.env['country.domicile.code'].search([('country_id', '=', res.country_id.id)], limit=1)
            if country:
                res.country_domicile_code = country.id
            else:
                res.country_domicile_code = False
    
    @api.onchange('employee_id')
    def onchange_employee(self):
        res = super(HREmployeeChangeRequest, self).onchange_employee()
        if self.employee_id:
            self.country_domicile_code = self.employee_id.country_domicile_code.id or False
            self.bpjs_ketenagakerjaan_no = self.employee_id.bpjs_ketenagakerjaan_no
            self.bpjs_ketenagakerjaan_date = self.employee_id.bpjs_ketenagakerjaan_date
            self.bpjs_kesehatan_no = self.employee_id.bpjs_kesehatan_no
            self.bpjs_kesehatan_date = self.employee_id.bpjs_kesehatan_date
            self.is_expatriate = self.employee_id.is_expatriate
            self.expatriate_tax = self.employee_id.expatriate_tax
            self.is_tax_treaty = self.employee_id.is_tax_treaty
            self.have_npwp = self.employee_id.have_npwp
            self.npwp_no = self.employee_id.npwp_no
            self.employee_tax_category = self.employee_id.employee_tax_category
            self.employee_tax_status = self.employee_id.employee_tax_status
            self.ptkp_id = self.employee_id.ptkp_id.id or False
            self.kpp_id = self.employee_id.kpp_id.id or False
        return res
    
    def confirm(self):
        res = super(HREmployeeChangeRequest, self).confirm()
        for rec in self:
            data_changes = []
            if rec.employee_id.country_domicile_code != rec.country_domicile_code:
                name_field = self._fields['country_domicile_code'].string
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': rec.employee_id.country_domicile_code.name,
                                            'after': rec.country_domicile_code.name}))
                                                                    
            if rec.employee_id.bpjs_ketenagakerjaan_no != rec.bpjs_ketenagakerjaan_no:
                name_field = self._fields['bpjs_ketenagakerjaan_no'].string
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': rec.employee_id.bpjs_ketenagakerjaan_no,
                                            'after': rec.bpjs_ketenagakerjaan_no}))
                                                                    
            if rec.employee_id.bpjs_ketenagakerjaan_date != rec.bpjs_ketenagakerjaan_date:
                name_field = self._fields['bpjs_ketenagakerjaan_date'].string
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': rec.employee_id.bpjs_ketenagakerjaan_date,
                                            'after': rec.bpjs_ketenagakerjaan_date}))
                                                                    
            if rec.employee_id.bpjs_kesehatan_no != rec.bpjs_kesehatan_no:
                name_field = self._fields['bpjs_kesehatan_no'].string
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': rec.employee_id.bpjs_kesehatan_no,
                                            'after': rec.bpjs_kesehatan_no}))
                                                                    
            if rec.employee_id.bpjs_kesehatan_date != rec.bpjs_kesehatan_date:
                name_field = self._fields['bpjs_kesehatan_date'].string
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': rec.employee_id.bpjs_kesehatan_date,
                                            'after': rec.bpjs_kesehatan_date}))
                                                                    
            if rec.employee_id.is_expatriate != rec.is_expatriate:
                name_field = self._fields['is_expatriate'].string
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': rec.employee_id.is_expatriate,
                                            'after': rec.is_expatriate}))
                                                                    
            if rec.employee_id.expatriate_tax != rec.expatriate_tax:
                name_field = self._fields['expatriate_tax'].string
                if rec.employee_id.expatriate_tax:
                    before = dict(self.env['hr.employee'].fields_get(allfields=['expatriate_tax'])['expatriate_tax']['selection'])[rec.employee_id.expatriate_tax]
                else:
                    before = ''
                after = dict(self.fields_get(allfields=['expatriate_tax'])['expatriate_tax']['selection'])[rec.expatriate_tax]
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': before,
                                            'after': after}))
                                                                    
            if rec.employee_id.is_tax_treaty != rec.is_tax_treaty:
                name_field = self._fields['is_tax_treaty'].string
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': rec.employee_id.is_tax_treaty,
                                            'after': rec.is_tax_treaty}))
                                                                    
            if rec.employee_id.have_npwp != rec.have_npwp:
                name_field = self._fields['have_npwp'].string
                before = dict(self.env['hr.employee'].fields_get(allfields=['have_npwp'])['have_npwp']['selection'])[rec.employee_id.have_npwp]
                after = dict(self.fields_get(allfields=['have_npwp'])['have_npwp']['selection'])[rec.have_npwp]
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': before,
                                            'after': after}))
                                                                    
            if rec.employee_id.npwp_no != rec.npwp_no:
                name_field = self._fields['npwp_no'].string
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': rec.employee_id.npwp_no,
                                            'after': rec.npwp_no}))
                                                                    
            if rec.employee_id.employee_tax_category != rec.employee_tax_category:
                name_field = self._fields['employee_tax_category'].string
                before = dict(self.env['hr.employee'].fields_get(allfields=['employee_tax_category'])['employee_tax_category']['selection'])[rec.employee_id.employee_tax_category]
                after = dict(self.fields_get(allfields=['employee_tax_category'])['employee_tax_category']['selection'])[rec.employee_tax_category]
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': before,
                                            'after': after}))
                                                                    
            if rec.employee_id.employee_tax_status != rec.employee_tax_status:
                name_field = self._fields['employee_tax_status'].string
                before = dict(self.env['hr.employee'].fields_get(allfields=['employee_tax_status'])['employee_tax_status']['selection'])[rec.employee_id.employee_tax_status]
                after = dict(self.fields_get(allfields=['employee_tax_status'])['employee_tax_status']['selection'])[rec.employee_tax_status]
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': before,
                                            'after': after}))
                                                                    
            if rec.employee_id.ptkp_id != rec.ptkp_id:
                name_field = self._fields['ptkp_id'].string
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': rec.employee_id.ptkp_id.ptkp_name,
                                            'after': rec.ptkp_id.ptkp_name}))
                                                                    
            if rec.employee_id.kpp_id != rec.kpp_id:
                name_field = self._fields['kpp_id'].string
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': rec.employee_id.kpp_id.name,
                                            'after': rec.kpp_id.name}))
                                                                    
            rec.change_request_line_ids = data_changes
        return res
    
    def prepare_data_employee(self):
        res = super(HREmployeeChangeRequest, self).prepare_data_employee()
        res.update({'country_domicile_code': self.country_domicile_code.id or False,
                    'bpjs_ketenagakerjaan_no': self.bpjs_ketenagakerjaan_no,
                    'bpjs_ketenagakerjaan_date': self.bpjs_ketenagakerjaan_date,
                    'bpjs_kesehatan_no': self.bpjs_kesehatan_no,
                    'bpjs_kesehatan_date': self.bpjs_kesehatan_date,
                    'is_expatriate': self.is_expatriate,
                    'expatriate_tax': self.expatriate_tax,
                    'is_tax_treaty': self.is_tax_treaty,
                    'have_npwp': self.have_npwp,
                    'npwp_no': self.npwp_no,
                    'employee_tax_category': self.employee_tax_category,
                    'employee_tax_status': self.employee_tax_status,
                    'ptkp_id': self.ptkp_id.id or False,
                    'kpp_id': self.kpp_id.id or False}
                    )
        return res