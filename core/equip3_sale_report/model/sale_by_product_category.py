from datetime import timedelta
import pytz
from odoo import api, fields, models
from odoo import tools
from odoo.tools import float_is_zero
import operator

class ListProduct(models.TransientModel):
    _inherit = "list.product"

    uom = fields.Char("UoM")
    total = fields.Float("Total")

class UserOrderDic(models.TransientModel):
    _inherit = "user.order.dic"

    sale_categ_id = fields.Many2one('sh.sale.category.wizard')
    categ = fields.Char("Category")

class SaleByCategoryWizard(models.TransientModel):
    _inherit = 'sh.sale.category.wizard'

    def domain_company(self):
        return [('id', 'in', self.env.companies.ids)]

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id)
    category_order_dic = fields.One2many('user.order.dic', 'sale_categ_id')
    currency_precision = fields.Integer(default=lambda self: self.env.company.currency_id.id)
    sh_start_date = fields.Datetime('Start Date', required=True, default=fields.Datetime.now() - timedelta(days=int(30)))
    company_ids = fields.Many2many(
        'res.company', domain=domain_company, string="Companies")

    
    def print_report(self):
        order_dic_obj = self.env['user.order.dic']
        list_product_obj = self.env['list.product']
        datas = self.read()[0]
        datas.update(self._get_report_values(datas))
        self.write({
            'category_order_dic': [(6,0,[])]
        })
        if datas['category_order_dic']:
            for categ in datas['category_order_dic']:
                dic = order_dic_obj.create({
                    'sale_categ_id': self.id,
                    'categ': categ,
                })
                for line in datas['category_order_dic'][categ]:
                    subtotal = line['sale_price'] * line['qty']
                    total = subtotal + line['tax']
                    list_product_obj.create({
                        'order_dic_id': dic.id,
                        'order_number': line['order_number'],
                        'order_date': line['order_date'],
                        'product_name': line['product'],
                        'qty': line['qty'],
                        'uom': line['uom'],
                        'price': line['sale_price'],
                        'tax': line['tax'],
                        'subtotal': subtotal,
                        'total': total,
                        'sale_currency_id': line['sale_currency_id'],
                    })
        return self.env.ref('equip3_sale_report.sh_sale_by_category_action').report_action(self)

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

    @api.model
    def _get_report_values(self, data=None):
        data = dict(data or {})
        sale_order_obj = self.env["sale.order"]
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
                    ('state', 'in', ['sale', 'done'])
                ]
                if data.get('company_ids', False):
                    domain.append(
                        ('company_id', 'in', data.get('company_ids', False)))
                search_orders = sale_order_obj.sudo().search(domain)
                if search_orders:
                    for order in search_orders:
                        if order.order_line:
                            order_dic = {}
                            for line in order.order_line.sudo().filtered(lambda x: x.product_id.categ_id.id == category.id):
                                line_dic = {
                                    'order_number': order.name,
                                    'order_date': order.date_order,
                                    'product': line.product_id.name_get()[0][1],
                                    'qty': line.product_uom_qty,
                                    'uom': line.product_uom.name,
                                    'sale_price': line.price_unit,
                                    'tax': line.price_tax,
                                    'sale_currency_id': line.currency_id.id
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
                category_order_dic.update({category.display_name: order_list})
        data.update({
            'date_start': data['sh_start_date'],
            'date_end': data['sh_end_date'],
            'category_order_dic': category_order_dic,
        })
        return data