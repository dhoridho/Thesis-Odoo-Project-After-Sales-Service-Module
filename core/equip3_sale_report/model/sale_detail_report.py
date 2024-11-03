from datetime import timedelta
import pytz
from odoo import api, fields, models
from odoo import tools

class SalesDetailWizard(models.TransientModel):
    _inherit = "sh.sale.details.report.wizard"
    _description = "sh sale details report wizard model"

    @api.model
    def domain_company(self):
        return [('id', 'in', self.env.companies.ids)]

    @api.model
    def default_company_ids(self):
        is_allowed_companies = self.env.context.get(
            'allowed_company_ids', False)
        if is_allowed_companies:
            return is_allowed_companies
        return

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id)
    company_ids = fields.Many2many(
        'res.company', string='Companies', default=default_company_ids, domain=domain_company)
    state = fields.Char("State")
    total_paid = fields.Float("Total")
    payments = fields.One2many('payment.sale.details.report', 'details_id', string="Payments")
    company_name = fields.Char("Company")
    taxes = fields.One2many('tax.sale.details.report', 'details_id', string="Tax")
    products = fields.One2many('product.sale.details.report', 'details_id', string="Product")
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
        payment_obj = self.env["payment.sale.details.report"]
        tax_obj = self.env["tax.sale.details.report"]
        product_obj = self.env["product.sale.details.report"]
        data = {'start_date': self.start_date, 'end_date': self.end_date,
                'team_ids': self.team_ids.ids, 'company_ids': self.company_ids.ids, 'state': self.state}
        data.update(self.get_sale_details(
            data['start_date'], data['end_date'], self.team_ids, self.company_ids, data['state']))
        self.write({
            'start_date': self.start_date,
            'end_date': self.end_date,
            'team_ids': self.team_ids,
            'company_ids': self.company_ids.ids,
            'state': self.state,
            'currency_precision': data['currency_precision'],
            'total_paid': data['total_paid'],
            'payments': [(6,0, [])],
            'taxes': [(6,0, [])],
            'products': [(6,0, [])]
        })
        for payment in data['payments']:
            payment['details_id'] = self.id
        payment_obj.create(data['payments'])
        for tax in data['taxes']:
            tax['details_id'] = self.id
        tax_obj.create(data['taxes'])
        for product in data['products']:
            product['details_id'] = self.id
        product_obj.create(data['products'])
        return self.env.ref('equip3_sale_report.sale_detail_report_action').report_action(self)

    @api.model
    def get_sale_details(self, date_start=False, date_stop=False, team_ids=False, company_ids=False, state=False):
        """ Serialise the orders of the day information

        params: date_start, date_stop string representing the datetime of order
        """
        if date_start:
            date_start = fields.Datetime.from_string(date_start)
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if date_stop:
            date_stop = fields.Datetime.from_string(date_stop)
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)
        if company_ids:
            domain = [
                ('date_order', '>=', fields.Datetime.to_string(date_start)),
                ('date_order', '<=', fields.Datetime.to_string(date_stop)),
                ('company_id', 'in', company_ids.ids)
            ]
        else:
            domain = [
                ('date_order', '>=', fields.Datetime.to_string(date_start)),
                ('date_order', '<=', fields.Datetime.to_string(date_stop)),
            ]

        if team_ids:
            domain.append(('team_id', 'in', team_ids.ids))

        if state and state == 'done':
            domain.append(('state', 'in', ['sale', 'done']))

        orders = self.env['sale.order'].sudo().search(domain)
        user_currency = self.env.company.currency_id
        total = 0.0
        products_sold = {}
        taxes = {}
        invoice_id_list = []
        for order in orders:
            if user_currency != order.pricelist_id.currency_id:
                total += order.pricelist_id.currency_id.compute(
                    order.amount_total, user_currency)
            else:
                total += order.amount_total
            currency = order.currency_id
            for line in order.order_line:
                if not line.display_type:
                    key = (line.product_id, line.price_unit, line.discount)
                    products_sold.setdefault(key, 0.0)
                    products_sold[key] += line.product_uom_qty
                    if line.tax_id:
                        line_taxes = line.tax_id.compute_all(line.price_unit * (1-(line.discount or 0.0)/100.0), currency,
                                                             line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_id or False)
                        for tax in line_taxes['taxes']:
                            taxes.setdefault(
                                tax['id'], {'name': tax['name'], 'total': 0.0})
                            taxes[tax['id']]['total'] += tax['amount']

            if order.invoice_ids:
                f_invoices = order.invoice_ids.filtered(
                    lambda inv: inv.state not in ['draft', 'cancel'])
                if f_invoices:
                    invoice_id_list += f_invoices.ids

        account_payment_obj = self.env["account.payment"]
        account_journal_obj = self.env["account.journal"]

        search_journals = account_journal_obj.sudo().search([
            ('type', 'in', ['bank', 'cash'])
        ])

        journal_wise_total_payment_list = []
        if invoice_id_list and search_journals:
            for journal in search_journals:
                invoice_domain = [
                    ('id', 'in', invoice_id_list)
                ]
                invoices = self.env['account.move'].sudo().search(
                    invoice_domain)
                payment_domain = []
                for invoice in invoices:
                    payment_domain.append(
                        ("payment_type", "in", ["inbound", "outbound"]))
                    payment_domain.append(("ref", "=", invoice.name))
                    payment_domain.append(("journal_id", "=", journal.id))
                payments = account_payment_obj.sudo().search(payment_domain)
                paid_total = 0.0
                if payments:
                    for payment in payments:
                        paid_total += payment.amount

                journal_wise_total_payment_list.append(
                    {"name": journal.name, "total": paid_total})
        else:
            journal_wise_total_payment_list = []

        return {
            'currency_precision': user_currency.decimal_places,
            'total_paid': user_currency.round(total),
            'payments': journal_wise_total_payment_list,
            'company_name': self.env.company.name,
            'taxes': taxes.values(),
            'products': sorted([{
                'product_id': product.id,
                'product_name': product.name,
                'code': product.default_code,
                'quantity': qty,
                'price_unit': price_unit,
                'discount': discount,
                'uom': product.uom_id.name
            } for (product, price_unit, discount), qty in products_sold.items()], key=lambda l: l['product_name'])
        }

class PaymentDetailsReport(models.TransientModel):
    _name = "payment.sale.details.report"
    _description = "Payment Sale Details Report"

    name = fields.Char("Name")
    total = fields.Float("Total")
    details_id = fields.Many2one('sh.sale.details.report.wizard')

class TaxDetailsReport(models.TransientModel):
    _name = "tax.sale.details.report"
    _description = "Tax Sale Details Report"

    name = fields.Char("Name")
    total = fields.Float("Total")
    details_id = fields.Many2one('sh.sale.details.report.wizard')

class ProductDetailsReport(models.TransientModel):
    _name = "product.sale.details.report"
    _description = "Product Sale Details Report"

    product_id = fields.Many2one('product.product', string="Product")
    product_name = fields.Char("Name")
    code = fields.Char("Code")
    quantity = fields.Float("Qty")
    price_unit = fields.Float("Price Unit")
    discount = fields.Float("Disc")
    uom = fields.Char("UoM")
    details_id = fields.Many2one('sh.sale.details.report.wizard')