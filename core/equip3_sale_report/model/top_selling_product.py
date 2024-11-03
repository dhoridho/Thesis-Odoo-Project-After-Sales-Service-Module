from datetime import timedelta
import pytz
from odoo import api, fields, models
from odoo import tools
from odoo.tools import float_is_zero
import operator

class ListTopProduct(models.TransientModel):
    _name = 'list.top.product'
    _description = "List Top Product"

    name = fields.Char("Product")
    qty = fields.Float("Qty")
    top_id = fields.Many2one('sh.tsp.top.selling.product.wizard')

class ListTopProductCompare(models.TransientModel):
    _name = 'list.top.product.compare'
    _description = "List Top Product Compare"

    name = fields.Char("Product")
    qty = fields.Float("Qty")
    top_id = fields.Many2one('sh.tsp.top.selling.product.wizard')

class LostProduct(models.TransientModel):
    _name = 'lost.product'
    _description = "Lost Product"

    name = fields.Char("Product")
    top_id = fields.Many2one('sh.tsp.top.selling.product.wizard')

class NewProduct(models.TransientModel):
    _name = 'new.product'
    _description = "New Product"

    name = fields.Char("Product")
    top_id = fields.Many2one('sh.tsp.top.selling.product.wizard')

class TopSellingWizard(models.TransientModel):
    _inherit = "sh.tsp.top.selling.product.wizard"

    def domain_company(self):
        return [('id', 'in', self.env.companies.ids)]

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id)
    top_product_ids = fields.One2many('list.top.product', 'top_id')
    top_product_compare_ids = fields.One2many('list.top.product.compare', 'top_id')
    lost_product_ids = fields.One2many('lost.product', 'top_id')
    new_product_ids = fields.One2many('new.product', 'top_id')
    date_from = fields.Datetime('Start Date', required=True, default=fields.Datetime.now() - timedelta(days=int(30)))
    company_ids = fields.Many2many(
        'res.company', string="Companies", domain=domain_company)

    def print_top_selling_product_report(self):
        self.ensure_one()
        lost_product_obj = self.env['lost.product']
        new_product_obj = self.env['new.product']
        top_product_obj = self.env['list.top.product']
        top_product_compare_obj = self.env['list.top.product.compare']
        # we read self because we use from date and start date in our core bi logic.(in abstract model)
        data = self.read()[0]
        data.update(self._get_report_values(data))
        # currency_id = self.env['res.currency'].browse(data['currency_id'][0])
        self.write({
            'top_product_ids': [(6,0,[])],
            'top_product_compare_ids': [(6,0,[])],
            'lost_product_ids': [(6,0,[])],
            'new_product_ids': [(6,0,[])]
        })
        i = 0
        for prod in data['products']:
            top_product_obj.create({
                'name': prod,
                'qty': data['products_qty'][i],
                'top_id': self.id
            })
            i += 1
        j = 0
        for prod_comp in data['compare_products']:
            top_product_compare_obj.create({
                'name': prod_comp,
                'qty': data['compare_products_qty'][j],
                'top_id': self.id
            })
            j += 1
        for new in data['new_products']:
            new_product_obj.create({
                'name': new,
                'top_id': self.id
            })
        for lost in data['lost_products']:
            lost_product_obj.create({
                'name': lost,
                'top_id': self.id
            })
        return self.env.ref('equip3_sale_report.sh_top_selling_product_report_action').report_action(self)

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