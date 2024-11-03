# -*- coding: utf-8 -*-
from odoo import fields, models, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    payslip_allow_send_email = fields.Boolean(config_parameter='equip3_hr_payroll_extend_id.payslip_allow_send_email', string='Allow send payslip to email')
    bpjs_kesehatan_limit = fields.Float(config_parameter='equip3_hr_payroll_extend_id.bpjs_kesehatan_limit', string='BPJS kesehatan Limit', default=12000000)
    jaminan_pensiun_limit = fields.Float(config_parameter='equip3_hr_payroll_extend_id.jaminan_pensiun_limit', string='Jaminan Pensiun Limit', default=8939700)
    limit_age_bpjs = fields.Integer(config_parameter='equip3_hr_payroll_extend_id.limit_age_bpjs', string='Limit Age of BPJS')
    tax_calculation_method = fields.Selection(
        [('monthly', 'Monthly'), ('average', 'Average')],
        config_parameter='equip3_hr_payroll_extend_id.tax_calculation_method', default='average')
    tax_calculation_schema = fields.Selection(
        [('pph21_ter', 'PPH21 TER'), ('pph21', 'PPH21')],
        config_parameter='equip3_hr_payroll_extend_id.tax_calculation_schema', default='pph21_ter')
    non_npwp_tax_rate = fields.Float(config_parameter='equip3_hr_payroll_extend_id.non_npwp_tax_rate', string='Non-NPWP Tax Rate(%)', default=20)
    is_cost_price_per_warehouse = fields.Boolean()

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(tax_calculation_method=self.env['ir.config_parameter'].sudo().get_param('equip3_hr_payroll_extend_id.tax_calculation_method',default='average'))
        res.update(tax_calculation_schema=self.env['ir.config_parameter'].sudo().get_param('equip3_hr_payroll_extend_id.tax_calculation_schema',default='pph21_ter'))
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('equip3_hr_payroll_extend_id.bpjs_kesehatan_limit', self.bpjs_kesehatan_limit)
        self.env['ir.config_parameter'].sudo().set_param('equip3_hr_payroll_extend_id.jaminan_pensiun_limit', self.jaminan_pensiun_limit)
        self.env['ir.config_parameter'].sudo().set_param('equip3_hr_payroll_extend_id.tax_calculation_method', self.tax_calculation_method)
        self.env['ir.config_parameter'].sudo().set_param('equip3_hr_payroll_extend_id.tax_calculation_schema', self.tax_calculation_schema)
        self.env['ir.config_parameter'].sudo().set_param('equip3_hr_payroll_extend_id.non_npwp_tax_rate', self.non_npwp_tax_rate)
        payslip_period = self.env['hr.payslip.period'].sudo().search([('state','in',['draft'])])
        if payslip_period:
            for period in payslip_period:
                period.write({'tax_calculation_schema': self.tax_calculation_schema})
        if self.tax_calculation_schema == 'pph21_ter':
            tax_bracket = self.env['hr.tax.bracket'].sudo().search([])
            if tax_bracket:
                for tax in tax_bracket:
                    tax.write({'tax_penalty_rate': 0})
