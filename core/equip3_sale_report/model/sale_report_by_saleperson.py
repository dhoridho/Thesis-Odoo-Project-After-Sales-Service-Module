from datetime import timedelta
import pytz
from odoo import api, fields, models
from odoo import tools

class UserOrderDic(models.TransientModel):
    _name = "user.order.dic"
    _description = "User Order Dic"

    report_id = fields.Many2one('sh.sale.report.salesperson.wizard')
    list_order = fields.One2many('list.order', 'order_dic_id')
    saleperson = fields.Char("Name")

class ListOrder(models.TransientModel):
    _name = "list.order"
    _description = "List order"

    order_dic_id = fields.Many2one('user.order.dic')
    order_number = fields.Char("Order Name")
    order_date = fields.Datetime("Order Date")
    customer = fields.Char("Customer")
    total = fields.Float("Total")
    paid_amount = fields.Float("Paid Amount")
    due_amount = fields.Float("Due Amount")

class SalespersonWizard(models.TransientModel):
    _inherit = "sh.sale.report.salesperson.wizard"


    def domain_company(self):
        return [('id', 'in', self.env.companies.ids)]

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id,domain=domain_company)
    company_ids = fields.Many2many(
        'res.company', string='Companies', domain=domain_company)
    user_order_dic = fields.One2many('user.order.dic', 'report_id')
    currency_precision = fields.Integer("Currency Precision")

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

    def print_report(self):
        order_dic_obj = self.env['user.order.dic']
        list_order_obj = self.env['list.order']
        datas = self.read()[0]
        datas.update(self._get_report_values(datas))
        for user in datas['user_list']:
            dic = order_dic_obj.create({
                'report_id': self.id,
                'saleperson': user,
            })
            for line in datas['user_order_dic'][user]:
                list_order_obj.create({
                    'order_dic_id': dic.id,
                    'order_number': line['order_number'],
                    'order_date': line['order_date'],
                    'customer': line['customer'],
                    'total': line['total'],
                    'paid_amount': line['paid_amount'],
                    'due_amount': line['due_amount']
                })
        self.write({
            'date_start': datas['date_start'],
            'date_end': datas['date_end'],
            'user_ids': [(6,0,datas['user_ids'])],
            'state': datas['state'],
            'company_ids': [(6,0,datas['company_ids'])],
            'currency_precision': datas['currency']
        })
        return self.env.ref('equip3_sale_report.sh_sale_report_salesperson_report_general').report_action(self)

    @api.model
    def _get_report_values(self, data=None):

        sale_order_obj = self.env["sale.order"]

        user_order_dic = {}
        user_list = []
        currency = False
        date_start = False
        date_stop = False
        if data['date_start']:
            date_start = fields.Datetime.from_string(data['date_start'])
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if data['date_end']:
            date_stop = fields.Datetime.from_string(data['date_end'])
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)

        if data.get('user_ids', False):
            for user_id in data.get('user_ids'):
                order_list = []
                domain = [
                    ("date_order", ">=", fields.Datetime.to_string(date_start)),
                    ("date_order", "<=", fields.Datetime.to_string(date_stop)),
                    ("user_id", "=", user_id)
                ]
                if data.get('company_ids', False):
                    domain.append(
                        ('company_id', 'in', data.get('company_ids', False)))
                if data.get('state', False) and data.get('state') == 'done':
                    domain.append(('state', 'in', ['sale', 'done']))

                search_orders = sale_order_obj.sudo().search(domain)
                if search_orders:
                    for order in search_orders:
                        if not currency:
                            currency = order.currency_id
                        order_dic = {
                            'order_number': order.name,
                            'order_date': order.date_order,
                            'customer': order.partner_id.name if order.partner_id else "",
                            'total': order.amount_total,
                            'paid_amount': 0.0,
                            'due_amount': 0.0,
                        }
                        if order.invoice_ids:
                            sum_of_invoice_amount = 0.0
                            sum_of_due_amount = 0.0
                            for invoice_id in order.invoice_ids.filtered(lambda inv: inv.state not in ['cancel', 'draft']):
                                sum_of_invoice_amount += invoice_id.amount_total_signed
                                sum_of_due_amount += invoice_id.amount_residual_signed

                            order_dic.update({
                                "paid_amount": sum_of_invoice_amount,
                                "due_amount": sum_of_due_amount,
                            })

                        order_list.append(order_dic)

                search_user = self.env['res.users'].sudo().search([
                    ('id', '=', user_id)
                ], limit=1)
                if search_user:
                    user_order_dic.update({search_user.name: order_list})
                    user_list.append(search_user.name)

        if not currency:
            currency = self.env.company.sudo().currency_id

        data = {
            'date_start': data['date_start'],
            'date_end': data['date_end'],
            'user_order_dic': user_order_dic,
            'user_list': user_list,
            'currency': currency,
        }
        return data

