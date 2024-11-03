# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.


from odoo import api, models, fields
import operator
import pytz
from datetime import datetime,timedelta


class TopSellingProduct(models.AbstractModel):
    _name = 'report.sh_sale_reports.sh_top_selling_product_doc'
    _description = "top selling product report abstract model"

    @api.model
    def _get_report_values(self, docids, data=None):

        data = dict(data or {})

        sale_order_line_obj = self.env['sale.order.line']
        ##################################
        # for product from to
        date_start = False
        date_stop = False
        if data['date_from']:
            date_start = fields.Datetime.from_string(data['date_from'])
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if data['date_to']:
            date_stop = fields.Datetime.from_string(data['date_to'])
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)
        domain = [
            ('order_id.state', 'in', ['sale', 'done']),
        ]
        if data.get('company_ids', False):
            domain.append(('order_id.company_id', 'in',
                           data.get('company_ids', False)))
        if data.get('date_from', False):
            domain.append(('order_id.date_order', '>=', fields.Datetime.to_string(date_start)))
        if data.get('date_to', False):
            domain.append(('order_id.date_order', '<=', fields.Datetime.to_string(date_stop)))

        if data.get('team_id'):
            team_id = data.get('team_id')
            team_id = team_id[0]
            domain.append(
                ('order_id.team_id', '=', team_id)
            )

        # search order line product and add into product_qty_dictionary
        search_order_lines = sale_order_line_obj.sudo().search(domain)

        product_total_qty_dic = {}
        if search_order_lines:
            for line in search_order_lines.sorted(key=lambda o: o.product_id.id):

                if product_total_qty_dic.get(line.product_id.name, False):
                    qty = product_total_qty_dic.get(line.product_id.name)
                    qty += line.product_uom_qty
                    product_total_qty_dic.update({line.product_id.name: qty})
                else:
                    product_total_qty_dic.update(
                        {line.product_id.name: line.product_uom_qty})

        final_product_list = []
        final_product_qty_list = []
        if product_total_qty_dic:
            # sort partner dictionary by descending order
            sorted_product_total_qty_list = sorted(
                product_total_qty_dic.items(), key=operator.itemgetter(1), reverse=True)
            counter = 0

            for tuple_item in sorted_product_total_qty_list:
                if data['product_uom_qty'] != 0 and tuple_item[1] >= data['product_uom_qty']:
                    final_product_list.append(tuple_item[0])

                elif data['product_uom_qty'] == 0:
                    final_product_list.append(tuple_item[0])

                final_product_qty_list.append(tuple_item[1])
                # only show record by user limit
                counter += 1
                if counter >= data['no_of_top_item']:
                    break

        ##################################
        # for Compare product from to
        date_start = False
        date_stop = False
        if data.get('date_compare_from'):
            date_start = fields.Datetime.from_string(data.get('date_compare_from'))
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if data.get('date_compare_to'):
            date_stop = fields.Datetime.from_string(data.get('date_compare_to'))
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)
        search_order_lines = False
        domain = [
            ('order_id.state', 'in', ['sale', 'done']),
        ]
        if data.get('company_ids', False):
            domain.append(('order_id.company_id', 'in',
                           data.get('company_ids', False)))
        if data.get('date_compare_from', False):
            domain.append(('order_id.date_order', '>=',
                           fields.Datetime.to_string(date_start)))
        if data.get('date_compare_to', False):
            domain.append(('order_id.date_order', '<=',
                           fields.Datetime.to_string(date_stop)))

        if data.get('team_id'):
            team_id = data.get('team_id')
            team_id = team_id[0]
            domain.append(
                ('order_id.team_id', '=', team_id)
            )

        search_order_lines = sale_order_line_obj.sudo().search(domain)

        product_total_qty_dic = {}
        if search_order_lines:
            for line in search_order_lines.sorted(key=lambda o: o.product_id.id):

                if product_total_qty_dic.get(line.product_id.name, False):
                    qty = product_total_qty_dic.get(line.product_id.name)
                    qty += line.product_uom_qty
                    product_total_qty_dic.update({line.product_id.name: qty})
                else:
                    product_total_qty_dic.update(
                        {line.product_id.name: line.product_uom_qty})

        final_compare_product_list = []
        final_compare_product_qty_list = []
        if product_total_qty_dic:
            # sort partner dictionary by descending order
            sorted_product_total_qty_list = sorted(
                product_total_qty_dic.items(), key=operator.itemgetter(1), reverse=True)
            counter = 0

            for tuple_item in sorted_product_total_qty_list:
                if data['product_uom_qty'] != 0 and tuple_item[1] >= data['product_uom_qty']:
                    final_compare_product_list.append(tuple_item[0])

                elif data['product_uom_qty'] == 0:
                    final_compare_product_list.append(tuple_item[0])

                final_compare_product_qty_list.append(tuple_item[1])
                # only show record by user limit
                counter += 1
                if counter >= data['no_of_top_item']:
                    break

        # find lost and new partner here
        lost_product_list = []
        new_product_list = []
        if final_product_list and final_compare_product_list:
            for item in final_product_list:
                if item not in final_compare_product_list:
                    lost_product_list.append(item)

            for item in final_compare_product_list:
                if item not in final_product_list:
                    new_product_list.append(item)

        data.update({'products': final_product_list,
                     'products_qty': final_product_qty_list,
                     'compare_products': final_compare_product_list,
                     'compare_products_qty': final_compare_product_qty_list,
                     'lost_products': lost_product_list,
                     'new_products': new_product_list,
                     })
        return data
