from datetime import timedelta
import pytz
from odoo import api, fields, models
from odoo import tools

class CustomerOrderDic(models.TransientModel):
    _name = "customer.order.dic"
    _description = "Customer Order Dic"

    report_id = fields.Many2one('sh.sale.invoice.summary.wizard')
    list_order = fields.One2many('list.order', 'cust_dic_id')
    saleperson = fields.Char("Name")

class ListOrder(models.TransientModel):
    _inherit = "list.order"

    cust_dic_id = fields.Many2one('customer.order.dic')
    invoice_number = fields.Char("Invoice Number")
    invoice_date = fields.Datetime("Invoice Date")
    invoice_currency_id = fields.Integer("Invoice Currency")

class SaleInvioceSummaryWizard(models.TransientModel):
    _inherit = 'sh.sale.invoice.summary.wizard'

    def domain_company(self):
        return [('id', 'in', self.env.companies.ids)]

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id,domain=domain_company)
    company_ids = fields.Many2many(
        'res.company', string='Companies', domain=domain_company)
    customer_order_dic = fields.One2many('customer.order.dic', 'report_id')
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
        order_dic_obj = self.env['customer.order.dic']
        list_order_obj = self.env['list.order']
        datas = self.read()[0]
        datas.update(self._get_report_values(datas))
        self.write({
            'customer_order_dic': [(6,0,[])]
        })
        for user in datas['sh_partner_ids']:
            name = self.env['res.partner'].browse(user).name
            dic = order_dic_obj.create({
                'report_id': self.id,
                'saleperson': name,
            })
            for line in datas['customer_order_dic'][name]:
                list_order_obj.create({
                    'cust_dic_id': dic.id,
                    'order_number': line['order_number'],
                    'order_date': line['order_date'],
                    'invoice_number': line['invoice_number'],
                    'invoice_date': line['invoice_date'],
                    'invoice_currency_id': line['invoice_currency_id'],
                    'total': line['invoice_amount'],
                    'paid_amount': line['invoice_paid_amount'],
                    'due_amount': line['due_amount']
                })
        self.write({
            'sh_start_date': datas['sh_start_date'],
            'sh_end_date': datas['sh_end_date'],
            'sh_partner_ids': [(6,0,datas['sh_partner_ids'])],
            'company_ids': [(6,0,datas['company_ids'])],
            'sh_status': datas['sh_status'],
            'currency_precision': datas['currency_precision']
        })
        return self.env.ref('equip3_sale_report.sale_invoice_summary_action').report_action(self)

    @api.model
    def _get_report_values(self, data=None):
        data = dict(data or {})
        sale_order_obj = self.env["sale.order"]
        customer_order_dic = {}
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
                    ('state', 'in', ['sale', 'done']),
                ]
                if data.get('company_ids', False):
                    domain.append(
                        ('company_id', 'in', data.get('company_ids', False)))
                search_orders = sale_order_obj.sudo().search(domain)
                invoice_ids = []
                sh_status_ids = data.get('sh_status', False)
                if search_orders:
                    for order in search_orders:
                        invoiced = True
                        if order.invoice_ids:
                            if sh_status_ids == 'both':
                                for invoice in order.invoice_ids:
                                    if invoice.state in ('draft', 'cancel'):
                                        invoiced = False
                                        break
                            elif sh_status_ids == 'open':
                                for invoice in order.invoice_ids:
                                    if invoice.state not in ('posted') or invoice.amount_residual == 0.0:
                                        invoiced = False
                                        break
                            elif sh_status_ids == 'paid':
                                for invoice in order.invoice_ids:
                                    if invoice.state not in ('posted') or invoice.amount_residual != 0.0:
                                        invoiced = False
                                        break
                        if order.invoice_ids and invoiced:
                            for invoice in order.invoice_ids:
                                if invoice.id not in invoice_ids:
                                    invoice_ids.append(invoice.id)
                                order_dic = {
                                    'order_number': order.name,
                                    'order_date': order.date_order,
                                    'invoice_number': invoice.name,
                                    'invoice_date': invoice.invoice_date,
                                    'invoice_currency_id': invoice.currency_id.id,
                                }
                                if invoice.move_type == 'out_invoice':
                                    order_dic.update({
                                        'invoice_amount': invoice.amount_total,
                                        'invoice_paid_amount': invoice.amount_total - invoice.amount_residual,
                                        'due_amount': invoice.amount_residual,
                                    })
                                elif invoice.move_type == 'out_refund':
                                    order_dic.update({
                                        'invoice_amount': -(invoice.amount_total),
                                        'invoice_paid_amount': -(invoice.amount_total - invoice.amount_residual),
                                        'due_amount': -(invoice.amount_residual),
                                    })
                                order_list.append(order_dic)

                search_partner = self.env['res.partner'].sudo().search([
                    ('id', '=', partner_id)
                ], limit=1)
                if search_partner:
                    customer_order_dic.update(
                        {search_partner.name_get()[0][1]: order_list})
        data.update({
            'date_start': data['sh_start_date'],
            'date_end': data['sh_end_date'],
            'customer_order_dic': customer_order_dic,
        })
        return data