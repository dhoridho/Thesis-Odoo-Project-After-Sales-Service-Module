# -*- coding: utf-8 -*-

from odoo import fields, models, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    is_from_pos_umum = fields.Boolean('Is from POS Umum?')
    is_from_pos_member = fields.Boolean('Is from POS Member?')
    is_from_pos_member_gabungan = fields.Boolean('Is from POS Member Gabungan?')
    is_from_pos_partner = fields.Boolean('Is from POS Partner?')
    is_pkp_record = fields.Boolean('Is PKP',default=False)
    deposit_account_journal_id = fields.Many2one('account.journal', string='Deposit Payment Method')
    create_from_session_id = fields.Many2one('pos.session', string='Create from POS Session', 
        help='When Create member Deposit from POS Frontend, store pos session info')

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []

        # TODO: hide pos invoice from Accounting Menu
        hide_invoice = self._context.get('hide_invoice_from_pos')
        if hide_invoice is True :
            domain += [('is_from_pos_umum','=',False), ('is_from_pos_member','=',False), 
                        ('is_from_pos_member_gabungan','=',False), ('is_from_pos_partner','=',False)]
        if hide_invoice == 'from_pos_umum':
            domain += [('is_from_pos_umum','=',False)]

        return super(AccountMove, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'


    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        
        # TODO: hide pos invoice from Accounting Menu
        hide_invoice = self._context.get('hide_invoice_from_pos')
        if hide_invoice == 'from_pos_umum':
            domain += [('move_id.is_from_pos_umum','=',False)]
                        
        return super(AccountMoveLine, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)