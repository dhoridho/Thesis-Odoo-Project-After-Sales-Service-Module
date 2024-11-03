from datetime import timedelta
import pytz
from odoo import api, fields, models
from odoo import tools
from odoo.tools import float_is_zero
import operator

class ListCategory(models.TransientModel):
    _name = "list.category"
    _description = "List Category"

    order_id = fields.Many2one('user.order.dic')
    categ = fields.Char("Category")
    product_ids = fields.One2many('list.product', 'categ_id')

class ListProduct(models.TransientModel):
    _inherit = "list.product"

    categ_id = fields.Many2one('list.category')

class UserOrderDic(models.TransientModel):
    _inherit = "user.order.dic"

    product_indent_id = fields.Many2one('sh.sale.product.indent.wizard')
    category_ids = fields.One2many('list.category', 'order_id')

class SaleProductIndentWizard(models.TransientModel):
    _inherit = 'sh.sale.product.indent.wizard'

    def domain_company(self):
        return [('id', 'in', self.env.companies.ids)]

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id)
    product_indent_dic = fields.One2many('user.order.dic', 'product_indent_id')
    sh_start_date = fields.Datetime('Start Date', required=True, default=fields.Datetime.now() - timedelta(days=int(30)))
    sh_status_ids = fields.Selection([('all', 'All'), ('draft', 'Draft'), ('sent', 'Quotation Sent'), ('sale', 'Sales Order'), ], string="Status", default='all')
    company_ids = fields.Many2many(
        'res.company', domain=domain_company, string="Companies")


    def print_report(self):
        order_dic_obj = self.env['user.order.dic']
        list_product_obj = self.env['list.product']
        list_categ_obj = self.env['list.category']
        datas = self.read()[0]
        datas.update(self._get_report_values(datas))
        self.write({
            'product_indent_dic': [(6,0,[])]
        })
        if datas['order_dic']:
            for name in datas['order_dic']:
                dic = order_dic_obj.create({
                    'product_indent_id': self.id,
                    'saleperson': name
                })
                for line in datas['order_dic'][name]:
                    for category in line:
                        categ_id = list_categ_obj.create({
                            'order_id': dic.id,
                            'categ': category
                        })
                        for categ in line[category]:
                            list_product_obj.create({
                                'categ_id': categ_id.id,
                                'product_name': categ['name'],
                                'qty': categ['qty'],
                            })
        return self.env.ref('equip3_sale_report.sh_sale_product_indent_action').report_action(self)

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
                        if data.get('sh_status_ids', False) == 'all':
                            domain.append(
                                ('order_id.state', 'not in', ['cancel']))
                        elif data.get('sh_status_ids', False) == 'draft':
                            domain.append(('order_id.state', 'in', ['draft']))
                        elif data.get('sh_status_ids', False) == 'sent':
                            domain.append(('order_id.state', 'in', ['sent']))
                        elif data.get('sh_status_ids', False) == 'sale':
                            domain.append(('order_id.state', 'in', ['sale']))
                        # elif data.get('sh_status_ids', False) == 'done':
                        #     domain.append(('order_id.state', 'in', ['done']))
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