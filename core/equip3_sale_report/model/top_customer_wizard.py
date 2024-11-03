from datetime import timedelta
import pytz
from odoo import api, fields, models
from odoo import tools
from odoo.tools import float_is_zero
import operator

class ListCustomer(models.TransientModel):
    _name = 'list.customer'
    _Description = "List Customer"

    name = fields.Char("Customer")
    sale_amount = fields.Float("Sale Amount")
    top_id = fields.Many2one('sh.tc.top.customer.wizard')

class ListCustomerCompare(models.TransientModel):
    _name = 'list.customer.compare'
    _description = "List Customer Compare"

    name = fields.Char("Customer")
    sale_amount = fields.Float("Sale Amount")
    top_id = fields.Many2one('sh.tc.top.customer.wizard')

class LostCustomer(models.TransientModel):
    _name = 'lost.customer'
    _description = "Lost Customer"

    name = fields.Char("Customer")
    top_id = fields.Many2one('sh.tc.top.customer.wizard')

class NewCustomer(models.TransientModel):
    _name = 'new.customer'
    _description = "New Customer"

    name = fields.Char("Customer")
    top_id = fields.Many2one('sh.tc.top.customer.wizard')

class TOPCustomerWizard(models.TransientModel):
    _inherit = "sh.tc.top.customer.wizard"


    def domain_company(self):
        return [('id', 'in', self.env.companies.ids)]

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id)
    top_customer_ids = fields.One2many('list.customer', 'top_id')
    top_customer_compare_ids = fields.One2many('list.customer.compare', 'top_id')
    lost_cust_ids = fields.One2many('lost.customer', 'top_id')
    new_cust_ids = fields.One2many('new.customer', 'top_id')
    sale_currency_id = fields.Many2one('res.currency', string='Currency', readonly=1, related=False)
    date_from = fields.Datetime('Start Date', required=True, default=fields.Datetime.now() - timedelta(days=int(30)))
    company_ids = fields.Many2many(
        'res.company', string="Company", domain=domain_company)


    def print_top_customer_report(self):
        self.ensure_one()
        lost_customer_obj = self.env['lost.customer']
        new_customer_obj = self.env['new.customer']
        top_customer_obj = self.env['list.customer']
        top_customer_compare_obj = self.env['list.customer.compare']
        # we read self because we use from date and start date in our core bi logic.(in abstract model)
        data = self.read()[0]
        data.update(self._get_report_values(data))
        # currency_id = self.env['res.currency'].browse(data['currency_id'][0])
        self.write({
            'sale_currency_id': data['currency_id'][0],
            'top_customer_ids': [(6,0,[])],
            'top_customer_compare_ids': [(6,0,[])],
            'lost_cust_ids': [(6,0,[])],
            'new_cust_ids': [(6,0,[])]
        })
        i = 0
        for cust in data['partners']:
            top_customer_obj.create({
                'name': cust,
                'sale_amount': data['partners_amount'][i],
                'top_id': self.id
            })
            i += 1
        j = 0
        for cust_comp in data['compare_partners']:
            top_customer_compare_obj.create({
                'name': cust_comp,
                'sale_amount': data['compare_partners_amount'][j],
                'top_id': self.id
            })
            j += 1
        for new in data['new_partners']:
            new_customer_obj.create({
                'name': new,
                'top_id': self.id
            })
        for lost in data['lost_partners']:
            lost_customer_obj.create({
                'name': lost,
                'top_id': self.id
            })
        return self.env.ref('equip3_sale_report.top_customers_report_action').report_action(self)

    @api.model
    def _get_report_values(self, data=None):
        data = dict(data or {})
        sale_order_obj = self.env['sale.order']
        currency_id = False
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
            ('date_order', '>=', fields.Datetime.to_string(date_start)),
            ('date_order', '<=', fields.Datetime.to_string(date_stop)),
            ('state', 'in', ['sale', 'done']),
        ]
        if data.get('company_ids', False):
            domain.append(('company_id', 'in', data.get('company_ids', False)))
        if data.get('team_id'):
            team_id = data.get('team_id')
            team_id = team_id[0]
            domain.append(
                ('team_id', '=', team_id)
            )

        sale_orders = sale_order_obj.sudo().search(domain)
        partner_total_amount_dic = {}
        if sale_orders:
            for order in sale_orders.sorted(key=lambda o: o.partner_id.id):
                if order.currency_id:
                    currency_id = order.currency_id

                if partner_total_amount_dic.get(order.partner_id.name, False):
                    amount = partner_total_amount_dic.get(
                        order.partner_id.name)
                    amount += order.amount_total
                    partner_total_amount_dic.update(
                        {order.partner_id.name: amount})
                else:
                    partner_total_amount_dic.update(
                        {order.partner_id.name: order.amount_total})

        final_partner_list = []
        final_partner_amount_list = []
        if partner_total_amount_dic:
            # sort partner dictionary by descending order
            sorted_partner_total_amount_list = sorted(
                partner_total_amount_dic.items(), key=operator.itemgetter(1), reverse=True)
            counter = 0

            for tuple_item in sorted_partner_total_amount_list:
                if data['amount_total'] != 0 and tuple_item[1] >= data['amount_total']:
                    final_partner_list.append(tuple_item[0])

                elif data['amount_total'] == 0:
                    final_partner_list.append(tuple_item[0])

                final_partner_amount_list.append(tuple_item[1])
                # only show record by user limit
                counter += 1
                if counter >= data['no_of_top_item']:
                    break

        sale_orders = False
        date_start = False
        date_stop = False
        if data['date_compare_from']:
            date_start = fields.Datetime.from_string(data['date_compare_from'])
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if data['date_compare_to']:
            date_stop = fields.Datetime.from_string(data['date_compare_to'])
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)
        domain = [
            ('date_order', '>=', fields.Datetime.to_string(date_start)),
            ('date_order', '<=', fields.Datetime.to_string(date_stop)),
            ('state', 'in', ['sale', 'done']),
        ]
        if data.get('company_ids', False):
            domain.append(('company_id', 'in', data.get('company_ids', False)))
        if data.get('team_id'):
            team_id = data.get('team_id')
            team_id = team_id[0]
            domain.append(
                ('team_id', '=', team_id)
            )

        sale_orders = sale_order_obj.sudo().search(domain)

        partner_total_amount_dic = {}
        if sale_orders:
            for order in sale_orders.sorted(key=lambda o: o.partner_id.id):
                if order.currency_id:
                    currency_id = order.currency_id

                if partner_total_amount_dic.get(order.partner_id.name, False):
                    amount = partner_total_amount_dic.get(
                        order.partner_id.name)
                    amount += order.amount_total
                    partner_total_amount_dic.update(
                        {order.partner_id.name: amount})
                else:
                    partner_total_amount_dic.update(
                        {order.partner_id.name: order.amount_total})

        final_compare_partner_list = []
        final_compare_partner_amount_list = []
        if partner_total_amount_dic:
            # sort compare partner dictionary by descending order
            sorted_partner_total_amount_list = sorted(
                partner_total_amount_dic.items(), key=operator.itemgetter(1), reverse=True)

            counter = 0
            for tuple_item in sorted_partner_total_amount_list:
                if data['amount_total'] != 0 and tuple_item[1] >= data['amount_total']:
                    final_compare_partner_list.append(tuple_item[0])

                elif data['amount_total'] == 0:
                    final_compare_partner_list.append(tuple_item[0])

                final_compare_partner_amount_list.append(tuple_item[1])
                # only show record by user limit
                counter += 1
                if counter >= data['no_of_top_item']:
                    break

        # find lost and new partner here
        lost_partner_list = []
        new_partner_list = []
        if final_partner_list and final_compare_partner_list:
            for item in final_partner_list:
                if item not in final_compare_partner_list:
                    lost_partner_list.append(item)

            for item in final_compare_partner_list:
                if item not in final_partner_list:
                    new_partner_list.append(item)

        #       finally update data dictionary
        if not currency_id:
            self.env.company.sudo().currency_id

        data.update({'partners': final_partner_list,
                     'partners_amount': final_partner_amount_list,
                     'compare_partners': final_compare_partner_list,
                     'compare_partners_amount': final_compare_partner_amount_list,
                     'lost_partners': lost_partner_list,
                     'new_partners': new_partner_list,
                     'currency': currency_id,
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