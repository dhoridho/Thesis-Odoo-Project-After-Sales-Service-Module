# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class AccountPayment(models.Model):
    _inherit = "account.payment"

    origin = fields.Char('Source Origin', readonly=1)
    pos_branch_id = fields.Many2one('res.branch', string='Branch', readonly=1, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
    pos_session_id = fields.Many2one('pos.session', string='POS Session', readonly=1)
    available_partner_bank_ids = fields.Many2many('res.partner.bank', string='Available Partner Banks')

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
        payment = super(AccountPayment, self).create(vals)
        return payment
    

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    available_partner_bank_ids = fields.Many2many('res.partner.bank', string='Available Partner Banks')
