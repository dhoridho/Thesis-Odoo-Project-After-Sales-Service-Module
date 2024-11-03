# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class HrTaxBracketPesangonUpmk(models.Model):
    _name = 'hr.tax.bracket.pesangon.upmk'
    _description = 'Tax Bracket Pesangon & UPMK'

    sequence = fields.Integer('Sequence')
    name = fields.Char('Name', required=True)
    tax_income_from = fields.Float('Taxable Income From', required=True)
    tax_income_to = fields.Float('Taxable Income To', required=True)
    tax_rate = fields.Float('Tax Rate (%)', required=True)

    @api.model
    def default_get(self, fields):
        res = super(HrTaxBracketPesangonUpmk, self).default_get(fields)
        num_list = []
        tax_bracket = self.search([])
        if not tax_bracket:
            res.update({'sequence': 1})
        elif tax_bracket:
            num_list.extend([data.sequence for data in tax_bracket])
            next_sequence = max(num_list) + 1
            res.update({'sequence': next_sequence})
        return res