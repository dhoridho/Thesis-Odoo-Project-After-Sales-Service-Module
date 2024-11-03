# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime
import pytz
import re
import json
from datetime import datetime


from odoo.addons.izi_lazada.objects.utils.lazada.finance import LazadaFinance

from odoo.addons.izi_marketplace.objects.utils.tools import generate_id


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'lazada'
        mp_field_mapping = {
            'name': ('name', lambda env, r: str(r)),
            'date': ('date', lambda env, r: datetime.strptime(r, "%Y/%m/%d")),
            'journal_id': ('journal_id', None),
            'mp_start_date': ('mp_date_start', lambda env, r: datetime.strptime(r, "%Y/%m/%d")),
            'mp_end_date': ('mp_date_end', lambda env, r: datetime.strptime(r, "%Y/%m/%d")),
        }

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(AccountBankStatement, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def _finish_create_records(self, records):
        records = super(AccountBankStatement, self)._finish_create_records(records)
        mp_account = self.get_mp_account_from_context()
        if mp_account.marketplace == 'lazada':
            records = self.lazada_proccess_mp_statement_line(records)
            records = self.process_bank_statement_line(mp_account, records.exists())
        return records

    @api.model
    def _finish_update_records(self, records):
        records = super(AccountBankStatement, self)._finish_create_records(records)
        mp_account = self.get_mp_account_from_context()
        if mp_account.marketplace == 'lazada':
            records = self.lazada_proccess_mp_statement_line(records)
            records = self.process_bank_statement_line(mp_account, records.exists())
        return records

    def lazada_proccess_mp_statement_line(self, records):
        mp_account = self.get_mp_account_from_context()
        mp_account_ctx = mp_account.generate_context()
        record_ids_to_unlink = []
        mp_statement_line_obj = self.env['mp.statement.line'].with_context(mp_account_ctx)
        for record in records:
            if mp_account.mp_token_id.state == 'valid':
                kwargs = {'access_token':  mp_account.mp_token_id.name}
                lz_account = mp_account.lazada_get_account(host=mp_account.lz_country, **kwargs)
                lz_finance = LazadaFinance(lz_account)
                params = {
                    'from_date': record.mp_start_date,
                    'to_date': record.mp_end_date,
                }
                lz_transactions_raw = lz_finance.get_transaction_detail(**params)
                if lz_transactions_raw:
                    mp_invoice_number_list = []
                    lz_wallets_by_inv = {}

                    wallet_by_mpexid = {}
                    for wlt in record.mp_line_ids:
                        wallet_by_mpexid[wlt.mp_external_id] = wlt
                    index = len(record.mp_line_ids) + 1

                    # grouping wallet by order no > transaction_type
                    for inv in lz_transactions_raw:
                        if 'order_no' in inv and inv['order_no'] not in lz_wallets_by_inv:
                            lz_wallets_by_inv[inv['order_no']] = {inv['transaction_type']: [inv]}
                            mp_invoice_number_list.append(inv['order_no'])
                        elif 'order_no' in inv:
                            if inv['transaction_type'] in lz_wallets_by_inv[inv['order_no']]:
                                lz_wallets_by_inv[inv['order_no']][inv['transaction_type']].append(inv)
                            else:
                                lz_wallets_by_inv[inv['order_no']][inv['transaction_type']] = [inv]
                        else:
                            if 'other' not in lz_wallets_by_inv:
                                lz_wallets_by_inv['other'] = {inv['transaction_type']: [inv]}
                            else:
                                if inv['transaction_type'] in lz_wallets_by_inv['other']:
                                    lz_wallets_by_inv['other'][inv['transaction_type']].append(inv)
                                else:
                                    lz_wallets_by_inv['other'][inv['transaction_type']] = [inv]

                    # fetch so dari odoo berdasarkan invoice dari wallet
                    so_obj = self.env['sale.order'].search([('mp_invoice_number', 'in', mp_invoice_number_list)])
                    so_by_mpexid = {}
                    for so in so_obj:
                        so_by_mpexid[so.mp_invoice_number] = so

                    final_lz_wallets_by_inv = []

                    mp_so = False
                    for wallet in lz_wallets_by_inv:
                        if so_by_mpexid:
                            mp_so = so_by_mpexid[wallet]
                        for ts_type in lz_wallets_by_inv[wallet]:
                            transaction_id = generate_id(ts_type + ' - %s' % (wallet))
                            base_data = {}
                            for val in lz_wallets_by_inv[wallet][ts_type]:
                                for k, v in val.items():
                                    if k in ['amount', 'WHT_amount', 'VAT_in_amount']:
                                        str_split = v.split('.')[0]
                                        new_v = str_split.replace(',', '')
                                        if k in base_data:
                                            base_data[k] += float(new_v)
                                        else:
                                            base_data[k] = float(new_v)
                                    elif k in ['fee_name']:
                                        if k in base_data:
                                            base_data[k] += '%s - %s\n ' % (v, wallet)
                                        else:
                                            base_data[k] = '%s - %s\n ' % (v, wallet)
                                    else:
                                        base_data[k] = v

                            if transaction_id in wallet_by_mpexid:
                                base_data['sequence'] = wallet_by_mpexid[transaction_id].sequence
                            else:
                                base_data['sequence'] = index
                                index += 1

                            base_data.update({
                                'transaction_id': transaction_id,
                                'statement_id': record.id,
                                # 'reason': '%s - %s' % (ts_type, wallet),
                                'order_id': mp_so.id if mp_so else None
                            })
                            final_lz_wallets_by_inv.append(base_data)

                    # if not record.balance_end_real:
                        # record.write({
                        #     'balance_start': final_sp_order_raws[-1]['current_balance'] - final_sp_order_raws[-1]['amount'],
                        # })
                    if record.wallet_raw == '{}':
                        record.write({
                            'wallet_raw': json.dumps(final_lz_wallets_by_inv, indent=4)
                        })
                    else:
                        raw = json.loads(record.wallet_raw)
                        raw.extend(final_lz_wallets_by_inv)
                        record.write({
                            'wallet_raw': json.dumps(raw, indent=4)
                        })
                    balance_end = sum([wlt['amount'] for wlt in final_lz_wallets_by_inv])
                    record.write({
                        'balance_end_real': record.balance_start + balance_end,
                    })

                    lz_data_raw, lz_data_sanitized = mp_statement_line_obj._prepare_mapping_raw_data(
                        raw_data=final_lz_wallets_by_inv)
                    check_existing_records_params = {
                        'identifier_field': 'lz_transaction_id',
                        'raw_data': lz_data_raw,
                        'mp_data': lz_data_sanitized,
                        'multi': isinstance(lz_data_raw, list)
                    }
                    check_existing_records = mp_statement_line_obj.with_context(
                        check_move_validity=False).check_existing_records(**check_existing_records_params)
                    mp_statement_line_obj.with_context(
                        check_move_validity=False).handle_result_check_existing_records(check_existing_records)
                else:
                    if not record.mp_line_ids:
                        record_ids_to_unlink.append(record.id)

        records.filtered(lambda r: r.id in record_ids_to_unlink).unlink()
        return records


class MarketplaceStatementLine(models.Model):
    _inherit = 'mp.statement.line'

    lz_transaction_id = fields.Char(string='Lazada Transacation ID')

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'lazada'
        mp_field_mapping = {
            'statement_id': ('statement_id', None),
            'lz_transaction_id': ('transaction_id', lambda env, r: str(r)),
            'mp_external_id': ('transaction_id', lambda env, r: str(r)),
            'payment_ref': ('transaction_type', None),
            'narration': ('fee_name', None),
            'amount': ('amount', None),
            'sequence': ('sequence', None),
            'order_id': ('order_id', None)
        }

        def _convert_str_date_to_datetime(env, data):
            if data:
                return datetime.strptime(data, '%d %b %Y').strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            else:
                return None

        def _convert_str_date_to_date(env, data):
            if data:
                return datetime.strptime(data, '%d %b %Y')
            else:
                return None

        mp_field_mapping.update({
            'mp_invoice_number': ('order_no', None),
            'mp_wallet_create_time': ('create_time', _convert_str_date_to_datetime),
            'date': ('transaction_date', _convert_str_date_to_date),
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MarketplaceStatementLine, cls)._add_rec_mp_field_mapping(mp_field_mappings)
