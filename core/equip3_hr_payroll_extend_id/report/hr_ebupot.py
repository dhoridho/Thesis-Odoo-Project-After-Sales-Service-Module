# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime

class HrEbupot(models.Model):
    _name = 'hr.ebupot'
    _description = "e-Bupot PPH 21/26"

    company_id = fields.Many2one('res.company', string='Company')
    year_id = fields.Many2one('hr.payslip.period', string='Year')
    month_id = fields.Many2one('hr.payslip.period.line', string="Month")
    ebupot_type = fields.Selection([('pph21','PPH21'),('pph26','PPH26')], string='e-Bupot Type')
    attachment = fields.Binary()
    attachment_fname = fields.Char()
    
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(HrEbupot, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(HrEbupot, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)