# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, _
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"

    origin = fields.Char('Source Origin')
    pos_branch_id = fields.Many2one('res.branch', string='Branch', readonly=1, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
    pos_session_id = fields.Many2one('pos.session', string='POS Session', readonly=1)
    pos_order_id = fields.Many2one('pos.order', 'POS Order')

    is_from_pos_receivable = fields.Boolean('Is from POS Receivable?')

    @api.model
    def create(self, vals):
        context = self._context.copy()
        if context.get('pos_session_id', None):
            vals.update({
                'pos_session_id': context.get('pos_session_id'),
                'origin': 'Point Of Sale'
            })
            session = self.env['pos.session'].sudo().browse(context.get('pos_session_id'))
            if session and session.config_id and session.config_id.pos_branch_id:
                vals.update({
                    'pos_branch_id': session.config_id.pos_branch_id.id
                })
        if not vals.get('pos_branch_id'):
            vals.update({'pos_branch_id': self.env['res.branch'].sudo().get_default_branch()})
        if not vals.get('company_id', None):
            vals.update({'company_id': self.env.user.company_id.id})
        move = super(AccountMove, self).create(vals)
        if move.pos_session_id and move.pos_session_id.config_id.analytic_account_id and move.line_ids:
            move.line_ids.write({'analytic_account_id': move.pos_session_id.config_id.analytic_account_id.id})
        return move

    def write(self, vals):
        res = super(AccountMove, self).write(vals)
        for move in self:
            if move.pos_session_id and move.pos_session_id.config_id.analytic_account_id and move.line_ids:
                move.line_ids.write({'analytic_account_id': move.pos_session_id.config_id.analytic_account_id.id})
        if vals.get('state', None) == 'posted':
            for move in self:
                _logger.info('[Move %s] posted' % move.id)
        return res

    
    def button_draft(self):
        res = super(AccountMove, self).button_draft()
        for move in self:
            for line in move.line_ids:
                line.check_reconcile_done = False
        return res

    def action_register_payment(self):
        res = super(AccountMove, self).action_register_payment()
        if len(self) == 1: # Activate POS Orders Validation
            res['context'].update({ 'is_from_pos_partner': self.is_from_pos_partner })
        return res

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    pos_branch_id = fields.Many2one(
        'res.branch',
        string='Branch',
        related='move_id.pos_branch_id',
        store=True,
        readonly=1
    )

    # TODO: why could not call create ??? If we remove comments here, pos session could not closing
    # TODO: dont reopen-comments codes
    # @api.model
    # def create(self, vals):
    #     if not vals.get('pos_branch_id'):
    #         vals.update({'pos_branch_id': self.env['res.branch'].sudo().get_default_branch()})
    #     move_line = super(AccountMoveLine, self).create(vals)
    #     return move_line

    approval_code = fields.Char('Approval Code')
    check_reconcile = fields.Html('Reconcile Check', compute='compute_reconcile_check')
    check_reconcile_done = fields.Boolean('Reconcile Check Done')
    check_reconcile_flag = fields.Boolean('Reconcile Check Flag')
    check_payment = fields.Boolean('Payment Check', default=False)

    @api.depends('check_reconcile_done', 'check_reconcile_flag')
    def compute_reconcile_check(self):
        check_true = '<span class="fa fa-check text-success" style="font-size: 20px; float: right;"/>'
        check_false = '<span class="fa fa-close text-danger" style="font-size: 20px; float: right;"/>'
        for record in self:
            record.check_reconcile = check_true if record.check_reconcile_done else check_false
