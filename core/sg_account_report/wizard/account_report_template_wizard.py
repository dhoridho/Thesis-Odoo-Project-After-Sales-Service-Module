# See LICENSE file for full copyright and licensing details.

import base64
import io
import time

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DSDF
from odoo.tools.misc import xlwt


class BsPlXlsReport(models.TransientModel):
    _name = "bs.pl.xls.report"
    _description = "Bs Pl Xls Report"

    file = fields.Binary("Click On Download Link To Download Xls File",
                         readonly=True)
    name = fields.Char("Name", invisible=True,
                       default='Financial_Report.xls')


class WizardReport(models.TransientModel):
    _name = "account.wizard.report"
    _inherit = 'account.common.report'
    _description = "Common Wizard Report"

    @api.model
    def _default_get_company(self):
        return self.env.user.company_id.id

    account_report_id = fields.Many2one('account.financial.report',
                                        string='Account Reports',
                                        required=True)
    afr_id = fields.Many2one('afr', 'Report Template')
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 default=_default_get_company)
    currency_id = fields.Many2one(
        'res.currency',
        'Currency',
        help="This will be the currency in which "
        "the report will be stated in. If no currency"
        "is selected, the default currency of the"
        "company will be selected.")
    columns = fields.Selection(
        [('one', 'End. Balance'),
         ('two', 'Debit | Credit'),
         ('four', 'Balance | Debit | Credit'),
         ('five', 'Balance | Debit | Credit | YTD'),
         ('qtr', "4 QTR's | YTD"),
         ('thirteen', '12 Months | YTD')], 'Columns',
        required=True, default='five')
    start_date = fields.Date('From Date', required=True,
                             default=lambda *a: time.strftime('%Y-01-01'))
    end_date = fields.Date('TO Date', required=True,
                           default=lambda *a: time.strftime('%Y-12-31'))
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                    ('all', 'All Entries')],
                                   string='Target Moves', required=True,
                                   default='posted')

    @api.onchange('columns')
    def onchange_columns(self):
        """Based on column updated the start and end date."""
        if self.columns == 'thirteen' and self.start_date:
            en_date = self.start_date + relativedelta(years=1)
            self.end_date = en_date.strftime(DSDF)
        if self.columns == 'qtr' and self.start_date:
            en_qtr_date = self.start_date + relativedelta(months=3)
            self.end_date = en_qtr_date.strftime(DSDF)
        elif self.columns not in ('qtr', 'thirteen'):
            self.end_date = time.strftime('%Y-12-31')

    @api.onchange('company_id')
    def onchange_company_id(self):
        """Based on the company select the currency and afr_id."""
        context = self.env.context
        company_id = self.company_id.id if self.company_id.id else False
        if context is None:
            context = {}
        context = dict(context)
        context.update({'company_id': company_id})
        if company_id:
            company_obj = self.env['res.company']
            comp_id = company_obj.with_context(
                context=context).browse(company_id)
            cur_id = comp_id.currency_id.id
            self.currency_id = cur_id or False
            self.afr_id = False

    @api.onchange('afr_id')
    def onchange_afr_id(self):
        """Set the afr_id based on currency."""
        afr_rec = self.afr_id or False
        if afr_rec:
            self.currency_id = afr_rec.currency_id.id if afr_rec.currency_id \
                else afr_rec.company_id.currency_id.id
            self.columns = afr_rec.columns or 'five'
            self.target_move = afr_rec.target_move or 'all'

    def _get_defaults(self, data):
        context = self.env.context
        user = self.env.user
        if user.company_id:
            company_id = user.company_id.id
        else:
            company_id = self.env['res.company'].search(
                [('parent_id', '=', False)], limit=1)
        data['form']['company_id'] = company_id.id
        data['form']['context'] = context
        return data['form']

    def _print_report(self, data):
        context = self.env.context
        if context is None:
            context = {}
        data['ids'] = context.get('active_ids', [])
        data['model'] = context.get('active_model', 'ir.ui.menu')
        selfdata = self.read([])[0]
        form = data['form']
        form.update(selfdata)
        form['date_from'] = selfdata.get('start_date', False)
        form['date_to'] = selfdata.get('end_date', False)
        form['used_context']['date_from'] = selfdata.get('start_date', False)
        form['used_context']['date_to'] = selfdata.get('end_date', False)
        form['used_context']['strict_range'] = True if \
            selfdata.get('end_date') else False

        if form['columns'] == 'qtr':
            acc_mon = 0
            if selfdata['start_date'] and selfdata['end_date']:
                st_date = selfdata['start_date']
                en_date = selfdata['end_date']
                diff = relativedelta(en_date, st_date)
                if st_date == en_date or st_date > en_date:
                    raise UserError(_('Selected dates are not according to \
                    quarter format'))
                if diff and diff.days and diff.days > 0:
                    raise UserError(_('Selected dates are not according to \
                    quarter format'))
                if diff and diff.months and diff.months > 0 or diff.years > 0:
                    acc_mon = diff.months
                    if diff.years:
                        acc_mon = acc_mon + (diff.years * 12)
                if acc_mon != 0 and (acc_mon % 3) != 0:
                    raise UserError(_('Selected dates are not according to \
                    quarter format\n Please select end date as quarter date'))
                quat_num = acc_mon / 3
                qtr_dates = {}
                sta_date = st_date
                for quat in range(int(quat_num)):
                    en_date = sta_date + relativedelta(months=3, days=-1)
                    qtr_dates.update({'qtr' + str(quat + 1):
                                      {'date_from': sta_date.strftime(DSDF),
                                       'date_to': en_date.strftime(DSDF)}})
                    sta_date = en_date + relativedelta(days=1)
                data['form'] = form
                data['form'].update({'qtr_dates': qtr_dates,
                                     'quat_num': quat_num})

        if data['form']['columns'] == 'thirteen':
            acc_mon = 0
            if selfdata['start_date'] and selfdata['end_date']:
                st_date = selfdata['start_date']
                en_date = selfdata['end_date']
                diff = relativedelta(en_date, st_date)
                if st_date == en_date or st_date > en_date:
                    raise UserError(_('Selected dates are not according to 12 \
                    month format'))
                if diff and diff.days and diff.days > 0:
                    raise UserError(_('Selected dates are not according to 12 \
                    month format'))
                if diff and diff.months and diff.months > 0:
                    raise UserError(_('Selected dates are not according to 12 \
                    month format'))
                if diff and diff.year and diff.year > 0:
                    acc_mon = diff.year
                quat_num = 12
                qtr_dates = {}
                sta_date = st_date
                for quat in range(int(quat_num)):
                    en_date = sta_date + relativedelta(months=1, days=-1)
                    qtr_dates.update({'qtr' + str(quat + 1):
                                      {'date_from': sta_date.strftime(DSDF),
                                       'date_to': en_date.strftime(DSDF)}})
                    sta_date = en_date + relativedelta(days=1)
                data['form'].update({'qtr_dates': qtr_dates,
                                     'quat_num': quat_num})
        if context and context.get('xls_report'):
            data['form']['xls_report'] = context.get('xls_report')
            return self.print_report_xls(data=data)
        if data['form']['columns'] == 'one':
            name = 'sg_account_report.account_pf_balance_report'
        if data['form']['columns'] == 'two':
            name = 'sg_account_report.account_pf_balance_report'
        if data['form']['columns'] == 'four':
            name = 'sg_account_report.account_pf_balance_report'
        if data['form']['columns'] == 'five':
            name = 'sg_account_report.account_pf_balance_report'
        if data['form']['columns'] == 'qtr':
            name = 'sg_account_report.account_pf_balance_qtr_report'
        if data['form']['columns'] == 'thirteen':
            name = 'sg_account_report.account_pf_balance_13_report'
        report_id = self.env.ref(name)
        return report_id.report_action(self, data=data, config=False)

    def print_report_xls(self, data):
        """Print the xls report."""
        context = self.env.context
        if context is None:
            context = {}
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Sheet 1')
        borders = xlwt.Borders()
        borders.top = xlwt.Borders.MEDIUM
        borders.bottom = xlwt.Borders.MEDIUM
        borders.left = xlwt.Borders.MEDIUM
        borders.right = xlwt.Borders.MEDIUM
        border_style = xlwt.XFStyle()
        border_style.borders = borders
        font = xlwt.Font()
        font.bold = True
        bold = xlwt.easyxf("font: bold on; align: wrap on;")
        bold1 = xlwt.easyxf("font: bold on; align: wrap on, horiz right;")
        bold2 = xlwt.easyxf("align: wrap on, horiz right;")
        bold3 = xlwt.easyxf("font: bold off; align: wrap on, horiz right;")
        header1 = xlwt.easyxf('font: bold on, height 220, color black;\
                                align: wrap on , horiz left;')
        header2 = xlwt.easyxf('font: bold on, height 220, color black;\
                                align: wrap on , horiz right;')
        style = xlwt.easyxf('align: wrap yes')
        worksheet.col(0).width = 15000
        worksheet.col(1).width = 4000
        worksheet.col(2).width = 4000
        worksheet.col(3).width = 4000
        worksheet.col(4).width = 4000
        worksheet.col(5).width = 4000
        worksheet.col(6).width = 4000
        worksheet.col(7).width = 4000
        worksheet.row(0).height = 500
        worksheet.row(1).height = 500
        worksheet.row(2).height = 500
        company_name = self.env.user.company_id.name
        rpt_name = 'report.sg_account_report.'\
            'financial_report_balance_full_temp'
        account_balance_inherit_obj = self.env[rpt_name]
        form = data['form']
        if form['columns'] in ('one', 'four', 'five', 'two'):
            acc_data = account_balance_inherit_obj.get_account_lines(form)
            worksheet.write(4, 0, "Account Name", header1)
            if form['columns'] in ('one', 'four', 'five'):
                worksheet.write(4, 1, "Balance", header2)
            if form['columns'] in ('two', 'four', 'five'):
                worksheet.write(4, 2, "Debit", header2)
                worksheet.write(4, 3, "Credit", bold1)
            if form['columns'] == 'five':
                worksheet.write(4, 4, "YTD", header2)
            row = 6
            if form['account_report_id'][1] == 'Balance Sheet':
                worksheet.write(0, 1, company_name, header1)
                worksheet.write(1, 1, 'Balance Sheet', header1)
            elif form['account_report_id'][1] == 'Profit and Loss':
                worksheet.write(0, 1, company_name, header1)
                worksheet.write(1, 1, 'Profit Loss', header1)
            if acc_data:
                for acc in acc_data:
                    if form['account_report_id'][1] == 'Balance Sheet':
                        if int(acc['level']) != 0:
                            if int(acc['level']) <= 3:
                                worksheet.write(
                                    row, 0, '    ' *
                                    (int(acc['level']) - 1) + acc['name'],
                                    bold)
                                if form['columns'] in ('one', 'four', 'five'):
                                    if acc['balance'] != 0:
                                        worksheet.write(
                                            row, 1,
                                            round(
                                                acc['balance'] or
                                                0.00, 2),
                                            bold)
                                    else:
                                        worksheet.write(row, 1, '0.00',
                                                        bold1)
                                if form['columns'] in ('two', 'four',
                                                       'five'):
                                    if acc['debit'] != 0:
                                        worksheet.write(row, 2,
                                                        round(acc['debit'],
                                                              2), bold)
                                    else:
                                        worksheet.write(row, 2, '0.00',
                                                        bold1)
                                    if acc['credit'] != 0:
                                        worksheet.write(
                                            row, 3,
                                            round(acc['credit'] or 0.00, 2),
                                            bold)
                                    else:
                                        worksheet.write(row, 3, '0.00',
                                                        bold1)
                                if form['columns'] == 'five':
                                    if acc['ytd'] != 0:
                                        worksheet.write(row, 4,
                                                        round(acc['ytd'] or
                                                              0.00, 2),
                                                        bold)
                                    else:
                                        worksheet.write(row, 4, '0.00',
                                                        bold1)
                            else:
                                worksheet.write(
                                    row, 0,
                                    '    ' *
                                    (int(acc['level']) - 1) + acc['name'],
                                    style)
                                if form['columns'] in ('one', 'four', 'five'):
                                    if acc['balance'] != 0:
                                        worksheet.write(
                                            row, 1,
                                            round(acc['balance'] or 0.00, 2),
                                            style)
                                    else:
                                        worksheet.write(row, 1, '0.00', bold2)
                                if form['columns'] in ('two', 'four', 'five'):
                                    if acc['debit'] != 0:
                                        worksheet.write(
                                            row, 2,
                                            round(acc['debit'] or
                                                  0.00, 2),
                                            style)
                                    else:
                                        worksheet.write(
                                            row, 2, '0.00', bold2)
                                    if acc['credit'] != 0:
                                        worksheet.write(
                                            row, 3,
                                            round(acc['credit'] or
                                                  0.00, 2),
                                            style)
                                    else:
                                        worksheet.write(row, 3, '0.00', bold2)
                                if form['columns'] == 'five':
                                    if acc['ytd'] != 0:
                                        worksheet.write(
                                            row, 4,
                                            round(acc['ytd'] or
                                                  0.00, 2),
                                            style)
                                    else:
                                        worksheet.write(row, 4, '0.00', bold2)
                            row += 1
                    if form['account_report_id'][1] == 'Profit and Loss':
                        if int(acc['level']) != 0:
                            if int(acc['level']) <= 3:
                                worksheet.write(
                                    row, 0,
                                    '    ' * (int(acc['level']) - 1) +
                                    acc['name'], bold)
                                if form['columns'] in ('one', 'four', 'five'):
                                    if acc['balance'] != 0:
                                        worksheet.write(
                                            row, 1,
                                            round(acc['balance'] or
                                                  0.00, 2),
                                            bold)
                                    else:
                                        worksheet.write(row, 1, '0.00',
                                                        bold1)
                                if form['columns'] in ('two', 'four', 'five'):
                                    if acc['debit'] != 0:
                                        worksheet.write(row, 2, round(
                                            acc['debit'], 2), bold)
                                    else:
                                        worksheet.write(row, 2, '0.00',
                                                        bold1)
                                    if acc['credit'] != 0:
                                        worksheet.write(
                                            row, 3,
                                            round(acc['credit'] or
                                                  0.00, 2),
                                            bold)
                                    else:
                                        worksheet.write(row, 3, '0.00',
                                                        bold1)
                                if form['columns'] == 'five':
                                    if acc['ytd'] != 0:
                                        worksheet.write(
                                            row,
                                            4,
                                            round(acc['ytd'] or 0.00, 2),
                                            bold)
                                    else:
                                        worksheet.write(
                                            row,
                                            4,
                                            '0.00',
                                            bold1)
                            else:
                                worksheet.write(
                                    row, 0,
                                    '    ' * (int(acc['level']) - 1) +
                                    acc['name'],
                                    style)
                                if form['columns'] in ('one', 'four', 'five'):
                                    if acc['balance'] != 0:
                                        worksheet.write(row, 1, round(
                                            acc['balance'] or 0.00, 2), style)
                                    else:
                                        worksheet.write(row, 1, '0.00', bold2)
                                if form['columns'] in ('two', 'four', 'five'):
                                    if acc['debit'] != 0:
                                        worksheet.write(row, 2, round(
                                            acc['debit'] or 0.00, 2), style)
                                    else:
                                        worksheet.write(row, 2, '0.00', bold2)
                                    if acc['credit'] != 0:
                                        worksheet.write(row, 3, round(
                                            acc['credit'] or 0.00, 2), style)
                                    else:
                                        worksheet.write(row, 3, '0.00', bold2)
                                if form['columns'] == 'five':
                                    if acc['ytd'] != 0:
                                        worksheet.write(row, 4, round(
                                            acc['ytd'] or 0.00, 2), style)
                                    else:
                                        worksheet.write(row, 4, '0.00', bold2)
                            row += 1
        if form['columns'] == 'qtr':
            account_balance_qtr_obj = self.env[
                'report.sg_account_report.account_full_qtr_balance_cols']
            acc_data = account_balance_qtr_obj.get_account_lines_qtr(form)
            worksheet.write(4, 0, "Account Name", header1)
            worksheet.write(4, 1, "Q1", header2)
            worksheet.write(4, 2, "Q2", header2)
            worksheet.write(4, 3, "Q3", bold1)
            worksheet.write(4, 4, "Q4", header2)
            worksheet.write(4, 5, "YTD", header2)
            if form['account_report_id'][1] == 'Balance Sheet':
                worksheet.write(0, 1, company_name, header1)
                worksheet.write(1, 1, 'Balance Sheet', header1)
            elif form['account_report_id'][1] == 'Profit and Loss':
                worksheet.write(0, 1, company_name, header1)
                worksheet.write(1, 1, 'Profit Loss', header1)
            row = 6
            if acc_data:
                for acc in acc_data:
                    if form['account_report_id'][1] == 'Balance Sheet':
                        if int(acc['level']) != 0:
                            if int(acc['level']) <= 3:
                                worksheet.write(row, 0, '    ' * (
                                    int(acc['level']) - 1) + acc['name'], bold)
                                if form['columns'] == 'qtr':
                                    if acc['balance1'] != 0:
                                        worksheet.write(row, 1, round(
                                            acc['balance1'] or 0.00, 2), bold)
                                    else:
                                        worksheet.write(row, 1, '0.00',
                                                        bold1)
                                    if acc['balance2'] != 0:
                                        worksheet.write(row, 2, round(
                                            acc['balance2'], 2), bold)
                                    else:
                                        worksheet.write(row, 2, '0.00',
                                                        bold1)
                                    if acc['balance3'] != 0:
                                        worksheet.write(
                                            row, 3,
                                            round(acc['balance3'] or
                                                  0.00, 2),
                                            bold)
                                    else:
                                        worksheet.write(row, 3, '0.00',
                                                        bold1)
                                    if acc['balance4'] != 0:
                                        worksheet.write(
                                            row, 4, round(acc['balance4'] or
                                                          0.00, 2),
                                            bold)
                                    else:
                                        worksheet.write(row, 4, '0.00',
                                                        bold1)
                                    if acc['ytd'] != 0:
                                        worksheet.write(row, 5, round(
                                            acc['ytd'] or 0.00, 2), bold)
                                    else:
                                        worksheet.write(row, 5, '0.00',
                                                        bold1)
                            else:
                                worksheet.write(row, 0, '    ' * (
                                    int(acc['level']) - 1) + acc['name'], style)
                                if form['columns'] == 'qtr':
                                    if acc['balance1'] != 0:
                                        worksheet.write(row, 1, round(
                                            acc['balance1'] or 0.00, 2), style)
                                    else:
                                        worksheet.write(row, 1, '0.00', bold2)
                                    if acc['balance2'] != 0:
                                        worksheet.write(row, 2, round(
                                            acc['balance2'] or 0.00, 2), style)
                                    else:
                                        worksheet.write(row, 2, '0.00', bold2)
                                    if acc['balance3'] != 0:
                                        worksheet.write(row, 3, round(
                                            acc['balance3'] or 0.00, 2), style)
                                    else:
                                        worksheet.write(row, 3, '0.00', bold2)
                                    if acc['balance4'] != 0:
                                        worksheet.write(row, 4, round(
                                            acc['balance4'] or 0.00, 2), style)
                                    else:
                                        worksheet.write(row, 4, '0.00', bold2)
                                    if acc['ytd'] != 0:
                                        worksheet.write(row, 5, round(
                                            acc['ytd'] or 0.00, 2), style)
                                    else:
                                        worksheet.write(row, 5, '0.00', bold2)
                            row += 1
                    if form['account_report_id'][1] == 'Profit and Loss':
                        if int(acc['level']) != 0:
                            if int(acc['level']) <= 3:
                                worksheet.write(row, 0, '    ' * (
                                    int(acc['level']) - 1) + acc['name'], bold)
                                if form['columns'] == 'qtr':
                                    if acc['balance1'] != 0:
                                        worksheet.write(
                                            row, 1,
                                            round(acc['balance1'] or
                                                  0.00, 2),
                                            bold)
                                    else:
                                        worksheet.write(row, 1, '0.00',
                                                        bold1)
                                    if acc['balance2'] != 0:
                                        worksheet.write(row, 2, round(
                                            acc['balance2'], 2), bold)
                                    else:
                                        worksheet.write(row, 2, '0.00',
                                                        bold1)
                                    if acc['balance3'] != 0:
                                        worksheet.write(
                                            row, 3,
                                            round(acc['balance3'] or
                                                  0.00, 2),
                                            bold)
                                    else:
                                        worksheet.write(row, 3, '0.00',
                                                        bold1)
                                    if acc['balance4'] != 0:
                                        worksheet.write(
                                            row, 4,
                                            round(acc['balance4'] or
                                                  0.00, 2),
                                            bold)
                                    else:
                                        worksheet.write(row, 4, '0.00',
                                                        bold1)
                                    if acc['ytd'] != 0:
                                        worksheet.write(row, 5, round(
                                            acc['ytd'] or 0.00, 2), bold)
                                    else:
                                        worksheet.write(row, 5, '0.00', bold1)
                            else:
                                worksheet.write(row, 0, '    ' * (
                                    int(acc['level']) - 1) + acc['name'], style)
                                if form['columns'] == 'qtr':
                                    if acc['balance1'] != 0:
                                        worksheet.write(row, 1, round(
                                            acc['balance1'] or 0.00, 2), style)
                                    else:
                                        worksheet.write(row, 1, '0.00', bold2)
                                    if acc['balance2'] != 0:
                                        worksheet.write(row, 2, round(
                                            acc['balance2'] or 0.00, 2), style)
                                    else:
                                        worksheet.write(row, 2, '0.00', bold2)
                                    if acc['balance3'] != 0:
                                        worksheet.write(row, 3, round(
                                            acc['balance3'] or 0.00, 2), style)
                                    else:
                                        worksheet.write(row, 3, '0.00', bold2)
                                    if acc['balance4'] != 0:
                                        worksheet.write(row, 4, round(
                                            acc['balance4'] or 0.00, 2), style)
                                    else:
                                        worksheet.write(row, 4, '0.00', bold2)
                                    if acc['ytd'] != 0:
                                        worksheet.write(row, 5, round(
                                            acc['ytd'] or 0.00, 2), style)
                                    else:
                                        worksheet.write(row, 5, '0.00', bold2)
                            row += 1
        if form['columns'] == 'thirteen':
            account_balance_twlv_obj = self.env[
                'report.sg_account_report.account_full_13_balance_cols']
            acc_data = account_balance_twlv_obj.get_account_lines_twelve_month(
                form)
            worksheet.write(4, 0, "Account Name", header1)
            worksheet.write(4, 1, "01", header2)
            worksheet.write(4, 2, "02", header2)
            worksheet.write(4, 3, "03", bold1)
            worksheet.write(4, 4, "04", header2)
            worksheet.write(4, 5, "05", header2)
            worksheet.write(4, 6, "06", header2)
            worksheet.write(4, 7, "07", header2)
            worksheet.write(4, 8, "08", header2)
            worksheet.write(4, 9, "09", header2)
            worksheet.write(4, 10, "10", header2)
            worksheet.write(4, 11, "11", header2)
            worksheet.write(4, 12, "12", header2)
            worksheet.write(4, 13, "YTD", header2)
            if form['account_report_id'][1] == 'Balance Sheet':
                worksheet.write(0, 1, company_name, header1)
                worksheet.write(1, 1, 'Balance Sheet', header1)
            elif form['account_report_id'][1] == 'Profit and Loss':
                worksheet.write(0, 1, company_name, header1)
                worksheet.write(1, 1, 'Profit Loss', header1)
            row = 6
            if acc_data:
                for acc in acc_data:

                    if form['account_report_id'][1] == 'Balance Sheet':
                        if int(acc['level']) != 0:
                            if int(acc['level']) <= 3:
                                worksheet.write(row, 0, '    ' * (
                                    int(acc['level']) - 1) + acc['name'], bold)

                                if 'balance1' in acc and acc['balance1'] != 0:
                                    worksheet.write(row, 1, round(
                                        acc['balance1'], 2) or '0.00', bold)
                                else:
                                    worksheet.write(row, 1, '0.00', bold1)

                                if 'balance2' in acc and acc['balance2'] != 0:
                                    worksheet.write(row, 2, round(
                                        acc['balance2'], 2) or '0.00', bold)
                                else:
                                    worksheet.write(row, 2, '0.00', bold1)

                                if 'balance3' in acc and acc['balance3'] != 0:
                                    worksheet.write(row, 3, round(
                                        acc['balance3'], 2) or '0.00', bold)
                                else:
                                    worksheet.write(row, 3, '0.00', bold1)

                                if 'balance4' in acc and acc['balance4'] != 0:
                                    worksheet.write(row, 4, round(
                                        acc['balance4'], 2) or '0.00', bold)
                                else:
                                    worksheet.write(row, 4, '0.00', bold1)

                                if 'balance5' in acc and acc['balance5'] != 0:
                                    worksheet.write(row, 5, round(
                                        acc['balance5'], 2) or '0.00', bold)
                                else:
                                    worksheet.write(row, 5, '0.00', bold1)

                                if 'balance6' in acc and acc['balance6'] != 0:
                                    worksheet.write(row, 6, round(
                                        acc['balance6'], 2) or '0.00', bold)
                                else:
                                    worksheet.write(row, 6, '0.00', bold1)

                                if 'balance7' in acc and acc['balance7'] != 0:
                                    worksheet.write(row, 7, round(
                                        acc['balance7'], 2) or '0.00', bold)
                                else:
                                    worksheet.write(row, 7, '0.00', bold1)

                                if 'balance8' in acc and acc['balance8'] != 0:
                                    worksheet.write(row, 8, round(
                                        acc['balance8'], 2) or '0.00', bold)
                                else:
                                    worksheet.write(row, 8, '0.00', bold1)

                                if 'balance9' in acc and acc['balance9'] != 0:
                                    worksheet.write(row, 9, round(
                                        acc['balance9'], 2) or '0.00', bold)
                                else:
                                    worksheet.write(row, 9, '0.00', bold1)

                                if 'balance10' in acc and \
                                        acc['balance10'] != 0:
                                    worksheet.write(row, 10, round(
                                        acc['balance10'], 2) or '0.00', bold)
                                else:
                                    worksheet.write(row, 10, '0.00', bold1)

                                if 'balance11' in acc and \
                                        acc['balance11'] != 0:
                                    worksheet.write(row, 11, round(
                                        acc['balance11'], 2) or '0.00', bold)
                                else:
                                    worksheet.write(row, 11, '0.00', bold1)

                                if 'balance12' in acc and \
                                        acc['balance12'] != 0:
                                    worksheet.write(row, 12, round(
                                        acc['balance12'], 2) or '0.00', bold)
                                else:
                                    worksheet.write(row, 12, '0.00', bold1)

                                if 'ytd' in acc and acc['ytd'] != 0:
                                    worksheet.write(row, 13, round(
                                        acc['ytd'] or 0.00, 2), bold)
                                else:
                                    worksheet.write(row, 13, '0.00', bold1)
                            else:
                                worksheet.write(row, 0, '    ' * (
                                    int(acc['level']) - 1) + acc['name'], style)

                                if 'balance1' in acc and acc['balance1'] != 0:
                                    worksheet.write(row, 1, round(
                                        acc['balance1'], 2) or '0.00', bold3)
                                else:
                                    worksheet.write(row, 1, '0.00', bold3)

                                if 'balance2' in acc and acc['balance2'] != 0:
                                    worksheet.write(row, 2, round(
                                        acc['balance2'], 2) or '0.00', bold3)
                                else:
                                    worksheet.write(row, 2, '0.00', bold3)

                                if 'balance3' in acc and acc['balance3'] != 0:
                                    worksheet.write(row, 3, round(
                                        acc['balance3'], 2) or '0.00', bold3)
                                else:
                                    worksheet.write(row, 3, '0.00', bold3)

                                if 'balance4' in acc and acc['balance4'] != 0:
                                    worksheet.write(row, 4, round(
                                        acc['balance4'], 2) or '0.00', bold3)
                                else:
                                    worksheet.write(row, 4, '0.00', bold3)

                                if 'balance5' in acc and acc['balance5'] != 0:
                                    worksheet.write(row, 5, round(
                                        acc['balance5'], 2) or '0.00', bold3)
                                else:
                                    worksheet.write(row, 5, '0.00', bold3)

                                if 'balance6' in acc and acc['balance6'] != 0:
                                    worksheet.write(row, 6, round(
                                        acc['balance6'], 2) or '0.00', bold3)
                                else:
                                    worksheet.write(row, 6, '0.00', bold3)

                                if 'balance7' in acc and acc['balance7'] != 0:
                                    worksheet.write(row, 7, round(
                                        acc['balance7'], 2) or '0.00', bold3)
                                else:
                                    worksheet.write(row, 7, '0.00', bold3)

                                if 'balance8' in acc and acc['balance8'] != 0:
                                    worksheet.write(row, 8, round(
                                        acc['balance8'], 2) or '0.00', bold3)
                                else:
                                    worksheet.write(row, 8, '0.00', bold3)

                                if 'balance9' in acc and acc['balance9'] != 0:
                                    worksheet.write(row, 9, round(
                                        acc['balance9'], 2) or '0.00', bold3)
                                else:
                                    worksheet.write(row, 9, '0.00', bold3)

                                if 'balance10' in acc and \
                                        acc['balance10'] != 0:
                                    worksheet.write(row, 10, round(
                                        acc['balance10'], 2) or '0.00', bold3)
                                else:
                                    worksheet.write(row, 10, '0.00', bold3)

                                if 'balance11' in acc and \
                                        acc['balance11'] != 0:
                                    worksheet.write(row, 11, round(
                                        acc['balance11'], 2) or '0.00', bold3)
                                else:
                                    worksheet.write(row, 11, '0.00', bold3)

                                if 'balance12' in acc and \
                                        acc['balance12'] != 0:
                                    worksheet.write(row, 12, round(
                                        acc['balance12'], 2) or '0.00', bold3)
                                else:
                                    worksheet.write(row, 12, '0.00', bold3)

                                if 'ytd' in acc and acc['ytd'] != 0:
                                    worksheet.write(row, 13, round(
                                        acc['ytd'] or 0.00, 2), bold3)
                                else:
                                    worksheet.write(row, 13, '0.00', bold3)
                            row += 1

                    if form['account_report_id'][1] == 'Profit and Loss':
                        if int(acc['level']) != 0:
                            if int(acc['level']) <= 3:
                                worksheet.write(row, 0, '    ' * (
                                    int(acc['level']) - 1) + acc['name'], bold)

                                if 'balance1' in acc and acc['balance1'] != 0:
                                    worksheet.write(row, 1, round(
                                        acc['balance1'], 2) or '0.00', bold)
                                else:
                                    worksheet.write(row, 1, '0.00', bold1)

                                if 'balance2' in acc and acc['balance2'] != 0:
                                    worksheet.write(row, 2, round(
                                        acc['balance2'], 2) or '0.00', bold)
                                else:
                                    worksheet.write(row, 2, '0.00', bold1)

                                if 'balance3' in acc and acc['balance3'] != 0:
                                    worksheet.write(row, 3, round(
                                        acc['balance3'], 2) or '0.00', bold)
                                else:
                                    worksheet.write(row, 3, '0.00', bold1)

                                if 'balance4' in acc and acc['balance4'] != 0:
                                    worksheet.write(row, 4, round(
                                        acc['balance4'], 2) or '0.00', bold)
                                else:
                                    worksheet.write(row, 4, '0.00', bold1)

                                if 'balance5' in acc and acc['balance5'] != 0:
                                    worksheet.write(row, 5, round(
                                        acc['balance5'], 2) or '0.00', bold)
                                else:
                                    worksheet.write(row, 5, '0.00', bold1)

                                if 'balance6' in acc and acc['balance6'] != 0:
                                    worksheet.write(row, 6, round(
                                        acc['balance6'], 2) or '0.00', bold)
                                else:
                                    worksheet.write(row, 6, '0.00', bold1)

                                if 'balance7' in acc and acc['balance7'] != 0:
                                    worksheet.write(row, 7, round(
                                        acc['balance7'], 2) or '0.00', bold)
                                else:
                                    worksheet.write(row, 7, '0.00', bold1)

                                if 'balance8' in acc and acc['balance8'] != 0:
                                    worksheet.write(row, 8, round(
                                        acc['balance8'], 2) or '0.00', bold)
                                else:
                                    worksheet.write(row, 8, '0.00', bold1)

                                if 'balance9' in acc and acc['balance9'] != 0:
                                    worksheet.write(row, 9, round(
                                        acc['balance9'], 2) or '0.00', bold)
                                else:
                                    worksheet.write(row, 9, '0.00', bold1)

                                if 'balance10' in acc and \
                                        acc['balance10'] != 0:
                                    worksheet.write(row, 10, round(
                                        acc['balance10'], 2) or '0.00', bold)
                                else:
                                    worksheet.write(row, 10, '0.00', bold1)

                                if 'balance11' in acc and \
                                        acc['balance11'] != 0:
                                    worksheet.write(row, 11, round(
                                        acc['balance11'], 2) or '0.00', bold)
                                else:
                                    worksheet.write(row, 11, '0.00', bold1)

                                if 'balance12' in acc and \
                                        acc['balance12'] != 0:
                                    worksheet.write(row, 12, round(
                                        acc['balance12'], 2) or '0.00', bold)
                                else:
                                    worksheet.write(row, 12, '0.00', bold1)

                                if 'ytd' in acc and acc['ytd'] != 0:
                                    worksheet.write(row, 13, round(
                                        acc['ytd'] or 0.00, 2), bold)
                                else:
                                    worksheet.write(row, 13, '0.00', bold1)
                            else:
                                worksheet.write(row, 0, '    ' * (
                                    int(acc['level']) - 1) + acc['name'], style)

                                if 'balance1' in acc and acc['balance1'] != 0:
                                    worksheet.write(row, 1, round(
                                        acc['balance1'], 2) or '0.00', bold3)
                                else:
                                    worksheet.write(row, 1, '0.00', bold3)

                                if 'balance2' in acc and acc['balance2'] != 0:
                                    worksheet.write(row, 2, round(
                                        acc['balance2'], 2) or '0.00', bold3)
                                else:
                                    worksheet.write(row, 2, '0.00', bold3)

                                if 'balance3' in acc and acc['balance3'] != 0:
                                    worksheet.write(row, 3, round(
                                        acc['balance3'], 2) or '0.00', bold3)
                                else:
                                    worksheet.write(row, 3, '0.00', bold3)

                                if 'balance4' in acc and acc['balance4'] != 0:
                                    worksheet.write(row, 4, round(
                                        acc['balance4'], 2) or '0.00', bold3)
                                else:
                                    worksheet.write(row, 4, '0.00', bold3)

                                if 'balance5' in acc and acc['balance5'] != 0:
                                    worksheet.write(row, 5, round(
                                        acc['balance5'], 2) or '0.00', bold3)
                                else:
                                    worksheet.write(row, 5, '0.00', bold3)

                                if 'balance6' in acc and acc['balance6'] != 0:
                                    worksheet.write(row, 6, round(
                                        acc['balance6'], 2) or '0.00', bold3)
                                else:
                                    worksheet.write(row, 6, '0.00', bold3)

                                if 'balance7' in acc and acc['balance7'] != 0:
                                    worksheet.write(row, 7, round(
                                        acc['balance7'], 2) or '0.00', bold3)
                                else:
                                    worksheet.write(row, 7, '0.00', bold3)

                                if 'balance8' in acc and acc['balance8'] != 0:
                                    worksheet.write(row, 8, round(
                                        acc['balance8'], 2) or '0.00', bold3)
                                else:
                                    worksheet.write(row, 8, '0.00', bold3)

                                if 'balance9' in acc and acc['balance9'] != 0:
                                    worksheet.write(row, 9, round(
                                        acc['balance9'], 2) or '0.00', bold3)
                                else:
                                    worksheet.write(row, 9, '0.00', bold3)

                                if 'balance10' in acc and \
                                        acc['balance10'] != 0:
                                    worksheet.write(row, 10, round(
                                        acc['balance10'], 2) or '0.00', bold3)
                                else:
                                    worksheet.write(row, 10, '0.00', bold3)

                                if 'balance11' in acc and \
                                        acc['balance11'] != 0:
                                    worksheet.write(row, 11, round(
                                        acc['balance11'], 2) or '0.00', bold3)
                                else:
                                    worksheet.write(row, 11, '0.00', bold3)

                                if 'balance12' in acc and \
                                        acc['balance12'] != 0:
                                    worksheet.write(row, 12, round(
                                        acc['balance12'], 2) or '0.00', bold3)
                                else:
                                    worksheet.write(row, 12, '0.00', bold3)

                                if 'ytd' in acc and acc['ytd'] != 0:
                                    worksheet.write(row, 13, round(
                                        acc['ytd'] or 0.00, 2), bold3)
                                else:
                                    worksheet.write(row, 13, '0.00', bold3)
                            row += 1
        fp = io.BytesIO()
        workbook.save(fp)
        fp.seek(0)
        data1 = fp.read()
        fp.close()
        file_res = base64.b64encode(data1)
        rep_obj = self.env['bs.pl.xls.report']
        bs_pl_xls_rec = rep_obj.create(
            {'file': file_res, 'name': 'Financial_Report.xls'})
        return {
            'name': _('Financial Xls Reports'),
            'res_id': bs_pl_xls_rec.id,
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'bs.pl.xls.report',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
        }
