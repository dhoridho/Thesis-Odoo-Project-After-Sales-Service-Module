# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountCommonReport(models.TransientModel):
    _inherit = "account.common.report"

    @api.model
    def _domain_branch(self):
        return [('id','in', self.env.companies.ids)]

    report_currency_id = fields.Many2one('res.currency', string="Currency")
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company, domain=_domain_branch,)
    
