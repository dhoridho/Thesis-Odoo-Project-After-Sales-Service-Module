import time
from odoo import fields, models, api, _
from datetime import datetime, date, timedelta
import io
import json
from odoo.exceptions import AccessError, UserError, AccessDenied
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class TaxReportView(models.TransientModel):
    _inherit = "account.common.report"
    _name = 'tax.report'

    account_ids = fields.Many2many(
        "account.account",
        string="Accounts", check_company=True,
    )
    tax_ids = fields.Many2many(
        "account.tax",
        string="Taxes", check_company=True,
    )
    company_ids = fields.Many2many(
        "res.company",
        string="Companies"
    )
    target_move = fields.Selection([('posted', 'Posted Entries'),
                                    ('unposted', 'Unposted Entries'),
                                    ], string='Target Moves', default="posted")
    branch_ids = fields.Many2many(
        "res.branch",
        string="Branch"
    )

    @api.model
    def view_report(self, option, **kw):
        r = self.env['tax.report'].search([('id', '=', option[0])])
        data = {
            'model': self,
            'accounts': r.account_ids,
            'target_move': r.target_move,
            'tax_ids': r.tax_ids,
            'company_ids': r.company_ids,
            'branch_ids': r.branch_ids,
        }

        start_date = date.today().replace(day=1)
        next_date = start_date.replace(day=28) + timedelta(days=4)
        end_date = next_date - timedelta(days=next_date.day)
        data.update({
            'date_from': start_date,
            'date_to': end_date
        })
        if r.date_from:
            data.update({
                'date_from': r.date_from,
            })
        if r.date_to:
            data.update({
                'date_to': r.date_to,
            })

        filters = self.get_filter(option)
        records = self._get_report_values(data)
        currency = self._get_currency()

        currency_ids = self.env['res.currency'].search([('active', '=', True)])
        currencies = [{
            'name': currency_id.name,
            'id': currency_id.id,
        } for currency_id in currency_ids]

        sort = kw.get('sort')
        sort_type = kw.get('sort_type')
        str_sort_list = ['account_name','ref_no','partner']
        if sort:
            for rec in records:
                for line in rec.get('record_lines'):
                    if sort_type == 'desc':
                        if sort in str_sort_list:
                            line['tax_lines'] = sorted(line['tax_lines'], key=lambda d: d[sort].lower(), reverse=True)
                        else:
                            line['tax_lines'] = sorted(line['tax_lines'], key=lambda d: d[sort], reverse=True)
                    else:
                        if sort in str_sort_list:
                            line['tax_lines'] = sorted(line['tax_lines'], key=lambda d: d[sort].lower())
                        else:
                            line['tax_lines'] = sorted(line['tax_lines'], key=lambda d: d[sort])

        return {
            'name': "Tax Report",
            'type': 'ir.actions.client',
            'tag': 'account_tax_report',
            'filters': filters,
            'report_lines': records,
            'currency': currency,
            'currencies': currencies,
        }

    @api.model
    def _get_currency(self):
        tax_report = self.search([], limit=1, order="id desc")
        report_currency_id = tax_report.report_currency_id
        lang = self.env.user.lang
        if not lang:
            lang = 'en_US'
        lang = lang.replace("_", '-')
        if not report_currency_id:
            currency_array = [self.env.company.currency_id.symbol,
                              self.env.company.currency_id.position, lang]
        else:
            currency_array = [report_currency_id.symbol,
                              report_currency_id.position, lang]
        return currency_array

    def _get_report_values(self, data):
        lines = []
        if data.get('tax_ids'):
            tax_ids = data.get('tax_ids')
        else:
            tax_ids = self.env['account.tax'].search([])
        if data.get('company_ids'):
            company_ids = data.get('company_ids')
        else:
            company_ids = self.env['res.company'].search([])
        if data.get('branch_ids'):
            branch_ids = data.get('branch_ids')
        else:
            branch_ids = self.env['res.branch'].search([])
        if data.get('accounts'):
            account_ids = data.get('accounts')
        else:
            account_ids = self.env['account.account'].search([])

        tax_report = self.search([], limit=1, order="id desc")

        report_currency_id = tax_report.report_currency_id
        currency_rate = 0
        if not report_currency_id:
            currency_id = self.env.company.currency_id
        else:
            currency_id = report_currency_id
            if data.get('date_from') and data.get('date_to'):
                rate_ids = currency_id.rate_ids.filtered(lambda r: r.name >= data.get('date_from') and r.name <= data.get('date_to')).sorted(key=lambda r: r.name)
                if rate_ids:
                    currency_rate = rate_ids[-1].mr_rate
                else:
                    currency_rate = currency_id.rate
            elif data.get('date_from'):
                rate_ids = currency_id.rate_ids.filtered(lambda r: r.name >= data.get('date_from')).sorted(key=lambda r: r.name)
                if rate_ids:
                    currency_rate = rate_ids[-1].mr_rate
                else:
                    currency_rate = currency_id.rate
            elif data.get('date_to'):
                rate_ids = currency_id.rate_ids.filtered(lambda r: r.name <= data.get('date_to')).sorted(key=lambda r: r.name)
                if rate_ids:
                    currency_rate = rate_ids[-1].mr_rate
                else:
                    currency_rate = currency_id.rate
            else:
                currency_rate = currency_id.rate

        filter_tax_ids = tax_ids.filtered(lambda r: r.company_id.id in company_ids.ids)
        tax_final_data = []
        domain = [
            ('date', '>=', data.get('date_from')),
            ('date','<=', data.get('date_to')),
            ('company_id', 'in', company_ids.ids),
            ('branch_id', 'in', branch_ids.ids),
            ('account_id', 'in', account_ids.ids),
            ('tax_ids', '=', False),
            ('tax_line_id', '!=', False),
        ]
        if data.get('target_move') == "posted":
            domain += [('move_id.state', '=', 'posted')]
        else:
            domain += [('move_id.state', '=', 'draft')]

        type_tax_use = sorted(list(set(filter_tax_ids.mapped('type_tax_use'))), reverse=True)
        tax_summary = False
        for tax_type in type_tax_use:
            final_data = []
            tax_vals = {
                'type': tax_type,
            }
            tax_final_untaxed_amount_total = 0
            tax_final_gst_total = 0
            tax_final_amount_total = 0
            for tax in filter_tax_ids.filtered(lambda r:r.type_tax_use == tax_type):
                vals = {
                    'tax_id': tax.id,
                    'type_tax_use': tax.type_tax_use,
                    'tax_name': tax.name,
                    'currency_position': currency_id.position,
                    'currency_symbol': currency_id.symbol,
                    'tax_lines': [],
                }
                move_line_domain = domain + [('tax_line_id', '=', tax.id)]
                account_move_lines = self.env['account.move.line'].search(move_line_domain)
                final_untaxed_amount_total = 0.0
                final_gst_total = 0.0
                final_amount_total = 0.0
                for line in account_move_lines:
                    amount_untaxed = line.move_id.amount_untaxed
                    tax_amount = line.move_id.amount_tax
                    total = line.move_id.amount_untaxed + line.move_id.amount_tax
                    if currency_rate > 0:
                        total = round(total * currency_rate, 2)
                        amount_untaxed = round(amount_untaxed * currency_rate, 2)
                        tax_amount = round(tax_amount * currency_rate, 2)
                    if tax.type_tax_use == 'sale':
                        total = -(total)
                        amount_untaxed = -(amount_untaxed)
                        tax_amount = -(tax_amount)

                    tax_line_vals = {
                        'move_id': line.move_id.id,
                        'reference': line.move_id.name,
                        'date': line.date.strftime(DEFAULT_SERVER_DATE_FORMAT),
                        'account': line.account_id.display_name,
                        'account_name': line.account_id.name,
                        'ref_no': line.move_id.payment_reference,
                        'partner': line.partner_id.name,
                        'untaxed_amount': amount_untaxed,
                        'tax_amount': tax_amount,
                        'amount_total': total,
                        'model': 'account.move',
                    }
                    vals['tax_lines'].append(tax_line_vals)
                    final_untaxed_amount_total += amount_untaxed
                    final_gst_total += tax_amount
                    final_amount_total += total

                voucher_line_domain = [
                    ('voucher_id.date', '>=', data.get('date_from')),
                    ('voucher_id.date','<=', data.get('date_to')),
                    ('company_id', 'in', company_ids.ids),
                    ('voucher_id.branch_id', 'in', branch_ids.ids),
                    ('account_id', 'in', account_ids.ids),
                    ('tax_ids', 'in', [tax.id]),
                    ('voucher_id.state', '=', 'posted'),
                ]
                account_voucher_lines = self.env['account.voucher.line'].search(voucher_line_domain)
                voucher_id_list = []
                for line in account_voucher_lines:
                    if line.voucher_id.id not in voucher_id_list:
                        voucher_id_list.append(line.voucher_id.id)
                        amount_untaxed = line.voucher_id.untax_amount
                        tax_amount = line.voucher_id.tax_amount
                        total = amount_untaxed + tax_amount
                        if currency_rate > 0:
                            total = round(total * currency_rate, 2)
                            amount_untaxed = round(amount_untaxed * currency_rate, 2)
                            tax_amount = round(tax_amount * currency_rate, 2)
                        if tax.type_tax_use == 'sale':
                            total = -(total)
                            amount_untaxed = -(amount_untaxed)
                            tax_amount = -(tax_amount)

                        tax_line_vals = {
                            'move_id': line.voucher_id.id,
                            'reference': line.voucher_id.number,
                            'date': line.voucher_id.date.strftime(DEFAULT_SERVER_DATE_FORMAT),
                            'account': '',
                            'account_name': '',
                            'ref_no': '',
                            'partner': line.voucher_id.partner_id.name or '',
                            'untaxed_amount': amount_untaxed,
                            'tax_amount': tax_amount,
                            'amount_total': total,
                            'model': 'account.voucher',
                        }
                        vals['tax_lines'].append(tax_line_vals)
                        final_untaxed_amount_total += amount_untaxed
                        final_gst_total += tax_amount
                        final_amount_total += total

                vals['total_line'] = {
                    'name': 'Total ' + tax.name,
                    'untaxed_amount_total': final_untaxed_amount_total,
                    'gst_total': final_gst_total,
                    'amount_total': final_amount_total
                }
                vals.update({
                    'untaxed_amount_total': final_untaxed_amount_total,
                    'gst_total': final_gst_total,
                    'amount_total': final_amount_total
                })
                tax_final_untaxed_amount_total += final_untaxed_amount_total
                tax_final_gst_total += final_gst_total
                tax_final_amount_total += final_amount_total

                if tax.amount == 0.0:
                    tax_zero_amount_domain = [
                                ('date', '>=', data.get('date_from')),
                                ('date','<=', data.get('date_to')),
                                ('company_id', 'in', company_ids.ids),
                                ('branch_id', 'in', branch_ids.ids),
                                ('account_id', 'in', account_ids.ids),
                            ]
                    if data.get('target_move') == "posted":
                        domain += [('move_id.state', '=', 'posted')]
                    else:
                        domain += [('move_id.state', '=', 'draft')]
                    tax_zero_amount_domain = tax_zero_amount_domain + [('tax_ids', 'in', tax.ids)]
                    tax_zero_amount = self.env['account.move.line'].search(tax_zero_amount_domain)
                    for line in tax_zero_amount:
                        tax_line_vals = {
                            'move_id': line.move_id.id,
                            'reference': line.move_id.name or '',
                            'date': line.date.strftime(DEFAULT_SERVER_DATE_FORMAT),
                            'account': '',
                            'account_name': '',
                            'ref_no': line.move_id.payment_reference or '',
                            'partner': line.partner_id.name or '',
                            'untaxed_amount': line.price_subtotal,
                            'tax_amount': line.price_tax,
                            'amount_total': line.price_total,
                            'model': 'account.move',
                        }
                        vals['tax_lines'].append(tax_line_vals)                        
                final_data.append(vals)
            tax_vals.update({
                'record_lines': final_data,
                'tax_final_untaxed_amount_total': tax_final_untaxed_amount_total,
                'tax_final_gst_total': tax_final_gst_total,
                'tax_final_amount_total': tax_final_amount_total,
            })
            tax_final_data.append(tax_vals)

            if not tax_summary:
                sales_tax_line = list(filter(lambda line_tax: line_tax['type'] == 'sale', tax_final_data))
                purchase_tax_line = list(filter(lambda line_tax: line_tax['type'] == 'purchase', tax_final_data))
                if sales_tax_line and purchase_tax_line:
                    tax_final_untaxed_amount_subtotal = sales_tax_line[0]['tax_final_untaxed_amount_total'] + purchase_tax_line[0]['tax_final_untaxed_amount_total']
                    tax_final_gst_subtotal = sales_tax_line[0]['tax_final_gst_total'] + purchase_tax_line[0]['tax_final_gst_total']
                    tax_final_amount_subtotal = sales_tax_line[0]['tax_final_amount_total'] + purchase_tax_line[0]['tax_final_amount_total']
                    if tax_final_amount_subtotal < 0:
                        name_tag_summary = "PPN (Kurang Bayar)"
                    elif tax_final_amount_subtotal > 0:
                        name_tag_summary = "PPN (Lebih Bayar)"
                    else:
                        name_tag_summary = "PPN (Nihil)"
                    summary_tax_sales_purchase = {
                        'type':'summary',
                        'name_tag_summary': name_tag_summary,
                        'record_lines' : [],
                        'tax_final_untaxed_amount_total': tax_final_untaxed_amount_subtotal,
                        'tax_final_gst_total': tax_final_gst_subtotal,
                        'tax_final_amount_total': tax_final_amount_subtotal,
                    }
                    tax_final_data.append(summary_tax_sales_purchase)
                    tax_summary = True

        return tax_final_data

    def get_filter(self, option):
        data = self.get_filter_data(option)

        filters = {}
        if data.get('account_ids', []):
            filters['accounts'] = self.env['account.account'].browse(data.get('account_ids', [])).mapped('code')
        else:
            filters['accounts'] = ['All Payable and Receivable']

        if data.get('company_ids', []):
            filters['company_ids'] = self.env['res.company'].browse(data.get('company_ids', [])).mapped('name')
        else:
            filters['company_ids'] = ['ALL']

        if data.get('branch_ids', []):
            filters['branch_ids'] = self.env['res.branch'].browse(data.get('branch_ids', [])).mapped('name')
        else:
            filters['branch_ids'] = ['ALL']

        if data.get('tax_ids', []):
            filters['tax_ids'] = self.env['account.tax'].browse(data.get('tax_ids', [])).mapped('name')
        else:
            filters['tax_ids'] = ['ALL']

        if data.get('target_move'):
            filters['target_move'] = data.get('target_move').capitalize()
        if data.get('date_from'):
            filters['date_from'] = data.get('date_from')
        if data.get('date_to'):
            filters['date_to'] = data.get('date_to')

        filters['company_id'] = ''
        filters['branch_id'] = ''
        filters['accounts_list'] = data.get('accounts_list')
        filters['companies_list'] = data.get('companies')
        filters['branch_list'] = data.get('branch')
        filters['taxes'] = data.get('taxes')

        filters['company_name'] = data.get('company_name')
        filters['branch_name'] = data.get('branch_name')

        filters['target_move'] = data.get('target_move').capitalize()
        return filters

    def get_filter_data(self, option):
        r = self.env['tax.report'].search([('id', '=', option[0])])
        default_filters = {}
        company_id = self.env.company
        company_ids = self.company_ids or self.env.company
        company_domain = [('company_id', 'in', company_ids.ids)]
        accounts = self.account_ids if self.account_ids else self.env['account.account'].search(company_domain)
        companies = self.company_ids if self.company_ids else self.env['res.company'].search([])
        branch = self.branch_ids if self.branch_ids else self.env['res.branch'].search([('id','in',self.env.context.get('allowed_branch_ids'))])
        taxes = self.tax_ids if self.tax_ids else self.env['account.tax'].search(company_domain)

        filter_dict = {
            'account_ids': r.account_ids.ids,
            'company_id': company_id.id,
            'date_from': r.date_from,
            'date_to': r.date_to,
            'target_move': r.target_move,
            'accounts_list': [(a.id, a.name) for a in accounts],
            'companies': [(c.id, c.name) for c in companies],
            'branch': [(c.id, c.name) for c in branch],
            'taxes': [(t.id, t.name) for t in taxes],
            'company_name': company_id and company_id.name,
        }
        filter_dict.update(default_filters)
        return filter_dict

    @api.model
    def create(self, vals):
        vals['target_move'] = 'posted'
        res = super(TaxReportView, self).create(vals)
        return res

    def write(self, vals):
        if vals.get('target_move'):
            vals.update({'target_move': vals.get('target_move').lower()})
        if vals.get('account_ids'):
            vals.update({'account_ids': [(4, j) for j in vals.get('account_ids')]})
        if not vals.get('account_ids'):
            vals.update({'account_ids': [(5,)]})

        if vals.get('company_ids'):
            vals.update({'company_ids': [(4, j) for j in vals.get('company_ids')]})
        if not vals.get('company_ids'):
            vals.update({'company_ids': [(5,)]})

        if vals.get('branch_ids'):
            vals.update({'branch_ids': [(6, 0, vals.get('branch_ids'))]})
        if not vals.get('branch_ids'):
            vals.update({'branch_ids': [(5,)]})

        if vals.get('tax_ids'):
            vals.update({'tax_ids': [(4, j) for j in vals.get('tax_ids')]})
        if not vals.get('tax_ids'):
            vals.update({'tax_ids': [(5,)]})

        res = super(TaxReportView, self).write(vals)
        return res

    def get_dynamic_xlsx_report(self, data, response, report_data, dfr_data):
        report_data_main = json.loads(report_data)
        output = io.BytesIO()
        filters = json.loads(data)

        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        head = workbook.add_format({'bold': True})
        sub_heading = workbook.add_format({'bold': True, 'border': 1, 'border_color': 'black'})
        txt = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        txt_l = workbook.add_format({'border': 1, 'bold': True, 'num_format': '#,##0.00'})
        sheet.merge_range('A2:D3',
                          filters.get('company_name') + ':' + ' Tax Report',
                          head)
        date_head = workbook.add_format({'bold': True})
        date_style = workbook.add_format({})
        if filters.get('date_from'):
            sheet.merge_range('A4:B4', 'From: ' + filters.get('date_from'),
                              date_head)
        if filters.get('date_to'):
            sheet.merge_range('C4:D4', 'To: ' + filters.get('date_to'),
                              date_head)
        sheet.merge_range('E5:F5',
                          'Target Moves: ' + filters.get('target_move'),
                          date_head)
        sheet.merge_range('A5:D5',
                          'Account Type: ' + ', '.join([lt or '' for lt in
                                                        filters[
                                                            'accounts']]),
                          date_head)

        # sheet.set_column('A:A', 100, '')
        # sheet.set_column('A:Z', 25, '')
        sheet.set_column('A:A', 25, '')
        sheet.set_column('B:B', 15, '')
        sheet.set_column('C:C', 25, '')
        sheet.set_column('D:D', 25, '')
        sheet.set_column('E:E', 25, '')
        sheet.set_column('F:F', 25, '')
        sheet.set_column('G:G', 25, '')
        sheet.set_column('H:H', 25, '')
        sheet.set_column('I:I', 25, '')

        row = 5
        col = 0
        for data_report in report_data_main:
            row += 1
            sheet.merge_range(row, col, row, col + 7, data_report['type'], txt_l)
            row += 1
            sheet.write(row, col, '', sub_heading)
            if data_report['type'] == 'summary':
                sheet.write(row, col + 1, '', sub_heading)
                sheet.write(row, col + 2, '', sub_heading)
                sheet.write(row, col + 3, '', sub_heading)
                sheet.write(row, col + 4, '', sub_heading)
            else:
                sheet.write(row, col + 1, 'Date', sub_heading)
                sheet.write(row, col + 2, 'Account', sub_heading)
                sheet.write(row, col + 3, 'Ref No', sub_heading)
                sheet.write(row, col + 4, 'Partner', sub_heading)
            sheet.write(row, col + 5, 'Untaxed Amount', sub_heading)
            sheet.write(row, col + 6, 'Tax Amount', sub_heading)
            sheet.write(row, col + 7, 'Total', sub_heading)
            for rec_data in data_report['record_lines']:
                row += 1
                sheet.merge_range(row, col, row, col + 4, rec_data['tax_name'], txt_l)
                sheet.write(row, col + 5, rec_data['untaxed_amount_total'], txt_l)
                sheet.write(row, col + 6, rec_data['gst_total'], txt_l)
                sheet.write(row, col + 7, rec_data['amount_total'], txt_l)
                for line_data in rec_data['tax_lines']:
                    row += 1
                    sheet.write(row, col, line_data['reference'], txt)
                    sheet.write(row, col + 1, line_data['date'], txt)
                    sheet.write(row, col + 2, line_data['account'], txt)
                    sheet.write(row, col + 3, line_data['ref_no'], txt)
                    sheet.write(row, col + 4, line_data['partner'], txt)
                    sheet.write(row, col + 5, line_data['untaxed_amount'], txt)
                    sheet.write(row, col + 6, line_data['tax_amount'], txt)
                    sheet.write(row, col + 7, line_data['amount_total'], txt)
            row += 1
            if data_report['type'] == 'summary':
                sheet.merge_range(row, col, row, col + 4, data_report['name_tag_summary'], txt_l)
            else:
                sheet.merge_range(row, col, row, col + 4, 'Total ' + data_report['type'], txt_l)
            sheet.write(row, col + 5, data_report['tax_final_untaxed_amount_total'], txt_l)
            sheet.write(row, col + 6, data_report['tax_final_gst_total'], txt_l)
            sheet.write(row, col + 7, data_report['tax_final_amount_total'], txt_l)
            row += 1
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()