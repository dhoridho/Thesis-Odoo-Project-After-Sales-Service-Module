# See LICENSE file for full copyright and licensing details.

import base64
import io

from odoo import fields, models
from odoo.tools.misc import xlwt


class ExcelExportTrial(models.TransientModel):
    _name = "excel.export.trial"
    _description = "Excel Export Trial"

    file = fields.Binary(
        "Click On Download Link To Download Xls File",
        readonly=True)
    name = fields.Char("Name", default='Trial_Balance.xls')


class AccountBalanceReport(models.TransientModel):
    _inherit = "account.common.account.report"
    _name = 'account.balance.report'
    _description = 'Trial Balance Report'

    journal_ids = fields.Many2many('account.journal',
                                   'account_balance_report_journal_rel',
                                   'account_id', 'journal_id',
                                   string='Journals', required=True,
                                   default=[])

    def _print_report(self, data):
        data = self.pre_print_report(data)
        records = self.env[data['model']].browse(data.get('ids', []))
        return self.env.ref(
            'sg_account_report.'
            'action_report_trial_balance').report_action(records, data=data)

    def get_trial_data(self):
        """Get the trial data."""
        context = self.env.context
        if context is None:
            context = {}
        context = dict(context)
        acc_data = self.read([])
        is_ytd = False
        result = {}
        if acc_data:
            acc_data = acc_data[0]
            result['journal_ids'] = 'journal_ids' in \
                acc_data.get('journal_ids') if acc_data else False
            result['state'] = 'target_move' in acc_data.get('target_move') \
                if acc_data else ''
            result['date_from'] = acc_data.get('date_from') or False
            result['date_to'] = acc_data.get('date_to') or False
            result['strict_range'] = True if result['date_from'] else False

            is_ytd = acc_data.get('is_ytd')

        start_dt = acc_data.get('date_from', False) if acc_data else False
        end_dt = acc_data.get('date_to', False) if acc_data else False
        account_obj = self.env['account.account']
        account_data = account_obj.browse(acc_data.get('chart_account_id', []))
        context.update({'form': acc_data,
                        'company_name': account_data.company_id.name,
                        'date_from': start_dt, 'date_to': end_dt})
        context = dict(context)
        start_date = context.get('date_from', False) or False
        end_date = context.get('date_to', False) or False

        if start_date and end_date:
            date = 'Start Date %s To End Date %s' % (start_date, end_date)
        elif not start_date and not end_date:
            date = 'All Dates'
        else:
            date = ' '

        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Sheet 1')
        font = xlwt.Font()
        font.bold = True
        header = xlwt.easyxf('font: bold 1, height 280')
        header1 = xlwt.easyxf(
            'pattern: pattern solid, fore_colour white;'
            'borders: top double, bottom double, right thin, '
            'bottom_color black; font: bold on, '
            'height 180, color black; align: wrap off')
        name_style = xlwt.easyxf('font: height 180;align: wrap on;')

        style = xlwt.easyxf('font: height 180;align: horiz right;')
        worksheet.col(0).width = 5000
        worksheet.col(1).width = 5000
        worksheet.col(2).width = 5000
        worksheet.row(0).height = 500
        worksheet.row(1).height = 500
        worksheet.row(2).height = 500
        company_name = self.env.user.company_id.name
        worksheet.write(0, 1, company_name, header)
        worksheet.write(1, 1, date, header)
        worksheet.write(2, 1, "Trial Balance Report", header)

        worksheet.write(4, 0, "Account", header1)
        worksheet.write(4, 1, "", header1)
        worksheet.write(4, 2, "Debit", header1)
        worksheet.write(4, 3, "Credit", header1)
        worksheet.write(4, 4, "Balance", header1)

        if is_ytd:
            worksheet.write(4, 5, " ", header1)
            worksheet.write(4, 6, "YTD Debit", header1)
            worksheet.write(4, 7, "YTD Credit", header1)
            worksheet.write(4, 8, "YTD Balance", header1)

        row = 5
        account_balance_inherit_obj = self.env[
            'report.sg_account_report.report_trialbalance']
        display_account = context['form'].get('display_account')
        accounts = self.env['account.account'].search([])
        account_data = account_balance_inherit_obj.with_context(
            result)._get_accounts(accounts, display_account)

        tot_deb = tot_cre = tot_ytd_deb = tot_ytd_cre = ttl_balance = \
            ttl_ytd_balance = 0.00
        for acc in account_data:
            acc_name = acc['name']
            if acc.get('code'):
                acc_name = str(acc.get('code', '')) + '  ' + acc['name']
            worksheet.write_merge(row, row, 0, 1, acc_name, name_style)

            base_amt = "0.00"

            if acc['debit']:
                worksheet.write(row, 2, format(
                    acc['debit'], '.3f')[:-1], style)
            else:
                worksheet.write(row, 2, base_amt, style)
            if acc['credit']:
                worksheet.write(row, 3, format(
                    acc['credit'], '.3f')[:-1], style)
            else:
                worksheet.write(row, 3, base_amt, style)
            if acc['balance']:
                worksheet.write(row, 4, format(
                    acc['balance'], '.3f')[:-1], style)
            else:
                worksheet.write(row, 4, base_amt, style)

            if is_ytd:

                if acc['ytd_debit']:
                    worksheet.write(row, 6, format(
                        acc['ytd_debit'], '.3f')[:-1], style)
                else:
                    worksheet.write(row, 6, base_amt, style)
                if acc['ytd_credit']:
                    worksheet.write(row, 7, format(
                        acc['ytd_credit'], '.3f')[:-1], style)
                else:
                    worksheet.write(row, 7, base_amt, style)
                if acc['ytd_balance']:
                    worksheet.write(row, 8, format(
                        acc['ytd_balance'], '.3f')[:-1], style)
                else:
                    worksheet.write(row, 8, base_amt, style)

            tot_deb += acc['debit']
            tot_cre += acc['credit']
            ttl_balance += acc['balance']

            if is_ytd:

                tot_ytd_deb += acc['ytd_debit']
                tot_ytd_cre += acc['ytd_credit']
                ttl_ytd_balance += acc['ytd_balance']
            row += 1
        row += 2

        worksheet.write(row, 0, 'Total', header1)
        worksheet.write(row, 1, "", header1)

        if tot_deb:
            worksheet.write(row, 2, format(tot_deb, '.3f')[:-1], header1)
        else:
            worksheet.write(row, 2, base_amt, header1)
        if tot_cre:
            worksheet.write(row, 3, format(tot_cre, '.3f')[:-1], header1)
        else:
            worksheet.write(row, 3, base_amt, header1)
        if ttl_balance:
            worksheet.write(row, 4, format(ttl_balance, '.3f')[:-1], header1)
        else:
            worksheet.write(row, 4, base_amt, header1)

        if is_ytd:

            worksheet.write(row, 5, "", header1)

            if tot_ytd_deb:
                worksheet.write(row, 6, format(
                    tot_ytd_deb, '.3f')[:-1], header1)
            else:
                worksheet.write(row, 6, base_amt, header1)
            if tot_ytd_cre:
                worksheet.write(row, 7, format(
                    tot_ytd_cre, '.3f')[:-1], header1)
            else:
                worksheet.write(row, 7, base_amt, header1)
            if ttl_ytd_balance:
                worksheet.write(row, 8, format(
                    ttl_ytd_balance, '.3f')[:-1], header1)
            else:
                worksheet.write(row, 8, base_amt, header1)

        row += 2
        fp = io.BytesIO()
        workbook.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()
        res = base64.b64encode(data)
        module_rec = self.env['excel.export.trial'].create(
            {'file': res,
             'name': 'Trial_Balance.xls'})

        return {
            'name': 'Trial Balance Report',
            'res_id': module_rec.id,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'excel.export.trial',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
        }
