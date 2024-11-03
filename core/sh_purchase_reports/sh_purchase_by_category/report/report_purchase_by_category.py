# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import api, models, fields
import pytz
from datetime import datetime,timedelta


class PurchaseByCategory(models.AbstractModel):
    _name = 'report.sh_purchase_reports.sh_po_by_category_doc'
    _description = 'Purchase by category report abstract model'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        purchase_order_obj = self.env["purchase.order"]
        category_order_dic = {}
        categories = False
        date_start = False
        date_stop = False
        if data['sh_start_date']:
            date_start = fields.Datetime.from_string(data['sh_start_date'])
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if data['sh_end_date']:
            date_stop = fields.Datetime.from_string(data['sh_end_date'])
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)
        if data.get('sh_category_ids', False):
            categories = self.env['product.category'].sudo().browse(
                data.get('sh_category_ids', False))
        else:
            categories = self.env['product.category'].sudo().search([])
        if categories:
            for category in categories:
                order_list = []
                domain = [
                    ("date_order", ">=", fields.Datetime.to_string(date_start)),
                    ("date_order", "<=", fields.Datetime.to_string(date_stop)),
                    ('state', 'in', ['purchase', 'done'])
                ]
                if data.get('company_ids', False):
                    domain.append(
                        ('company_id', 'in', data.get('company_ids', False)))
                search_orders = purchase_order_obj.sudo().search(domain)
                if search_orders:
                    for order in search_orders:
                        if order.order_line:
                            order_dic = {}
                            for line in order.order_line.sudo().filtered(lambda x: x.product_id.categ_id.id == category.id):
                                line_dic = {
                                    'order_number': order.name,
                                    'order_date': order.date_order,
                                    'product': line.product_id.name_get()[0][1],
                                    'qty': line.product_qty,
                                    'uom': line.product_uom.name,
                                    'purchase_price': line.price_unit,
                                    'tax': line.price_tax,
                                    'purchase_currency_id': line.currency_id.id
                                }
                                if order_dic.get(line.product_id.id, False):
                                    qty = order_dic.get(
                                        line.product_id.id)['qty']
                                    qty = qty + line.product_uom_qty
                                    tax = order_dic.get(
                                        line.product_id.id)['tax']
                                    tax = tax + line.price_tax
                                    line_dic.update({
                                        'qty': qty,
                                        'tax': tax
                                    })
                                order_dic.update(
                                    {line.product_id.id: line_dic})
                            for key, value in order_dic.items():
                                order_list.append(value)
                category_order_dic.update({category.display_name: order_list})
        data.update({
            'date_start': data['sh_start_date'],
            'date_end': data['sh_end_date'],
            'category_order_dic': category_order_dic,
        })
        return data
