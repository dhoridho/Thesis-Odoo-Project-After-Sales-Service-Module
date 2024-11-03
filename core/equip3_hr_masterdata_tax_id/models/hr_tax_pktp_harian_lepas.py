from odoo import _, api, fields, models


class HRTaxPktpHarianLepas(models.Model):
    _name = 'hr.tax.ptkp.harian.lepas'
    _description = 'HR Tax Pktp Harian Lepas'

    name = fields.Char("Name", required=True, readonly=True)
    daily_income_ptkp = fields.Float(string='Daily Income (PTKP)')
    cummulative_income_start = fields.Float(string='Cummulative Income Start')
    cummulative_income_end = fields.Float(string='Cummulative Income End')
    tax_rate = fields.Float(string='Tax Rate (%)')
    tax_penalty_rate = fields.Float(string='Tax Penalty Rate (%)')
