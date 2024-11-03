# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from datetime import datetime
import pytz
import re
import json

from odoo.addons.izi_tokopedia.objects.utils.tokopedia.order_wallet import TokopediaOrderWallet


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'tokopedia'
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
        if mp_account.marketplace == 'tokopedia':
            records = self.tokopedia_proccess_mp_statement_line(records)
            records = self.process_bank_statement_line(mp_account, records.exists())
        return records

    @api.model
    def _finish_update_records(self, records):
        records = super(AccountBankStatement, self)._finish_create_records(records)
        mp_account = self.get_mp_account_from_context()
        if mp_account.marketplace == 'tokopedia':
            records = self.tokopedia_proccess_mp_statement_line(records)
            records = self.process_bank_statement_line(mp_account, records.exists())
        return records

    def tokopedia_proccess_mp_statement_line(self, records):
        mp_account = self.get_mp_account_from_context()
        mp_account_ctx = mp_account.generate_context()
        mp_statement_line_obj = self.env['mp.statement.line'].with_context(mp_account_ctx)
        tp_account = mp_account.tokopedia_get_account()
        tp_order_wallet = TokopediaOrderWallet(tp_account, api_version="v1")
        record_ids_to_unlink = []
        for record in records:
            params = {
                'from_date': record.mp_start_date,
                'to_date': record.mp_end_date,
                'shop_id': mp_account.tp_shop_id.shop_id,
            }
            tp_wallets_raw = tp_order_wallet.get_saldo_history(**params)
            wallet_statement_config = self.env['mp.wallet.statement.label'].sudo().search(
                [('mp_account_ids', 'in', mp_account_ctx.get('mp_account_id'))])
            reconcile_label = [
                label.name for label in wallet_statement_config.line_ids if label.action_type == 'reconcile']
            if tp_wallets_raw:
                if not record.balance_end_real:
                    record.write({
                        'balance_start': tp_wallets_raw[-1]['saldo'] - tp_wallets_raw[-1]['amount'],
                    })
                record.write({
                    'wallet_raw': json.dumps(tp_wallets_raw, indent=4),
                    'balance_end_real': tp_wallets_raw[0]['saldo'],
                })
                final_wallets_raw = []
                tp_wallets_by_inv = {}
                mp_invoice_number_list = []

                # grouping saldo by invoice number
                for tp_order_wallets_raw in tp_wallets_raw:
                    mp_invoice_number = re.findall("(INV\/\d+\/\w+\/\d+)", tp_order_wallets_raw['note'])
                    # custom wallet line not mergeable
                    if tp_order_wallets_raw['type'] == 4010:
                        tp_order_wallets_raw['mergeable'] = False
                    else:
                        tp_order_wallets_raw['mergeable'] = any(
                            [tp_order_wallets_raw['type_description'].lower().find(label.lower()) >= 0 for label in reconcile_label])
                    tp_order_wallets_raw['note'] = tp_order_wallets_raw['note'] + \
                        ' : %s' % (str(tp_order_wallets_raw['amount']))
                    tp_order_wallets_raw['statement_id'] = record.id
                    if mp_invoice_number:
                        if mp_invoice_number[0] not in tp_wallets_by_inv:
                            tp_wallets_by_inv[mp_invoice_number[0]] = [tp_order_wallets_raw]
                        else:
                            tp_wallets_by_inv[mp_invoice_number[0]].append(tp_order_wallets_raw)
                        mp_invoice_number_list.append(mp_invoice_number[0])
                    else:
                        if 'other' not in tp_wallets_by_inv:
                            tp_wallets_by_inv['other'] = [tp_order_wallets_raw]
                        else:
                            tp_wallets_by_inv['other'].append(tp_order_wallets_raw)

                # fetch so dari odoo berdasarkan invoice dari wallet
                so_obj = self.env['sale.order'].search(
                    [('mp_invoice_number', 'in', mp_invoice_number_list), ('mp_account_id', '=', mp_account.id)])
                so_by_mpexid = {}
                for so in so_obj:
                    so_by_mpexid[so.mp_invoice_number] = so

                for mp_inv_nbr, result_dict_values in tp_wallets_by_inv.items():
                    # sort list of dict
                    sorted_result_dict_values = sorted(result_dict_values, key=lambda d: d["deposit_id"])
                    if mp_inv_nbr in so_by_mpexid:
                        for data in sorted_result_dict_values:
                            data['order_id'] = so_by_mpexid[mp_inv_nbr].id

                    # grouped by mergable
                    mergeable_result_dict_values = list(filter(lambda d: d["mergeable"], sorted_result_dict_values))
                    unmergeable_result_dict_values = list(
                        filter(lambda d: not d["mergeable"], sorted_result_dict_values))

                    # merging
                    merged_result_dict_value = mergeable_result_dict_values[0] if mergeable_result_dict_values else []
                    merging_result_dict_values = mergeable_result_dict_values[1:]

                    # merge amounts
                    if mergeable_result_dict_values:
                        merged_result_dict_value["amount"] += sum([val["amount"] for val in merging_result_dict_values])

                        # merge notes
                        merged_result_dict_value["custom_note"] = "\n".join(
                            [val["note"] for val in mergeable_result_dict_values])

                    # add custom_notes in unmergeable_result_dict_values
                    for umg in unmergeable_result_dict_values:
                        umg['custom_note'] = umg['note']

                    # append to new dict
                    if merged_result_dict_value:
                        final_wallets_raw.extend([merged_result_dict_value] + unmergeable_result_dict_values)
                    else:
                        final_wallets_raw.extend(unmergeable_result_dict_values)

                tp_final_wallets_raw = sorted(final_wallets_raw, key=lambda d: d["create_time"])
                wallet_by_mpexid = {}
                for wlt in record.mp_line_ids:
                    wallet_by_mpexid[wlt.tp_deposit_id] = wlt
                index = len(record.mp_line_ids) + 1
                for wallet in tp_final_wallets_raw:
                    if str(wallet['deposit_id']) in wallet_by_mpexid:
                        wallet['sequence'] = wallet_by_mpexid[str(wallet['deposit_id'])].sequence
                    else:
                        wallet['sequence'] = index
                        index += 1

                tp_data_raw, tp_data_sanitized = mp_statement_line_obj._prepare_mapping_raw_data(
                    raw_data=final_wallets_raw)

                check_existing_records_params = {
                    'identifier_field': 'tp_deposit_id',
                    'raw_data': tp_data_raw,
                    'mp_data': tp_data_sanitized,
                    'multi': isinstance(tp_data_raw, list)
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

    tp_deposit_id = fields.Char(string='Tokopedia Deposit ID')

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'tokopedia'
        mp_field_mapping = {
            'statement_id': ('statement_id', None),
            'tp_deposit_id': ('deposit_id', lambda env, r: str(r)),
            'mp_external_id': ('deposit_id', lambda env, r: str(r)),
            'payment_ref': ('type_description', None),
            'narration': ('custom_note', None),
            'amount': ('amount', None),
            'sequence': ('sequence', None),
            'order_id': ('order_id', None)
        }

        def _handle_invoice_number(env, data):
            if data:
                invoice = re.findall("(INV\/\d+\/\w+\/\d+)", data)
                if invoice:
                    return invoice[0]
            return None

        def _handle_string_to_date(env, data):
            if data:
                return datetime.strptime(data, "%Y-%m-%d %H:%M:%S")
            return None

        def _handle_string_to_datetime(env, data):
            from_tz = pytz.timezone('Asia/Jakarta')
            to_tz = pytz.timezone('UTC')
            if data:
                asia_time = datetime.strptime(data, "%Y-%m-%d %H:%M:%S")
                time_utc = from_tz.localize(asia_time).astimezone(to_tz)
                return time_utc
            return None

        mp_field_mapping.update({
            'mp_invoice_number': ('note', _handle_invoice_number),
            'mp_wallet_create_time': ('create_time', _handle_string_to_date),
            'date': ('create_time', _handle_string_to_date),
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MarketplaceStatementLine, cls)._add_rec_mp_field_mapping(mp_field_mappings)
