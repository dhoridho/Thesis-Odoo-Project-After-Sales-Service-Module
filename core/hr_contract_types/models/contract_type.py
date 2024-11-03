# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ContractType(models.Model):
    _name = 'hr.contract.type'
    _description = 'Contract Type'
    _order = 'sequence, id'

    name = fields.Char(string='Contract Type', required=True, help="Name")
    sequence = fields.Integer(help="Gives the sequence when displaying a list of Contract.", default=10)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

class ContractInherit(models.Model):
    _inherit = 'hr.contract'
    
    @api.model
    def _multi_company_domain(self):
        return [('company_id','=', self.env.company.id)]

    type_id = fields.Many2one('hr.contract.type', string="Employee Category",
                              required=True, help="Employee category",
                              domain=_multi_company_domain)
