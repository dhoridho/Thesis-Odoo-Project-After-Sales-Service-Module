from odoo import _, api, fields, models

class HRTaxSetting(models.Model):
    _name = 'hr.tax.setting'
    _description = 'HR Tax Setting'

    name = fields.Char("Name", required=True, readonly=True)
    job_cost_rate = fields.Float(string='Job Title Cost Rate (%)')
    max_job_cost_rate_monthly = fields.Float(string='Max Job Title Cost (Monthly)')
    max_job_cost_rate_annualized = fields.Float(string='Max Job Title Cost (Annualized)')
    pph26_rate = fields.Float(string='PPh26 Rate (%)')