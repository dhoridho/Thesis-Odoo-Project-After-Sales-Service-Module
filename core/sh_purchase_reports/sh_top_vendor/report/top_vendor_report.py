# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import api, models, fields
import operator
import pytz
from datetime import datetime, timedelta


class TopVendorsReport(models.AbstractModel):
    _name = 'report.sh_purchase_reports.sh_tv_top_vendors_doc'
    _description = "top Vendors report abstract model"

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        purchase_order_obj = self.env['purchase.order']
        currency_id = False
        basic_date_start = False
        basic_date_stop = False
        if data['date_from']:
            basic_date_start = fields.Datetime.from_string(data['date_from'])
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            basic_date_start = today.astimezone(pytz.timezone('UTC'))

        if data['date_to']:
            basic_date_stop = fields.Datetime.from_string(data['date_to'])
            # avoid a date_stop smaller than date_start
            if (basic_date_stop < basic_date_start):
                basic_date_stop = basic_date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            basic_date_stop = basic_date_start + timedelta(days=1, seconds=-1)
        ##################################
        # for partner from to
        domain = [
            ('date_order', '>=', fields.Datetime.to_string(basic_date_start)),
            ('date_order', '<=', fields.Datetime.to_string(basic_date_stop)),
            ('state', 'in', ['purchase', 'done']),
        ]
        if data.get('company_ids', False):
            domain.append(('company_id', 'in', data.get('company_ids', False)))
        purchase_orders = purchase_order_obj.sudo().search(domain)
        partner_total_amount_dic = {}
        if purchase_orders:
            for order in purchase_orders.sorted(key=lambda o: o.partner_id.id):
                if order.currency_id:
                    currency_id = order.currency_id

                if partner_total_amount_dic.get(order.partner_id.name, False):
                    amount = partner_total_amount_dic.get(
                        order.partner_id.name)
                    amount += order.amount_total
                    partner_total_amount_dic.update(
                        {order.partner_id.name: amount})
                else:
                    partner_total_amount_dic.update(
                        {order.partner_id.name: order.amount_total})

        final_partner_list = []
        final_partner_amount_list = []
        if partner_total_amount_dic:
            # sort partner dictionary by descending order
            sorted_partner_total_amount_list = sorted(
                partner_total_amount_dic.items(), key=operator.itemgetter(1), reverse=True)
            counter = 0

            for tuple_item in sorted_partner_total_amount_list:
                if data['amount_total'] != 0 and tuple_item[1] >= data['amount_total']:
                    final_partner_list.append(tuple_item[0])
                elif data['amount_total'] == 0:
                    final_partner_list.append(tuple_item[0])

                final_partner_amount_list.append(tuple_item[1])
                # only show record by user limit
                counter += 1
                if counter >= data['no_of_top_item']:
                    break

        ##################################
        # for Compare partner from to
        compare_date_start = False
        compare_date_stop = False
        if data['date_compare_from']:
            compare_date_start = fields.Datetime.from_string(data['date_compare_from'])
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            compare_date_start = today.astimezone(pytz.timezone('UTC'))

        if data['date_compare_to']:
            compare_date_stop = fields.Datetime.from_string(data['date_compare_to'])
            # avoid a date_stop smaller than date_start
            if (compare_date_stop < compare_date_start):
                compare_date_stop = compare_date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            compare_date_stop = compare_date_start + timedelta(days=1, seconds=-1)
        purchase_orders = False
        domain = [
            ('date_order', '>=', fields.Datetime.to_string(compare_date_start)),
            ('date_order', '<=', fields.Datetime.to_string(compare_date_stop)),
            ('state', 'in', ['purchase', 'done']),
        ]
        if data.get('company_ids', False):
            domain.append(('company_id', 'in', data.get('company_ids', False)))

        purchase_orders = purchase_order_obj.sudo().search(domain)

        partner_total_amount_dic = {}
        if purchase_orders:
            for order in purchase_orders.sorted(key=lambda o: o.partner_id.id):
                if order.currency_id:
                    currency_id = order.currency_id

                if partner_total_amount_dic.get(order.partner_id.name, False):
                    amount = partner_total_amount_dic.get(
                        order.partner_id.name)
                    amount += order.amount_total
                    partner_total_amount_dic.update(
                        {order.partner_id.name: amount})
                else:
                    partner_total_amount_dic.update(
                        {order.partner_id.name: order.amount_total})

        final_compare_partner_list = []
        final_compare_partner_amount_list = []
        if partner_total_amount_dic:
            # sort compare partner dictionary by descending order
            sorted_partner_total_amount_list = sorted(
                partner_total_amount_dic.items(), key=operator.itemgetter(1), reverse=True)

            counter = 0
            for tuple_item in sorted_partner_total_amount_list:
                if data['amount_total'] != 0 and tuple_item[1] >= data['amount_total']:
                    final_compare_partner_list.append(tuple_item[0])

                elif data['amount_total'] == 0:
                    final_compare_partner_list.append(tuple_item[0])

                final_compare_partner_amount_list.append(tuple_item[1])
                # only show record by user limit
                counter += 1
                if counter >= data['no_of_top_item']:
                    break

        # find lost and new partner here
        lost_partner_list = []
        new_partner_list = []
        if final_partner_list and final_compare_partner_list:
            for item in final_partner_list:
                if item not in final_compare_partner_list:
                    lost_partner_list.append(item)

            for item in final_compare_partner_list:
                if item not in final_partner_list:
                    new_partner_list.append(item)

#       finally update data dictionary
        if not currency_id:
            self.env.user.company_id.sudo().currency_id

        data.update({'partners': final_partner_list,
                     'partners_amount': final_partner_amount_list,
                     'compare_partners': final_compare_partner_list,
                     'compare_partners_amount': final_compare_partner_amount_list,
                     'lost_partners': lost_partner_list,
                     'new_partners': new_partner_list,
                     'currency': currency_id,
                     })
        return data
