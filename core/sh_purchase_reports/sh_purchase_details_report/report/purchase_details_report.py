# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from datetime import timedelta
import pytz
from odoo import api, fields, models



class ReportSaleDetails(models.AbstractModel):

    _name = 'report.sh_purchase_reports.sh_pr_details_report_doc'
    _description = 'Purchase details report abstract model'

    @api.model
    def get_sale_details(self, date_start=False, date_stop=False, company_ids=False, state=False):
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

        domain = [
            ('date_order', '>=', fields.Datetime.to_string(date_start)),
            ('date_order', '<=', fields.Datetime.to_string(date_stop)),
        ]
        if company_ids:
            domain.append(('company_id', 'in', company_ids.ids))

        if state and state == 'done':
            domain.append(('state', 'in', ['purchase', 'done']))

        orders = self.env['purchase.order'].sudo().search(domain)
        user_currency = self.env.user.company_id.currency_id
        total = 0.0
        products_purchased = {}
        taxes = {}
        invoice_id_list = []
        for order in orders:
            if user_currency != order.partner_id.currency_id:
                total += order.partner_id.currency_id.compute(
                    order.amount_total, user_currency)
            else:
                total += order.amount_total
            currency = order.currency_id
            for line in order.order_line:
                if not line.display_type:
                    key = (line.product_id, line.price_unit)
                    products_purchased.setdefault(key, 0.0)
                    products_purchased[key] += line.product_qty
                    if line.taxes_id:
                        line_taxes = line.taxes_id.compute_all(
                            line.price_unit * (1/100.0), currency, line.product_qty, product=line.product_id, partner=line.order_id.partner_id or False)
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
                domain = []
                invoices = self.env['account.move'].browse(invoice_id_list)
                if invoices:
                    reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                        ['|', ('debit_move_id', 'in', invoices.mapped('line_ids').ids), ('credit_move_id', 'in', invoices.mapped('line_ids').ids)])
                    if reconcile_lines:
                        domain.append(('|'))
                        domain.append(
                            ('invoice_line_ids.id', 'in', reconcile_lines.mapped('credit_move_id').ids))
                        domain.append(
                            ('invoice_line_ids.id', 'in', reconcile_lines.mapped('debit_move_id').ids))
                        domain.append(
                            ("payment_type", "in", ["inbound", "outbound"]))
                        domain.append(("journal_id", "=", journal.id))
                        domain.append(("partner_type", "in", ["supplier"]))
                payments = account_payment_obj.sudo().search(domain)
                paid_total = 0.0
                if payments:
                    for payment in payments:
                        paid_total += payment.amount
                if {'name': journal.name, "total": paid_total} not in journal_wise_total_payment_list:
                    journal_wise_total_payment_list.append(
                        {"name": journal.name, "total": paid_total})
        else:
            journal_wise_total_payment_list = []

        return {
            'currency_precision': user_currency.decimal_places,
            'total_paid': user_currency.round(total),
            'payments': journal_wise_total_payment_list,
            'company_name': self.env.user.company_id.name,
            'taxes': taxes.values(),
            'products': sorted([{
                'product_id': product.id,
                'product_name': product.name,
                'code': product.default_code,
                'quantity': qty,
                'price_unit': price_unit,
                'uom': product.uom_id.name
            } for (product, price_unit), qty in products_purchased.items()], key=lambda l: l['product_name'])
        }

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        company_ids = self.env['res.company'].browse(data['company_ids'])
        data.update(self.get_sale_details(
            data['date_start'], data['date_stop'], company_ids, data['state']))
        return data
