from datetime import timedelta, datetime
import pytz
from odoo import api, fields, models
from odoo import tools
from odoo.tools import float_is_zero

class ListOrder(models.TransientModel):
    _inherit = "list.order"

    salesperson = fields.Char("Sales Person")
    sale_currency_id = fields.Integer("Currency")
    sale_amount = fields.Float("Sale Amount")
    paid_amount = fields.Float("Paid Amount")
    balance_amount = fields.Float("Balance Amount")

class ListProduct(models.TransientModel):
    _name = "list.product"
    _description = "List Product"

    order_dic_id = fields.Many2one('user.order.dic')
    salesperson = fields.Char("Sales Person")
    order_number = fields.Char("Order Number")
    order_date = fields.Datetime("Order Date")
    product_name = fields.Char("Product Name")
    price = fields.Float("Price")
    qty = fields.Float("Qty")
    discount = fields.Float("Disc")
    tax = fields.Float("Tax")
    subtotal = fields.Float("Subtotal")
    sale_currency_id = fields.Integer("Currency ID")

class UserOrderDic(models.TransientModel):
    _inherit = "user.order.dic"

    list_product = fields.One2many('list.product', 'order_dic_id')
    sale_analysis_id = fields.Many2one('sh.sale.analysis.wizard')

class SalesAnalysisWizard(models.TransientModel):
    _inherit = 'sh.sale.analysis.wizard'

    def domain_company(self):
        return [('id', 'in', self.env.companies.ids)]

    company_ids = fields.Many2many(
        'res.company', domain=domain_company, string="Companies")

    sh_partner_ids = fields.Many2many('res.partner', string='Customers', required=False)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id)
    sale_analysis_dic = fields.One2many('user.order.dic', 'sale_analysis_id')
    sale_currency_id = fields.Integer("Currency")
    sh_status_ids = fields.Selection([('all', 'All'), ('draft', 'Draft'), ('sent', 'Quotation Sent'), ('sale', 'Sales Order'), ], string="Status", default='all')
    sh_start_date = fields.Datetime('Start Date', required=True, default=fields.Datetime.now() - timedelta(days=int(30)))
    #
    # @api.onchange('sh_start_date')
    # def onchange_sh_start_date(self, days=30):
    #     for record in self:
    #         record.sh_start_date = datetime.now() - timedelta(days=int(days))

    def print_report(self):
        order_dic_obj = self.env['user.order.dic']
        list_order_obj = self.env['list.order']
        list_product_obj = self.env['list.product']
        currency_id = 1
        datas = self.read()[0]
        datas.update(self._get_report_values(datas))
        self.write({
            'sale_analysis_dic': [(6, 0, [])]
        })
        for user in datas['sh_partner_ids']:
            name = self.env['res.partner'].browse(user).name
            dic = order_dic_obj.create({
                'sale_analysis_id': self.id,
                'saleperson': name,
            })
            if datas['order_dic_by_orders']:
                for line in datas['order_dic_by_orders'][name]:
                    currency_id = line['sale_currency_id']
                    list_order_obj.create({
                        'order_dic_id': dic.id,
                        'order_number': line['order_number'],
                        'order_date': line['order_date'],
                        'salesperson': line['salesperson'],
                        'sale_currency_id': line['sale_currency_id'],
                        'sale_amount': line['sale_amount'],
                        'paid_amount': line['paid_amount'],
                        'balance_amount': line['balance_amount']
                    })
            if datas['order_dic_by_products']:
                for line in datas['order_dic_by_products'][name]:
                    currency_id = line['sale_currency_id']
                    list_product_obj.create({
                        'order_dic_id': dic.id,
                        'salesperson': name,
                        'order_number': line['order_number'],
                        'order_date': line['order_date'],
                        'product_name': line['product_name'],
                        'price': line['price'],
                        'qty': line['qty'],
                        'discount': line['discount'],
                        'tax': line['tax'],
                        'subtotal': line['subtotal'],
                        'sale_currency_id': line['sale_currency_id'],
                    })
        self.write({
            'sale_currency_id': currency_id,
            'sh_start_date': datas['sh_start_date'],
            'sh_end_date': datas['sh_end_date'],
            'sh_partner_ids': [(6,0,datas['sh_partner_ids'])],
            'sh_product_ids': [(6,0,datas['sh_product_ids'])],
            'sh_status_ids': datas['sh_status_ids'],
            'company_ids': [(6,0,datas['company_ids'])],
        })
        return self.env.ref('equip3_sale_report.cus_sales_analysis_actions').report_action(self)

    @api.model
    def _get_report_values(self, data=None):
        data = dict(data or {})
        sale_order_obj = self.env["sale.order"]
        order_dic_by_orders = {}
        order_dic_by_products = {}
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
        if data.get('sh_partner_ids', False):
            for partner_id in data.get('sh_partner_ids'):
                order_list = []
                domain = [
                    ("date_order", ">=", fields.Datetime.to_string(date_start)),
                    ("date_order", "<=", fields.Datetime.to_string(date_stop)),
                    ("partner_id", "=", partner_id),
                ]
                if data.get('sh_status_ids') == 'all':
                    domain.append(('state','not in',['cancel']))
                elif data.get('sh_status_ids') == 'draft':
                    domain.append(('state','in',['draft']))
                elif data.get('sh_status_ids') == 'sent':
                    domain.append(('state','in',['sent']))
                elif data.get('sh_status_ids ') == 'sale':
                    domain.append(('state','in',['sale']))

                if data.get('company_ids', False):
                    domain.append(
                        ('company_id', 'in', data.get('company_ids', False)))
                search_orders = sale_order_obj.sudo().search(domain)
                if search_orders:
                    for order in search_orders:
                        if data.get('report_by') == 'order':
                            order_dic = {
                                'order_number': order.name,
                                'order_date': order.date_order,
                                'salesperson': order.user_id.name,
                                'sale_amount': order.amount_total,
                                'sale_currency_id':order.currency_id.id,
                            }
                            paid_amount = 0.0
                            if order.invoice_ids:
                                for invoice in order.invoice_ids:
                                    if invoice.move_type == 'out_invoice':
                                        paid_amount+=invoice.amount_total - invoice.amount_residual
                                    elif invoice.move_type == 'out_refund':
                                        paid_amount+=-(invoice.amount_total - invoice.amount_residual)
                            order_dic.update({
                                'paid_amount':paid_amount,
                                'balance_amount':order.amount_total - paid_amount
                            })
                            order_list.append(order_dic)
                        elif data.get('report_by') == 'product' and order.order_line:
                            lines = False
                            if data.get('sh_product_ids'):
                                lines = order.order_line.sudo().filtered(lambda x: x.product_id.id in data.get('sh_product_ids'))
                            else:
                                products = self.env['product.product'].sudo().search([])
                                lines = order.order_line.sudo().filtered(lambda x: x.product_id.id in products.ids)
                            if lines:
                                for line in lines:
                                    order_dic = {
                                        'order_number':line.order_id.name,
                                        'order_date':line.order_id.date_order,
                                        'product_name': line.product_id.name_get()[0][1],
                                        'price': line.price_unit,
                                        'qty':line.product_uom_qty,
                                        'discount':line.discount,
                                        'tax':line.price_total - line.price_reduce,
                                        'subtotal':line.price_subtotal,
                                        'sale_currency_id':order.currency_id.id,
                                    }
                                    order_list.append(order_dic)
                search_partner = self.env['res.partner'].sudo().search([
                    ('id', '=', partner_id)
                ], limit=1)
                if search_partner:
                    if data.get('report_by') == 'order':
                        order_dic_by_orders.update({search_partner.name_get()[0][1]: order_list})
                    elif data.get('report_by') == 'product':
                        order_dic_by_products.update({search_partner.name_get()[0][1]: order_list})
        data.update({
            'date_start': data['sh_start_date'],
            'date_end': data['sh_end_date'],
            'order_dic_by_orders': order_dic_by_orders,
            'report_by':data.get('report_by'),
            'order_dic_by_products':order_dic_by_products,
        })
        return data

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