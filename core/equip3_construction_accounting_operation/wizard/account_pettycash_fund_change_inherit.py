# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools.translate import _
from odoo.exceptions import ValidationError


class AccountPettycashFundChange(models.TransientModel):
    _inherit = 'account.pettycash.fund.change'

    project = fields.Many2one ('project.project', string="Project", related='fund.project')
    referred_budget_material = fields.Many2one('material.overhead', 'Referred Budget', related='fund.referred_budget_material')
    referred_budget_budget = fields.Many2one('budget.overhead', 'Referred Budget', related='fund.referred_budget_budget')

    @api.onchange('new_amount')
    def onchange_new_amount(self):
        res = super(AccountPettycashFundChange, self).onchange_new_amount()
        for wiz in self:
            if wiz.new_amount > 0:
                if wiz.referred_budget_budget:
                    if wiz.new_amount > wiz.referred_budget_budget.amt_left:
                        raise ValidationError(_("The fund amount is over the remaining budget"))
                    else:
                        return res
                elif wiz.referred_budget_material:
                    if wiz.new_amount > wiz.referred_budget_material.budgeted_amt_left:
                        raise ValidationError(_("The fund amount is over the remaining budget"))
                    else:
                        return res
                else:
                    pass
    
    def change_fund(self):
        res = super(AccountPettycashFundChange, self).change_fund()
        for wiz in self:
            if wiz.new_amount > 0:
                if wiz.referred_budget_budget:
                    if wiz.new_amount > wiz.referred_budget_budget.amt_left:
                        raise ValidationError(_("The fund amount is over the remaining budget"))
                    else:
                        return res
                elif wiz.referred_budget_material:
                    if wiz.new_amount > wiz.referred_budget_material.budgeted_amt_left:
                        raise ValidationError(_("The fund amount is over the remaining budget"))
                    else:
                        return res
                else:
                    pass

