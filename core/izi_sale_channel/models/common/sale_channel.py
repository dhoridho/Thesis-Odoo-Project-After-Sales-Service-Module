# -*- coding: utf-8 -*-
# Copyright 2022 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models

class SaleChannel(models.Model):
    _name = 'sale.channel'
    _description = 'Sale Channel'
    _rec_name = 'complete_name'
    _order = 'complete_name'
    
    _sql_constraints = [
        ('code_unique', 'unique(code, company_id)', 'Code must be unique per company.')
    ]

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    complete_name = fields.Char(
        'Complete Name', compute='_compute_complete_name',
        store=True)
    parent_id = fields.Many2one('sale.channel', string='Parent')
    child_ids = fields.One2many('sale.channel', 'parent_id', string='Child')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    analytic_tag_id = fields.Many2one('account.analytic.tag', string='Analytic Tag')

    confirm_sale_auto_post_invoice = fields.Boolean('Auto Post Invoice')
    confirm_sale_without_picking = fields.Boolean('No Create Picking')

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for record in self:
            if record.parent_id:
                record.complete_name = '%s / %s' % (record.parent_id.complete_name, record.name)
            else:
                record.complete_name = record.name

    def domain_company(self):
        return [('id', 'in', self.env.companies.ids)]

    company_id = fields.Many2one('res.company', string='Company', domain=domain_company)
