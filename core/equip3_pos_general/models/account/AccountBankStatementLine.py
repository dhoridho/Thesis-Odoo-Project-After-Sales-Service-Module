# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountBankStatement(models.Model):
    _inherit = "account.bank.statement"

    pos_branch_id = fields.Many2one('res.branch', string='Branch', readonly=1, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])

    @api.model
    def create(self, vals):
        if not vals.get('pos_branch_id'):
            vals.update({'pos_branch_id': self.env['res.branch'].sudo().get_default_branch()})
        statement = super(AccountBankStatement, self).create(vals)
        return statement

    def write(self, vals):
        for statement in self:
            pos_session = statement.pos_session_id
            if pos_session.pos_branch_id:
                vals.update({'pos_branch_id': pos_session.pos_branch_id.id})
                self.env.cr.execute("UPDATE account_bank_statement_line SET pos_branch_id=%s WHERE statement_id=%s" % (
                    pos_session.pos_branch_id.id, statement.id))
        return super(AccountBankStatement, self).write(vals)

class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    pos_branch_id = fields.Many2one('res.branch', string='Branch', readonly=1, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
    voucher_id = fields.Many2one('pos.voucher', 'Voucher', readonly=1)
    pos_session_id = fields.Many2one('pos.session', 'POS Session')
    pos_cash_type = fields.Selection([
        ('none', 'None'),
        ('in', 'In'),
        ('out', 'Out')
    ], string='POS Cash Type', default='none')
    pos_statement_id = fields.Many2one('pos.order', string="POS statement", ondelete='cascade')

    @api.model
    def create(self, vals):
        if not vals.get('pos_branch_id'):
            vals.update({'pos_branch_id': self.env['res.branch'].sudo().get_default_branch()})
        return super(AccountBankStatementLine, self).create(vals)
