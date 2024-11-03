from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import xlwt
import base64
from io import BytesIO
import pytz
from datetime import datetime, timedelta
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from odoo import tools

class ListOrder(models.TransientModel):
    _inherit = "list.order"

    product = fields.Char("Product")
    customer = fields.Char("Customer")
    qty = fields.Float("Qty")
    cost = fields.Float("Cost")
    sale_price = fields.Float("Sale Price")
    profit = fields.Float("Profit")
    margin = fields.Float("Margin")

class UserOrderDic(models.TransientModel):
    _inherit = "user.order.dic"

    prduct_profit_id = fields.Many2one('sh.sale.product.profit.wizard')
    product = fields.Char("Product")

class SalesProductProfitWizard(models.TransientModel):
    _inherit = 'sh.sale.product.profit.wizard'

    def domain_company(self):
        return [('id', 'in', self.env.companies.ids)]

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id)
    user_order_dic = fields.One2many('user.order.dic', 'prduct_profit_id')
    currency_precision = fields.Integer(default=lambda self: self.env.company.currency_id.id)
    sh_start_date = fields.Datetime('Start Date', required=True, default=fields.Datetime.now() - timedelta(days=int(30)))
    company_ids = fields.Many2many(
        'res.company', domain=domain_company, string="Companies")


    def print_report(self):
        order_dic_obj = self.env['user.order.dic']
        list_order_obj = self.env['list.order']
        datas = self.read()[0]
        datas.update(self._get_report_values(datas))
        self.write({
            'user_order_dic': [(6,0,[])]
        })
        for user in datas['order_dic_by_customers']:
            dic = order_dic_obj.create({
                'prduct_profit_id': self.id,
                'saleperson': user,
            })
            for line in datas['order_dic_by_customers'][user]:
                cost = line['cost'] * line['qty']
                sale_price = line['sale_price'] * line['qty']
                profit = sale_price - cost
                margin = 0
                if sale_price != 0:
                    margin = (profit/sale_price) * 100
                list_order_obj.create({
                    'order_dic_id': dic.id,
                    'order_number': line['order_number'],
                    'order_date': line['order_date'],
                    'product': line['product'],
                    'qty': line['qty'],
                    'cost': cost,
                    'sale_price': sale_price,
                    'profit': profit,
                    'margin': margin
                })

        for user in datas['order_dic_by_products']:
            dic = order_dic_obj.create({
                'prduct_profit_id': self.id,
                'product': user,
            })
            for line in datas['order_dic_by_products'][user]:
                cost = line['cost'] * line['qty']
                sale_price = line['sale_price'] * line['qty']
                profit = sale_price - cost
                margin = 0
                if sale_price != 0:
                    margin = (profit/sale_price) * 100
                list_order_obj.create({
                    'order_dic_id': dic.id,
                    'order_number': line['order_number'],
                    'order_date': line['order_date'],
                    'customer': line['customer'],
                    'qty': line['qty'],
                    'cost': cost,
                    'sale_price': sale_price,
                    'profit': profit,
                    'margin': margin
                })

        if datas['both_order_list']:
            dic = order_dic_obj.create({
                'prduct_profit_id': self.id,
            })
            for user in datas['both_order_list']:
                line = user
                cost = line['cost'] * line['qty']
                sale_price = line['sale_price'] * line['qty']
                profit = sale_price - cost
                margin = 0
                if sale_price != 0:
                    margin = (profit/sale_price) * 100
                list_order_obj.create({
                    'order_dic_id': dic.id,
                    'order_number': line['order_number'],
                    'order_date': line['order_date'],
                    'product': line['product'],
                    'customer': line['customer'],
                    'qty': line['qty'],
                    'cost': cost,
                    'sale_price': sale_price,
                    'profit': profit,
                    'margin': margin
                })
        return self.env.ref('equip3_sale_report.sh_sales_product_profit_action').report_action(self)

    def _get_street(self, partner):
        self.ensure_one()
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
        self.ensure_one()
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
    
    def _get_product_warehouse_price(self, product_id, warehouse_id):
        product_price = self.env['product.warehouse.price'].sudo().search(
            [('product_id', '=', product_id), ('warehouse_id', '=', warehouse_id)], limit=1).standard_price or 0
        return product_price or self.env['product.product'].browse(product_id).standard_price

    @api.model
    def _get_report_values(self, data=None):
        data = dict(data or {})
        order_dic_by_customers = {}
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
        if data.get('report_by') == 'customer':
            partners = False
            if data.get('sh_partner_ids', False):
                partners = self.env['res.partner'].sudo().browse(
                    data.get('sh_partner_ids', False))
            else:
                partners = self.env['res.partner'].sudo().search([])
            if partners:
                for partner_id in partners:
                    order_list = []
                    domain = [
                        ("date_order", ">=", fields.Datetime.to_string(date_start)),
                        ("date_order", "<=", fields.Datetime.to_string(date_stop)),
                        ("partner_id", "=", partner_id.id),
                        ("state", 'in', ('sale','done'))
                    ]
                    if data.get('company_ids', False):
                        domain.append(
                            ('company_id', 'in', data.get('company_ids', False)))
                    search_orders = self.env['sale.order'].sudo().search(
                        domain)
                    if search_orders:
                        for order in search_orders:
                            if order.order_line.filtered(lambda x: x.is_reward_line != True and x.is_downpayment != True and x.is_delivery != True):
                                order_dic = {}
                                for line in order.order_line:
                                    if not line.display_type:
                                        line_dic = {
                                            'order_number': order.name,
                                            'order_date': order.date_order,
                                            'product': line.product_id.name_get()[0][1],
                                            'qty': line.product_uom_qty,
                                            'cost': line.purchase_price,
                                            'sale_price': line.price_unit,
                                        }
                                        if order_dic.get(line.product_id.id, False):
                                            qty = order_dic.get(
                                                line.product_id.id)['qty']
                                            qty = qty + line.product_uom_qty
                                            line_dic.update({
                                                'qty': qty,
                                            })
                                        order_dic.update(
                                            {line.product_id.id: line_dic})
                                for key, value in order_dic.items():
                                    order_list.append(value)
                    order_dic_by_customers.update(
                        {partner_id.name_get()[0][1]: order_list})
        elif data.get('report_by') == 'product':
            products = False
            if data.get('sh_product_ids', False):
                products = self.env['product.product'].sudo().browse(
                    data.get('sh_product_ids', False))
            else:
                products = self.env['product.product'].sudo().search([])
            if products:
                for product_id in products:
                    order_list = []
                    domain = [
                        ("date_order", ">=", fields.Datetime.to_string(date_start)),
                        ("date_order", "<=", fields.Datetime.to_string(date_stop)),
                        ("state", 'in', ('sale','done'))
                    ]
                    if data.get('company_ids', False):
                        domain.append(
                            ('company_id', 'in', data.get('company_ids', False)))
                    search_orders = self.env['sale.order'].sudo().search(
                        domain)
                    if search_orders:
                        for order in search_orders:
                            if order.order_line.filtered(lambda x: x.product_id.id in products.ids and x.is_reward_line != True and x.is_downpayment != True and x.is_delivery != True):
                                order_dic = {}
                                for line in order.order_line.sudo().filtered(lambda x: x.product_id.id == product_id.id):
                                    if not line.display_type:
                                        line_dic = {
                                            'order_number': order.name,
                                            'order_date': order.date_order,
                                            'customer': order.partner_id.name_get()[0][1],
                                            'qty': line.product_uom_qty,
                                            'cost': line.purchase_price,
                                            'sale_price': line.price_unit,
                                        }
                                        if order_dic.get(line.product_id.id, False):
                                            qty = order_dic.get(
                                                line.product_id.id)['qty']
                                            qty = qty + line.product_uom_qty
                                            line_dic.update({
                                                'qty': qty,
                                            })
                                        order_dic.update(
                                            {line.product_id.id: line_dic})
                                for key, value in order_dic.items():
                                    order_list.append(value)
                    order_dic_by_products.update(
                        {product_id.name_get()[0][1]: order_list})
        elif data.get('report_by') == 'both':
            products = False
            partners = False
            if data.get('sh_product_ids', False):
                products = self.env['product.product'].sudo().browse(
                    data.get('sh_product_ids', False))
            else:
                products = self.env['product.product'].sudo().search([])
            if data.get('sh_partner_ids', False):
                partners = self.env['res.partner'].sudo().browse(
                    data.get('sh_partner_ids', False))
            else:
                partners = self.env['res.partner'].sudo().search([])
            domain = [
                ("date_order", ">=", fields.Datetime.to_string(date_start)),
                ("date_order", "<=", fields.Datetime.to_string(date_stop)),
                ("state", 'in', ('sale','done'))
            ]
            if data.get('company_ids', False):
                domain.append(
                    ('company_id', 'in', data.get('company_ids', False)))
            search_orders = self.env['sale.order'].sudo().search(domain)
            if search_orders:
                for order in search_orders.sudo().filtered(lambda x: x.partner_id.id in partners.ids):
                    if order.order_line:
                        order_dic = {}
                        for line in order.order_line.sudo().filtered(lambda x: x.product_id.id in products.ids and x.is_reward_line != True and x.is_downpayment != True and x.is_delivery != True):
                            if not line.display_type:
                                line_dic = {
                                    'order_number': order.name,
                                    'order_date': order.date_order,
                                    'customer': order.partner_id.name_get()[0][1],
                                    'product': line.product_id.name_get()[0][1],
                                    'qty': line.product_uom_qty,
                                    'cost': line.purchase_price,
                                    'sale_price': line.price_unit,
                                }
                                if order_dic.get(line.product_id.id, False):
                                    qty = order_dic.get(line.product_id.id)['qty']
                                    qty = qty + line.product_uom_qty
                                    line_dic.update({
                                        'qty': qty,
                                    })
                                order_dic.update({line.product_id.id: line_dic})
                        for key, value in order_dic.items():
                            both_order_list.append(value)
        data.update({
            'date_start': data['sh_start_date'],
            'date_end': data['sh_end_date'],
            'order_dic_by_customers': order_dic_by_customers,
            'order_dic_by_products': order_dic_by_products,
            'both_order_list': both_order_list,
            'report_by': data.get('report_by'),
        })
        return data
    
    def print_xls_report(self):
        workbook = xlwt.Workbook(encoding='utf-8')
        heading_format = xlwt.easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = xlwt.easyxf(
            'font:bold True,height 215;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold_center = xlwt.easyxf(
            'font:height 240,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center;')
        worksheet = workbook.add_sheet(
            'Sales Product Profit', bold_center)
        left = xlwt.easyxf('align: horiz center;font:bold True')
        center = xlwt.easyxf('align: horiz center;')
        bold_center_total = xlwt.easyxf('align: horiz center;font:bold True')
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
        if self.report_by == 'customer':
            worksheet.write_merge(
                0, 1, 0, 7, 'Sales Product Profit', heading_format)
            worksheet.write_merge(2, 2, 0, 7, start_date + " to " + end_date, bold)
        elif self.report_by == 'product':
            worksheet.write_merge(
                0, 1, 0, 7, 'Sales Product Profit', heading_format)
            worksheet.write_merge(2, 2, 0, 7, start_date + " to " + end_date, bold)
        elif self.report_by == 'both':
            worksheet.write_merge(
                0, 1, 0, 8, 'Sales Product Profit', heading_format)
            worksheet.write_merge(2, 2, 0, 8, start_date + " to " + end_date, bold)
        worksheet.col(0).width = int(30 * 260)
        worksheet.col(1).width = int(30 * 260)
        worksheet.col(2).width = int(18 * 260)
        worksheet.col(3).width = int(18 * 260)
        worksheet.col(4).width = int(33 * 260)
        worksheet.col(5).width = int(15 * 260)
        worksheet.col(6).width = int(15 * 260)
        worksheet.col(7).width = int(15 * 260)
        order_dic_by_customers = {}
        order_dic_by_products = {}
        both_order_list = []
        if self.report_by == 'customer':
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
                        ("state", 'in', ('sale','done'))
                    ]
                    if self.company_ids:
                        domain.append(
                            ('company_id', 'in', self.company_ids.ids))
                    search_orders = self.env['sale.order'].sudo().search(
                        domain)
                    if search_orders:
                        for order in search_orders:
                            if order.order_line:
                                order_dic = {}
                                for line in order.order_line.filtered(lambda x: x.is_reward_line != True and x.is_downpayment != True and x.is_delivery != True):
                                    if not line.display_type:
                                        line_dic = {
                                            'order_number': order.name,
                                            'order_date': order.date_order.date(),
                                            'product': line.product_id.name_get()[0][1],
                                            'qty': line.product_uom_qty,
                                            'cost': line.purchase_price,
                                            'sale_price': line.price_unit,
                                        }
                                        if order_dic.get(line.product_id.id, False):
                                            qty = order_dic.get(
                                                line.product_id.id)['qty']
                                            qty = qty + line.product_uom_qty
                                            line_dic.update({
                                                'qty': qty,
                                            })
                                        order_dic.update(
                                            {line.product_id.id: line_dic})
                                for key, value in order_dic.items():
                                    order_list.append(value)
                    order_dic_by_customers.update(
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
                        ("state", 'in', ('sale','done'))
                    ]
                    if self.company_ids:
                        domain.append(
                            ('company_id', 'in', self.company_ids.ids))
                    search_orders = self.env['sale.order'].sudo().search(
                        domain)
                    if search_orders:
                        for order in search_orders:
                            if order.order_line:
                                order_dic = {}
                                for line in order.order_line.sudo().filtered(lambda x: x.product_id.id == product_id.id):
                                    if not line.display_type and not line.is_reward_line and not line.is_downpayment and not line.is_delivery:
                                        line_dic = {
                                            'order_number': order.name,
                                            'order_date': order.date_order.date(),
                                            'customer': order.partner_id.name_get()[0][1],
                                            'qty': line.product_uom_qty,
                                            'cost': line.product_id.standard_price,
                                            'sale_price': line.price_unit,
                                        }
                                        if order_dic.get(line.product_id.id, False):
                                            qty = order_dic.get(
                                                line.product_id.id)['qty']
                                            qty = qty + line.product_uom_qty
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
                ("state", 'in', ('sale','done'))
            ]
            if self.company_ids:
                domain.append(
                    ('company_id', 'in', self.company_ids.ids))
            search_orders = self.env['sale.order'].sudo().search(domain)
            if search_orders:
                for order in search_orders.sudo().filtered(lambda x: x.partner_id.id in partners.ids):
                    if order.order_line:
                        order_dic = {}
                        for line in order.order_line.sudo().filtered(lambda x: x.product_id.id in products.ids and x.is_reward_line != True and x.is_downpayment != True and x.is_delivery != True):
                            if not line.display_type:
                                line_dic = {
                                    'order_number': order.name,
                                    'order_date': order.date_order.date(),
                                    'customer': order.partner_id.name_get()[0][1],
                                    'product': line.product_id.name_get()[0][1],
                                    'qty': line.product_uom_qty,
                                    'cost': line.purchase_price,
                                    'sale_price': line.price_unit,
                                }
                                if order_dic.get(line.product_id.id, False):
                                    qty = order_dic.get(line.product_id.id)['qty']
                                    qty = qty + line.product_uom_qty
                                    line_dic.update({
                                        'qty': qty,
                                    })
                                order_dic.update({line.product_id.id: line_dic})
                        for key, value in order_dic.items():
                            both_order_list.append(value)
        row = 4
        if self.report_by == 'customer':
            if order_dic_by_customers:
                for customer in order_dic_by_customers.keys():
                    worksheet.write_merge(
                        row, row, 0, 7, customer, bold_center)
                    row = row+2
                    total_cost = 0.0
                    total_sale_price = 0.0
                    total_profit = 0.0
                    total_margin = 0.0
                    worksheet.write(row, 0, "Order Number", bold)
                    worksheet.write(row, 1, "Order Date", bold)
                    worksheet.write(row, 2, "Product", bold)
                    worksheet.write(row, 3, "Quantity", bold)
                    worksheet.write(row, 4, "Cost", bold)
                    worksheet.write(row, 5, "Sale Price", bold)
                    worksheet.write(row, 6, "Profit", bold)
                    worksheet.write(row, 7, "Margin(%)", bold)
                    row += 1
                    for rec in order_dic_by_customers[customer]:
                        worksheet.write(row, 0, rec.get(
                            'order_number'), center)
                        worksheet.write(row, 1, str(
                            rec.get('order_date')), center)
                        worksheet.write(row, 2, rec.get('product'), center)
                        worksheet.write(row, 3, "{:.2f}".format(
                            rec.get('qty')), center)
                        cost = rec.get('cost', 0.0) * rec.get('qty', 0.0)
                        worksheet.write(row, 4, "{:.2f}".format(cost), center)
                        sale_price = rec.get(
                            'sale_price', 0.0) * rec.get('qty', 0.0)
                        worksheet.write(
                            row, 5, "{:.2f}".format(sale_price), center)
                        profit = rec.get('sale_price', 0.0)*rec.get('qty', 0.0) - (
                            rec.get('cost', 0.0)*rec.get('qty', 0.0))
                        worksheet.write(
                            row, 6, "{:.2f}".format(profit), center)
                        if sale_price != 0.0:
                            margin = (profit/sale_price)*100
                        else:
                            margin = 0.00
                        worksheet.write(
                            row, 7, "{:.2f}".format(margin), center)
                        total_cost = total_cost + cost
                        total_sale_price = total_sale_price + sale_price
                        if profit:
                            total_profit = total_profit + profit
                        total_margin = total_margin + margin
                        row = row + 1
                        worksheet.write(row, 3, "Total", left)
                        worksheet.write(row, 4, "{:.2f}".format(
                            total_cost), bold_center_total)
                        worksheet.write(
                            row, 5, "{:.2f}".format(
                                total_sale_price), bold_center_total)
                        worksheet.write(row, 6, "{:.2f}".format(total_profit),
                                        bold_center_total)
                        worksheet.write(row, 7, "{:.2f}".format(total_margin),
                                        bold_center_total)
                    row = row + 2

        elif self.report_by == 'product':
            if order_dic_by_products:
                for product in order_dic_by_products.keys():
                    worksheet.write_merge(
                        row, row, 0, 7, product, bold_center)
                    row += 2
                    total_cost = 0.0
                    total_sale_price = 0.0
                    total_profit = 0.0
                    total_margin = 0.0
                    worksheet.write(row, 0, "Order Number", bold)
                    worksheet.write(row, 1, "Order Date", bold)
                    worksheet.write(row, 2, "Customer", bold)
                    worksheet.write(row, 3, "Quantity", bold)
                    worksheet.write(row, 4, "Cost", bold)
                    worksheet.write(row, 5, "Sale Price", bold)
                    worksheet.write(row, 6, "Profit", bold)
                    worksheet.write(row, 7, "Margin(%)", bold)
                    row += 1
                    for rec in order_dic_by_products[product]:
                        worksheet.write(row, 0, rec.get(
                            'order_number'), center)
                        worksheet.write(row, 1, str(
                            rec.get('order_date')), center)
                        worksheet.write(row, 2, rec.get('customer'), center)
                        worksheet.write(row, 3, "{:.2f}".format(
                            rec.get('qty')), center)
                        cost = rec.get('cost', 0.0) * rec.get('qty', 0.0)
                        worksheet.write(row, 4, "{:.2f}".format(cost), center)
                        sale_price = rec.get(
                            'sale_price', 0.0) * rec.get('qty', 0.0)
                        worksheet.write(
                            row, 5, "{:.2f}".format(sale_price), center)
                        profit = rec.get('sale_price', 0.0)*rec.get('qty', 0.0) - (
                            rec.get('cost', 0.0)*rec.get('qty', 0.0))
                        worksheet.write(
                            row, 6, "{:.2f}".format(profit), center)
                        if sale_price != 0.0:
                            margin = (profit/sale_price)*100
                        else:
                            margin = 0.00
                        worksheet.write(
                            row, 7, "{:.2f}".format(margin), center)
                        total_cost = total_cost + cost
                        total_sale_price = total_sale_price + sale_price
                        if profit:
                            total_profit = total_profit + profit
                        total_margin = total_margin + margin
                        row += 1
                        worksheet.write(row, 3, "Total", left)
                        worksheet.write(row, 4, "{:.2f}".format(
                            total_cost), bold_center_total)
                        worksheet.write(
                            row, 5, "{:.2f}".format(
                                total_sale_price), bold_center_total)
                        worksheet.write(row, 6, "{:.2f}".format(total_profit),
                                        bold_center_total)
                        worksheet.write(row, 7, "{:.2f}".format(total_margin),
                                        bold_center_total)
                    row += 2
        elif self.report_by == 'both':
            total_cost = 0.0
            total_sale_price = 0.0
            total_profit = 0.0
            total_margin = 0.0
            worksheet.write(row, 0, "Order Number", bold)
            worksheet.write(row, 1, "Order Date", bold)
            worksheet.write(row, 2, "Customer", bold)
            worksheet.write(row, 3, "Product", bold)
            worksheet.write(row, 4, "Quantity", bold)
            worksheet.write(row, 5, "Cost", bold)
            worksheet.write(row, 6, "Sale Price", bold)
            worksheet.write(row, 7, "Profit", bold)
            worksheet.write(row, 8, "Margin(%)", bold)
            row = row + 1
            if both_order_list:
                for order in both_order_list:
                    worksheet.write(row, 0, order.get(
                        'order_number'), center)
                    worksheet.write(row, 1, str(
                        order.get('order_date')), center)
                    worksheet.write(row, 2, order.get('customer'), center)
                    worksheet.write(row, 3, order.get('product'), center)
                    worksheet.write(row, 4, "{:.2f}".format(
                        order.get('qty')), center)
                    cost = order.get('cost', 0.0) * order.get('qty', 0.0)
                    worksheet.write(row, 5, "{:.2f}".format(cost), center)
                    sale_price = order.get(
                        'sale_price', 0.0) * order.get('qty', 0.0)
                    worksheet.write(
                        row, 6, "{:.2f}".format(sale_price), center)
                    profit = order.get('sale_price', 0.0)*order.get('qty', 0.0) - (
                        order.get('cost', 0.0)*order.get('qty', 0.0))
                    worksheet.write(
                        row, 7, "{:.2f}".format(profit), center)
                    if sale_price != 0.0:
                        margin = (profit/sale_price)*100
                    else:
                        margin = 0.00
                    worksheet.write(
                        row, 8, "{:.2f}".format(margin), center)
                    total_cost = total_cost + cost
                    total_sale_price = total_sale_price + sale_price
                    if profit:
                        total_profit = total_profit + profit
                    total_margin = total_margin + margin
                    row += 1
                    worksheet.write(row, 4, "Total", left)
                    worksheet.write(row, 5, "{:.2f}".format(
                        total_cost), bold_center_total)
                    worksheet.write(
                        row, 6, "{:.2f}".format(
                            total_sale_price), bold_center_total)
                    worksheet.write(row, 7, "{:.2f}".format(total_profit),
                                    bold_center_total)
                    worksheet.write(row, 8, "{:.2f}".format(total_margin),
                                    bold_center_total)
                row += 2
        filename = ('Sales Product Profit' + '.xls')
        fp = BytesIO()
        workbook.save(fp)

        export_id = self.env['sh.sale.product.profit.xls'].sudo().create({
            'excel_file': base64.encodestring(fp.getvalue()),
            'file_name': filename,
        })

        fp.close()
        return{
            'type': 'ir.actions.act_window',
            'name': 'Sales Product Profit',
            'res_id': export_id.id,
            'res_model': 'sh.sale.product.profit.xls',
            'view_mode': 'form',
            'target': 'new',
        }