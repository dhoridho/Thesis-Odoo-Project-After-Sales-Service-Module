# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from tabnanny import check
from odoo import api, fields, models
from odoo.exceptions import ValidationError
import json
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime, timedelta
import time
import hashlib
import pytz

from odoo.addons.izi_tiktok.models.utils.order_wallet import TiktokOrderWallet
from odoo.addons.izi_marketplace.objects.utils.tools import generate_id


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'tiktok'
        mp_field_mapping = {
            'name': ('name', lambda env, r: str(r)),
            'date': ('date', lambda env, r: datetime.strptime(r, "%Y/%m/%d")),
            'journal_id': ('journal_id', None),
            'mp_start_date': ('mp_date_start', lambda env, r: datetime.strptime(r, "%Y/%m/%d %H:%M:%S")),
            'mp_end_date': ('mp_date_end', lambda env, r: datetime.strptime(r, "%Y/%m/%d %H:%M:%S")),
        }

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(AccountBankStatement, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def _finish_create_records(self, records):
        records = super(AccountBankStatement, self)._finish_create_records(records)
        mp_account = self.get_mp_account_from_context()
        if mp_account.marketplace == 'tiktok':
            records = self.tiktok_process_mp_statement_line(mp_account, records)
            records = self.process_bank_statement_line(mp_account, records.exists())
        return records

    @api.model
    def _finish_update_records(self, records):
        records = super(AccountBankStatement, self)._finish_update_records(records)
        mp_account = self.get_mp_account_from_context()
        if mp_account.marketplace == 'tiktok':
            records = self.tiktok_process_mp_statement_line(mp_account, records)
            records = self.process_bank_statement_line(mp_account, records.exists())
        return records

    def tiktok_process_mp_statement_line(self, mp_account, records):
        record_ids_to_unlink = []
        mp_account_ctx = mp_account.generate_context()
        _logger = self.env['mp.base']._logger
        mp_statement_line_obj = self.env['mp.statement.line'].with_context(mp_account_ctx)
        for record in records:
            if mp_account.mp_token_id.state == 'valid':
                account_params = {'access_token': mp_account.mp_token_id.name}
                tts_account = mp_account.tiktok_get_account(**account_params)
                tts_order_wallet = TiktokOrderWallet(tts_account)
                params = {
                    'from_date': record.mp_start_date,
                    'to_date': record.mp_end_date,
                    # 'limit': mp_account_ctx.get('order_limit'),
                }
                tts_order_wallet_list = tts_order_wallet.get_finance_settlements_list(**params)
                final_tts_order_raws = []
                api_tz = pytz.timezone('UTC')
                as_tz = pytz.timezone(mp_account_ctx.get('timezone'))
                data_utc = datetime.strftime(datetime.now().astimezone(api_tz), '%d/%m/%Y %H:%M:%S')
                date_gmt = datetime.strftime(datetime.now().astimezone(as_tz), '%d/%m/%Y %H:%M:%S')
                if tts_order_wallet_list:
                    for raw in tts_order_wallet_list:
                        time_in_utc = datetime.fromtimestamp(time.mktime(time.gmtime(raw['create_time'])))
                        time_in_tz = time_in_utc + timedelta(hours=7)
                        wallet_raw_date = time_in_tz.date()
                        # wallet_raw_date = time_in_utc.date()
                        if wallet_raw_date == record.date:
                            final_tts_order_raws.append(raw)
                    if final_tts_order_raws:
                        if not record.balance_end_real:
                            record.write({
                                'balance_start': final_tts_order_raws[-1]['current_balance'] - final_tts_order_raws[-1]['amount'],
                            })
                        if record.wallet_raw == '{}':
                            record.write({
                                'wallet_raw': json.dumps(final_tts_order_raws, indent=4)
                            })
                        else:
                            raw = json.loads(record.wallet_raw)
                            raw.extend(final_tts_order_raws)
                            record.write({
                                'wallet_raw': json.dumps(raw, indent=4)
                            })
                        record.write({
                            'balance_end_real': final_tts_order_raws[0]['current_balance'],
                        })

                        final_wallets_raw = []
                        invoice_wallet = list(
                            filter(lambda d: len(d["order_sn"]) > 0, final_tts_order_raws))
                        non_invoice_wallet = list(
                            filter(lambda d: len(d["order_sn"]) == 0, final_tts_order_raws))

                        mp_invoice_number_list = []
                        tts_wallets_by_inv = {}
                        for inv in invoice_wallet:
                            tts_wallets_by_inv[inv['order_sn']] = inv
                            mp_invoice_number_list.append(inv['order_sn'])

                        # fetch so dari odoo berdasarkan invoice dari wallet
                        so_obj = self.env['sale.order'].search([('mp_invoice_number', 'in', mp_invoice_number_list)])
                        so_by_mpexid = {}
                        for so in so_obj:
                            so_by_mpexid[so.mp_invoice_number] = so

                        for i, mp_invoice_number in enumerate(mp_invoice_number_list):
                            # _logger(mp_account.marketplace, '(%s/%s) PROCESSING ORDER WALLET : %s' % (i, len(mp_invoice_number_list), mp_invoice_number),
                            #         notify=False,
                            #         notif_sticky=False)
                            mp_so = False
                            statement_line_by_invoice_number = []
                            order_income = False
                            check_delivery = False
                            # cek so tiktok yang ada di odoo
                            if mp_invoice_number in so_by_mpexid:
                                mp_so = so_by_mpexid[mp_invoice_number]
                                tts_order_raw = json.loads(mp_so.raw, strict=False)
                                order_income = tts_order_raw['order_income']
                                check_delivery = True if 'delivery' in mp_so.mapped('order_line.product_type') else False

                            if order_income:
                                # create income wallet
                                income_string = 'Hasil Penjualan Produk'
                                cost_off_gold_sold = order_income.get('sales_fee', 0)
                                tiktok_discount = order_income.get('platform_promotion', 0)
                                if cost_off_gold_sold == 0:
                                    cost_off_gold_sold = order_income.get('transaction_fee')
                                wallet_vals = {
                                    'transaction_id': generate_id(income_string + ' - %s' % (mp_invoice_number)),
                                    'transaction_type': income_string,
                                    'reason': income_string + ' - %s' % (mp_invoice_number),
                                    'statement_id': record.id,
                                    'amount': cost_off_gold_sold, ###-tiktok_discount,
                                    'order_sn': mp_invoice_number,
                                    'create_time': tts_wallets_by_inv[mp_invoice_number]['create_time'],
                                    'order_id': mp_so.id if mp_so else None
                                }
                                if check_delivery:
                                    wallet_vals['amount'] = wallet_vals['amount'] + \
                                        order_income.get('shipping_fee_adjustment')
                                statement_line_by_invoice_number.append(wallet_vals)

                                # create comission fee wallet
                                commission_string = 'Biaya Komisi Marketplace'
                                commission_fee = -order_income.get('platform_commission')
                                commission_vals = {
                                    'transaction_id': generate_id(commission_string + ' - %s' % (mp_invoice_number)),
                                    'transaction_type': commission_string,
                                    'reason': commission_string + ' - %s' % (mp_invoice_number),
                                    'statement_id': record.id,
                                    'amount': commission_fee,
                                    'order_sn': mp_invoice_number,
                                    'create_time': tts_wallets_by_inv[mp_invoice_number]['create_time'],
                                    'order_id': mp_so.id if mp_so else None
                                }
                                statement_line_by_invoice_number.append(commission_vals)

                                # create service fee wallet
                                servicefee_string = 'Biaya Service Marketplace'
                                servicefee_vals = {
                                    'transaction_id': generate_id(servicefee_string + ' - %s' % (mp_invoice_number)),
                                    'transaction_type': servicefee_string,
                                    'statement_id': record.id,
                                    'reason': '',
                                    'amount': 0,
                                    'order_sn': mp_invoice_number,
                                    'create_time': tts_wallets_by_inv[mp_invoice_number]['create_time'],
                                    'order_id': mp_so.id if mp_so else None
                                }
                                service_fee_list = order_income.get('transaction_fee')
                                if service_fee_list:
                                    servicefee_vals['reason'] = "\n".join([svc['fee_name'] + ' - %s' % (mp_invoice_number)
                                                                          for svc in service_fee_list])
                                    servicefee_vals['amount'] += sum([-svc['fee_amount'] for svc in service_fee_list])
                                    statement_line_by_invoice_number.append(servicefee_vals)

                                # create discount Shipping wallet
                                delivery_fee_discount = order_income.get('shipping_fee_subsidy', 0) #+ \
                                    # order_income.get('shipping_fee_discount_from_3pl', 0) + \
                                    # order_income.get('tiktok_shipping_rebate', 0) + \
                                    # (-order_income.get('actual_shipping_fee', 0)) + \
                                    # (order_income.get('reverse_shipping_fee', 0))

                                if delivery_fee_discount:
                                    delivery_string = 'Pendapatan dari Ekspedisi'
                                    delivery_fee_vals = {
                                        'transaction_id': generate_id(delivery_string + ' - %s' % (mp_invoice_number)),
                                        'transaction_type': delivery_string,
                                        'reason': delivery_string + ' - %s' % (mp_invoice_number),
                                        'statement_id': record.id,
                                        'amount': delivery_fee_discount,
                                        'order_sn': mp_invoice_number,
                                        'create_time': tts_wallets_by_inv[mp_invoice_number]['create_time'],
                                        'order_id': mp_so.id if mp_so else None
                                    }
                                    statement_line_by_invoice_number.append(delivery_fee_vals)

                                # create vocuher from seller
                                voucher_seller = (-order_income.get('promotion_adjustment', 0)) #+ \
                                    # (-order_income.get('seller_coin_cash_back',))
                                if voucher_seller:
                                    voucher_string = 'Voucher dari Seller'
                                    voucher_fee_vals = {
                                        'transaction_id': generate_id(voucher_string + ' - %s' % (mp_invoice_number)),
                                        'transaction_type': voucher_string,
                                        'reason': voucher_string + ' - %s' % (mp_invoice_number),
                                        'statement_id': record.id,
                                        'amount': voucher_seller,
                                        'order_sn': mp_invoice_number,
                                        'create_time': tts_wallets_by_inv[mp_invoice_number]['create_time'],
                                        'order_id': mp_so.id if mp_so else None
                                    }
                                    statement_line_by_invoice_number.append(voucher_fee_vals)

                                escrow_amount = tts_wallets_by_inv[mp_invoice_number]['amount']
                                total_amount = sum([stl['amount'] for stl in statement_line_by_invoice_number])
                                if total_amount == escrow_amount:
                                    statement_line_by_invoice_number[0]['reason'] = income_string + \
                                        ' - %s ( Match )' % (mp_invoice_number)
                                else:
                                    diff_amount = escrow_amount-total_amount
                                    if tiktok_discount and abs(diff_amount) == tiktok_discount:
                                        statement_line_by_invoice_number[0]['reason'] = income_string + \
                                            ' - %s (Match)' % (mp_invoice_number)
                                        difference_total = 'Tiktok Discount'
                                        difference_total_vals = {
                                            'transaction_id': generate_id(difference_total + ' - %s' % (mp_invoice_number)),
                                            'transaction_type': difference_total,
                                            'reason': difference_total + ' - %s' % (mp_invoice_number),
                                            'statement_id': record.id,
                                            'amount': tiktok_discount,
                                            'order_sn': mp_invoice_number,
                                            'create_time': tts_wallets_by_inv[mp_invoice_number]['create_time'],
                                            'order_id': mp_so.id if mp_so else None
                                        }
                                    else:
                                        statement_line_by_invoice_number[0]['reason'] = income_string + \
                                            ' - %s (Dont Match)' % (mp_invoice_number)
                                        difference_total = 'Total Selisih'
                                        difference_total_vals = {
                                            'transaction_id': generate_id(difference_total + ' - %s' % (mp_invoice_number)),
                                            'transaction_type': difference_total,
                                            'reason': difference_total + ' - %s' % (mp_invoice_number),
                                            'statement_id': record.id,
                                            'amount': diff_amount,
                                            'order_sn': mp_invoice_number,
                                            'create_time': tts_wallets_by_inv[mp_invoice_number]['create_time'],
                                            'order_id': mp_so.id if mp_so else None
                                        }
                                    statement_line_by_invoice_number.append(difference_total_vals)

                                final_wallets_raw.extend(statement_line_by_invoice_number)
                        tts_non_invoice_wallet = [
                            # Insert statement_id into tts_order_wallet_list
                            dict(tts_data_wallets_raw,
                                 **dict([('statement_id', record.id)]))
                            for tts_data_wallets_raw in non_invoice_wallet
                        ]
                        final_wallets_raw.extend(tts_non_invoice_wallet)
                        sorted_result_dict_values = sorted(final_wallets_raw, key=lambda d: d["create_time"])
                        wallet_by_mpexid = {}
                        for wlt in record.mp_line_ids:
                            wallet_by_mpexid[wlt.mp_external_id] = wlt
                        index = len(record.mp_line_ids) + 1
                        for wallet in sorted_result_dict_values:
                            if wallet['transaction_id'] in wallet_by_mpexid:
                                wallet['sequence'] = wallet_by_mpexid[wallet['transaction_id']].sequence
                            else:
                                wallet['sequence'] = index
                                index += 1
                        tts_data_raw, tts_data_sanitized = mp_statement_line_obj._prepare_mapping_raw_data(
                            raw_data=final_wallets_raw)
                        check_existing_records_params = {
                            'identifier_field': 'tts_transaction_id',
                            'raw_data': tts_data_raw,
                            'mp_data': tts_data_sanitized,
                            'multi': isinstance(tts_data_raw, list)
                        }
                        check_existing_records = mp_statement_line_obj.with_context(
                            check_move_validity=False).check_existing_records(**check_existing_records_params)
                        mp_statement_line_obj.with_context(
                            check_move_validity=False).handle_result_check_existing_records(check_existing_records)
                    else:
                        if not record.mp_line_ids:
                            record_ids_to_unlink.append(record.id)
                else:
                    if not record.mp_line_ids:
                        record_ids_to_unlink.append(record.id)
            else:
                if not record.mp_line_ids:
                    record_ids_to_unlink.append(record.id)
                raise ValidationError('Your token was expired or invalid. Please reauthenticated or refresh token.')
        records.filtered(lambda r: r.id in record_ids_to_unlink).unlink()
        return records


class MarketplaceStatementLine(models.Model):
    _inherit = 'mp.statement.line'

    tts_transaction_id = fields.Char(string='Tiktok Transacation ID')

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'tiktok'
        mp_field_mapping = {
            'statement_id': ('statement_id', None),
            'tts_transaction_id': ('transaction_id', lambda env, r: str(r)),
            'mp_external_id': ('transaction_id', lambda env, r: str(r)),
            'payment_ref': ('transaction_type', None),
            'narration': ('reason', None),
            'amount': ('amount', None),
            'sequence': ('sequence', None),
            'order_id': ('order_id', None)
        }

        def _convert_timestamp_to_datetime(env, data):
            if data:
                return datetime.fromtimestamp(time.mktime(time.gmtime(data))).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            else:
                return None

        def _convert_timestamp_to_date(env, data):
            if data:
                timezone = env.context.get('timezone')
                return datetime.fromtimestamp(data, tz=pytz.timezone(timezone)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            else:
                return None

        mp_field_mapping.update({
            'mp_invoice_number': ('order_sn', None),
            'mp_wallet_create_time': ('create_time', _convert_timestamp_to_datetime),
            'date': ('create_time', _convert_timestamp_to_date),
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MarketplaceStatementLine, cls)._add_rec_mp_field_mapping(mp_field_mappings)
