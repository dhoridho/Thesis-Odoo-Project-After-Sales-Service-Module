# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import api, models, fields
import pytz
from datetime import datetime,timedelta


class PurchaseProductProfitAnalysis(models.AbstractModel):
    _name = 'report.sh_purchase_reports.sh_po_product_profit_doc'
    _description = 'Purchase Product Profit report abstract model'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        order_dic_by_vendors = {}
        order_dic_by_products = {}
        both_order_list = []
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
        if data.get('report_by') == 'vendor':
            partners = False
            if data.get('sh_partner_ids', False):
                partners = self.env['res.partner'].sudo().browse(data.get('sh_partner_ids', False))
            else:
                partners = self.env['res.partner'].sudo().search([])
            if partners:
                for partner_id in partners:
                    order_list = []
                    domain = [
                        ("date_order", ">=", fields.Datetime.to_string(date_start)),
                        ("date_order", "<=", fields.Datetime.to_string(date_stop)),
                        ("partner_id", "=", partner_id.id),
                        ('state','in',['purchase','done'])
                    ]
                    if data.get('company_ids', False):
                        domain.append(
                            ('company_id', 'in', data.get('company_ids', False)))
                    search_orders = self.env['purchase.order'].sudo().search(domain)
                    if search_orders:
                        for order in search_orders:
                            if order.order_line:
                                order_dic = {}
                                for line in order.order_line:
                                    if not line.display_type:
                                        line_dic = {
                                            'order_number': order.name,
                                            'order_date': order.date_order,
                                            'product':line.product_id.name_get()[0][1],
                                            'qty':line.product_qty,
                                            'cost':line.product_id.standard_price,
                                            'purchase_price':line.price_unit,
                                        }
                                        if order_dic.get(line.product_id.id,False):
                                            qty = order_dic.get(line.product_id.id)['qty']
                                            qty = qty + line.product_qty
                                            line_dic.update({
                                                'qty': qty,
                                                })
                                        order_dic.update({line.product_id.id: line_dic})
                                for key,value in order_dic.items():
                                    order_list.append(value)
                    order_dic_by_vendors.update({partner_id.name_get()[0][1]: order_list})
        elif data.get('report_by') == 'product':
            products = False
            if data.get('sh_product_ids', False):
                products = self.env['product.product'].sudo().browse(data.get('sh_product_ids', False))
            else:
                products = self.env['product.product'].sudo().search([])
            if products:
                for product_id in products:
                    order_list = []
                    domain = [
                        ("date_order", ">=", fields.Datetime.to_string(date_start)),
                        ("date_order", "<=", fields.Datetime.to_string(date_stop)),
                        ('state','in',['purchase','done'])
                    ]
                    if data.get('company_ids', False):
                        domain.append(
                            ('company_id', 'in', data.get('company_ids', False)))
                    search_orders = self.env['purchase.order'].sudo().search(domain)
                    if search_orders:
                        for order in search_orders:
                            if order.order_line:
                                order_dic = {}
                                for line in order.order_line.sudo().filtered(lambda x:x.product_id.id == product_id.id):
                                    if not line.display_type:
                                        line_dic = {
                                            'order_number': order.name,
                                            'order_date': order.date_order,
                                            'vendor':order.partner_id.name_get()[0][1],
                                            'qty':line.product_qty,
                                            'cost':line.product_id.standard_price,
                                            'purchase_price':line.price_unit,
                                        }
                                        if order_dic.get(line.product_id.id,False):
                                            qty = order_dic.get(line.product_id.id)['qty']
                                            qty = qty + line.product_qty
                                            line_dic.update({
                                                'qty': qty,
                                                })
                                        order_dic.update({line.product_id.id: line_dic})
                                for key,value in order_dic.items():
                                    order_list.append(value)
                    order_dic_by_products.update({product_id.name_get()[0][1]: order_list})
        elif data.get('report_by') == 'both':
            products = False
            partners = False
            if data.get('sh_product_ids', False):
                products = self.env['product.product'].sudo().browse(data.get('sh_product_ids', False))
            else:
                products = self.env['product.product'].sudo().search([])
            if data.get('sh_partner_ids', False):
                partners = self.env['res.partner'].sudo().browse(data.get('sh_partner_ids', False))
            else:
                partners = self.env['res.partner'].sudo().search([])
            domain = [
                ("date_order", ">=", fields.Datetime.to_string(date_start)),
                ("date_order", "<=", fields.Datetime.to_string(date_stop)),
                ('state','in',['purchase','done'])
            ]
            if data.get('company_ids', False):
                domain.append(
                    ('company_id', 'in', data.get('company_ids', False)))
            search_orders = self.env['purchase.order'].sudo().search(domain)
            if search_orders:
                for order in search_orders.sudo().filtered(lambda x:x.partner_id.id in partners.ids):
                    if order.order_line:
                        order_dic = {}
                        for line in order.order_line.sudo().filtered(lambda x: x.product_id.id in products.ids):
                            if not line.display_type:
                                line_dic = {
                                    'order_number': order.name,
                                    'order_date': order.date_order,
                                    'vendor':order.partner_id.name_get()[0][1],
                                    'product':line.product_id.name_get()[0][1],
                                    'qty':line.product_qty,
                                    'cost':line.product_id.standard_price,
                                    'purchase_price':line.price_unit,
                                }
                                if order_dic.get(line.product_id.id,False):
                                    qty = order_dic.get(line.product_id.id)['qty']
                                    qty = qty + line.product_qty
                                    line_dic.update({
                                        'qty': qty,
                                        })
                                order_dic.update({line.product_id.id: line_dic})
                        for key,value in order_dic.items():
                            both_order_list.append(value)
        data.update({
            'date_start': data['sh_start_date'],
            'date_end': data['sh_end_date'],
            'order_dic_by_vendors':order_dic_by_vendors,
            'order_dic_by_products':order_dic_by_products,
            'both_order_list':both_order_list,
            'report_by':data.get('report_by'),
        })
        return data
