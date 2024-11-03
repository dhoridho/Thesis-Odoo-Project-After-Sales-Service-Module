# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from odoo.exceptions import ValidationError, UserError


class AccountBankStatement(models.Model):
    _name = "account.bank.statement"
    _inherit = ['account.bank.statement', 'mp.base']

    # MP Account
    mp_account_id = fields.Many2one(required=False)
    mp_start_date = fields.Datetime(string='MP Wallet Create Date Start')
    mp_end_date = fields.Datetime(string='MP Wallet Create Date End')
    wallet_raw = fields.Text(string="Wallet Raw Data", readonly=True, required=True, default="{}")
    mp_line_ids = fields.One2many('mp.statement.line', 'statement_id', string='Marketplace Statement Lines')

    def action_view_mp_statement_line(self):
        self.ensure_one()
        action = self.env.ref('izi_marketplace.action_window_mp_statement_line').read()[0]
        action.update({
            'domain': [('statement_id', '=', self.id)]
        })
        return action

    def process_bank_statement_line(self, mp_account, records):
        mp_account_ctx = mp_account.generate_context()
        _logger = self.env['mp.base']._logger
        max_iterator = 100
        mp_account_ctx.update({
            'check_move_validity': False,
        })
        bank_statement_line_obj = self.env['account.bank.statement.line'].with_context(mp_account_ctx)
        for record in records:
            # Get Possible Ref From MP Line
            # self.env.cr.execute('''
            #     SELECT DISTINCT(payment_ref)
            #     FROM mp_statement_line
            #     WHERE statement_id = %s;
            # ''' % (str(record.id)))
            # refs = self.env.cr.dictfetchall()
            refs = list(set(record.mp_line_ids.mapped('payment_ref')))
            for ref in refs:
                # ref = ref.get('payment_ref')
                # Check Latest Bank Statement Line
                iterator = 0
                sequence = 1
                cur_bank_statement_line = False
                latest_bank_statement_line = bank_statement_line_obj.search(
                    [('statement_id', '=', record.id), ('payment_ref', '=', ref), ('move_id.state', '=', 'draft')], limit=1, order='sequence desc')
                if latest_bank_statement_line:
                    iterator = len(latest_bank_statement_line.mp_line_ids)
                    cur_bank_statement_line = latest_bank_statement_line
                    if iterator >= max_iterator:
                        sequence = latest_bank_statement_line.sequence + 1
                        cur_bank_statement_line = bank_statement_line_obj.create({
                            'statement_id': record.id,
                            'payment_ref': ref,
                            'sequence': sequence,
                            'ref': str(sequence),
                            'narration': str(sequence),
                        })
                else:
                    cur_bank_statement_line = bank_statement_line_obj.create({
                        'statement_id': record.id,
                        'payment_ref': ref,
                        'sequence': sequence,
                        'ref': str(sequence),
                        'narration': str(sequence),
                    })

                # Check MP Line
                mp_lines_to_process = record.mp_line_ids.filtered(
                    lambda r: not r.statement_line_id and r.payment_ref == ref)
                total_mp_lines_to_process = len(mp_lines_to_process)
                for i, mp_line in enumerate(mp_lines_to_process):
                    if iterator < max_iterator:
                        mp_line.write({
                            'statement_line_id': cur_bank_statement_line.id,
                        })
                        iterator += 1
                    # Compute Total Amount
                    if iterator == max_iterator or i == (total_mp_lines_to_process - 1):
                        cur_bank_statement_line.amount = sum(cur_bank_statement_line.mp_line_ids.mapped('amount'))
                        if iterator == max_iterator and i < (total_mp_lines_to_process - 1):
                            # Create New Bank Statement Line
                            iterator = 0
                            sequence += 1
                            cur_bank_statement_line = bank_statement_line_obj.create({
                                'statement_id': record.id,
                                'payment_ref': ref,
                                'sequence': sequence,
                                'ref': str(sequence),
                                'narration': str(sequence),
                            })

    def process_bank_statement_reconciliation(self):
        for bank_statement in self:
            # Check Wallet Config
            wallet_statement_label = self.env['mp.wallet.statement.label'].search(
                [('mp_account_ids', 'in', bank_statement.mp_account_id.id)], limit=1)
            wallet_line_by_label = {}
            if not wallet_statement_label:
                raise UserError('No Wallet Configuration Can Be Found For This Marketplace Account')
            for wallet_line in wallet_statement_label.line_ids:
                wallet_line_by_label[wallet_line.name] = wallet_line

            # Iterate Bank Statement Line
            for bs_line in bank_statement.line_ids:
                if bs_line.payment_ref and bs_line.payment_ref in wallet_line_by_label and not bs_line.is_reconciled:
                    action_type = wallet_line_by_label[bs_line.payment_ref].action_type
                    account = wallet_line_by_label[bs_line.payment_ref].account_id
                    # Manual Operation
                    if action_type == 'manual':
                        for aml in bs_line.line_ids:
                            if aml.account_id != aml.journal_id.default_account_id and aml.account_id != account:
                                aml.write({'account_id': account.id})
                    # Reconcile, Check The Invoices
                    if action_type == 'reconcile':
                        reconcile_vals = []
                        total_amount = 0
                        # Loop Marketplace Statement Line
                        for mp_line in bs_line.mp_line_ids:
                            if mp_line.amount == 0:
                                mp_line.valid = True
                                continue
                            # TODO: Check If This Search Is Taking Forever. Change to Query
                            account_move_line = self.env['account.move.line'].search([
                                ('reconciled', '=', False),
                                ('account_internal_type', '=', 'receivable'),
                                ('mp_invoice_number', '=', mp_line.mp_invoice_number),
                            ], limit=1)
                            if account_move_line and account_move_line.debit == mp_line.amount:
                                mp_line.valid = True
                                total_amount += account_move_line.debit
                                reconcile_vals.append({
                                    'id': account_move_line.id,
                                })
                        if reconcile_vals:
                            # Check Total Value
                            if total_amount == bs_line.amount:
                                if bs_line.move_id.state != 'posted':
                                    bs_line.move_id._post(soft=False)
                                bs_line.reconcile(reconcile_vals, to_check=False)


class AccountBankStatementLine(models.Model):
    _name = "account.bank.statement.line"
    _inherit = ['account.bank.statement.line', 'mp.base']

    mp_account_id = fields.Many2one(required=False)
    order_id = fields.Many2one('sale.order', string='Sale Order')
    mp_invoice_number = fields.Char(string='MP Invoice Number')
    mp_wallet_create_time = fields.Datetime(string='MP Wallet Create Time')
    mp_line_ids = fields.One2many('mp.statement.line', 'statement_line_id', string='Marketplace Statement Lines')


class MarketplaceStatementLine(models.Model):
    _name = 'mp.statement.line'
    _inherit = 'mp.base'

    statement_id = fields.Many2one('account.bank.statement', string='Statement')
    statement_line_id = fields.Many2one('account.bank.statement.line', string='Statement Line')
    date = fields.Date('Date', required=True)
    payment_ref = fields.Char('Label', required=True)
    narration = fields.Char('Notes')
    amount = fields.Float('Amount')
    sequence = fields.Integer('Sequence')
    order_id = fields.Many2one('sale.order', string='Sale Order')
    mp_invoice_number = fields.Char(string='MP Invoice Number')
    mp_wallet_create_time = fields.Datetime(string='MP Wallet Create Time')
    valid = fields.Boolean('Valid to Reconcile', default=False)
