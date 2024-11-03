
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    company_uen = fields.Char('Company UEN')
    gst_no = fields.Char('GST No')
    iaf_creation_date = fields.Date('IAF Creation Date')
    product_version = fields.Char('Product Version')
    iaf_version = fields.Char('IAF Version')
    credit_account_ids = fields.Many2many('account.account',
                                          'credit_account_company_rel',
                                          'company_id', 'account_id',
                                          'Creditable Accounts')
    debit_account_ids = fields.Many2many('account.account',
                                         'debit_account_company_rel',
                                         'company_id', 'account_id',
                                         'Debitable Accounts')
