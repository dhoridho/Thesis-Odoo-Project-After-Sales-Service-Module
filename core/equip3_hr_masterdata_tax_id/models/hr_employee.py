from odoo import _, api, fields, models
from datetime import datetime
from odoo.exceptions import ValidationError


class HashmicroHREmployeeInherit(models.Model):
    _inherit = 'hr.employee'
    
    @api.model
    def _multi_company_domain(self):
        return [('company_id','=', self.env.company.id)]
    
    ptkp_id = fields.Many2one('hr.tax.ptkp', string="PTKP",domain=_multi_company_domain)
    kpp_id = fields.Many2one('hr.tax.kpp', string="KPP Company")
    bpjs_ketenagakerjaan_no = fields.Char(string="BPJS Ketenagakerjaan No")
    bpjs_ketenagakerjaan_date = fields.Date(string="BPJS Ketenagakerjaan Date")
    bpjs_kesehatan_no = fields.Char(string="BPJS Kesehatan No")
    bpjs_kesehatan_date = fields.Date(string="BPJS Kesehatan Date")
    have_npwp = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], default='yes', string='Have NPWP ?')
    npwp_no = fields.Char(string="NPWP No")
    # employee_tax_status = fields.Selection(
    #     [('pegawai_tetap', 'Pegawai Tetap'), ('pegawai_tidak_tetap', 'Pegawai Tidak Tetap'),
    #      ('pegawai_harian_lepas', 'Pegawai Harian Lepas')], string='Employee Tax Status')
    employee_tax_status = fields.Selection(
        [('pegawai_tetap', 'Pegawai Tetap'), ('pegawai_tidak_tetap', 'Pegawai Tidak Tetap / Harian Lepas')],
        string='Employee Tax Status', default='pegawai_tetap')
    employee_payment_method = fields.Selection(
        [('paid_monthly', 'Dibayar Bulanan'), ('non_paid_monthly', 'Tidak Dibayar Bulanan (Harian, Mingguan, Satuan atau Borongan)')],
        string='Employee Payment Method', default='paid_monthly')
    tax_calculation_method = fields.Selection(
        [('gross', 'Gross'), ('gross_up', 'Gross-Up'),
         ('nett', 'Nett'), ('mix', 'Mix')], string='Tax Calculation Method', default='gross')
    country_domicile_code = fields.Many2one('country.domicile.code', string='Country Domicile Code')
    employee_tax_category = fields.Selection(
        [('non_pns', 'Non PNS'), ('pns', 'PNS')], default='non_pns', string='Employee Tax Category')
    is_expatriate = fields.Boolean('Is Expatriate', default=False)
    expatriate_tax = fields.Selection(
        [('pph21', 'PPh 21'), ('pph26', 'PPh 26')], string='Expatriate Tax')
    is_tax_treaty = fields.Boolean('Is Tax Treaty', default=False)

    @api.onchange('country_id')
    def _onchange_country_id(self):
        for res in self:
            country = self.env['country.domicile.code'].search([('country_id', '=', res.country_id.id)], limit=1)
            if country:
                res.country_domicile_code = country.id
            else:
                res.country_domicile_code = False

    @api.onchange('location_id')
    def onchange_location_id(self):
        for rec in self:
            rec.kpp_id = rec.location_id.kpp_id.id

    @api.onchange('identification_id')
    def onchange_identification_id(self):
        for rec in self:
            if rec.have_npwp == "yes":
                rec.npwp_no = rec.identification_id
    
    @api.onchange('have_npwp')
    def onchange_have_npwp(self):
        for rec in self:
            if rec.have_npwp == "yes":
                rec.npwp_no = rec.identification_id
            else:
                rec.npwp_no = ""

class WorkLocationObject(models.Model):
    _inherit = 'work.location.object'

    kpp_id = fields.Many2one('hr.tax.kpp', string='KPP', required=True)