# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api, _, tools
from odoo.exceptions import ValidationError
import xlwt
import operator
import base64
from io import BytesIO
import pytz
from datetime import datetime, timedelta
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import float_is_zero

class PurchaseProductProfitWizard(models.TransientModel):
    _inherit = 'sh.purchase.product.profit.wizard'

    branch_ids = fields.Many2many('res.branch', domain="[('company_id', 'in', company_ids)]")

    def print_xls_report(self):
        workbook = xlwt.Workbook(encoding='utf-8')
        heading_format = xlwt.easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = xlwt.easyxf(
            'font:bold True,height 215;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold_center = xlwt.easyxf(
            'align: horiz center;font:bold True')
        worksheet = workbook.add_sheet(
            'Purchase Product Profit', bold_center)
        left = xlwt.easyxf('align: horiz center;font:bold True')
        center = xlwt.easyxf('align: horiz center;')
        bold_center_total = xlwt.easyxf('align: horiz center;font:bold True')
        order_dic_by_vendors = {}
        order_dic_by_products = {}
        both_order_list = []
        date_start = False
        date_stop = False
        if self.sh_start_date:
            date_start = fields.Datetime.from_string(self.sh_start_date)
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if self.sh_end_date:
            date_stop = fields.Datetime.from_string(self.sh_end_date)
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)
        user_tz = self.env.user.tz or pytz.utc
        local = pytz.timezone(user_tz)
        start_date = datetime.strftime(pytz.utc.localize(datetime.strptime(str(self.sh_start_date),
        DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT)
        end_date = datetime.strftime(pytz.utc.localize(datetime.strptime(str(self.sh_end_date),
        DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT)
        if self.report_by == 'vendor':
            partners = False
            if self.sh_partner_ids:
                partners = self.sh_partner_ids
            else:
                partners = self.env['res.partner'].sudo().search([])
            if partners:
                for partner_id in partners:
                    order_list = []
                    domain = [
                        ("date_order", ">=", fields.Datetime.to_string(date_start)),
                        ("date_order", "<=", fields.Datetime.to_string(date_stop)),
                        ("partner_id", "=", partner_id.id),
                        ('state', 'in', ['purchase', 'done'])
                    ]
                    if self.company_ids:
                        domain.append(
                            ('company_id', 'in', self.company_ids.ids))
                    if self.branch_ids:
                        domain.append(
                            ('branch_id', 'in', self.branch_ids.ids))
                    search_orders = self.env['purchase.order'].sudo().search(
                        domain)
                    if search_orders:
                        for order in search_orders:
                            if order.order_line:
                                order_dic = {}
                                for line in order.order_line:
                                    if not line.display_type:
                                        line_dic = {
                                            'order_number': order.name,
                                            'order_date': order.date_order.date(),
                                            'product': line.product_id.name_get()[0][1],
                                            'qty': line.product_qty,
                                            'cost': line.product_id.standard_price,
                                            'purchase_price': line.price_unit,
                                        }
                                        if order_dic.get(line.product_id.id, False):
                                            qty = order_dic.get(
                                                line.product_id.id)['qty']
                                            qty = qty + line.product_qty
                                            line_dic.update({
                                                'qty': qty,
                                            })
                                        order_dic.update(
                                            {line.product_id.id: line_dic})
                                for key, value in order_dic.items():
                                    order_list.append(value)
                    order_dic_by_vendors.update(
                        {partner_id.name_get()[0][1]: order_list})
        elif self.report_by == 'product':
            products = False
            if self.sh_product_ids:
                products = self.sh_product_ids
            else:
                products = self.env['product.product'].sudo().search([])
            if products:
                for product_id in products:
                    order_list = []
                    domain = [
                        ("date_order", ">=", fields.Datetime.to_string(date_start)),
                        ("date_order", "<=", fields.Datetime.to_string(date_stop)),
                        ('state', 'in', ['purchase', 'done'])
                    ]
                    if self.company_ids:
                        domain.append(
                            ('company_id', 'in', self.company_ids.ids))
                    if self.branch_ids:
                        domain.append(
                            ('branch_id', 'in', self.branch_ids.ids))
                    search_orders = self.env['purchase.order'].sudo().search(
                        domain)
                    if search_orders:
                        for order in search_orders:
                            if order.order_line:
                                order_dic = {}
                                for line in order.order_line.sudo().filtered(lambda x: x.product_id.id == product_id.id):
                                    if not line.display_type:
                                        line_dic = {
                                            'order_number': order.name,
                                            'order_date': order.date_order.date(),
                                            'vendor': order.partner_id.name_get()[0][1],
                                            'qty': line.product_qty,
                                            'cost': line.product_id.standard_price,
                                            'purchase_price': line.price_unit,
                                        }
                                        if order_dic.get(line.product_id.id, False):
                                            qty = order_dic.get(
                                                line.product_id.id)['qty']
                                            qty = qty + line.product_qty
                                            line_dic.update({
                                                'qty': qty,
                                            })
                                        order_dic.update(
                                            {line.product_id.id: line_dic})
                                for key, value in order_dic.items():
                                    order_list.append(value)
                    order_dic_by_products.update(
                        {product_id.name_get()[0][1]: order_list})
        elif self.report_by == 'both':
            products = False
            partners = False
            if self.sh_product_ids:
                products = self.sh_product_ids
            else:
                products = self.env['product.product'].sudo().search([])
            if self.sh_partner_ids:
                partners = self.sh_partner_ids
            else:
                partners = self.env['res.partner'].sudo().search([])
            domain = [
                ("date_order", ">=", fields.Datetime.to_string(date_start)),
                ("date_order", "<=", fields.Datetime.to_string(date_stop)),
                ('state', 'in', ['purchase', 'done'])
            ]
            if self.company_ids:
                domain.append(
                    ('company_id', 'in', self.company_ids.ids))
            if self.branch_ids:
                domain.append(
                    ('branch_id', 'in', self.branch_ids.ids))
            search_orders = self.env['purchase.order'].sudo().search(domain)
            if search_orders:
                for order in search_orders.sudo().filtered(lambda x: x.partner_id.id in partners.ids):
                    if order.order_line:
                        order_dic = {}
                        for line in order.order_line.sudo().filtered(lambda x: x.product_id.id in products.ids):
                            if not line.display_type:
                                line_dic = {
                                    'order_number': order.name,
                                    'order_date': order.date_order.date(),
                                    'vendor': order.partner_id.name_get()[0][1],
                                    'product': line.product_id.name_get()[0][1],
                                    'qty': line.product_qty,
                                    'cost': line.product_id.standard_price,
                                    'purchase_price': line.price_unit,
                                }
                                if order_dic.get(line.product_id.id, False):
                                    qty = order_dic.get(line.product_id.id)['qty']
                                    qty = qty + line.product_qty
                                    line_dic.update({
                                        'qty': qty,
                                    })
                                order_dic.update({line.product_id.id: line_dic})
                        for key, value in order_dic.items():
                            both_order_list.append(value)
        worksheet.col(0).width = int(30 * 260)
        worksheet.col(1).width = int(30 * 260)
        worksheet.col(2).width = int(60 * 260)
        worksheet.col(3).width = int(18 * 260)
        worksheet.col(4).width = int(33 * 260)
        worksheet.col(5).width = int(15 * 260)
        worksheet.col(6).width = int(15 * 260)
        worksheet.col(7).width = int(15 * 260)
        worksheet.col(8).width = int(15 * 260)
        row = 4
        if self.report_by == 'vendor':
            worksheet.write_merge(
                0, 1, 0, 7, 'Purchase Product Profit', heading_format)
            worksheet.write_merge(2, 2, 0, 7, start_date + " to " + end_date, bold)
            if order_dic_by_vendors:
                for vendor in order_dic_by_vendors.keys():
                    worksheet.write_merge(
                        row, row, 0, 7, vendor, bold)
                    row = row + 2
                    total_cost = 0.0
                    total_purchase_price = 0.0
                    total_profit = 0.0
                    total_margin = 0.0
                    worksheet.write(row, 0, "Order Number", bold_center)
                    worksheet.write(row, 1, "Order Date", bold_center)
                    worksheet.write(row, 2, "Product", bold_center)
                    worksheet.write(row, 3, "Quantity", bold_center)
                    worksheet.write(row, 4, "Cost", bold_center)
                    worksheet.write(row, 5, "Purchase Price", bold_center)
                    worksheet.write(row, 6, "Profit", bold_center)
                    worksheet.write(row, 7, "Margin(%)", bold_center)
                    row = row + 1
                    for order in order_dic_by_vendors[vendor]:
                        cost = order.get('cost', 0.0) * order.get('qty', 0.0)
                        purchase_price = (
                            order.get('purchase_price', 0.0)*order.get('qty', 0.0))
                        profit = (order.get('purchase_price', 0.0)*order.get('qty', 0.0)
                                  ) - (order.get('cost', 0.0)*order.get('qty', 0.0))
                        if purchase_price == 0:
                            purchase_price = 1
                        margin = (profit / purchase_price) * 100
                        worksheet.write(row, 0, order.get(
                            'order_number', ''), center)
                        worksheet.write(row, 1, str(
                            order.get('order_date', '')), center)
                        worksheet.write(row, 2, order.get(
                            'product', ''), center)
                        worksheet.write(row, 3, order.get('qty', 0.0), center)
                        worksheet.write(row, 4, "{:.2f}".format(cost), center)
                        worksheet.write(row, 5, "{:.2f}".format(purchase_price), center)
                        worksheet.write(row, 6, "{:.2f}".format(profit), center)
                        worksheet.write(row, 7, "{:.2f}".format(margin), center)
                        total_cost = total_cost + cost
                        total_purchase_price=total_purchase_price+purchase_price
                        total_profit=total_profit+profit
                        total_margin=total_margin+margin
                        row = row + 1
                        worksheet.write(row, 3, "Total", left)
                        worksheet.write(row, 4, "{:.2f}".format(
                            total_cost), bold_center_total)
                        worksheet.write(
                            row, 5, "{:.2f}".format(
                                total_purchase_price), bold_center_total)
                        worksheet.write(row, 6, "{:.2f}".format(total_profit),
                                        bold_center_total)
                        worksheet.write(row, 7, "{:.2f}".format(total_margin),
                                        bold_center_total)
                    row=row+2

        elif self.report_by == 'product':
            worksheet.write_merge(
                0, 1, 0, 7, 'Purchase Product Profit', heading_format)
            worksheet.write_merge(2, 2, 0, 7, start_date + " to " + end_date, bold)
            if order_dic_by_products:
                for product in order_dic_by_products.keys():
                    worksheet.write_merge(
                        row, row, 0, 7, product, bold)
                    row = row + 2
                    total_cost = 0.0
                    total_purchase_price = 0.0
                    total_profit = 0.0
                    total_margin = 0.0
                    worksheet.write(row, 0, "Order Number", bold_center)
                    worksheet.write(row, 1, "Order Date", bold_center)
                    worksheet.write(row, 2, "Vendor", bold_center)
                    worksheet.write(row, 3, "Quantity", bold_center)
                    worksheet.write(row, 4, "Cost", bold_center)
                    worksheet.write(row, 5, "Purchase Price", bold_center)
                    worksheet.write(row, 6, "Profit", bold_center)
                    worksheet.write(row, 7, "Margin(%)", bold_center)
                    row = row + 1
                    for order in order_dic_by_products[product]:
                        cost = order.get('cost', 0.0) * order.get('qty', 0.0)
                        purchase_price = (
                            order.get('purchase_price', 0.0)*order.get('qty', 0.0))
                        profit = (order.get('purchase_price', 0.0)*order.get('qty', 0.0)
                                  ) - (order.get('cost', 0.0)*order.get('qty', 0.0))
                        if purchase_price == 0:
                            purchase_price = 1
                        margin = (profit / purchase_price) * 100
                        worksheet.write(row, 0, order.get(
                            'order_number', ''), center)
                        worksheet.write(row, 1, str(
                            order.get('order_date', '')), center)
                        worksheet.write(
                            row, 2, order.get('vendor', ''), center)
                        worksheet.write(row, 3, order.get('qty', 0.0), center)
                        worksheet.write(row, 4, "{:.2f}".format(cost), center)
                        worksheet.write(row, 5, "{:.2f}".format(purchase_price), center)
                        worksheet.write(
                            row, 6, "{:.2f}".format(profit), center)
                        worksheet.write(
                            row, 7, "{:.2f}".format(margin), center)
                        total_cost = total_cost + cost
                        total_purchase_price = total_purchase_price+purchase_price
                        total_profit = total_profit+profit
                        total_margin = total_margin+margin
                        row = row + 1
                        worksheet.write(row, 3, "Total", left)
                        worksheet.write(row, 4, "{:.2f}".format(
                            total_cost), bold_center_total)
                        worksheet.write(
                            row, 5, "{:.2f}".format(
                                total_purchase_price), bold_center_total)
                        worksheet.write(row, 6, "{:.2f}".format(total_profit),
                                        bold_center_total)
                        worksheet.write(row, 7, "{:.2f}".format(total_margin),
                                        bold_center_total)
                    row=row+2
        elif self.report_by == 'both':
            worksheet.col(0).width = int(30 * 260)
            worksheet.col(1).width = int(30 * 260)
            worksheet.col(2).width = int(30 * 260)
            worksheet.col(3).width = int(60 * 260)
            worksheet.col(4).width = int(33 * 260)
            worksheet.col(5).width = int(15 * 260)
            worksheet.col(6).width = int(15 * 260)
            worksheet.col(7).width = int(15 * 260)
            worksheet.col(8).width = int(15 * 260)
            worksheet.write_merge(
                0, 1, 0, 8, 'Purchase Product Profit', heading_format)
            worksheet.write_merge(2, 2, 0, 8, start_date + " to " + end_date, bold)
            if both_order_list:
                total_cost = 0.0
                total_purchase_price = 0.0
                total_profit = 0.0
                total_margin = 0.0
                worksheet.write(row, 0, "Order Number", bold_center)
                worksheet.write(row, 1, "Order Date", bold_center)
                worksheet.write(row, 2, "Vendor", bold_center)
                worksheet.write(row, 3, "Product", bold_center)
                worksheet.write(row, 4, "Quantity", bold_center)
                worksheet.write(row, 5, "Cost", bold_center)
                worksheet.write(row, 6, "Purchase Price", bold_center)
                worksheet.write(row, 7, "Profit", bold_center)
                worksheet.write(row, 8, "Margin(%)", bold_center)
                row = row + 1
                for order in both_order_list:
                    cost = order.get('cost', 0.0) * order.get('qty', 0.0)
                    purchase_price = (
                        order.get('purchase_price', 0.0)*order.get('qty', 0.0))
                    profit = (order.get('purchase_price', 0.0)*order.get('qty', 0.0)
                              ) - (order.get('cost', 0.0)*order.get('qty', 0.0))
                    if purchase_price == 0:
                        purchase_price = 1
                    margin = (profit / purchase_price) * 100

                    worksheet.write(row, 0, order.get(
                        'order_number', ''), center)
                    worksheet.write(row, 1, str(
                        order.get('order_date', '')), center)
                    worksheet.write(row, 2, order.get('vendor', ''), center)
                    worksheet.write(row, 3, order.get('product', ''), center)
                    worksheet.write(row, 4, order.get('qty', 0.0), center)
                    worksheet.write(row, 5, "{:.2f}".format(cost), center)
                    worksheet.write(row, 6, "{:.2f}".format(purchase_price), center)
                    worksheet.write(row, 7, "{:.2f}".format(profit), center)
                    worksheet.write(
                        row, 8, "{:.2f}".format(margin), center)
                    total_cost = total_cost + cost
                    total_purchase_price = total_purchase_price+purchase_price
                    total_profit = total_profit+profit
                    total_margin = total_margin+margin
                    row = row + 1
                    worksheet.write(row, 4, "Total", left)
                    worksheet.write(row, 5, "{:.2f}".format(
                        total_cost), bold_center_total)
                    worksheet.write(
                        row, 6, "{:.2f}".format(
                            total_purchase_price), bold_center_total)
                    worksheet.write(row, 7, "{:.2f}".format(total_profit),
                                    bold_center_total)
                    worksheet.write(row, 8, "{:.2f}".format(total_margin),
                                    bold_center_total)
                row=row+2
        filename = ('Purchase Product Profit' + '.xls')
        fp = BytesIO()
        workbook.save(fp)

        export_id = self.env['sh.purchase.product.profit.xls'].sudo().create({
            'excel_file': base64.encodestring(fp.getvalue()),
            'file_name': filename,
        })

        fp.close()
        return{
            'type': 'ir.actions.act_window',
            'name': 'Purchase Product Profit',
            'res_id': export_id.id,
            'res_model': 'sh.purchase.product.profit.xls',
            'view_mode': 'form',
            'target': 'new',
        }

class PurchaseProductProfitAnalysis(models.AbstractModel):
    _name = 'report.sh_purchase_reports.sh_po_product_profit_doc'
    _description = 'Purchase Product Profit report abstract model'

    def _get_street(self, partner):
        res = {}
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_address_details(self, partner):
        res = {}
        address = ''
        if partner.city:
            address = "%s" % (partner.city)
        if partner.state_id.name:
            address += ", %s" % (partner.state_id.name)
        if partner.zip:
            address += ", %s" % (partner.zip)
        if partner.country_id.name:
            address += ", %s" % (partner.country_id.name)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

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
                    if data.get('branch_ids', False):
                        domain.append(
                            ('branch_id', 'in', data.get('branch_ids', False)))
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
                    if data.get('branch_ids', False):
                        domain.append(
                            ('branch_id', 'in', data.get('branch_ids', False)))
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
            if data.get('branch_ids', False):
                domain.append(
                    ('branch_id', 'in', data.get('branch_ids', False)))
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
        company_id = self.env.company
        street_company = self._get_street(company_id.partner_id)
        address_company = self._get_address_details(company_id.partner_id)
        currency = self.env.user.company_id.sudo().currency_id
        data.update({
            'date_start': datetime.strptime(data['sh_start_date'], '%Y-%m-%d %H:%M:%S').strftime('%d %B %Y'),
            'date_end': datetime.strptime(data['sh_end_date'], '%Y-%m-%d %H:%M:%S').strftime('%d %B %Y'),
            'order_dic_by_vendors':order_dic_by_vendors,
            'order_dic_by_products':order_dic_by_products,
            'both_order_list':both_order_list,
            'report_by':data.get('report_by'),
            'company_id': company_id,
            'currency': currency,
            'street_company': street_company,
            'address_company': address_company,
            'print_date': (fields.Datetime.now()+timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S'),
        })
        return data