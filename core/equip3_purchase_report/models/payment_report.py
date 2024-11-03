# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import api, models
from odoo.tools import float_is_zero
import datetime


class PaymentRpoert(models.AbstractModel):
    _inherit = 'report.sh_purchase_reports.sh_payment_pr_report_doc'

    @api.model
    def _get_report_values(self, docids, data=None):

        data = dict(data or {})
        account_payment_obj = self.env["account.payment"]
        account_journal_obj = self.env["account.journal"]

        journal_domain = [('type','in',['bank','cash'])]
        if data.get('company_ids', False):
            journal_domain.append(('company_id','in',data.get('company_ids', False)))
        search_journals = account_journal_obj.sudo().search(journal_domain)

        final_col_list = ["Bill", "Bill Date",
                          "Purchase Representative", "Vendor"]
        final_total_col_list = []
        for journal in search_journals:
            if journal.name not in final_col_list:
                final_col_list.append(journal.name)
            if journal.name not in final_total_col_list:
                final_total_col_list.append(journal.name)

        final_col_list.append("Total")
        final_total_col_list.append("Total")

        currency = False
        grand_journal_dic = {}
        j_refund = 0.0

        user_data_dic = {}
        if data.get("user_ids", False):

            for user_id in data.get("user_ids"):

                domain = [
                    ("date", ">=", data["date_start"]),
                    ("date", "<=", data["date_end"]),
                    ("payment_type", "in", ["inbound", "outbound"]),
                    ("partner_type", "in", ["supplier"])
                ]
                state = data.get("state")
                if data.get('company_ids', False):
                    domain.append(
                        ("company_id", "in", data.get('company_ids', False)))
                # journal wise payment first we total all bank, cash etc etc.
                payments = account_payment_obj.sudo().search(domain)
                invoice_pay_dic = {}
                invoice_ids = []
                if payments and search_journals:
                    for journal_wise_payment in payments.filtered(lambda x: x.journal_id.id in search_journals.ids):
                        if journal_wise_payment.reconciled_bill_ids:
                            invoices = False
                            if data.get("state", False):
                                if state == 'all':
                                    invoices = journal_wise_payment.reconciled_bill_ids.sudo().filtered(
                                        lambda x: x.state not in ['draft', 'cancel'] and x.invoice_user_id.id == user_id)
                                elif state == 'open' or state == 'paid':
                                    invoices = journal_wise_payment.reconciled_bill_ids.sudo().filtered(
                                        lambda x: x.state in ['posted'] and x.invoice_user_id.id == user_id)
                            for invoice in invoices:
                                if invoice.id not in invoice_ids:
                                    invoice_ids.append(invoice.id)
                                else:
                                    continue
                                pay_term_line_ids = invoice.line_ids.filtered(
                                    lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                                partials = pay_term_line_ids.mapped(
                                    'matched_debit_ids') + pay_term_line_ids.mapped('matched_credit_ids')
                                if partials:
                                    start_date = datetime.datetime.strptime(
                                        data['date_start'], "%Y-%m-%d").date()
                                    end_date = datetime.datetime.strptime(
                                        data['date_end'], "%Y-%m-%d").date()
                                    for partial in partials.sudo().filtered(lambda x: x.max_date >= start_date and x.max_date <= end_date):
                                        counterpart_lines = partial.debit_move_id + partial.credit_move_id
                                        counterpart_line = counterpart_lines.filtered(
                                            lambda line: line.id not in invoice.line_ids.ids)
                                        foreign_currency = invoice.currency_id if invoice.currency_id != self.env.company.currency_id else False
                                        if foreign_currency and partial.currency_id == foreign_currency:
                                            payment_amount = partial.amount_currency
                                        else:
                                            payment_amount = partial.company_currency_id._convert(
                                                partial.amount, invoice.currency_id, self.env.company, invoice.invoice_date)
                                        if float_is_zero(payment_amount, precision_rounding=invoice.currency_id.rounding):
                                            continue
                                        if not currency:
                                            currency = invoice.currency_id
                                        if invoice.move_type == "in_invoice":
                                            if invoice_pay_dic.get(invoice.name, False):
                                                pay_dic = invoice_pay_dic.get(
                                                    invoice.name)
                                                total = pay_dic.get("Total")
                                                if pay_dic.get(counterpart_line.payment_id.journal_id.name, False):
                                                    amount = pay_dic.get(
                                                        counterpart_line.payment_id.journal_id.name)
                                                    total += payment_amount
                                                    amount += payment_amount
                                                    pay_dic.update(
                                                        {counterpart_line.payment_id.journal_id.name: amount, "Total": total})
                                                else:
                                                    total += payment_amount
                                                    pay_dic.update(
                                                        {counterpart_line.payment_id.journal_id.name: payment_amount, "Total": total})

                                                invoice_pay_dic.update(
                                                    {invoice.name: pay_dic})
                                            else:
                                                invoice_pay_dic.update({invoice.name: {counterpart_line.payment_id.journal_id.name: payment_amount, "Total": payment_amount, "Bill": invoice.name, "Vendor": invoice.partner_id.name,
                                                                                       "Bill Date": invoice.invoice_date, "Purchase Representative": invoice.user_id.name if invoice.user_id else "", "style": 'border: 1px solid black;'}})

                                        if invoice.move_type == "in_refund":
                                            j_refund += payment_amount
                                            if invoice_pay_dic.get(invoice.name, False):
                                                pay_dic = invoice_pay_dic.get(
                                                    invoice.name)
                                                total = pay_dic.get("Total")
                                                if pay_dic.get(counterpart_line.payment_id.journal_id.name, False):
                                                    amount = pay_dic.get(
                                                        counterpart_line.payment_id.journal_id.name)
                                                    total -= payment_amount
                                                    amount -= payment_amount
                                                    pay_dic.update(
                                                        {counterpart_line.payment_id.journal_id.name: amount, "Total": total})
                                                else:
                                                    total -= payment_amount
                                                    pay_dic.update(
                                                        {counterpart_line.payment_id.journal_id.name: -1 * (payment_amount), "Total": total})

                                                invoice_pay_dic.update(
                                                    {invoice.name: pay_dic})

                                            else:
                                                invoice_pay_dic.update({invoice.name: {counterpart_line.payment_id.journal_id.name: -1 * (payment_amount), "Total": -1 * (payment_amount), "Bill": invoice.name, "Vendor": invoice.partner_id.name,
                                                                                       "Bill Date": invoice.invoice_date, "Purchase Representative": invoice.user_id.name if invoice.user_id else "", "style": 'border: 1px solid black;color:red'}})
                # all final list and [{},{},{}] format
                # here we get the below total.
                # total journal amount is a grand total and format is : {} just a dictionary
                final_list = []
                total_journal_amount = {}
                for value in invoice_pay_dic.items():
                    final_list.append(value)
                    for col_name in final_total_col_list:
                        if total_journal_amount.get(col_name, False):
                            total = total_journal_amount.get(col_name)
                            total += value[1].get(col_name, 0.0)

                            total_journal_amount.update({col_name: total})

                        else:
                            total_journal_amount.update(
                                {col_name: value[1].get(col_name, 0.0)})

                # finally make user wise dic here.
                search_user = self.env['res.users'].sudo().search([
                    ('id', '=', user_id)
                ], limit=1)
                if search_user:
                    user_data_dic.update({
                        search_user.name: {'pay': final_list,
                                           'grand_total': total_journal_amount}
                    })

                for col_name in final_total_col_list:
                    j_total = 0.0
                    j_total = total_journal_amount.get(col_name, 0.0)
                    j_total += grand_journal_dic.get(col_name, 0.0)
                    grand_journal_dic.update({col_name: j_total})

            j_refund = j_refund * -1
            grand_journal_dic.update({'Refund': j_refund})
        data.update({
            'date_start': data['date_start'],
            'date_end': data['date_end'],
            'columns': final_col_list,
            'user_data_dic': user_data_dic,
            'currency': currency,
            'grand_journal_dic': grand_journal_dic,
        })
        return data