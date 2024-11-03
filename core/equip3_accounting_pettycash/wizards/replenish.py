# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError

class ReplenishWizard(models.TransientModel):
    _name = 'replenish.wizard'
    _description = 'Replenish Petty Cash Fund'

    @api.model
    def _get_fund(self):
        fund_id = self.env.context.get('active_id', False)
        return fund_id

    @api.model
    def _domain_replenish_account(self):
        return [('user_type_id.name','in',['Receivable','Bank and Cash','Current Assets']), ('company_id','=', self.env.company.id)]

    fund_id = fields.Many2one(
        'account.pettycash', default=_get_fund, required=True)
    effective_date = fields.Date('Accounting Date')
    replenish_account_id = fields.Many2one('account.account', string='Replenish Account', domain=_domain_replenish_account)
    replenish_amount = fields.Float('Replenish Amount')

    def replenish_fund(self):
        move_vals = {}
        for record in self:
            if record.fund_id.balance > record.fund_id.amount:
                raise ValidationError("Balance should be lesser than fund amount!")
            amount = record.fund_id.amount - record.fund_id.balance
            if amount > 0.00:
                replenish_amount = amount
            else:
                replenish_amount = -(amount)
            if record.replenish_amount and record.replenish_amount > replenish_amount:
                raise ValidationError("Replenish amount should be lesser than fund and balance difference amount!")
            move_line1_vals = {
                'name': record.fund_id.name,
                'debit': record.replenish_amount,
                'credit': 0.0,
                'account_id': record.fund_id.journal.default_account_id.id,
                'journal_id': record.fund_id.journal.id,
                'partner_id': record.fund_id.custodian_partner.id,
                'date_maturity': record.effective_date,
            }

            # Create the second line
            move_line2_vals = {
                'name': record.fund_id.name,
                'debit': 0.0,
                'credit': record.replenish_amount,
                'journal_id': record.fund_id.journal.id,
                'account_id': record.replenish_account_id.id,
                'partner_id': record.fund_id.custodian_partner.id,
                'date_maturity': record.effective_date,
            }

            # Update the journal entry and post
            move_vals.update({
                'journal_id': record.fund_id.journal.id,
                'branch_id': record.fund_id.branch_id.id,
                'date': record.effective_date,
                'line_ids': [(0, 0, move_line2_vals), (0, 0, move_line1_vals)]
            })
            move = self.env['account.move'].create(move_vals)
            move.post()
            move.write({'pettycash_id': record.fund_id.id})
        return True