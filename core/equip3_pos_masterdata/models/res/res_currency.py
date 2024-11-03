# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ResCurrency(models.Model):
    _inherit = 'res.currency'

    company_id = fields.Many2one(required=True)
    converted_currency = fields.Float('Converted Currency', compute="_compute_converted_currency")

    @api.depends('company_id')
    def _compute_converted_currency(self):
        company_currency = self.env.company.currency_id
        for i in self:
            if i.id == company_currency.id:
                i.converted_currency = 1
            else:
                rate = (i.rate / company_currency.rate)
                i.converted_currency = rate


class ResCurrencyRate(models.Model):
    _inherit = "res.currency.rate"

    @api.model
    def create(self, vals):
        if vals.get('rate', False) and vals.get('rate') == 0:
            raise UserError('Rate can not is 0')
        return super(ResCurrencyRate, self).create(vals)

    def write(self, vals):
        if vals.get('rate', False) and vals.get('rate') == 0:
            raise UserError('Rate can not is 0')
        return super(ResCurrencyRate, self).write(vals)