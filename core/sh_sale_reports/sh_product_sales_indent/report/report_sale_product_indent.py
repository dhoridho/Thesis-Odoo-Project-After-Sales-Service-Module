# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import api, models, fields
import pytz
from datetime import datetime,timedelta


class SaleProductIndent(models.AbstractModel):
    _name = 'report.sh_sale_reports.sh_sale_product_indent_doc'
    _description = 'Sale product indent report abstract model'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        order_dic = {}
        categories = self.env['product.category'].sudo().browse(
            data.get('sh_category_ids', False))
        partners = self.env['res.partner'].sudo().browse(
            data.get('sh_partner_ids', False))
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
        if partners:
            for partner in partners:
                customer_list = []
                for category in categories:
                    category_dic = {}
                    category_list = []
                    products = self.env['product.product'].sudo().search(
                        [('categ_id', '=', category.id)])
                    for product in products:
                        domain = [
                            ("order_id.date_order", ">=",
                             fields.Datetime.to_string(date_start)),
                            ("order_id.date_order", "<=", fields.Datetime.to_string(date_stop)),
                            ('order_id.partner_id', '=', partner.id),
                            ('product_id', '=', product.id)
                        ]
                        if data.get('sh_status', False) == 'all':
                            domain.append(
                                ('order_id.state', 'not in', ['cancel']))
                        elif data.get('sh_status', False) == 'draft':
                            domain.append(('order_id.state', 'in', ['draft']))
                        elif data.get('sh_status', False) == 'sent':
                            domain.append(('order_id.state', 'in', ['sent']))
                        elif data.get('sh_status', False) == 'sale':
                            domain.append(('order_id.state', 'in', ['sale']))
                        elif data.get('sh_status', False) == 'done':
                            domain.append(('order_id.state', 'in', ['done']))
                        if data.get('company_ids', False):
                            domain.append(
                                ('company_id', 'in', data.get('company_ids', False)))
                        order_lines = self.env['sale.order.line'].sudo().search(
                            domain).mapped('product_uom_qty')
                        product_qty = 0.0
                        if order_lines:
                            for qty in order_lines:
                                product_qty += qty
                        product_dic = {
                            'name': product.name_get()[0][1],
                            'qty': product_qty,
                        }
                        category_list.append(product_dic)
                    category_dic.update({
                        category.display_name: category_list
                    })
                    customer_list.append(category_dic)
                order_dic.update({partner.name_get()[0][1]: customer_list})
        data.update({
            'date_start': data['sh_start_date'],
            'date_end': data['sh_end_date'],
            'order_dic': order_dic,
        })
        return data
