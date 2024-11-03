# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class KsSalesForecast(models.Model):
    _inherit = 'ks.sales.forecast'

    company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)

    @api.model
    def create(self, vals):
        if 'ks_name' not in vals or vals['ks_name'] == _('New'):
            company = self.env.company.name
            code = self.env['ir.sequence'].search([('code','=','ks.sales.forecast.' + company)])
            if code:
                vals['ks_name'] = self.env['ir.sequence'].next_by_code('ks.sales.forecast.' + company) or _('New')
        return super().create(vals)

class KsSalesForecast(models.Model):
    _inherit = 'ks.sales.forecast.result'

    company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)
