# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import xlwt
import base64
from io import BytesIO
from odoo.tools import float_is_zero


class BillPaymentReportXls(models.Model):
    _name = 'bill.payment.report.xls'
    _description = 'Bill Payment Xls Report'
    excel_file = fields.Binary('Download report Excel')
    file_name = fields.Char('Excel File', size=64, readonly=True)

    def download_report(self):
        return{
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=bill.payment.report.xls&field=excel_file&download=true&id=%s&filename=%s' % (self.id, self.file_name),
            'target': 'new',
        }


class ShPaymentPurchaseReportWizard(models.TransientModel):
    _name = "sh.purchase.payment.report.wizard"
    _description = 'bill payment report wizard Model'

    @api.model
    def default_company_ids(self):
        is_allowed_companies = self.env.context.get(
            'allowed_company_ids', False)
        if is_allowed_companies:
            return is_allowed_companies
        return

    date_start = fields.Date(
        string="Start Date", required=True, default=fields.Date.today)
    date_end = fields.Date(
        string="End Date", required=True, default=fields.Date.today)

    state = fields.Selection([
        ('all', 'All'),
        ('open', 'Open'),
        ('paid', 'Paid'),
    ], string='Status', default='all')

    user_ids = fields.Many2many(
        comodel_name='res.users',
        relation='rel_sh_payment_purchase_report_wizard_res_user',
        string='Purchase Representative')

    company_ids = fields.Many2many(
        'res.company', string='Companies', default=default_company_ids)

    @api.model
    def default_get(self, fields):
        rec = super(ShPaymentPurchaseReportWizard, self).default_get(fields)

        search_users = self.env["res.users"].search([
            ('id', '=', self.env.user.id),
        ], limit=1)
        if self.env.user.has_group('purchase.group_purchase_manager'):
            rec.update({
                "user_ids": [(6, 0, search_users.ids)],
            })
        else:
            rec.update({
                "user_ids": [(6, 0, [self.env.user.id])],
            })
        return rec

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        if self.filtered(lambda c: c.date_end and c.date_start > c.date_end):
            raise ValidationError(_('start date must be less than end date.'))

    def print_report(self):
        datas = self.read()[0]

        return self.env.ref('sh_purchase_reports.sh_payment_purchase_report_action').report_action([], data=datas)

    def print_xls_report(self):
        workbook = xlwt.Workbook(encoding='utf-8')
        heading_format = xlwt.easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = xlwt.easyxf(
            'font:bold True,height 215;pattern: pattern solid, fore_colour gray25;align: horiz center')
        total_bold = xlwt.easyxf('font:bold True')
        bold_center = xlwt.easyxf(
            'font:height 240,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center;')
        worksheet = workbook.add_sheet('Bill Payment Report', bold_center)
        worksheet.write_merge(
            0, 1, 0, 7, 'Bill Payment Report', heading_format)
        worksheet.write_merge(2, 2, 0, 7, str(
            self.date_start) + " to " + str(self.date_end), bold)
        account_payment_obj = self.env["account.payment"]
        account_journal_obj = self.env["account.journal"]
        currency = False
        j_refund = 0.0
        data = {}
        grand_journal_dic = {}
        user_data_dic = {}
        search_user = self.env['res.users'].sudo().search(
            [('id', 'in', self.user_ids.ids)])
        journal_domain = [('type','in',['bank','cash'])]
        if self.company_ids:
            journal_domain.append(('company_id','in',self.company_ids.ids))
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
        if search_user:
            for user_id in search_user:
                domain = [
                    ("date", ">=", self.date_start),
                    ("date", "<=", self.date_end),
                    ("payment_type", "in", ["inbound", "outbound"]),
                    ("partner_type", "in", ["supplier"])
                ]
                state = self.state
                if data.get('company_ids', False):
                    domain.append(
                        ("company_id", "in", self.company_ids.ids))
                # journal wise payment first we total all bank, cash etc etc.
                payments = account_payment_obj.sudo().search(domain)
                invoice_pay_dic = {}
                invoice_ids = []
                if payments and search_journals:
                    for journal_wise_payment in payments.filtered(lambda x: x.journal_id.id in search_journals.ids):
                        if journal_wise_payment.reconciled_bill_ids:
                            invoices = False
                            if state:
                                if state == 'all':
                                    invoices = journal_wise_payment.reconciled_bill_ids.sudo().filtered(
                                        lambda x: x.state not in ['draft', 'cancel'] and x.invoice_user_id.id == user_id.id)
                                elif state == 'open' or state == 'paid':
                                    invoices = journal_wise_payment.reconciled_bill_ids.sudo().filtered(
                                        lambda x: x.state in ['posted'] and x.invoice_user_id.id == user_id.id)
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
                                    for partial in partials.sudo().filtered(lambda x: x.max_date >= self.date_start and x.max_date <= self.date_end):
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
                                                invoice_pay_dic.update({invoice.name: {counterpart_line.payment_id.journal_id.name: payment_amount, "Total": payment_amount, "Bill": invoice.name, "Vendor": invoice.partner_id.name, "Bill Date": str(
                                                    invoice.invoice_date), "Purchase Representative": invoice.user_id.name if invoice.user_id else "", "style": ''}})

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
                                                invoice_pay_dic.update({invoice.name: {counterpart_line.payment_id.journal_id.name: -1 * (payment_amount), "Total": -1 * (payment_amount), "Bill": invoice.name, "Vendor": invoice.partner_id.name, "Bill Date": str(
                                                    invoice.invoice_date), "Purchase Representative": invoice.user_id.name if invoice.user_id else "", "style": 'font:color red'}})

                # all final list and [{},{},{}] format
                # here we get the below total.
                # total journal amount is a grand total and format is : {} just a dictionary
                final_list = []
                total_journal_amount = {}
                for key, value in invoice_pay_dic.items():
                    final_list.append(value)
                    for col_name in final_total_col_list:
                        if total_journal_amount.get(col_name, False):
                            total = total_journal_amount.get(col_name)
                            total += value.get(col_name, 0.0)

                            total_journal_amount.update({col_name: total})

                        else:
                            total_journal_amount.update(
                                {col_name: value.get(col_name, 0.0)})

                # finally make user wise dic here.
                search_user = self.env['res.users'].search([
                    ('id', '=', user_id.id)
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
            'columns': final_col_list,
            'user_data_dic': user_data_dic,
            'currency': currency,
            'grand_journal_dic': grand_journal_dic,
        })
        row = 3
        col = 0

        for user in user_data_dic.keys():
            pay_list = []
            pay_list.append(user_data_dic.get(user).get('pay', []))
            row = row + 2
            worksheet.write_merge(
                row, row, 0, 7, "Purchase Representative: " + user, bold_center)
            row = row + 2
            col = 0
            for column in data.get('columns'):
                worksheet.col(col).width = int(15 * 260)
                worksheet.write(row, col, column, bold)
                col = col + 1
            for p in pay_list:
                row = row + 1
                col = 0
                for dic in p:
                    row = row + 1
                    col = 0
                    for column in data.get('columns'):
                        style = xlwt.easyxf(dic.get('style', ''))
                        worksheet.write(row, col, dic.get(column, 0), style)
                        col = col + 1
            row = row + 1
            col = 3
            worksheet.col(col).width = int(15 * 260)
            worksheet.write(row, col, "Total", total_bold)
            col = col + 1
            if user_data_dic.get(user, False):
                grand_total = user_data_dic.get(user).get('grand_total', {})
                if grand_total:
                    for column in data.get('columns'):
                        if column not in ['Bill', 'Bill Date', 'Purchase Representative', 'Vendor']:
                            worksheet.write(row, col, grand_total.get(
                                column, 0), total_bold)
                            col = col + 1
        row = row + 2
        worksheet.write_merge(row, row, 0, 1, "Payment Method", bold)
        row = row + 1
        worksheet.write(row, 0, "Name", bold)
        worksheet.write(row, 1, "Total", bold)
        for column in data.get('columns'):
            col = 0
            if column not in ["Bill", "Bill Date", "Purchase Representative", "Vendor"]:
                row = row + 1
                worksheet.col(col).width = int(15 * 260)
                worksheet.write(row, col, column)
                col = col + 1
                worksheet.write(row, col, grand_journal_dic.get(column, 0))
        if grand_journal_dic.get('Refund', False):
            row = row + 1
            col = 0
            worksheet.col(col).width = int(15 * 260)
            worksheet.write(row, col, "Refund")
            worksheet.write(row, col + 1, grand_journal_dic.get('Refund', 0.0))

        filename = ('Bill Payment Report' + '.xls')
        fp = BytesIO()
        workbook.save(fp)

        export_id = self.env['bill.payment.report.xls'].sudo().create({
            'excel_file': base64.encodebytes(fp.getvalue()),
            'file_name': filename,
        })

        fp.close()
        return{
            'type': 'ir.actions.act_window',
            'name': 'Bill Payment Report',
            'res_id': export_id.id,
            'res_model': 'bill.payment.report.xls',
            'view_mode': 'form',
            'target': 'new',
        }
