# -*- coding: utf-8 -*-
import calendar
import babel
from odoo import models, fields, api, tools, _
import math
from odoo.addons import decimal_precision as dp
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
from pytz import timezone, utc
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
from odoo.exceptions import UserError, ValidationError, Warning
import pytz

def timezone_datetime(time):
    if not time.tzinfo:
        time = time.replace(tzinfo=utc)
    return time

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, "%s" % (rec.number)))
        return res

    # def _domain_employee(self):
    #     cotract_obj = self.env['hr.contract'].search([('state', '=', 'open')])
    #     employee_obj = self.env['hr.employee'].search([('contract_ids', '!=', False), ('contract_ids', 'in', cotract_obj.ids)])
    #
    #     if employee_obj:
    #         domain = [('id', 'in', employee_obj.ids)]
    #     else:
    #         domain = [('id', '=', -1)]
    #     return domain

    @api.depends('payslip_pesangon')
    def _compute_allowed_employee_ids(self):
        for rec in self:
            if rec.payslip_pesangon == False:
                cotract_obj = self.env['hr.contract'].search([('state', 'in', ['open','close'])])
            else:
                transition_category = self.env['career.transition.category'].search([('name', '=', 'Termination')], limit=1)
                transition_type = self.env['career.transition.type'].search([('name', 'in', ['Termination', 'Pension'])])
                career_transition_type = [x.id for x in transition_type]
                pesangon_term = self.env['hr.career.transition'].search(
                    [('status', '=', 'approve'),
                     ('transition_category_id', '=', transition_category.id),
                     ('career_transition_type', 'in', career_transition_type)], order="id DESC")
                pesangon_term_array = [x.id for x in pesangon_term]
                cotract_obj = self.env['hr.contract'].search([('state', 'in', ['open', 'close']), ('career_transition_id', 'in', pesangon_term_array)], order="id DESC")
            if cotract_obj:
                rec.allowed_employee_ids = self.env['hr.employee'].search([('contract_ids', '!=', False), ('contract_ids', 'in', cotract_obj.ids),('company_id','=',self.company_id.id)])
            else:
                rec.allowed_employee_ids = self.env['hr.employee'].search([('id', '=', -1),('company_id','=',self.company_id.id)])

    allowed_employee_ids = fields.Many2many('hr.employee', compute='_compute_allowed_employee_ids')
    # employee_id = fields.Many2one('hr.employee', string='Employee', required=True, readonly=True, help="Employee",
    #                               states={'draft': [('readonly', False)]}, domain=_domain_employee)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, readonly=True, help="Employee",
                                  states={'draft': [('readonly', False)]}, domain="[('id', 'in', allowed_employee_ids)]")
    payslip_period_id = fields.Many2one('hr.payslip.period', string='Payslip Period', domain="[('state','=','open')]")
    period_tax_calculation_method = fields.Selection(related="payslip_period_id.tax_calculation_method", string='Period Tax Calculation Method')
    payslip_report_date = fields.Date(string='Payslip Report Date', readonly=True)
    month = fields.Many2one('hr.payslip.period.line', string="Month", domain="[('period_id','=',payslip_period_id)]")
    month_name = fields.Char('Month Name', readonly=True)
    year = fields.Char('Year', readonly=True)
    department_id = fields.Many2one('hr.department', string="Department")
    job_id = fields.Many2one('hr.job', string="Job Position")
    is_expatriate = fields.Boolean('Is Expatriate', readonly=True)
    expatriate_tax = fields.Char(string='Expatriate Tax', readonly=True)
    employee_tax_status = fields.Char('Employee Tax Status', readonly=True)
    emp_tax_status = fields.Selection(
        [('pegawai_tetap', 'Pegawai Tetap'), ('pegawai_tidak_tetap', 'Pegawai Tidak Tetap / Harian Lepas')],
        string='Employee Tax Status', readonly=True)
    employee_payment_method = fields.Selection(
        [('paid_monthly', 'Dibayar Bulanan'), ('non_paid_monthly', 'Tidak Dibayar Bulanan (Harian, Mingguan, Satuan atau Borongan)')],
        string='Employee Payment Method', readonly=True)
    npwp = fields.Char('NPWP', readonly=True)
    kpp_id = fields.Many2one('hr.tax.kpp', string="KPP", readonly=True)
    kpp = fields.Char('KPP', readonly=True)
    ptkp_id = fields.Many2one('hr.tax.ptkp', string="PTKP", readonly=True)
    ptkp = fields.Char('PTKP', readonly=True)
    tax_calculation_method = fields.Char('Tax Calculation Method', readonly=True)
    tax_period_length = fields.Integer('Tax Period Length', default=1, readonly=True)
    tax_end_month = fields.Integer('Tax End Month', default=12, readonly=True)
    income_reguler_ids = fields.One2many('hr.payslip.tax.calculation', 'slip_id', string='Income Reguler', readonly=True,
                               domain=[('tax_category', '=', 'income_reguler')], states={'draft': [('readonly', False)]})
    income_irreguler_ids = fields.One2many('hr.payslip.tax.calculation', 'slip_id', string='Income Irreguler',
                                           domain=[('tax_category', '=', 'income_irreguler')], readonly=True, states={'draft': [('readonly', False)]})
    deduction_ids = fields.One2many('hr.payslip.tax.calculation', 'slip_id', string='Deduction',
                                           domain=[('tax_category', '=', 'deduction')], readonly=True, states={'draft': [('readonly', False)]})
    akum_income = fields.Float('Akumulasi Income Reguler', help='Akumulasi Reguler Income Gross up', compute='_amount_akum_income', store=True)
    akum_income_last_month = fields.Float('Akumulasi Income Reguler Bulan Sebelumnya', default=0)
    akum_thn = fields.Float('Akumulasi Income Reguler Disetahunkan', help='Akumulasi Income Reguler Gross up Disetahunkan', compute='_amount_akum_thn', store=True)
    akum_irreguler = fields.Float('Akumulasi Income Irreguler', help='Akumulasi Income Irreguler Gross up', compute='_amount_akum_irreguler', store=True)
    akum_irreguler_last_month = fields.Float('Akumulasi Income Irreguler Bulan Sebelumnya', default=0)
    bruto = fields.Float('Bruto', help='Jumlah Bruto Gross Up', compute='_amount_bruto', store=True)
    biaya_jab = fields.Float('Biaya Jabatan Reguler', help='Biaya Jabatan Reguler Gross up', compute='_amount_biaya_jab', store=True)
    biaya_jab_month_reg = fields.Float('Biaya Jabatan Month Reguler', help='Biaya Jabatan Month Reguler Gross Up', compute='_amount_biaya_jab_month_reg', store=True)
    biaya_jab_irreguler = fields.Float('Biaya Jabatan Irreguler', help='Biaya Jabatan Irreguler Gross up', compute='_amount_biaya_jab_irreguler', store=True)
    akum_ded = fields.Float('Akumulasi Deduction', help='Akumulasi Deduction Gross up', compute='_amount_akum_ded', store=True)
    akum_ded_last_month = fields.Float('Akumulasi Deduction Bulan Sebelumnya', default=0)
    akum_ded_thn = fields.Float('Akumulasi Deduction Disetahunkan', compute='_amount_akum_ded_thn', store=True)
    total_peng_reguler = fields.Float('Total Pengurang Reguler', compute='_amount_total_peng_reguler', store=True)
    total_peng_irreguler = fields.Float('Total Pengurang Irreguler', compute='_amount_total_peng_irreguler', store=True)
    peng_thn_reguler = fields.Float('Penghasilan Disetahunakan Reguler', help='Penghasilan Disetahunakan Reguler Gross up', compute='_amount_peng_thn_reguler', store=True)
    peng_ptkp = fields.Float('Penghasilan Tidak Kena Pajak (PTKP)', compute='_amount_peng_ptkp', store=True)
    peng_kena_pjk_reguler = fields.Float('Penghasilan Kena Pajak Reguler', help='Penghasilan Kena Pajak Reguler Gross up', compute='_amount_peng_kena_pjk_reguler', store=True)
    peng_thn_irreguler = fields.Float('Penghasilan Disetahunakan Irreguler', help='Penghasilan Disetahunakan Irreguler Gross up', compute='_amount_peng_thn_irreguler', store=True)
    peng_kena_pjk_irreguler = fields.Float('Penghasilan Kena Pajak Irreguler', help='Penghasilan Kena Pajak Irreguler Gross up', compute='_amount_peng_kena_pjk_irreguler', store=True)
    pjk_thn_reguler = fields.Float('Pajak Disetahunkan Reguler', help='Pajak Disetahunkan Reguler Gross up', compute='_amount_pjk_thn_reguler', store=True)
    pjk_thn_irreguler = fields.Float('Pajak Disetahunkan Irreguler', help='Pajak Disetahunkan Irreguler Gross up', compute='_amount_pjk_thn_irreguler', store=True)
    pjk_terhutang_reguler = fields.Float('Pajak Terhutang Reguler', help='Pajak Terhutang Reguler Gross up', compute='_amount_pjk_terhutang_reguler', store=True)
    pjk_terhutang_irreguler = fields.Float('Pajak Terhutang Irreguler', help='Pajak Terhutang Irreguler Gross up', compute='_amount_pjk_terhutang_irreguler', store=True)
    # tunj_pjk_reguler = fields.Float('Tunjangan Pajak Reguler', compute='_amount_tunj_pjk_reguler', store=True)
    # tunj_pjk_irreguler = fields.Float('Tunjangan Pajak Irreguler', compute='_amount_tunj_pjk_irreguler', store=True)
    tunj_pjk_reguler = fields.Float('Tunjangan Pajak Reguler', readonly=True, default=0)
    tunj_pjk_irreguler = fields.Float('Tunjangan Pajak Irreguler', readonly=True, default=0)
    pjk_terhutang_reguler_last_month = fields.Float('Akumulasi Pajak Reguler Bulan Sebelumnya', default=0)
    pjk_terhutang_irreguler_last_month = fields.Float('Akumulasi Pajak Irreguler Bulan Sebelumnya', default=0)
    pjk_bln_reguler = fields.Float('Pajak Perbulan Reguler', compute='_amount_pjk_bln_reguler', store=True)
    pjk_bln_irreguler = fields.Float('Pajak Perbulan Irreguler', compute='_amount_pjk_bln_irreguler', store=True)
    pjk_pph26 = fields.Float('Pajak PPh26', compute='_amount_pjk_pph26', store=True)
    late_deduction_ids = fields.One2many('hr.payslip.late.deduction', 'slip_id', string='Late Deduction', readonly=True,
                                    states={'draft': [('readonly', False)]})
    total_late_amount = fields.Float('Total Late Amount', compute='_total_late_amount', store=True)
    send_email_flag = fields.Boolean('Send Email', default=False)
    allow_send_email = fields.Boolean('Allow Send Email', compute='_allow_send_email')
    count_payslip_type = fields.Boolean('Payslip Type', compute='_compute_payslip_type')
    count_bonus_payslip_type = fields.Boolean('Bonus Payslip Type', compute='_compute_payslip_type')
    count_thr_payslip_type = fields.Boolean('THR Payslip Type', compute='_compute_payslip_type')
    termination = fields.Boolean('Termination', readonly=True)
    termination_date = fields.Date(string='Termination Date', readonly=True)
    kelebihan_pajak = fields.Float(string='Kelebihan Pajak', readonly=True, default=0)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id.id)
    state = fields.Selection(selection_add=[('refund', 'Refund')])
    refund_reference = fields.Many2one('hr.payslip', string='Refund Reference', readonly=True)
    hide_button_refund = fields.Boolean('Hide Button Refund', compute='_compute_button_refund')
    payslip_pesangon = fields.Boolean('Payslip Pesangon', default=False)
    date_of_joining = fields.Date(string='Joined Date', compute='compute_date_of_joining', store=True, readonly=True)
    years_of_service = fields.Integer(string="Years of Service", compute='compute_year_of_service', store=True)
    months_of_service = fields.Integer(compute='compute_year_of_service', store=True)
    days_of_service = fields.Integer(compute='compute_year_of_service', store=True)
    masa_kerja = fields.Integer(compute='compute_year_of_service', store=True)
    payment_type = fields.Selection([('full_payment', 'Full Payment'), ('partial_payment', 'Partial Payment')],
                                    default='full_payment', string='Payment Type')
    pesangon = fields.Float('Pesangon', help='Pesangon', compute='_amount_pesangon', store=True)
    upmk = fields.Float('UPMK', help='UPMK', compute='_amount_upmk', store=True)
    bruto_pesangon = fields.Float('Bruto Pesangon', help='Bruto Pesangon', compute='_amount_bruto_pesangon', store=True)
    pph21_pesangon = fields.Float('PPh21 Pesangon', help='PPh21 Pesangon', compute='_amount_pph21_pesangon', store=True)
    pph21_pesangon_ids = fields.One2many('hr.payslip.tax.pesangon', 'slip_id', string='Tax Pesangon Table',
                                         compute='compute_pph21_pesangon', store=True)
    pph21_reguler_ids = fields.One2many('hr.payslip.tax.reguler', 'slip_id', string='Tax Reguler Table',
                                         compute='compute_pph21_reguler', store=True)
    pph21_irreguler_ids = fields.One2many('hr.payslip.tax.irreguler', 'slip_id', string='Tax Irreguler Table',
                                        compute='compute_pph21_irreguler', store=True)
    pph21_reguler_gross_ids = fields.One2many('hr.payslip.tax.reguler.gross', 'slip_id', string='Tax Reguler Table',
                                         compute='compute_pph21_reguler', store=True)
    pph21_irreguler_gross_ids = fields.One2many('hr.payslip.tax.irreguler.gross', 'slip_id', string='Tax Irreguler Table',
                                        compute='compute_pph21_irreguler', store=True)
    rapel_amount = fields.Float('Rapel Amount', readonly=True, default=0)
    neto_masa_sebelumnya = fields.Float('Neto Masa Sebelumnya', compute='compute_neto_masa_sebelumnya', store=True)
    
    ## tax calculation gross/nett ##
    akum_income_gross = fields.Float('Akumulasi Income Reguler Gross', help='Akumulasi Reguler Income Gross', compute='_amount_akum_income_gross', store=True)
    akum_income_last_month_gross = fields.Float('Akumulasi Income Reguler Gross Bulan Sebelumnya', default=0)
    akum_thn_gross = fields.Float('Akumulasi Income Reguler Disetahunkan Gross', help='Akumulasi Income Reguler Gross Disetahunkan', compute='_amount_akum_thn_gross', store=True)
    akum_irreguler_gross = fields.Float('Akumulasi Income Irreguler Gross', help='Akumulasi Income Irreguler Gross', compute='_amount_akum_irreguler_gross', store=True)
    akum_irreguler_last_month_gross = fields.Float('Akumulasi Income Irreguler Gross Bulan Sebelumnya', default=0)
    bruto_gross = fields.Float('Bruto', help='Jumlah Bruto Gross', compute='_amount_bruto_gross', store=True)
    biaya_jab_gross = fields.Float('Biaya Jabatan Reguler Gross', help='Biaya Jabatan Reguler Gross', compute='_amount_biaya_jab_gross', store=True)
    biaya_jab_month_reg_gross = fields.Float('Biaya Jabatan Month Reguler Gross', help='Biaya Jabatan Month Reguler Gross', compute='_amount_biaya_jab_month_reg_gross', store=True)
    biaya_jab_irreguler_gross = fields.Float('Biaya Jabatan Irreguler Gross', help='Biaya Jabatan Irreguler Gross', compute='_amount_biaya_jab_irreguler_gross', store=True)
    akum_ded_gross = fields.Float('Akumulasi Deduction Gross', help='Akumulasi Deduction Gross', compute='_amount_akum_ded_gross', store=True)
    akum_ded_last_month_gross = fields.Float('Akumulasi Deduction Bulan Sebelumnya Gross', default=0)
    akum_ded_thn_gross = fields.Float('Akumulasi Deduction Disetahunkan Gross', compute='_amount_akum_ded_thn_gross', store=True)
    total_peng_reguler_gross = fields.Float('Total Pengurang Reguler Gross', compute='_amount_total_peng_reguler_gross', store=True)
    total_peng_irreguler_gross = fields.Float('Total Pengurang Irreguler Gross', compute='_amount_total_peng_irreguler_gross', store=True)
    peng_thn_reguler_gross = fields.Float('Penghasilan Disetahunakan Reguler Gross', help='Penghasilan Disetahunakan Reguler Gross', compute='_amount_peng_thn_reguler_gross', store=True)
    peng_kena_pjk_reguler_gross = fields.Float('Penghasilan Kena Pajak Reguler Gross', help='Penghasilan Kena Pajak Reguler Gross', compute='_amount_peng_kena_pjk_reguler_gross', store=True)
    peng_thn_irreguler_gross = fields.Float('Penghasilan Disetahunakan Irreguler Gross', help='Penghasilan Disetahunakan Irreguler Gross', compute='_amount_peng_thn_irreguler_gross', store=True)
    peng_kena_pjk_irreguler_gross = fields.Float('Penghasilan Kena Pajak Irreguler Gross', help='Penghasilan Kena Pajak Irreguler Gross', compute='_amount_peng_kena_pjk_irreguler_gross', store=True)
    pjk_thn_reguler_gross = fields.Float('Pajak Disetahunkan Reguler Gross', help='Pajak Disetahunkan Reguler Gross', compute='_amount_pjk_thn_reguler_gross', store=True)
    pjk_thn_irreguler_gross = fields.Float('Pajak Disetahunkan Irreguler Gross', help='Pajak Disetahunkan Irreguler Gross', compute='_amount_pjk_thn_irreguler_gross', store=True)
    pjk_terhutang_reguler_gross = fields.Float('Pajak Terhutang Reguler Gross', help='Pajak Terhutang Reguler Gross', compute='_amount_pjk_terhutang_reguler_gross', store=True)
    pjk_terhutang_irreguler_gross = fields.Float('Pajak Terhutang Irreguler Gross', help='Pajak Terhutang Irreguler Gross', compute='_amount_pjk_terhutang_irreguler_gross', store=True)
    pjk_terhutang_reguler_last_month_gross = fields.Float('Akumulasi Pajak Reguler Bulan Sebelumnya Gross', default=0)
    pjk_terhutang_irreguler_last_month_gross = fields.Float('Akumulasi Pajak Irreguler Bulan Sebelumnya Gross', default=0)
    pjk_bln_reguler_gross = fields.Float('Pajak Perbulan Reguler Gross', compute='_amount_pjk_bln_reguler_gross', store=True)
    pjk_bln_irreguler_gross = fields.Float('Pajak Perbulan Irreguler Gross', compute='_amount_pjk_bln_irreguler_gross', store=True)
    kelebihan_pajak_gross = fields.Float(string='Kelebihan Pajak Gross', readonly=True, default=0)

    ## tax calculation TER Gross Up ##
    period_tax_calculation_schema = fields.Selection(related="payslip_period_id.tax_calculation_schema", string="Tax Calculation Schema")
    income_reguler_ter_ids = fields.One2many('hr.payslip.tax.ter.calculation', 'slip_id', string='Income Reguler', readonly=True,
                                             domain=[('tax_category','=','income_reguler')], states={'draft': [('readonly', False)]})
    income_irreguler_ter_ids = fields.One2many('hr.payslip.tax.ter.calculation', 'slip_id', string='Income Irreguler',
                                               domain=[('tax_category','=','income_irreguler')], readonly=True, states={'draft': [('readonly', False)]})
    deduction_ter_ids = fields.One2many('hr.payslip.tax.ter.calculation', 'slip_id', string='Deduction',
                                        domain=[('tax_category','=','deduction')], readonly=True, states={'draft': [('readonly', False)]})
    pph21_ter_reguler_ids = fields.One2many('hr.payslip.tax.ter.reguler', 'slip_id', string='Tax Bracket Reguler',
                                            compute='compute_pph21_ter_reguler', store=True)
    pph21_ter_irreguler_ids = fields.One2many('hr.payslip.tax.ter.irreguler', 'slip_id', string='Tax Bracket Irreguler',
                                              compute='compute_pph21_ter_irreguler', store=True)
    ter_category_ids = fields.One2many('hr.payslip.ter.cat', 'slip_id', string='TER Category',
                                       compute='compute_ter_category', store=True)
    ter_akum_income_last_month = fields.Float('Akumulasi Icome Reguler Bulan Sebelumnya', default=0)
    ter_akum_irreguler_last_month = fields.Float('Akumulasi Icome Irreguler Bulan Sebelumnya', default=0)
    ter_akum_income_reguler = fields.Float('Akumulasi Income Reguler', help='Akumulasi Income Reguler', compute='_amount_ter_akum_income_reguler', store=True)
    ter_akum_income_irreguler = fields.Float('Akumulasi Income Irreguler', help='Akumulasi Income Irreguler', compute='_amount_ter_akum_income_irreguler', store=True)
    ter_bruto = fields.Float('Bruto', compute='_amount_ter_bruto', store=True)
    ter_akum_ded_last_month = fields.Float('Akumulasi Deduction Sebelumnya', default=0)
    ter_neto_masa_sebelumnya = fields.Float('Neto Masa Sebelumnya', compute='compute_ter_neto_masa_sebelumnya', store=True)
    ter_akum_ded = fields.Float('Akumulasi Deduction', help='Akumulasi Deduction', compute='_amount_ter_akum_ded', store=True)
    ter_akum_ded_thn = fields.Float('Akumulasi Deduction Disetahunkan', compute='_amount_ter_akum_ded_thn', store=True)
    ter_biaya_jab_month = fields.Float('Biaya Jabatan Monthly', compute='_amount_ter_biaya_jab_month', store=True)
    ter_biaya_jab_reguler = fields.Float('Biaya Jabatan Reguler', compute='_amount_ter_biaya_jab_reguler', store=True)
    ter_biaya_jab_irreguler = fields.Float('Biaya Jabatan Irreguler', compute='_amount_ter_biaya_jab_irreguler', store=True)
    ter_total_peng_reguler = fields.Float('Total Pengurang Reguler', compute='_amount_ter_total_peng_reguler', store=True)
    ter_total_peng_irreguler = fields.Float('Total Pengurang Irreguler', compute='_amount_ter_total_peng_irreguler', store=True)
    ter_akum_thn_reguler = fields.Float('Akumulasi Income Reguler Disetahunkan', compute='_amount_ter_akum_thn_reguler', store=True)
    ter_peng_thn_reguler = fields.Float('Penghasilan Disetahunakan Reguler', compute='_amount_ter_peng_thn_reguler', store=True)
    ter_peng_thn_irreguler = fields.Float('Penghasilan Disetahunakan Irreguler', compute='_amount_ter_peng_thn_irreguler', store=True)
    ter_peng_kena_pjk_reguler = fields.Float('Penghasilan Kena Pajak Reguler', compute='_amount_ter_peng_kena_pjk_reguler', store=True)
    ter_peng_kena_pjk_irreguler = fields.Float('Penghasilan Kena Pajak Irreguler', compute='_amount_ter_peng_kena_pjk_irreguler', store=True)
    ter_pjk_thn_reguler = fields.Float('Pajak Disetahunkan Reguler', compute='_amount_ter_pjk_thn_reguler', store=True)
    ter_pjk_thn_irreguler = fields.Float('Pajak Disetahunkan Irreguler', compute='_amount_ter_pjk_thn_irreguler', store=True)
    ter_pjk_terhutang_reguler = fields.Float('Pajak Terhutang Reguler', compute='_amount_ter_pjk_terhutang_reguler', store=True)
    ter_pjk_terhutang_irreguler = fields.Float('Pajak Terhutang Irreguler', compute='_amount_ter_pjk_terhutang_irreguler', store=True)
    ter_pjk_bln = fields.Float('PPH21 Perbulan', compute='_amount_ter_pjk_bln', store=True)
    ter_pph21_paid = fields.Float('PPH21 Paid', compute='_amount_ter_pph21_paid', store=True)
    ter_diff = fields.Float('Difference', compute='_amount_ter_diff', store=True)
    ter_tunj_pjk_bln = fields.Float('Tunjangan PPH21 Perbulan', default=0)
    ter_tunj_pjk_terhutang_reguler = fields.Float('Tunjangan Pajak Terhutang Regular', default=0)
    ter_tunj_pjk_terhutang_irreguler = fields.Float('Tunjangan Pajak Terhutang Irregular', default=0)
    ter_pjk_terhutang_reguler_last_month = fields.Float('Akumulasi Pajak Reguler Bulan Sebelumnya', default=0)
    ter_pjk_terhutang_irreguler_last_month = fields.Float('Akumulasi Pajak Irreguler Bulan Sebelumnya', default=0)
    ter_pjk_natura = fields.Float('PPh21 Atas Natura', compute='_amount_ter_pjk_natura', store=True)

    ## tax calculation TER Gross Up Non Natura ##
    pph21_ter_reguler_non_natura_ids = fields.One2many('hr.payslip.tax.ter.reguler.non.natura', 'slip_id', string='Tax Bracket Reguler',
                                            compute='compute_pph21_ter_reguler_non_natura', store=True)
    pph21_ter_irreguler_non_natura_ids = fields.One2many('hr.payslip.tax.ter.irreguler.non.natura', 'slip_id', string='Tax Bracket Irreguler',
                                              compute='compute_pph21_ter_irreguler_non_natura', store=True)
    ter_category_non_natura_ids = fields.One2many('hr.payslip.ter.cat.non.natura', 'slip_id', string='TER Category',
                                       compute='compute_ter_category_non_natura', store=True)
    ter_akum_income_last_month_non_natura = fields.Float('Akumulasi Icome Reguler Bulan Sebelumnya', default=0)
    ter_akum_irreguler_last_month_non_natura = fields.Float('Akumulasi Icome Irreguler Bulan Sebelumnya', default=0)
    ter_akum_income_reguler_non_natura = fields.Float('Akumulasi Income Reguler', help='Akumulasi Income Reguler', compute='_amount_ter_akum_income_reguler_non_natura', store=True)
    ter_akum_income_irreguler_non_natura = fields.Float('Akumulasi Income Irreguler', help='Akumulasi Income Irreguler', compute='_amount_ter_akum_income_irreguler_non_natura', store=True)
    ter_bruto_non_natura = fields.Float('Bruto', compute='_amount_ter_bruto_non_natura', store=True)
    ter_akum_ded_last_month_non_natura = fields.Float('Akumulasi Deduction Sebelumnya', default=0)
    ter_neto_masa_sebelumnya_non_natura = fields.Float('Neto Masa Sebelumnya', compute='compute_ter_neto_masa_sebelumnya_non_natura', store=True)
    ter_akum_ded_non_natura = fields.Float('Akumulasi Deduction', help='Akumulasi Deduction', compute='_amount_ter_akum_ded_non_natura', store=True)
    ter_akum_ded_thn_non_natura = fields.Float('Akumulasi Deduction Disetahunkan', compute='_amount_ter_akum_ded_thn_non_natura', store=True)
    ter_biaya_jab_month_non_natura = fields.Float('Biaya Jabatan Monthly', compute='_amount_ter_biaya_jab_month_non_natura', store=True)
    ter_biaya_jab_reguler_non_natura = fields.Float('Biaya Jabatan Reguler', compute='_amount_ter_biaya_jab_reguler_non_natura', store=True)
    ter_biaya_jab_irreguler_non_natura = fields.Float('Biaya Jabatan Irreguler', compute='_amount_ter_biaya_jab_irreguler_non_natura', store=True)
    ter_total_peng_reguler_non_natura = fields.Float('Total Pengurang Reguler', compute='_amount_ter_total_peng_reguler_non_natura', store=True)
    ter_total_peng_irreguler_non_natura = fields.Float('Total Pengurang Irreguler', compute='_amount_ter_total_peng_irreguler_non_natura', store=True)
    ter_akum_thn_reguler_non_natura = fields.Float('Akumulasi Income Reguler Disetahunkan', compute='_amount_ter_akum_thn_reguler_non_natura', store=True)
    ter_peng_thn_reguler_non_natura = fields.Float('Penghasilan Disetahunakan Reguler', compute='_amount_ter_peng_thn_reguler_non_natura', store=True)
    ter_peng_thn_irreguler_non_natura = fields.Float('Penghasilan Disetahunakan Irreguler', compute='_amount_ter_peng_thn_irreguler_non_natura', store=True)
    ter_peng_kena_pjk_reguler_non_natura = fields.Float('Penghasilan Kena Pajak Reguler', compute='_amount_ter_peng_kena_pjk_reguler_non_natura', store=True)
    ter_peng_kena_pjk_irreguler_non_natura = fields.Float('Penghasilan Kena Pajak Irreguler', compute='_amount_ter_peng_kena_pjk_irreguler_non_natura', store=True)
    ter_pjk_thn_reguler_non_natura = fields.Float('Pajak Disetahunkan Reguler', compute='_amount_ter_pjk_thn_reguler_non_natura', store=True)
    ter_pjk_thn_irreguler_non_natura = fields.Float('Pajak Disetahunkan Irreguler', compute='_amount_ter_pjk_thn_irreguler_non_natura', store=True)
    ter_pjk_terhutang_reguler_non_natura = fields.Float('Pajak Terhutang Reguler', compute='_amount_ter_pjk_terhutang_reguler_non_natura', store=True)
    ter_pjk_terhutang_irreguler_non_natura = fields.Float('Pajak Terhutang Irreguler', compute='_amount_ter_pjk_terhutang_irreguler_non_natura', store=True)
    ter_pjk_bln_non_natura = fields.Float('PPH21 Perbulan', compute='_amount_ter_pjk_bln_non_natura', store=True)
    ter_pph21_paid_non_natura = fields.Float('PPH21 Paid', compute='_amount_ter_pph21_paid_non_natura', store=True)
    ter_diff_non_natura = fields.Float('Difference', compute='_amount_ter_diff_non_natura', store=True)
    ter_tunj_pjk_bln_non_natura = fields.Float('Tunjangan PPH21 Perbulan', default=0)
    ter_tunj_pjk_terhutang_reguler_non_natura = fields.Float('Tunjangan Pajak Terhutang Regular', default=0)
    ter_tunj_pjk_terhutang_irreguler_non_natura = fields.Float('Tunjangan Pajak Terhutang Irregular', default=0)
    ter_pjk_terhutang_reguler_last_month_non_natura = fields.Float('Akumulasi Pajak Reguler Bulan Sebelumnya', default=0)
    ter_pjk_terhutang_irreguler_last_month_non_natura = fields.Float('Akumulasi Pajak Irreguler Bulan Sebelumnya', default=0)

    ## tax calculation TER Gross ##
    pph21_ter_reguler_gross_ids = fields.One2many('hr.payslip.tax.ter.reguler.gross', 'slip_id', string='Tax Bracket Reguler',
                                            compute='compute_pph21_ter_reguler_gross', store=True)
    pph21_ter_irreguler_gross_ids = fields.One2many('hr.payslip.tax.ter.irreguler.gross', 'slip_id', string='Tax Bracket Irreguler',
                                              compute='compute_pph21_ter_irreguler_gross', store=True)
    ter_category_gross_ids = fields.One2many('hr.payslip.ter.cat.gross', 'slip_id', string='TER Category',
                                       compute='compute_ter_category_gross', store=True)
    ter_akum_income_last_month_gross = fields.Float('Akumulasi Icome Reguler Bulan Sebelumnya', default=0)
    ter_akum_irreguler_last_month_gross = fields.Float('Akumulasi Icome Irreguler Bulan Sebelumnya', default=0)
    ter_akum_income_reguler_gross = fields.Float('Akumulasi Income Reguler', help='Akumulasi Income Reguler', compute='_amount_ter_akum_income_reguler_gross', store=True)
    ter_akum_income_irreguler_gross = fields.Float('Akumulasi Income Irreguler', help='Akumulasi Income Irreguler', compute='_amount_ter_akum_income_irreguler_gross', store=True)
    ter_bruto_gross = fields.Float('Bruto', compute='_amount_ter_bruto_gross', store=True)
    ter_akum_ded_last_month_gross = fields.Float('Akumulasi Deduction Sebelumnya', default=0)
    ter_neto_masa_sebelumnya_gross = fields.Float('Neto Masa Sebelumnya', compute='compute_ter_neto_masa_sebelumnya_gross', store=True)
    ter_akum_ded_gross = fields.Float('Akumulasi Deduction', help='Akumulasi Deduction', compute='_amount_ter_akum_ded_gross', store=True)
    ter_akum_ded_thn_gross = fields.Float('Akumulasi Deduction Disetahunkan', compute='_amount_ter_akum_ded_thn_gross', store=True)
    ter_biaya_jab_month_gross = fields.Float('Biaya Jabatan Monthly', compute='_amount_ter_biaya_jab_month_gross', store=True)
    ter_biaya_jab_reguler_gross = fields.Float('Biaya Jabatan Reguler', compute='_amount_ter_biaya_jab_reguler_gross', store=True)
    ter_biaya_jab_irreguler_gross = fields.Float('Biaya Jabatan Irreguler', compute='_amount_ter_biaya_jab_irreguler_gross', store=True)
    ter_total_peng_reguler_gross = fields.Float('Total Pengurang Reguler', compute='_amount_ter_total_peng_reguler_gross', store=True)
    ter_total_peng_irreguler_gross = fields.Float('Total Pengurang Irreguler', compute='_amount_ter_total_peng_irreguler_gross', store=True)
    ter_akum_thn_reguler_gross = fields.Float('Akumulasi Income Reguler Disetahunkan', compute='_amount_ter_akum_thn_reguler_gross', store=True)
    ter_peng_thn_reguler_gross = fields.Float('Penghasilan Disetahunakan Reguler', compute='_amount_ter_peng_thn_reguler_gross', store=True)
    ter_peng_thn_irreguler_gross = fields.Float('Penghasilan Disetahunakan Irreguler', compute='_amount_ter_peng_thn_irreguler_gross', store=True)
    ter_peng_kena_pjk_reguler_gross = fields.Float('Penghasilan Kena Pajak Reguler', compute='_amount_ter_peng_kena_pjk_reguler_gross', store=True)
    ter_peng_kena_pjk_irreguler_gross = fields.Float('Penghasilan Kena Pajak Irreguler', compute='_amount_ter_peng_kena_pjk_irreguler_gross', store=True)
    ter_pjk_thn_reguler_gross = fields.Float('Pajak Disetahunkan Reguler', compute='_amount_ter_pjk_thn_reguler_gross', store=True)
    ter_pjk_thn_irreguler_gross = fields.Float('Pajak Disetahunkan Irreguler', compute='_amount_ter_pjk_thn_irreguler_gross', store=True)
    ter_pjk_terhutang_reguler_gross = fields.Float('Pajak Terhutang Reguler', compute='_amount_ter_pjk_terhutang_reguler_gross', store=True)
    ter_pjk_terhutang_irreguler_gross = fields.Float('Pajak Terhutang Irreguler', compute='_amount_ter_pjk_terhutang_irreguler_gross', store=True)
    ter_pjk_bln_gross = fields.Float('PPH21 Perbulan', compute='_amount_ter_pjk_bln_gross', store=True)
    ter_pph21_paid_gross = fields.Float('PPH21 Paid', compute='_amount_ter_pph21_paid_gross', store=True)
    ter_diff_gross = fields.Float('Difference', compute='_amount_ter_diff_gross', store=True)
    ter_pjk_terhutang_reguler_last_month_gross = fields.Float('Akumulasi Pajak Reguler Bulan Sebelumnya', default=0)
    ter_pjk_terhutang_irreguler_last_month_gross = fields.Float('Akumulasi Pajak Irreguler Bulan Sebelumnya', default=0)
    ter_pjk_natura_gross = fields.Float('PPh21 Atas Natura Gross', compute='_amount_ter_pjk_natura_gross', store=True)

    ## tax calculation TER Gross Non Natura ##
    pph21_ter_reguler_gross_non_natura_ids = fields.One2many('hr.payslip.tax.ter.reguler.gross.non.natura', 'slip_id', string='Tax Bracket Reguler',
                                            compute='compute_pph21_ter_reguler_gross_non_natura', store=True)
    pph21_ter_irreguler_gross_non_natura_ids = fields.One2many('hr.payslip.tax.ter.irreguler.gross.non.natura', 'slip_id', string='Tax Bracket Irreguler',
                                              compute='compute_pph21_ter_irreguler_gross_non_natura', store=True)
    ter_category_gross_non_natura_ids = fields.One2many('hr.payslip.ter.cat.gross.non.natura', 'slip_id', string='TER Category',
                                       compute='compute_ter_category_gross_non_natura', store=True)
    ter_akum_income_last_month_gross_non_natura = fields.Float('Akumulasi Icome Reguler Bulan Sebelumnya', default=0)
    ter_akum_irreguler_last_month_gross_non_natura = fields.Float('Akumulasi Icome Irreguler Bulan Sebelumnya', default=0)
    ter_akum_income_reguler_gross_non_natura = fields.Float('Akumulasi Income Reguler', help='Akumulasi Income Reguler', compute='_amount_ter_akum_income_reguler_gross_non_natura', store=True)
    ter_akum_income_irreguler_gross_non_natura = fields.Float('Akumulasi Income Irreguler', help='Akumulasi Income Irreguler', compute='_amount_ter_akum_income_irreguler_gross_non_natura', store=True)
    ter_bruto_gross_non_natura = fields.Float('Bruto', compute='_amount_ter_bruto_gross_non_natura', store=True)
    ter_akum_ded_last_month_gross_non_natura = fields.Float('Akumulasi Deduction Sebelumnya', default=0)
    ter_neto_masa_sebelumnya_gross_non_natura = fields.Float('Neto Masa Sebelumnya', compute='compute_ter_neto_masa_sebelumnya_gross_non_natura', store=True)
    ter_akum_ded_gross_non_natura = fields.Float('Akumulasi Deduction', help='Akumulasi Deduction', compute='_amount_ter_akum_ded_gross_non_natura', store=True)
    ter_akum_ded_thn_gross_non_natura = fields.Float('Akumulasi Deduction Disetahunkan', compute='_amount_ter_akum_ded_thn_gross_non_natura', store=True)
    ter_biaya_jab_month_gross_non_natura = fields.Float('Biaya Jabatan Monthly', compute='_amount_ter_biaya_jab_month_gross_non_natura', store=True)
    ter_biaya_jab_reguler_gross_non_natura = fields.Float('Biaya Jabatan Reguler', compute='_amount_ter_biaya_jab_reguler_gross_non_natura', store=True)
    ter_biaya_jab_irreguler_gross_non_natura = fields.Float('Biaya Jabatan Irreguler', compute='_amount_ter_biaya_jab_irreguler_gross_non_natura', store=True)
    ter_total_peng_reguler_gross_non_natura = fields.Float('Total Pengurang Reguler', compute='_amount_ter_total_peng_reguler_gross_non_natura', store=True)
    ter_total_peng_irreguler_gross_non_natura = fields.Float('Total Pengurang Irreguler', compute='_amount_ter_total_peng_irreguler_gross_non_natura', store=True)
    ter_akum_thn_reguler_gross_non_natura = fields.Float('Akumulasi Income Reguler Disetahunkan', compute='_amount_ter_akum_thn_reguler_gross_non_natura', store=True)
    ter_peng_thn_reguler_gross_non_natura = fields.Float('Penghasilan Disetahunakan Reguler', compute='_amount_ter_peng_thn_reguler_gross_non_natura', store=True)
    ter_peng_thn_irreguler_gross_non_natura = fields.Float('Penghasilan Disetahunakan Irreguler', compute='_amount_ter_peng_thn_irreguler_gross_non_natura', store=True)
    ter_peng_kena_pjk_reguler_gross_non_natura = fields.Float('Penghasilan Kena Pajak Reguler', compute='_amount_ter_peng_kena_pjk_reguler_gross_non_natura', store=True)
    ter_peng_kena_pjk_irreguler_gross_non_natura = fields.Float('Penghasilan Kena Pajak Irreguler', compute='_amount_ter_peng_kena_pjk_irreguler_gross_non_natura', store=True)
    ter_pjk_thn_reguler_gross_non_natura = fields.Float('Pajak Disetahunkan Reguler', compute='_amount_ter_pjk_thn_reguler_gross_non_natura', store=True)
    ter_pjk_thn_irreguler_gross_non_natura = fields.Float('Pajak Disetahunkan Irreguler', compute='_amount_ter_pjk_thn_irreguler_gross_non_natura', store=True)
    ter_pjk_terhutang_reguler_gross_non_natura = fields.Float('Pajak Terhutang Reguler', compute='_amount_ter_pjk_terhutang_reguler_gross_non_natura', store=True)
    ter_pjk_terhutang_irreguler_gross_non_natura = fields.Float('Pajak Terhutang Irreguler', compute='_amount_ter_pjk_terhutang_irreguler_gross_non_natura', store=True)
    ter_pjk_bln_gross_non_natura = fields.Float('PPH21 Perbulan', compute='_amount_ter_pjk_bln_gross_non_natura', store=True)
    ter_pph21_paid_gross_non_natura = fields.Float('PPH21 Paid', compute='_amount_ter_pph21_paid_gross_non_natura', store=True)
    ter_diff_gross_non_natura = fields.Float('Difference', compute='_amount_ter_diff_gross_non_natura', store=True)
    ter_pjk_terhutang_reguler_last_month_gross_non_natura = fields.Float('Akumulasi Pajak Reguler Bulan Sebelumnya', default=0)
    ter_pjk_terhutang_irreguler_last_month_gross_non_natura = fields.Float('Akumulasi Pajak Irreguler Bulan Sebelumnya', default=0)

    ## tax calculation TER pegawai tidak tetap
    income_reguler_non_permanent_ids = fields.One2many('hr.payslip.tax.non.permanent', 'slip_id', string='Income Reguler', readonly=True,
                                                       domain=[('tax_category','=','income_reguler')], states={'draft': [('readonly', False)]})
    income_irreguler_non_permanent_ids = fields.One2many('hr.payslip.tax.non.permanent', 'slip_id', string='Income Irreguler', readonly=True,
                                                         domain=[('tax_category','=','income_irreguler')], states={'draft': [('readonly', False)]})
    pph21_ter_non_permanent_ids = fields.One2many('hr.payslip.tax.ter.non.permanent', 'slip_id', string='Tax Bracket',
                                              compute='compute_tax_bracket_non_permanent', store=True)
    ter_category_non_permanent_ids = fields.One2many('hr.payslip.ter.cat.non.permanent', 'slip_id', string='TER Category',
                                                     compute='compute_ter_category_non_permanent', store=True)
    ter_daily_rate_ids = fields.One2many('hr.payslip.ter.daily.rate', 'slip_id', string='TER Daily Rate',
                                         compute='compute_ter_daily_rate', store=True)
    ter_akum_income_reguler_non_permanent = fields.Float('Akumulasi Income Reguler', help='Akumulasi Income Reguler Non Permanent', compute='_amount_ter_akum_income_reguler_non_permanent', store=True)
    ter_akum_income_irreguler_non_permanent = fields.Float('Akumulasi Income Reguler', help='Akumulasi Income Irreguler Non Permanent', compute='_amount_ter_akum_income_irreguler_non_permanent', store=True)
    ter_bruto_non_permanent = fields.Float('Bruto', compute='_amount_ter_bruto_non_permanent', store=True)
    ter_pjk_non_permanent = fields.Float('PPH21', compute='_amount_ter_pjk_non_permanent', store=True)
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(HrPayslip, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(HrPayslip, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    @api.model
    def create(self, vals):
        if not self.env['hr.contract'].search([('employee_id', '=', vals.get('employee_id'))]):
            raise ValidationError(_("Contract is not found for this employee"))
        if self.env['hr.contract'].search([('employee_id', '=', vals.get('employee_id')), ('state', '=', 'draft')]):
            raise ValidationError(_("Contract is not running for this employee"))
        
        if vals.get('payslip_pesangon') == False and vals.get('credit_note') == False:
            payslip_exist = self.search([('employee_id','=',vals.get('employee_id')),('date_from','<=',vals.get('date_to')),('date_to','>',vals.get('date_from')),('payslip_pesangon','=',False),('state','in',['draft','done']),('credit_note','=',False)])
            if payslip_exist:
                raise ValidationError(_("There is same payslip period for this employee!"))
        return super(HrPayslip, self).create(vals)
    
    def write(self, vals):
        res = super(HrPayslip, self).write(vals)
        for rec in self:
            if rec.payslip_pesangon == False and rec.credit_note == False and rec.state in ('draft','done'):
                payslip_exist = self.search([('id','!=',rec.id),('employee_id','=',rec.employee_id.id),('date_from','<=',vals.get('date_to')),('date_to','>',vals.get('date_from')),('payslip_pesangon','=',False),('state','in',['draft','done']),('credit_note','=',False)])
                if payslip_exist:
                    raise ValidationError(_("There is same payslip period for this employee!"))
        return res

    def _allow_send_email(self):
        for res in self:
            allow_send_email = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_payroll_extend_id.payslip_allow_send_email')
            res.allow_send_email = allow_send_email

    def round_up(self, n, decimals=0):
        multiplier = 10 ** decimals
        return math.ceil(n * multiplier) / multiplier

    def round_down(self, n, decimals=0):
        multiplier = 10 ** decimals
        return math.floor(n * multiplier) / multiplier

    @api.depends('employee_id.date_of_joining')
    def compute_date_of_joining(self):
        for record in self:
            if record.employee_id.date_of_joining:
                record.date_of_joining = record.employee_id.date_of_joining

    @api.depends('date_of_joining', 'termination_date')
    def compute_year_of_service(self):
        for record in self:
            if record.payslip_pesangon:
                if record.date_of_joining and record.termination_date:
                    termination_date = record.termination_date
                    d1 = record.date_of_joining
                    d2 = termination_date
                    diff = relativedelta(d2, d1)
                    record.years_of_service = diff.years
                    record.months_of_service = diff.months
                    record.days_of_service = diff.days
                    ## masa kerja dlm bulan
                    record.masa_kerja = diff.months + (12 * diff.years)
                else:
                    record.years_of_service = 0
                    record.months_of_service = 0
                    record.days_of_service = 0
                    record.masa_kerja = 0
            else:
                if record.date_of_joining and not record.termination_date:
                    current_day = date.today()
                    d1 = record.date_of_joining
                    d2 = current_day
                    diff = relativedelta(d2, d1)
                    record.years_of_service = diff.years
                    record.months_of_service = diff.months
                    record.days_of_service = diff.days
                    ## masa kerja dlm bulan
                    record.masa_kerja = diff.months + (12 * diff.years)
                elif record.date_of_joining and record.termination_date:
                    termination_date = record.termination_date
                    d1 = record.date_of_joining
                    d2 = termination_date
                    diff = relativedelta(d2, d1)
                    record.years_of_service = diff.years
                    record.months_of_service = diff.months
                    record.days_of_service = diff.days
                    ## masa kerja dlm bulan
                    record.masa_kerja = diff.months + (12 * diff.years)
                else:
                    record.years_of_service = 0
                    record.months_of_service = 0
                    record.days_of_service = 0
                    record.masa_kerja = 0

    @api.model
    def get_contract(self, employee, date_from, date_to):

        """
        @param employee: recordset of employee
        @param date_from: date field
        @param date_to: date field
        @return: returns the ids of all the contracts for the given employee that need to be considered for the given dates
        """
        # a contract is valid if it ends between the given dates
        clause_1 = ['&', ('date_end', '<=', date_to), ('date_end', '>=', date_from)]
        # OR if it starts between the given dates
        clause_2 = ['&', ('date_start', '<=', date_to), ('date_start', '>=', date_from)]
        # OR if it starts before the date_from and finish after the date_end (or never finish)
        clause_3 = ['&', ('date_start', '<=', date_from), '|', ('date_end', '=', False), ('date_end', '>=', date_to)]
        clause_final = [('employee_id', '=', employee.id), ('state', 'in', ['open']), '|',
                        '|'] + clause_1 + clause_2 + clause_3
        clause_finals = [('employee_id', '=', employee.id), ('state', 'in', ['close'])
                        ] + clause_1
        if self.env['hr.contract'].search(clause_final):
            return self.env['hr.contract'].search(clause_final).ids
        elif self.env['hr.contract'].search(clause_finals):
            return self.env['hr.contract'].search(clause_finals).ids
        else:
            return self.env['hr.contract'].search(clause_final).ids

    @api.onchange('employee_id', 'date_from', 'date_to')
    def onchange_employee(self):
        res = super(HrPayslip, self).onchange_employee()
        if (not self.employee_id) or (not self.date_from) or (not self.date_to):
            return

        if self.payslip_pesangon == False:
            self.name = _('Salary Slip of %s for %s-%s') % (
                self.employee_id.name, self.month.month, self.month.year)

            if self.employee_id.have_npwp == "yes":
                self.npwp = self.employee_id.npwp_no
            else:
                self.npwp = ''
            if self.employee_id.department_id:
                self.department_id = self.employee_id.department_id.id
            if self.employee_id.job_id:
                self.job_id = self.employee_id.job_id.id
            if self.employee_id.kpp_id:
                self.kpp_id = self.employee_id.kpp_id.id
                self.kpp = self.employee_id.kpp_id.name
            if self.employee_id.ptkp_id:
                self.ptkp_id = self.employee_id.ptkp_id.id
                self.ptkp = self.employee_id.ptkp_id.ptkp_name
            if self.employee_id.tax_calculation_method:
                tax_calculation_method = dict(self.env['hr.employee'].fields_get(allfields=['tax_calculation_method'])['tax_calculation_method']['selection'])[self.employee_id.tax_calculation_method]
                self.tax_calculation_method = tax_calculation_method
            if self.employee_id.employee_tax_status:
                employee_tax_status = dict(self.env['hr.employee'].fields_get(allfields=['employee_tax_status'])['employee_tax_status']['selection'])[self.employee_id.employee_tax_status]
                self.employee_tax_status = employee_tax_status
                self.emp_tax_status = self.employee_id.employee_tax_status
                if self.employee_id.employee_tax_status == "pegawai_tidak_tetap":
                    self.employee_payment_method = self.employee_id.employee_payment_method
            if self.employee_id.is_expatriate:
                self.is_expatriate = self.employee_id.is_expatriate
            if self.employee_id.expatriate_tax:
                expatriate_tax = dict(self.env['hr.employee'].fields_get(allfields=['expatriate_tax'])['expatriate_tax']['selection'])[self.employee_id.expatriate_tax]
                self.expatriate_tax = expatriate_tax
            date_join = self.employee_id.date_of_joining
            tax_period_length = 0
            date_join_month = datetime.strptime(str(date_join), '%Y-%m-%d').date().month
            date_join_year = datetime.strptime(str(date_join), '%Y-%m-%d').date().year
            if self.payslip_period_id:
                if self.payslip_period_id.start_period_based_on == 'start_date':
                    this_month = datetime.strptime(str(self.date_from), '%Y-%m-%d').date().month
                    this_year = datetime.strptime(str(self.date_from), '%Y-%m-%d').date().year
                elif self.payslip_period_id.start_period_based_on == 'end_date':
                    this_month = datetime.strptime(str(self.date_to), '%Y-%m-%d').date().month
                    this_year = datetime.strptime(str(self.date_to), '%Y-%m-%d').date().year

                if this_year == date_join_year:
                    if (this_month >= date_join_month):
                        tax_period_length = (int(this_month) - int(date_join_month)) + 1
                    self.tax_period_length = tax_period_length
                    self.tax_end_month = (12 - int(date_join_month)) + 1
                else:
                    self.tax_period_length = this_month
                    self.tax_end_month = 12

                contract_ids = self.get_contract(self.employee_id, self.date_from, self.date_to)
                if not contract_ids:
                    self.contract_id = False
                    return
                else:
                    self.contract_id = self.env['hr.contract'].browse(contract_ids[0])
                transition_category = self.env['career.transition.category'].search([('name', '=', 'Termination')], limit=1)
                term = self.env['hr.career.transition'].search(
                    [('employee_id', '=', self.employee_id.id), ('status', '=', 'approve'),
                     ('transition_category_id', '=', transition_category.id), ('transition_date', '>=', self.date_from),
                     ('transition_date', '<=', self.date_to)], limit=1, order="id DESC")
                if term:
                    self.termination = True
                    self.termination_date = term.transition_date
                    date_resign = term.transition_date
                    date_resign_month = datetime.strptime(str(date_resign), '%Y-%m-%d').date().month
                    date_resign_year = datetime.strptime(str(date_resign), '%Y-%m-%d').date().year
                    if this_year == date_resign_year:
                        if (date_resign >= self.date_from) and (date_resign <= self.date_to):
                            self.tax_end_month = int(this_month)
                elif self.contract_id.state == "close":
                    self.termination = True
                    self.termination_date = self.contract_id.date_end
                    date_resign = self.contract_id.date_end
                    date_resign_month = datetime.strptime(str(date_resign), '%Y-%m-%d').date().month
                    date_resign_year = datetime.strptime(str(date_resign), '%Y-%m-%d').date().year
                    if this_year == date_resign_year:
                        if (date_resign >= self.date_from) and (date_resign <= self.date_to):
                            self.tax_end_month = int(this_month)
                else:
                    self.termination = False
                    self.termination_date = False
                if not self.contract_id.struct_id:
                    return
                self.struct_id = self.contract_id.struct_id
                if self.contract_id:
                    contract_ids = self.contract_id.ids
                # computation of the salary input
                contracts = self.env['hr.contract'].browse(contract_ids)
                other_input_entries = []
                other_input_ids = self.env['hr.other.input.entries'].search([('employee', '=', self.employee_id.id),
                                                                             ('payslip_period_id', '=',
                                                                              self.payslip_period_id.id),
                                                                             ('month', '=', self.month.id)])
                for contract in contracts:
                    for input in other_input_ids:
                        input_data = {
                            'name': input.other_input_id.name,
                            'code': input.code,
                            'amount': input.amount,
                            'contract_id': contract.id,
                        }
                        other_input_entries += [input_data]
                    attendance_alw = {
                        'name': "Attendance's Allowance",
                        'code': 'ATT_ALW',
                        'amount': 0,
                        'contract_id': contract.id,
                    }
                    other_input_entries += [attendance_alw]
                input_lines = self.input_line_ids.browse([])
                for r in other_input_entries:
                    input_lines += input_lines.new(r)
                self.input_line_ids += input_lines

                day_from = datetime.combine(fields.Date.from_string(self.date_from), time.min)
                day_to = datetime.combine(fields.Date.from_string(self.date_to), time.max)
                self.env.cr.execute(
                    ''' select id, hour_from, check_in, tolerance_late, attendance_formula_id from hr_attendance WHERE employee_id = %s AND check_in >= '%s' and check_in <= '%s' and checkin_status = 'late' and active = 'true' ''' % (
                        self.employee_id.id, day_from, day_to))
                attendances = self.env.cr.dictfetchall()
                if attendances:
                    checkin_late_deduction = []
                    for att in attendances:
                        input_data = {
                            'hour_from': att.get('hour_from'),
                            'date_checkin': att.get('check_in'),
                            'tolerance_for_late': att.get('tolerance_late'),
                            'attendance_formula_id': att.get('attendance_formula_id'),
                        }
                        checkin_late_deduction += [input_data]

                    checkin_late_ded = self.late_deduction_ids.browse([])
                    for r in checkin_late_deduction:
                        checkin_late_ded += checkin_late_ded.new(r)
                    self.late_deduction_ids = checkin_late_ded
                else:
                    remove = []
                    for line in self.late_deduction_ids:
                        remove.append((2, line.id))
                    self.late_deduction_ids = remove
                
                att_alw_amount = 0
                attendance_formula_setting = self.env['hr.config.settings'].sudo().search([],limit=1)
                if attendance_formula_setting.use_attendance_formula:
                    self.env.cr.execute(
                        ''' select id, check_in, attendance_formula_id from hr_attendance WHERE employee_id = %s AND check_in >= '%s' and check_in <= '%s' and attendance_status = 'present' and active = 'true' ''' % (
                            self.employee_id.id, day_from, day_to))
                    attendance_alw = self.env.cr.dictfetchall()
                    if attendance_alw:
                        for att_alw in attendance_alw:
                            if att_alw.get('attendance_formula_id'):
                                att_formula_obj = self.env['hr.attendance.formula'].browse(int(att_alw.get('attendance_formula_id')))
                                amount = att_formula_obj._execute_formula_alw()
                                att_alw_amount += amount
                
                for rec in self.input_line_ids:
                    if rec.code == 'ATT_ALW':
                        rec.amount = att_alw_amount

        elif self.payslip_pesangon:
            self.date_from = False
            self.date_to = False

            transition_category = self.env['career.transition.category'].search([('name', '=', 'Termination')], limit=1)
            transition_type = self.env['career.transition.type'].search([('name', 'in', ['Termination','Pension'])])
            career_transition_type = [x.id for x in transition_type]
            pesangon_term = self.env['hr.career.transition'].search(
                [('employee_id', '=', self.employee_id.id), ('status', '=', 'approve'),
                 ('transition_category_id', '=', transition_category.id),
                 ('career_transition_type', 'in', career_transition_type)], limit=1, order="id DESC")
            if pesangon_term:
                self.termination_date = pesangon_term.transition_date
            else:
                self.termination_date = False

            pesangon_month = False
            pesangon_year = False
            if self.termination_date:
                pesangon_month = datetime.strptime(str(self.termination_date), '%Y-%m-%d').strftime("%B")
                pesangon_year = datetime.strptime(str(self.termination_date), '%Y-%m-%d').date().year
            self.name = _('Pesangon Payslip of %s for %s-%s') % (
                self.employee_id.name, pesangon_month, pesangon_year)

            cotract_obj = self.env['hr.contract'].search(
                [('state', 'in', ['open', 'close']), ('career_transition_id', '=', pesangon_term.id)], limit=1)
            if not cotract_obj:
                self.contract_id = False
                return
            else:
                self.contract_id = cotract_obj.id
            if not self.contract_id.struct_pesangon_id:
                return
            self.struct_id = self.contract_id.struct_pesangon_id
        return res

    @api.onchange('payslip_period_id')
    def _onchange_payslip_period_id(self):
        for res in self:
            if res.payslip_period_id:
                res.date_from = False
                res.date_to = False

    @api.onchange('month')
    def _onchange_month(self):
        for res in self:
            if res.payslip_period_id:
                if res.month:
                    period_line_obj = self.env['hr.payslip.period.line'].search(
                        [('id', '=', res.month.id)], limit=1)
                    if period_line_obj:
                        for rec in period_line_obj:
                            res.date_from = rec.start_date
                            res.date_to = rec.end_date
                            res.month_name = res.month.month
                            res.year = res.month.year
                        if res.payslip_period_id.start_period_based_on == 'start_date':
                            res.payslip_report_date = res.date_from
                        elif res.payslip_period_id.start_period_based_on == 'end_date':
                            res.payslip_report_date = res.date_to
                    else:
                        res.date_from = False
                        res.date_to = False
                        res.month_name = False
                        res.year = False

    def compute_sheet(self):

        for payslip in self:
            number = payslip.number or self.env['ir.sequence'].next_by_code('salary.slip')
            if payslip.period_tax_calculation_schema == "pph21":
                if payslip.payslip_pesangon == False:
                    # delete old payslip lines
                    if payslip.credit_note == True:
                        payslip.line_ids.unlink()
                    else:
                        for line in payslip.line_ids:
                            self.env.cr.execute("""DELETE FROM hr_payslip_line WHERE id = %s""" % (line.id))
                    # set the list of contract for which the rules have to be applied
                    # if we don't give the contract, then the rules to apply should be for all current contracts of the employee
                    contract_ids = payslip.contract_id.ids or \
                                self.get_contract(payslip.employee_id, payslip.date_from, payslip.date_to)

                    salary_rules = self._get_payslip_lines(contract_ids, payslip.id)

                    rules_income_reguler = []
                    rules_income_irreguler = []
                    rules_deduction = []
                    for rec in salary_rules:
                        self.env.cr.execute(
                            ''' select tax_category, tax_calculation_method, category_on_natura_tax from hr_salary_rule WHERE id = '%s' ''' % (rec['salary_rule_id']))
                        rules = self.env.cr.dictfetchall()
                        b = {'tax_category': rules[0].get('tax_category'),
                            'tax_calculation_method': rules[0].get('tax_calculation_method'),
                            'category_on_natura_tax': rules[0].get('category_on_natura_tax')}
                        rec.update(b)
                        if rec['tax_category'] == 'income_reguler':
                            rules_income_reguler.append(rec)
                        if rec['tax_category'] == 'income_irreguler':
                            rules_income_irreguler.append(rec)
                        if rec['tax_category'] == 'deduction':
                            rules_deduction.append(rec)

                    for line in payslip.income_reguler_ids:
                        self.env.cr.execute("""DELETE FROM hr_payslip_tax_calculation WHERE id = %s""" % (line.id))

                    income_reguler_lines = []
                    for line in rules_income_reguler:
                        amount = line['amount']
                        if line['category_on_natura_tax']:
                            natura_category = self.env['hr.natura.category'].sudo().browse(int(line['category_on_natura_tax']))
                            if natura_category.schema_type == "monthly":
                                if line['amount'] > natura_category.max_amount:
                                    amount = line['amount'] - natura_category.max_amount
                                else:
                                    amount = 0
                            elif natura_category.schema_type == "yearly":
                                self.env.cr.execute(
                                    '''select sum(pl.total) as sum_total FROM hr_payslip p LEFT JOIN hr_payslip_line pl ON (p.id=pl.slip_id) WHERE p.employee_id = %s and p.payslip_report_date < '%s' AND p.year = '%s' and p.state not in ('refund','cancel') and pl.salary_rule_id = %s''' % (
                                        payslip.employee_id.id, payslip.payslip_report_date, payslip.year, line['salary_rule_id']))
                                previous_payslip = self.env.cr.dictfetchall()
                                akum_amount = line['amount']
                                if previous_payslip and previous_payslip[0].get('sum_total') is not None:
                                    akum_amount = line['amount'] + previous_payslip[0].get('sum_total')
                                
                                self.env.cr.execute(
                                    '''select sum(ptx.amount) as sum_amount FROM hr_payslip p LEFT JOIN hr_payslip_tax_calculation ptx ON (p.id=ptx.slip_id) WHERE p.employee_id = %s and p.payslip_report_date < '%s' AND p.year = '%s' and p.state not in ('refund','cancel') and ptx.code = '%s' ''' % (
                                        payslip.employee_id.id, payslip.payslip_report_date, payslip.year, line['code']))
                                previous_tax = self.env.cr.dictfetchall()

                                amount_tax = 0
                                if previous_tax and previous_tax[0].get('sum_amount') is not None:
                                    amount_tax = previous_tax[0].get('sum_amount')

                                if akum_amount > natura_category.max_amount and amount_tax > 0:
                                    amount = line['amount']
                                elif akum_amount > natura_category.max_amount:
                                    amount = akum_amount - natura_category.max_amount
                                else:
                                    amount = 0
                        input_data = {
                            'name': line['name'],
                            'code': line['code'],
                            'sequence': line['sequence'],
                            'category_id': line['category_id'],
                            'employee_id': payslip.employee_id.id,
                            'tax_calculation_method': line['tax_calculation_method'],
                            'tax_category': line['tax_category'],
                            'amount': amount,
                        }
                        income_reguler_lines += [input_data]

                    for line in payslip.income_irreguler_ids:
                        self.env.cr.execute("""DELETE FROM hr_payslip_tax_calculation WHERE id = %s""" % (line.id))

                    income_irreguler_lines = []
                    for line in rules_income_irreguler:
                        amount = line['amount']
                        if line['category_on_natura_tax']:
                            natura_category = self.env['hr.natura.category'].sudo().browse(int(line['category_on_natura_tax']))
                            if natura_category.schema_type == "monthly":
                                if line['amount'] > natura_category.max_amount:
                                    amount = line['amount'] - natura_category.max_amount
                                else:
                                    amount = 0
                            elif natura_category.schema_type == "yearly":
                                self.env.cr.execute(
                                    '''select sum(pl.total) as sum_total FROM hr_payslip p LEFT JOIN hr_payslip_line pl ON (p.id=pl.slip_id) WHERE p.employee_id = %s and p.payslip_report_date < '%s' AND p.year = '%s' and p.state not in ('refund','cancel') and pl.salary_rule_id = %s''' % (
                                        payslip.employee_id.id, payslip.payslip_report_date, payslip.year, line['salary_rule_id']))
                                previous_payslip = self.env.cr.dictfetchall()
                                akum_amount = line['amount']
                                if previous_payslip and previous_payslip[0].get('sum_total') is not None:
                                    akum_amount = line['amount'] + previous_payslip[0].get('sum_total')
                                
                                self.env.cr.execute(
                                    '''select sum(ptx.amount) as sum_amount FROM hr_payslip p LEFT JOIN hr_payslip_tax_calculation ptx ON (p.id=ptx.slip_id) WHERE p.employee_id = %s and p.payslip_report_date < '%s' AND p.year = '%s' and p.state not in ('refund','cancel') and ptx.code = '%s' ''' % (
                                        payslip.employee_id.id, payslip.payslip_report_date, payslip.year, line['code']))
                                previous_tax = self.env.cr.dictfetchall()

                                amount_tax = 0
                                if previous_tax and previous_tax[0].get('sum_amount') is not None:
                                    amount_tax = previous_tax[0].get('sum_amount')

                                if akum_amount > natura_category.max_amount and amount_tax > 0:
                                    amount = line['amount']
                                elif akum_amount > natura_category.max_amount:
                                    amount = akum_amount - natura_category.max_amount
                                else:
                                    amount = 0
                        input_data = {
                            'name': line['name'],
                            'code': line['code'],
                            'sequence': line['sequence'],
                            'category_id': line['category_id'],
                            'employee_id': payslip.employee_id.id,
                            'tax_calculation_method': line['tax_calculation_method'],
                            'tax_category': line['tax_category'],
                            'amount': amount,
                        }
                        income_irreguler_lines += [input_data]

                    for line in payslip.deduction_ids:
                        self.env.cr.execute("""DELETE FROM hr_payslip_tax_calculation WHERE id = %s""" % (line.id))

                    deduction_lines = []
                    for line in rules_deduction:
                        amount = line['amount']
                        if line['category_on_natura_tax']:
                            natura_category = self.env['hr.natura.category'].sudo().browse(int(line['category_on_natura_tax']))
                            if natura_category.schema_type == "monthly":
                                if line['amount'] > natura_category.max_amount:
                                    amount = line['amount'] - natura_category.max_amount
                                else:
                                    amount = 0
                            elif natura_category.schema_type == "yearly":
                                self.env.cr.execute(
                                    '''select sum(pl.total) as sum_total FROM hr_payslip p LEFT JOIN hr_payslip_line pl ON (p.id=pl.slip_id) WHERE p.employee_id = %s and p.payslip_report_date < '%s' AND p.year = '%s' and p.state not in ('refund','cancel') and pl.salary_rule_id = %s''' % (
                                        payslip.employee_id.id, payslip.payslip_report_date, payslip.year, line['salary_rule_id']))
                                previous_payslip = self.env.cr.dictfetchall()
                                akum_amount = line['amount']
                                if previous_payslip and previous_payslip[0].get('sum_total') is not None:
                                    akum_amount = line['amount'] + previous_payslip[0].get('sum_total')
                                
                                self.env.cr.execute(
                                    '''select sum(ptx.amount) as sum_amount FROM hr_payslip p LEFT JOIN hr_payslip_tax_calculation ptx ON (p.id=ptx.slip_id) WHERE p.employee_id = %s and p.payslip_report_date < '%s' AND p.year = '%s' and p.state not in ('refund','cancel') and ptx.code = '%s' ''' % (
                                        payslip.employee_id.id, payslip.payslip_report_date, payslip.year, line['code']))
                                previous_tax = self.env.cr.dictfetchall()

                                amount_tax = 0
                                if previous_tax and previous_tax[0].get('sum_amount') is not None:
                                    amount_tax = previous_tax[0].get('sum_amount')

                                if akum_amount > natura_category.max_amount and amount_tax > 0:
                                    amount = line['amount']
                                elif akum_amount > natura_category.max_amount:
                                    amount = akum_amount - natura_category.max_amount
                                else:
                                    amount = 0
                        input_data = {
                            'name': line['name'],
                            'code': line['code'],
                            'sequence': line['sequence'],
                            'category_id': line['category_id'],
                            'employee_id': payslip.employee_id.id,
                            'tax_calculation_method': line['tax_calculation_method'],
                            'tax_category': line['tax_category'],
                            'amount': amount,
                        }
                        deduction_lines += [input_data]

                    payslip.write({'income_reguler_ids': [(0, 0, x) for x in income_reguler_lines], 'income_irreguler_ids': [(0, 0, x) for x in income_irreguler_lines], 'deduction_ids': [(0, 0, x) for x in deduction_lines]})

                    # get value from last month
                    if payslip.payslip_period_id.start_period_based_on == 'start_date':
                        date_period = payslip.date_from
                    elif payslip.payslip_period_id.start_period_based_on == 'end_date':
                        date_period = payslip.date_to
                    previous_month_date = datetime.strptime(str(date_period), '%Y-%m-%d') - relativedelta(months=1)
                    previous_month = previous_month_date.strftime("%B")

                    if payslip.termination:
                        self.env.cr.execute(
                            ''' select akum_income, akum_irreguler, akum_ded, pjk_terhutang_reguler, pjk_terhutang_irreguler, akum_income_gross, akum_irreguler_gross, akum_ded_gross, pjk_terhutang_reguler_gross, pjk_terhutang_irreguler_gross, pjk_terhutang_irreguler_last_month_gross, pjk_bln_irreguler_gross from hr_payslip WHERE employee_id = %s and month_name = '%s' AND year = '%s' and state not in ('refund','cancel') ORDER BY id DESC LIMIT 1 ''' % (
                                payslip.employee_id.id, previous_month, payslip.year))
                        last_payslip = self.env.cr.dictfetchall()
                        if last_payslip and payslip.employee_id.employee_tax_status == 'pegawai_tetap' and not payslip.employee_id.is_expatriate:
                            pjk_terhutang_irreguler_last_month_gross = last_payslip[0].get('pjk_terhutang_irreguler_last_month_gross') if last_payslip[0].get('pjk_terhutang_irreguler_last_month_gross') else 0
                            payslip.write({'akum_income_last_month': last_payslip[0].get('akum_income'),
                                        'akum_irreguler_last_month': last_payslip[0].get('akum_irreguler'),
                                        'akum_ded_last_month': last_payslip[0].get('akum_ded'),
                                        'pjk_terhutang_reguler_last_month': last_payslip[0].get('pjk_terhutang_reguler'),
                                        'pjk_terhutang_irreguler_last_month': last_payslip[0].get('pjk_terhutang_irreguler'),
                                        'akum_income_last_month_gross': last_payslip[0].get('akum_income_gross'),
                                        'akum_irreguler_last_month_gross': last_payslip[0].get('akum_irreguler_gross'),
                                        'akum_ded_last_month_gross': last_payslip[0].get('akum_ded_gross'),
                                        'pjk_terhutang_reguler_last_month_gross': last_payslip[0].get('pjk_terhutang_reguler_gross'),
                                        'pjk_terhutang_irreguler_last_month_gross': last_payslip[0].get('pjk_bln_irreguler_gross')  + pjk_terhutang_irreguler_last_month_gross
                                        })
                        else:
                            payslip.write({'akum_income_last_month': 0.0,
                                        'akum_irreguler_last_month': 0.0,
                                        'akum_ded_last_month': 0.0,
                                        'pjk_terhutang_reguler_last_month': 0.0,
                                        'pjk_terhutang_irreguler_last_month': 0.0,
                                        'akum_income_last_month_gross': 0.0,
                                        'akum_irreguler_last_month_gross': 0.0,
                                        'akum_ded_last_month_gross': 0.0,
                                        'pjk_terhutang_reguler_last_month_gross': 0.0,
                                        'pjk_terhutang_irreguler_last_month_gross': 0.0
                                        })
                        self.compute_pph_21_gross_final()
                        self.compute_pph_21_grossup_final()
                    else:
                        self.env.cr.execute(
                            ''' select akum_income, akum_irreguler, akum_ded, pjk_terhutang_reguler, pjk_terhutang_irreguler, akum_income_gross, akum_irreguler_gross, akum_ded_gross, pjk_terhutang_reguler_gross, pjk_terhutang_irreguler_gross, pjk_terhutang_irreguler_last_month_gross, pjk_bln_irreguler_gross from hr_payslip WHERE employee_id = %s and month_name = '%s' AND year = '%s' and state not in ('refund','cancel') ORDER BY id DESC LIMIT 1 ''' % (
                                payslip.employee_id.id, previous_month, payslip.year))
                        last_payslip = self.env.cr.dictfetchall()
                        if last_payslip and payslip.employee_id.employee_tax_status == 'pegawai_tetap' and not payslip.employee_id.is_expatriate:
                            pjk_terhutang_irreguler_last_month_gross = last_payslip[0].get('pjk_terhutang_irreguler_last_month_gross') if last_payslip[0].get('pjk_terhutang_irreguler_last_month_gross') else 0
                            if payslip.payslip_period_id.tax_calculation_method == "monthly":
                                payslip.write({'akum_income_last_month': 0.0,
                                            'akum_irreguler_last_month': last_payslip[0].get('akum_irreguler'),
                                            'akum_ded_last_month': 0.0,
                                            'pjk_terhutang_reguler_last_month': 0.0,
                                            'pjk_terhutang_irreguler_last_month': 0.0,
                                            'akum_income_last_month_gross': 0.0,
                                            'akum_irreguler_last_month_gross': last_payslip[0].get('akum_irreguler_gross'),
                                            'akum_ded_last_month_gross': 0.0,
                                            'pjk_terhutang_reguler_last_month_gross': 0.0,
                                            'pjk_terhutang_irreguler_last_month_gross': 0.0
                                            })
                            else:
                                payslip.write({'akum_income_last_month': last_payslip[0].get('akum_income'),
                                            'akum_irreguler_last_month': last_payslip[0].get('akum_irreguler'),
                                            'akum_ded_last_month': last_payslip[0].get('akum_ded'),
                                            'pjk_terhutang_reguler_last_month': last_payslip[0].get('pjk_terhutang_reguler'),
                                            'pjk_terhutang_irreguler_last_month': last_payslip[0].get('pjk_terhutang_irreguler'),
                                            'akum_income_last_month_gross': last_payslip[0].get('akum_income_gross'),
                                            'akum_irreguler_last_month_gross': last_payslip[0].get('akum_irreguler_gross'),
                                            'akum_ded_last_month_gross': last_payslip[0].get('akum_ded_gross'),
                                            'pjk_terhutang_reguler_last_month_gross': last_payslip[0].get('pjk_terhutang_reguler_gross'),
                                            'pjk_terhutang_irreguler_last_month_gross': last_payslip[0].get('pjk_bln_irreguler_gross') + pjk_terhutang_irreguler_last_month_gross
                                            })
                        else:
                            payslip.write({'akum_income_last_month': 0.0,
                                        'akum_irreguler_last_month': 0.0,
                                        'akum_ded_last_month': 0.0,
                                        'pjk_terhutang_reguler_last_month': 0.0,
                                        'pjk_terhutang_irreguler_last_month': 0.0,
                                        'akum_income_last_month_gross': 0.0,
                                        'akum_irreguler_last_month_gross': 0.0,
                                        'akum_ded_last_month_gross': 0.0,
                                        'pjk_terhutang_reguler_last_month_gross': 0.0,
                                        'pjk_terhutang_irreguler_last_month_gross': 0.0
                                        })

                    if not payslip.termination:
                        tunjangan_pjk = payslip.compute_pph_21_grossup()
                        payslip.tunj_pjk_reguler = tunjangan_pjk["tunj_pjk_reguler"]
                        payslip.tunj_pjk_irreguler = tunjangan_pjk["tunj_pjk_irreguler"]

                    if payslip.credit_note == True:
                        lines = [(0, 0, line) for line in self._get_payslip_lines(contract_ids, payslip.id)]
                        payslip.write({'line_ids': lines, 'number': number})
                    else:
                        for line in self._get_payslip_lines(contract_ids, payslip.id):
                            salary_rule = self.env['hr.salary.rule'].search([('id', '=', line['salary_rule_id'])], limit=1)
                            if not line['register_id']:
                                register_id = None
                            else:
                                register_id = line['register_id']
                            total = float(line['quantity']) * line['amount'] * line['rate'] / 100
                            company_id = payslip.employee_id.company_id.id
                            self.env.cr.execute("INSERT INTO "
                                                "hr_payslip_line(salary_rule_id,contract_id,name,code,category_id,sequence,"
                                                "appears_on_payslip,condition_select,condition_python,condition_range,condition_range_min,"
                                                "condition_range_max,amount_select,amount_fix,amount_python_compute,amount_percentage,"
                                                "amount_percentage_base,register_id,amount,employee_id,quantity,rate,slip_id,active,total,company_id,create_uid,create_date,write_uid,category_on_payslip,tax_category) "
                                                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                                                (line['salary_rule_id'], line['contract_id'],line['name'],line['code'],
                                                line['category_id'],line['sequence'],line['appears_on_payslip'],line['condition_select'],
                                                line['condition_python'],line['condition_range'],line['condition_range_min'],line['condition_range_max'],
                                                line['amount_select'],line['amount_fix'],line['amount_python_compute'],line['amount_percentage'],
                                                line['amount_percentage_base'],register_id,line['amount'],line['employee_id'],
                                                line['quantity'],line['rate'],payslip.id,'true',total,company_id,self.env.uid,
                                                datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),self.env.uid,salary_rule.category_on_payslip,salary_rule.tax_category))
                        payslip.write({'number': number})
                else:
                    for line in payslip.line_ids:
                        self.env.cr.execute("""DELETE FROM hr_payslip_line WHERE id = %s""" % (line.id))

                    contract_ids = payslip.contract_id.ids

                    salary_rules = self._get_payslip_lines(contract_ids, payslip.id)

                    rules_income_reguler = []
                    for rec in salary_rules:
                        self.env.cr.execute(
                            ''' select tax_category, tax_calculation_method from hr_salary_rule WHERE id = '%s' ''' % (rec['salary_rule_id']))
                        rules = self.env.cr.dictfetchall()
                        b = {'tax_category': rules[0].get('tax_category'),
                            'tax_calculation_method': rules[0].get('tax_calculation_method')}
                        rec.update(b)
                        if rec['tax_category'] == 'income_reguler':
                            rules_income_reguler.append(rec)

                    for line in payslip.income_reguler_ids:
                        self.env.cr.execute("""DELETE FROM hr_payslip_tax_calculation WHERE id = %s""" % (line.id))

                    income_reguler_lines = []
                    for line in rules_income_reguler:
                        input_data = {
                            'name': line['name'],
                            'code': line['code'],
                            'sequence': line['sequence'],
                            'category_id': line['category_id'],
                            'employee_id': payslip.employee_id.id,
                            'tax_calculation_method': line['tax_calculation_method'],
                            'tax_category': line['tax_category'],
                            'amount': line['amount'],
                        }
                        income_reguler_lines += [input_data]

                    payslip.write({'income_reguler_ids': [(0, 0, x) for x in income_reguler_lines]})

                    for line in self._get_payslip_lines(contract_ids, payslip.id):
                        salary_rule = self.env['hr.salary.rule'].search([('id', '=', line['salary_rule_id'])], limit=1)
                        if not line['register_id']:
                            register_id = None
                        else:
                            register_id = line['register_id']
                        total = float(line['quantity']) * line['amount'] * line['rate'] / 100
                        company_id = payslip.employee_id.company_id.id
                        self.env.cr.execute("INSERT INTO "
                                            "hr_payslip_line(salary_rule_id,contract_id,name,code,category_id,sequence,"
                                            "appears_on_payslip,condition_select,condition_python,condition_range,condition_range_min,"
                                            "condition_range_max,amount_select,amount_fix,amount_python_compute,amount_percentage,"
                                            "amount_percentage_base,register_id,amount,employee_id,quantity,rate,slip_id,active,total,company_id,create_uid,create_date,write_uid,category_on_payslip,tax_category) "
                                            "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                                            (line['salary_rule_id'], line['contract_id'], line['name'], line['code'],
                                            line['category_id'], line['sequence'], line['appears_on_payslip'],
                                            line['condition_select'],
                                            line['condition_python'], line['condition_range'], line['condition_range_min'],
                                            line['condition_range_max'],
                                            line['amount_select'], line['amount_fix'], line['amount_python_compute'],
                                            line['amount_percentage'],
                                            line['amount_percentage_base'], register_id, line['amount'],
                                            line['employee_id'],
                                            line['quantity'], line['rate'], payslip.id, 'true', total, company_id,
                                            self.env.uid,
                                            datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT), self.env.uid,
                                            salary_rule.category_on_payslip, salary_rule.tax_category))

                    payslip.write({'number': number})
            elif payslip.period_tax_calculation_schema == "pph21_ter":
                if payslip.emp_tax_status == 'pegawai_tetap':
                    if payslip.payslip_pesangon == False:
                        # delete old payslip lines
                        if payslip.credit_note == True:
                            payslip.line_ids.unlink()
                        else:
                            for line in payslip.line_ids:
                                self.env.cr.execute("""DELETE FROM hr_payslip_line WHERE id = %s""" % (line.id))
                        # set the list of contract for which the rules have to be applied
                        # if we don't give the contract, then the rules to apply should be for all current contracts of the employee
                        contract_ids = payslip.contract_id.ids or \
                                    self.get_contract(payslip.employee_id, payslip.date_from, payslip.date_to)

                        salary_rules = self._get_payslip_lines(contract_ids, payslip.id)

                        rules_income_reguler_ter = []
                        rules_income_irreguler_ter = []
                        rules_deduction_ter = []
                        for rec in salary_rules:
                            self.env.cr.execute(
                                ''' select tax_category, category_on_natura_tax from hr_salary_rule WHERE id = '%s' ''' % (rec['salary_rule_id']))
                            rules = self.env.cr.dictfetchall()
                            b = {'tax_category': rules[0].get('tax_category'),
                                'category_on_natura_tax': rules[0].get('category_on_natura_tax')}
                            rec.update(b)
                            if rec['tax_category'] == 'income_reguler':
                                rules_income_reguler_ter.append(rec)
                            if rec['tax_category'] == 'income_irreguler':
                                rules_income_irreguler_ter.append(rec)
                            if rec['tax_category'] == 'deduction':
                                rules_deduction_ter.append(rec)
                        
                        for line in payslip.income_reguler_ter_ids:
                            self.env.cr.execute("""DELETE FROM hr_payslip_tax_ter_calculation WHERE id = %s""" % (line.id))

                        income_reguler_ter_lines = []
                        for line in rules_income_reguler_ter:
                            amount = line['amount']
                            if line['category_on_natura_tax']:
                                natura_category = self.env['hr.natura.category'].sudo().browse(int(line['category_on_natura_tax']))
                                if natura_category.schema_type == "monthly":
                                    if line['amount'] > natura_category.max_amount:
                                        amount = line['amount'] - natura_category.max_amount
                                    else:
                                        amount = 0
                                elif natura_category.schema_type == "yearly":
                                    self.env.cr.execute(
                                        '''select sum(pl.total) as sum_total FROM hr_payslip p LEFT JOIN hr_payslip_line pl ON (p.id=pl.slip_id) WHERE p.employee_id = %s and p.payslip_report_date < '%s' AND p.year = '%s' and p.state not in ('refund','cancel') and pl.salary_rule_id = %s''' % (
                                            payslip.employee_id.id, payslip.payslip_report_date, payslip.year, line['salary_rule_id']))
                                    previous_payslip = self.env.cr.dictfetchall()
                                    akum_amount = line['amount']
                                    if previous_payslip and previous_payslip[0].get('sum_total') is not None:
                                        akum_amount = line['amount'] + previous_payslip[0].get('sum_total')
                                    
                                    self.env.cr.execute(
                                        '''select sum(ptx.amount) as sum_amount FROM hr_payslip p LEFT JOIN hr_payslip_tax_ter_calculation ptx ON (p.id=ptx.slip_id) WHERE p.employee_id = %s and p.payslip_report_date < '%s' AND p.year = '%s' and p.state not in ('refund','cancel') and ptx.code = '%s' ''' % (
                                            payslip.employee_id.id, payslip.payslip_report_date, payslip.year, line['code']))
                                    previous_tax = self.env.cr.dictfetchall()

                                    amount_tax = 0
                                    if previous_tax and previous_tax[0].get('sum_amount') is not None:
                                        amount_tax = previous_tax[0].get('sum_amount')

                                    if akum_amount > natura_category.max_amount and amount_tax > 0:
                                        amount = line['amount']
                                    elif akum_amount > natura_category.max_amount:
                                        amount = akum_amount - natura_category.max_amount
                                    else:
                                        amount = 0
                            input_data = {
                                'name': line['name'],
                                'code': line['code'],
                                'sequence': line['sequence'],
                                'category_id': line['category_id'],
                                'employee_id': payslip.employee_id.id,
                                'tax_category': line['tax_category'],
                                'category_on_natura_tax_id': line['category_on_natura_tax'],
                                'amount': amount,
                            }
                            income_reguler_ter_lines += [input_data]
                        
                        for line in payslip.income_irreguler_ter_ids:
                            self.env.cr.execute("""DELETE FROM hr_payslip_tax_ter_calculation WHERE id = %s""" % (line.id))

                        income_irreguler_ter_lines = []
                        for line in rules_income_irreguler_ter:
                            amount = line['amount']
                            if line['category_on_natura_tax']:
                                natura_category = self.env['hr.natura.category'].sudo().browse(int(line['category_on_natura_tax']))
                                if natura_category.schema_type == "monthly":
                                    if line['amount'] > natura_category.max_amount:
                                        amount = line['amount'] - natura_category.max_amount
                                    else:
                                        amount = 0
                                elif natura_category.schema_type == "yearly":
                                    self.env.cr.execute(
                                        '''select sum(pl.total) as sum_total FROM hr_payslip p LEFT JOIN hr_payslip_line pl ON (p.id=pl.slip_id) WHERE p.employee_id = %s and p.payslip_report_date < '%s' AND p.year = '%s' and p.state not in ('refund','cancel') and pl.salary_rule_id = %s''' % (
                                            payslip.employee_id.id, payslip.payslip_report_date, payslip.year, line['salary_rule_id']))
                                    previous_payslip = self.env.cr.dictfetchall()
                                    akum_amount = line['amount']
                                    if previous_payslip and previous_payslip[0].get('sum_total') is not None:
                                        akum_amount = line['amount'] + previous_payslip[0].get('sum_total')
                                    
                                    self.env.cr.execute(
                                        '''select sum(ptx.amount) as sum_amount FROM hr_payslip p LEFT JOIN hr_payslip_tax_ter_calculation ptx ON (p.id=ptx.slip_id) WHERE p.employee_id = %s and p.payslip_report_date < '%s' AND p.year = '%s' and p.state not in ('refund','cancel') and ptx.code = '%s' ''' % (
                                            payslip.employee_id.id, payslip.payslip_report_date, payslip.year, line['code']))
                                    previous_tax = self.env.cr.dictfetchall()

                                    amount_tax = 0
                                    if previous_tax and previous_tax[0].get('sum_amount') is not None:
                                        amount_tax = previous_tax[0].get('sum_amount')

                                    if akum_amount > natura_category.max_amount and amount_tax > 0:
                                        amount = line['amount']
                                    elif akum_amount > natura_category.max_amount:
                                        amount = akum_amount - natura_category.max_amount
                                    else:
                                        amount = 0
                            input_data = {
                                'name': line['name'],
                                'code': line['code'],
                                'sequence': line['sequence'],
                                'category_id': line['category_id'],
                                'employee_id': payslip.employee_id.id,
                                'tax_category': line['tax_category'],
                                'category_on_natura_tax_id': line['category_on_natura_tax'],
                                'amount': amount,
                            }
                            income_irreguler_ter_lines += [input_data]
                        
                        for line in payslip.deduction_ter_ids:
                            self.env.cr.execute("""DELETE FROM hr_payslip_tax_ter_calculation WHERE id = %s""" % (line.id))

                        deduction_ter_lines = []
                        for line in rules_deduction_ter:
                            amount = line['amount']
                            if line['category_on_natura_tax']:
                                natura_category = self.env['hr.natura.category'].sudo().browse(int(line['category_on_natura_tax']))
                                if natura_category.schema_type == "monthly":
                                    if line['amount'] > natura_category.max_amount:
                                        amount = line['amount'] - natura_category.max_amount
                                    else:
                                        amount = 0
                                elif natura_category.schema_type == "yearly":
                                    self.env.cr.execute(
                                        '''select sum(pl.total) as sum_total FROM hr_payslip p LEFT JOIN hr_payslip_line pl ON (p.id=pl.slip_id) WHERE p.employee_id = %s and p.payslip_report_date < '%s' AND p.year = '%s' and p.state not in ('refund','cancel') and pl.salary_rule_id = %s''' % (
                                            payslip.employee_id.id, payslip.payslip_report_date, payslip.year, line['salary_rule_id']))
                                    previous_payslip = self.env.cr.dictfetchall()
                                    akum_amount = line['amount']
                                    if previous_payslip and previous_payslip[0].get('sum_total') is not None:
                                        akum_amount = line['amount'] + previous_payslip[0].get('sum_total')
                                    
                                    self.env.cr.execute(
                                        '''select sum(ptx.amount) as sum_amount FROM hr_payslip p LEFT JOIN hr_payslip_tax_ter_calculation ptx ON (p.id=ptx.slip_id) WHERE p.employee_id = %s and p.payslip_report_date < '%s' AND p.year = '%s' and p.state not in ('refund','cancel') and ptx.code = '%s' ''' % (
                                            payslip.employee_id.id, payslip.payslip_report_date, payslip.year, line['code']))
                                    previous_tax = self.env.cr.dictfetchall()

                                    amount_tax = 0
                                    if previous_tax and previous_tax[0].get('sum_amount') is not None:
                                        amount_tax = previous_tax[0].get('sum_amount')

                                    if akum_amount > natura_category.max_amount and amount_tax > 0:
                                        amount = line['amount']
                                    elif akum_amount > natura_category.max_amount:
                                        amount = akum_amount - natura_category.max_amount
                                    else:
                                        amount = 0
                            input_data = {
                                'name': line['name'],
                                'code': line['code'],
                                'sequence': line['sequence'],
                                'category_id': line['category_id'],
                                'employee_id': payslip.employee_id.id,
                                'tax_category': line['tax_category'],
                                'category_on_natura_tax_id': line['category_on_natura_tax'],
                                'amount': amount,
                            }
                            deduction_ter_lines += [input_data]
                        
                        payslip.write({'income_reguler_ter_ids': [(0, 0, x) for x in income_reguler_ter_lines], 'income_irreguler_ter_ids': [(0, 0, x) for x in income_irreguler_ter_lines], 'deduction_ter_ids': [(0, 0, x) for x in deduction_ter_lines]})

                        # get value from last month
                        if payslip.payslip_period_id.start_period_based_on == 'start_date':
                            date_period = payslip.date_from
                        elif payslip.payslip_period_id.start_period_based_on == 'end_date':
                            date_period = payslip.date_to
                        previous_month_date = datetime.strptime(str(date_period), '%Y-%m-%d') - relativedelta(months=1)
                        previous_month = previous_month_date.strftime("%B")

                        self.env.cr.execute(
                            ''' select ter_akum_income_reguler, ter_akum_income_irreguler, ter_akum_ded, ter_pjk_terhutang_reguler, ter_pjk_terhutang_irreguler, ter_akum_income_reguler_gross, ter_akum_income_irreguler_gross, ter_akum_ded_gross, ter_pjk_terhutang_reguler_gross, ter_pjk_terhutang_irreguler_gross, ter_akum_income_reguler_non_natura, ter_akum_income_irreguler_non_natura, ter_akum_ded_non_natura, ter_pjk_terhutang_reguler_non_natura, ter_pjk_terhutang_irreguler_non_natura, ter_akum_income_reguler_gross_non_natura, ter_akum_income_irreguler_gross_non_natura, ter_akum_ded_gross_non_natura, ter_pjk_terhutang_reguler_gross_non_natura, ter_pjk_terhutang_irreguler_gross_non_natura from hr_payslip WHERE employee_id = %s and month_name = '%s' AND year = '%s' and state not in ('refund','cancel') ORDER BY id DESC LIMIT 1 ''' % (
                                payslip.employee_id.id, previous_month, payslip.year))
                        last_payslip = self.env.cr.dictfetchall()
                        if last_payslip and payslip.employee_id.employee_tax_status == 'pegawai_tetap' and not payslip.employee_id.is_expatriate:
                            payslip.write({'ter_akum_income_last_month': last_payslip[0].get('ter_akum_income_reguler'),
                                        'ter_akum_irreguler_last_month': last_payslip[0].get('ter_akum_income_irreguler'),
                                        'ter_akum_ded_last_month': last_payslip[0].get('ter_akum_ded'),
                                        'ter_pjk_terhutang_reguler_last_month': last_payslip[0].get('ter_pjk_terhutang_reguler'),
                                        'ter_pjk_terhutang_irreguler_last_month': last_payslip[0].get('ter_pjk_terhutang_irreguler'),
                                        'ter_akum_income_last_month_gross': last_payslip[0].get('ter_akum_income_reguler_gross'),
                                        'ter_akum_irreguler_last_month_gross': last_payslip[0].get('ter_akum_income_irreguler_gross'),
                                        'ter_akum_ded_last_month_gross': last_payslip[0].get('ter_akum_ded_gross'),
                                        'ter_pjk_terhutang_reguler_last_month_gross': last_payslip[0].get('ter_pjk_terhutang_reguler_gross'),
                                        'ter_pjk_terhutang_irreguler_last_month_gross': last_payslip[0].get('ter_pjk_terhutang_irreguler_gross'),
                                        'ter_akum_income_last_month_non_natura': last_payslip[0].get('ter_akum_income_reguler_non_natura'),
                                        'ter_akum_irreguler_last_month_non_natura': last_payslip[0].get('ter_akum_income_irreguler_non_natura'),
                                        'ter_akum_ded_last_month_non_natura': last_payslip[0].get('ter_akum_ded_non_natura'),
                                        'ter_pjk_terhutang_reguler_last_month_non_natura': last_payslip[0].get('ter_pjk_terhutang_reguler_non_natura'),
                                        'ter_pjk_terhutang_irreguler_last_month_non_natura': last_payslip[0].get('ter_pjk_terhutang_irreguler_non_natura'),
                                        'ter_akum_income_last_month_gross_non_natura': last_payslip[0].get('ter_akum_income_reguler_gross_non_natura'),
                                        'ter_akum_irreguler_last_month_gross_non_natura': last_payslip[0].get('ter_akum_income_irreguler_gross_non_natura'),
                                        'ter_akum_ded_last_month_gross_non_natura': last_payslip[0].get('ter_akum_ded_gross_non_natura'),
                                        'ter_pjk_terhutang_reguler_last_month_gross_non_natura': last_payslip[0].get('ter_pjk_terhutang_reguler_gross_non_natura'),
                                        'ter_pjk_terhutang_irreguler_last_month_gross_non_natura': last_payslip[0].get('ter_pjk_terhutang_irreguler_gross_non_natura'),
                                        })
                        else:
                            payslip.write({'ter_akum_income_last_month': 0.0,
                                        'ter_akum_irreguler_last_month': 0.0,
                                        'ter_akum_ded_last_month': 0.0,
                                        'ter_pjk_terhutang_reguler_last_month': 0.0,
                                        'ter_pjk_terhutang_irreguler_last_month': 0.0,
                                        'ter_akum_income_last_month_gross': 0.0,
                                        'ter_akum_irreguler_last_month_gross': 0.0,
                                        'ter_akum_ded_last_month_gross': 0.0,
                                        'ter_pjk_terhutang_reguler_last_month_gross': 0.0,
                                        'ter_pjk_terhutang_irreguler_last_month_gross': 0.0,
                                        'ter_akum_income_last_month_non_natura': 0.0,
                                        'ter_akum_irreguler_last_month_non_natura': 0.0,
                                        'ter_akum_ded_last_month_non_natura': 0.0,
                                        'ter_pjk_terhutang_reguler_last_month_non_natura': 0.0,
                                        'ter_pjk_terhutang_irreguler_last_month_non_natura': 0.0,
                                        'ter_akum_income_last_month_gross_non_natura': 0.0,
                                        'ter_akum_irreguler_last_month_gross_non_natura': 0.0,
                                        'ter_akum_ded_last_month_gross_non_natura': 0.0,
                                        'ter_pjk_terhutang_reguler_last_month_gross_non_natura': 0.0,
                                        'ter_pjk_terhutang_irreguler_last_month_gross_non_natura': 0.0,
                                        })
                            
                        if not payslip.termination:
                            ter_tunjangan_pjk = payslip.compute_ter_pph_21_grossup()
                            payslip.ter_tunj_pjk_terhutang_reguler = ter_tunjangan_pjk["ter_tunj_pjk_reguler"]
                            payslip.ter_tunj_pjk_terhutang_irreguler = ter_tunjangan_pjk["ter_tunj_pjk_irreguler"]
                            ter_tunj_pjk_bln = payslip.compute_ter_tunj_pph_21_bln()
                            payslip.ter_tunj_pjk_bln = ter_tunj_pjk_bln["ter_tunj_pjk_bln"]
                            ter_tunjangan_pjk_non_natura = payslip.compute_ter_pph_21_grossup_non_natura()
                            payslip.ter_tunj_pjk_terhutang_reguler_non_natura = ter_tunjangan_pjk_non_natura["ter_tunj_pjk_reguler_non_natura"]
                            payslip.ter_tunj_pjk_terhutang_irreguler_non_natura = ter_tunjangan_pjk_non_natura["ter_tunj_pjk_irreguler_non_natura"]
                            ter_tunj_pjk_bln_non_natura = payslip.compute_ter_tunj_pph_21_bln_non_natura()
                            payslip.ter_tunj_pjk_bln_non_natura = ter_tunj_pjk_bln_non_natura["ter_tunj_pjk_bln_non_natura"]

                        if payslip.credit_note == True:
                            lines = [(0, 0, line) for line in self._get_payslip_lines(contract_ids, payslip.id)]
                            payslip.write({'line_ids': lines, 'number': number})
                        else:
                            for line in self._get_payslip_lines(contract_ids, payslip.id):
                                salary_rule = self.env['hr.salary.rule'].search([('id', '=', line['salary_rule_id'])], limit=1)
                                if not line['register_id']:
                                    register_id = None
                                else:
                                    register_id = line['register_id']
                                total = float(line['quantity']) * line['amount'] * line['rate'] / 100
                                company_id = payslip.employee_id.company_id.id
                                self.env.cr.execute("INSERT INTO "
                                                    "hr_payslip_line(salary_rule_id,contract_id,name,code,category_id,sequence,"
                                                    "appears_on_payslip,condition_select,condition_python,condition_range,condition_range_min,"
                                                    "condition_range_max,amount_select,amount_fix,amount_python_compute,amount_percentage,"
                                                    "amount_percentage_base,register_id,amount,employee_id,quantity,rate,slip_id,active,total,company_id,create_uid,create_date,write_uid,category_on_payslip,tax_category) "
                                                    "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                                                    (line['salary_rule_id'], line['contract_id'],line['name'],line['code'],
                                                    line['category_id'],line['sequence'],line['appears_on_payslip'],line['condition_select'],
                                                    line['condition_python'],line['condition_range'],line['condition_range_min'],line['condition_range_max'],
                                                    line['amount_select'],line['amount_fix'],line['amount_python_compute'],line['amount_percentage'],
                                                    line['amount_percentage_base'],register_id,line['amount'],line['employee_id'],
                                                    line['quantity'],line['rate'],payslip.id,'true',total,company_id,self.env.uid,
                                                    datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),self.env.uid,salary_rule.category_on_payslip,salary_rule.tax_category))
                            payslip.write({'number': number})
                elif payslip.emp_tax_status == 'pegawai_tidak_tetap':
                    if payslip.payslip_pesangon == False:
                        # delete old payslip lines
                        if payslip.credit_note == True:
                            payslip.line_ids.unlink()
                        else:
                            for line in payslip.line_ids:
                                self.env.cr.execute("""DELETE FROM hr_payslip_line WHERE id = %s""" % (line.id))
                        # set the list of contract for which the rules have to be applied
                        # if we don't give the contract, then the rules to apply should be for all current contracts of the employee
                        contract_ids = payslip.contract_id.ids or \
                                    self.get_contract(payslip.employee_id, payslip.date_from, payslip.date_to)

                        salary_rules = self._get_payslip_lines(contract_ids, payslip.id)

                        rules_income_reguler_non_permanent = []
                        rules_income_irreguler_non_permanent = []
                        for rec in salary_rules:
                            self.env.cr.execute(
                                ''' select tax_category, category_on_natura_tax from hr_salary_rule WHERE id = '%s' ''' % (rec['salary_rule_id']))
                            rules = self.env.cr.dictfetchall()
                            b = {'tax_category': rules[0].get('tax_category'),
                                'category_on_natura_tax': rules[0].get('category_on_natura_tax')}
                            rec.update(b)
                            if rec['tax_category'] == 'income_reguler':
                                rules_income_reguler_non_permanent.append(rec)
                            if rec['tax_category'] == 'income_irreguler':
                                rules_income_irreguler_non_permanent.append(rec)
                        
                        for line in payslip.income_reguler_non_permanent_ids:
                            self.env.cr.execute("""DELETE FROM hr_payslip_tax_non_permanent WHERE id = %s""" % (line.id))
                        
                        income_reguler_ter_non_permanent_lines = []
                        for line in rules_income_reguler_non_permanent:
                            amount = line['amount']
                            input_data = {
                                'name': line['name'],
                                'code': line['code'],
                                'sequence': line['sequence'],
                                'category_id': line['category_id'],
                                'employee_id': payslip.employee_id.id,
                                'tax_category': line['tax_category'],
                                'category_on_natura_tax_id': line['category_on_natura_tax'],
                                'amount': amount,
                            }
                            income_reguler_ter_non_permanent_lines += [input_data]

                        for line in payslip.income_irreguler_non_permanent_ids:
                            self.env.cr.execute("""DELETE FROM hr_payslip_tax_non_permanent WHERE id = %s""" % (line.id))

                        income_irreguler_ter_non_permanent_lines = []
                        for line in rules_income_irreguler_non_permanent:
                            amount = line['amount']
                            input_data = {
                                'name': line['name'],
                                'code': line['code'],
                                'sequence': line['sequence'],
                                'category_id': line['category_id'],
                                'employee_id': payslip.employee_id.id,
                                'tax_category': line['tax_category'],
                                'category_on_natura_tax_id': line['category_on_natura_tax'],
                                'amount': amount,
                            }
                            income_irreguler_ter_non_permanent_lines += [input_data]
                        
                        payslip.write({'income_reguler_non_permanent_ids': [(0, 0, x) for x in income_reguler_ter_non_permanent_lines], 'income_irreguler_non_permanent_ids': [(0, 0, x) for x in income_irreguler_ter_non_permanent_lines]})

                        if payslip.credit_note == True:
                            lines = [(0, 0, line) for line in self._get_payslip_lines(contract_ids, payslip.id)]
                            payslip.write({'line_ids': lines, 'number': number})
                        else:
                            for line in self._get_payslip_lines(contract_ids, payslip.id):
                                salary_rule = self.env['hr.salary.rule'].search([('id', '=', line['salary_rule_id'])], limit=1)
                                if not line['register_id']:
                                    register_id = None
                                else:
                                    register_id = line['register_id']
                                total = float(line['quantity']) * line['amount'] * line['rate'] / 100
                                company_id = payslip.employee_id.company_id.id
                                self.env.cr.execute("INSERT INTO "
                                                    "hr_payslip_line(salary_rule_id,contract_id,name,code,category_id,sequence,"
                                                    "appears_on_payslip,condition_select,condition_python,condition_range,condition_range_min,"
                                                    "condition_range_max,amount_select,amount_fix,amount_python_compute,amount_percentage,"
                                                    "amount_percentage_base,register_id,amount,employee_id,quantity,rate,slip_id,active,total,company_id,create_uid,create_date,write_uid,category_on_payslip,tax_category) "
                                                    "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                                                    (line['salary_rule_id'], line['contract_id'],line['name'],line['code'],
                                                    line['category_id'],line['sequence'],line['appears_on_payslip'],line['condition_select'],
                                                    line['condition_python'],line['condition_range'],line['condition_range_min'],line['condition_range_max'],
                                                    line['amount_select'],line['amount_fix'],line['amount_python_compute'],line['amount_percentage'],
                                                    line['amount_percentage_base'],register_id,line['amount'],line['employee_id'],
                                                    line['quantity'],line['rate'],payslip.id,'true',total,company_id,self.env.uid,
                                                    datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),self.env.uid,salary_rule.category_on_payslip,salary_rule.tax_category))
                            payslip.write({'number': number})
        return True

    def compute_tax_bracket(self, pkp=0.0, npwp=False):
        amount = pkp
        amounts = amount
        total = 0
        tax_bracket = self.env['hr.tax.bracket'].sudo().search([])
        for tax in tax_bracket:
            tax_rate = tax.tax_rate / 100.00
            tax_penalty_rate = tax.tax_penalty_rate / 100.00
            net = amounts - tax.taxable_income_to
            if npwp:
                if net <= 0:
                    total += amount * tax_rate
                    break
                else:
                    total += (tax.taxable_income_to - tax.taxable_income_from) * tax_rate
                    amount = amount - (tax.taxable_income_to - tax.taxable_income_from)
            else:
                if net <= 0:
                    total += amount * tax_penalty_rate
                    break
                else:
                    total += (tax.taxable_income_to - tax.taxable_income_from) * tax_penalty_rate
                    amount = amount - (tax.taxable_income_to - tax.taxable_income_from)

        return total

    def compute_tax_harian_lepas(self, income_reguler=0.0, pkp=0.0, npwp=False):
        total = 0
        tax_harian_lepas = self.env['hr.tax.ptkp.harian.lepas'].sudo().search([], limit=1)
        tax_rates = tax_harian_lepas.tax_rate
        tax_penalty_rates = tax_harian_lepas.tax_penalty_rate
        tax_rate = tax_rates / 100.00
        tax_penalty_rate = tax_penalty_rates / 100.00
        if income_reguler >= tax_harian_lepas.cummulative_income_start and income_reguler <= tax_harian_lepas.cummulative_income_end:
            if npwp:
                total = pkp * tax_rate
            else:
                total = pkp * tax_penalty_rate
        elif income_reguler > tax_harian_lepas.cummulative_income_end:
            total = self.compute_tax_bracket(pkp, npwp)
        return total

    def compute_pesangon_bracket(self, yos, rules=False):
        total = 0.0
        pesangon_bracket = self.env['hr.pesangon.upmk.settings'].sudo().search([], limit=1)
        for pesangon in pesangon_bracket:
            years = 0
            values = 0
            num = 0
            count = len(pesangon.pesangon_setting_ids)
            for rec in pesangon.pesangon_setting_ids:
                num += 1
                if num == count and yos >= rec.year_of_services:
                    pesangon_rules = [i.code for i in rec.salary_rules]
                    sub_total = 0.0
                    for rule in rules:
                        if rule.code in pesangon_rules:
                            sub_total += rule.amount
                    total = rec.value * sub_total
                    break
                elif yos >= years and yos < rec.year_of_services:
                    pesangon_rules = [i.code for i in rec.salary_rules]
                    sub_total = 0.0
                    for rule in rules:
                        if rule.code in pesangon_rules:
                            sub_total += rule.amount
                    total = values * sub_total
                    break
                else:
                    years = rec.year_of_services
                    values = rec.value
        return total

    def compute_upmk_bracket(self, yos=0, rules=False):
        total = 0.0
        pesangon_bracket = self.env['hr.pesangon.upmk.settings'].sudo().search([], limit=1)
        for pesangon in pesangon_bracket:
            years = 0
            values = 0
            num = 0
            count = len(pesangon.upmk_setting_ids)
            for rec in pesangon.upmk_setting_ids:
                num += 1
                if num == count and yos >= rec.year_of_services:
                    pesangon_rules = [i.code for i in rec.salary_rules]
                    sub_total = 0.0
                    for rule in rules:
                        if rule.code in pesangon_rules:
                            sub_total += rule.amount
                    total = rec.value * sub_total
                    break
                elif yos >= years and yos < rec.year_of_services:
                    pesangon_rules = [i.code for i in rec.salary_rules]
                    sub_total = 0.0
                    for rule in rules:
                        if rule.code in pesangon_rules:
                            sub_total += rule.amount
                    total = values * sub_total
                    break
                else:
                    years = rec.year_of_services
                    values = rec.value
        return total

    def compute_tax_pesangon_bracket(self, nilai=0.0):
        amount = nilai
        amounts = amount
        total = 0
        tax_pesangon_bracket = self.env['hr.tax.bracket.pesangon.upmk'].sudo().search([])
        for tax in tax_pesangon_bracket:
            tax_rate = tax.tax_rate / 100.00
            net = amounts - tax.tax_income_to
            if net <= 0:
                total += amount * tax_rate
                break
            else:
                total += (tax.tax_income_to - tax.tax_income_from) * tax_rate
                amount = amount - (tax.tax_income_to - tax.tax_income_from)

        return total

    def compute_pph21_pesangon_calculation(self, nilai=0.0):
        amount = nilai
        amounts = amount
        pph21_pesangon = []
        tax_pesangon_bracket = self.env['hr.tax.bracket.pesangon.upmk'].sudo().search([])
        for tax in tax_pesangon_bracket:
            tax_rate = tax.tax_rate / 100.00
            net = amounts - tax.tax_income_to
            if net <= 0:
                bruto_pesangon = amount
                total = bruto_pesangon * tax_rate
                input_data = {
                    'sequence': tax.sequence,
                    'name': tax.name,
                    'tax_income_from': tax.tax_income_from,
                    'tax_income_to': tax.tax_income_to,
                    'tax_rate': tax.tax_rate,
                    'bruto_pesangon': round(bruto_pesangon),
                    'pph21_amount': round(total),
                }
                pph21_pesangon += [input_data]
                break
            else:
                amount_diff = (tax.tax_income_to - tax.tax_income_from)
                bruto_pesangon = amount_diff
                total = (tax.tax_income_to - tax.tax_income_from) * tax_rate
                amount = amount - (tax.tax_income_to - tax.tax_income_from)

            input_data = {
                'sequence': tax.sequence,
                'name': tax.name,
                'tax_income_from': tax.tax_income_from,
                'tax_income_to': tax.tax_income_to,
                'tax_rate': tax.tax_rate,
                'bruto_pesangon': round(bruto_pesangon),
                'pph21_amount': round(total),
            }
            pph21_pesangon += [input_data]

        return pph21_pesangon

    def compute_pph21_bracket_calculation(self, pkp=0.0, npwp=False):
        amount = pkp
        amounts = amount
        total = 0
        pph21_bracket = []
        tax_bracket = self.env['hr.tax.bracket'].sudo().search([])
        for tax in tax_bracket:
            tax_rate = tax.tax_rate / 100.00
            tax_penalty_rate = tax.tax_penalty_rate / 100.00
            net = amounts - tax.taxable_income_to
            if npwp:
                if net <= 0:
                    pkp_thn = amount
                    total += pkp_thn * tax_rate
                    input_data = {
                        'sequence': tax.sequence,
                        'name': tax.name,
                        'tax_income_from': tax.taxable_income_from,
                        'tax_income_to': tax.taxable_income_to,
                        'tax_rate': tax.tax_rate,
                        'tax_penalty_rate': tax.tax_penalty_rate,
                        'pkp': round(pkp_thn),
                        'pph21_amount': round(total),
                    }
                    pph21_bracket += [input_data]
                    break
                else:
                    amount_diff = (tax.taxable_income_to - tax.taxable_income_from)
                    pkp_thn = amount_diff
                    total += (tax.taxable_income_to - tax.taxable_income_from) * tax_rate
                    amount = amount - (tax.taxable_income_to - tax.taxable_income_from)
                input_data = {
                    'sequence': tax.sequence,
                    'name': tax.name,
                    'tax_income_from': tax.taxable_income_from,
                    'tax_income_to': tax.taxable_income_to,
                    'tax_rate': tax.tax_rate,
                    'tax_penalty_rate': tax.tax_penalty_rate,
                    'pkp': round(pkp_thn),
                    'pph21_amount': round(total),
                }
                pph21_bracket += [input_data]
            else:
                if net <= 0:
                    pkp_thn = amount
                    total += pkp_thn * tax_penalty_rate
                    input_data = {
                        'sequence': tax.sequence,
                        'name': tax.name,
                        'tax_income_from': tax.taxable_income_from,
                        'tax_income_to': tax.taxable_income_to,
                        'tax_rate': tax.tax_rate,
                        'tax_penalty_rate': tax.tax_penalty_rate,
                        'pkp': round(pkp_thn),
                        'pph21_amount': round(total),
                    }
                    pph21_bracket += [input_data]
                    break
                else:
                    amount_diff = (tax.taxable_income_to - tax.taxable_income_from)
                    pkp_thn = amount_diff
                    total += (tax.taxable_income_to - tax.taxable_income_from) * tax_penalty_rate
                    amount = amount - (tax.taxable_income_to - tax.taxable_income_from)
                input_data = {
                    'sequence': tax.sequence,
                    'name': tax.name,
                    'tax_income_from': tax.taxable_income_from,
                    'tax_income_to': tax.taxable_income_to,
                    'tax_rate': tax.tax_rate,
                    'tax_penalty_rate': tax.tax_penalty_rate,
                    'pkp': round(pkp_thn),
                    'pph21_amount': round(total),
                }
                pph21_bracket += [input_data]
        return pph21_bracket
    
    def compute_pph21_gross_bracket_calculation(self, pkp=0.0, npwp=False):
        amount = pkp
        amounts = amount
        total = 0
        pph21_bracket = []
        tax_bracket = self.env['hr.tax.bracket'].sudo().search([])
        for tax in tax_bracket:
            tax_rate = tax.tax_rate / 100.00
            tax_penalty_rate = tax.tax_penalty_rate / 100.00
            net = amounts - tax.taxable_income_to
            if npwp:
                if net <= 0:
                    pkp_thn = amount
                    total += pkp_thn * tax_rate
                    input_data = {
                        'sequence': tax.sequence,
                        'name': tax.name,
                        'tax_income_from': tax.taxable_income_from,
                        'tax_income_to': tax.taxable_income_to,
                        'tax_rate': tax.tax_rate,
                        'tax_penalty_rate': tax.tax_penalty_rate,
                        'pkp': round(pkp_thn),
                        'pph21_amount': round(total),
                    }
                    pph21_bracket += [input_data]
                    break
                else:
                    amount_diff = (tax.taxable_income_to - tax.taxable_income_from)
                    pkp_thn = amount_diff
                    total += (tax.taxable_income_to - tax.taxable_income_from) * tax_rate
                    amount = amount - (tax.taxable_income_to - tax.taxable_income_from)
                input_data = {
                    'sequence': tax.sequence,
                    'name': tax.name,
                    'tax_income_from': tax.taxable_income_from,
                    'tax_income_to': tax.taxable_income_to,
                    'tax_rate': tax.tax_rate,
                    'tax_penalty_rate': tax.tax_penalty_rate,
                    'pkp': round(pkp_thn),
                    'pph21_amount': round(total),
                }
                pph21_bracket += [input_data]
            else:
                if net <= 0:
                    pkp_thn = amount
                    total += pkp_thn * tax_penalty_rate
                    input_data = {
                        'sequence': tax.sequence,
                        'name': tax.name,
                        'tax_income_from': tax.taxable_income_from,
                        'tax_income_to': tax.taxable_income_to,
                        'tax_rate': tax.tax_rate,
                        'tax_penalty_rate': tax.tax_penalty_rate,
                        'pkp': round(pkp_thn),
                        'pph21_amount': round(total),
                    }
                    pph21_bracket += [input_data]
                    break
                else:
                    amount_diff = (tax.taxable_income_to - tax.taxable_income_from)
                    pkp_thn = amount_diff
                    total += (tax.taxable_income_to - tax.taxable_income_from) * tax_penalty_rate
                    amount = amount - (tax.taxable_income_to - tax.taxable_income_from)
                input_data = {
                    'sequence': tax.sequence,
                    'name': tax.name,
                    'tax_income_from': tax.taxable_income_from,
                    'tax_income_to': tax.taxable_income_to,
                    'tax_rate': tax.tax_rate,
                    'tax_penalty_rate': tax.tax_penalty_rate,
                    'pkp': round(pkp_thn),
                    'pph21_amount': round(total),
                }
                pph21_bracket += [input_data]
        return pph21_bracket
    
    def compute_pph21_gross_bracket_calculation(self, pkp=0.0, npwp=False):
        amount = pkp
        amounts = amount
        total = 0
        pph21_bracket = []
        tax_bracket = self.env['hr.tax.bracket'].sudo().search([])
        for tax in tax_bracket:
            tax_rate = tax.tax_rate / 100.00
            tax_penalty_rate = tax.tax_penalty_rate / 100.00
            net = amounts - tax.taxable_income_to
            if npwp:
                if net <= 0:
                    pkp_thn = amount
                    total += pkp_thn * tax_rate
                    input_data = {
                        'sequence': tax.sequence,
                        'name': tax.name,
                        'tax_income_from': tax.taxable_income_from,
                        'tax_income_to': tax.taxable_income_to,
                        'tax_rate': tax.tax_rate,
                        'tax_penalty_rate': tax.tax_penalty_rate,
                        'pkp': round(pkp_thn),
                        'pph21_amount': round(total),
                    }
                    pph21_bracket += [input_data]
                    break
                else:
                    amount_diff = (tax.taxable_income_to - tax.taxable_income_from + 1)
                    pkp_thn = amount_diff
                    total += (tax.taxable_income_to - tax.taxable_income_from + 1) * tax_rate
                    amount = amount - (tax.taxable_income_to - tax.taxable_income_from + 1)
                input_data = {
                    'sequence': tax.sequence,
                    'name': tax.name,
                    'tax_income_from': tax.taxable_income_from,
                    'tax_income_to': tax.taxable_income_to,
                    'tax_rate': tax.tax_rate,
                    'tax_penalty_rate': tax.tax_penalty_rate,
                    'pkp': round(pkp_thn),
                    'pph21_amount': round(total),
                }
                pph21_bracket += [input_data]
            else:
                if net <= 0:
                    pkp_thn = amount
                    total += pkp_thn * tax_penalty_rate
                    input_data = {
                        'sequence': tax.sequence,
                        'name': tax.name,
                        'tax_income_from': tax.taxable_income_from,
                        'tax_income_to': tax.taxable_income_to,
                        'tax_rate': tax.tax_rate,
                        'tax_penalty_rate': tax.tax_penalty_rate,
                        'pkp': round(pkp_thn),
                        'pph21_amount': round(total),
                    }
                    pph21_bracket += [input_data]
                    break
                else:
                    amount_diff = (tax.taxable_income_to - tax.taxable_income_from + 1)
                    pkp_thn = amount_diff
                    total += (tax.taxable_income_to - tax.taxable_income_from + 1) * tax_penalty_rate
                    amount = amount - (tax.taxable_income_to - tax.taxable_income_from + 1)
                input_data = {
                    'sequence': tax.sequence,
                    'name': tax.name,
                    'tax_income_from': tax.taxable_income_from,
                    'tax_income_to': tax.taxable_income_to,
                    'tax_rate': tax.tax_rate,
                    'tax_penalty_rate': tax.tax_penalty_rate,
                    'pkp': round(pkp_thn),
                    'pph21_amount': round(total),
                }
                pph21_bracket += [input_data]
        return pph21_bracket


    def compute_pph_21_grossup(self):
        # self.ensure_one()
        result = {
            "tunj_pjk_reguler": 0.0,
            "tunj_pjk_irreguler": 0.0,
        }
        npwp = self.npwp
        tax_setting = self.env['hr.tax.setting'].sudo().search([], limit=1)
        job_cost_rate = tax_setting.job_cost_rate
        max_job_cost_rate_monthly = tax_setting.max_job_cost_rate_monthly

        ## calculation for reguler
        total_income_reguler = 0
        for rec in self.income_reguler_ids.filtered(lambda r: r.tax_calculation_method == "gross_up"):
            total_income_reguler += rec.amount
        if self.employee_id.is_expatriate and self.employee_id.expatriate_tax == "pph21":
            akum_thn = (total_income_reguler * 12)
        else:
            akum_thn = ((total_income_reguler + self.akum_income_last_month) * self.tax_end_month) / self.tax_period_length
        if (((job_cost_rate/100) * akum_thn) > (max_job_cost_rate_monthly * self.tax_end_month)):
            biaya_jab_reg = (max_job_cost_rate_monthly * self.tax_end_month)
        else:
            biaya_jab_reg = ((job_cost_rate/100) * akum_thn)
        akum_ded_thn = (self.akum_ded * self.tax_end_month) / self.tax_period_length
        total_peng_reguler = biaya_jab_reg + akum_ded_thn
        peng_thn_reguler = akum_thn - total_peng_reguler

        ## calculation for irreguler
        total_income_irreguler = 0
        for rec in self.income_irreguler_ids.filtered(lambda r: r.tax_calculation_method == "gross_up"):
            total_income_irreguler += rec.amount
        akum_irreguler = total_income_irreguler + self.akum_irreguler_last_month
        if akum_irreguler == 0:
            biaya_jab_irreg = 0
        elif (((job_cost_rate/100) * (akum_thn + akum_irreguler)) > (max_job_cost_rate_monthly * self.tax_end_month)):
            biaya_jab_irreg = (max_job_cost_rate_monthly * self.tax_end_month) - biaya_jab_reg
        else:
            biaya_jab_irreg = ((job_cost_rate/100) * (akum_thn + akum_irreguler)) - biaya_jab_reg
        total_peng_irreguler = biaya_jab_reg + biaya_jab_irreg + akum_ded_thn
        peng_thn_irreguler = (akum_thn + akum_irreguler) - total_peng_irreguler

        peng_ptkp = self.ptkp_id.ptkp_amount

        ## calculation PKP Reguler
        peng_kena_pjk_reguler = peng_thn_reguler - peng_ptkp
        if peng_kena_pjk_reguler < 0:
            peng_kena_pjk_reguler = 0

        ## calculation PKP Irreguler
        peng_kena_pjk_irreguler = peng_thn_irreguler - peng_ptkp
        if peng_kena_pjk_irreguler < 0:
            peng_kena_pjk_irreguler = 0

        selisih_reg = 0.0
        iteration_reg = 0
        selisih_irreg = 0.0
        iteration_irreg = 0

        pjk_terhutang_reguler_last_month = (self.pjk_terhutang_reguler_last_month * self.tax_end_month) / self.tax_period_length
        pjk_terhutang_irreguler_last_month = self.pjk_terhutang_irreguler_last_month

        ### perhitungan disetahunkan reguler###
        if (selisih_reg == 0.0):
            tunjanganPphReguler = self.compute_tax_bracket(peng_kena_pjk_reguler,npwp)
            bruto = akum_thn + tunjanganPphReguler
            if (((job_cost_rate/100) * bruto) > (max_job_cost_rate_monthly * self.tax_end_month)):
                biaya_jab_reg = (max_job_cost_rate_monthly * self.tax_end_month)
            else:
                biaya_jab_reg = ((job_cost_rate/100) * bruto)
            jabatan_reg = biaya_jab_reg
            neto = bruto - jabatan_reg - akum_ded_thn
            pkp = self.round_down(neto - peng_ptkp, -3)
            rulePph = self.compute_tax_bracket(pkp,npwp) - pjk_terhutang_reguler_last_month
            selisih_reg = rulePph - tunjanganPphReguler

        while (selisih_reg != 0.0):
            if iteration_reg == 100:
                break
            if tunjanganPphReguler < 0:
                tunjanganPphReguler = 0
            tunjanganPphReguler = tunjanganPphReguler + selisih_reg
            bruto = akum_thn + tunjanganPphReguler
            if (((job_cost_rate/100) * bruto) > (max_job_cost_rate_monthly * self.tax_end_month)):
                biaya_jab_reg = (max_job_cost_rate_monthly * self.tax_end_month)
            else:
                biaya_jab_reg = ((job_cost_rate/100) * bruto)
            if biaya_jab_reg < 0:
                jabatan_reg = 0
            else:
                jabatan_reg = biaya_jab_reg
            neto = bruto - jabatan_reg - akum_ded_thn
            pkp = self.round_down(neto - peng_ptkp, -3)
            rulePph = self.compute_tax_bracket(pkp,npwp) - pjk_terhutang_reguler_last_month
            if rulePph < 0:
                rulePph = 0
            selisih_reg = rulePph - tunjanganPphReguler
            iteration_reg = iteration_reg + 1

        ### perhitungan disetahunkan irreguler###
        if (selisih_irreg == 0.0):
            tunjanganPphIrreguler = self.compute_tax_bracket(peng_kena_pjk_irreguler, npwp)
            bruto_irreg = akum_irreguler + tunjanganPphIrreguler

            if akum_irreguler == 0:
                biaya_jab_irreg = 0
            elif (((job_cost_rate/100) * (bruto + bruto_irreg)) > (max_job_cost_rate_monthly * self.tax_end_month)):
                biaya_jab_irreg = (max_job_cost_rate_monthly * self.tax_end_month) - jabatan_reg
            else:
                biaya_jab_irreg = ((job_cost_rate/100) * (bruto + bruto_irreg)) - jabatan_reg

            jabatan_irreg = biaya_jab_irreg
            neto_irreg = (bruto + bruto_irreg) - (jabatan_reg + jabatan_irreg + akum_ded_thn)
            pkp_irreg = self.round_down(neto_irreg - peng_ptkp, -3)
            rulePphIrreg = self.compute_tax_bracket(pkp_irreg, npwp) - rulePph - pjk_terhutang_reguler_last_month - pjk_terhutang_irreguler_last_month
            selisih_irreg = rulePphIrreg - round(tunjanganPphIrreguler)

        while (selisih_irreg != 0.0):
            if iteration_irreg == 100:
                break
            if tunjanganPphIrreguler < 0:
                tunjanganPphIrreguler = 0
            tunjanganPphIrreguler = tunjanganPphIrreguler + selisih_irreg
            bruto_irreg = akum_irreguler + tunjanganPphIrreguler

            if akum_irreguler == 0:
                biaya_jab_irreg = 0
            elif (((job_cost_rate/100) * (bruto + bruto_irreg)) > (max_job_cost_rate_monthly * self.tax_end_month)):
                biaya_jab_irreg = (max_job_cost_rate_monthly * self.tax_end_month) - jabatan_reg
            else:
                biaya_jab_irreg = ((job_cost_rate/100) * (bruto + bruto_irreg)) - jabatan_reg

            jabatan_irreg = biaya_jab_irreg
            neto_irreg = (bruto + bruto_irreg) - (jabatan_reg + jabatan_irreg + akum_ded_thn)
            pkp_irreg = self.round_down(neto_irreg - peng_ptkp, -3)
            rulePphIrreg = self.compute_tax_bracket(pkp_irreg, npwp)
            PphIrreg = rulePphIrreg - rulePph - pjk_terhutang_reguler_last_month - pjk_terhutang_irreguler_last_month
            if PphIrreg < 0:
                PphIrreg = 0
            selisih_irreg = PphIrreg - round(tunjanganPphIrreguler)
            iteration_irreg = iteration_irreg + 1

        if self.employee_id.is_expatriate and self.employee_id.expatriate_tax == "pph21":
            result["tunj_pjk_reguler"] = (tunjanganPphReguler / 12)
        else:
            result["tunj_pjk_reguler"] = (tunjanganPphReguler / self.tax_end_month) * self.tax_period_length
        result["tunj_pjk_irreguler"] = round(tunjanganPphIrreguler)

        return result

    def compute_pph_21_gross_final(self):
        for res in self:
            if res.termination:
                tax_setting = self.env['hr.tax.setting'].sudo().search([], limit=1)
                job_cost_rate = tax_setting.job_cost_rate
                max_job_cost_rate_monthly = tax_setting.max_job_cost_rate_monthly
                previous_payslip = self.search([('id', '!=', res.id), ('employee_id', '=', res.employee_id.id), ('year', '=', res.year)])
                npwp = res.npwp
                peng_ptkp = res.ptkp_id.ptkp_amount
                akum_income_last_month = 0
                akum_irreguler_last_month = 0
                pjk_terhutang_reguler_last_month = 0
                pjk_terhutang_irreguler_last_month = 0
                akum_ded_last_month = 0
                akum_pajak_normal = 0
                akum_pajak = 0
                for slip in previous_payslip:
                    akum_pajak_normal += slip.pjk_bln_reguler_gross + slip.pjk_bln_irreguler_gross
                    tax_period_length = slip.tax_period_length
                    tax_end_month = res.tax_end_month
                    total_income_reguler = 0
                    for rec in slip.income_reguler_ids.filtered(lambda r: r.tax_calculation_method == "gross" or r.tax_calculation_method == "nett"):
                        total_income_reguler += rec.amount
                    akum_income = total_income_reguler + akum_income_last_month
                    akum_income_last_month += total_income_reguler
                    total_income_irreguler = 0
                    for rec in slip.income_irreguler_ids.filtered(lambda r: r.tax_calculation_method == "gross" or r.tax_calculation_method == "nett"):
                        total_income_irreguler += rec.amount
                    akum_irreguler = total_income_irreguler + akum_irreguler_last_month
                    akum_irreguler_last_month += total_income_irreguler
                    total_deduction = 0
                    for rec in slip.deduction_ids.filtered(lambda r: r.tax_calculation_method == "gross" or r.tax_calculation_method == "nett"):
                        total_deduction += rec.amount
                    akum_ded = total_deduction + akum_ded_last_month
                    akum_ded_last_month = akum_ded

                    if tax_period_length and tax_end_month:
                        akum_ded_thn = (akum_ded * tax_end_month) / tax_period_length
                    else:
                        akum_ded_thn = 0

                    if (((job_cost_rate/100) * akum_income) > max_job_cost_rate_monthly):
                        biaya_jab_month_reg = max_job_cost_rate_monthly
                    else:
                        biaya_jab_month_reg = round(((job_cost_rate/100) * akum_income))

                    if tax_period_length and tax_end_month:
                        akum_thn = (akum_income * tax_end_month) / tax_period_length
                    else:
                        akum_thn = 0

                    if (((job_cost_rate/100) * akum_thn) > (max_job_cost_rate_monthly * tax_end_month)):
                        biaya_jab = round((max_job_cost_rate_monthly * tax_end_month))
                    else:
                        biaya_jab = round(((job_cost_rate/100) * akum_thn))

                    if akum_irreguler == 0:
                        biaya_jab_irreguler = 0
                    elif (((job_cost_rate/100) * (akum_thn + akum_irreguler)) > (max_job_cost_rate_monthly * tax_end_month)):
                        biaya_jab_irreguler = round((max_job_cost_rate_monthly * tax_end_month) - biaya_jab)
                    else:
                        biaya_jab_irreguler = round(((job_cost_rate/100) * (akum_thn + akum_irreguler)) - biaya_jab)

                    total_peng_reguler = round((biaya_jab + akum_ded_thn))

                    if akum_irreguler == 0:
                        total_peng_irreguler = 0.0
                    else:
                        total_peng_irreguler = round((biaya_jab + biaya_jab_irreguler + akum_ded_thn))

                    if (akum_thn - total_peng_reguler) <= 0:
                        peng_thn_reguler = 0
                    else:
                        peng_thn_reguler = akum_thn - total_peng_reguler

                    if total_income_irreguler == 0:
                        peng_thn_irreguler = 0.0
                    else:
                        peng_thn_irreguler = (akum_thn + akum_irreguler) - total_peng_irreguler

                    if peng_thn_reguler == 0:
                        peng_kena_pjk_reguler = 0
                    elif (peng_thn_reguler - peng_ptkp) < 0:
                        peng_kena_pjk_reguler = 0
                    else:
                        peng_kena_pjk_reguler = self.round_down((peng_thn_reguler - peng_ptkp), -3)

                    if peng_thn_irreguler == 0:
                        peng_kena_pjk_irreguler = 0
                    elif (peng_thn_irreguler - peng_ptkp) < 0:
                        peng_kena_pjk_irreguler = 0
                    else:
                        peng_kena_pjk_irreguler = self.round_down((peng_thn_irreguler - peng_ptkp), -3)

                    pjk_thn_reguler = round(self.compute_tax_bracket(peng_kena_pjk_reguler, npwp))

                    if total_income_irreguler == 0:
                        pjk_thn_irreguler = 0
                    else:
                        pjk_thn_irreguler = round(self.compute_tax_bracket(peng_kena_pjk_irreguler, npwp))

                    pjk_terhutang_reguler = (pjk_thn_reguler / tax_end_month) * tax_period_length

                    if pjk_thn_irreguler == 0:
                        pjk_terhutang_irreguler = 0.0
                    else:
                        pjk_terhutang_irreguler = pjk_thn_irreguler - pjk_thn_reguler

                    if (pjk_terhutang_reguler - pjk_terhutang_reguler_last_month) < 0:
                        pjk_bln_reguler = 0
                    else:
                        pjk_bln_reguler = pjk_terhutang_reguler - pjk_terhutang_reguler_last_month

                    if pjk_thn_irreguler == 0:
                        pjk_bln_irreguler = 0.0
                    elif (pjk_terhutang_irreguler - pjk_terhutang_irreguler_last_month) < 0:
                        pjk_bln_irreguler = 0.0
                    else:
                        pjk_bln_irreguler = pjk_terhutang_irreguler - pjk_terhutang_irreguler_last_month

                    res.pjk_terhutang_reguler_last_month_gross = pjk_terhutang_reguler
                    res.pjk_terhutang_irreguler_last_month_gross = pjk_terhutang_irreguler
                    pjk_terhutang_reguler_last_month = pjk_terhutang_reguler
                    pjk_terhutang_irreguler_last_month = pjk_terhutang_irreguler
                    akum_pajak += pjk_bln_reguler + pjk_bln_irreguler
                if akum_pajak_normal - (akum_pajak + res.pjk_bln_reguler_gross + res.pjk_bln_irreguler_gross) < 0:
                    res.kelebihan_pajak_gross = 0
                else:
                    res.kelebihan_pajak_gross = akum_pajak_normal - (akum_pajak + res.pjk_bln_reguler_gross + res.pjk_bln_irreguler_gross)

    def compute_pph_21_grossup_final(self):
        for res in self:
            if res.termination:
                tax_setting = self.env['hr.tax.setting'].sudo().search([], limit=1)
                job_cost_rate = tax_setting.job_cost_rate
                max_job_cost_rate_monthly = tax_setting.max_job_cost_rate_monthly
                previous_payslip = self.search(
                    [('id', '!=', res.id), ('employee_id', '=', res.employee_id.id), ('year', '=', res.year)])
                npwp = res.npwp
                peng_ptkp = res.ptkp_id.ptkp_amount
                akum_income_last_month = 0
                akum_irreguler_last_month = 0
                pjk_terhutang_reguler_last_month = 0
                pjk_terhutang_irreguler_last_month = 0
                akum_ded_last_month = 0
                akum_pajak_normal = 0
                akum_pajak = 0
                for slip in previous_payslip:
                    akum_pajak_normal += slip.pjk_bln_reguler + slip.pjk_bln_irreguler
                    tax_period_length = slip.tax_period_length
                    tax_end_month = res.tax_end_month

                    ## calculation for reguler
                    _total_income_reguler = 0
                    for rec in slip.income_reguler_ids.filtered(lambda r: r.tax_calculation_method == "gross_up"):
                        _total_income_reguler += rec.amount
                    _akum_thn = ((_total_income_reguler + akum_income_last_month) * tax_end_month) / tax_period_length
                    if (((job_cost_rate/100) * _akum_thn) > (max_job_cost_rate_monthly * tax_end_month)):
                        _biaya_jab_reg = (max_job_cost_rate_monthly * tax_end_month)
                    else:
                        _biaya_jab_reg = ((job_cost_rate/100) * _akum_thn)
                    _akum_ded_thn = (slip.akum_ded * tax_end_month) / tax_period_length
                    _total_peng_reguler = _biaya_jab_reg + _akum_ded_thn
                    _peng_thn_reguler = _akum_thn - _total_peng_reguler

                    ## calculation for irreguler
                    _total_income_irreguler = 0
                    for rec in slip.income_irreguler_ids.filtered(lambda r: r.tax_calculation_method == "gross_up"):
                        _total_income_irreguler += rec.amount
                    _akum_irreguler = _total_income_irreguler + akum_irreguler_last_month
                    if _akum_irreguler == 0:
                        _biaya_jab_irreg = 0
                    elif (((job_cost_rate/100) * (_akum_thn + _akum_irreguler)) > (max_job_cost_rate_monthly * tax_end_month)):
                        _biaya_jab_irreg = (max_job_cost_rate_monthly * tax_end_month) - _biaya_jab_reg
                    else:
                        _biaya_jab_irreg = ((job_cost_rate/100) * (_akum_thn + _akum_irreguler)) - _biaya_jab_reg
                    _total_peng_irreguler = _biaya_jab_reg + _biaya_jab_irreg + _akum_ded_thn
                    _peng_thn_irreguler = (_akum_thn + _akum_irreguler) - _total_peng_irreguler

                    ## calculation PKP Reguler
                    _peng_kena_pjk_reguler = _peng_thn_reguler - peng_ptkp
                    if _peng_kena_pjk_reguler < 0:
                        _peng_kena_pjk_reguler = 0

                    ## calculation PKP Irreguler
                    _peng_kena_pjk_irreguler = _peng_thn_irreguler - peng_ptkp
                    if _peng_kena_pjk_irreguler < 0:
                        _peng_kena_pjk_irreguler = 0

                    selisih_reg = 0.0
                    iteration_reg = 0
                    selisih_irreg = 0.0
                    iteration_irreg = 0

                    _pjk_terhutang_reguler_last_month = (slip.pjk_terhutang_reguler * tax_end_month) / tax_period_length
                    _pjk_terhutang_irreguler_last_month = slip.pjk_terhutang_irreguler

                    ### perhitungan disetahunkan reguler###
                    if (selisih_reg == 0.0):
                        tunjanganPphReguler = self.compute_tax_bracket(_peng_kena_pjk_reguler, npwp)
                        bruto = _akum_thn + tunjanganPphReguler
                        if (((job_cost_rate/100) * bruto) > (max_job_cost_rate_monthly * tax_end_month)):
                            _biaya_jab_reg = (max_job_cost_rate_monthly * tax_end_month)
                        else:
                            _biaya_jab_reg = ((job_cost_rate/100) * bruto)
                        _jabatan_reg = _biaya_jab_reg
                        neto = bruto - _jabatan_reg - _akum_ded_thn
                        pkp = self.round_down(neto - peng_ptkp, -3)
                        rulePph = self.compute_tax_bracket(pkp, npwp) - _pjk_terhutang_reguler_last_month
                        selisih_reg = rulePph - tunjanganPphReguler

                    while (selisih_reg != 0.0):
                        if iteration_reg == 100:
                            break
                        if tunjanganPphReguler < 0:
                            tunjanganPphReguler = 0
                        tunjanganPphReguler = tunjanganPphReguler + selisih_reg
                        bruto = _akum_thn + tunjanganPphReguler
                        if (((job_cost_rate/100) * bruto) > (max_job_cost_rate_monthly * tax_end_month)):
                            _biaya_jab_reg = (max_job_cost_rate_monthly * tax_end_month)
                        else:
                            _biaya_jab_reg = ((job_cost_rate/100) * bruto)
                        if _biaya_jab_reg < 0:
                            _jabatan_reg = 0
                        else:
                            _jabatan_reg = _biaya_jab_reg
                        neto = bruto - _jabatan_reg - _akum_ded_thn
                        pkp = self.round_down(neto - peng_ptkp, -3)
                        rulePph = self.compute_tax_bracket(pkp, npwp) - _pjk_terhutang_reguler_last_month
                        if rulePph < 0:
                            rulePph = 0
                        selisih_reg = rulePph - tunjanganPphReguler
                        iteration_reg = iteration_reg + 1

                    ### perhitungan disetahunkan irreguler###
                    if (selisih_irreg == 0.0):
                        tunjanganPphIrreguler = self.compute_tax_bracket(_peng_kena_pjk_irreguler, npwp)
                        bruto_irreg = _akum_irreguler + tunjanganPphIrreguler

                        if _akum_irreguler == 0:
                            _biaya_jab_irreg = 0
                        elif (((job_cost_rate/100) * (bruto + bruto_irreg)) > (max_job_cost_rate_monthly * tax_end_month)):
                            _biaya_jab_irreg = (max_job_cost_rate_monthly * tax_end_month) - _jabatan_reg
                        else:
                            _biaya_jab_irreg = ((job_cost_rate/100) * (bruto + bruto_irreg)) - _jabatan_reg

                        _jabatan_irreg = _biaya_jab_irreg
                        neto_irreg = (bruto + bruto_irreg) - (_jabatan_reg + _jabatan_irreg + _akum_ded_thn)
                        pkp_irreg = self.round_down(neto_irreg - peng_ptkp, -3)
                        rulePphIrreg = self.compute_tax_bracket(pkp_irreg,
                                                                npwp) - rulePph - _pjk_terhutang_reguler_last_month - pjk_terhutang_irreguler_last_month
                        selisih_irreg = rulePphIrreg - round(tunjanganPphIrreguler)

                    while (selisih_irreg != 0.0):
                        if iteration_irreg == 100:
                            break
                        if tunjanganPphIrreguler < 0:
                            tunjanganPphIrreguler = 0
                        tunjanganPphIrreguler = tunjanganPphIrreguler + selisih_irreg
                        bruto_irreg = _akum_irreguler + tunjanganPphIrreguler

                        if _akum_irreguler == 0:
                            _biaya_jab_irreg = 0
                        elif (((job_cost_rate/100) * (bruto + bruto_irreg)) > (max_job_cost_rate_monthly * tax_end_month)):
                            _biaya_jab_irreg = (max_job_cost_rate_monthly * tax_end_month) - _jabatan_reg
                        else:
                            _biaya_jab_irreg = ((job_cost_rate/100) * (bruto + bruto_irreg)) - _jabatan_reg

                        _jabatan_irreg = _biaya_jab_irreg
                        neto_irreg = (bruto + bruto_irreg) - (_jabatan_reg + _jabatan_irreg + _akum_ded_thn)
                        pkp_irreg = self.round_down(neto_irreg - peng_ptkp, -3)
                        rulePphIrreg = self.compute_tax_bracket(pkp_irreg, npwp)
                        PphIrreg = rulePphIrreg - rulePph - _pjk_terhutang_reguler_last_month - _pjk_terhutang_irreguler_last_month
                        if PphIrreg < 0:
                            PphIrreg = 0
                        selisih_irreg = PphIrreg - round(tunjanganPphIrreguler)
                        iteration_irreg = iteration_irreg + 1

                    tunj_pjk_reguler = (tunjanganPphReguler / tax_end_month) * tax_period_length
                    tunj_pjk_irreguler = round(tunjanganPphIrreguler)

                    total_income_reguler = 0
                    for rec in slip.income_reguler_ids.filtered(lambda r: r.tax_calculation_method == "gross_up"):
                        total_income_reguler += rec.amount
                    akum_income = total_income_reguler + akum_income_last_month + tunj_pjk_reguler
                    akum_income_last_month += total_income_reguler
                    total_income_irreguler = 0
                    for rec in slip.income_irreguler_ids.filtered(lambda r: r.tax_calculation_method == "gross_up"):
                        total_income_irreguler += rec.amount
                    akum_irreguler = total_income_irreguler + akum_irreguler_last_month + tunj_pjk_irreguler
                    akum_irreguler_last_month += total_income_irreguler
                    total_deduction = 0
                    for rec in slip.deduction_ids.filtered(lambda r: r.tax_calculation_method == "gross_up"):
                        total_deduction += rec.amount
                    akum_ded = total_deduction + akum_ded_last_month
                    akum_ded_last_month = akum_ded

                    if tax_period_length and tax_end_month:
                        akum_ded_thn = (akum_ded * tax_end_month) / tax_period_length
                    else:
                        akum_ded_thn = 0

                    if (((job_cost_rate/100) * akum_income) > max_job_cost_rate_monthly):
                        biaya_jab_month_reg = max_job_cost_rate_monthly
                    else:
                        biaya_jab_month_reg = round(((job_cost_rate/100) * akum_income))

                    if tax_period_length and tax_end_month:
                        akum_thn = (akum_income * tax_end_month) / tax_period_length
                    else:
                        akum_thn = 0

                    if (((job_cost_rate/100) * akum_thn) > (max_job_cost_rate_monthly * tax_end_month)):
                        biaya_jab = round((max_job_cost_rate_monthly * tax_end_month))
                    else:
                        biaya_jab = round(((job_cost_rate/100) * akum_thn))

                    if akum_irreguler == 0:
                        biaya_jab_irreguler = 0
                    elif (((job_cost_rate/100) * (akum_thn + akum_irreguler)) > (max_job_cost_rate_monthly * tax_end_month)):
                        biaya_jab_irreguler = round((max_job_cost_rate_monthly * tax_end_month) - biaya_jab)
                    else:
                        biaya_jab_irreguler = round(((job_cost_rate/100) * (akum_thn + akum_irreguler)) - biaya_jab)

                    total_peng_reguler = round((biaya_jab + akum_ded_thn))

                    if akum_irreguler == 0:
                        total_peng_irreguler = 0.0
                    else:
                        total_peng_irreguler = round((biaya_jab + biaya_jab_irreguler + akum_ded_thn))

                    if (akum_thn - total_peng_reguler) <= 0:
                        peng_thn_reguler = 0
                    else:
                        peng_thn_reguler = akum_thn - total_peng_reguler

                    if total_income_irreguler == 0:
                        peng_thn_irreguler = 0.0
                    else:
                        peng_thn_irreguler = (akum_thn + akum_irreguler) - total_peng_irreguler

                    if peng_thn_reguler == 0:
                        peng_kena_pjk_reguler = 0
                    elif (peng_thn_reguler - peng_ptkp) < 0:
                        peng_kena_pjk_reguler = 0
                    else:
                        peng_kena_pjk_reguler = self.round_down((peng_thn_reguler - peng_ptkp), -3)

                    if peng_thn_irreguler == 0:
                        peng_kena_pjk_irreguler = 0
                    elif (peng_thn_irreguler - peng_ptkp) < 0:
                        peng_kena_pjk_irreguler = 0
                    else:
                        peng_kena_pjk_irreguler = self.round_down((peng_thn_irreguler - peng_ptkp), -3)

                    pjk_thn_reguler = round(self.compute_tax_bracket(peng_kena_pjk_reguler, npwp))

                    if total_income_irreguler == 0:
                        pjk_thn_irreguler = 0
                    else:
                        pjk_thn_irreguler = round(self.compute_tax_bracket(peng_kena_pjk_irreguler, npwp))

                    pjk_terhutang_reguler = (pjk_thn_reguler / tax_end_month) * tax_period_length

                    if pjk_thn_irreguler == 0:
                        pjk_terhutang_irreguler = 0.0
                    else:
                        pjk_terhutang_irreguler = pjk_thn_irreguler - pjk_thn_reguler

                    if (pjk_terhutang_reguler - pjk_terhutang_reguler_last_month) < 0:
                        pjk_bln_reguler = 0
                    else:
                        pjk_bln_reguler = pjk_terhutang_reguler - pjk_terhutang_reguler_last_month

                    if pjk_thn_irreguler == 0:
                        pjk_bln_irreguler = 0.0
                    elif (pjk_terhutang_irreguler - pjk_terhutang_irreguler_last_month) < 0:
                        pjk_bln_irreguler = 0.0
                    else:
                        pjk_bln_irreguler = pjk_terhutang_irreguler - pjk_terhutang_irreguler_last_month

                    res.pjk_terhutang_reguler_last_month = pjk_terhutang_reguler
                    res.pjk_terhutang_irreguler_last_month = pjk_terhutang_irreguler
                    pjk_terhutang_reguler_last_month = pjk_terhutang_reguler
                    pjk_terhutang_irreguler_last_month = pjk_terhutang_irreguler
                    akum_pajak += pjk_bln_reguler + pjk_bln_irreguler
                if akum_pajak_normal - (akum_pajak + res.pjk_bln_reguler + res.pjk_bln_irreguler) < 0:
                    res.kelebihan_pajak = 0
                else:
                    res.kelebihan_pajak = akum_pajak_normal - (akum_pajak + res.pjk_bln_reguler + res.pjk_bln_irreguler)
    
    @api.depends('employee_id', 'year', 'date_of_joining','akum_thn')
    def compute_neto_masa_sebelumnya(self):
        for res in self:
            check_bukti_potong = self.env['hr.bukti.potong'].sudo().search([('employee_id','=',res.employee_id.id),('tahun_pajak','=',res.year)], limit=1)
            if check_bukti_potong and res.date_of_joining:
                if check_bukti_potong.spt_type_code == "1721_A1":
                    if check_bukti_potong.imported_date > res.date_of_joining and check_bukti_potong.imported_date >= res.date_from and check_bukti_potong.imported_date <= res.date_to or check_bukti_potong.imported_date > res.date_of_joining and check_bukti_potong.imported_date <= res.date_from:
                        res.neto_masa_sebelumnya = check_bukti_potong.jumlah_14
                    elif check_bukti_potong.imported_date < res.date_of_joining and res.date_of_joining >= res.date_from and res.date_of_joining <= res.date_to or check_bukti_potong.imported_date < res.date_of_joining and res.date_of_joining <= res.date_from:
                        res.neto_masa_sebelumnya = check_bukti_potong.jumlah_14
                    else:
                        res.neto_masa_sebelumnya = 0.0
                elif check_bukti_potong.spt_type_code == "1721_A2":
                    if check_bukti_potong.imported_date > res.date_of_joining and check_bukti_potong.imported_date >= res.date_from and check_bukti_potong.imported_date <= res.date_to or check_bukti_potong.imported_date > res.date_of_joining and check_bukti_potong.imported_date <= res.date_from:
                        res.neto_masa_sebelumnya = check_bukti_potong.jumlah_17
                    elif check_bukti_potong.imported_date < res.date_of_joining and res.date_of_joining >= res.date_from and res.date_of_joining <= res.date_to or check_bukti_potong.imported_date < res.date_of_joining and res.date_of_joining <= res.date_from:
                        res.neto_masa_sebelumnya = check_bukti_potong.jumlah_17
                    else:
                        res.neto_masa_sebelumnya = 0.0
                else:
                    res.neto_masa_sebelumnya = 0.0
            else:
                res.neto_masa_sebelumnya = 0.0



    def get_bpjs_kesehatan_limit(self):
        bpjs_kesehatan_limit = float(self.env['ir.config_parameter'].sudo().get_param('equip3_hr_payroll_extend_id.bpjs_kesehatan_limit'))
        if bpjs_kesehatan_limit > 0:
            return bpjs_kesehatan_limit
        else:
            return 0

    def get_jaminan_pensiun_limit(self):
        jaminan_pensiun_limit = float(self.env['ir.config_parameter'].sudo().get_param('equip3_hr_payroll_extend_id.jaminan_pensiun_limit'))
        if jaminan_pensiun_limit > 0:
            return jaminan_pensiun_limit
        else:
            return 0

    def get_limit_age_bpjs(self):
        limit_age_bpjs = float(self.env['ir.config_parameter'].sudo().get_param('equip3_hr_payroll_extend_id.limit_age_bpjs'))
        return limit_age_bpjs

    def compute_thr_rule(self, payslip):
        result = {
            "allow_thr": False,
            "thr_additional_rate": 0.0,
            "masa_kerja": 0,
        }
        payslip_rec = self.sudo().browse(payslip)[0]
        current_day = date.today()
        d1 = payslip_rec.employee_id.date_of_joining
        d2 = current_day
        diff = relativedelta(d2, d1)

        date_from = payslip_rec.date_from
        date_to = payslip_rec.date_to

        allow_thr = False
        thr_additional_rate = 0.0
        masa_kerja = 0

        thr_rule = self.env['thr.rule'].sudo().search([('date','>=',date_from),('date','<=',date_to)])
        if thr_rule:
            for thr in thr_rule:
                if thr.employee_ids.filtered(
                    lambda r: r.id == payslip_rec.employee_id.id
                ):
                    diff_cut_off = relativedelta(thr.cut_off_date, d1)
                    masa_kerja = diff_cut_off.months + (12 * diff_cut_off.years)
                    if masa_kerja >= thr.minimun_joined:
                        allow_thr = True
                    else:
                        allow_thr = False
                    if thr.additional_rate and diff_cut_off.years >= thr.yos_after:
                        thr_additional_rate = thr.thr_additional_rate
                    else:
                        thr_additional_rate = 0.0
        else:
            allow_thr = False
            thr_additional_rate = 0.0
            masa_kerja = 0

        result["allow_thr"] = allow_thr
        result["thr_additional_rate"] = thr_additional_rate
        result["masa_kerja"] = masa_kerja

        return result

    # @api.depends('tax_calculation_method')
    # def _amount_tunj_pjk_reguler(self):
    #     for res in self:
    #         total = 0
    #         if res.tax_calculation_method == "Gross-Up":
    #             tunj_pjk_reguler = self.compute_pph_21_grossup()
    #             res.tunj_pjk_reguler = tunj_pjk_reguler["tunj_pjk_reguler"]
    #         else:
    #             res.tunj_pjk_reguler = total

    # @api.depends('tax_calculation_method')
    # def _amount_tunj_pjk_irreguler(self):
    #     for res in self:
    #         total = 0
    #         if res.tax_calculation_method == "Gross-Up":
    #             tunj_pjk_irreguler = self.compute_pph_21_grossup()
    #             res.tunj_pjk_irreguler = tunj_pjk_irreguler["tunj_pjk_irreguler"]
    #         else:
    #             res.tunj_pjk_irreguler = total

    @api.depends('income_reguler_ids.amount','akum_income_last_month','tunj_pjk_reguler')
    def _amount_akum_income(self):
        for res in self:
            total = 0
            for rec in res.income_reguler_ids.filtered(lambda r: r.tax_calculation_method == "gross_up"):
                total += rec.amount
            if res.tunj_pjk_reguler < 0:
                tunj_pjk_reguler = 0
            else:
                tunj_pjk_reguler = res.tunj_pjk_reguler
            if res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph26":
                res.akum_income = total
            elif res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph21":
                res.akum_income = total + tunj_pjk_reguler
            elif res.employee_id.employee_tax_status == 'pegawai_tetap':
                if res.payslip_period_id.tax_calculation_method == "monthly":
                    if res.tax_period_length == 12:
                        akum_income_before = 0
                        self.env.cr.execute(
                                ''' select sum(akum_income) as akum_income_before from hr_payslip WHERE employee_id = %s and date_from < '%s' AND year = '%s' and state in ('done')''' % (
                                    res.employee_id.id, res.date_from, res.year))
                        payslip_before = self.env.cr.dictfetchall()
                        if payslip_before:
                            akum_income_before = payslip_before[0].get('akum_income_before')
                        res.akum_income = total + tunj_pjk_reguler + akum_income_before
                    else:
                        res.akum_income = total + tunj_pjk_reguler
                else:
                    res.akum_income = total + tunj_pjk_reguler + res.akum_income_last_month
            else:
                res.akum_income = total + tunj_pjk_reguler + res.akum_income_last_month
    
    @api.depends('income_reguler_ids.amount','akum_income_last_month_gross')
    def _amount_akum_income_gross(self):
        for res in self:
            total = 0
            for rec in res.income_reguler_ids.filtered(lambda r: r.tax_calculation_method == "gross" or r.tax_calculation_method == "nett"):
                total += rec.amount
            if res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph26":
                res.akum_income_gross = total
            elif res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph21":
                res.akum_income_gross = total
            elif res.employee_id.employee_tax_status == 'pegawai_tetap':
                if res.payslip_period_id.tax_calculation_method == "monthly":
                    if res.tax_period_length == 12:
                        akum_income_gross_before = 0
                        self.env.cr.execute(
                                ''' select sum(akum_income_gross) as akum_income_gross_before from hr_payslip WHERE employee_id = %s and date_from < '%s' AND year = '%s' and state in ('done')''' % (
                                    res.employee_id.id, res.date_from, res.year))
                        payslip_before = self.env.cr.dictfetchall()
                        if payslip_before:
                            akum_income_gross_before = payslip_before[0].get('akum_income_gross_before')
                        res.akum_income_gross = total + akum_income_gross_before
                    else:
                        res.akum_income_gross = total
                else:
                    res.akum_income_gross = total + res.akum_income_last_month_gross
            else:
                res.akum_income_gross = total + res.akum_income_last_month_gross

    @api.depends('akum_income','tax_period_length','tax_end_month')
    def _amount_akum_thn(self):
        for res in self:
            total = 0.0
            if res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph26":
                res.akum_thn = total
            elif res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph21":
                res.akum_thn = (res.akum_income * 12)
            elif res.employee_id.employee_tax_status == 'pegawai_tetap':
                if res.payslip_period_id.tax_calculation_method == "monthly":
                    if res.tax_period_length == 12:
                        res.akum_thn = res.akum_income
                    else:
                        res.akum_thn = (res.akum_income * 12)
                else:
                    if res.tax_period_length and res.tax_end_month:
                        total = (res.akum_income * res.tax_end_month) / res.tax_period_length
                        res.akum_thn = total
                    else:
                        res.akum_thn = total
            elif res.employee_id.employee_tax_status == 'pegawai_tidak_tetap':
                res.akum_thn = (res.akum_income * 12)
            else:
                res.akum_thn = total
    
    @api.depends('akum_income_gross','tax_period_length','tax_end_month')
    def _amount_akum_thn_gross(self):
        for res in self:
            total = 0.0
            if res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph26":
                res.akum_thn_gross = total
            elif res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph21":
                res.akum_thn_gross = (res.akum_income_gross * 12)
            elif res.employee_id.employee_tax_status == 'pegawai_tetap':
                if res.payslip_period_id.tax_calculation_method == "monthly":
                    if res.tax_period_length == 12:
                        res.akum_thn_gross = res.akum_income_gross
                    else:
                        res.akum_thn_gross = (res.akum_income_gross * 12)
                else:
                    if res.tax_period_length and res.tax_end_month:
                        total = (res.akum_income_gross * res.tax_end_month) / res.tax_period_length
                        res.akum_thn_gross = total
                    else:
                        res.akum_thn_gross = total
            elif res.employee_id.employee_tax_status == 'pegawai_tidak_tetap':
                res.akum_thn_gross = (res.akum_income_gross * 12)
            else:
                res.akum_thn_gross = total

    @api.depends('income_irreguler_ids.amount')
    def _amount_akum_irreguler(self):
        for res in self:
            total = 0
            for rec in res.income_irreguler_ids:
                total += rec.amount
            if res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph26":
                res.akum_irreguler = total
            elif res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph21":
                res.akum_irreguler = total + res.tunj_pjk_irreguler
            else:
                res.akum_irreguler = total + res.tunj_pjk_irreguler + res.akum_irreguler_last_month
    
    @api.depends('income_irreguler_ids.amount')
    def _amount_akum_irreguler_gross(self):
        for res in self:
            total = 0
            for rec in res.income_irreguler_ids.filtered(lambda r: r.tax_calculation_method == "gross" or r.tax_calculation_method == "nett"):
                total += rec.amount
            if res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph26":
                res.akum_irreguler_gross = total
            elif res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph21":
                res.akum_irreguler_gross = total
            else:
                res.akum_irreguler_gross = total + res.akum_irreguler_last_month_gross

    @api.depends('akum_income', 'akum_irreguler')
    def _amount_bruto(self):
        for res in self:
            res.bruto = res.akum_income + res.akum_irreguler
    
    @api.depends('akum_income_gross', 'akum_irreguler_gross')
    def _amount_bruto_gross(self):
        for res in self:
            res.bruto_gross = res.akum_income_gross + res.akum_irreguler_gross

    @api.depends('akum_thn','tax_end_month')
    def _amount_biaya_jab(self):
        for res in self:
            tax_setting = self.env['hr.tax.setting'].sudo().search([], limit=1)
            job_cost_rate = tax_setting.job_cost_rate
            max_job_cost_rate_monthly = tax_setting.max_job_cost_rate_monthly
            if res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph26":
                res.biaya_jab = 0.0
            elif res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph21":
                if (((job_cost_rate/100) * res.akum_thn) > (max_job_cost_rate_monthly * res.tax_end_month)):
                    total = (max_job_cost_rate_monthly * res.tax_end_month)
                else:
                    total = ((job_cost_rate/100) * res.akum_thn)
                res.biaya_jab = round(total)
            elif res.employee_id.employee_tax_status == 'pegawai_tetap':
                if (((job_cost_rate/100) * res.akum_thn) > (max_job_cost_rate_monthly * res.tax_end_month)):
                    total = (max_job_cost_rate_monthly * res.tax_end_month)
                else:
                    total = ((job_cost_rate/100) * res.akum_thn)
                res.biaya_jab = round(total)
            else:
                res.biaya_jab = 0.0
    
    @api.depends('akum_thn_gross','tax_end_month')
    def _amount_biaya_jab_gross(self):
        for res in self:
            tax_setting = self.env['hr.tax.setting'].sudo().search([], limit=1)
            job_cost_rate = tax_setting.job_cost_rate
            max_job_cost_rate_monthly = tax_setting.max_job_cost_rate_monthly
            if res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph26":
                res.biaya_jab_gross = 0.0
            elif res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph21":
                if (((job_cost_rate/100) * res.akum_thn_gross) > (max_job_cost_rate_monthly * res.tax_end_month)):
                    total = (max_job_cost_rate_monthly * res.tax_end_month)
                else:
                    total = ((job_cost_rate/100) * res.akum_thn_gross)
                res.biaya_jab_gross = round(total)
            elif res.employee_id.employee_tax_status == 'pegawai_tetap':
                if (((job_cost_rate/100) * res.akum_thn_gross) > (max_job_cost_rate_monthly * res.tax_end_month)):
                    total = (max_job_cost_rate_monthly * res.tax_end_month)
                else:
                    total = ((job_cost_rate/100) * res.akum_thn_gross)
                res.biaya_jab_gross = round(total)
            else:
                res.biaya_jab_gross = 0.0

    @api.depends('akum_income')
    def _amount_biaya_jab_month_reg(self):
        for res in self:
            tax_setting = self.env['hr.tax.setting'].sudo().search([], limit=1)
            job_cost_rate = tax_setting.job_cost_rate
            max_job_cost_rate_monthly = tax_setting.max_job_cost_rate_monthly
            if res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph26":
                res.biaya_jab_month_reg = 0.0
            elif res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph21":
                if (((job_cost_rate/100) * res.akum_income) > max_job_cost_rate_monthly):
                    total = max_job_cost_rate_monthly
                else:
                    total = ((job_cost_rate/100) * res.akum_income)
                res.biaya_jab_month_reg = round(total)
            elif res.employee_id.employee_tax_status == 'pegawai_tetap':
                if (((job_cost_rate/100) * res.akum_income) > max_job_cost_rate_monthly):
                    total = max_job_cost_rate_monthly
                else:
                    total = ((job_cost_rate/100) * res.akum_income)
                res.biaya_jab_month_reg = round(total)
            else:
                res.biaya_jab_month_reg = 0.0
    
    @api.depends('akum_income_gross')
    def _amount_biaya_jab_month_reg_gross(self):
        for res in self:
            tax_setting = self.env['hr.tax.setting'].sudo().search([], limit=1)
            job_cost_rate = tax_setting.job_cost_rate
            max_job_cost_rate_monthly = tax_setting.max_job_cost_rate_monthly
            if res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph26":
                res.biaya_jab_month_reg_gross = 0.0
            elif res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph21":
                if (((job_cost_rate/100) * res.akum_income_gross) > max_job_cost_rate_monthly):
                    total = max_job_cost_rate_monthly
                else:
                    total = ((job_cost_rate/100) * res.akum_income_gross)
                res.biaya_jab_month_reg_gross = round(total)
            elif res.employee_id.employee_tax_status == 'pegawai_tetap':
                if (((job_cost_rate/100) * res.akum_income_gross) > max_job_cost_rate_monthly):
                    total = max_job_cost_rate_monthly
                else:
                    total = ((job_cost_rate/100) * res.akum_income_gross)
                res.biaya_jab_month_reg_gross = round(total)
            else:
                res.biaya_jab_month_reg_gross = 0.0

    @api.depends('akum_thn','akum_irreguler','biaya_jab','tax_end_month')
    def _amount_biaya_jab_irreguler(self):
        for res in self:
            tax_setting = self.env['hr.tax.setting'].sudo().search([], limit=1)
            job_cost_rate = tax_setting.job_cost_rate
            max_job_cost_rate_monthly = tax_setting.max_job_cost_rate_monthly
            if res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph26":
                res.biaya_jab_irreguler = 0.0
            elif res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph21":
                if res.akum_irreguler == 0:
                    total = 0
                elif (((job_cost_rate/100) * (res.akum_thn + res.akum_irreguler)) > (max_job_cost_rate_monthly * res.tax_end_month)):
                    total = (max_job_cost_rate_monthly * res.tax_end_month) - res.biaya_jab
                else:
                    total = ((job_cost_rate/100) * (res.akum_thn + res.akum_irreguler)) - res.biaya_jab
                res.biaya_jab_irreguler = round(total)
            elif res.employee_id.employee_tax_status == 'pegawai_tetap':
                if res.akum_irreguler == 0:
                    total = 0
                elif (((job_cost_rate/100) * (res.akum_thn + res.akum_irreguler)) > (max_job_cost_rate_monthly * res.tax_end_month)):
                    total = (max_job_cost_rate_monthly * res.tax_end_month) - res.biaya_jab
                else:
                    total = ((job_cost_rate/100) * (res.akum_thn + res.akum_irreguler)) - res.biaya_jab
                res.biaya_jab_irreguler = round(total)
            else:
                res.biaya_jab_irreguler = 0.0
    
    @api.depends('akum_thn_gross','akum_irreguler_gross','biaya_jab_gross','tax_end_month')
    def _amount_biaya_jab_irreguler_gross(self):
        for res in self:
            tax_setting = self.env['hr.tax.setting'].sudo().search([], limit=1)
            job_cost_rate = tax_setting.job_cost_rate
            max_job_cost_rate_monthly = tax_setting.max_job_cost_rate_monthly
            if res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph26":
                res.biaya_jab_irreguler_gross = 0.0
            elif res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph21":
                if res.akum_irreguler_gross == 0:
                    total = 0
                elif (((job_cost_rate/100) * (res.akum_thn_gross + res.akum_irreguler_gross)) > (max_job_cost_rate_monthly * res.tax_end_month)):
                    total = (max_job_cost_rate_monthly * res.tax_end_month) - res.biaya_jab_gross
                else:
                    total = ((job_cost_rate/100) * (res.akum_thn_gross + res.akum_irreguler_gross)) - res.biaya_jab_gross
                res.biaya_jab_irreguler_gross = round(total)
            elif res.employee_id.employee_tax_status == 'pegawai_tetap':
                if res.akum_irreguler_gross == 0:
                    total = 0
                elif (((job_cost_rate/100) * (res.akum_thn_gross + res.akum_irreguler_gross)) > (max_job_cost_rate_monthly * res.tax_end_month)):
                    total = (max_job_cost_rate_monthly * res.tax_end_month) - res.biaya_jab_gross
                else:
                    total = ((job_cost_rate/100) * (res.akum_thn_gross + res.akum_irreguler_gross)) - res.biaya_jab_gross
                res.biaya_jab_irreguler_gross = round(total)
            else:
                res.biaya_jab_irreguler_gross = 0.0

    @api.depends('deduction_ids.amount')
    def _amount_akum_ded(self):
        for res in self:
            total = 0
            for rec in res.deduction_ids.filtered(lambda r: r.tax_calculation_method == "gross_up"):
                total += rec.amount
            if res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph26":
                res.akum_ded = 0.0
            elif res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph21":
                res.akum_ded = total
            elif res.employee_id.employee_tax_status == 'pegawai_tetap':
                if res.payslip_period_id.tax_calculation_method == "monthly":
                    if res.tax_period_length == 12:
                        akum_ded_before = 0
                        self.env.cr.execute(
                                ''' select sum(akum_ded) as akum_ded_before from hr_payslip WHERE employee_id = %s and date_from < '%s' AND year = '%s' and state in ('done')''' % (
                                    res.employee_id.id, res.date_from, res.year))
                        payslip_before = self.env.cr.dictfetchall()
                        if payslip_before:
                            akum_ded_before = payslip_before[0].get('akum_ded_before')
                        res.akum_ded = total + akum_ded_before
                    else:
                        res.akum_ded = total
                else:
                    res.akum_ded = total + res.akum_ded_last_month
            else:
                res.akum_ded = total + res.akum_ded_last_month
    
    @api.depends('deduction_ids.amount')
    def _amount_akum_ded_gross(self):
        for res in self:
            total = 0
            for rec in res.deduction_ids.filtered(lambda r: r.tax_calculation_method == "gross" or r.tax_calculation_method == "nett"):
                total += rec.amount
            if res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph26":
                res.akum_ded_gross = 0.0
            elif res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph21":
                res.akum_ded_gross = total
            elif res.employee_id.employee_tax_status == 'pegawai_tetap':
                if res.payslip_period_id.tax_calculation_method == "monthly":
                    if res.tax_period_length == 12:
                        akum_ded_gross_before = 0
                        self.env.cr.execute(
                                ''' select sum(akum_ded_gross) as akum_ded_gross_before from hr_payslip WHERE employee_id = %s and date_from < '%s' AND year = '%s' and state in ('done')''' % (
                                    res.employee_id.id, res.date_from, res.year))
                        payslip_before = self.env.cr.dictfetchall()
                        if payslip_before:
                            akum_ded_gross_before = payslip_before[0].get('akum_ded_gross_before')
                        res.akum_ded_gross = total + akum_ded_gross_before
                    else:
                        res.akum_ded_gross = total
                else:
                    res.akum_ded_gross = total + res.akum_ded_last_month_gross
            else:
                res.akum_ded_gross = total + res.akum_ded_last_month_gross

    @api.depends('akum_ded')
    def _amount_akum_ded_thn(self):
        for res in self:
            total = 0.0
            if res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph26":
                res.akum_ded_thn = 0.0
            elif res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph21":
                if res.tax_period_length and res.tax_end_month:
                    res.akum_ded_thn = (res.akum_ded * 12)
            elif res.employee_id.employee_tax_status == 'pegawai_tetap':
                if res.payslip_period_id.tax_calculation_method == "monthly":
                    if res.tax_period_length == 12:
                        res.akum_ded_thn = res.akum_ded
                    else:
                        res.akum_ded_thn = (res.akum_ded * 12)
                else:
                    if res.tax_period_length and res.tax_end_month:
                        total = (res.akum_ded * res.tax_end_month) / res.tax_period_length
                        res.akum_ded_thn = total
                    else:
                        res.akum_ded_thn = total
            elif res.employee_id.employee_tax_status == 'pegawai_tidak_tetap':
                res.akum_ded_thn = (res.akum_ded * 12)
            else:
                res.akum_ded_thn = total
    
    @api.depends('akum_ded_gross')
    def _amount_akum_ded_thn_gross(self):
        for res in self:
            total = 0.0
            if res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph26":
                res.akum_ded_thn_gross = 0.0
            elif res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph21":
                if res.tax_period_length and res.tax_end_month:
                    res.akum_ded_thn_gross = (res.akum_ded_gross * 12)
            elif res.employee_id.employee_tax_status == 'pegawai_tetap':
                if res.payslip_period_id.tax_calculation_method == "monthly":
                    if res.tax_period_length == 12:
                        res.akum_ded_thn_gross = res.akum_ded_gross
                    else:
                        res.akum_ded_thn_gross = (res.akum_ded_gross * 12)
                else:
                    if res.tax_period_length and res.tax_end_month:
                        total = (res.akum_ded_gross * res.tax_end_month) / res.tax_period_length
                        res.akum_ded_thn_gross = total
                    else:
                        res.akum_ded_thn_gross = total
            elif res.employee_id.employee_tax_status == 'pegawai_tidak_tetap':
                res.akum_ded_thn_gross = (res.akum_ded_gross * 12)
            else:
                res.akum_ded_thn_gross = total

    @api.depends('biaya_jab','akum_ded_thn')
    def _amount_total_peng_reguler(self):
        for res in self:
            total = (res.biaya_jab + res.akum_ded_thn)
            res.total_peng_reguler = round(total)
    
    @api.depends('biaya_jab_gross','akum_ded_thn_gross')
    def _amount_total_peng_reguler_gross(self):
        for res in self:
            total = (res.biaya_jab_gross + res.akum_ded_thn_gross)
            res.total_peng_reguler_gross = round(total)

    @api.depends('biaya_jab','biaya_jab_irreguler','akum_ded_thn')
    def _amount_total_peng_irreguler(self):
        for res in self:
            if res.akum_irreguler == 0:
                res.total_peng_irreguler = 0.0
            else:
                total = (res.biaya_jab + res.biaya_jab_irreguler + res.akum_ded_thn)
                res.total_peng_irreguler = round(total)
    
    @api.depends('biaya_jab_gross','biaya_jab_irreguler_gross','akum_ded_thn_gross')
    def _amount_total_peng_irreguler_gross(self):
        for res in self:
            if res.akum_irreguler_gross == 0:
                res.total_peng_irreguler_gross = 0.0
            else:
                total = (res.biaya_jab_gross + res.biaya_jab_irreguler_gross + res.akum_ded_thn_gross)
                res.total_peng_irreguler_gross = round(total)

    @api.depends('akum_thn','total_peng_reguler')
    def _amount_peng_thn_reguler(self):
        for res in self:
            total = (res.akum_thn - res.total_peng_reguler)
            if total < 0:
                total = 0
            if res.tax_calculation_method == "Gross-Up":
                total += res.neto_masa_sebelumnya
            res.peng_thn_reguler = total
    
    @api.depends('akum_thn_gross','total_peng_reguler_gross')
    def _amount_peng_thn_reguler_gross(self):
        for res in self:
            total = (res.akum_thn_gross - res.total_peng_reguler_gross)
            if total < 0:
                total = 0
            if res.tax_calculation_method != "Gross-Up":
                total += res.neto_masa_sebelumnya
            res.peng_thn_reguler_gross = total

    @api.depends('ptkp_id.ptkp_amount')
    def _amount_peng_ptkp(self):
        for res in self:
            total = res.ptkp_id.ptkp_amount
            if res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph26":
                res.peng_ptkp = 0.0
            else:
                res.peng_ptkp = total

    @api.depends('peng_thn_reguler', 'peng_ptkp')
    def _amount_peng_kena_pjk_reguler(self):
        for res in self:
            if res.peng_thn_reguler == 0:
                total = 0
            elif (res.peng_thn_reguler - res.peng_ptkp) < 0:
                total = 0
            else:
                total = (res.peng_thn_reguler - res.peng_ptkp)
            res.peng_kena_pjk_reguler = self.round_down(total, -3)
    
    @api.depends('peng_thn_reguler_gross', 'peng_ptkp')
    def _amount_peng_kena_pjk_reguler_gross(self):
        for res in self:
            if res.peng_thn_reguler_gross == 0:
                total = 0
            elif (res.peng_thn_reguler_gross - res.peng_ptkp) < 0:
                total = 0
            else:
                total = (res.peng_thn_reguler_gross - res.peng_ptkp)
            res.peng_kena_pjk_reguler_gross = self.round_down(total, -3)

    @api.depends('akum_thn', 'akum_irreguler', 'total_peng_irreguler')
    def _amount_peng_thn_irreguler(self):
        for res in self:
            income_irreguler = 0
            for rec in res.income_irreguler_ids:
                income_irreguler += rec.amount
            if income_irreguler == 0:
                res.peng_thn_irreguler = 0.0
            else:
                total = (res.akum_thn + res.akum_irreguler) - res.total_peng_irreguler
                res.peng_thn_irreguler = total
    
    @api.depends('akum_thn_gross', 'akum_irreguler_gross', 'total_peng_irreguler_gross')
    def _amount_peng_thn_irreguler_gross(self):
        for res in self:
            income_irreguler_gross = 0
            for rec in res.income_irreguler_ids.filtered(lambda r: r.tax_calculation_method == "gross" or r.tax_calculation_method == "nett"):
                income_irreguler_gross += rec.amount
            if income_irreguler_gross == 0:
                res.peng_thn_irreguler_gross = 0.0
            else:
                total = (res.akum_thn_gross + res.akum_irreguler_gross) - res.total_peng_irreguler_gross
                res.peng_thn_irreguler_gross = total

    @api.depends('peng_thn_irreguler', 'peng_ptkp')
    def _amount_peng_kena_pjk_irreguler(self):
        for res in self:
            if res.peng_thn_irreguler == 0:
                total = 0
            elif (res.peng_thn_irreguler - res.peng_ptkp) < 0:
                total = 0
            else:
                total = (res.peng_thn_irreguler - res.peng_ptkp)
            res.peng_kena_pjk_irreguler = self.round_down(total, -3)
    
    @api.depends('peng_thn_irreguler_gross', 'peng_ptkp')
    def _amount_peng_kena_pjk_irreguler_gross(self):
        for res in self:
            if res.peng_thn_irreguler_gross == 0:
                total = 0
            elif (res.peng_thn_irreguler_gross - res.peng_ptkp) < 0:
                total = 0
            else:
                total = (res.peng_thn_irreguler_gross - res.peng_ptkp)
            res.peng_kena_pjk_irreguler_gross = self.round_down(total, -3)

    @api.depends('peng_kena_pjk_reguler')
    def _amount_pjk_thn_reguler(self):
        for res in self:
            income_reguler = 0
            for rec in res.income_reguler_ids.filtered(lambda r: r.tax_calculation_method == "gross_up"):
                income_reguler += rec.amount
            if res.employee_id.employee_tax_status == 'pegawai_tidak_tetap' and not res.employee_id.is_expatriate:
                res.pjk_thn_reguler = round(self.compute_tax_harian_lepas(income_reguler, res.peng_kena_pjk_reguler, res.npwp))
            elif res.employee_id.employee_tax_status == 'pegawai_tidak_tetap' and res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph26":
                res.pjk_thn_reguler = 0.0
            else:
                res.pjk_thn_reguler = round(self.compute_tax_bracket(res.peng_kena_pjk_reguler,res.npwp))
    
    @api.depends('peng_kena_pjk_reguler_gross')
    def _amount_pjk_thn_reguler_gross(self):
        for res in self:
            income_reguler_gross = 0
            for rec in res.income_reguler_ids.filtered(lambda r: r.tax_calculation_method == "gross" or r.tax_calculation_method == "nett"):
                income_reguler_gross += rec.amount
            if res.employee_id.employee_tax_status == 'pegawai_tidak_tetap' and not res.employee_id.is_expatriate:
                res.pjk_thn_reguler_gross = round(self.compute_tax_harian_lepas(income_reguler_gross, res.peng_kena_pjk_reguler_gross, res.npwp))
            elif res.employee_id.employee_tax_status == 'pegawai_tidak_tetap' and res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph26":
                res.pjk_thn_reguler_gross = 0.0
            else:
                res.pjk_thn_reguler_gross = round(self.compute_tax_bracket(res.peng_kena_pjk_reguler_gross,res.npwp))

    @api.depends('peng_kena_pjk_irreguler')
    def _amount_pjk_thn_irreguler(self):
        for res in self:
            income_irreguler = 0
            for rec in res.income_irreguler_ids:
                income_irreguler += rec.amount
            if income_irreguler == 0:
                res.pjk_thn_irreguler = 0
            else:
                income_reguler = 0
                for rec in res.income_reguler_ids:
                    income_reguler += rec.amount
                if res.employee_id.employee_tax_status == 'pegawai_tidak_tetap' and not res.employee_id.is_expatriate:
                    res.pjk_thn_irreguler = round(self.compute_tax_harian_lepas(income_reguler, res.peng_kena_pjk_irreguler, res.npwp))
                elif res.employee_id.employee_tax_status == 'pegawai_tidak_tetap' and res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph26":
                    res.pjk_thn_irreguler = 0.0
                else:
                    res.pjk_thn_irreguler = round(self.compute_tax_bracket(res.peng_kena_pjk_irreguler,res.npwp))
    
    @api.depends('peng_kena_pjk_irreguler_gross')
    def _amount_pjk_thn_irreguler_gross(self):
        for res in self:
            income_irreguler_gross = 0
            for rec in res.income_irreguler_ids.filtered(lambda r: r.tax_calculation_method == "gross" or r.tax_calculation_method == "nett"):
                income_irreguler_gross += rec.amount
            if income_irreguler_gross == 0:
                res.pjk_thn_irreguler_gross = 0
            else:
                income_reguler_gross = 0
                for rec in res.income_reguler_ids.filtered(lambda r: r.tax_calculation_method == "gross" or r.tax_calculation_method == "nett"):
                    income_reguler_gross += rec.amount
                if res.employee_id.employee_tax_status == 'pegawai_tidak_tetap' and not res.employee_id.is_expatriate:
                    res.pjk_thn_irreguler_gross = round(self.compute_tax_harian_lepas(income_reguler_gross, res.peng_kena_pjk_irreguler_gross, res.npwp))
                elif res.employee_id.employee_tax_status == 'pegawai_tidak_tetap' and res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph26":
                    res.pjk_thn_irreguler_gross = 0.0
                else:
                    res.pjk_thn_irreguler_gross = round(self.compute_tax_bracket(res.peng_kena_pjk_irreguler_gross,res.npwp))

    @api.depends('pjk_thn_reguler')
    def _amount_pjk_terhutang_reguler(self):
        for res in self:
            if res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph26":
                res.pjk_terhutang_reguler = 0.0
            elif res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph21":
                res.pjk_terhutang_reguler = (res.pjk_thn_reguler / 12)
            elif res.employee_id.employee_tax_status == 'pegawai_tetap':
                if res.payslip_period_id.tax_calculation_method == "monthly":
                    res.pjk_terhutang_reguler = (res.pjk_thn_reguler / 12)
                else:
                    total = (res.pjk_thn_reguler / res.tax_end_month) * res.tax_period_length
                    res.pjk_terhutang_reguler = total
            elif res.employee_id.employee_tax_status == 'pegawai_tidak_tetap':
                res.pjk_terhutang_reguler = (res.pjk_thn_reguler / 12)
            else:
                res.pjk_terhutang_reguler = 0.0
    
    @api.depends('pjk_thn_reguler_gross')
    def _amount_pjk_terhutang_reguler_gross(self):
        for res in self:
            if res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph26":
                res.pjk_terhutang_reguler_gross = 0.0
            elif res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph21":
                res.pjk_terhutang_reguler_gross = (res.pjk_thn_reguler_gross / 12)
            elif res.employee_id.employee_tax_status == 'pegawai_tetap':
                if res.payslip_period_id.tax_calculation_method == "monthly":
                    res.pjk_terhutang_reguler_gross = (res.pjk_thn_reguler_gross / 12)
                else:
                    total = (res.pjk_thn_reguler_gross / res.tax_end_month) * res.tax_period_length
                    res.pjk_terhutang_reguler_gross = total
            elif res.employee_id.employee_tax_status == 'pegawai_tidak_tetap':
                res.pjk_terhutang_reguler_gross = (res.pjk_thn_reguler_gross / 12)
            else:
                res.pjk_terhutang_reguler_gross = 0.0

    @api.depends('pjk_thn_irreguler')
    def _amount_pjk_terhutang_irreguler(self):
        for res in self:
            if res.pjk_thn_irreguler == 0:
                total = 0.0
            else:
                total = res.pjk_thn_irreguler - res.pjk_thn_reguler
            res.pjk_terhutang_irreguler = total
    
    @api.depends('pjk_thn_irreguler_gross')
    def _amount_pjk_terhutang_irreguler_gross(self):
        for res in self:
            if res.pjk_thn_irreguler_gross == 0:
                total = 0.0
            else:
                total = res.pjk_thn_irreguler_gross - res.pjk_thn_reguler_gross
            res.pjk_terhutang_irreguler_gross = total

    @api.depends('pjk_terhutang_reguler','pjk_terhutang_reguler_last_month')
    def _amount_pjk_bln_reguler(self):
        for res in self:
            if res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph26":
                total = 0.0
            elif res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph21":
                total = res.pjk_terhutang_reguler
            elif res.employee_id.employee_tax_status == 'pegawai_tetap':
                if res.payslip_period_id.tax_calculation_method == "monthly":
                    if res.tax_period_length == 12:
                        pjk_terhutang_reguler_before = 0
                        self.env.cr.execute(
                                ''' select sum(pjk_terhutang_reguler) as pjk_terhutang_reguler_before from hr_payslip WHERE employee_id = %s and date_from < '%s' AND year = '%s' and state in ('done')''' % (
                                    res.employee_id.id, res.date_from, res.year))
                        payslip_before = self.env.cr.dictfetchall()
                        if payslip_before:
                            pjk_terhutang_reguler_before = payslip_before[0].get('pjk_terhutang_reguler_before')
                        total = res.pjk_thn_reguler - pjk_terhutang_reguler_before
                    else:
                        total = res.pjk_terhutang_reguler
                else:
                    total = res.pjk_terhutang_reguler - res.pjk_terhutang_reguler_last_month
            else:
                total = res.pjk_terhutang_reguler - res.pjk_terhutang_reguler_last_month
            if total <= 0:
                res.pjk_bln_reguler = 0
            else:
                res.pjk_bln_reguler = total
    
    @api.depends('pjk_terhutang_reguler_gross','pjk_terhutang_reguler_last_month_gross')
    def _amount_pjk_bln_reguler_gross(self):
        for res in self:
            if res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph26":
                total = 0.0
            elif res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph21":
                total = res.pjk_terhutang_reguler_gross
            elif res.employee_id.employee_tax_status == 'pegawai_tetap':
                if res.payslip_period_id.tax_calculation_method == "monthly":
                    if res.tax_period_length == 12:
                        pjk_terhutang_reguler_gross_before = 0
                        self.env.cr.execute(
                                ''' select sum(pjk_terhutang_reguler_gross) as pjk_terhutang_reguler_gross_before from hr_payslip WHERE employee_id = %s and date_from < '%s' AND year = '%s' and state in ('done')''' % (
                                    res.employee_id.id, res.date_from, res.year))
                        payslip_before = self.env.cr.dictfetchall()
                        if payslip_before:
                            pjk_terhutang_reguler_gross_before = payslip_before[0].get('pjk_terhutang_reguler_gross_before')
                        total = res.pjk_thn_reguler_gross - pjk_terhutang_reguler_gross_before
                    else:
                        total = res.pjk_terhutang_reguler_gross
                else:
                    total = res.pjk_terhutang_reguler_gross - res.pjk_terhutang_reguler_last_month_gross
            else:
                total = res.pjk_terhutang_reguler_gross - res.pjk_terhutang_reguler_last_month_gross
            if total <= 0:
                res.pjk_bln_reguler_gross = 0
            else:
                res.pjk_bln_reguler_gross = total

    @api.depends('pjk_terhutang_irreguler', 'pjk_terhutang_irreguler_last_month')
    def _amount_pjk_bln_irreguler(self):
        for res in self:
            if res.employee_id.employee_tax_status == 'pegawai_tetap':
                if res.payslip_period_id.tax_calculation_method == "monthly":
                    if res.tax_period_length == 12:
                        pjk_terhutang_irreguler_before = 0
                        self.env.cr.execute(
                                ''' select sum(pjk_terhutang_irreguler) as pjk_terhutang_irreguler_before from hr_payslip WHERE employee_id = %s and date_from < '%s' AND year = '%s' and state in ('done')''' % (
                                    res.employee_id.id, res.date_from, res.year))
                        payslip_before = self.env.cr.dictfetchall()
                        if payslip_before:
                            pjk_terhutang_irreguler_before = payslip_before[0].get('pjk_terhutang_irreguler_before')
                        total = res.pjk_terhutang_irreguler - pjk_terhutang_irreguler_before
                    else:
                        if res.pjk_terhutang_irreguler == 0:
                            total = 0.0
                        else:
                            total = res.pjk_terhutang_irreguler
                else:
                    if res.pjk_terhutang_irreguler == 0:
                        total = 0.0
                    else:
                        total = res.pjk_terhutang_irreguler - res.pjk_terhutang_irreguler_last_month
            else:
                if res.pjk_terhutang_irreguler == 0:
                    total = 0.0
                else:
                    if res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph21":
                        total = res.pjk_terhutang_irreguler
                    else:
                        total = res.pjk_terhutang_irreguler - res.pjk_terhutang_irreguler_last_month
            res.pjk_bln_irreguler = total
    
    @api.depends('pjk_terhutang_irreguler_gross', 'pjk_terhutang_irreguler_last_month_gross')
    def _amount_pjk_bln_irreguler_gross(self):
        for res in self:
            if res.employee_id.employee_tax_status == 'pegawai_tetap':
                if res.payslip_period_id.tax_calculation_method == "monthly":
                    if res.tax_period_length == 12:
                        pjk_terhutang_irreguler_gross_before = 0
                        self.env.cr.execute(
                                ''' select sum(pjk_terhutang_irreguler_gross) as pjk_terhutang_irreguler_gross_before from hr_payslip WHERE employee_id = %s and date_from < '%s' AND year = '%s' and state in ('done')''' % (
                                    res.employee_id.id, res.date_from, res.year))
                        payslip_before = self.env.cr.dictfetchall()
                        if payslip_before:
                            pjk_terhutang_irreguler_gross_before = payslip_before[0].get('pjk_terhutang_irreguler_gross_before')
                        total = res.pjk_terhutang_irreguler_gross - pjk_terhutang_irreguler_gross_before
                    else:
                        if res.pjk_terhutang_irreguler_gross == 0:
                            total = 0.0
                        else:
                            total = res.pjk_terhutang_irreguler_gross
                else:
                    if res.pjk_terhutang_irreguler_gross == 0:
                        total = 0.0
                    else:
                        total = res.pjk_terhutang_irreguler_gross - res.pjk_terhutang_irreguler_last_month_gross
            else:
                if res.pjk_terhutang_irreguler_gross == 0:
                    total = 0.0
                else:
                    if res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph21":
                        total = res.pjk_terhutang_irreguler_gross
                    else:
                        total = res.pjk_terhutang_irreguler_gross - res.pjk_terhutang_irreguler_last_month_gross
            res.pjk_bln_irreguler_gross = total

    @api.depends('bruto', 'employee_id.country_id.tax_treaty_rate')
    def _amount_pjk_pph26(self):
        for res in self:
            tax_setting = self.env['hr.tax.setting'].sudo().search([], limit=1)
            pph26_rate = tax_setting.pph26_rate
            tax_treaty_rate = res.employee_id.country_id.tax_treaty_rate
            if res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph26" and res.employee_id.is_tax_treaty:
                res.pjk_pph26 = (res.bruto * tax_treaty_rate) / 100
            elif res.employee_id.is_expatriate and res.employee_id.expatriate_tax == "pph26":
                res.pjk_pph26 = (res.bruto * pph26_rate) / 100
            else:
                res.pjk_pph26 = 0

    @api.depends('late_deduction_ids.amount')
    def _total_late_amount(self):
        for res in self:
            total = 0
            for rec in res.late_deduction_ids:
                total += rec.amount
            res.total_late_amount = total

    @api.depends('years_of_service','income_reguler_ids')
    def _amount_pesangon(self):
        for res in self:
            if res.payslip_pesangon:
                res.pesangon = self.compute_pesangon_bracket(res.years_of_service,res.income_reguler_ids)
            else:
                res.pesangon = 0

    @api.depends('years_of_service','income_reguler_ids')
    def _amount_upmk(self):
        for res in self:
            if res.payslip_pesangon:
                res.upmk = self.compute_upmk_bracket(res.years_of_service,res.income_reguler_ids)
            else:
                res.pesangon = 0

    @api.depends('pesangon','upmk')
    def _amount_bruto_pesangon(self):
        for res in self:
            if res.payslip_pesangon:
                res.bruto_pesangon = res.pesangon + res.upmk
            else:
                res.bruto_pesangon = 0

    @api.depends('bruto_pesangon')
    def _amount_pph21_pesangon(self):
        for res in self:
            if res.payslip_pesangon:
                res.pph21_pesangon = round(self.compute_tax_pesangon_bracket(res.bruto_pesangon))
            else:
                res.pph21_pesangon = 0

    @api.depends('bruto_pesangon')
    def compute_pph21_pesangon(self):
        for res in self:
            if res.payslip_pesangon:
                res.pph21_pesangon_ids = False
                if res.bruto_pesangon > 0:
                    pph21_pesangon = self.compute_pph21_pesangon_calculation(res.bruto_pesangon)
                    res.pph21_pesangon_ids = [(0, 0, x) for x in pph21_pesangon]
            else:
                res.pph21_pesangon_ids = False

    @api.depends('peng_kena_pjk_reguler')
    def compute_pph21_reguler(self):
        for res in self:
            if res.payslip_pesangon == False:
                res.pph21_reguler_ids = False
                res.pph21_reguler_gross_ids = False
                if res.peng_kena_pjk_reguler > 0:
                    pph21_reguler = self.compute_pph21_bracket_calculation(res.peng_kena_pjk_reguler,res.npwp)
                    res.pph21_reguler_ids = [(0, 0, x) for x in pph21_reguler]
                if res.peng_kena_pjk_reguler_gross > 0:
                    pph21_reguler_gross = self.compute_pph21_gross_bracket_calculation(res.peng_kena_pjk_reguler_gross,res.npwp)
                    res.pph21_reguler_gross_ids = [(0, 0, x) for x in pph21_reguler_gross]
            else:
                res.pph21_reguler_ids = False
                res.pph21_reguler_gross_ids = False

    @api.depends('peng_kena_pjk_irreguler')
    def compute_pph21_irreguler(self):
        for res in self:
            if res.payslip_pesangon == False:
                res.pph21_irreguler_ids = False
                res.pph21_irreguler_gross_ids = False
                if res.peng_kena_pjk_irreguler > 0:
                    pph21_irreguler = self.compute_pph21_bracket_calculation(res.peng_kena_pjk_irreguler, res.npwp)
                    res.pph21_irreguler_ids = [(0, 0, x) for x in pph21_irreguler]
                if res.peng_kena_pjk_irreguler_gross > 0:
                    pph21_irreguler_gross = self.compute_pph21_gross_bracket_calculation(res.peng_kena_pjk_irreguler_gross, res.npwp)
                    res.pph21_irreguler_gross_ids = [(0, 0, x) for x in pph21_irreguler_gross]
            else:
                res.pph21_irreguler_ids = False
                res.pph21_irreguler_gross_ids = False

    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):

        """
        @param contract: Browse record of contracts
        @return: returns a list of dict containing the input that should be applied for the given contract between date_from and date_to
        """
        res = []
        # fill only if the contract as a working schedule linked
        for contract in contracts.filtered(lambda contract: contract.resource_calendar_id):
            day_from = datetime.combine(fields.Date.from_string(date_from), time.min)
            day_to = datetime.combine(fields.Date.from_string(date_to), time.max)

            # compute leave days
            leaves = {}
            calendar = contract.resource_calendar_id
            tz = timezone(calendar.tz)
            day_leave_intervals = contract.employee_id.list_leaves(day_from, day_to,
                                                                   calendar=contract.resource_calendar_id)
            for day, hours, leave in day_leave_intervals:
                holiday = leave.holiday_id
                current_leave_struct = leaves.setdefault(holiday.holiday_status_id, {
                    'name': holiday.holiday_status_id.name or _('Global Leaves'),
                    'sequence': 3,
                    'code': holiday.holiday_status_id.code or 'GLOBAL',
                    'number_of_days': 0.0,
                    'number_of_hours': 0.0,
                    'contract_id': contract.id,
                })
                current_leave_struct['number_of_hours'] += hours
                work_hours = calendar.get_work_hours_count(
                    tz.localize(datetime.combine(day, time.min)),
                    tz.localize(datetime.combine(day, time.max)),
                    compute_leaves=False,
                )
                if work_hours:
                    current_leave_struct['number_of_days'] += hours / work_hours

            # compute worked days
            if contract.resource_calendar_id.schedule == "fixed_schedule":
                work_data = contract.employee_id.get_work_days_data(day_from, day_to,
                                                                    calendar=contract.resource_calendar_id)
            else:
                work_data = contract.resource_calendar_id.get_shift_work_days_data(day_from, day_to)
            attendances = {
                'name': _("Normal Working Days paid at 100%"),
                'sequence': 1,
                'code': 'WORK100',
                'number_of_days': work_data['days'],
                'number_of_hours': work_data['hours'],
                'contract_id': contract.id,
            }

            res.append(attendances)
            res.extend(leaves.values())

            count_saturdays = 0
            count_sundays = 0
            # if self.date_from and self.date_to and self.month_days:
            if date_from and date_to:
                day_start = datetime.strptime(str(date_from), "%Y-%m-%d")
                day_end = datetime.strptime(str(date_to), "%Y-%m-%d")
                nb_of_days = (day_end - day_start).days + 1
                for day in range(0, nb_of_days):
                    if day == 0 and str(day_start.strftime('%A')) == 'Saturday':
                        count_saturdays += 1
                    else:
                        month_date = day_start + relativedelta(days=day)
                        if str(month_date.strftime('%A')) == 'Saturday':
                            count_saturdays += 1
                    if day == 0 and str(day_start.strftime('%A')) == 'Sunday':
                        count_sundays += 1
                    else:
                        month_date = day_start + relativedelta(days=day)
                        if str(month_date.strftime('%A')) == 'Sunday':
                            count_sundays += 1

            res.append({
                'name': _("Total Calendar Days in Current Month"),
                'sequence': 2,
                'code': 'CALDAYS',
                'number_of_days': nb_of_days,
                'number_of_hours': 0.0,
                'contract_id': contract.id,
            })
            count_present = 0.0
            self.env.cr.execute(
                ''' select count(*) as jumlah from hr_attendance WHERE employee_id = %s and check_in >= '%s' and check_in <= '%s' and active = true and worked_hours < minimum_hours''' % (
                    contract.employee_id.id, timezone_datetime(day_from), timezone_datetime(day_to)))
            present = self.env.cr.dictfetchall()
            if present:
                count_present = present[0].get('jumlah')
            res.append({
                'name': _("Total Present in Current Month"),
                'sequence': 4,
                'code': 'COUNT_PRESENT',
                'number_of_days': count_present,
                'number_of_hours': 0.0,
                'contract_id': contract.id,
            })
            count_fully_present = 0.0
            self.env.cr.execute(
                ''' select count(*) as jumlah from hr_attendance WHERE employee_id = %s and check_in >= '%s' and check_in <= '%s' and active = true and worked_hours >= minimum_hours''' % (
                    contract.employee_id.id, timezone_datetime(day_from), timezone_datetime(day_to)))
            fully_present = self.env.cr.dictfetchall()
            if fully_present:
                count_fully_present = fully_present[0].get('jumlah')
            res.append({
                'name': _("Total Fully Present in Current Month"),
                'sequence': 5,
                'code': 'COUNT_FULLY_PRESENT',
                'number_of_days': count_fully_present,
                'number_of_hours': 0.0,
                'contract_id': contract.id,
            })
            count_absent = 0.0
            self.env.cr.execute(
                ''' select count(*) as jumlah from hr_attendance WHERE employee_id = %s and attendance_status = 'absent' and start_working_date >= '%s' and start_working_date <= '%s' and active = true ''' % (
                    contract.employee_id.id, day_start, day_end))
            absent = self.env.cr.dictfetchall()
            if absent:
                count_absent = absent[0].get('jumlah')
            res.append({
                'name': _("Total Absent in Current Month"),
                'sequence': 6,
                'code': 'COUNT_ABSENT',
                'number_of_days': count_absent,
                'number_of_hours': 0.0,
                'contract_id': contract.id,
            })
            count_leave = 0.0
            self.env.cr.execute(
                ''' select count(*) as jumlah from hr_attendance WHERE employee_id = %s and attendance_status = 'leave' and start_working_date >= '%s' and start_working_date <= '%s' and active = true ''' % (
                    contract.employee_id.id, day_start, day_end))
            leave = self.env.cr.dictfetchall()
            if leave:
                count_leave = leave[0].get('jumlah')
            res.append({
                'name': _("Total Leave in Current Month"),
                'sequence': 7,
                'code': 'COUNT_LEAVE',
                'number_of_days': count_leave,
                'number_of_hours': 0.0,
                'contract_id': contract.id,
            })
            count_early_checkin = 0.0
            hours_early_checkin = 0.0
            self.env.cr.execute(
                ''' select count(*) as jumlah, SUM(early_check_in_diff) as sum_hours from hr_attendance WHERE employee_id = %s and checkin_status = 'early' and check_in >= '%s' and check_in <= '%s' and active = true ''' % (
                    contract.employee_id.id, timezone_datetime(day_from), timezone_datetime(day_to)))
            early_checkin = self.env.cr.dictfetchall()
            if early_checkin:
                count_early_checkin = early_checkin[0].get('jumlah')
                hours_early_checkin = early_checkin[0].get('sum_hours')
            res.append({
                'name': _("Early Check in"),
                'sequence': 8,
                'code': 'EARLY_CHECKIN',
                'number_of_days': count_early_checkin,
                'number_of_hours': hours_early_checkin,
                'contract_id': contract.id,
            })
            count_ontime_checkin = 0.0
            self.env.cr.execute(
                ''' select count(*) as jumlah from hr_attendance WHERE employee_id = %s and checkin_status = 'ontime' and check_in >= '%s' and check_in <= '%s' and active = true ''' % (
                    contract.employee_id.id, timezone_datetime(day_from), timezone_datetime(day_to)))
            ontime_checkin = self.env.cr.dictfetchall()
            if ontime_checkin:
                count_ontime_checkin = ontime_checkin[0].get('jumlah')
            res.append({
                'name': _("Ontime Check in"),
                'sequence': 9,
                'code': 'ONTIME_CHECKIN',
                'number_of_days': count_ontime_checkin,
                'number_of_hours': 0.0,
                'contract_id': contract.id,
            })
            count_late_checkin = 0.0
            hours_late_checkin = 0.0
            self.env.cr.execute(
                ''' select count(*) as jumlah, SUM(check_in_diff) as sum_hours from hr_attendance WHERE employee_id = %s and checkin_status = 'late' and check_in >= '%s' and check_in <= '%s' and active = true ''' % (
                    contract.employee_id.id, timezone_datetime(day_from), timezone_datetime(day_to)))
            late_checkin = self.env.cr.dictfetchall()
            if late_checkin:
                count_late_checkin = late_checkin[0].get('jumlah')
                hours_late_checkin = late_checkin[0].get('sum_hours')
            res.append({
                'name': _("Late Check in"),
                'sequence': 10,
                'code': 'LATE_CHECKIN',
                'number_of_days': count_late_checkin,
                'number_of_hours': hours_late_checkin,
                'contract_id': contract.id,
            })
            count_no_checkin = 0.0
            self.env.cr.execute(
                ''' select count(*) as jumlah from hr_attendance WHERE employee_id = %s and checkin_status = 'no_checking' and start_working_date >= '%s' and start_working_date <= '%s' and active = true ''' % (
                    contract.employee_id.id, day_start, day_end))
            no_checkin = self.env.cr.dictfetchall()
            if no_checkin:
                count_no_checkin = no_checkin[0].get('jumlah')
            res.append({
                'name': _("No Check in"),
                'sequence': 11,
                'code': 'NO_CHECKIN',
                'number_of_days': count_no_checkin,
                'number_of_hours': 0.0,
                'contract_id': contract.id,
            })
            count_early_checkout = 0.0
            hours_early_checkout = 0.0
            self.env.cr.execute(
                ''' select count(*) as jumlah, SUM(early_check_out_diff) as sum_hours from hr_attendance WHERE employee_id = %s and checkout_status = 'early' and check_in >= '%s' and check_in <= '%s' and active = true ''' % (
                    contract.employee_id.id, timezone_datetime(day_from), timezone_datetime(day_to)))
            early_checkout = self.env.cr.dictfetchall()
            if early_checkout:
                count_early_checkout = early_checkout[0].get('jumlah')
                hours_early_checkout = early_checkout[0].get('sum_hours')
            res.append({
                'name': _("Early Check out"),
                'sequence': 12,
                'code': 'EARLY_CHECKOUT',
                'number_of_days': count_early_checkout,
                'number_of_hours': hours_early_checkout,
                'contract_id': contract.id,
            })
            count_ontime_checkout = 0.0
            self.env.cr.execute(
                ''' select count(*) as jumlah from hr_attendance WHERE employee_id = %s and checkout_status = 'ontime' and check_in >= '%s' and check_in <= '%s' and active = true ''' % (
                    contract.employee_id.id, timezone_datetime(day_from), timezone_datetime(day_to)))
            ontime_checkout = self.env.cr.dictfetchall()
            if ontime_checkout:
                count_ontime_checkout = ontime_checkout[0].get('jumlah')
            res.append({
                'name': _("Ontime Check out"),
                'sequence': 13,
                'code': 'ONTIME_CHECKOUT',
                'number_of_days': count_ontime_checkout,
                'number_of_hours': 0.0,
                'contract_id': contract.id,
            })
            count_late_checkout = 0.0
            hours_late_checkout = 0.0
            self.env.cr.execute(
                ''' select count(*) as jumlah, SUM(late_check_out_diff) as sum_hours from hr_attendance WHERE employee_id = %s and checkout_status = 'late' and check_in >= '%s' and check_in <= '%s' and active = true ''' % (
                    contract.employee_id.id, timezone_datetime(day_from), timezone_datetime(day_to)))
            late_checkout = self.env.cr.dictfetchall()
            if late_checkout:
                count_late_checkout = late_checkout[0].get('jumlah')
                hours_late_checkout = late_checkout[0].get('sum_hours')
            res.append({
                'name': _("Late Check out"),
                'sequence': 14,
                'code': 'LATE_CHECKOUT',
                'number_of_days': count_late_checkout,
                'number_of_hours': hours_late_checkout,
                'contract_id': contract.id,
            })
            count_no_checkout = 0.0
            self.env.cr.execute(
                ''' select count(*) as jumlah from hr_attendance WHERE employee_id = %s and checkout_status = 'no_checkout' and check_in >= '%s' and check_in <= '%s' and active = true ''' % (
                    contract.employee_id.id, timezone_datetime(day_from), timezone_datetime(day_to)))
            no_checkout = self.env.cr.dictfetchall()
            if no_checkout:
                count_no_checkout = no_checkout[0].get('jumlah')
            res.append({
                'name': _("No Check out"),
                'sequence': 15,
                'code': 'NO_CHECKOUT',
                'number_of_days': count_no_checkout,
                'number_of_hours': 0.0,
                'contract_id': contract.id,
            })
            res.append({
                'name': _("Total Saturdays in Current Month"),
                'sequence': 16,
                'code': 'SATURDAYS',
                'number_of_days': count_saturdays,
                'number_of_hours': 0.0,
                'contract_id': contract.id,
            })
            res.append({
                'name': _("Total Sundays in Current Month"),
                'sequence': 17,
                'code': 'SUNDAYS',
                'number_of_days': count_sundays,
                'number_of_hours': 0.0,
                'contract_id': contract.id,
            })
            res.append({
                'name': _("Total Overtime"),
                'sequence': 18,
                'code': 'OVERTIME',
                'number_of_days': 0.0,
                'number_of_hours': 0.0,
                'contract_id': contract.id,
            })
        return res

    def compute_multi_payslips(self):
        for record in self:
            if record.state == 'draft':
                record.compute_sheet()

    def action_send_email_payslip(self):
        self.ensure_one()
        template = self.env.ref('equip3_hr_payroll_extend_id.email_template_for_payslip')
        if template:
            self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True)
            self.send_email_flag = True

            view = self.env.ref('equip3_hr_payroll_extend_id.view_payslip_send_email_message_form')
            view_id = view and view.id or False
            context = dict(self._context or {})
            return {
                'name': "Message",
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'payslip.send.email.message',
                'views': [(view_id, 'form')],
                'view_id': view_id,
                'target': 'new',
                'context': context,
            }

    def action_send_email_payslips(self):
        self.ensure_one()
        template = self.env.ref('equip3_hr_payroll_extend_id.email_template_for_payslip')
        if template:
            self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True)
            self.send_email_flag = True

    def get_income_subtotal_payslip(self):
        if self.line_ids:
            income = 0.00
            for line in self.line_ids:
                if line.salary_rule_id.appears_on_payslip and line.salary_rule_id.category_on_payslip == 'income':
                    for rec in line.salary_rule_id.payslip_type:
                        if rec.name == 'Employee Payslip':
                            income += line.total
            return income
        else:
            return 0

    def get_deduction_subtotal_payslip(self):
        if self.line_ids:
            income = 0.00
            for line in self.line_ids:
                if line.salary_rule_id.appears_on_payslip and line.salary_rule_id.category_on_payslip == 'deduction':
                    for rec in line.salary_rule_id.payslip_type:
                        if rec.name == 'Employee Payslip':
                            income += line.total
            return income
        else:
            return 0

    def get_income_subtotal_bonus_payslip(self):
        if self.line_ids:
            income = 0.00
            for line in self.line_ids:
                if line.salary_rule_id.appears_on_payslip and line.salary_rule_id.category_on_payslip == 'income':
                    for rec in line.salary_rule_id.payslip_type:
                        if rec.name == 'Bonus Payslip':
                            income += line.total
            return income
        else:
            return 0

    def get_deduction_subtotal_bonus_payslip(self):
        if self.line_ids:
            income = 0.00
            for line in self.line_ids:
                if line.salary_rule_id.appears_on_payslip and line.salary_rule_id.category_on_payslip == 'deduction':
                    for rec in line.salary_rule_id.payslip_type:
                        if rec.name == 'Bonus Payslip':
                            income += line.total
            return income
        else:
            return 0

    def get_income_subtotal_thr_payslip(self):
        if self.line_ids:
            income = 0.00
            for line in self.line_ids:
                if line.salary_rule_id.appears_on_payslip and line.salary_rule_id.category_on_payslip == 'income':
                    for rec in line.salary_rule_id.payslip_type:
                        if rec.name == 'THR Payslip':
                            income += line.total
            return income
        else:
            return 0

    def get_deduction_subtotal_thr_payslip(self):
        if self.line_ids:
            income = 0.00
            for line in self.line_ids:
                if line.salary_rule_id.appears_on_payslip and line.salary_rule_id.category_on_payslip == 'deduction':
                    for rec in line.salary_rule_id.payslip_type:
                        if rec.name == 'THR Payslip':
                            income += line.total
            return income
        else:
            return 0

    def _compute_payslip_type(self):
        for res in self:
            payslip = 0.0
            bonus_payslip = 0.0
            thr_payslip = 0.0
            for line in res.line_ids:
                for rec in line.salary_rule_id.payslip_type:
                    if rec.name == 'Employee Payslip':
                        payslip += 1.0
                    if rec.name == 'Bonus Payslip':
                        bonus_payslip += 1.0
                    if rec.name == 'THR Payslip':
                        thr_payslip += 1.0
            res.count_payslip_type = payslip
            res.count_bonus_payslip_type = bonus_payslip
            res.count_thr_payslip_type = thr_payslip

    def _compute_button_refund(self):
        for res in self:
            payslip_obj = self.env['hr.payslip'].sudo().search([('employee_id', '=', res.employee_id.id),
                                                                (
                                                                'payslip_period_id', '=', res.payslip_period_id.id),
                                                                ('state', '=', 'done')], limit=1,
                                                               order='payslip_report_date desc')
            if payslip_obj.id != res.id:
                res.hide_button_refund = True
            else:
                res.hide_button_refund = False

    def action_payslip_done(self):
        res = super(HrPayslip, self).action_payslip_done()

        for slip in self:
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            date = slip.date or slip.date_to
            currency = slip.company_id.currency_id

            if not slip.payslip_pesangon:
                month_name = slip.month_name
                year = slip.year
                name = _('Payslip of %s') % (slip.employee_id.name)
            else:
                month_name = date.strftime("%B")
                year = date.strftime("%Y")
                name = _('Pesangon Payslip of %s') % (slip.employee_id.name)

            move_dict = {
                'narration': name,
                'ref': slip.number,
                'journal_id': slip.journal_id.id,
                'date': date,
            }
            for line in slip.details_by_salary_rule_category:
                amount = currency.round(slip.credit_note and -line.total or line.total)
                if currency.is_zero(amount):
                    continue
                debit_account_id = line.salary_rule_id.account_debit.id
                credit_account_id = line.salary_rule_id.account_credit.id

                if debit_account_id:
                    debit_line = (0, 0, {
                        'name': slip.employee_id.name + '-' + slip.number + '-' + month_name + ' ' + year + '-' + line.name,
                        'partner_id': line._get_partner_id(credit_account=False),
                        'account_id': debit_account_id,
                        'journal_id': slip.journal_id.id,
                        'date': date,
                        'debit': amount > 0.0 and amount or 0.0,
                        'credit': amount < 0.0 and -amount or 0.0,
                        'analytic_account_id': line.salary_rule_id.analytic_account_id.id,
                        'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        'analytic_tag_ids': slip.employee_id.analytic_group_id.ids,
                    })
                    line_ids.append(debit_line)
                    debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
                if credit_account_id:
                    credit_line = (0, 0, {
                        'name': slip.employee_id.name + '-' + slip.number + '-' + month_name + ' ' + year + '-' + line.name,
                        'partner_id': line._get_partner_id(credit_account=True),
                        'account_id': credit_account_id,
                        'journal_id': slip.journal_id.id,
                        'date': date,
                        'debit': amount < 0.0 and -amount or 0.0,
                        'credit': amount > 0.0 and amount or 0.0,
                        'analytic_account_id': line.salary_rule_id.analytic_account_id.id,
                        'tax_line_id': line.salary_rule_id.account_tax_id.id,
                        'analytic_tag_ids': slip.employee_id.analytic_group_id.ids,
                    })
                    line_ids.append(credit_line)
                    credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']

            if currency.compare_amounts(credit_sum, debit_sum) == -1:
                acc_id = slip.journal_id.default_credit_account_id.id
                if not acc_id:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Credit Account!') % (
                        slip.journal_id.name))
                adjust_credit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'partner_id': False,
                    'account_id': acc_id,
                    'journal_id': slip.journal_id.id,
                    'date': date,
                    'debit': 0.0,
                    'credit': currency.round(debit_sum - credit_sum),
                })
                line_ids.append(adjust_credit)

            elif currency.compare_amounts(debit_sum, credit_sum) == -1:
                acc_id = slip.journal_id.default_debit_account_id.id
                if not acc_id:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Debit Account!') % (
                        slip.journal_id.name))
                adjust_debit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'partner_id': False,
                    'account_id': acc_id,
                    'journal_id': slip.journal_id.id,
                    'date': date,
                    'debit': currency.round(credit_sum - debit_sum),
                    'credit': 0.0,
                })
                line_ids.append(adjust_debit)
            move_dict['line_ids'] = line_ids
            move = self.env['account.move'].create(move_dict)
            slip.write({'move_id': move.id, 'date': date})
            if not move.line_ids:
                raise UserError(_("As you installed the payroll accounting module you have to choose Debit and Credit"
                                  " account for at least one salary rule in the choosen Salary Structure."))
            move.post()
        return res

    def action_payslip_refund(self):
        return self.write({'state': 'refund'})

    def refund_sheet(self):
        for payslip in self:
            payslip_obj = self.env['hr.payslip'].sudo().search([('employee_id','=',payslip.employee_id.id),
                                                                ('payslip_period_id','=',payslip.payslip_period_id.id),
                                                                ('state','=','done')], limit=1, order='payslip_report_date desc')
            if payslip_obj.id != payslip.id:
                raise ValidationError(_("Can't refund this payslip!"))
            else:
                copied_payslip = payslip.copy({'credit_note': True, 'name': _('Refund: ') + payslip.name, 'refund_reference': payslip.id})
                copied_payslip.compute_sheet()
                copied_payslip.action_payslip_done()
                copied_payslip.action_payslip_refund()
                payslip.action_payslip_refund()
                payslip.refund_reference = copied_payslip.id
        formview_ref = self.env.ref('hr_payroll_community.view_hr_payslip_form', False)
        treeview_ref = self.env.ref('hr_payroll_community.view_hr_payslip_tree', False)
        return {
            'name': ("Refund Payslip"),
            'view_mode': 'tree, form',
            'view_id': False,
            'res_model': 'hr.payslip',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': "[('id', 'in', %s)]" % copied_payslip.ids,
            'views': [(treeview_ref and treeview_ref.id or False, 'tree'),
                      (formview_ref and formview_ref.id or False, 'form')],
            'context': {}
        }

    def get_salary(self, payslip, date_from, date_to):
        payslip_rec = self.sudo().browse(payslip)[0]
        amount = 0.0
        payslip_rec.write({'rapel_amount': 0.0})

        rec = payslip_rec.contract_id
        start_contract_month = datetime.strptime(str(rec.date_start), '%Y-%m-%d').strftime("%B")
        start_contract_year = datetime.strptime(str(rec.date_start), '%Y-%m-%d').date().year
        payslip_month = payslip_rec.month.month
        payslip_year = payslip_rec.year

        if rec:
            contract_before = self.env['hr.contract'].sudo().search([('employee_id', '=', payslip_rec.employee_id.id),('date_start', '<', rec.date_start),('state', '=', 'close')], order='id desc', limit=1)
            if rec.rapel_date:
                if rec.date_start >= rec.rapel_date:
                    if date_from.day == rec.date_start.day and start_contract_month == payslip_month and str(start_contract_year) == payslip_year:
                        amount = rec.wage
                    elif start_contract_month == payslip_month and str(start_contract_year) == payslip_year:
                        day_from_payslip = datetime.combine(fields.Date.from_string(date_from), time.min)
                        day_to_payslip = datetime.combine(fields.Date.from_string(date_to), time.max)
                        first_date_before = datetime.combine(fields.Date.from_string(contract_before.date_end.replace(day=1)), time.min)
                        get_last_date_before = calendar.monthrange(contract_before.date_end.year, contract_before.date_end.month)[1]
                        last_date_before = datetime.combine(fields.Date.from_string(contract_before.date_end.replace(day=get_last_date_before)), time.min)
                        day_from_before = datetime.combine(fields.Date.from_string(contract_before.date_start), time.min)
                        day_to_before = datetime.combine(fields.Date.from_string(contract_before.date_end), time.max)
                        first_date = datetime.combine(fields.Date.from_string(rec.date_start.replace(day=1)), time.min)
                        get_last_date = calendar.monthrange(rec.date_start.year, rec.date_start.month)[1]
                        last_date = datetime.combine(fields.Date.from_string(rec.date_start.replace(day=get_last_date)), time.min)
                        day_from = datetime.combine(fields.Date.from_string(rec.date_start), time.min)
                        
                        work_day_before = relativedelta(last_date_before, first_date_before).days + 1
                        work_data_before = relativedelta(day_to_before, day_from_payslip).days + 1
                        salary_before = (contract_before.wage / work_day_before) * work_data_before
                        
                        work_day = relativedelta(last_date, first_date).days + 1
                        work_data = relativedelta(day_to_payslip, day_from).days + 1
                        salary = (rec.wage / work_day) * work_data
                        
                        amount = salary_before + salary
                    else:
                        amount = rec.wage

                elif (date_from <= rec.rapel_date <= date_to) or (date_from > rec.rapel_date):
                    amount = rec.wage
                else:
                    amount = contract_before.wage if contract_before else 0.0

                    if date_from.day == rec.date_start.day and start_contract_month == payslip_month and str(start_contract_year) == payslip_year:
                        rapel_amount = rec.wage - contract_before.wage
                        payslip_rec.write({'rapel_amount': rapel_amount})
                    elif start_contract_month == payslip_month and str(start_contract_year) == payslip_year:
                        day_from_payslip = datetime.combine(fields.Date.from_string(date_from), time.min)
                        day_to_payslip = datetime.combine(fields.Date.from_string(date_to), time.max)
                        first_date_before = datetime.combine(fields.Date.from_string(contract_before.date_end.replace(day=1)), time.min)
                        get_last_date_before = calendar.monthrange(contract_before.date_end.year, contract_before.date_end.month)[1]
                        last_date_before = datetime.combine(fields.Date.from_string(contract_before.date_end.replace(day=get_last_date_before)), time.min)
                        day_from_before = datetime.combine(fields.Date.from_string(contract_before.date_start), time.min)
                        day_to_before = datetime.combine(fields.Date.from_string(contract_before.date_end), time.max)
                        first_date = datetime.combine(fields.Date.from_string(rec.date_start.replace(day=1)), time.min)
                        get_last_date = calendar.monthrange(rec.date_start.year, rec.date_start.month)[1]
                        last_date = datetime.combine(fields.Date.from_string(rec.date_start.replace(day=get_last_date)), time.min)
                        day_from = datetime.combine(fields.Date.from_string(rec.date_start), time.min)
                        
                        work_day_before = relativedelta(last_date_before, first_date_before).days + 1
                        work_data_before = relativedelta(day_to_before, day_from_payslip).days + 1
                        salary_before = (contract_before.wage / work_day_before) * work_data_before
                        
                        work_day = relativedelta(last_date, first_date).days + 1
                        work_data = relativedelta(day_to_payslip, day_from).days + 1
                        salary = (rec.wage / work_day) * work_data
                        
                        total = salary_before + salary
                        rapel_amount = total - contract_before.wage
                        payslip_rec.write({'rapel_amount': rapel_amount})
                    else:
                        rapel_amount = rec.wage - contract_before.wage
                        payslip_rec.write({'rapel_amount': rapel_amount})
            elif contract_before and contract_before.wage != rec.wage:
                if date_from.day == rec.date_start.day and start_contract_month == payslip_month and str(start_contract_year) == payslip_year:
                    amount = rec.wage
                elif start_contract_month == payslip_month and str(start_contract_year) == payslip_year:
                    day_from_payslip = datetime.combine(fields.Date.from_string(date_from), time.min)
                    day_to_payslip = datetime.combine(fields.Date.from_string(date_to), time.max)
                    first_date_before = datetime.combine(fields.Date.from_string(contract_before.date_end.replace(day=1)), time.min)
                    get_last_date_before = calendar.monthrange(contract_before.date_end.year, contract_before.date_end.month)[1]
                    last_date_before = datetime.combine(fields.Date.from_string(contract_before.date_end.replace(day=get_last_date_before)), time.min)
                    day_from_before = datetime.combine(fields.Date.from_string(contract_before.date_start), time.min)
                    day_to_before = datetime.combine(fields.Date.from_string(contract_before.date_end), time.max)
                    first_date = datetime.combine(fields.Date.from_string(rec.date_start.replace(day=1)), time.min)
                    get_last_date = calendar.monthrange(rec.date_start.year, rec.date_start.month)[1]
                    last_date = datetime.combine(fields.Date.from_string(rec.date_start.replace(day=get_last_date)), time.min)
                    day_from = datetime.combine(fields.Date.from_string(rec.date_start), time.min)
                    
                    work_day_before = relativedelta(last_date_before, first_date_before).days + 1
                    work_data_before = relativedelta(day_to_before, day_from_payslip).days + 1
                    salary_before = (contract_before.wage / work_day_before) * work_data_before
                    
                    work_day = relativedelta(last_date, first_date).days + 1
                    work_data = relativedelta(day_to_payslip, day_from).days + 1
                    salary = (rec.wage / work_day) * work_data
                    
                    amount = salary_before + salary
                else:
                    amount = rec.wage
            else:
                amount = rec.wage
        return amount

    def get_rapel_salary(self, payslip, date_from, date_to):
        payslip_rec = self.sudo().browse(payslip)[0]
        amount = 0.0
        # a contract is valid if it ends between the given dates
        clause_1 = ['&', ('date_end', '<=', date_to), ('date_end', '>=', date_from)]
        # OR if it starts between the given dates
        clause_2 = ['&', ('date_start', '<=', date_to), ('date_start', '>=', date_from)]
        # OR if it starts before the date_from and finish after the date_end (or never finish)
        clause_3 = ['&', ('date_start', '<=', date_from), '|', ('date_end', '=', False), ('date_end', '>=', date_to)]
        clause_final = [('employee_id', '=', payslip_rec.employee_id.id), ('state', '=', 'open'), '|',
                        '|'] + clause_1 + clause_2 + clause_3
        contract_lines = self.env['hr.contract'].sudo().search(clause_final)
        if contract_lines:
            for rec in contract_lines:
                if rec.rapel_date and rec.rapel_date >= date_from and rec.rapel_date <= date_to:
                    contract_before = self.env['hr.contract'].sudo().search([('employee_id', '=', payslip_rec.employee_id.id),('date_start', '<', rec.date_start),('state', '=', 'close')], order='id desc', limit=1)
                    start_contract_month = datetime.strptime(str(rec.date_start), '%Y-%m-%d').date().month
                    payslip_before = self.sudo().search([
                        ('employee_id', '=', payslip_rec.employee_id.id),
                        ('year', '=', payslip_rec.year),
                        ('tax_period_length', '>=', start_contract_month),
                        ('date_from', '<', date_from),
                        ('state', '=', 'done')])
                    amount = 0.0
                    for slip in payslip_before:
                        amount += slip.rapel_amount
                else:
                    amount = 0.0
        return amount

    def get_allowance(self, payslip, date_from, date_to):
        result = {
            "allowance_1": 0.0,
            "allowance_2": 0.0,
            "allowance_3": 0.0,
            "allowance_4": 0.0,
            "allowance_5": 0.0,
            "allowance_6": 0.0,
            "allowance_7": 0.0,
            "allowance_8": 0.0,
            "allowance_9": 0.0,
            "allowance_10": 0.0,
        }
        payslip_rec = self.sudo().browse(payslip)[0]
        amount_allowance_1 = 0.0
        amount_allowance_2 = 0.0
        amount_allowance_3 = 0.0
        amount_allowance_4 = 0.0
        amount_allowance_5 = 0.0
        amount_allowance_6 = 0.0
        amount_allowance_7 = 0.0
        amount_allowance_8 = 0.0
        amount_allowance_9 = 0.0
        amount_allowance_10 = 0.0

        rec = payslip_rec.contract_id

        if rec and rec.state == "open":
                if rec.rapel_date:
                    contract_before = self.env['hr.contract'].sudo().search([('employee_id', '=', payslip_rec.employee_id.id),('date_start', '<', rec.date_start),('state', '=', 'close')], order='id desc', limit=1)
                    if date_from < rec.rapel_date:
                        amount_allowance_1 = contract_before.other_allowance_1 if contract_before else 0.0
                        amount_allowance_2 = contract_before.other_allowance_2 if contract_before else 0.0
                        amount_allowance_3 = contract_before.other_allowance_3 if contract_before else 0.0
                        amount_allowance_4 = contract_before.other_allowance_4 if contract_before else 0.0
                        amount_allowance_5 = contract_before.other_allowance_5 if contract_before else 0.0
                        amount_allowance_6 = contract_before.other_allowance_6 if contract_before else 0.0
                        amount_allowance_7 = contract_before.other_allowance_7 if contract_before else 0.0
                        amount_allowance_8 = contract_before.other_allowance_8 if contract_before else 0.0
                        amount_allowance_9 = contract_before.other_allowance_9 if contract_before else 0.0
                        amount_allowance_10 = contract_before.other_allowance_10 if contract_before else 0.0
                    else:
                        amount_allowance_1 = rec.other_allowance_1
                        amount_allowance_2 = rec.other_allowance_2
                        amount_allowance_3 = rec.other_allowance_3
                        amount_allowance_4 = rec.other_allowance_4
                        amount_allowance_5 = rec.other_allowance_5
                        amount_allowance_6 = rec.other_allowance_6
                        amount_allowance_7 = rec.other_allowance_7
                        amount_allowance_8 = rec.other_allowance_8
                        amount_allowance_9 = rec.other_allowance_9
                        amount_allowance_10 = rec.other_allowance_10
                else:
                    amount_allowance_1 = rec.other_allowance_1
                    amount_allowance_2 = rec.other_allowance_2
                    amount_allowance_3 = rec.other_allowance_3
                    amount_allowance_4 = rec.other_allowance_4
                    amount_allowance_5 = rec.other_allowance_5
                    amount_allowance_6 = rec.other_allowance_6
                    amount_allowance_7 = rec.other_allowance_7
                    amount_allowance_8 = rec.other_allowance_8
                    amount_allowance_9 = rec.other_allowance_9
                    amount_allowance_10 = rec.other_allowance_10
        result["allowance_1"] = amount_allowance_1
        result["allowance_2"] = amount_allowance_2
        result["allowance_3"] = amount_allowance_3
        result["allowance_4"] = amount_allowance_4
        result["allowance_5"] = amount_allowance_5
        result["allowance_6"] = amount_allowance_6
        result["allowance_7"] = amount_allowance_7
        result["allowance_8"] = amount_allowance_8
        result["allowance_9"] = amount_allowance_9
        result["allowance_10"] = amount_allowance_10
        return result

    def get_rapel_allowance(self, payslip, date_from, date_to):
        result = {
            "allowance_1": 0.0,
            "allowance_2": 0.0,
            "allowance_3": 0.0,
            "allowance_4": 0.0,
            "allowance_5": 0.0,
            "allowance_6": 0.0,
            "allowance_7": 0.0,
            "allowance_8": 0.0,
            "allowance_9": 0.0,
            "allowance_10": 0.0,
        }
        payslip_rec = self.sudo().browse(payslip)[0]
        amount_allowance_1 = 0.0
        amount_allowance_2 = 0.0
        amount_allowance_3 = 0.0
        amount_allowance_4 = 0.0
        amount_allowance_5 = 0.0
        amount_allowance_6 = 0.0
        amount_allowance_7 = 0.0
        amount_allowance_8 = 0.0
        amount_allowance_9 = 0.0
        amount_allowance_10 = 0.0
        # a contract is valid if it ends between the given dates
        clause_1 = ['&', ('date_end', '<=', date_to), ('date_end', '>=', date_from)]
        # OR if it starts between the given dates
        clause_2 = ['&', ('date_start', '<=', date_to), ('date_start', '>=', date_from)]
        # OR if it starts before the date_from and finish after the date_end (or never finish)
        clause_3 = ['&', ('date_start', '<=', date_from), '|', ('date_end', '=', False), ('date_end', '>=', date_to)]
        clause_final = [('employee_id', '=', payslip_rec.employee_id.id), ('state', '=', 'open'), '|',
                        '|'] + clause_1 + clause_2 + clause_3
        contract_lines = self.env['hr.contract'].sudo().search(clause_final)
        if contract_lines:
            for rec in contract_lines:
                if rec.rapel_date and rec.rapel_date >= date_from and rec.rapel_date <= date_to:
                    contract_before = self.env['hr.contract'].sudo().search([('employee_id', '=', payslip_rec.employee_id.id),('date_start', '<', rec.date_start),('state', '=', 'close')], order='id desc', limit=1)
                    allowance_1 = rec.other_allowance_1 - contract_before.other_allowance_1 if contract_before else 0.0
                    allowance_2 = rec.other_allowance_2 - contract_before.other_allowance_2 if contract_before else 0.0
                    allowance_3 = rec.other_allowance_3 - contract_before.other_allowance_3 if contract_before else 0.0
                    allowance_4 = rec.other_allowance_4 - contract_before.other_allowance_4 if contract_before else 0.0
                    allowance_5 = rec.other_allowance_5 - contract_before.other_allowance_5 if contract_before else 0.0
                    allowance_6 = rec.other_allowance_6 - contract_before.other_allowance_6 if contract_before else 0.0
                    allowance_7 = rec.other_allowance_7 - contract_before.other_allowance_7 if contract_before else 0.0
                    allowance_8 = rec.other_allowance_8 - contract_before.other_allowance_8 if contract_before else 0.0
                    allowance_9 = rec.other_allowance_9 - contract_before.other_allowance_9 if contract_before else 0.0
                    allowance_10 = rec.other_allowance_10 - contract_before.other_allowance_10 if contract_before else 0.0
                    start_contract_month = datetime.strptime(str(rec.date_start), '%Y-%m-%d').date().month
                    payslip_before = self.sudo().search([
                        ('employee_id', '=', payslip_rec.employee_id.id),
                        ('year', '=', payslip_rec.year),
                        ('tax_period_length', '>=', start_contract_month),
                        ('date_from', '<', date_from),
                        ('state', '=', 'done')])
                    amount_allowance_1 = allowance_1 * len(payslip_before)
                    amount_allowance_2 = allowance_2 * len(payslip_before)
                    amount_allowance_3 = allowance_3 * len(payslip_before)
                    amount_allowance_4 = allowance_4 * len(payslip_before)
                    amount_allowance_5 = allowance_5 * len(payslip_before)
                    amount_allowance_6 = allowance_6 * len(payslip_before)
                    amount_allowance_7 = allowance_7 * len(payslip_before)
                    amount_allowance_8 = allowance_8 * len(payslip_before)
                    amount_allowance_9 = allowance_9 * len(payslip_before)
                    amount_allowance_10 = allowance_10 * len(payslip_before)
                else:
                    amount_allowance_1 = 0.0
                    amount_allowance_2 = 0.0
                    amount_allowance_3 = 0.0
                    amount_allowance_4 = 0.0
                    amount_allowance_5 = 0.0
                    amount_allowance_6 = 0.0
                    amount_allowance_7 = 0.0
                    amount_allowance_8 = 0.0
                    amount_allowance_9 = 0.0
                    amount_allowance_10 = 0.0
        result["allowance_1"] = amount_allowance_1
        result["allowance_2"] = amount_allowance_2
        result["allowance_3"] = amount_allowance_3
        result["allowance_4"] = amount_allowance_4
        result["allowance_5"] = amount_allowance_5
        result["allowance_6"] = amount_allowance_6
        result["allowance_7"] = amount_allowance_7
        result["allowance_8"] = amount_allowance_8
        result["allowance_9"] = amount_allowance_9
        result["allowance_10"] = amount_allowance_10
        return result

    def get_rapel_bpjs_comp(self, payslip, date_from, date_to, bpjs_kes_co):
        payslip_rec = self.sudo().browse(payslip)[0]
        amount = 0.0
        # a contract is valid if it ends between the given dates
        clause_1 = ['&', ('date_end', '<=', date_to), ('date_end', '>=', date_from)]
        # OR if it starts between the given dates
        clause_2 = ['&', ('date_start', '<=', date_to), ('date_start', '>=', date_from)]
        # OR if it starts before the date_from and finish after the date_end (or never finish)
        clause_3 = ['&', ('date_start', '<=', date_from), '|', ('date_end', '=', False), ('date_end', '>=', date_to)]
        clause_final = [('employee_id', '=', payslip_rec.employee_id.id), ('state', '=', 'open'), '|',
                        '|'] + clause_1 + clause_2 + clause_3
        contract_lines = self.env['hr.contract'].sudo().search(clause_final)
        if contract_lines:
            for rec in contract_lines:
                if rec.rapel_date and rec.rapel_date >= date_from and rec.rapel_date <= date_to:
                    amount_bpjs = bpjs_kes_co

                    start_contract_month = datetime.strptime(str(rec.date_start), '%Y-%m-%d').date().month
                    payslip_before = self.sudo().search([
                        ('employee_id', '=', payslip_rec.employee_id.id),
                        ('year', '=', payslip_rec.year),
                        ('tax_period_length', '>=', start_contract_month),
                        ('date_from', '<', date_from),
                        ('state', '=', 'done')])
                    
                    amount_rapel_bpjs = 0.0
                    for res in payslip_before:
                        bpjs_before = res.income_reguler_ids.filtered(lambda r: r.code == 'BPJS_KES_CO')[0]
                        amount_rapel_bpjs += amount_bpjs - bpjs_before.amount

                    amount = amount_rapel_bpjs
                else:
                    amount = 0.0
        return amount

    @api.depends('income_reguler_ter_ids.amount','ter_akum_income_last_month','ter_tunj_pjk_terhutang_reguler')
    def _amount_ter_akum_income_reguler(self):
        for res in self:
            total = 0
            for rec in res.income_reguler_ter_ids:
                total += rec.amount
            if res.ter_tunj_pjk_terhutang_reguler > 0:
                ter_tunj_pjk_terhutang_reguler = res.ter_tunj_pjk_terhutang_reguler
            else:
                ter_tunj_pjk_terhutang_reguler = 0
            res.ter_akum_income_reguler = total + ter_tunj_pjk_terhutang_reguler + res.ter_akum_income_last_month
    
    @api.depends('income_reguler_ter_ids.amount','ter_akum_income_last_month_non_natura','ter_tunj_pjk_terhutang_reguler_non_natura')
    def _amount_ter_akum_income_reguler_non_natura(self):
        for res in self:
            total = 0
            for rec in res.income_reguler_ter_ids:
                if not rec.category_on_natura_tax_id:
                    total += rec.amount
            if res.ter_tunj_pjk_terhutang_reguler_non_natura > 0:
                ter_tunj_pjk_terhutang_reguler_non_natura = res.ter_tunj_pjk_terhutang_reguler_non_natura
            else:
                ter_tunj_pjk_terhutang_reguler_non_natura = 0
            res.ter_akum_income_reguler_non_natura = total + ter_tunj_pjk_terhutang_reguler_non_natura + res.ter_akum_income_last_month_non_natura
    
    @api.depends('income_reguler_ter_ids.amount','ter_akum_income_last_month_gross')
    def _amount_ter_akum_income_reguler_gross(self):
        for res in self:
            total = 0
            for rec in res.income_reguler_ter_ids:
                total += rec.amount
            res.ter_akum_income_reguler_gross = total + res.ter_akum_income_last_month_gross
    
    @api.depends('income_reguler_ter_ids.amount','ter_akum_income_last_month_gross_non_natura')
    def _amount_ter_akum_income_reguler_gross_non_natura(self):
        for res in self:
            total = 0
            for rec in res.income_reguler_ter_ids:
                if not rec.category_on_natura_tax_id:
                    total += rec.amount
            res.ter_akum_income_reguler_gross_non_natura = total + res.ter_akum_income_last_month_gross_non_natura
    
    @api.depends('income_irreguler_ter_ids.amount','ter_akum_irreguler_last_month','ter_tunj_pjk_terhutang_irreguler')
    def _amount_ter_akum_income_irreguler(self):
        for res in self:
            total = 0
            for rec in res.income_irreguler_ter_ids:
                total += rec.amount
            if res.ter_tunj_pjk_terhutang_irreguler > 0:
                ter_tunj_pjk_terhutang_irreguler = res.ter_tunj_pjk_terhutang_irreguler
            else:
                ter_tunj_pjk_terhutang_irreguler = 0
            res.ter_akum_income_irreguler = total + ter_tunj_pjk_terhutang_irreguler + res.ter_akum_irreguler_last_month
    
    @api.depends('income_irreguler_ter_ids.amount','ter_akum_irreguler_last_month_non_natura','ter_tunj_pjk_terhutang_irreguler_non_natura')
    def _amount_ter_akum_income_irreguler_non_natura(self):
        for res in self:
            total = 0
            for rec in res.income_irreguler_ter_ids:
                if not rec.category_on_natura_tax_id:
                    total += rec.amount
            if res.ter_tunj_pjk_terhutang_irreguler_non_natura > 0:
                ter_tunj_pjk_terhutang_irreguler_non_natura = res.ter_tunj_pjk_terhutang_irreguler_non_natura
            else:
                ter_tunj_pjk_terhutang_irreguler_non_natura = 0
            res.ter_akum_income_irreguler_non_natura = total + ter_tunj_pjk_terhutang_irreguler_non_natura + res.ter_akum_irreguler_last_month_non_natura
    
    @api.depends('income_irreguler_ter_ids.amount','ter_akum_irreguler_last_month_gross')
    def _amount_ter_akum_income_irreguler_gross(self):
        for res in self:
            total = 0
            for rec in res.income_irreguler_ter_ids:
                total += rec.amount
            res.ter_akum_income_irreguler_gross = total + res.ter_akum_irreguler_last_month_gross
    
    @api.depends('income_irreguler_ter_ids.amount','ter_akum_irreguler_last_month_gross_non_natura')
    def _amount_ter_akum_income_irreguler_gross_non_natura(self):
        for res in self:
            total = 0
            for rec in res.income_irreguler_ter_ids:
                if not rec.category_on_natura_tax_id:
                    total += rec.amount
            res.ter_akum_income_irreguler_gross_non_natura = total + res.ter_akum_irreguler_last_month_gross_non_natura
    
    @api.depends('ter_akum_income_reguler', 'ter_akum_income_irreguler')
    def _amount_ter_bruto(self):
        for res in self:
            res.ter_bruto = res.ter_akum_income_reguler + res.ter_akum_income_irreguler
    
    @api.depends('ter_akum_income_reguler_non_natura', 'ter_akum_income_irreguler_non_natura')
    def _amount_ter_bruto_non_natura(self):
        for res in self:
            res.ter_bruto_non_natura = res.ter_akum_income_reguler_non_natura + res.ter_akum_income_irreguler_non_natura
    
    @api.depends('ter_akum_income_reguler_gross', 'ter_akum_income_irreguler_gross')
    def _amount_ter_bruto_gross(self):
        for res in self:
            res.ter_bruto_gross = res.ter_akum_income_reguler_gross + res.ter_akum_income_irreguler_gross
    
    @api.depends('ter_akum_income_reguler_gross_non_natura', 'ter_akum_income_irreguler_gross_non_natura')
    def _amount_ter_bruto_gross_non_natura(self):
        for res in self:
            res.ter_bruto_gross_non_natura = res.ter_akum_income_reguler_gross_non_natura + res.ter_akum_income_irreguler_gross_non_natura
    
    @api.depends('employee_id', 'year', 'date_of_joining','ter_akum_thn_reguler')
    def compute_ter_neto_masa_sebelumnya(self):
        for res in self:
            check_bukti_potong = self.env['hr.bukti.potong'].sudo().search([('employee_id','=',res.employee_id.id),('tahun_pajak','=',res.year)], limit=1)
            if check_bukti_potong and res.date_of_joining:
                if check_bukti_potong.spt_type_code == "1721_A1":
                    if check_bukti_potong.imported_date > res.date_of_joining and check_bukti_potong.imported_date >= res.date_from and check_bukti_potong.imported_date <= res.date_to or check_bukti_potong.imported_date > res.date_of_joining and check_bukti_potong.imported_date <= res.date_from:
                        res.ter_neto_masa_sebelumnya = check_bukti_potong.jumlah_14
                    elif check_bukti_potong.imported_date < res.date_of_joining and res.date_of_joining >= res.date_from and res.date_of_joining <= res.date_to or check_bukti_potong.imported_date < res.date_of_joining and res.date_of_joining <= res.date_from:
                        res.ter_neto_masa_sebelumnya = check_bukti_potong.jumlah_14
                    else:
                        res.ter_neto_masa_sebelumnya = 0.0
                elif check_bukti_potong.spt_type_code == "1721_A2":
                    if check_bukti_potong.imported_date > res.date_of_joining and check_bukti_potong.imported_date >= res.date_from and check_bukti_potong.imported_date <= res.date_to or check_bukti_potong.imported_date > res.date_of_joining and check_bukti_potong.imported_date <= res.date_from:
                        res.ter_neto_masa_sebelumnya = check_bukti_potong.jumlah_17
                    elif check_bukti_potong.imported_date < res.date_of_joining and res.date_of_joining >= res.date_from and res.date_of_joining <= res.date_to or check_bukti_potong.imported_date < res.date_of_joining and res.date_of_joining <= res.date_from:
                        res.ter_neto_masa_sebelumnya = check_bukti_potong.jumlah_17
                    else:
                        res.ter_neto_masa_sebelumnya = 0.0
                else:
                    res.ter_neto_masa_sebelumnya = 0.0
            else:
                res.ter_neto_masa_sebelumnya = 0.0
    
    @api.depends('employee_id', 'year', 'date_of_joining','ter_akum_thn_reguler_non_natura')
    def compute_ter_neto_masa_sebelumnya_non_natura(self):
        for res in self:
            check_bukti_potong = self.env['hr.bukti.potong'].sudo().search([('employee_id','=',res.employee_id.id),('tahun_pajak','=',res.year)], limit=1)
            if check_bukti_potong and res.date_of_joining:
                if check_bukti_potong.spt_type_code == "1721_A1":
                    if check_bukti_potong.imported_date > res.date_of_joining and check_bukti_potong.imported_date >= res.date_from and check_bukti_potong.imported_date <= res.date_to or check_bukti_potong.imported_date > res.date_of_joining and check_bukti_potong.imported_date <= res.date_from:
                        res.ter_neto_masa_sebelumnya_non_natura = check_bukti_potong.jumlah_14
                    elif check_bukti_potong.imported_date < res.date_of_joining and res.date_of_joining >= res.date_from and res.date_of_joining <= res.date_to or check_bukti_potong.imported_date < res.date_of_joining and res.date_of_joining <= res.date_from:
                        res.ter_neto_masa_sebelumnya_non_natura = check_bukti_potong.jumlah_14
                    else:
                        res.ter_neto_masa_sebelumnya_non_natura = 0.0
                elif check_bukti_potong.spt_type_code == "1721_A2":
                    if check_bukti_potong.imported_date > res.date_of_joining and check_bukti_potong.imported_date >= res.date_from and check_bukti_potong.imported_date <= res.date_to or check_bukti_potong.imported_date > res.date_of_joining and check_bukti_potong.imported_date <= res.date_from:
                        res.ter_neto_masa_sebelumnya_non_natura = check_bukti_potong.jumlah_17
                    elif check_bukti_potong.imported_date < res.date_of_joining and res.date_of_joining >= res.date_from and res.date_of_joining <= res.date_to or check_bukti_potong.imported_date < res.date_of_joining and res.date_of_joining <= res.date_from:
                        res.ter_neto_masa_sebelumnya_non_natura = check_bukti_potong.jumlah_17
                    else:
                        res.ter_neto_masa_sebelumnya_non_natura = 0.0
                else:
                    res.ter_neto_masa_sebelumnya_non_natura = 0.0
            else:
                res.ter_neto_masa_sebelumnya_non_natura = 0.0
    
    @api.depends('employee_id', 'year', 'date_of_joining','ter_akum_thn_reguler_gross')
    def compute_ter_neto_masa_sebelumnya_gross(self):
        for res in self:
            check_bukti_potong = self.env['hr.bukti.potong'].sudo().search([('employee_id','=',res.employee_id.id),('tahun_pajak','=',res.year)], limit=1)
            if check_bukti_potong and res.date_of_joining:
                if check_bukti_potong.spt_type_code == "1721_A1":
                    if check_bukti_potong.imported_date > res.date_of_joining and check_bukti_potong.imported_date >= res.date_from and check_bukti_potong.imported_date <= res.date_to or check_bukti_potong.imported_date > res.date_of_joining and check_bukti_potong.imported_date <= res.date_from:
                        res.ter_neto_masa_sebelumnya_gross = check_bukti_potong.jumlah_14
                    elif check_bukti_potong.imported_date < res.date_of_joining and res.date_of_joining >= res.date_from and res.date_of_joining <= res.date_to or check_bukti_potong.imported_date < res.date_of_joining and res.date_of_joining <= res.date_from:
                        res.ter_neto_masa_sebelumnya_gross = check_bukti_potong.jumlah_14
                    else:
                        res.ter_neto_masa_sebelumnya_gross = 0.0
                elif check_bukti_potong.spt_type_code == "1721_A2":
                    if check_bukti_potong.imported_date > res.date_of_joining and check_bukti_potong.imported_date >= res.date_from and check_bukti_potong.imported_date <= res.date_to or check_bukti_potong.imported_date > res.date_of_joining and check_bukti_potong.imported_date <= res.date_from:
                        res.ter_neto_masa_sebelumnya_gross = check_bukti_potong.jumlah_17
                    elif check_bukti_potong.imported_date < res.date_of_joining and res.date_of_joining >= res.date_from and res.date_of_joining <= res.date_to or check_bukti_potong.imported_date < res.date_of_joining and res.date_of_joining <= res.date_from:
                        res.ter_neto_masa_sebelumnya_gross = check_bukti_potong.jumlah_17
                    else:
                        res.ter_neto_masa_sebelumnya_gross = 0.0
                else:
                    res.ter_neto_masa_sebelumnya_gross = 0.0
            else:
                res.ter_neto_masa_sebelumnya_gross = 0.0
    
    @api.depends('employee_id', 'year', 'date_of_joining','ter_akum_thn_reguler_gross_non_natura')
    def compute_ter_neto_masa_sebelumnya_gross_non_natura(self):
        for res in self:
            check_bukti_potong = self.env['hr.bukti.potong'].sudo().search([('employee_id','=',res.employee_id.id),('tahun_pajak','=',res.year)], limit=1)
            if check_bukti_potong and res.date_of_joining:
                if check_bukti_potong.spt_type_code == "1721_A1":
                    if check_bukti_potong.imported_date > res.date_of_joining and check_bukti_potong.imported_date >= res.date_from and check_bukti_potong.imported_date <= res.date_to or check_bukti_potong.imported_date > res.date_of_joining and check_bukti_potong.imported_date <= res.date_from:
                        res.ter_neto_masa_sebelumnya_gross_non_natura = check_bukti_potong.jumlah_14
                    elif check_bukti_potong.imported_date < res.date_of_joining and res.date_of_joining >= res.date_from and res.date_of_joining <= res.date_to or check_bukti_potong.imported_date < res.date_of_joining and res.date_of_joining <= res.date_from:
                        res.ter_neto_masa_sebelumnya_gross_non_natura = check_bukti_potong.jumlah_14
                    else:
                        res.ter_neto_masa_sebelumnya_gross_non_natura = 0.0
                elif check_bukti_potong.spt_type_code == "1721_A2":
                    if check_bukti_potong.imported_date > res.date_of_joining and check_bukti_potong.imported_date >= res.date_from and check_bukti_potong.imported_date <= res.date_to or check_bukti_potong.imported_date > res.date_of_joining and check_bukti_potong.imported_date <= res.date_from:
                        res.ter_neto_masa_sebelumnya_gross_non_natura = check_bukti_potong.jumlah_17
                    elif check_bukti_potong.imported_date < res.date_of_joining and res.date_of_joining >= res.date_from and res.date_of_joining <= res.date_to or check_bukti_potong.imported_date < res.date_of_joining and res.date_of_joining <= res.date_from:
                        res.ter_neto_masa_sebelumnya_gross_non_natura = check_bukti_potong.jumlah_17
                    else:
                        res.ter_neto_masa_sebelumnya_gross_non_natura = 0.0
                else:
                    res.ter_neto_masa_sebelumnya_gross_non_natura = 0.0
            else:
                res.ter_neto_masa_sebelumnya_gross_non_natura = 0.0
    
    @api.depends('deduction_ter_ids.amount','ter_akum_ded_last_month')
    def _amount_ter_akum_ded(self):
        for res in self:
            total = 0
            for rec in res.deduction_ter_ids:
                total += rec.amount
            res.ter_akum_ded = total + res.ter_akum_ded_last_month
    
    @api.depends('deduction_ter_ids.amount','ter_akum_ded_last_month_non_natura')
    def _amount_ter_akum_ded_non_natura(self):
        for res in self:
            total = 0
            for rec in res.deduction_ter_ids:
                if not rec.category_on_natura_tax_id:
                    total += rec.amount
            res.ter_akum_ded_non_natura = total + res.ter_akum_ded_last_month_non_natura
    
    @api.depends('deduction_ter_ids.amount','ter_akum_ded_last_month_gross')
    def _amount_ter_akum_ded_gross(self):
        for res in self:
            total = 0
            for rec in res.deduction_ter_ids:
                total += rec.amount
            res.ter_akum_ded_gross = total + res.ter_akum_ded_last_month_gross
    
    @api.depends('deduction_ter_ids.amount','ter_akum_ded_last_month_gross_non_natura')
    def _amount_ter_akum_ded_gross_non_natura(self):
        for res in self:
            total = 0
            for rec in res.deduction_ter_ids:
                if not rec.category_on_natura_tax_id:
                    total += rec.amount
            res.ter_akum_ded_gross_non_natura = total + res.ter_akum_ded_last_month_gross_non_natura
    
    @api.depends('ter_akum_ded')
    def _amount_ter_akum_ded_thn(self):
        for res in self:
            total = 0.0
            if res.employee_id.employee_tax_status == 'pegawai_tetap':
                if res.tax_period_length and res.tax_end_month:
                    total = (res.ter_akum_ded * res.tax_end_month) / res.tax_period_length
                    res.ter_akum_ded_thn = total
                else:
                    res.ter_akum_ded_thn = total
            else:
                res.ter_akum_ded_thn = total
    
    @api.depends('ter_akum_ded_non_natura')
    def _amount_ter_akum_ded_thn_non_natura(self):
        for res in self:
            total = 0.0
            if res.employee_id.employee_tax_status == 'pegawai_tetap':
                if res.tax_period_length and res.tax_end_month:
                    total = (res.ter_akum_ded_non_natura * res.tax_end_month) / res.tax_period_length
                    res.ter_akum_ded_thn_non_natura = total
                else:
                    res.ter_akum_ded_thn_non_natura = total
            else:
                res.ter_akum_ded_thn_non_natura = total
    
    @api.depends('ter_akum_ded_gross')
    def _amount_ter_akum_ded_thn_gross(self):
        for res in self:
            total = 0.0
            if res.employee_id.employee_tax_status == 'pegawai_tetap':
                if res.tax_period_length and res.tax_end_month:
                    total = (res.ter_akum_ded_gross * res.tax_end_month) / res.tax_period_length
                    res.ter_akum_ded_thn_gross = total
                else:
                    res.ter_akum_ded_thn_gross = total
            else:
                res.ter_akum_ded_thn_gross = total
    
    @api.depends('ter_akum_ded_gross_non_natura')
    def _amount_ter_akum_ded_thn_gross_non_natura(self):
        for res in self:
            total = 0.0
            if res.employee_id.employee_tax_status == 'pegawai_tetap':
                if res.tax_period_length and res.tax_end_month:
                    total = (res.ter_akum_ded_gross_non_natura * res.tax_end_month) / res.tax_period_length
                    res.ter_akum_ded_thn_gross_non_natura = total
                else:
                    res.ter_akum_ded_thn_gross_non_natura = total
            else:
                res.ter_akum_ded_thn_gross_non_natura = total
    
    @api.depends('ter_akum_income_reguler')
    def _amount_ter_biaya_jab_month(self):
        for res in self:
            tax_setting = self.env['hr.tax.setting'].sudo().search([], limit=1)
            job_cost_rate = tax_setting.job_cost_rate
            max_job_cost_rate_monthly = tax_setting.max_job_cost_rate_monthly
            if res.employee_id.employee_tax_status == 'pegawai_tetap':
                if (((job_cost_rate/100) * res.ter_akum_income_reguler) > max_job_cost_rate_monthly):
                    total = max_job_cost_rate_monthly
                else:
                    total = ((job_cost_rate/100) * res.ter_akum_income_reguler)
                res.ter_biaya_jab_month = round(total)
            else:
                res.ter_biaya_jab_month = 0.0
    
    @api.depends('ter_akum_income_reguler_non_natura')
    def _amount_ter_biaya_jab_month_non_natura(self):
        for res in self:
            tax_setting = self.env['hr.tax.setting'].sudo().search([], limit=1)
            job_cost_rate = tax_setting.job_cost_rate
            max_job_cost_rate_monthly = tax_setting.max_job_cost_rate_monthly
            if res.employee_id.employee_tax_status == 'pegawai_tetap':
                if (((job_cost_rate/100) * res.ter_akum_income_reguler_non_natura) > max_job_cost_rate_monthly):
                    total = max_job_cost_rate_monthly
                else:
                    total = ((job_cost_rate/100) * res.ter_akum_income_reguler_non_natura)
                res.ter_biaya_jab_month_non_natura = round(total)
            else:
                res.ter_biaya_jab_month_non_natura = 0.0
    
    @api.depends('ter_akum_income_reguler_gross')
    def _amount_ter_biaya_jab_month_gross(self):
        for res in self:
            tax_setting = self.env['hr.tax.setting'].sudo().search([], limit=1)
            job_cost_rate = tax_setting.job_cost_rate
            max_job_cost_rate_monthly = tax_setting.max_job_cost_rate_monthly
            if res.employee_id.employee_tax_status == 'pegawai_tetap':
                if (((job_cost_rate/100) * res.ter_akum_income_reguler_gross) > max_job_cost_rate_monthly):
                    total = max_job_cost_rate_monthly
                else:
                    total = ((job_cost_rate/100) * res.ter_akum_income_reguler_gross)
                res.ter_biaya_jab_month_gross = round(total)
            else:
                res.ter_biaya_jab_month_gross = 0.0
    
    @api.depends('ter_akum_income_reguler_gross_non_natura')
    def _amount_ter_biaya_jab_month_gross_non_natura(self):
        for res in self:
            tax_setting = self.env['hr.tax.setting'].sudo().search([], limit=1)
            job_cost_rate = tax_setting.job_cost_rate
            max_job_cost_rate_monthly = tax_setting.max_job_cost_rate_monthly
            if res.employee_id.employee_tax_status == 'pegawai_tetap':
                if (((job_cost_rate/100) * res.ter_akum_income_reguler_gross_non_natura) > max_job_cost_rate_monthly):
                    total = max_job_cost_rate_monthly
                else:
                    total = ((job_cost_rate/100) * res.ter_akum_income_reguler_gross_non_natura)
                res.ter_biaya_jab_month_gross_non_natura = round(total)
            else:
                res.ter_biaya_jab_month_gross_non_natura = 0.0
    
    @api.depends('ter_akum_thn_reguler','tax_end_month')
    def _amount_ter_biaya_jab_reguler(self):
        for res in self:
            tax_setting = self.env['hr.tax.setting'].sudo().search([], limit=1)
            job_cost_rate = tax_setting.job_cost_rate
            max_job_cost_rate_monthly = tax_setting.max_job_cost_rate_monthly
            if res.employee_id.employee_tax_status == 'pegawai_tetap':
                if (((job_cost_rate/100) * res.ter_akum_thn_reguler) > (max_job_cost_rate_monthly * res.tax_end_month)):
                    total = (max_job_cost_rate_monthly * res.tax_end_month)
                else:
                    total = ((job_cost_rate/100) * res.ter_akum_thn_reguler)
                res.ter_biaya_jab_reguler = round(total)
            else:
                res.ter_biaya_jab_reguler = 0.0
    
    @api.depends('ter_akum_thn_reguler_non_natura','tax_end_month')
    def _amount_ter_biaya_jab_reguler_non_natura(self):
        for res in self:
            tax_setting = self.env['hr.tax.setting'].sudo().search([], limit=1)
            job_cost_rate = tax_setting.job_cost_rate
            max_job_cost_rate_monthly = tax_setting.max_job_cost_rate_monthly
            if res.employee_id.employee_tax_status == 'pegawai_tetap':
                if (((job_cost_rate/100) * res.ter_akum_thn_reguler_non_natura) > (max_job_cost_rate_monthly * res.tax_end_month)):
                    total = (max_job_cost_rate_monthly * res.tax_end_month)
                else:
                    total = ((job_cost_rate/100) * res.ter_akum_thn_reguler_non_natura)
                res.ter_biaya_jab_reguler_non_natura = round(total)
            else:
                res.ter_biaya_jab_reguler_non_natura = 0.0
    
    @api.depends('ter_akum_thn_reguler_gross','tax_end_month')
    def _amount_ter_biaya_jab_reguler_gross(self):
        for res in self:
            tax_setting = self.env['hr.tax.setting'].sudo().search([], limit=1)
            job_cost_rate = tax_setting.job_cost_rate
            max_job_cost_rate_monthly = tax_setting.max_job_cost_rate_monthly
            if res.employee_id.employee_tax_status == 'pegawai_tetap':
                if (((job_cost_rate/100) * res.ter_akum_thn_reguler_gross) > (max_job_cost_rate_monthly * res.tax_end_month)):
                    total = (max_job_cost_rate_monthly * res.tax_end_month)
                else:
                    total = ((job_cost_rate/100) * res.ter_akum_thn_reguler_gross)
                res.ter_biaya_jab_reguler_gross = round(total)
            else:
                res.ter_biaya_jab_reguler_gross = 0.0
    
    @api.depends('ter_akum_thn_reguler_gross_non_natura','tax_end_month')
    def _amount_ter_biaya_jab_reguler_gross_non_natura(self):
        for res in self:
            tax_setting = self.env['hr.tax.setting'].sudo().search([], limit=1)
            job_cost_rate = tax_setting.job_cost_rate
            max_job_cost_rate_monthly = tax_setting.max_job_cost_rate_monthly
            if res.employee_id.employee_tax_status == 'pegawai_tetap':
                if (((job_cost_rate/100) * res.ter_akum_thn_reguler_gross_non_natura) > (max_job_cost_rate_monthly * res.tax_end_month)):
                    total = (max_job_cost_rate_monthly * res.tax_end_month)
                else:
                    total = ((job_cost_rate/100) * res.ter_akum_thn_reguler_gross_non_natura)
                res.ter_biaya_jab_reguler_gross_non_natura = round(total)
            else:
                res.ter_biaya_jab_reguler_gross_non_natura = 0.0
    
    @api.depends('ter_akum_thn_reguler','ter_akum_income_irreguler','ter_biaya_jab_reguler','tax_end_month')
    def _amount_ter_biaya_jab_irreguler(self):
        for res in self:
            tax_setting = self.env['hr.tax.setting'].sudo().search([], limit=1)
            job_cost_rate = tax_setting.job_cost_rate
            max_job_cost_rate_monthly = tax_setting.max_job_cost_rate_monthly
            if res.employee_id.employee_tax_status == 'pegawai_tetap':
                if res.ter_akum_income_irreguler == 0:
                    total = 0
                elif (((job_cost_rate/100) * (res.ter_akum_thn_reguler + res.ter_akum_income_irreguler)) > (max_job_cost_rate_monthly * res.tax_end_month)):
                    total = (max_job_cost_rate_monthly * res.tax_end_month) - res.ter_biaya_jab_reguler
                else:
                    total = ((job_cost_rate/100) * (res.ter_akum_thn_reguler + res.ter_akum_income_irreguler)) - res.ter_biaya_jab_reguler
                res.ter_biaya_jab_irreguler = round(total)
            else:
                res.ter_biaya_jab_irreguler = 0.0
    
    @api.depends('ter_akum_thn_reguler_non_natura','ter_akum_income_irreguler_non_natura','ter_biaya_jab_reguler_non_natura','tax_end_month')
    def _amount_ter_biaya_jab_irreguler_non_natura(self):
        for res in self:
            tax_setting = self.env['hr.tax.setting'].sudo().search([], limit=1)
            job_cost_rate = tax_setting.job_cost_rate
            max_job_cost_rate_monthly = tax_setting.max_job_cost_rate_monthly
            if res.employee_id.employee_tax_status == 'pegawai_tetap':
                if res.ter_akum_income_irreguler_non_natura == 0:
                    total = 0
                elif (((job_cost_rate/100) * (res.ter_akum_thn_reguler_non_natura + res.ter_akum_income_irreguler_non_natura)) > (max_job_cost_rate_monthly * res.tax_end_month)):
                    total = (max_job_cost_rate_monthly * res.tax_end_month) - res.ter_biaya_jab_reguler_non_natura
                else:
                    total = ((job_cost_rate/100) * (res.ter_akum_thn_reguler_non_natura + res.ter_akum_income_irreguler_non_natura)) - res.ter_biaya_jab_reguler_non_natura
                res.ter_biaya_jab_irreguler_non_natura = round(total)
            else:
                res.ter_biaya_jab_irreguler_non_natura = 0.0
    
    @api.depends('ter_akum_thn_reguler_gross','ter_akum_income_irreguler_gross','ter_biaya_jab_reguler_gross','tax_end_month')
    def _amount_ter_biaya_jab_irreguler_gross(self):
        for res in self:
            tax_setting = self.env['hr.tax.setting'].sudo().search([], limit=1)
            job_cost_rate = tax_setting.job_cost_rate
            max_job_cost_rate_monthly = tax_setting.max_job_cost_rate_monthly
            if res.employee_id.employee_tax_status == 'pegawai_tetap':
                if res.ter_akum_income_irreguler_gross == 0:
                    total = 0
                elif (((job_cost_rate/100) * (res.ter_akum_thn_reguler_gross + res.ter_akum_income_irreguler_gross)) > (max_job_cost_rate_monthly * res.tax_end_month)):
                    total = (max_job_cost_rate_monthly * res.tax_end_month) - res.ter_biaya_jab_reguler_gross
                else:
                    total = ((job_cost_rate/100) * (res.ter_akum_thn_reguler_gross + res.ter_akum_income_irreguler_gross)) - res.ter_biaya_jab_reguler_gross
                res.ter_biaya_jab_irreguler_gross = round(total)
            else:
                res.ter_biaya_jab_irreguler_gross = 0.0
    
    @api.depends('ter_akum_thn_reguler_gross_non_natura','ter_akum_income_irreguler_gross_non_natura','ter_biaya_jab_reguler_gross_non_natura','tax_end_month')
    def _amount_ter_biaya_jab_irreguler_gross_non_natura(self):
        for res in self:
            tax_setting = self.env['hr.tax.setting'].sudo().search([], limit=1)
            job_cost_rate = tax_setting.job_cost_rate
            max_job_cost_rate_monthly = tax_setting.max_job_cost_rate_monthly
            if res.employee_id.employee_tax_status == 'pegawai_tetap':
                if res.ter_akum_income_irreguler_gross_non_natura == 0:
                    total = 0
                elif (((job_cost_rate/100) * (res.ter_akum_thn_reguler_gross_non_natura + res.ter_akum_income_irreguler_gross_non_natura)) > (max_job_cost_rate_monthly * res.tax_end_month)):
                    total = (max_job_cost_rate_monthly * res.tax_end_month) - res.ter_biaya_jab_reguler_gross_non_natura
                else:
                    total = ((job_cost_rate/100) * (res.ter_akum_thn_reguler_gross_non_natura + res.ter_akum_income_irreguler_gross_non_natura)) - res.ter_biaya_jab_reguler_gross_non_natura
                res.ter_biaya_jab_irreguler_gross_non_natura = round(total)
            else:
                res.ter_biaya_jab_irreguler_gross_non_natura = 0.0
    
    @api.depends('ter_biaya_jab_reguler','ter_akum_ded_thn')
    def _amount_ter_total_peng_reguler(self):
        for res in self:
            total = (res.ter_biaya_jab_reguler + res.ter_akum_ded_thn)
            res.ter_total_peng_reguler = round(total)
    
    @api.depends('ter_biaya_jab_reguler_non_natura','ter_akum_ded_thn_non_natura')
    def _amount_ter_total_peng_reguler_non_natura(self):
        for res in self:
            total = (res.ter_biaya_jab_reguler_non_natura + res.ter_akum_ded_thn_non_natura)
            res.ter_total_peng_reguler_non_natura = round(total)

    @api.depends('ter_biaya_jab_reguler_gross','ter_akum_ded_thn_gross')
    def _amount_ter_total_peng_reguler_gross(self):
        for res in self:
            total = (res.ter_biaya_jab_reguler_gross + res.ter_akum_ded_thn_gross)
            res.ter_total_peng_reguler_gross = round(total)
    
    @api.depends('ter_biaya_jab_reguler_gross_non_natura','ter_akum_ded_thn_gross_non_natura')
    def _amount_ter_total_peng_reguler_gross_non_natura(self):
        for res in self:
            total = (res.ter_biaya_jab_reguler_gross_non_natura + res.ter_akum_ded_thn_gross_non_natura)
            res.ter_total_peng_reguler_gross_non_natura = round(total)
    
    @api.depends('ter_akum_income_irreguler','ter_biaya_jab_reguler','ter_biaya_jab_irreguler','ter_akum_ded_thn')
    def _amount_ter_total_peng_irreguler(self):
        for res in self:
            if res.ter_akum_income_irreguler == 0:
                res.ter_total_peng_irreguler = 0.0
            else:
                total = (res.ter_biaya_jab_reguler + res.ter_biaya_jab_irreguler + res.ter_akum_ded_thn)
                res.ter_total_peng_irreguler = round(total)
    
    @api.depends('ter_akum_income_irreguler_non_natura','ter_biaya_jab_reguler_non_natura','ter_biaya_jab_irreguler_non_natura','ter_akum_ded_thn_non_natura')
    def _amount_ter_total_peng_irreguler_non_natura(self):
        for res in self:
            if res.ter_akum_income_irreguler_non_natura == 0:
                res.ter_total_peng_irreguler_non_natura = 0.0
            else:
                total = (res.ter_biaya_jab_reguler_non_natura + res.ter_biaya_jab_irreguler_non_natura + res.ter_akum_ded_thn_non_natura)
                res.ter_total_peng_irreguler_non_natura = round(total)
    
    @api.depends('ter_akum_income_irreguler_gross','ter_biaya_jab_reguler_gross','ter_biaya_jab_irreguler_gross','ter_akum_ded_thn_gross')
    def _amount_ter_total_peng_irreguler_gross(self):
        for res in self:
            if res.ter_akum_income_irreguler_gross == 0:
                res.ter_total_peng_irreguler_gross = 0.0
            else:
                total = (res.ter_biaya_jab_reguler_gross + res.ter_biaya_jab_irreguler_gross + res.ter_akum_ded_thn_gross)
                res.ter_total_peng_irreguler_gross = round(total)
    
    @api.depends('ter_akum_income_irreguler_gross_non_natura','ter_biaya_jab_reguler_gross_non_natura','ter_biaya_jab_irreguler_gross_non_natura','ter_akum_ded_thn_gross_non_natura')
    def _amount_ter_total_peng_irreguler_gross_non_natura(self):
        for res in self:
            if res.ter_akum_income_irreguler_gross_non_natura == 0:
                res.ter_total_peng_irreguler_gross_non_natura = 0.0
            else:
                total = (res.ter_biaya_jab_reguler_gross_non_natura + res.ter_biaya_jab_irreguler_gross_non_natura + res.ter_akum_ded_thn_gross_non_natura)
                res.ter_total_peng_irreguler_gross_non_natura = round(total)
    
    @api.depends('ter_akum_income_reguler','tax_period_length','tax_end_month')
    def _amount_ter_akum_thn_reguler(self):
        for res in self:
            total = 0.0
            if res.tax_period_length and res.tax_end_month:
                total = (res.ter_akum_income_reguler * res.tax_end_month) / res.tax_period_length
                res.ter_akum_thn_reguler = total
            else:
                res.ter_akum_thn_reguler = total
    
    @api.depends('ter_akum_income_reguler_non_natura','tax_period_length','tax_end_month')
    def _amount_ter_akum_thn_reguler_non_natura(self):
        for res in self:
            total = 0.0
            if res.tax_period_length and res.tax_end_month:
                total = (res.ter_akum_income_reguler_non_natura * res.tax_end_month) / res.tax_period_length
                res.ter_akum_thn_reguler_non_natura = total
            else:
                res.ter_akum_thn_reguler_non_natura = total
    
    @api.depends('ter_akum_income_reguler_gross','tax_period_length','tax_end_month')
    def _amount_ter_akum_thn_reguler_gross(self):
        for res in self:
            total = 0.0
            if res.tax_period_length and res.tax_end_month:
                total = (res.ter_akum_income_reguler_gross * res.tax_end_month) / res.tax_period_length
                res.ter_akum_thn_reguler_gross = total
            else:
                res.ter_akum_thn_reguler_gross = total
    
    @api.depends('ter_akum_income_reguler_gross_non_natura','tax_period_length','tax_end_month')
    def _amount_ter_akum_thn_reguler_gross_non_natura(self):
        for res in self:
            total = 0.0
            if res.tax_period_length and res.tax_end_month:
                total = (res.ter_akum_income_reguler_gross_non_natura * res.tax_end_month) / res.tax_period_length
                res.ter_akum_thn_reguler_gross_non_natura = total
            else:
                res.ter_akum_thn_reguler_gross_non_natura = total
    
    @api.depends('ter_akum_thn_reguler','ter_total_peng_reguler','ter_neto_masa_sebelumnya')
    def _amount_ter_peng_thn_reguler(self):
        for res in self:
            total = (res.ter_akum_thn_reguler - res.ter_total_peng_reguler)
            if total < 0:
                total = 0
            total += res.ter_neto_masa_sebelumnya
            res.ter_peng_thn_reguler = total
    
    @api.depends('ter_akum_thn_reguler_non_natura','ter_total_peng_reguler_non_natura','ter_neto_masa_sebelumnya_non_natura')
    def _amount_ter_peng_thn_reguler_non_natura(self):
        for res in self:
            total = (res.ter_akum_thn_reguler_non_natura - res.ter_total_peng_reguler_non_natura)
            if total < 0:
                total = 0
            total += res.ter_neto_masa_sebelumnya_non_natura
            res.ter_peng_thn_reguler_non_natura = total
    
    @api.depends('ter_akum_thn_reguler_gross','ter_total_peng_reguler_gross','ter_neto_masa_sebelumnya_gross')
    def _amount_ter_peng_thn_reguler_gross(self):
        for res in self:
            total = (res.ter_akum_thn_reguler_gross - res.ter_total_peng_reguler_gross)
            if total < 0:
                total = 0
            total += res.ter_neto_masa_sebelumnya_gross
            res.ter_peng_thn_reguler_gross = total
    
    @api.depends('ter_akum_thn_reguler_gross_non_natura','ter_total_peng_reguler_gross_non_natura','ter_neto_masa_sebelumnya_gross_non_natura')
    def _amount_ter_peng_thn_reguler_gross_non_natura(self):
        for res in self:
            total = (res.ter_akum_thn_reguler_gross_non_natura - res.ter_total_peng_reguler_gross_non_natura)
            if total < 0:
                total = 0
            total += res.ter_neto_masa_sebelumnya_gross_non_natura
            res.ter_peng_thn_reguler_gross_non_natura = total
    
    @api.depends('ter_akum_thn_reguler', 'ter_akum_income_irreguler', 'ter_total_peng_irreguler')
    def _amount_ter_peng_thn_irreguler(self):
        for res in self:
            if res.ter_akum_income_irreguler == 0:
                res.ter_peng_thn_irreguler = 0.0
            else:
                res.ter_peng_thn_irreguler = (res.ter_akum_thn_reguler + res.ter_akum_income_irreguler) - res.ter_total_peng_irreguler

    @api.depends('ter_akum_thn_reguler_non_natura', 'ter_akum_income_irreguler_non_natura', 'ter_total_peng_irreguler_non_natura')
    def _amount_ter_peng_thn_irreguler_non_natura(self):
        for res in self:
            if res.ter_akum_income_irreguler_non_natura == 0:
                res.ter_peng_thn_irreguler_non_natura = 0.0
            else:
                res.ter_peng_thn_irreguler_non_natura = (res.ter_akum_thn_reguler_non_natura + res.ter_akum_income_irreguler_non_natura) - res.ter_total_peng_irreguler_non_natura

    @api.depends('ter_akum_thn_reguler_gross', 'ter_akum_income_irreguler_gross', 'ter_total_peng_irreguler_gross')
    def _amount_ter_peng_thn_irreguler_gross(self):
        for res in self:
            if res.ter_akum_income_irreguler_gross == 0:
                res.ter_peng_thn_irreguler_gross = 0.0
            else:
                res.ter_peng_thn_irreguler_gross = (res.ter_akum_thn_reguler_gross + res.ter_akum_income_irreguler_gross) - res.ter_total_peng_irreguler_gross
    
    @api.depends('ter_akum_thn_reguler_gross_non_natura', 'ter_akum_income_irreguler_gross_non_natura', 'ter_total_peng_irreguler_gross_non_natura')
    def _amount_ter_peng_thn_irreguler_gross_non_natura(self):
        for res in self:
            if res.ter_akum_income_irreguler_gross_non_natura == 0:
                res.ter_peng_thn_irreguler_gross_non_natura = 0.0
            else:
                res.ter_peng_thn_irreguler_gross_non_natura = (res.ter_akum_thn_reguler_gross_non_natura + res.ter_akum_income_irreguler_gross_non_natura) - res.ter_total_peng_irreguler_gross_non_natura

    @api.depends('ter_peng_thn_reguler', 'peng_ptkp')
    def _amount_ter_peng_kena_pjk_reguler(self):
        for res in self:
            if res.ter_peng_thn_reguler == 0:
                total = 0
            elif (res.ter_peng_thn_reguler - res.peng_ptkp) < 0:
                total = 0
            else:
                total = (res.ter_peng_thn_reguler - res.peng_ptkp)
            res.ter_peng_kena_pjk_reguler = self.round_down(total, -3)
    
    @api.depends('ter_peng_thn_reguler_non_natura', 'peng_ptkp')
    def _amount_ter_peng_kena_pjk_reguler_non_natura(self):
        for res in self:
            if res.ter_peng_thn_reguler_non_natura == 0:
                total = 0
            elif (res.ter_peng_thn_reguler_non_natura - res.peng_ptkp) < 0:
                total = 0
            else:
                total = (res.ter_peng_thn_reguler_non_natura - res.peng_ptkp)
            res.ter_peng_kena_pjk_reguler_non_natura = self.round_down(total, -3)
    
    @api.depends('ter_peng_thn_reguler_gross', 'peng_ptkp')
    def _amount_ter_peng_kena_pjk_reguler_gross(self):
        for res in self:
            if res.ter_peng_thn_reguler_gross == 0:
                total = 0
            elif (res.ter_peng_thn_reguler_gross - res.peng_ptkp) < 0:
                total = 0
            else:
                total = (res.ter_peng_thn_reguler_gross - res.peng_ptkp)
            res.ter_peng_kena_pjk_reguler_gross = self.round_down(total, -3)
    
    @api.depends('ter_peng_thn_reguler_gross_non_natura', 'peng_ptkp')
    def _amount_ter_peng_kena_pjk_reguler_gross_non_natura(self):
        for res in self:
            if res.ter_peng_thn_reguler_gross_non_natura == 0:
                total = 0
            elif (res.ter_peng_thn_reguler_gross_non_natura - res.peng_ptkp) < 0:
                total = 0
            else:
                total = (res.ter_peng_thn_reguler_gross_non_natura - res.peng_ptkp)
            res.ter_peng_kena_pjk_reguler_gross_non_natura = self.round_down(total, -3)
    
    @api.depends('ter_peng_thn_irreguler', 'peng_ptkp')
    def _amount_ter_peng_kena_pjk_irreguler(self):
        for res in self:
            if res.ter_peng_thn_irreguler == 0:
                total = 0
            elif (res.ter_peng_thn_irreguler - res.peng_ptkp) < 0:
                total = 0
            else:
                total = (res.ter_peng_thn_irreguler - res.peng_ptkp)
            res.ter_peng_kena_pjk_irreguler = self.round_down(total, -3)
    
    @api.depends('ter_peng_thn_irreguler_non_natura', 'peng_ptkp')
    def _amount_ter_peng_kena_pjk_irreguler_non_natura(self):
        for res in self:
            if res.ter_peng_thn_irreguler_non_natura == 0:
                total = 0
            elif (res.ter_peng_thn_irreguler_non_natura - res.peng_ptkp) < 0:
                total = 0
            else:
                total = (res.ter_peng_thn_irreguler_non_natura - res.peng_ptkp)
            res.ter_peng_kena_pjk_irreguler_non_natura = self.round_down(total, -3)
    
    @api.depends('ter_peng_thn_irreguler_gross', 'peng_ptkp')
    def _amount_ter_peng_kena_pjk_irreguler_gross(self):
        for res in self:
            if res.ter_peng_thn_irreguler_gross == 0:
                total = 0
            elif (res.ter_peng_thn_irreguler_gross - res.peng_ptkp) < 0:
                total = 0
            else:
                total = (res.ter_peng_thn_irreguler_gross - res.peng_ptkp)
            res.ter_peng_kena_pjk_irreguler_gross = self.round_down(total, -3)
    
    @api.depends('ter_peng_thn_irreguler_gross_non_natura', 'peng_ptkp')
    def _amount_ter_peng_kena_pjk_irreguler_gross_non_natura(self):
        for res in self:
            if res.ter_peng_thn_irreguler_gross_non_natura == 0:
                total = 0
            elif (res.ter_peng_thn_irreguler_gross_non_natura - res.peng_ptkp) < 0:
                total = 0
            else:
                total = (res.ter_peng_thn_irreguler_gross_non_natura - res.peng_ptkp)
            res.ter_peng_kena_pjk_irreguler_gross_non_natura = self.round_down(total, -3)
    
    def compute_ter_tax_bracket(self, pkp=0.0):
        amount = pkp
        amounts = amount
        total = 0
        tax_bracket = self.env['hr.tax.bracket'].sudo().search([])
        for tax in tax_bracket:
            tax_rate = tax.tax_rate / 100.00
            net = amounts - tax.taxable_income_to
            if net <= 0:
                total += amount * tax_rate
                break
            else:
                total += (tax.taxable_income_to - tax.taxable_income_from) * tax_rate
                amount = amount - (tax.taxable_income_to - tax.taxable_income_from)
        return total
    
    def compute_ter_pph_21_grossup(self):
        result = {
            "ter_tunj_pjk_reguler": 0.0,
            "ter_tunj_pjk_irreguler": 0.0,
        }
        tax_setting = self.env['hr.tax.setting'].sudo().search([], limit=1)
        job_cost_rate = tax_setting.job_cost_rate
        max_job_cost_rate_monthly = tax_setting.max_job_cost_rate_monthly

        ## calculation for reguler
        total_income_reguler = 0
        for rec in self.income_reguler_ter_ids:
            total_income_reguler += rec.amount
        if self.employee_id.is_expatriate and self.employee_id.expatriate_tax == "pph21":
            akum_thn = (total_income_reguler * 12)
        else:
            akum_thn = ((total_income_reguler + self.ter_akum_income_last_month) * self.tax_end_month) / self.tax_period_length
        if (((job_cost_rate/100) * akum_thn) > (max_job_cost_rate_monthly * self.tax_end_month)):
            biaya_jab_reg = (max_job_cost_rate_monthly * self.tax_end_month)
        else:
            biaya_jab_reg = ((job_cost_rate/100) * akum_thn)
        akum_ded_thn = (self.ter_akum_ded * self.tax_end_month) / self.tax_period_length
        total_peng_reguler = biaya_jab_reg + akum_ded_thn
        peng_thn_reguler = akum_thn - total_peng_reguler

        ## calculation for irreguler
        total_income_irreguler = 0
        for rec in self.income_irreguler_ter_ids:
            total_income_irreguler += rec.amount
        akum_irreguler = total_income_irreguler + self.ter_akum_irreguler_last_month
        if akum_irreguler == 0:
            biaya_jab_irreg = 0
        elif (((job_cost_rate/100) * (akum_thn + akum_irreguler)) > (max_job_cost_rate_monthly * self.tax_end_month)):
            biaya_jab_irreg = (max_job_cost_rate_monthly * self.tax_end_month) - biaya_jab_reg
        else:
            biaya_jab_irreg = ((job_cost_rate/100) * (akum_thn + akum_irreguler)) - biaya_jab_reg
        total_peng_irreguler = biaya_jab_reg + biaya_jab_irreg + akum_ded_thn
        peng_thn_irreguler = (akum_thn + akum_irreguler) - total_peng_irreguler

        peng_ptkp = self.ptkp_id.ptkp_amount

        ## calculation PKP Reguler
        peng_kena_pjk_reguler = peng_thn_reguler - peng_ptkp
        if peng_kena_pjk_reguler < 0:
            peng_kena_pjk_reguler = 0

        ## calculation PKP Irreguler
        peng_kena_pjk_irreguler = peng_thn_irreguler - peng_ptkp
        if peng_kena_pjk_irreguler < 0:
            peng_kena_pjk_irreguler = 0

        selisih_reg = 0.0
        iteration_reg = 0
        selisih_irreg = 0.0
        iteration_irreg = 0

        pjk_terhutang_reguler_last_month = (self.ter_pjk_terhutang_reguler_last_month * self.tax_end_month) / self.tax_period_length
        pjk_terhutang_irreguler_last_month = self.ter_pjk_terhutang_irreguler_last_month

        # non_npwp_tax_rate_setting = float(self.env['ir.config_parameter'].sudo().get_param('equip3_hr_payroll_extend_id.non_npwp_tax_rate'))
        # if non_npwp_tax_rate_setting > 0:
        #     non_npwp_tax_rate = non_npwp_tax_rate_setting
        # else:
        #     non_npwp_tax_rate = 0

        ### perhitungan disetahunkan reguler###
        if (selisih_reg == 0.0):
            # if self.npwp:
            #     tunjanganPphReguler = self.compute_ter_tax_bracket(peng_kena_pjk_reguler)
            # else:
            #     tunjanganPphReguler = (self.compute_ter_tax_bracket(peng_kena_pjk_reguler) * (non_npwp_tax_rate / 100)) + self.compute_ter_tax_bracket(peng_kena_pjk_reguler)
            tunjanganPphReguler = self.compute_ter_tax_bracket(peng_kena_pjk_reguler)
            bruto = akum_thn + tunjanganPphReguler
            if (((job_cost_rate/100) * bruto) > (max_job_cost_rate_monthly * self.tax_end_month)):
                biaya_jab_reg = (max_job_cost_rate_monthly * self.tax_end_month)
            else:
                biaya_jab_reg = ((job_cost_rate/100) * bruto)
            jabatan_reg = biaya_jab_reg
            neto = bruto - jabatan_reg - akum_ded_thn
            pkp = self.round_down(neto - peng_ptkp, -3)
            # if self.npwp:
            #     rulePph = self.compute_ter_tax_bracket(pkp) - pjk_terhutang_reguler_last_month
            # else:
            #     rulePph = (self.compute_ter_tax_bracket(pkp) * (non_npwp_tax_rate / 100)) + self.compute_ter_tax_bracket(pkp) - pjk_terhutang_reguler_last_month
            rulePph = self.compute_ter_tax_bracket(pkp) - pjk_terhutang_reguler_last_month
            selisih_reg = rulePph - tunjanganPphReguler

        while (selisih_reg != 0.0):
            if iteration_reg == 100:
                break
            if tunjanganPphReguler < 0:
                tunjanganPphReguler = 0
            tunjanganPphReguler = tunjanganPphReguler + selisih_reg
            bruto = akum_thn + tunjanganPphReguler
            if (((job_cost_rate/100) * bruto) > (max_job_cost_rate_monthly * self.tax_end_month)):
                biaya_jab_reg = (max_job_cost_rate_monthly * self.tax_end_month)
            else:
                biaya_jab_reg = ((job_cost_rate/100) * bruto)
            if biaya_jab_reg < 0:
                jabatan_reg = 0
            else:
                jabatan_reg = biaya_jab_reg
            neto = bruto - jabatan_reg - akum_ded_thn
            pkp = self.round_down(neto - peng_ptkp, -3)
            # if self.npwp:
            #     rulePph = self.compute_ter_tax_bracket(pkp) - pjk_terhutang_reguler_last_month
            # else:
            #     rulePph = (self.compute_ter_tax_bracket(pkp) * (non_npwp_tax_rate / 100)) + self.compute_ter_tax_bracket(pkp) - pjk_terhutang_reguler_last_month
            rulePph = self.compute_ter_tax_bracket(pkp) - pjk_terhutang_reguler_last_month
            if rulePph < 0:
                rulePph = 0
            selisih_reg = rulePph - tunjanganPphReguler
            iteration_reg = iteration_reg + 1

        ### perhitungan disetahunkan irreguler###
        if (selisih_irreg == 0.0):
            # if self.npwp:
            #     tunjanganPphIrreguler = self.compute_ter_tax_bracket(peng_kena_pjk_irreguler)
            # else:
            #     tunjanganPphIrreguler = (self.compute_ter_tax_bracket(peng_kena_pjk_irreguler) * (non_npwp_tax_rate / 100)) + self.compute_ter_tax_bracket(peng_kena_pjk_irreguler)
            tunjanganPphIrreguler = self.compute_ter_tax_bracket(peng_kena_pjk_irreguler)
            bruto_irreg = akum_irreguler + tunjanganPphIrreguler

            if akum_irreguler == 0:
                biaya_jab_irreg = 0
            elif (((job_cost_rate/100) * (bruto + bruto_irreg)) > (max_job_cost_rate_monthly * self.tax_end_month)):
                biaya_jab_irreg = (max_job_cost_rate_monthly * self.tax_end_month) - jabatan_reg
            else:
                biaya_jab_irreg = ((job_cost_rate/100) * (bruto + bruto_irreg)) - jabatan_reg

            jabatan_irreg = biaya_jab_irreg
            neto_irreg = (bruto + bruto_irreg) - (jabatan_reg + jabatan_irreg + akum_ded_thn)
            pkp_irreg = self.round_down(neto_irreg - peng_ptkp, -3)
            # if self.npwp:
            #     rulePphIrreg = self.compute_ter_tax_bracket(pkp_irreg) - rulePph - pjk_terhutang_reguler_last_month - pjk_terhutang_irreguler_last_month
            # else:
            #     rulePphIrreg = (self.compute_ter_tax_bracket(pkp_irreg) * (non_npwp_tax_rate / 100)) + self.compute_ter_tax_bracket(pkp_irreg) - rulePph - pjk_terhutang_reguler_last_month - pjk_terhutang_irreguler_last_month
            rulePphIrreg = self.compute_ter_tax_bracket(pkp_irreg) - rulePph - pjk_terhutang_reguler_last_month - pjk_terhutang_irreguler_last_month
            selisih_irreg = rulePphIrreg - round(tunjanganPphIrreguler)

        while (selisih_irreg != 0.0):
            if iteration_irreg == 100:
                break
            if tunjanganPphIrreguler < 0:
                tunjanganPphIrreguler = 0
            tunjanganPphIrreguler = tunjanganPphIrreguler + selisih_irreg
            bruto_irreg = akum_irreguler + tunjanganPphIrreguler

            if akum_irreguler == 0:
                biaya_jab_irreg = 0
            elif (((job_cost_rate/100) * (bruto + bruto_irreg)) > (max_job_cost_rate_monthly * self.tax_end_month)):
                biaya_jab_irreg = (max_job_cost_rate_monthly * self.tax_end_month) - jabatan_reg
            else:
                biaya_jab_irreg = ((job_cost_rate/100) * (bruto + bruto_irreg)) - jabatan_reg

            jabatan_irreg = biaya_jab_irreg
            neto_irreg = (bruto + bruto_irreg) - (jabatan_reg + jabatan_irreg + akum_ded_thn)
            pkp_irreg = self.round_down(neto_irreg - peng_ptkp, -3)
            # if self.npwp:
            #     rulePphIrreg = self.compute_ter_tax_bracket(pkp_irreg)
            # else:
            #     rulePphIrreg = (self.compute_ter_tax_bracket(pkp_irreg) * (non_npwp_tax_rate / 100)) + self.compute_ter_tax_bracket(pkp_irreg)
            rulePphIrreg = self.compute_ter_tax_bracket(pkp_irreg)
            PphIrreg = rulePphIrreg - rulePph - pjk_terhutang_reguler_last_month - pjk_terhutang_irreguler_last_month
            if PphIrreg < 0:
                PphIrreg = 0
            selisih_irreg = PphIrreg - round(tunjanganPphIrreguler)
            iteration_irreg = iteration_irreg + 1

        if self.employee_id.is_expatriate and self.employee_id.expatriate_tax == "pph21":
            result["ter_tunj_pjk_reguler"] = (tunjanganPphReguler / 12)
        else:
            result["ter_tunj_pjk_reguler"] = (tunjanganPphReguler / self.tax_end_month) * self.tax_period_length
        result["ter_tunj_pjk_irreguler"] = round(tunjanganPphIrreguler)

        return result
    
    def compute_ter_pph_21_grossup_non_natura(self):
        result = {
            "ter_tunj_pjk_reguler_non_natura": 0.0,
            "ter_tunj_pjk_irreguler_non_natura": 0.0,
        }
        tax_setting = self.env['hr.tax.setting'].sudo().search([], limit=1)
        job_cost_rate = tax_setting.job_cost_rate
        max_job_cost_rate_monthly = tax_setting.max_job_cost_rate_monthly

        ## calculation for reguler
        total_income_reguler = 0
        for rec in self.income_reguler_ter_ids:
            if not rec.category_on_natura_tax_id:
                total_income_reguler += rec.amount
        if self.employee_id.is_expatriate and self.employee_id.expatriate_tax == "pph21":
            akum_thn = (total_income_reguler * 12)
        else:
            akum_thn = ((total_income_reguler + self.ter_akum_income_last_month_non_natura) * self.tax_end_month) / self.tax_period_length
        if (((job_cost_rate/100) * akum_thn) > (max_job_cost_rate_monthly * self.tax_end_month)):
            biaya_jab_reg = (max_job_cost_rate_monthly * self.tax_end_month)
        else:
            biaya_jab_reg = ((job_cost_rate/100) * akum_thn)
        akum_ded_thn = (self.ter_akum_ded_non_natura * self.tax_end_month) / self.tax_period_length
        total_peng_reguler = biaya_jab_reg + akum_ded_thn
        peng_thn_reguler = akum_thn - total_peng_reguler

        ## calculation for irreguler
        total_income_irreguler = 0
        for rec in self.income_irreguler_ter_ids:
            if not rec.category_on_natura_tax_id:
                total_income_irreguler += rec.amount
        akum_irreguler = total_income_irreguler + self.ter_akum_irreguler_last_month_non_natura
        if akum_irreguler == 0:
            biaya_jab_irreg = 0
        elif (((job_cost_rate/100) * (akum_thn + akum_irreguler)) > (max_job_cost_rate_monthly * self.tax_end_month)):
            biaya_jab_irreg = (max_job_cost_rate_monthly * self.tax_end_month) - biaya_jab_reg
        else:
            biaya_jab_irreg = ((job_cost_rate/100) * (akum_thn + akum_irreguler)) - biaya_jab_reg
        total_peng_irreguler = biaya_jab_reg + biaya_jab_irreg + akum_ded_thn
        peng_thn_irreguler = (akum_thn + akum_irreguler) - total_peng_irreguler

        peng_ptkp = self.ptkp_id.ptkp_amount

        ## calculation PKP Reguler
        peng_kena_pjk_reguler = peng_thn_reguler - peng_ptkp
        if peng_kena_pjk_reguler < 0:
            peng_kena_pjk_reguler = 0

        ## calculation PKP Irreguler
        peng_kena_pjk_irreguler = peng_thn_irreguler - peng_ptkp
        if peng_kena_pjk_irreguler < 0:
            peng_kena_pjk_irreguler = 0

        selisih_reg = 0.0
        iteration_reg = 0
        selisih_irreg = 0.0
        iteration_irreg = 0

        pjk_terhutang_reguler_last_month = (self.ter_pjk_terhutang_reguler_last_month_non_natura * self.tax_end_month) / self.tax_period_length
        pjk_terhutang_irreguler_last_month = self.ter_pjk_terhutang_irreguler_last_month_non_natura

        ### perhitungan disetahunkan reguler###
        if (selisih_reg == 0.0):
            tunjanganPphReguler = self.compute_ter_tax_bracket(peng_kena_pjk_reguler)
            bruto = akum_thn + tunjanganPphReguler
            if (((job_cost_rate/100) * bruto) > (max_job_cost_rate_monthly * self.tax_end_month)):
                biaya_jab_reg = (max_job_cost_rate_monthly * self.tax_end_month)
            else:
                biaya_jab_reg = ((job_cost_rate/100) * bruto)
            jabatan_reg = biaya_jab_reg
            neto = bruto - jabatan_reg - akum_ded_thn
            pkp = self.round_down(neto - peng_ptkp, -3)
            rulePph = self.compute_ter_tax_bracket(pkp) - pjk_terhutang_reguler_last_month
            selisih_reg = rulePph - tunjanganPphReguler

        while (selisih_reg != 0.0):
            if iteration_reg == 100:
                break
            if tunjanganPphReguler < 0:
                tunjanganPphReguler = 0
            tunjanganPphReguler = tunjanganPphReguler + selisih_reg
            bruto = akum_thn + tunjanganPphReguler
            if (((job_cost_rate/100) * bruto) > (max_job_cost_rate_monthly * self.tax_end_month)):
                biaya_jab_reg = (max_job_cost_rate_monthly * self.tax_end_month)
            else:
                biaya_jab_reg = ((job_cost_rate/100) * bruto)
            if biaya_jab_reg < 0:
                jabatan_reg = 0
            else:
                jabatan_reg = biaya_jab_reg
            neto = bruto - jabatan_reg - akum_ded_thn
            pkp = self.round_down(neto - peng_ptkp, -3)
            rulePph = self.compute_ter_tax_bracket(pkp) - pjk_terhutang_reguler_last_month
            if rulePph < 0:
                rulePph = 0
            selisih_reg = rulePph - tunjanganPphReguler
            iteration_reg = iteration_reg + 1

        ### perhitungan disetahunkan irreguler###
        if (selisih_irreg == 0.0):
            tunjanganPphIrreguler = self.compute_ter_tax_bracket(peng_kena_pjk_irreguler)
            bruto_irreg = akum_irreguler + tunjanganPphIrreguler

            if akum_irreguler == 0:
                biaya_jab_irreg = 0
            elif (((job_cost_rate/100) * (bruto + bruto_irreg)) > (max_job_cost_rate_monthly * self.tax_end_month)):
                biaya_jab_irreg = (max_job_cost_rate_monthly * self.tax_end_month) - jabatan_reg
            else:
                biaya_jab_irreg = ((job_cost_rate/100) * (bruto + bruto_irreg)) - jabatan_reg

            jabatan_irreg = biaya_jab_irreg
            neto_irreg = (bruto + bruto_irreg) - (jabatan_reg + jabatan_irreg + akum_ded_thn)
            pkp_irreg = self.round_down(neto_irreg - peng_ptkp, -3)
            rulePphIrreg = self.compute_ter_tax_bracket(pkp_irreg) - rulePph - pjk_terhutang_reguler_last_month - pjk_terhutang_irreguler_last_month
            selisih_irreg = rulePphIrreg - round(tunjanganPphIrreguler)

        while (selisih_irreg != 0.0):
            if iteration_irreg == 100:
                break
            if tunjanganPphIrreguler < 0:
                tunjanganPphIrreguler = 0
            tunjanganPphIrreguler = tunjanganPphIrreguler + selisih_irreg
            bruto_irreg = akum_irreguler + tunjanganPphIrreguler

            if akum_irreguler == 0:
                biaya_jab_irreg = 0
            elif (((job_cost_rate/100) * (bruto + bruto_irreg)) > (max_job_cost_rate_monthly * self.tax_end_month)):
                biaya_jab_irreg = (max_job_cost_rate_monthly * self.tax_end_month) - jabatan_reg
            else:
                biaya_jab_irreg = ((job_cost_rate/100) * (bruto + bruto_irreg)) - jabatan_reg

            jabatan_irreg = biaya_jab_irreg
            neto_irreg = (bruto + bruto_irreg) - (jabatan_reg + jabatan_irreg + akum_ded_thn)
            pkp_irreg = self.round_down(neto_irreg - peng_ptkp, -3)
            rulePphIrreg = self.compute_ter_tax_bracket(pkp_irreg)
            PphIrreg = rulePphIrreg - rulePph - pjk_terhutang_reguler_last_month - pjk_terhutang_irreguler_last_month
            if PphIrreg < 0:
                PphIrreg = 0
            selisih_irreg = PphIrreg - round(tunjanganPphIrreguler)
            iteration_irreg = iteration_irreg + 1

        if self.employee_id.is_expatriate and self.employee_id.expatriate_tax == "pph21":
            result["ter_tunj_pjk_reguler_non_natura"] = (tunjanganPphReguler / 12)
        else:
            result["ter_tunj_pjk_reguler_non_natura"] = (tunjanganPphReguler / self.tax_end_month) * self.tax_period_length
        result["ter_tunj_pjk_irreguler_non_natura"] = round(tunjanganPphIrreguler)

        return result
    
    @api.depends('ter_peng_kena_pjk_reguler')
    def _amount_ter_pjk_thn_reguler(self):
        for res in self:
            # if res.npwp:
            #     res.ter_pjk_thn_reguler = round(self.compute_ter_tax_bracket(res.ter_peng_kena_pjk_reguler))
            # else:
            #     non_npwp_tax_rate_setting = float(self.env['ir.config_parameter'].sudo().get_param('equip3_hr_payroll_extend_id.non_npwp_tax_rate'))
            #     if non_npwp_tax_rate_setting > 0:
            #         non_npwp_tax_rate = non_npwp_tax_rate_setting
            #     else:
            #         non_npwp_tax_rate = 0
            #     res.ter_pjk_thn_reguler = round(self.compute_ter_tax_bracket(res.ter_peng_kena_pjk_reguler)) + (round(self.compute_ter_tax_bracket(res.ter_peng_kena_pjk_reguler)) * (non_npwp_tax_rate / 100))
            res.ter_pjk_thn_reguler = round(self.compute_ter_tax_bracket(res.ter_peng_kena_pjk_reguler))
    
    @api.depends('ter_peng_kena_pjk_reguler_non_natura')
    def _amount_ter_pjk_thn_reguler_non_natura(self):
        for res in self:
            res.ter_pjk_thn_reguler_non_natura = round(self.compute_ter_tax_bracket(res.ter_peng_kena_pjk_reguler_non_natura))
    
    @api.depends('ter_peng_kena_pjk_reguler_gross')
    def _amount_ter_pjk_thn_reguler_gross(self):
        for res in self:
            res.ter_pjk_thn_reguler_gross = round(self.compute_ter_tax_bracket(res.ter_peng_kena_pjk_reguler_gross))
    
    @api.depends('ter_peng_kena_pjk_reguler_gross_non_natura')
    def _amount_ter_pjk_thn_reguler_gross_non_natura(self):
        for res in self:
            res.ter_pjk_thn_reguler_gross_non_natura = round(self.compute_ter_tax_bracket(res.ter_peng_kena_pjk_reguler_gross_non_natura))
    
    @api.depends('ter_peng_kena_pjk_irreguler')
    def _amount_ter_pjk_thn_irreguler(self):
        for res in self:
            if res.ter_akum_income_irreguler == 0:
                res.ter_pjk_thn_irreguler = 0
            else:
                # if res.npwp:
                #     res.ter_pjk_thn_irreguler = round(self.compute_ter_tax_bracket(res.ter_peng_kena_pjk_irreguler))
                # else:
                #     non_npwp_tax_rate_setting = float(self.env['ir.config_parameter'].sudo().get_param('equip3_hr_payroll_extend_id.non_npwp_tax_rate'))
                #     if non_npwp_tax_rate_setting > 0:
                #         non_npwp_tax_rate = non_npwp_tax_rate_setting
                #     else:
                #         non_npwp_tax_rate = 0
                #     res.ter_pjk_thn_irreguler = round(self.compute_ter_tax_bracket(res.ter_peng_kena_pjk_irreguler)) + (round(self.compute_ter_tax_bracket(res.ter_peng_kena_pjk_irreguler)) * (non_npwp_tax_rate / 100))
                res.ter_pjk_thn_irreguler = round(self.compute_ter_tax_bracket(res.ter_peng_kena_pjk_irreguler))
    
    @api.depends('ter_peng_kena_pjk_irreguler_non_natura')
    def _amount_ter_pjk_thn_irreguler_non_natura(self):
        for res in self:
            if res.ter_akum_income_irreguler_non_natura == 0:
                res.ter_pjk_thn_irreguler_non_natura = 0
            else:
                res.ter_pjk_thn_irreguler_non_natura = round(self.compute_ter_tax_bracket(res.ter_peng_kena_pjk_irreguler_non_natura))
    
    @api.depends('ter_peng_kena_pjk_irreguler_gross')
    def _amount_ter_pjk_thn_irreguler_gross(self):
        for res in self:
            if res.ter_akum_income_irreguler_gross == 0:
                res.ter_pjk_thn_irreguler_gross = 0
            else:
                res.ter_pjk_thn_irreguler_gross = round(self.compute_ter_tax_bracket(res.ter_peng_kena_pjk_irreguler_gross))
    
    @api.depends('ter_peng_kena_pjk_irreguler_gross_non_natura')
    def _amount_ter_pjk_thn_irreguler_gross_non_natura(self):
        for res in self:
            if res.ter_akum_income_irreguler_gross_non_natura == 0:
                res.ter_pjk_thn_irreguler_gross_non_natura = 0
            else:
                res.ter_pjk_thn_irreguler_gross_non_natura = round(self.compute_ter_tax_bracket(res.ter_peng_kena_pjk_irreguler_gross_non_natura))
    
    @api.depends('ter_pjk_thn_reguler')
    def _amount_ter_pjk_terhutang_reguler(self):
        for res in self:
            if res.employee_id.employee_tax_status == 'pegawai_tetap':
                total = (res.ter_pjk_thn_reguler / res.tax_end_month) * res.tax_period_length
                res.ter_pjk_terhutang_reguler = math.ceil(total)
            else:
                res.ter_pjk_terhutang_reguler = 0.0
    
    @api.depends('ter_pjk_thn_reguler_non_natura')
    def _amount_ter_pjk_terhutang_reguler_non_natura(self):
        for res in self:
            if res.employee_id.employee_tax_status == 'pegawai_tetap':
                total = (res.ter_pjk_thn_reguler_non_natura / res.tax_end_month) * res.tax_period_length
                res.ter_pjk_terhutang_reguler_non_natura = math.ceil(total)
            else:
                res.ter_pjk_terhutang_reguler_non_natura = 0.0
    
    @api.depends('ter_pjk_thn_reguler_gross')
    def _amount_ter_pjk_terhutang_reguler_gross(self):
        for res in self:
            if res.employee_id.employee_tax_status == 'pegawai_tetap':
                total = (res.ter_pjk_thn_reguler_gross / res.tax_end_month) * res.tax_period_length
                res.ter_pjk_terhutang_reguler_gross = math.ceil(total)
            else:
                res.ter_pjk_terhutang_reguler_gross = 0.0
    
    @api.depends('ter_pjk_thn_reguler_gross_non_natura')
    def _amount_ter_pjk_terhutang_reguler_gross_non_natura(self):
        for res in self:
            if res.employee_id.employee_tax_status == 'pegawai_tetap':
                total = (res.ter_pjk_thn_reguler_gross_non_natura / res.tax_end_month) * res.tax_period_length
                res.ter_pjk_terhutang_reguler_gross_non_natura = math.ceil(total)
            else:
                res.ter_pjk_terhutang_reguler_gross_non_natura = 0.0
    
    @api.depends('ter_pjk_thn_irreguler')
    def _amount_ter_pjk_terhutang_irreguler(self):
        for res in self:
            if res.ter_pjk_thn_irreguler == 0:
                total = 0.0
            else:
                total = res.ter_pjk_thn_irreguler - res.ter_pjk_thn_reguler
            res.ter_pjk_terhutang_irreguler = math.ceil(total)
    
    @api.depends('ter_pjk_thn_irreguler_non_natura')
    def _amount_ter_pjk_terhutang_irreguler_non_natura(self):
        for res in self:
            if res.ter_pjk_thn_irreguler_non_natura == 0:
                total = 0.0
            else:
                total = res.ter_pjk_thn_irreguler_non_natura - res.ter_pjk_thn_reguler_non_natura
            res.ter_pjk_terhutang_irreguler_non_natura = math.ceil(total)
    
    @api.depends('ter_pjk_thn_irreguler_gross')
    def _amount_ter_pjk_terhutang_irreguler_gross(self):
        for res in self:
            if res.ter_pjk_thn_irreguler_gross == 0:
                total = 0.0
            else:
                total = res.ter_pjk_thn_irreguler_gross - res.ter_pjk_thn_reguler_gross
            res.ter_pjk_terhutang_irreguler_gross = math.ceil(total)
    
    @api.depends('ter_pjk_thn_irreguler_gross_non_natura')
    def _amount_ter_pjk_terhutang_irreguler_gross_non_natura(self):
        for res in self:
            if res.ter_pjk_thn_irreguler_gross_non_natura == 0:
                total = 0.0
            else:
                total = res.ter_pjk_thn_irreguler_gross_non_natura - res.ter_pjk_thn_reguler_gross_non_natura
            res.ter_pjk_terhutang_irreguler_gross_non_natura = math.ceil(total)
    
    @api.depends('income_reguler_ter_ids.amount','income_irreguler_ter_ids.amount','ptkp_id','ter_tunj_pjk_bln')
    def _amount_ter_pjk_bln(self):
        for res in self:
            if res.tax_period_length == res.tax_end_month:
                res.ter_pjk_bln = (res.ter_pjk_terhutang_reguler + res.ter_pjk_terhutang_irreguler) - res.ter_pph21_paid
            else:
                total_income_reguler = 0
                for rec in res.income_reguler_ter_ids:
                    total_income_reguler += rec.amount
                total_income_irreguler = 0
                for rec in res.income_irreguler_ter_ids:
                    total_income_irreguler += rec.amount
                bruto = total_income_reguler + total_income_irreguler + res.ter_tunj_pjk_bln
                ter_category = self.env['hr.ter.category'].search([('ptkp_ids','in',[res.ptkp_id.id]),('bruto_income_from','<=',bruto),('bruto_income_to','>=',bruto)],limit=1)
                if ter_category:
                    # if res.npwp:
                    #     res.ter_pjk_bln = bruto * (ter_category.ter_rate / 100)
                    # else:
                    #     non_npwp_tax_rate_setting = float(self.env['ir.config_parameter'].sudo().get_param('equip3_hr_payroll_extend_id.non_npwp_tax_rate'))
                    #     if non_npwp_tax_rate_setting > 0:
                    #         non_npwp_tax_rate = non_npwp_tax_rate_setting
                    #     else:
                    #         non_npwp_tax_rate = 0
                    #     res.ter_pjk_bln = (bruto * (ter_category.ter_rate / 100) * (non_npwp_tax_rate / 100)) + (bruto * (ter_category.ter_rate / 100))
                    res.ter_pjk_bln = bruto * (ter_category.ter_rate / 100)
                else:
                    res.ter_pjk_bln = 0
    
    @api.depends('income_reguler_ter_ids.amount','income_irreguler_ter_ids.amount','ptkp_id','ter_tunj_pjk_bln_non_natura')
    def _amount_ter_pjk_bln_non_natura(self):
        for res in self:
            if res.tax_period_length == res.tax_end_month:
                res.ter_pjk_bln_non_natura = (res.ter_pjk_terhutang_reguler_non_natura + res.ter_pjk_terhutang_irreguler_non_natura) - res.ter_pph21_paid_non_natura
            else:
                total_income_reguler = 0
                for rec in res.income_reguler_ter_ids:
                    if not rec.category_on_natura_tax_id:
                        total_income_reguler += rec.amount
                total_income_irreguler = 0
                for rec in res.income_irreguler_ter_ids:
                    if not rec.category_on_natura_tax_id:
                        total_income_irreguler += rec.amount
                bruto = total_income_reguler + total_income_irreguler + res.ter_tunj_pjk_bln_non_natura
                ter_category = self.env['hr.ter.category'].search([('ptkp_ids','in',[res.ptkp_id.id]),('bruto_income_from','<=',bruto),('bruto_income_to','>=',bruto)],limit=1)
                if ter_category:
                    res.ter_pjk_bln_non_natura = bruto * (ter_category.ter_rate / 100)
                else:
                    res.ter_pjk_bln_non_natura = 0
    
    @api.depends('income_reguler_ter_ids.amount','income_irreguler_ter_ids.amount','ptkp_id')
    def _amount_ter_pjk_bln_gross(self):
        for res in self:
            if res.tax_period_length == res.tax_end_month:
                res.ter_pjk_bln_gross = (res.ter_pjk_terhutang_reguler_gross + res.ter_pjk_terhutang_irreguler_gross) - res.ter_pph21_paid_gross
            else:
                total_income_reguler = 0
                for rec in res.income_reguler_ter_ids:
                    total_income_reguler += rec.amount
                total_income_irreguler = 0
                for rec in res.income_irreguler_ter_ids:
                    total_income_irreguler += rec.amount
                bruto = total_income_reguler + total_income_irreguler
                ter_category = self.env['hr.ter.category'].search([('ptkp_ids','in',[res.ptkp_id.id]),('bruto_income_from','<=',bruto),('bruto_income_to','>=',bruto)],limit=1)
                if ter_category:
                    res.ter_pjk_bln_gross = bruto * (ter_category.ter_rate / 100)
                else:
                    res.ter_pjk_bln_gross = 0
    
    @api.depends('income_reguler_ter_ids.amount','income_irreguler_ter_ids.amount','ptkp_id')
    def _amount_ter_pjk_bln_gross_non_natura(self):
        for res in self:
            if res.tax_period_length == res.tax_end_month:
                res.ter_pjk_bln_gross_non_natura = (res.ter_pjk_terhutang_reguler_gross_non_natura + res.ter_pjk_terhutang_irreguler_gross_non_natura) - res.ter_pph21_paid_gross_non_natura
            else:
                total_income_reguler = 0
                for rec in res.income_reguler_ter_ids:
                    if not rec.category_on_natura_tax_id:
                        total_income_reguler += rec.amount
                total_income_irreguler = 0
                for rec in res.income_irreguler_ter_ids:
                    if not rec.category_on_natura_tax_id:
                        total_income_irreguler += rec.amount
                bruto = total_income_reguler + total_income_irreguler
                ter_category = self.env['hr.ter.category'].search([('ptkp_ids','in',[res.ptkp_id.id]),('bruto_income_from','<=',bruto),('bruto_income_to','>=',bruto)],limit=1)
                if ter_category:
                    res.ter_pjk_bln_gross_non_natura = bruto * (ter_category.ter_rate / 100)
                else:
                    res.ter_pjk_bln_gross_non_natura = 0
    
    @api.depends('ter_pjk_bln')
    def _amount_ter_pph21_paid(self):
        for res in self:
            # get value from last month
            date_period = res.date_from
            if res.payslip_period_id.start_period_based_on == 'start_date':
                date_period = res.date_from
            elif res.payslip_period_id.start_period_based_on == 'end_date':
                date_period = res.date_to
            previous_month_date = datetime.strptime(str(date_period), '%Y-%m-%d') - relativedelta(months=1)
            previous_month = previous_month_date.strftime("%B")

            if res.employee_id and previous_month:
                self.env.cr.execute(
                    ''' select ter_pph21_paid from hr_payslip WHERE employee_id = %s and month_name = '%s' AND year = '%s' and state not in ('refund','cancel') ORDER BY id DESC LIMIT 1 ''' % (
                        res.employee_id.id, previous_month, res.year))
                last_payslip = self.env.cr.dictfetchall()
                if last_payslip and res.employee_id.employee_tax_status == 'pegawai_tetap' and not res.employee_id.is_expatriate:
                    ter_pph21_paid_last_month = last_payslip[0].get('ter_pph21_paid') if last_payslip[0].get('ter_pph21_paid') else 0
                    if res.tax_period_length == res.tax_end_month:
                        ter_pph21_paid = ter_pph21_paid_last_month
                    else:
                        ter_pph21_paid = ter_pph21_paid_last_month + res.ter_pjk_bln
                    res.ter_pph21_paid = ter_pph21_paid
                else:
                    res.ter_pph21_paid = res.ter_pjk_bln
    
    @api.depends('ter_pjk_bln_non_natura')
    def _amount_ter_pph21_paid_non_natura(self):
        for res in self:
            # get value from last month
            date_period = res.date_from
            if res.payslip_period_id.start_period_based_on == 'start_date':
                date_period = res.date_from
            elif res.payslip_period_id.start_period_based_on == 'end_date':
                date_period = res.date_to
            previous_month_date = datetime.strptime(str(date_period), '%Y-%m-%d') - relativedelta(months=1)
            previous_month = previous_month_date.strftime("%B")

            if res.employee_id and previous_month:
                self.env.cr.execute(
                    ''' select ter_pph21_paid_non_natura from hr_payslip WHERE employee_id = %s and month_name = '%s' AND year = '%s' and state not in ('refund','cancel') ORDER BY id DESC LIMIT 1 ''' % (
                        res.employee_id.id, previous_month, res.year))
                last_payslip = self.env.cr.dictfetchall()
                if last_payslip and res.employee_id.employee_tax_status == 'pegawai_tetap' and not res.employee_id.is_expatriate:
                    ter_pph21_paid_last_month_non_natura = last_payslip[0].get('ter_pph21_paid_non_natura') if last_payslip[0].get('ter_pph21_paid_non_natura') else 0
                    if res.tax_period_length == res.tax_end_month:
                        ter_pph21_paid_non_natura = ter_pph21_paid_last_month_non_natura
                    else:
                        ter_pph21_paid_non_natura = ter_pph21_paid_last_month_non_natura + res.ter_pjk_bln_non_natura
                    res.ter_pph21_paid_non_natura = ter_pph21_paid_non_natura
                else:
                    res.ter_pph21_paid_non_natura = res.ter_pjk_bln_non_natura
    
    @api.depends('ter_pjk_bln_gross')
    def _amount_ter_pph21_paid_gross(self):
        for res in self:
            # get value from last month
            date_period = res.date_from
            if res.payslip_period_id.start_period_based_on == 'start_date':
                date_period = res.date_from
            elif res.payslip_period_id.start_period_based_on == 'end_date':
                date_period = res.date_to
            previous_month_date = datetime.strptime(str(date_period), '%Y-%m-%d') - relativedelta(months=1)
            previous_month = previous_month_date.strftime("%B")

            if res.employee_id and previous_month:
                self.env.cr.execute(
                    ''' select ter_pph21_paid_gross from hr_payslip WHERE employee_id = %s and month_name = '%s' AND year = '%s' and state not in ('refund','cancel') ORDER BY id DESC LIMIT 1 ''' % (
                        res.employee_id.id, previous_month, res.year))
                last_payslip = self.env.cr.dictfetchall()
                if last_payslip and res.employee_id.employee_tax_status == 'pegawai_tetap' and not res.employee_id.is_expatriate:
                    ter_pph21_paid_gross_last_month = last_payslip[0].get('ter_pph21_paid_gross') if last_payslip[0].get('ter_pph21_paid_gross') else 0
                    if res.tax_period_length == res.tax_end_month:
                        ter_pph21_paid_gross = ter_pph21_paid_gross_last_month
                    else:
                        ter_pph21_paid_gross = ter_pph21_paid_gross_last_month + res.ter_pjk_bln_gross
                    res.ter_pph21_paid_gross = ter_pph21_paid_gross
                else:
                    res.ter_pph21_paid_gross = res.ter_pjk_bln_gross
    
    @api.depends('ter_pjk_bln_gross_non_natura')
    def _amount_ter_pph21_paid_gross_non_natura(self):
        for res in self:
            # get value from last month
            date_period = res.date_from
            if res.payslip_period_id.start_period_based_on == 'start_date':
                date_period = res.date_from
            elif res.payslip_period_id.start_period_based_on == 'end_date':
                date_period = res.date_to
            previous_month_date = datetime.strptime(str(date_period), '%Y-%m-%d') - relativedelta(months=1)
            previous_month = previous_month_date.strftime("%B")

            if res.employee_id and previous_month:
                self.env.cr.execute(
                    ''' select ter_pph21_paid_gross_non_natura from hr_payslip WHERE employee_id = %s and month_name = '%s' AND year = '%s' and state not in ('refund','cancel') ORDER BY id DESC LIMIT 1 ''' % (
                        res.employee_id.id, previous_month, res.year))
                last_payslip = self.env.cr.dictfetchall()
                if last_payslip and res.employee_id.employee_tax_status == 'pegawai_tetap' and not res.employee_id.is_expatriate:
                    ter_pph21_paid_gross_last_month_non_natura = last_payslip[0].get('ter_pph21_paid_gross_non_natura') if last_payslip[0].get('ter_pph21_paid_gross_non_natura') else 0
                    if res.tax_period_length == res.tax_end_month:
                        ter_pph21_paid_gross_non_natura = ter_pph21_paid_gross_last_month_non_natura
                    else:
                        ter_pph21_paid_gross_non_natura = ter_pph21_paid_gross_last_month_non_natura + res.ter_pjk_bln_gross_non_natura
                    res.ter_pph21_paid_gross_non_natura = ter_pph21_paid_gross_non_natura
                else:
                    res.ter_pph21_paid_gross_non_natura = res.ter_pjk_bln_gross_non_natura

    @api.depends('ter_pjk_terhutang_reguler','ter_pjk_terhutang_irreguler','ter_pph21_paid')
    def _amount_ter_diff(self):
        for res in self:
            if res.tax_period_length == res.tax_end_month:
                res.ter_diff = 0
            else:
                res.ter_diff = (res.ter_pjk_terhutang_reguler + res.ter_pjk_terhutang_irreguler) - res.ter_pph21_paid

    @api.depends('ter_pjk_terhutang_reguler_non_natura','ter_pjk_terhutang_irreguler_non_natura','ter_pph21_paid_non_natura')
    def _amount_ter_diff_non_natura(self):
        for res in self:
            if res.tax_period_length == res.tax_end_month:
                res.ter_diff_non_natura = 0
            else:
                res.ter_diff_non_natura = (res.ter_pjk_terhutang_reguler_non_natura + res.ter_pjk_terhutang_irreguler_non_natura) - res.ter_pph21_paid_non_natura

    @api.depends('ter_pjk_terhutang_reguler_gross','ter_pjk_terhutang_irreguler_gross','ter_pph21_paid_gross')
    def _amount_ter_diff_gross(self):
        for res in self:
            if res.tax_period_length == res.tax_end_month:
                res.ter_diff_gross = 0
            else:
                res.ter_diff_gross = (res.ter_pjk_terhutang_reguler_gross + res.ter_pjk_terhutang_irreguler_gross) - res.ter_pph21_paid_gross

    @api.depends('ter_pjk_terhutang_reguler_gross_non_natura','ter_pjk_terhutang_irreguler_gross_non_natura','ter_pph21_paid_gross_non_natura')
    def _amount_ter_diff_gross_non_natura(self):
        for res in self:
            if res.tax_period_length == res.tax_end_month:
                res.ter_diff_gross_non_natura = 0
            else:
                res.ter_diff_gross_non_natura = (res.ter_pjk_terhutang_reguler_gross_non_natura + res.ter_pjk_terhutang_irreguler_gross_non_natura) - res.ter_pph21_paid_gross_non_natura

    @api.depends('ter_pjk_bln','ter_pjk_bln_non_natura')
    def _amount_ter_pjk_natura(self):
        for res in self:
            res.ter_pjk_natura = res.ter_pjk_bln - res.ter_pjk_bln_non_natura
    
    @api.depends('ter_pjk_bln_gross','ter_pjk_bln_gross_non_natura')
    def _amount_ter_pjk_natura_gross(self):
        for res in self:
            res.ter_pjk_natura_gross = res.ter_pjk_bln_gross - res.ter_pjk_bln_gross_non_natura

    def compute_pph21_ter_bracket_calculation(self, pkp=0.0):
        amount = pkp
        amounts = amount
        total = 0
        pph21_bracket = []
        tax_bracket = self.env['hr.tax.bracket'].sudo().search([])
        for tax in tax_bracket:
            tax_rate = tax.tax_rate / 100.00
            net = amounts - tax.taxable_income_to
            if net <= 0:
                pkp_thn = amount
                total += pkp_thn * tax_rate
                input_data = {
                    'sequence': tax.sequence,
                    'name': tax.name,
                    'tax_able_income_from': tax.taxable_income_from,
                    'tax_able_income_to': tax.taxable_income_to,
                    'tax_rate': tax.tax_rate,
                    'tax_penalty_rate': tax.tax_penalty_rate,
                    'pkp_ter': round(pkp_thn),
                    'pph21_amount': round(total),
                }
                pph21_bracket += [input_data]
                break
            else:
                amount_diff = (tax.taxable_income_to - tax.taxable_income_from)
                pkp_thn = amount_diff
                total += (tax.taxable_income_to - tax.taxable_income_from) * tax_rate
                amount = amount - (tax.taxable_income_to - tax.taxable_income_from)
            input_data = {
                'sequence': tax.sequence,
                'name': tax.name,
                'tax_able_income_from': tax.taxable_income_from,
                'tax_able_income_to': tax.taxable_income_to,
                'tax_rate': tax.tax_rate,
                'tax_penalty_rate': tax.tax_penalty_rate,
                'pkp_ter': round(pkp_thn),
                'pph21_amount': round(total),
            }
            pph21_bracket += [input_data]
        return pph21_bracket
    
    @api.depends('ter_peng_kena_pjk_reguler')
    def compute_pph21_ter_reguler(self):
        for res in self:
            if res.payslip_pesangon == False:
                res.pph21_ter_reguler_ids = False
                if res.ter_peng_kena_pjk_reguler > 0:
                    pph21_ter_reguler = self.compute_pph21_ter_bracket_calculation(res.ter_peng_kena_pjk_reguler)
                    res.pph21_ter_reguler_ids = [(0, 0, x) for x in pph21_ter_reguler]
            else:
                res.pph21_ter_reguler_ids = False
    
    @api.depends('ter_peng_kena_pjk_reguler_non_natura')
    def compute_pph21_ter_reguler_non_natura(self):
        for res in self:
            if res.payslip_pesangon == False:
                res.pph21_ter_reguler_non_natura_ids = False
                if res.ter_peng_kena_pjk_reguler_non_natura > 0:
                    pph21_ter_reguler_non_natura = self.compute_pph21_ter_bracket_calculation(res.ter_peng_kena_pjk_reguler_non_natura)
                    res.pph21_ter_reguler_non_natura_ids = [(0, 0, x) for x in pph21_ter_reguler_non_natura]
            else:
                res.pph21_ter_reguler_non_natura_ids = False
    
    @api.depends('ter_peng_kena_pjk_reguler_gross')
    def compute_pph21_ter_reguler_gross(self):
        for res in self:
            if res.payslip_pesangon == False:
                res.pph21_ter_reguler_gross_ids = False
                if res.ter_peng_kena_pjk_reguler_gross > 0:
                    pph21_ter_reguler_gross = self.compute_pph21_ter_bracket_calculation(res.ter_peng_kena_pjk_reguler_gross)
                    res.pph21_ter_reguler_gross_ids = [(0, 0, x) for x in pph21_ter_reguler_gross]
            else:
                res.pph21_ter_reguler_gross_ids = False
    
    @api.depends('ter_peng_kena_pjk_reguler_gross_non_natura')
    def compute_pph21_ter_reguler_gross_non_natura(self):
        for res in self:
            if res.payslip_pesangon == False:
                res.pph21_ter_reguler_gross_non_natura_ids = False
                if res.ter_peng_kena_pjk_reguler_gross_non_natura > 0:
                    pph21_ter_reguler_gross_non_natura = self.compute_pph21_ter_bracket_calculation(res.ter_peng_kena_pjk_reguler_gross_non_natura)
                    res.pph21_ter_reguler_gross_non_natura_ids = [(0, 0, x) for x in pph21_ter_reguler_gross_non_natura]
            else:
                res.pph21_ter_reguler_gross_non_natura_ids = False
    
    @api.depends('ter_peng_kena_pjk_irreguler')
    def compute_pph21_ter_irreguler(self):
        for res in self:
            if res.payslip_pesangon == False:
                res.pph21_ter_irreguler_ids = False
                if res.ter_peng_kena_pjk_irreguler > 0:
                    pph21_ter_irreguler = self.compute_pph21_ter_bracket_calculation(res.ter_peng_kena_pjk_irreguler)
                    res.pph21_ter_irreguler_ids = [(0, 0, x) for x in pph21_ter_irreguler]
            else:
                res.pph21_ter_irreguler_ids = False
    
    @api.depends('ter_peng_kena_pjk_irreguler_non_natura')
    def compute_pph21_ter_irreguler_non_natura(self):
        for res in self:
            if res.payslip_pesangon == False:
                res.pph21_ter_irreguler_non_natura_ids = False
                if res.ter_peng_kena_pjk_irreguler_non_natura > 0:
                    pph21_ter_irreguler_non_natura = self.compute_pph21_ter_bracket_calculation(res.ter_peng_kena_pjk_irreguler_non_natura)
                    res.pph21_ter_irreguler_non_natura_ids = [(0, 0, x) for x in pph21_ter_irreguler_non_natura]
            else:
                res.pph21_ter_irreguler_non_natura_ids = False
    
    @api.depends('ter_peng_kena_pjk_irreguler_gross')
    def compute_pph21_ter_irreguler_gross(self):
        for res in self:
            if res.payslip_pesangon == False:
                res.pph21_ter_irreguler_gross_ids = False
                if res.ter_peng_kena_pjk_irreguler_gross > 0:
                    pph21_ter_irreguler_gross = self.compute_pph21_ter_bracket_calculation(res.ter_peng_kena_pjk_irreguler_gross)
                    res.pph21_ter_irreguler_gross_ids = [(0, 0, x) for x in pph21_ter_irreguler_gross]
            else:
                res.pph21_ter_irreguler_gross_ids = False
    
    @api.depends('ter_peng_kena_pjk_irreguler_gross_non_natura')
    def compute_pph21_ter_irreguler_gross_non_natura(self):
        for res in self:
            if res.payslip_pesangon == False:
                res.pph21_ter_irreguler_gross_non_natura_ids = False
                if res.ter_peng_kena_pjk_irreguler_gross_non_natura > 0:
                    pph21_ter_irreguler_gross_non_natura = self.compute_pph21_ter_bracket_calculation(res.ter_peng_kena_pjk_irreguler_gross_non_natura)
                    res.pph21_ter_irreguler_gross_non_natura_ids = [(0, 0, x) for x in pph21_ter_irreguler_gross_non_natura]
            else:
                res.pph21_ter_irreguler_gross_non_natura_ids = False
    
    def get_ter_category(self, bruto=0.0, ptkp=False):
        ter_cat_val = []
        if ptkp:
            bruto_val = bruto
            selisih = 0
            sequence = 1
            if (selisih == 0):
                ter_category = self.env['hr.ter.category'].search([('ptkp_ids','in',[ptkp.id]),('bruto_income_from','<=',bruto_val),('bruto_income_to','>=',bruto_val)],limit=1)
                pph21_ter = bruto_val * (ter_category.ter_rate / 100)
                selisih = bruto_val - pph21_ter
                input_data = {
                    'sequence': sequence,
                    'category': ter_category.category,
                    'ptkp_ids': ter_category.ptkp_ids.ids,
                    'bruto_income_from': ter_category.bruto_income_from,
                    'bruto_income_to': ter_category.bruto_income_to,
                    'ter_rate': ter_category.ter_rate,
                    'bruto': bruto_val,
                    'pph21_ter': pph21_ter,
                }
                ter_cat_val += [input_data]
                sequence += 1
                bruto_val = bruto + pph21_ter

            while float_compare(selisih, bruto, precision_digits=2) == -1:
                if float_compare(selisih, bruto, precision_digits=2) == 0:
                    break
                ter_category = self.env['hr.ter.category'].search([('ptkp_ids','in',[ptkp.id]),('bruto_income_from','<=',bruto_val),('bruto_income_to','>=',bruto_val)],limit=1)
                pph21_ter = bruto_val * (ter_category.ter_rate / 100)
                selisih = round(bruto_val - pph21_ter, 2)
                input_data = {
                    'sequence': sequence,
                    'category': ter_category.category,
                    'ptkp_ids': ter_category.ptkp_ids.ids,
                    'bruto_income_from': ter_category.bruto_income_from,
                    'bruto_income_to': ter_category.bruto_income_to,
                    'ter_rate': ter_category.ter_rate,
                    'bruto': bruto_val,
                    'pph21_ter': pph21_ter,
                }
                ter_cat_val += [input_data]
                sequence += 1
                bruto_val = bruto + pph21_ter
        return ter_cat_val

    def get_ter_category_gross(self, bruto=0.0, ptkp=False):
        ter_cat_val = []
        if ptkp:
            ter_category = self.env['hr.ter.category'].search([('ptkp_ids','in',[ptkp.id]),('bruto_income_from','<=',bruto),('bruto_income_to','>=',bruto)],limit=1)
            sequence = 1
            pph21_ter = bruto * (ter_category.ter_rate / 100)
            for cat in ter_category:
                input_data = {
                    'sequence': sequence,
                    'category': cat.category,
                    'ptkp_ids': cat.ptkp_ids.ids,
                    'bruto_income_from': cat.bruto_income_from,
                    'bruto_income_to': cat.bruto_income_to,
                    'ter_rate': cat.ter_rate,
                    'bruto': bruto,
                    'pph21_ter': pph21_ter,
                }
                ter_cat_val += [input_data]
                sequence += 1
        return ter_cat_val
    
    @api.depends('income_reguler_ter_ids.amount','income_irreguler_ter_ids.amount','ptkp_id')
    def compute_ter_category(self):
        for res in self:
            if res.ptkp:
                res.ter_category_ids = False
                total_income_reguler = 0
                for rec in res.income_reguler_ter_ids:
                    total_income_reguler += rec.amount
                total_income_irreguler = 0
                for rec in res.income_irreguler_ter_ids:
                    total_income_irreguler += rec.amount
                bruto = total_income_reguler + total_income_irreguler
                ter_category = self.get_ter_category(bruto,res.ptkp_id)
                res.ter_category_ids = [(0, 0, x) for x in ter_category]
            else:
                res.ter_category_ids = False
    
    @api.depends('income_reguler_ter_ids.amount','income_irreguler_ter_ids.amount','ptkp_id')
    def compute_ter_category_non_natura(self):
        for res in self:
            if res.ptkp:
                res.ter_category_non_natura_ids = False
                total_income_reguler = 0
                for rec in res.income_reguler_ter_ids:
                    if not rec.category_on_natura_tax_id:
                        total_income_reguler += rec.amount
                total_income_irreguler = 0
                for rec in res.income_irreguler_ter_ids:
                    if not rec.category_on_natura_tax_id:
                        total_income_irreguler += rec.amount
                bruto = total_income_reguler + total_income_irreguler
                ter_category = self.get_ter_category(bruto,res.ptkp_id)
                res.ter_category_non_natura_ids = [(0, 0, x) for x in ter_category]
            else:
                res.ter_category_non_natura_ids = False
    
    @api.depends('income_reguler_ter_ids.amount','income_irreguler_ter_ids.amount','ptkp_id')
    def compute_ter_category_gross(self):
        for res in self:
            if res.ptkp:
                res.ter_category_gross_ids = False
                total_income_reguler = 0
                for rec in res.income_reguler_ter_ids:
                    total_income_reguler += rec.amount
                total_income_irreguler = 0
                for rec in res.income_irreguler_ter_ids:
                    total_income_irreguler += rec.amount
                bruto = total_income_reguler + total_income_irreguler
                ter_category = self.get_ter_category_gross(bruto,res.ptkp_id)
                res.ter_category_gross_ids = [(0, 0, x) for x in ter_category]
            else:
                res.ter_category_gross_ids = False
    
    @api.depends('income_reguler_ter_ids.amount','income_irreguler_ter_ids.amount','ptkp_id')
    def compute_ter_category_gross_non_natura(self):
        for res in self:
            if res.ptkp:
                res.ter_category_gross_non_natura_ids = False
                total_income_reguler = 0
                for rec in res.income_reguler_ter_ids:
                    if not rec.category_on_natura_tax_id:
                        total_income_reguler += rec.amount
                total_income_irreguler = 0
                for rec in res.income_irreguler_ter_ids:
                    if not rec.category_on_natura_tax_id:
                        total_income_irreguler += rec.amount
                bruto = total_income_reguler + total_income_irreguler
                ter_category = self.get_ter_category_gross(bruto,res.ptkp_id)
                res.ter_category_gross_non_natura_ids = [(0, 0, x) for x in ter_category]
            else:
                res.ter_category_gross_non_natura_ids = False
    
    def compute_ter_tunj_pph_21_bln(self):
        result = {
            "ter_tunj_pjk_bln": 0.0,
        }
        tunj_pph21_ter = 0
        if self.ptkp:
            if self.tax_period_length == self.tax_end_month:
                tunj_pph21_ter = (self.ter_pjk_terhutang_reguler + self.ter_pjk_terhutang_irreguler) - self.ter_pph21_paid
            else:
                total_income_reguler = 0
                for rec in self.income_reguler_ter_ids:
                    total_income_reguler += rec.amount
                total_income_irreguler = 0
                for rec in self.income_irreguler_ter_ids:
                    total_income_irreguler += rec.amount
                bruto = total_income_reguler + total_income_irreguler
                bruto_val = bruto
                selisih = 0

                # non_npwp_tax_rate_setting = float(self.env['ir.config_parameter'].sudo().get_param('equip3_hr_payroll_extend_id.non_npwp_tax_rate'))
                # if non_npwp_tax_rate_setting > 0:
                #     non_npwp_tax_rate = non_npwp_tax_rate_setting
                # else:
                #     non_npwp_tax_rate = 0

                if self.npwp:
                    if (selisih == 0):
                        ter_category = self.env['hr.ter.category'].search([('ptkp_ids','in',[self.ptkp_id.id]),('bruto_income_from','<=',bruto_val),('bruto_income_to','>=',bruto_val)],limit=1)
                        tunj_pph21_ter = bruto_val * (ter_category.ter_rate / 100)
                        selisih = bruto_val - tunj_pph21_ter
                        bruto_val = bruto + tunj_pph21_ter
                    
                    while float_compare(selisih, bruto, precision_digits=2) == -1:
                        if float_compare(selisih, bruto, precision_digits=2) == 0:
                            break
                        ter_category = self.env['hr.ter.category'].search([('ptkp_ids','in',[self.ptkp_id.id]),('bruto_income_from','<=',bruto_val),('bruto_income_to','>=',bruto_val)],limit=1)
                        tunj_pph21_ter = bruto_val * (ter_category.ter_rate / 100)
                        selisih = round(bruto_val - tunj_pph21_ter, 2)
                        bruto_val = bruto + tunj_pph21_ter
                else:
                    if (selisih == 0):
                        ter_category = self.env['hr.ter.category'].search([('ptkp_ids','in',[self.ptkp_id.id]),('bruto_income_from','<=',bruto_val),('bruto_income_to','>=',bruto_val)],limit=1)
                        # tunj_pph21_ter = (bruto_val * (ter_category.ter_rate / 100) * (non_npwp_tax_rate / 100)) + (bruto_val * (ter_category.ter_rate / 100))
                        tunj_pph21_ter = bruto_val * (ter_category.ter_rate / 100)
                        selisih = bruto_val - tunj_pph21_ter
                        bruto_val = bruto + tunj_pph21_ter
                    
                    while float_compare(selisih, bruto, precision_digits=2) == -1:
                        if float_compare(selisih, bruto, precision_digits=2) == 0:
                            break
                        ter_category = self.env['hr.ter.category'].search([('ptkp_ids','in',[self.ptkp_id.id]),('bruto_income_from','<=',bruto_val),('bruto_income_to','>=',bruto_val)],limit=1)
                        # tunj_pph21_ter = (bruto_val * (ter_category.ter_rate / 100) * (non_npwp_tax_rate / 100)) + (bruto_val * (ter_category.ter_rate / 100))
                        tunj_pph21_ter = bruto_val * (ter_category.ter_rate / 100)
                        selisih = round(bruto_val - tunj_pph21_ter, 2)
                        bruto_val = bruto + tunj_pph21_ter

        result["ter_tunj_pjk_bln"] = tunj_pph21_ter
        return result
    
    def compute_ter_tunj_pph_21_bln_non_natura(self):
        result = {
            "ter_tunj_pjk_bln_non_natura": 0.0,
        }
        tunj_pph21_ter = 0
        if self.ptkp:
            if self.tax_period_length == self.tax_end_month:
                tunj_pph21_ter = (self.ter_pjk_terhutang_reguler_non_natura + self.ter_pjk_terhutang_irreguler_non_natura) - self.ter_pph21_paid_non_natura
            else:
                total_income_reguler = 0
                for rec in self.income_reguler_ter_ids:
                    if not rec.category_on_natura_tax_id:
                        total_income_reguler += rec.amount
                total_income_irreguler = 0
                for rec in self.income_irreguler_ter_ids:
                    if not rec.category_on_natura_tax_id:
                        total_income_irreguler += rec.amount
                bruto = total_income_reguler + total_income_irreguler
                bruto_val = bruto
                selisih = 0

                if self.npwp:
                    if (selisih == 0):
                        ter_category = self.env['hr.ter.category'].search([('ptkp_ids','in',[self.ptkp_id.id]),('bruto_income_from','<=',bruto_val),('bruto_income_to','>=',bruto_val)],limit=1)
                        tunj_pph21_ter = bruto_val * (ter_category.ter_rate / 100)
                        selisih = bruto_val - tunj_pph21_ter
                        bruto_val = bruto + tunj_pph21_ter
                    
                    while float_compare(selisih, bruto, precision_digits=2) == -1:
                        if float_compare(selisih, bruto, precision_digits=2) == 0:
                            break
                        ter_category = self.env['hr.ter.category'].search([('ptkp_ids','in',[self.ptkp_id.id]),('bruto_income_from','<=',bruto_val),('bruto_income_to','>=',bruto_val)],limit=1)
                        tunj_pph21_ter = bruto_val * (ter_category.ter_rate / 100)
                        selisih = round(bruto_val - tunj_pph21_ter, 2)
                        bruto_val = bruto + tunj_pph21_ter
                else:
                    if (selisih == 0):
                        ter_category = self.env['hr.ter.category'].search([('ptkp_ids','in',[self.ptkp_id.id]),('bruto_income_from','<=',bruto_val),('bruto_income_to','>=',bruto_val)],limit=1)
                        tunj_pph21_ter = bruto_val * (ter_category.ter_rate / 100)
                        selisih = bruto_val - tunj_pph21_ter
                        bruto_val = bruto + tunj_pph21_ter
                    
                    while float_compare(selisih, bruto, precision_digits=2) == -1:
                        if float_compare(selisih, bruto, precision_digits=2) == 0:
                            break
                        ter_category = self.env['hr.ter.category'].search([('ptkp_ids','in',[self.ptkp_id.id]),('bruto_income_from','<=',bruto_val),('bruto_income_to','>=',bruto_val)],limit=1)
                        tunj_pph21_ter = bruto_val * (ter_category.ter_rate / 100)
                        selisih = round(bruto_val - tunj_pph21_ter, 2)
                        bruto_val = bruto + tunj_pph21_ter

        result["ter_tunj_pjk_bln_non_natura"] = tunj_pph21_ter
        return result

    def get_tax_bracket_non_permanent(self, bruto=0.0):
        tax_bracket_val = []
        tax_bracket = self.env['hr.tax.bracket'].search([('taxable_income_from','<=',bruto),('taxable_income_to','>=',bruto)],limit=1)
        sequence = 1
        pph21_ter = bruto * (tax_bracket.tax_rate / 100)
        input_data = {
            'sequence': sequence,
            'name': tax_bracket.name,
            'tax_able_income_from': tax_bracket.taxable_income_from,
            'tax_able_income_to': tax_bracket.taxable_income_to,
            'tax_rate': tax_bracket.tax_rate,
            'pkp_ter': bruto,
            'pph21_amount': pph21_ter,
        }
        tax_bracket_val += [input_data]
        return tax_bracket_val
    
    def get_ter_daily_rate(self, bruto=0.0):
        ter_daily_val = []
        ter_daily = self.env['hr.ter.daily.rate'].search([('daily_bruto_income_from','<=',bruto),('daily_bruto_income_to','>=',bruto)],limit=1)
        sequence = 1
        pph21_ter = bruto * (ter_daily.daily_rate / 100)
        input_data = {
            'sequence': sequence,
            'daily_bruto_income_from': ter_daily.daily_bruto_income_from,
            'daily_bruto_income_to': ter_daily.daily_bruto_income_to,
            'ter_rate': ter_daily.daily_rate,
            'bruto': bruto,
            'pph21_ter': pph21_ter,
        }
        ter_daily_val += [input_data]
        return ter_daily_val
    
    @api.depends('emp_tax_status','employee_payment_method','ter_bruto_non_permanent')
    def compute_tax_bracket_non_permanent(self):
        for res in self:
            res.pph21_ter_non_permanent_ids = False
            if res.emp_tax_status == 'pegawai_tidak_tetap':
                if res.employee_payment_method == 'non_paid_monthly':
                    if res.ter_bruto_non_permanent > 2500000:
                        tax_bracket = self.get_tax_bracket_non_permanent(res.ter_bruto_non_permanent)
                        res.pph21_ter_non_permanent_ids = [(0, 0, x) for x in tax_bracket]
    
    @api.depends('emp_tax_status','employee_payment_method','ptkp_id','ter_bruto_non_permanent')
    def compute_ter_category_non_permanent(self):
        for res in self:
            res.ter_category_non_permanent_ids = False
            if res.ptkp:
                if res.emp_tax_status == 'pegawai_tidak_tetap':
                    if res.employee_payment_method == 'paid_monthly':
                        ter_category = self.get_ter_category_gross(res.ter_bruto_non_permanent,res.ptkp_id)
                        res.ter_category_non_permanent_ids = [(0, 0, x) for x in ter_category]
    
    @api.depends('emp_tax_status','employee_payment_method','ter_bruto_non_permanent')
    def compute_ter_daily_rate(self):
        for res in self:
            res.ter_daily_rate_ids = False
            if res.emp_tax_status == 'pegawai_tidak_tetap':
                if res.employee_payment_method == 'non_paid_monthly':
                    ter_daily = self.get_ter_daily_rate(res.ter_bruto_non_permanent)
                    res.ter_daily_rate_ids = [(0, 0, x) for x in ter_daily]
    
    @api.depends('income_reguler_non_permanent_ids.amount')
    def _amount_ter_akum_income_reguler_non_permanent(self):
        for res in self:
            total = 0
            for rec in res.income_reguler_non_permanent_ids:
                total += rec.amount
            res.ter_akum_income_reguler_non_permanent = total
    
    @api.depends('income_irreguler_non_permanent_ids.amount')
    def _amount_ter_akum_income_irreguler_non_permanent(self):
        for res in self:
            total = 0
            for rec in res.income_irreguler_non_permanent_ids:
                total += rec.amount
            res.ter_akum_income_irreguler_non_permanent = total
    
    @api.depends('ter_akum_income_reguler_non_permanent', 'ter_akum_income_irreguler_non_permanent')
    def _amount_ter_bruto_non_permanent(self):
        for res in self:
            res.ter_bruto_non_permanent = res.ter_akum_income_reguler_non_permanent + res.ter_akum_income_irreguler_non_permanent
    
    @api.depends('ter_bruto_non_permanent','ptkp_id')
    def _amount_ter_pjk_non_permanent(self):
        for res in self:
            if res.emp_tax_status == 'pegawai_tidak_tetap':
                if res.employee_payment_method == 'non_paid_monthly':
                    if res.ter_bruto_non_permanent <= 2500000:
                        ter_daily = self.env['hr.ter.daily.rate'].search([('daily_bruto_income_from','<=',res.ter_bruto_non_permanent),('daily_bruto_income_to','>=',res.ter_bruto_non_permanent)],limit=1)
                        if ter_daily:
                            res.ter_pjk_non_permanent = res.ter_bruto_non_permanent * (ter_daily.daily_rate / 100)
                        else:
                            res.ter_pjk_non_permanent = 0
                    else:
                        ter_daily = self.env['hr.ter.daily.rate'].search([('daily_bruto_income_from','<=',res.ter_bruto_non_permanent),('daily_bruto_income_to','>=',res.ter_bruto_non_permanent)],limit=1)
                        tax_bracket = self.env['hr.tax.bracket'].search([('taxable_income_from','<=',res.ter_bruto_non_permanent),('taxable_income_to','>=',res.ter_bruto_non_permanent)],limit=1)
                        if ter_daily and tax_bracket:
                            res.ter_pjk_non_permanent = (res.ter_bruto_non_permanent * (ter_daily.daily_rate / 100)) * (tax_bracket.tax_rate / 100)
                        else:
                            res.ter_pjk_non_permanent = 0
                elif res.employee_payment_method == 'paid_monthly':
                    ter_category = self.env['hr.ter.category'].search([('ptkp_ids','in',[res.ptkp_id.id]),('bruto_income_from','<=',res.ter_bruto_non_permanent),('bruto_income_to','>=',res.ter_bruto_non_permanent)],limit=1)
                    if ter_category:
                        res.ter_pjk_non_permanent = res.ter_bruto_non_permanent * (ter_category.ter_rate / 100)
                    else:
                        res.ter_pjk_non_permanent = 0

class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    payslip_period_id = fields.Many2one('hr.payslip.period', string='Payslip Period', domain="[('state','=','open')]", required=True)
    month = fields.Many2one('hr.payslip.period.line', string="Month", domain="[('period_id','=',payslip_period_id)]",
                            required=True)
    payslip_batch_report_date = fields.Date(string='Payslip Batch Report Date', readonly=True)
    move_id = fields.Many2one('account.move', 'Accounting Entry', readonly=True, copy=False)
    is_confirm_all = fields.Boolean('is Confirm All')
    send_email_flag = fields.Boolean('Send Email', default=False)
    allow_send_email = fields.Boolean('Allow Send Email', compute='_allow_send_email')
    state = fields.Selection(selection_add=[('refund', 'Refund')])
    move_refund_id = fields.Many2one('account.move', 'Refund Accounting Entry', readonly=True, copy=False)
    hide_button_refund = fields.Boolean('Hide Button Refund', compute='_compute_button_refund')
    employee_tax_status = fields.Selection(
        [('pegawai_tetap', 'Pegawai Tetap'), ('pegawai_tidak_tetap', 'Pegawai Tidak Tetap')],
        string='Employee Tax Status', default='pegawai_tetap', required=True)

    def _allow_send_email(self):
        for res in self:
            allow_send_email = self.env['ir.config_parameter'].sudo().get_param(
                'equip3_hr_payroll_extend_id.payslip_allow_send_email')
            res.allow_send_email = allow_send_email

    def action_send_email_payslip(self):
        values = self.slip_ids
        for rec in values:
            email_action = rec.action_send_email_payslips()
            if email_action and email_action.get('context'):
                email_ctx = email_action['context']
                email_ctx.update(default_email_from=values.company_id.email)
                rec.with_context(email_ctx).message_post_with_template(email_ctx.get('default_template_id'))
        self.send_email_flag = True
        # return True
        view = self.env.ref('equip3_hr_payroll_extend_id.view_payslip_send_email_message_form')
        view_id = view and view.id or False
        context = dict(self._context or {})
        return {
            'name': "Message",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'payslip.send.email.message',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
            'context': context,
        }

    @api.onchange('month')
    def _onchange_month(self):
        if self.payslip_period_id:
            if self.month:
                period_line_obj = self.env['hr.payslip.period.line'].search(
                    [('id', '=', self.month.id)], limit=1)
                if period_line_obj:
                    for rec in period_line_obj:
                        self.date_start = rec.start_date
                        self.date_end = rec.end_date
                        if self.payslip_period_id.start_period_based_on == 'start_date':
                            self.payslip_batch_report_date = rec.start_date
                        elif self.payslip_period_id.start_period_based_on == 'end_date':
                            self.payslip_batch_report_date = rec.end_date
                else:
                    self.date_start = False
                    self.date_end = False

    def _compute_button_refund(self):
        for res in self:
            payslip_obj = self.env['hr.payslip.run'].sudo().search([('payslip_period_id', '=', res.payslip_period_id.id),
                                                                    ('state', '=', 'close')], limit=1,
                                                                   order='payslip_batch_report_date desc')
            if payslip_obj.id != res.id:
                res.hide_button_refund = True
            else:
                res.hide_button_refund = False

    def confirm_all_payslips(self):
        for record in self:
            if record.slip_ids:
                date = record.payslip_batch_report_date or record.date_to
                line_ids = []
                move_dict = {
                    'narration': record.name,
                    'ref': record.name,
                    'journal_id': record.journal_id.id,
                    'date': date,
                }

                debit_sum = 0.0
                credit_sum = 0.0
                currency = False

                struct_map = record.slip_ids.mapped("struct_id")
                rule_val = []
                for struct in struct_map:
                    for rec in struct.rule_ids:
                        if rec.id not in rule_val:
                            rule_val.append(rec.id)
                rule_conf = self.env['hr.salary.rule'].search([('id','in',rule_val)])
                
                for val in rule_conf:
                    salary_rule = record.slip_ids.mapped("details_by_salary_rule_category").filtered(lambda slip: slip.slip_id.state == 'draft')
                    amount = 0
                    for rule in salary_rule:
                        currency = rule.slip_id.company_id.currency_id
                        if rule.salary_rule_id == val:
                            amounts = currency.round(record.credit_note and -rule.total or rule.total)
                            if currency.is_zero(amounts):
                                continue
                            amount += amounts

                    debit_account_id = val.account_debit.id
                    credit_account_id = val.account_credit.id
                    if debit_account_id and amount > 0:
                        debit_line = (0, 0, {
                            'name': 'Payslip' + '-' + record.month.month + ' ' + record.month.year + '-' + val.name,
                            'account_id': debit_account_id,
                            'journal_id': record.journal_id.id,
                            'date': date,
                            'debit': amount > 0.0 and amount or 0.0,
                            'credit': amount < 0.0 and -amount or 0.0,
                            'analytic_account_id': val.analytic_account_id.id,
                            'tax_line_id': val.account_tax_id.id,
                        })
                        line_ids.append(debit_line)
                        debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
                    if credit_account_id and amount > 0:
                        credit_line = (0, 0, {
                            'name': 'Payslip' + '-' + record.month.month + ' ' + record.month.year + '-' + val.name,
                            'account_id': credit_account_id,
                            'journal_id': record.journal_id.id,
                            'date': date,
                            'debit': amount < 0.0 and -amount or 0.0,
                            'credit': amount > 0.0 and amount or 0.0,
                            'analytic_account_id': val.analytic_account_id.id,
                            'tax_line_id': val.account_tax_id.id,
                        })
                        line_ids.append(credit_line)
                        credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']

                if currency and currency.compare_amounts(credit_sum, debit_sum) == -1:
                    acc_id = record.journal_id.default_credit_account_id.id
                    if not acc_id:
                        raise UserError(
                            _('The Expense Journal "%s" has not properly configured the Credit Account!') % (
                                record.journal_id.name))
                    adjust_credit = (0, 0, {
                        'name': _('Adjustment Entry'),
                        'partner_id': False,
                        'account_id': acc_id,
                        'journal_id': record.journal_id.id,
                        'date': date,
                        'debit': 0.0,
                        'credit': currency.round(debit_sum - credit_sum),
                    })
                    line_ids.append(adjust_credit)

                elif currency and currency.compare_amounts(debit_sum, credit_sum) == -1:
                    acc_id = record.journal_id.default_debit_account_id.id
                    if not acc_id:
                        raise UserError(_('The Expense Journal "%s" has not properly configured the Debit Account!') % (
                            record.journal_id.name))
                    adjust_debit = (0, 0, {
                        'name': _('Adjustment Entry'),
                        'partner_id': False,
                        'account_id': acc_id,
                        'journal_id': record.journal_id.id,
                        'date': date,
                        'debit': currency.round(credit_sum - debit_sum),
                        'credit': 0.0,
                    })
                    line_ids.append(adjust_debit)

                move_dict['line_ids'] = line_ids
                move = self.env['account.move'].create(move_dict)
                for slip_rec in record.slip_ids.filtered(lambda slip: slip.state == 'draft'):
                    slip_rec.write({'journal_id': record.journal_id.id, 'move_id': move.id, 'date': date, 'state': 'done'})
                if not move.line_ids:
                    raise UserError(
                        _("As you installed the payroll accounting module you have to choose Debit and Credit"
                          " account for at least one salary rule in the choosen Salary Structure."))
                move.post()

                record.write({
                    'is_confirm_all': True,
                    'state': 'close',
                    'move_id': move.id
                })

    def action_refund_payslips(self):
        for record in self:
            payslip_obj = self.env['hr.payslip.run'].sudo().search([(
                                                                'payslip_period_id', '=', record.payslip_period_id.id),
                                                                ('state', '=', 'close')], limit=1,
                                                               order='payslip_batch_report_date desc')
            if payslip_obj.id != record.id:
                raise ValidationError(_("Can't refund this payslip batch!"))
            else:
                if record.slip_ids:
                    date = record.payslip_batch_report_date or record.date_to
                    line_ids = []
                    copied_payslip_ids = []
                    move_dict = {
                        'narration': record.name,
                        'ref': record.name,
                        'journal_id': record.journal_id.id,
                        'date': date,
                    }
                    for rec in record.slip_ids.filtered(lambda slip: slip.state == 'done'):
                        copied_payslip = rec.copy({'credit_note': True, 'name': _('Refund: ') + rec.name, 'refund_reference': rec.id})
                        copied_payslip.compute_sheet()
                        debit_sum = 0.0
                        credit_sum = 0.0
                        currency = rec.company_id.currency_id

                        for line in rec.details_by_salary_rule_category:
                            amount = currency.round(copied_payslip.credit_note and -line.total or line.total)
                            if currency.is_zero(amount):
                                continue
                            debit_account_id = line.salary_rule_id.account_debit.id
                            credit_account_id = line.salary_rule_id.account_credit.id

                            if debit_account_id:
                                debit_line = (0, 0, {
                                    'name': copied_payslip.employee_id.name + '-' + copied_payslip.number + '-' + copied_payslip.month_name + ' ' + copied_payslip.year + '-' + copied_payslip.name,
                                    'partner_id': line._get_partner_id(credit_account=False),
                                    'account_id': debit_account_id,
                                    'journal_id': record.journal_id.id,
                                    'date': date,
                                    'debit': amount > 0.0 and amount or 0.0,
                                    'credit': amount < 0.0 and -amount or 0.0,
                                    'analytic_account_id': line.salary_rule_id.analytic_account_id.id,
                                    'tax_line_id': line.salary_rule_id.account_tax_id.id,
                                })
                                line_ids.append(debit_line)
                                debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
                            if credit_account_id:
                                credit_line = (0, 0, {
                                    'name': copied_payslip.employee_id.name + '-' + copied_payslip.number + '-' + copied_payslip.month_name + ' ' + copied_payslip.year + '-' + copied_payslip.name,
                                    'partner_id': line._get_partner_id(credit_account=True),
                                    'account_id': credit_account_id,
                                    'journal_id': record.journal_id.id,
                                    'date': date,
                                    'debit': amount < 0.0 and -amount or 0.0,
                                    'credit': amount > 0.0 and amount or 0.0,
                                    'analytic_account_id': line.salary_rule_id.analytic_account_id.id,
                                    'tax_line_id': line.salary_rule_id.account_tax_id.id,
                                })
                                line_ids.append(credit_line)
                                credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']

                        copied_payslip_ids += copied_payslip
                        rec.action_payslip_refund()
                        rec.refund_reference = copied_payslip.id

                    if currency.compare_amounts(credit_sum, debit_sum) == -1:
                        acc_id = record.journal_id.default_credit_account_id.id
                        if not acc_id:
                            raise UserError(
                                _('The Expense Journal "%s" has not properly configured the Credit Account!') % (
                                    record.journal_id.name))
                        adjust_credit = (0, 0, {
                            'name': _('Adjustment Entry'),
                            'partner_id': False,
                            'account_id': acc_id,
                            'journal_id': record.journal_id.id,
                            'date': date,
                            'debit': 0.0,
                            'credit': currency.round(debit_sum - credit_sum),
                        })
                        line_ids.append(adjust_credit)

                    elif currency.compare_amounts(debit_sum, credit_sum) == -1:
                        acc_id = record.journal_id.default_debit_account_id.id
                        if not acc_id:
                            raise UserError(_('The Expense Journal "%s" has not properly configured the Debit Account!') % (
                                record.journal_id.name))
                        adjust_debit = (0, 0, {
                            'name': _('Adjustment Entry'),
                            'partner_id': False,
                            'account_id': acc_id,
                            'journal_id': record.journal_id.id,
                            'date': date,
                            'debit': currency.round(credit_sum - debit_sum),
                            'credit': 0.0,
                        })
                        line_ids.append(adjust_debit)
                    move_dict['line_ids'] = line_ids
                    move = self.env['account.move'].create(move_dict)
                    if not move.line_ids:
                        raise UserError(
                            _("As you installed the payroll accounting module you have to choose Debit and Credit"
                              " account for at least one salary rule in the choosen Salary Structure."))
                    move.post()

                    for slip_rec in copied_payslip_ids:
                        slip_rec.write({'state': 'refund', 'move_id': move.id, 'date': date})

                    record.write({
                        'state': 'refund',
                        'move_refund_id': move.id,
                        'credit_note': True
                    })

class HrPayslipTaxCalculation(models.Model):
    _name = 'hr.payslip.tax.calculation'
    _description = 'Payslip Tax Calculation'
    _order = 'sequence'

    name = fields.Char('Salary Rule', required=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(required=True, index=True)
    category_id = fields.Many2one('hr.salary.rule.category', string='Category', required=True)
    slip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', help="Payslip")
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, help="Employee")
    tax_calculation_method = fields.Char('Tax Calculation Method')
    tax_category = fields.Selection([('income_reguler', 'Income Reguler'), ('income_irreguler', 'Income Irreguler'),
                                     ('deduction', 'Deduction')], string='Tax Category')
    amount = fields.Float(string='Amount', digits=dp.get_precision('Payroll'))

class HrPayslipLateDeduction(models.Model):
    _name = 'hr.payslip.late.deduction'
    _description = 'Payslip Late Deduction'

    slip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', help="Payslip")
    hour_from = fields.Float('Work From', readonly=True)
    date_checkin = fields.Datetime('Date Checkin', readonly=True)
    tolerance_for_late = fields.Float('Tolerance for Late', readonly=True)
    number_of_hours = fields.Float('Number of Hours', compute="get_number_of_hours", store=True, readonly=True)
    attendance_formula_id = fields.Many2one('hr.attendance.formula', string="Attendance Formula")
    amount = fields.Float('Amount', compute="get_amount", store=True, readonly=True)

    @api.depends('hour_from', 'date_checkin', 'tolerance_for_late')
    def get_number_of_hours(self):
        for res in self:
            user_tz = res.slip_id.employee_id.tz or pytz.utc
            local = pytz.timezone(user_tz)
            check_in = pytz.UTC.localize(res.date_checkin).astimezone(local)
            checkin_time = check_in.time()
            checkin_float = checkin_time.hour + checkin_time.minute / 60
            res.number_of_hours = checkin_float - res.hour_from - res.tolerance_for_late

    @api.depends('number_of_hours')
    def get_amount(self):
        for res in self:
            attendance_formula_setting = self.env['hr.config.settings'].sudo().search([],limit=1)
            working_time = res.slip_id.employee_id.resource_calendar_id
            late_deduction_rule = working_time.late_dedution_rules_id
            amounts = 0.0
            if attendance_formula_setting.use_attendance_formula:
                numb_mins = res.number_of_hours * 60
                numb_hour, numb_minute = divmod(numb_mins, 60)
                val_minute = (round(numb_hour) * 60) + round(numb_minute)
                if res.attendance_formula_id:
                    wage = res.slip_id.contract_id.wage if res.slip_id.contract_id else 0
                    amounts = res.attendance_formula_id._execute_formula(wage,val_minute)
            else:
                if late_deduction_rule.late_deduction_lines:
                    for rec in late_deduction_rule.late_deduction_lines:
                        if not rec.is_multiple:
                            if round(res.number_of_hours, 2) >= round(rec.time, 2):
                                amounts = rec.amount
                        else:
                            if round(res.number_of_hours, 2) >= round(rec.time, 2):
                                if round(res.number_of_hours, 2) <= round(rec.maximum_time, 2):
                                    diff = int(round(res.number_of_hours / rec.time, 2))
                                else:
                                    diff = rec.maximum_time / rec.time
                                amounts = rec.amount * diff
            res.amount = amounts

class HrPayslipTaxPesango(models.Model):
    _name = 'hr.payslip.tax.pesangon'
    _description = 'Pesangon Tax Calculation'
    _order = 'sequence'

    slip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', help="Payslip")
    sequence = fields.Integer(required=True, index=True)
    name = fields.Char('Name', required=True)
    tax_income_from = fields.Float('Taxable Income From')
    tax_income_to = fields.Float('Taxable Income To')
    tax_rate = fields.Float('Tax Rate (%)')
    bruto_pesangon = fields.Float('Bruto Pesangon')
    pph21_amount = fields.Float('PPh 21 Pesangon')

class HrPayslipTaxReguler(models.Model):
    _name = 'hr.payslip.tax.reguler'
    _description = 'Reguler Tax Calculation Gross Up'
    _order = 'sequence'

    slip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', help="Payslip")
    sequence = fields.Integer(required=True, index=True)
    name = fields.Char('Name', required=True)
    tax_income_from = fields.Float('Taxable Income From')
    tax_income_to = fields.Float('Taxable Income To')
    tax_rate = fields.Float('Tax Rate (%)')
    tax_penalty_rate = fields.Float('Tax Penalty Rate (%)')
    pkp = fields.Float('PKP Reguler')
    pph21_amount = fields.Float('PPh 21 Reguler')

class HrPayslipTaxIrreguler(models.Model):
    _name = 'hr.payslip.tax.irreguler'
    _description = 'Irreguler Tax Calculation Gross Up'
    _order = 'sequence'

    slip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', help="Payslip")
    sequence = fields.Integer(required=True, index=True)
    name = fields.Char('Name', required=True)
    tax_income_from = fields.Float('Taxable Income From')
    tax_income_to = fields.Float('Taxable Income To')
    tax_rate = fields.Float('Tax Rate (%)')
    tax_penalty_rate = fields.Float('Tax Penalty Rate (%)')
    pkp = fields.Float('PKP Irreguler')
    pph21_amount = fields.Float('PPh 21 Irreguler')

class HrPayslipTaxRegulerGross(models.Model):
    _name = 'hr.payslip.tax.reguler.gross'
    _description = 'Reguler Tax Calculation Gross'
    _order = 'sequence'

    slip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', help="Payslip")
    sequence = fields.Integer(required=True, index=True)
    name = fields.Char('Name', required=True)
    tax_income_from = fields.Float('Taxable Income From')
    tax_income_to = fields.Float('Taxable Income To')
    tax_rate = fields.Float('Tax Rate (%)')
    tax_penalty_rate = fields.Float('Tax Penalty Rate (%)')
    pkp = fields.Float('PKP Reguler')
    pph21_amount = fields.Float('PPh 21 Reguler')

class HrPayslipTaxIrregulerGross(models.Model):
    _name = 'hr.payslip.tax.irreguler.gross'
    _description = 'Irreguler Tax Calculation Gross'
    _order = 'sequence'

    slip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', help="Payslip")
    sequence = fields.Integer(required=True, index=True)
    name = fields.Char('Name', required=True)
    tax_income_from = fields.Float('Taxable Income From')
    tax_income_to = fields.Float('Taxable Income To')
    tax_rate = fields.Float('Tax Rate (%)')
    tax_penalty_rate = fields.Float('Tax Penalty Rate (%)')
    pkp = fields.Float('PKP Irreguler')
    pph21_amount = fields.Float('PPh 21 Irreguler')

class HrPayslipTaxTerCalculation(models.Model):
    _name = 'hr.payslip.tax.ter.calculation'
    _description = 'Payslip Tax TER Calculation'
    _order = 'sequence'

    name = fields.Char('Salary Rule', required=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(required=True, index=True)
    category_id = fields.Many2one('hr.salary.rule.category', string='Category', required=True)
    slip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', help="Payslip")
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, help="Employee")
    tax_category = fields.Selection([('income_reguler', 'Income Reguler'), ('income_irreguler', 'Income Irreguler'),
                                     ('deduction', 'Deduction')], string='Tax Category')
    category_on_natura_tax_id = fields.Many2one('hr.natura.category', string="Category on Natura Tax")
    amount = fields.Float(string='Amount', digits=dp.get_precision('Payroll'))

class HrPayslipTaxTerReguler(models.Model):
    _name = 'hr.payslip.tax.ter.reguler'
    _description = 'Tax Calculation TER Reguler'
    _order = 'sequence'

    slip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', help="Payslip")
    sequence = fields.Integer(required=True, index=True)
    name = fields.Char('Name', required=True)
    tax_able_income_from = fields.Float('Taxable Income From')
    tax_able_income_to = fields.Float('Taxable Income To')
    tax_rate = fields.Float('Tax Rate (%)')
    tax_penalty_rate = fields.Float('Tax Penalty Rate (%)')
    pkp_ter = fields.Float('PKP')
    pph21_amount = fields.Float('PPH21')

class HrPayslipTaxTerIrreguler(models.Model):
    _name = 'hr.payslip.tax.ter.irreguler'
    _description = 'Tax Calculation TER Irreguler'
    _order = 'sequence'

    slip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', help="Payslip")
    sequence = fields.Integer(required=True, index=True)
    name = fields.Char('Name', required=True)
    tax_able_income_from = fields.Float('Taxable Income From')
    tax_able_income_to = fields.Float('Taxable Income To')
    tax_rate = fields.Float('Tax Rate (%)')
    tax_penalty_rate = fields.Float('Tax Penalty Rate (%)')
    pkp_ter = fields.Float('PKP')
    pph21_amount = fields.Float('PPH21')

class HrPayslipTerCat(models.Model):
    _name = 'hr.payslip.ter.cat'
    _description = 'TER Category'
    _order = 'sequence'

    slip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', help="Payslip")
    sequence = fields.Integer(required=True, index=True)
    category = fields.Char('Category', required=True)
    ptkp_ids = fields.Many2many('hr.tax.ptkp', string="PTKP")
    bruto_income_from = fields.Float('Bruto Income From', group_operator=False)
    bruto_income_to = fields.Float('Bruto Income To', group_operator=False)
    ter_rate = fields.Float('Rate (%)', group_operator=False)
    bruto = fields.Float('Bruto', help='Gross Income This Month', group_operator=False)
    pph21_ter = fields.Float('PPH21', group_operator=False)

class HrPayslipTaxTerRegulerNonNatura(models.Model):
    _name = 'hr.payslip.tax.ter.reguler.non.natura'
    _description = 'Tax Calculation TER Reguler Non Natura'
    _order = 'sequence'

    slip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', help="Payslip")
    sequence = fields.Integer(required=True, index=True)
    name = fields.Char('Name', required=True)
    tax_able_income_from = fields.Float('Taxable Income From')
    tax_able_income_to = fields.Float('Taxable Income To')
    tax_rate = fields.Float('Tax Rate (%)')
    tax_penalty_rate = fields.Float('Tax Penalty Rate (%)')
    pkp_ter = fields.Float('PKP')
    pph21_amount = fields.Float('PPH21')

class HrPayslipTaxTerIrregulerNonNatura(models.Model):
    _name = 'hr.payslip.tax.ter.irreguler.non.natura'
    _description = 'Tax Calculation TER Irreguler Non Natura'
    _order = 'sequence'

    slip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', help="Payslip")
    sequence = fields.Integer(required=True, index=True)
    name = fields.Char('Name', required=True)
    tax_able_income_from = fields.Float('Taxable Income From')
    tax_able_income_to = fields.Float('Taxable Income To')
    tax_rate = fields.Float('Tax Rate (%)')
    tax_penalty_rate = fields.Float('Tax Penalty Rate (%)')
    pkp_ter = fields.Float('PKP')
    pph21_amount = fields.Float('PPH21')

class HrPayslipTerCatNonNatura(models.Model):
    _name = 'hr.payslip.ter.cat.non.natura'
    _description = 'TER Category Non Natura'
    _order = 'sequence'

    slip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', help="Payslip")
    sequence = fields.Integer(required=True, index=True)
    category = fields.Char('Category', required=True)
    ptkp_ids = fields.Many2many('hr.tax.ptkp', string="PTKP")
    bruto_income_from = fields.Float('Bruto Income From', group_operator=False)
    bruto_income_to = fields.Float('Bruto Income To', group_operator=False)
    ter_rate = fields.Float('Rate (%)', group_operator=False)
    bruto = fields.Float('Bruto', help='Gross Income This Month', group_operator=False)
    pph21_ter = fields.Float('PPH21', group_operator=False)

class HrPayslipTaxTerRegulerGross(models.Model):
    _name = 'hr.payslip.tax.ter.reguler.gross'
    _description = 'Tax Calculation TER Reguler Gross'
    _order = 'sequence'

    slip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', help="Payslip")
    sequence = fields.Integer(required=True, index=True)
    name = fields.Char('Name', required=True)
    tax_able_income_from = fields.Float('Taxable Income From')
    tax_able_income_to = fields.Float('Taxable Income To')
    tax_rate = fields.Float('Tax Rate (%)')
    tax_penalty_rate = fields.Float('Tax Penalty Rate (%)')
    pkp_ter = fields.Float('PKP')
    pph21_amount = fields.Float('PPH21')

class HrPayslipTaxTerIrregulerGross(models.Model):
    _name = 'hr.payslip.tax.ter.irreguler.gross'
    _description = 'Tax Calculation TER Irreguler Gross'
    _order = 'sequence'

    slip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', help="Payslip")
    sequence = fields.Integer(required=True, index=True)
    name = fields.Char('Name', required=True)
    tax_able_income_from = fields.Float('Taxable Income From')
    tax_able_income_to = fields.Float('Taxable Income To')
    tax_rate = fields.Float('Tax Rate (%)')
    tax_penalty_rate = fields.Float('Tax Penalty Rate (%)')
    pkp_ter = fields.Float('PKP')
    pph21_amount = fields.Float('PPH21')

class HrPayslipTerCatGross(models.Model):
    _name = 'hr.payslip.ter.cat.gross'
    _description = 'TER Category Gross'
    _order = 'sequence'

    slip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', help="Payslip")
    sequence = fields.Integer(required=True, index=True)
    category = fields.Char('Category', required=True)
    ptkp_ids = fields.Many2many('hr.tax.ptkp', string="PTKP")
    bruto_income_from = fields.Float('Bruto Income From', group_operator=False)
    bruto_income_to = fields.Float('Bruto Income To', group_operator=False)
    ter_rate = fields.Float('Rate (%)', group_operator=False)
    bruto = fields.Float('Bruto', help='Gross Income This Month', group_operator=False)
    pph21_ter = fields.Float('PPH21', group_operator=False)

class HrPayslipTaxTerRegulerGrossNonNatura(models.Model):
    _name = 'hr.payslip.tax.ter.reguler.gross.non.natura'
    _description = 'Tax Calculation TER Reguler Gross Non Natura'
    _order = 'sequence'

    slip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', help="Payslip")
    sequence = fields.Integer(required=True, index=True)
    name = fields.Char('Name', required=True)
    tax_able_income_from = fields.Float('Taxable Income From')
    tax_able_income_to = fields.Float('Taxable Income To')
    tax_rate = fields.Float('Tax Rate (%)')
    tax_penalty_rate = fields.Float('Tax Penalty Rate (%)')
    pkp_ter = fields.Float('PKP')
    pph21_amount = fields.Float('PPH21')

class HrPayslipTaxTerIrregulerGrossNonNatura(models.Model):
    _name = 'hr.payslip.tax.ter.irreguler.gross.non.natura'
    _description = 'Tax Calculation TER Irreguler Gross Non Natura'
    _order = 'sequence'

    slip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', help="Payslip")
    sequence = fields.Integer(required=True, index=True)
    name = fields.Char('Name', required=True)
    tax_able_income_from = fields.Float('Taxable Income From')
    tax_able_income_to = fields.Float('Taxable Income To')
    tax_rate = fields.Float('Tax Rate (%)')
    tax_penalty_rate = fields.Float('Tax Penalty Rate (%)')
    pkp_ter = fields.Float('PKP')
    pph21_amount = fields.Float('PPH21')

class HrPayslipTerCatGrossNonNatura(models.Model):
    _name = 'hr.payslip.ter.cat.gross.non.natura'
    _description = 'TER Category Gross Non Natura'
    _order = 'sequence'

    slip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', help="Payslip")
    sequence = fields.Integer(required=True, index=True)
    category = fields.Char('Category', required=True)
    ptkp_ids = fields.Many2many('hr.tax.ptkp', string="PTKP")
    bruto_income_from = fields.Float('Bruto Income From', group_operator=False)
    bruto_income_to = fields.Float('Bruto Income To', group_operator=False)
    ter_rate = fields.Float('Rate (%)', group_operator=False)
    bruto = fields.Float('Bruto', help='Gross Income This Month', group_operator=False)
    pph21_ter = fields.Float('PPH21', group_operator=False)

class HrPayslipTaxTerNonPermanent(models.Model):
    _name = 'hr.payslip.tax.non.permanent'
    _description = 'Payslip Tax TER Non Permanent'
    _order = 'sequence'

    slip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', help="Payslip")
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, help="Employee")
    name = fields.Char('Salary Rule', required=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(required=True, index=True)
    tax_calculation_method = fields.Char('Tax Calculation Method')
    category_id = fields.Many2one('hr.salary.rule.category', string='Category', required=True)
    tax_category = fields.Selection([('income_reguler', 'Income Reguler'), ('income_irreguler', 'Income Irreguler'),
                                     ('deduction', 'Deduction')], string='Tax Category')
    category_on_natura_tax_id = fields.Many2one('hr.natura.category', string="Category on Natura Tax")
    amount = fields.Float(string='Amount', digits=dp.get_precision('Payroll'))

class HrPayslipTaxTerNonPermanent(models.Model):
    _name = 'hr.payslip.tax.ter.non.permanent'
    _description = 'Tax Bracket TER Non Permanent'
    _order = 'sequence'

    slip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', help="Payslip")
    sequence = fields.Integer(required=True, index=True)
    name = fields.Char('Name', required=True)
    tax_able_income_from = fields.Float('Taxable Income From')
    tax_able_income_to = fields.Float('Taxable Income To')
    tax_rate = fields.Float('Tax Rate (%)')
    tax_penalty_rate = fields.Float('Tax Penalty Rate (%)')
    pkp_ter = fields.Float('PKP')
    pph21_amount = fields.Float('PPH21')

class HrPayslipTerCatNonPermanent(models.Model):
    _name = 'hr.payslip.ter.cat.non.permanent'
    _description = 'TER Category Non Permanent'
    _order = 'sequence'

    slip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', help="Payslip")
    sequence = fields.Integer(required=True, index=True)
    category = fields.Char('Category', required=True)
    ptkp_ids = fields.Many2many('hr.tax.ptkp', string="PTKP")
    bruto_income_from = fields.Float('Bruto Income From', group_operator=False)
    bruto_income_to = fields.Float('Bruto Income To', group_operator=False)
    bruto = fields.Float('Bruto', help='Gross Income This Month', group_operator=False)
    ter_rate = fields.Float('Rate (%)', group_operator=False)
    pph21_ter = fields.Float('PPH21', group_operator=False)

class HrPayslipTerDailyRate(models.Model):
    _name = 'hr.payslip.ter.daily.rate'
    _description = 'TER Daily Rate'
    _order = 'sequence'

    slip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', help="Payslip")
    sequence = fields.Integer(required=True, index=True)
    daily_bruto_income_from = fields.Float('Bruto Income From', group_operator=False)
    daily_bruto_income_to = fields.Float('Bruto Income To', group_operator=False)
    bruto = fields.Float('Bruto', help='Gross Income This Month', group_operator=False)
    ter_rate = fields.Float('Rate (%)', group_operator=False)
    pph21_ter = fields.Float('PPH21', group_operator=False)