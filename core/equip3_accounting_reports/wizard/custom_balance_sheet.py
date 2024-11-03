import time
from odoo import fields, models, api, _
import io
import json
from odoo.exceptions import AccessError, UserError, AccessDenied
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar
from odoo.tools.misc import formatLang, format_date
from odoo.tools import config, date_utils, get_lang
from babel.dates import get_quarter_names
import datetime
import re, copy

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class BalanceSheetView(models.TransientModel):
    _name = 'ctm.dynamic.balance.sheet.report'

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    journal_ids = fields.Many2many('account.journal', string='Journals', required=True, default=[])
    account_ids = fields.Many2many("account.account", string="Accounts")
    account_tag_ids = fields.Many2many("account.account.tag", string="Account Tags")
    analytic_ids = fields.Many2many("account.analytic.account", string="Analytic Accounts")
    analytic_tag_ids = fields.Many2many("account.analytic.tag", string="Analytic Tags")
    display_account = fields.Selection(
        [('all', 'All'), ('movement', 'With movements'),
         ('not_zero', 'With balance is not equal to 0')],
        string='Display Accounts', required=True, default='movement')
    target_move = fields.Selection(
        [('all', 'All'), ('posted', 'Posted')],
        string='Target Move', required=True, default='posted')
    date_from = fields.Date(string="Start date")
    date_to = fields.Date(string="End date")
    analytic_group_ids = fields.Many2many("account.analytic.group", "acc_analytic_group_ctm_dynamic_balance_sheet_report_rel", "account_analytic_tag_id", "ctm_dynamic_balance_sheet_report_id", string="Analytic Groups")
    comparison = fields.Integer(string="Comparison")
    previous = fields.Boolean(string="Previous", default=False)
    report_currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    book = fields.Selection(
        [('commercial', 'Commercial Book.'), ('fiscal', 'Fiscal Book')],
        string='Book', required=True, default='commercial')
    consolidate = fields.Selection(
        [('off', 'Consolidate OFF'), ('on', 'Consolidate On')],
        string='Consolidate', required=True, default='off')
    comp_detail = fields.Selection(
        [('no', 'No'),
         ('today', 'Today'), 
         ('month', 'This Month'),
         ('quarter', 'This Quarter'),
         ('year', 'This Year'),
         ('lastmonth', 'Last Month'),
         ('lastquarter', 'Last Quarter'),
         ('lastyear', 'Last Year'),
         ('custom', 'Custom'),
         ('same_lastmonth', 'same_lastmonth'),
         ('same_lastyear', 'same_lastyear'),
         ('custom_comp', 'custom_comp')],
        string='Comparison Detail', required=True, default='no')
    filter_budget = fields.Boolean('Budget Filter', default=False)
    budget = fields.Selection([
            ('off', 'Budget Off'), 
            ('on', 'Budget On')],
            string='Budget', required=True, default='off')
    debit_credit = fields.Selection([
            ('off', 'Off'), 
            ('on', 'On')],
            string='Debit & Credit', required=True, default='off')
    entities_comparison = fields.Selection([('off', 'OFF'), ('on', 'ON')], string='Entities Comparison', required=True, default='off')
    all_account = fields.Selection([('off', 'OFF'), ('on', 'ON')], string='show all Account', required=True, default='off')
    currency_ids = fields.Many2many('res.currency', string='Currencies', required=True, default=[])
    
    @api.model
    def _getcodeacc(self,rep_name):
        res = []
        report_tmp = self.env['account.financial.report'].search([('name', 'ilike', rep_name)])
        for xx in report_tmp:
            if xx.type == 'account_report':
                report_PL = xx.account_report_id._get_children_by_order()
                for rep_pl_dt in report_PL:
                    tmp_acc = self.env['account.account'].search([('user_type_id', 'in', rep_pl_dt.account_type_ids.ids)])
                    for acctmp in tmp_acc:
                        res.append(acctmp.code)
                    for acctmp in rep_pl_dt.account_ids:
                        res.append(rep_pl_dt.code)
        return res

    @api.model
    def get_month_list(self, date_start, date_end):
        date_start = date_start.replace(day=1)
        date_end = date_end.replace(day=1)
        months_str = calendar.month_name
        months = []
        while date_start <= date_end:
            month = date_start.month
            year = date_start.year
            month_str = months_str[month]
            months.append("{0}-{1}".format(month_str, year))
            next_month = month + 1 if month != 12 else 1
            next_year = year + 1 if next_month == 1 else year
            date_start = date_start.replace(month=next_month, year=next_year)
        return months

    @api.model
    def get_budget_amount(self, account_id,data):
        date_from = fields.Date.from_string(data['date_from'])
        date_to = fields.Date.from_string(data['date_to'])
        if data['budget'] == 'on':
            where = 'account_id = %s' % account_id
            if data['report_name']:
                account_plan_id = ''
                if data['report_name'] == 'Profit and Loss':
                    account_plan_id = 'profit_lose'
                elif data['report_name'] == 'Balance Sheet':
                    account_plan_id = 'balance_sheet'
                if account_plan_id:
                    where = where + ' AND ' if where else ''
                    where += "account_plan_id = '%s'" % account_plan_id
            month_range = []
            if date_from and date_to:
                month_range = self.get_month_list(date_from, date_to)
                year_list = []
                for month in month_range:
                    year = month.split('-')[1]
                    year_list.append(year)
                if year_list:
                    year_list = list(set(year_list))
                    if len(year_list) == 1:
                        where = where + ' AND ' if where else ''
                        where += "year_name = '%s'" % str(year_list[0])
                    elif len(year_list) > 1:
                        where = where + ' AND ' if where else ''
                        where += "year_name in %s" % str(tuple(year_list))
            if where:
                where = ' WHERE ' + where
            sql = '''SELECT 
                year_name, account_id, 
                jan_month, jan_actual, 
                feb_month, feb_actual, 
                march_month, march_actual,
                april_month, april_actual,
                may_month, may_actual,
                june_month, june_actual,
                july_month, july_actual,
                august_month, august_actual,
                sep_month, sep_actual,
                oct_month, oct_actual,
                nov_month, nov_actual,
                dec_month, dec_actual
                FROM monthly_account_budget_lines
            '''
            
            self.env.cr.execute(sql + where)
            budget_res = self.env.cr.dictfetchall()
            planned_amount = 0.0
            actual_amount = 0.0
            if not month_range:
                planned_list = [
                    'jan_month',
                    'feb_month',
                    'march_month',
                    'april_month',
                    'may_month',
                    'june_month',
                    'july_month',
                    'august_month',
                    'sep_month',
                    'oct_month',
                    'nov_month',
                    'dec_month',
                ]
                actual_list = [
                    'jan_actual',
                    'feb_actual',
                    'march_actual',
                    'april_actual',
                    'may_actual',
                    'june_actual',
                    'july_actual',
                    'august_actual',
                    'sep_actual',
                    'oct_actual',
                    'nov_actual',
                    'dec_actual',
                ]
                for budget_line in budget_res:
                    for planned_item in planned_list:
                        planned_amount += budget_line.get(planned_item)
                    for actual_item in actual_list:
                        actual_amount += budget_line.get(actual_item)
            if month_range:
                for item in month_range:
                    item_split = item.split('-')
                    month_name = item_split[0]
                    year_name = item_split[1]
                    for budget_line in budget_res:
                        if budget_line.get('year_name') == year_name:
                            if month_name == 'January':
                                planned_amount += budget_line.get('jan_month')
                                actual_amount += budget_line.get('jan_actual')
                            elif month_name == 'February':
                                planned_amount += budget_line.get('feb_month')
                                actual_amount += budget_line.get('feb_actual')
                            elif month_name == 'March':
                                planned_amount += budget_line.get('march_month')
                                actual_amount += budget_line.get('march_actual')
                            elif month_name == 'April':
                                planned_amount += budget_line.get('april_month')
                                actual_amount += budget_line.get('april_actual')
                            elif month_name == 'May':
                                planned_amount += budget_line.get('may_month')
                                actual_amount += budget_line.get('may_actual')
                            elif month_name == 'June':
                                planned_amount += budget_line.get('june_month')
                                actual_amount += budget_line.get('june_actual')
                            elif month_name == 'July':
                                planned_amount += budget_line.get('july_month')
                                actual_amount += budget_line.get('july_actual')
                            elif month_name == 'August':
                                planned_amount += budget_line.get('august_month')
                                actual_amount += budget_line.get('august_actual')
                            elif month_name == 'September':
                                planned_amount += budget_line.get('sep_month')
                                actual_amount += budget_line.get('sep_actual')
                            elif month_name == 'October':
                                planned_amount += budget_line.get('oct_month')
                                actual_amount += budget_line.get('oct_actual')
                            elif month_name == 'November':
                                planned_amount += budget_line.get('nov_month')
                                actual_amount += budget_line.get('nov_actual')
                            elif month_name == 'December':
                                planned_amount += budget_line.get('dec_month')
                                actual_amount += budget_line.get('dec_actual')
            return {'planned_amount': planned_amount, 'actual_amount': actual_amount}

    @api.model
    def _get_dates_previous_year(self, data, period_vals):
        period_type = period_vals
        mode = data.get('report_name')
        strict_range = False
        date_from = fields.Date.from_string(data.get('date_from'))
        date_from = date_from - relativedelta(years=1)
        date_to = fields.Date.from_string(data.get('date_to'))
        date_to = date_to - relativedelta(years=1)

        if period_type in ['month','lastmonth']:
            date_from, date_to = date_utils.get_month(date_to)
        return self._get_dates_period(data, date_from, date_to, mode, period_type=period_type, strict_range=strict_range)


    @api.model
    def _get_dates_previous_period(self, data, period_vals):
        period_type = period_vals
        mode = data.get('report_name')
        strict_range = False
        range_date = (fields.Date.from_string(data.get('date_to')) - fields.Date.from_string(data.get('date_from'))).days
        date_from = fields.Date.from_string(data.get('date_from')) - datetime.timedelta(days=range_date+1)
        date_to = fields.Date.from_string(data.get('date_from')) - datetime.timedelta(days=1)
        if period_type in ('year', 'lastyear'):
            company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(date_to)
            return self._get_dates_period(data, company_fiscalyear_dates['date_from'], company_fiscalyear_dates['date_to'], mode, strict_range=strict_range)
        if period_type in ('lastmonth','month'):
            return self._get_dates_period(data, *date_utils.get_month(date_to), mode, period_type='month', strict_range=strict_range)
        if period_type in ('quarter', 'lastquarter'):
            return self._get_dates_period(data, *date_utils.get_quarter(date_to), mode, period_type='quarter', strict_range=strict_range)
        if period_type in ('custom','no','today','same_lastmonth','same_lastyear','custom_comp'):
            if mode == 'Balance Sheet':
                if period_type == 'custom_comp':
                    date_from = fields.Date.from_string(data.get('date_from'))
                    date_to = fields.Date.from_string(data.get('date_from'))
                elif period_type == 'today':
                    date_from = fields.Date.from_string(data.get('date_to')) - datetime.timedelta(days=1)
                    date_to = fields.Date.from_string(data.get('date_to')) - datetime.timedelta(days=1)
                    return self._get_dates_period(data, date_from, date_to, mode, period_type='today', strict_range=strict_range)
                else:
                    date_from = fields.Date.from_string(data.get('date_to')) - datetime.timedelta(days=1)
                    date_to = fields.Date.from_string(data.get('date_to')) - datetime.timedelta(days=1)
            return self._get_dates_period(data, date_from, date_to, mode, period_type='custom', strict_range=strict_range)
        return None

    @api.model
    def _init_filter_date(self, data, previous_options=None):
        if data.get('date_from') is False or data.get('date_to') is False:
            return

        mode = data.get('report_name', 'Profit and Loss')
        options_filter = data.get('comp_detail') or ('today' if mode == 'Balance Sheet' else 'year')
        date_from = data.get('date_from') and fields.Date.from_string(data['date_from'])
        date_to = data.get('date_to') and fields.Date.from_string(data['date_to'])
        strict_range = False
        if previous_options and (data.get('date_from') and data.get('date_to')) and data.get('comp_detail') \
                and not (data.get('comp_detail') == 'today' and mode == 'Profit and Loss'):

            options_filter = previous_options
            if options_filter == 'custom' or options_filter == 'no' :
                if data.get('date_from') and mode == 'Profit and Loss':
                    date_from = fields.Date.from_string(data.get('date_from'))
                if data.get('date_to'):
                    date_to = fields.Date.from_string(data.get('date_to'))

        if options_filter in ['today']:
            date_to = fields.Date.context_today(self)
            date_from = date_utils.get_month(date_to)[0]
        elif options_filter in ['month','lastmonth']:
            date_from, date_to = date_utils.get_month(fields.Date.context_today(self))
        elif options_filter in ['quarter','lastquarter']:
            date_from, date_to = date_utils.get_quarter(fields.Date.context_today(self))
        elif options_filter in ['year','lastyear']:
            company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(fields.Date.context_today(self))
            date_from = company_fiscalyear_dates['date_from']
            date_to = company_fiscalyear_dates['date_to']
        elif not date_from:
            # # options_filter == 'custom' && mode == 'single'
            # date_from = date_utils.get_month(date_to)[0]
            date_from = (data.get('date_from') and fields.Date.from_string(data['date_from'])) or date_utils.get_month(date_to)[0]
            date_to = data.get('date_to') and fields.Date.from_string(data['date_to'])

        if options_filter in ['lastmonth','lastquarter','lastyear']:
            return self._get_dates_previous_period(data,options_filter)
        return self._get_dates_period(data, date_from, date_to, mode, period_type=options_filter, strict_range=strict_range)

    @api.model
    def _get_dates_period(self, data, date_from, date_to, mode, period_type=None, strict_range=False):
        def match(dt_from, dt_to):
            return (dt_from, dt_to) == (date_from, date_to)

        string = None
        if not period_type:
            date = date_to or date_from
            company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(date)
            if match(company_fiscalyear_dates['date_from'], company_fiscalyear_dates['date_to']):
                period_type = 'year'
                if company_fiscalyear_dates.get('record'):
                    string = company_fiscalyear_dates['record'].name
            elif match(*date_utils.get_month(date)):
                period_type = 'month'
            elif match(*date_utils.get_quarter(date)):
                period_type = 'quarter'
            elif match(date_utils.get_month(date)[0], fields.Date.today()):
                period_type = 'today'
            else:
                period_type = 'custom'

        elif period_type in ['year', 'lastyear']:
            date = date_to or date_from
            company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(date)
            record = company_fiscalyear_dates.get('record')
            string = record and record.name

        if not string:
            fy_day = self.env.company.fiscalyear_last_day
            fy_month = int(self.env.company.fiscalyear_last_month)
            # if mode == 'Balance Sheet' and period_type not in ['year','lastyear','month','lastmonth','quarter','lastquarter']:
            if mode == 'Balance Sheet':
                if period_type in ['month','lastmonth']:
                    string = format_date(self.env, fields.Date.to_string(date_to), date_format='MMM yyyy')
                elif period_type in ['quarter','lastquarter']:
                    quarter_names = get_quarter_names('abbreviated', locale=get_lang(self.env).code)
                    string = u'%s\N{NO-BREAK SPACE}%s' % (quarter_names[date_utils.get_quarter_number(date_to)], date_to.year)
                elif period_type in ['year','lastyear'] or (period_type in ['year','lastyear'] and (date_from, date_to) == date_utils.get_fiscal_year(date_to)):
                    string = date_to.strftime('%Y')
                elif period_type in ['year','lastyear'] and (date_from, date_to) == date_utils.get_fiscal_year(date_to, day=fy_day, month=fy_month):
                    string = '%s - %s' % (date_to.year - 1, date_to.year)
                else:
                   string = _('As of %s') % (format_date(self.env, fields.Date.to_string(date_to)))
            elif period_type in ['year','lastyear'] or (period_type in ['year','lastyear'] and (date_from, date_to) == date_utils.get_fiscal_year(date_to)):
                string = date_to.strftime('%Y')
            elif period_type in ['year','lastyear'] and (date_from, date_to) == date_utils.get_fiscal_year(date_to, day=fy_day, month=fy_month):
                string = '%s - %s' % (date_to.year - 1, date_to.year)
            elif period_type in ['month','lastmonth']:
                string = format_date(self.env, fields.Date.to_string(date_to), date_format='MMM yyyy')
            elif period_type in ['quarter','lastquarter']:
                quarter_names = get_quarter_names('abbreviated', locale=get_lang(self.env).code)
                string = u'%s\N{NO-BREAK SPACE}%s' % (quarter_names[date_utils.get_quarter_number(date_to)], date_to.year)
            else:
                dt_from_str = format_date(self.env, fields.Date.to_string(date_from))
                dt_to_str = format_date(self.env, fields.Date.to_string(date_to))
                string = _('From %s to %s') % (dt_from_str, dt_to_str)

        return {
            'string': string,
            'period_type': period_type,
            'mode': mode,
            'strict_range': strict_range,
            'date_from': date_from and fields.Date.to_string(date_from) or False,
            'date_to': fields.Date.to_string(date_to),
        }

    def calculate_percentage_change(self, original_number, final_number):
        if original_number == 0:
            return 'n/a'

        percentage_difference = ((final_number - original_number) / abs(original_number)) * 100
        percentage_difference = '%.2f' % percentage_difference + '%'

        return percentage_difference

    @api.model
    def view_report(self, option, tag, **kw):
        r = self.env['ctm.dynamic.balance.sheet.report'].search(
            [('id', '=', option[0])])
        data = {
            'display_account': r.display_account if r.budget == 'off' else 'all',
            'model': self,
            'journals': r.journal_ids,
            'target_move': r.target_move,
            'accounts': r.account_ids,
            'account_tags': r.account_tag_ids,
            'analytic_ids': r.analytic_ids,
            'analytic_tag_ids': r.analytic_tag_ids,
            'analytic_group_ids': r.analytic_group_ids,
            'comparison': r.comparison,
            'previous': r.previous,
            'currency_id': r.report_currency_id,
            'book': r.book,
            'consolidate': r.consolidate,
            'entities_comparison': r.entities_comparison,
            'comp_detail': r.comp_detail,
            'filter_budget': r.filter_budget,
            'date_from': r.date_from,
            'date_to': r.date_to,
            'report_name': tag,
            'budget': r.budget,
            'debit_credit': r.debit_credit,
            'all_account': r.all_account,
            'currencies': r.currency_ids,
        }

        if r.date_from:
            data.update({'date_from': r.date_from})
        else:
            if tag == "Balance Sheet":
                data.update({'date_from': date.today()})
            else:
                data.update({'date_from': date.today().replace(day=1)})

        if r.date_to:
            data.update({'date_to': r.date_to})
        else:
            if tag == "Balance Sheet":
                data.update({'date_to': date.today()})
            else:
                data.update({'date_to': date.today() + relativedelta(day=31)})
        
        if r.entities_comparison:
            if r.entities_comparison == 'on':
                cop_ids = self.env['res.company'].search([('id', 'in', self.env.context['allowed_company_ids'])])
                company_domain = [('company_id', 'in', self.env.context['allowed_company_ids'])]
            else:
                cop_ids = self.env.company
                company_domain = [('company_id', '=', self.env.company.id)]
        else:
            company_domain = [('company_id', '=', self.env.company.id)]
            cop_ids = self.env.company

        if r.account_tag_ids:
            company_domain.append(
                ('tag_ids', 'in', r.account_tag_ids.ids))
        
        if r.account_ids:
            company_domain.append(('id', 'in', r.account_ids.ids))
        
        sort = kw.get('sort')
        sort_type = kw.get('sort_type')
        
        # new_account_ids = self.env['account.account'].search([('id', 'in', result_query)])
        # new_account_ids = self.env['account.account'].search([('company_id', 'in', cop_ids.ids)])
        new_account_ids = self.env['account.account'].search(company_domain)
        data.update({'accounts': new_account_ids,})

        def rec_report(analytic_report_name, company_id):
            records = self._get_report_values(data, company_id)
            currency = data['currency_id']
            symbol = currency.symbol
            rounding = currency.rounding
            position = currency.position
            currency_rate = 0
            currency_id = currency
            rate_curr_ids = currency_id.rate_ids.sorted(key=lambda r: r.name)
            if data.get('date_from') and data.get('date_to'):
                rate_ids = currency_id.rate_ids.filtered(lambda r: r.name >= fields.Date.from_string(data.get('date_from')) and r.name <= fields.Date.from_string(data.get('date_to'))).sorted(key=lambda r: r.name)
                if rate_ids:
                    currency_rate = rate_ids[-1].rate
                else:
                    if rate_curr_ids:
                        currency_rate = rate_curr_ids[len(rate_curr_ids)-1].rate
                    else:
                        currency_rate = currency_id.rate
            elif data.get('date_from'):
                rate_ids = currency_id.rate_ids.filtered(lambda r: r.name >= fields.Date.from_string(data.get('date_from'))).sorted(key=lambda r: r.name)
                if rate_ids:
                    currency_rate = rate_ids[-1].rate
                else:
                    if rate_curr_ids:
                        currency_rate = rate_curr_ids[len(rate_curr_ids)-1].rate
                    else:
                        currency_rate = currency_id.rate
            elif data.get('date_to'):
                rate_ids = currency_id.rate_ids.filtered(lambda r: r.name <= fields.Date.from_string(data.get('date_to'))).sorted(key=lambda r: r.name)
                if rate_ids:
                    currency_rate = rate_ids[-1].rate
                else:
                    if rate_curr_ids:
                        currency_rate = rate_curr_ids[len(rate_curr_ids)-1].rate
                    else:
                        currency_rate = currency_id.rate
            else:
                if rate_curr_ids:
                    currency_rate = rate_curr_ids[len(rate_curr_ids)-1].rate
                else:
                    currency_rate = currency_id.rate

            def final_record(rec_rprt): 
                if filters['account_tags'] != ['All']:
                    tag_accounts = list(map(lambda x: x.code, new_account_ids))

                    def filter_code(rec_dict):
                        if rec_dict['code'] in tag_accounts:
                            return True
                        else:
                            return False

                    new_records = list(filter(filter_code, records['Accounts']))
                    records['Accounts'] = new_records

                account_report_id = self.env['account.financial.report'].search([
                    ('name', 'ilike', tag)])

                if data['analytic_ids'] or data['analytic_tag_ids'] or data['analytic_group_ids']:
                    new_data = {
                                'id': self.id,
                                'enable_filter': True,
                                'debit_credit': True,
                                'date_from': False,
                                'date_to': False,
                                'account_report_id': account_report_id,
                                'target_move': filters['target_move'],
                                'filter_budget': data['filter_budget'],
                                'budget': data['budget'],
                                'debit_credit': data['debit_credit'],
                                'analytic_ids': data['analytic_ids'],
                                'analytic_tag_ids': data['analytic_tag_ids'],
                                'analytic_group_ids': data['analytic_group_ids'],
                                'view_format': 'vertical',
                                'company_id': company_id.id,
                                'consolidate': filters['consolidate'].lower(),
                                'entities_comparison': filters['entities_comparison'].lower(),
                                'all_account': filters['all_account'].lower(),
                                'used_context': {
                                                 'journal_ids': False,
                                                 'state': filters['target_move'].lower(),
                                                 'date_from': False if tag == "Balance Sheet" else data['date_from'],
                                                 'date_to': data['date_to'],
                                                 'filter_budget': data['filter_budget'],
                                                 'budget': data['budget'],
                                                 'strict_range': False,
                                                 'company_id': company_id.id,
                                                 'consolidate': filters['consolidate'].lower(),
                                                 'entities_comparison': filters['entities_comparison'].lower(),
                                                 'lang': 'en_US',
                                                 'analytic_ids': data['analytic_ids'],
                                                 'analytic_tag_ids': data['analytic_tag_ids'],
                                                 'analytic_group_ids': data['analytic_group_ids'],
                                                 'all_account': filters['all_account'].lower(),
                                                 'currency_ids': False,
                                                }
                               }
                else:
                    new_data = {
                                'id': self.id,
                                'enable_filter': True,
                                'debit_credit': True,
                                'date_from': False,
                                'date_to': False,
                                'account_report_id': account_report_id,
                                'target_move': filters['target_move'],
                                'filter_budget': data['filter_budget'],
                                'budget': data['budget'],
                                'debit_credit': data['debit_credit'],
                                'view_format': 'vertical',
                                'company_id': company_id.id,
                                'consolidate': filters['consolidate'].lower(),
                                'entities_comparison': filters['entities_comparison'].lower(),
                                'all_account': filters['all_account'].lower(),
                                'used_context': {
                                                 'journal_ids': False,
                                                 'state': filters['target_move'].lower(),
                                                 'date_from': False if tag == "Balance Sheet" else data['date_from'],
                                                 'date_to': data['date_to'],
                                                 'filter_budget': data['filter_budget'],
                                                 'budget': data['budget'],
                                                 'debit_credit': data['debit_credit'],
                                                 'strict_range': False,
                                                 'company_id': company_id.id,
                                                 'consolidate': filters['consolidate'].lower(),
                                                 'entities_comparison': filters['entities_comparison'].lower(),
                                                 'lang': 'en_US',
                                                 'all_account': filters['all_account'].lower(),
                                                 'currency_ids': False,
                                                }
                               }
                
                account_lines = self.get_account_lines(new_data)
                report_lines = self.view_report_pdf(account_lines, new_data)['report_lines']
                move_line_accounts = []
                move_lines_dict = {}


                for rec in rec_rprt['Accounts']:
                    move_line_accounts.append(rec['code'])
                    move_lines_dict[rec['code']] = {}
                    move_lines_dict[rec['code']]['debit'] = rec['debit']
                    move_lines_dict[rec['code']]['credit'] = rec['credit']
                    move_lines_dict[rec['code']]['balance'] = rec['balance']
                    # move_lines_dict[rec['code']]['balance'] = (move_lines_dict[rec['code']]['debit'] - move_lines_dict[rec['code']]['credit'])

                report_lines_move = []
                parent_list = []

                def filter_movelines_parents(obj):
                    for each in obj:
                        if each['report_type'] == 'accounts':
                            if 'code' in each:
                                if each['code'] in move_line_accounts:
                                    parent_list.append(each['p_id'])
                        report_lines_move.append(each)

                filter_movelines_parents(report_lines)

                for rec in report_lines_move:
                    if rec['report_type'] == 'accounts':
                        if 'code' in rec:
                            if rec['code'] in move_line_accounts:
                                rec['debit'] = move_lines_dict[rec['code']]['debit']
                                rec['credit'] = move_lines_dict[rec['code']]['credit']
                                rec['balance'] = move_lines_dict[rec['code']]['balance']
                                # rec['balance'] = (move_lines_dict[rec['code']]['debit'] - move_lines_dict[rec['code']]['credit'])

                parent_list = list(set(parent_list))
                max_level = 0
                for rep in report_lines_move:
                    if rep['level'] > max_level:
                        max_level = rep['level']

                def get_parents(obj):
                    for item in report_lines_move:
                        for each in obj:
                            if each in item['c_ids']:
                                obj.append(item['r_id'])
                        if item['report_type'] == 'account_report':
                            obj.append(item['r_id'])
                            # break

                get_parents(parent_list)

                for i in range(max_level):
                    get_parents(parent_list)

                parent_list = list(set(parent_list))
                final_report_lines = []

                
                for rec in report_lines_move:
                    if rec['report_type'] != 'accounts':
                        if rec['r_id'] in parent_list:
                            final_report_lines.append(rec)
                    else:
                        final_report_lines.append(rec)

                
                def filter_sum(obj):
                    sum_list = {}
                    for pl in parent_list:
                        sum_list[pl] = {}
                        sum_list[pl]['s_debit'] = 0
                        sum_list[pl]['s_credit'] = 0
                        sum_list[pl]['s_balance'] = 0

                    cek = 0
                    d = 0
                    c = 0
                    for each in obj:
                        if each['p_id'] and each['p_id'] in parent_list:
                            sum_list[each['p_id']]['s_debit'] += each['debit']
                            sum_list[each['p_id']]['s_credit'] += each['credit']
                            sum_list[each['p_id']]['s_balance'] += each['balance']
                    return sum_list

                def assign_sum(obj):
                    for each in obj:
                        if each['r_id'] in parent_list and \
                                each['report_type'] != 'account_report':
                            each['debit'] = sum_list_new[each['r_id']]['s_debit']
                            each['credit'] = sum_list_new[each['r_id']]['s_credit']

                for p in range(max_level):
                    sum_list_new = filter_sum(final_report_lines)
                    assign_sum(final_report_lines)  

                for rec in final_report_lines:
                    if data.get('budget') == 'on':
                        budget_amount = {'planned_amount': 0.0, 'actual_amount': 0.0}
                        if rec['type'] == 'account':
                            budget_amount = self.get_budget_amount(rec['account'], data)
                        rec['planned_amount'] = budget_amount.get('planned_amount')
                        rec['actual_amount'] = budget_amount.get('actual_amount')
                    rec['balance'] = rec['balance'] * int(rec['report_sign'])
                    rec['debit'] = round(rec['debit'] * currency_rate, 2)
                    rec['credit'] = round(rec['credit'] * currency_rate, 2)
                    rec['balance'] = round(rec['balance'] * currency_rate, 2)
                    # rec['balance'] = round((rec['debit'] - rec['credit']), 2)
                    rec['balance_cmp'] = round(rec['balance_cmp'] * currency_rate, 2)
                    
                    # if rec['report_type'] != 'account_report':
                    #     rec['balance'] = rec['debit'] - rec['credit']
                    
                    # if (rec['balance_cmp'] < 0 and rec['balance'] > 0) or (
                    #         rec['balance_cmp']  > 0 and rec['balance'] < 0):
                    #     rec['balance'] = rec['balance'] * -1

                    if position == "before":
                        rec['m_debit'] = symbol + " " + "{:,.2f}".format(rec['debit'])
                        rec['m_credit'] = symbol + " " + "{:,.2f}".format(rec['credit'])
                        rec['m_balance'] = symbol + " " + "{:,.2f}".format(rec['balance'])
                        if data.get('budget') == 'on':
                            rec['m_planned_amount'] = symbol + " " + "{:,.2f}".format(rec['planned_amount'])
                            rec['m_actual_amount'] = symbol + " " + "{:,.2f}".format(rec['actual_amount'])
                    else:
                        rec['m_debit'] = "{:,.2f}".format(rec['debit']) + " " + symbol
                        rec['m_credit'] = "{:,.2f}".format(rec['credit']) + " " + symbol
                        rec['m_balance'] = "{:,.2f}".format(rec['balance']) + " " + symbol
                        if data.get('budget') == 'on':
                            rec['m_planned_amount'] = "{:,.2f}".format(rec['planned_amount']) + " " + symbol
                            rec['m_actual_amount'] = "{:,.2f}".format(rec['actual_amount']) + " " + symbol

                return final_report_lines

            cat_report_line = []
            res_rprt = {
                'anl_id': '00001',
                'anl_name': analytic_report_name,
                'report_lines': records['Accounts'],
                'final_report_lines': final_record(records),
                'budget_name': ['Actual Amount', 'Planned Amount'],
            }
            cat_report_line.append(res_rprt)


            vals_tmp = []
            acc_new = []
            number = 1
            for s in cat_report_line:
                for q in s['final_report_lines']:
                    if 'code' in q:
                        for r in s['report_lines']:
                            if r['code'] == q['code']:
                                code_acc = list(filter(lambda x: x['number'] == r['code'] and x['parentid'] == q['parent'], vals_tmp))
                                if code_acc:
                                    code_acc[0][s['anl_name']] = q['balance']
                                    if data.get('budget') == 'on':
                                        code_acc[0]['planned_amount'] = q['planned_amount']
                                        code_acc[0]['actual_amount'] = q['actual_amount']
                                else:
                                    res={}
                                    res['id'] = r['id']
                                    res['code'] = r['code']
                                    res['name'] = r['name']
                                    res['code_anl'] = analytic_report_name
                                    res['debit'] = q['debit']
                                    res['credit'] = q['credit']
                                    res[s['anl_name']] = q['balance']
                                    res['balance'] = q['balance']
                                    if data.get('budget') == 'on':
                                        res['planned_amount'] = q['planned_amount']
                                        res['actual_amount'] = q['actual_amount']
                                    res['number'] = r['code']
                                    res['number_id'] = str(q['a_id']) + str(q['parent'] if q['parent'] else '')
                                    res['parentid'] = q['parent']
                                    res['level'] = q['level']
                                    res['sequence'] = 999
                                    vals_tmp.append(res)
                            if 'new_code' in r:
                                if r['new_code'] == True:
                                    newacc = list(filter(lambda x: r['code'] in x, acc_new))
                                    if not newacc:
                                        acc_new.append(r)
                    else:
                        code_acc1 = list(filter(lambda x: x['name'] == q['name'] and x['parentid'] == q['parent'], vals_tmp))                   
                        if code_acc1:
                            code_acc1[0][str(s['anl_name'])] = q['balance']
                            if data.get('budget') == 'on':
                                code_acc1[0]['planned_amount'] = q['planned_amount']
                                code_acc1[0]['actual_amount'] = q['actual_amount']
                        else:
                            res={}
                            # res['number'] = '0000' + str(number)
                            res['number'] = q['id']
                            res['number_id'] = q['id']
                            res['name'] = q['name']
                            res['code_anl'] = analytic_report_name
                            res[s['anl_name']] = q['balance']
                            res['debit'] = q['debit']
                            res['credit'] = q['credit']
                            res['balance'] = q['balance']
                            if data.get('budget') == 'on':
                                res['planned_amount'] = q['planned_amount']
                                res['actual_amount'] = q['actual_amount']
                            res['parentid'] = q['parent']
                            res['level'] = q['level']
                            res['sequence'] = q['sequence']
                            vals_tmp.append(res)
                            number = number+1

                    for newacc in acc_new:
                        children = self.env['account.financial.report'].search([('account_ids', 'in', [newacc['code']])], order='sequence ASC')
                        if not children:
                            childrenacc = self.env['account.account'].search([('code', 'in', [newacc['code']])])
                            children3 = self.env['account.financial.report'].search([('account_type_ids', 'in', [(tn.user_type_id.id) for tn in childrenacc])], order='sequence ASC')
                            for mnb in children3:
                                parent_rep = list(filter(lambda x: x['report_type'] != 'sum' and x['type'] == 'report' and x['name'] == mnb.name, s['final_report_lines']))
                                if parent_rep:
                                    code_acc = list(filter(lambda x: x['number'] == newacc['code'] and x['parentid'] == parent_rep[0]['id'], vals_tmp))
                                    if code_acc:
                                        code_acc[0][s['anl_name']] = newacc['balance']
                                        if data.get('budget') == 'on':
                                            code_acc[0]['planned_amount'] = newacc['planned_amount']
                                            code_acc[0]['actual_amount'] = newacc['actual_amount']
                                    else:
                                        res={}
                                        res['id'] = newacc['id']
                                        res['code'] = newacc['code']
                                        res['name'] = newacc['name']
                                        res['code_anl'] = analytic_report_name
                                        res['debit'] = newacc['debit']
                                        res['credit'] = newacc['credit']
                                        res['balance'] = newacc['balance']
                                        res[s['anl_name']] = newacc['balance']
                                        if data.get('budget') == 'on':
                                            res['planned_amount'] = newacc['planned_amount']
                                            res['actual_amount'] = newacc['actual_amount']
                                        res['number'] = newacc['code']
                                        res['number_id'] = str(newacc['code']) + str(newacc['name']) + str(newacc['id']) + str(parent_rep[0]['id'] if parent_rep[0]['id'] else '')
                                        res['parentid'] = parent_rep[0]['id']
                                        res['level'] = parent_rep[0]['level'] + 1
                                        res['sequence'] = 999
                                        no=1
                                        for newtemp in vals_tmp:
                                            if newtemp['parentid'] == parent_rep[0]['id']:
                                                vals_tmp.insert(no, res)
                                                break
                                            no=no+1

                    report_tmp = self._getcodeacc(q['name'])
                    code_acc3 = list(filter(lambda x: x['code'] in report_tmp, s['report_lines']))
                    if code_acc3:
                        for cekpl in code_acc3:
                            total_acc = 0
                            total_planned_amount = 0
                            total_actual_amount = 0
                            for xxx in code_acc3:
                                total_acc += xxx['balance']
                                if data.get('budget') == 'on':
                                    total_planned_amount += xxx['planned_amount']
                                    total_actual_amount += xxx['actual_amount']
                        code_acc4 = list(filter(lambda x: x['name'] == q['name'], vals_tmp))
                        if code_acc4:
                            code_acc4[0][s['anl_name']] = total_acc
                            if data.get('budget') == 'on':
                                code_acc4[0]['planned_amount'] = total_planned_amount
                                code_acc4[0]['actual_amount'] = total_actual_amount

                    code_acc2 = list(filter(lambda x: x['number'] == q['parent'], vals_tmp))
                    if code_acc2:
                        code_acc5 = list(filter(lambda x: x['parentid'] == code_acc2[0]['number'], vals_tmp))
                        total_acc = 0
                        total_planned_amount = 0
                        total_actual_amount = 0
                        for xxx in code_acc5:
                            if s['anl_name'] in xxx:
                                total_acc += xxx[s['anl_name']]
                                if data.get('budget') == 'on':
                                    total_planned_amount += xxx['planned_amount']
                                    total_actual_amount += xxx['actual_amount']
                        code_acc2[0][s['anl_name']] = total_acc
                        if data.get('budget') == 'on':
                            code_acc2[0]['planned_amount'] = total_planned_amount
                            code_acc2[0]['actual_amount'] = total_actual_amount

                code_acc5 = list(filter(lambda x: x['number'] not in [(accres['code']) for accres in s['report_lines']] , vals_tmp))
                numb = len(code_acc5)-1
                while numb >= 0:
                  code_acc6 = list(filter(lambda x: x['parentid'] == code_acc5[numb]['number'], vals_tmp))
                  if code_acc6:
                    total_acc = 0
                    total_planned_amount = 0
                    total_actual_amount = 0
                    for total_balance in code_acc6:
                        if s['anl_name'] in total_balance:
                            total_acc += total_balance[s['anl_name']]
                            if data.get('budget') == 'on':
                                total_planned_amount += total_balance['planned_amount']
                                total_actual_amount += total_balance['actual_amount']
                    code_acc5[numb][s['anl_name']] = total_acc
                    if data.get('budget') == 'on':
                        code_acc5[numb]['planned_amount'] = total_planned_amount
                        code_acc5[numb]['actual_amount'] = total_actual_amount
                  numb -= 1
                code_acc5 = list(filter(lambda x: x['parentid'] == False, vals_tmp))
                if code_acc5:
                    code_acc6 = list(filter(lambda x: x['parentid'] == code_acc5[0]['number'], vals_tmp))
                    if code_acc6:
                        total_acc = 0
                        total_planned_amount = 0
                        total_actual_amount = 0
                        for xxx in code_acc6:
                            if s['anl_name'] in xxx:
                                total_acc += xxx[s['anl_name']]
                                if data.get('budget') == 'on':
                                    total_planned_amount += xxx['planned_amount']
                                    total_actual_amount += xxx['actual_amount']
                        code_acc5[0][s['anl_name']] = total_acc
                        if data.get('budget') == 'on':
                            code_acc5[0]['planned_amount'] = total_planned_amount
                            code_acc5[0]['actual_amount'] = total_actual_amount
                
                for rec_Rep in vals_tmp:
                    if s['anl_name'] in rec_Rep: 
                        rec_Rep[s['anl_name']] = 0.0 if rec_Rep[s['anl_name']] == -0.0 else rec_Rep[s['anl_name']]
                        rec_Rep['debit'] = 0.0 if rec_Rep['debit'] == -0.0 else rec_Rep['debit']
                        rec_Rep['credit'] = 0.0 if rec_Rep['credit'] == -0.0 else rec_Rep['credit']
                        if position == "before":
                            rec_Rep[s['anl_name']] = symbol + " " + "{:,.2f}".format(rec_Rep[s['anl_name']])
                            rec_Rep['debit'] = symbol + " " + "{:,.2f}".format(rec_Rep['debit'])
                            rec_Rep['credit'] = symbol + " " + "{:,.2f}".format(rec_Rep['credit'])                            
                            if data.get('budget') == 'on':
                                rec_Rep['planned_amount'] = symbol + " " + "{:,.2f}".format(rec_Rep['planned_amount'])
                                rec_Rep['actual_amount'] = symbol + " " + "{:,.2f}".format(rec_Rep['actual_amount'])
                        else:
                            rec_Rep[s['anl_name']] = "{:,.2f}".format(rec_Rep[s['anl_name']]) + " " + symbol
                            rec_Rep['debit'] = "{:,.2f}".format(rec_Rep['debit']) + " " + symbol
                            rec_Rep['credit'] = "{:,.2f}".format(rec_Rep['credit']) + " " + symbol
                            if data.get('budget') == 'on':
                                rec_Rep['planned_amount'] = "{:,.2f}".format(rec_Rep['planned_amount']) + " " + symbol
                                rec_Rep['actual_amount'] = "{:,.2f}".format(rec_Rep['actual_amount']) + " " + symbol            
            
            if sort:
                vals_tmp_parent = [d for d in vals_tmp if d['level'] < 3]
                vals_tmp_child = [d for d in vals_tmp if d['level'] >= 3]
                if sort_type == 'desc':
                    vals_tmp_child = sorted(vals_tmp_child, key=lambda d: d[sort], reverse=True)
                else:
                    vals_tmp_child = sorted(vals_tmp_child, key=lambda d: d[sort])
                vals_tmp = vals_tmp_parent + vals_tmp_child

            return {
                'name': tag,
                'type': 'ir.actions.client',
                'tag': tag,
                'filters': filters,
                'currency': currency,
                'currency_id': currency.id,
                'bs_lines': vals_tmp,
                'cat_report_line': cat_report_line,
                'years_preview': False,
            }

        comp_vals_rep = []
        vals_rep = []
        list_cop_names = []
        list_cop_ids = []
        filters = False
        currency = False
        currency_id = False
        years_preview = False
        for company_id in cop_ids:
            if r.entities_comparison:
                if r.entities_comparison == 'on':
                    cop_ids = self.env['res.company'].search([])
                    context = dict(self.env.context)
                    context.update({'allowed_company_ids' : cop_ids.ids})
                    self.env.context = context
                    comp = self.env['res.company'].search([('id', 'in', cop_ids.ids)])
                    self.env.companies = comp
                else:
                    cop_ids = self.env.company
            else:
                cop_ids = self.env.company
            
            cek_accounts = self.env['account.account'].search([('company_id', '=', company_id.id)])
            if not cek_accounts:
                continue
            list_cop_names.append(company_id.name)
            list_cop_ids.append(company_id.id)
            filters = self._get_filter(option, company_id)                    
            datareport = {}
            if data.get('comp_detail') == 'custom_comp':
                data['comparison'] +=1
            if data.get('analytic_group_ids'):
                for group_anl in data.get('analytic_group_ids'):
                    get_filter_date = self._init_filter_date(data, data.get('comp_detail'))
                    date_comp = fields.Date.from_string(get_filter_date['date_from'])
                    data.update({
                                    'date_from': False if tag == 'Balance Sheet' else fields.Date.from_string(get_filter_date['date_from']),
                                    'date_to': fields.Date.from_string(get_filter_date['date_to']),
                                    })
                    filters.update({
                                    'date_from': False if tag == 'Balance Sheet' else fields.Date.from_string(get_filter_date['date_from']),
                                    'date_to': fields.Date.from_string(get_filter_date['date_to']),
                                })
                    for group_anl_line in group_anl.analyticnew_ids:
                        data.update({
                                    'analytic_ids': self.env['account.analytic.account'].browse(group_anl_line.name.ids)
                                    })
                        filters.update({
                                    'analytic_ids': self._init_filter_date(data, data.get('comp_detail'))
                                    })
                        
                        nameanl = group_anl_line.name.name
                        d_report = rec_report(nameanl, company_id)
                        data.update({'date_from': date_comp})
                        filters.update({'date_from': date_comp})
                        if 'name' not in datareport:
                            datareport['name'] = d_report['tag']
                        if 'type' not in datareport:
                            datareport['type'] = 'ir.actions.client'
                        if 'tag' not in datareport:
                            datareport['tag'] = d_report['tag']
                        if 'filters' not in datareport:
                            datareport['filters'] = d_report['filters']
                        if 'currency' not in datareport:
                            datareport['currency'] = d_report['currency']
                        if 'currency_id' not in datareport:
                            datareport['currency_id'] = d_report['currency_id']
                        if 'preview_acc' not in datareport:
                            datareport['preview_acc'] = [nameanl]
                        else:
                            datareport['preview_acc'].append(nameanl)
                        if 'lines' not in datareport:
                            datareport['lines'] = []
                        for x in d_report['bs_lines']:
                            x['rprt_lines']=[]
                            res_tmp_rprt = {}
                            res_tmp_rprt['report_line'] = nameanl
                            res_tmp_rprt[nameanl] = x[nameanl]
                            res_tmp_rprt['debit'] = x['debit']
                            res_tmp_rprt['credit'] = x['credit']
                            if 'planned_amount' in x:
                                res_tmp_rprt['planned_amount'] = x['planned_amount']
                                res_tmp_rprt['actual_amount'] =  x['actual_amount']
                            # x['rprt_lines'].update({nameanl : res_tmp_rprt})
                            x['rprt_lines'].append({'company' : company_id.name, 'company_id' : company_id.id, company_id.id : {nameanl : res_tmp_rprt}})
                            cek_acc_key = list(filter(lambda y: y['number_id'] == x['number_id'], datareport['lines']))
                            if cek_acc_key:
                                for cek_acc_key_line in (cek_acc_key[0]['rprt_lines']):
                                    if company_id.id in cek_acc_key_line:
                                        (cek_acc_key_line[company_id.id])[nameanl] = res_tmp_rprt

                                target_values = []
                                for item in cek_acc_key[0]['rprt_lines']:
                                    inner_dict = item.get(1, {})
                                    for inner_key, inner_value in inner_dict.items():
                                        if isinstance(inner_value, dict) and inner_key in inner_value:
                                            target_values.append(inner_value[inner_key])

                                total_analytic = 0
                                for value in target_values:
                                    value_match = re.search(r'(-?[\d,]+[.]?[\d]*)', value)
                                    value_float = float(value_match.group().replace(',', ''))
                                    total_analytic += value_float

                                currency = data['currency_id']
                                symbol = currency.symbol
                                position = currency.position
                                if position == "before":
                                    total_analytic = symbol + " " + "{:,.2f}".format(total_analytic)
                                else:
                                    total_analytic = "{:,.2f}".format(total_analytic) + " " + symbol

                                cek_acc_key_line['total_analytic'] = total_analytic

                                continue
                            datareport['lines'].append(x)
                            # cek_anl_detail = list(filter(lambda x: x['company_id'] == company_detail['company_id'], datareport['lines']))
                            # if not cek_anl_detail:
                            #     rec_Rep['rprt_lines'].append(company_detail)
                    else:
                        nameanl = group_anl.name
                        d_report = rec_report(nameanl, company_id)
                        data.update({'date_from': date_comp})
                        filters.update({'date_from': date_comp})
                        if 'name' not in datareport:
                            datareport['name'] = d_report['tag']
                        if 'type' not in datareport:
                            datareport['type'] = 'ir.actions.client'
                        if 'tag' not in datareport:
                            datareport['tag'] = d_report['tag']
                        if 'filters' not in datareport:
                            datareport['filters'] = d_report['filters']
                        if 'currency' not in datareport:
                            datareport['currency'] = d_report['currency']
                        if 'currency_id' not in datareport:
                            datareport['currency_id'] = d_report['currency_id']
                        if 'preview_acc' not in datareport:
                            datareport['preview_acc'] = [nameanl]
                        else:
                            datareport['preview_acc'].append(nameanl)
                        if 'lines' not in datareport:
                            datareport['lines'] = []
                        for x in d_report['bs_lines']:
                            x['rprt_lines']=[]
                            res_tmp_rprt = {}
                            res_tmp_rprt['report_line'] = nameanl
                            res_tmp_rprt[nameanl] = x[nameanl]
                            res_tmp_rprt['debit'] = x['debit']
                            res_tmp_rprt['credit'] = x['credit']
                            if 'planned_amount' in x:
                                res_tmp_rprt['planned_amount'] = x['planned_amount']
                                res_tmp_rprt['actual_amount'] =  x['actual_amount']
                            # x['rprt_lines'].update({nameanl : res_tmp_rprt})
                            x['rprt_lines'].append({'company' : company_id.name, 'company_id' : company_id.id, company_id.id : {nameanl : res_tmp_rprt}})
                            cek_acc_key = list(filter(lambda y: y['number_id'] == x['number_id'], datareport['lines']))
                            if cek_acc_key:
                                for cek_acc_key_line in (cek_acc_key[0]['rprt_lines']):
                                    if company_id.id in cek_acc_key_line:
                                        (cek_acc_key_line[company_id.id])[nameanl] = res_tmp_rprt
                                continue
                            datareport['lines'].append(x)
            else:
                numb_comp = data['comparison'] + 1
                for numb_comp in range(0,data['comparison'] + 1):
                    if numb_comp > 0:
                        if data.get('previous'):
                            get_filter_date = self._get_dates_previous_period(data, data.get('comp_detail'))
                        else:
                            if data.get('comp_detail') == 'custom_comp':
                                get_filter_date = self._get_dates_previous_period(data, data.get('comp_detail'))
                            else:
                                get_filter_date = self._get_dates_previous_year(data, data.get('comp_detail'))
                        date_comp = fields.Date.from_string(get_filter_date['date_from'])
                        data.update({
                                    'date_from': False if tag == 'Balance Sheet' else fields.Date.from_string(get_filter_date['date_from']),
                                    'date_to': fields.Date.from_string(get_filter_date['date_to']),
                                    })
                        filters.update({
                                        'date_from': False if tag == 'Balance Sheet' else fields.Date.from_string(get_filter_date['date_from']),
                                        'date_to': fields.Date.from_string(get_filter_date['date_to']),
                                    })
                    else:
                        get_filter_date = self._init_filter_date(data, data.get('comp_detail'))
                        date_comp = fields.Date.from_string(get_filter_date['date_from'])
                        data.update({
                                    'date_from': False if tag == 'Balance Sheet' else fields.Date.from_string(get_filter_date['date_from']),
                                    'date_to': fields.Date.from_string(get_filter_date['date_to']),
                                    })
                        filters.update({
                                        'date_from': False if tag == 'Balance Sheet' else fields.Date.from_string(get_filter_date['date_from']),
                                        'date_to': fields.Date.from_string(get_filter_date['date_to']),
                                    })
                    d_report = rec_report(get_filter_date['string'], company_id)
                    if tag == 'Balance Sheet':
                        if data.get('comp_detail') == 'today':
                            data.update({'date_from': fields.Date.from_string(get_filter_date['date_to']),
                                         'date_to': fields.Date.from_string(get_filter_date['date_to'])})
                            filters.update({'date_from': fields.Date.from_string(get_filter_date['date_to']),
                                            'date_to': fields.Date.from_string(get_filter_date['date_to'])})
                        else:
                            data.update({'date_from': date_comp})
                            filters.update({'date_from': date_comp})
                    else:
                        data.update({'date_from': date_comp})
                        filters.update({'date_from': date_comp})


                    if 'name' not in datareport:
                        datareport['name'] = d_report['tag']
                    if 'type' not in datareport:
                        datareport['type'] = 'ir.actions.client'
                    if 'tag' not in datareport:
                        datareport['tag'] = d_report['tag']
                    if 'filters' not in datareport:
                        datareport['filters'] = d_report['filters']
                    if 'currency' not in datareport:
                        datareport['currency'] = d_report['currency']
                    if 'currency_id' not in datareport:
                        datareport['currency_id'] = d_report['currency_id']
                    if 'preview_acc' not in datareport:
                        datareport['preview_acc'] = [get_filter_date['string']]
                    else:
                        datareport['preview_acc'].append(get_filter_date['string'])
                    if 'lines' not in datareport:
                        datareport['lines'] = []
                    for x in d_report['bs_lines']:
                        x['rprt_lines']=[]
                        res_tmp_rprt = {}
                        res_tmp_rprt['report_line'] = get_filter_date['string']
                        res_tmp_rprt[get_filter_date['string']] = x[get_filter_date['string']]
                        res_tmp_rprt['debit'] = x['debit']
                        res_tmp_rprt['credit'] = x['credit']
                        if 'planned_amount' in x:
                            res_tmp_rprt['planned_amount'] = x['planned_amount']
                            res_tmp_rprt['actual_amount'] =  x['actual_amount']
                        x['rprt_lines'].append({'company' : company_id.name, 'company_id' : company_id.id, company_id.id : {get_filter_date['string'] : res_tmp_rprt}})

                        percentage_difference = 'n/a'
                        cek_acc_key = list(filter(lambda y: y['number_id'] == x['number_id'], datareport['lines']))
                        if cek_acc_key:
                            for cek_acc_key_line in (cek_acc_key[0]['rprt_lines']):
                                if company_id.id in cek_acc_key_line:
                                    (cek_acc_key_line[company_id.id])[get_filter_date['string']] = res_tmp_rprt

                            target_values = []
                            for item in cek_acc_key[0]['rprt_lines']:
                                inner_dict = item.get(1, {})
                                for inner_key, inner_value in inner_dict.items():
                                    if isinstance(inner_value, dict) and inner_key in inner_value:
                                        target_values.append(inner_value[inner_key])

                            if len(target_values) == 2:
                                value1_match = re.search(r'(-?[\d,]+[.]?[\d]*)', target_values[0])
                                value2_match = re.search(r'(-?[\d,]+[.]?[\d]*)', target_values[1])

                                if value1_match and value2_match:
                                    value1 = float(value1_match.group().replace(',', ''))
                                    value2 = float(value2_match.group().replace(',', ''))

                                    percentage_difference = self.calculate_percentage_change(value2, value1)
                                    cek_acc_key_line['comparison_percentage'] = percentage_difference

                            continue

                        x['rprt_lines'][0]['comparison_percentage'] = percentage_difference
                        datareport['lines'].append(x)

            if len(comp_vals_rep) > 0:
                for dump_lines in datareport['lines']:
                    cek_dump_lines = list(filter(lambda y: y['number_id'] == dump_lines['number_id'], comp_vals_rep))
                    if cek_dump_lines:
                        (cek_dump_lines[0]['rprt_lines']).append((dump_lines['rprt_lines'])[0])
                    else:
                        comp_vals_rep.append(dump_lines)
            else:
                comp_vals_rep = datareport['lines']

            filters = datareport['filters']
            currency = datareport['currency']
            currency_id = datareport['currency_id']
            years_preview = datareport['preview_acc']
        list_company_detail = list(filter(lambda y: y['parentid'] == False, comp_vals_rep))
        if list_company_detail:
            list_company_detail = list_company_detail[0]['rprt_lines']
        comp_vals_rep = sorted(comp_vals_rep, key=lambda d: d.get('sequence', float('inf')))
        def _get_children_by_ord(pid,vals_tmp_data):
            res = [pid]
            children = list(filter(lambda x: x['parentid'] == pid, vals_tmp_data))
            for child in children:
                res += _get_children_by_ord(child['number_id'],vals_tmp_data)
            return res

        numb_rep = 0
        currency = data['currency_id']
        symbol = currency.symbol
        position = currency.position
        blank_field = symbol + " 0.00" if position == "before" else "0.00 " + symbol
        if comp_vals_rep:
            if comp_vals_rep:
                sortview = _get_children_by_ord((comp_vals_rep[0])['number_id'], comp_vals_rep)
                for rec_Rep in sortview:
                    mid = list(filter(lambda x: x['number_id'] == rec_Rep, comp_vals_rep))
                    if mid:
                        vals_rep += mid
                numb_rep = 0
                for rec_Rep in vals_rep:
                    for company_detail in list_company_detail:
                        cek_company_detail = list(filter(lambda x: x['company_id'] == company_detail['company_id'], rec_Rep['rprt_lines']))
                        if not cek_company_detail:
                            rec_Rep['rprt_lines'].append(company_detail)
                        if cek_company_detail:
                            for years in years_preview:
                                for key, value in cek_company_detail[0].items():
                                    if key == company_detail['company_id']:
                                        if not years in value:
                                            res_anl_det = {}
                                            res_anl_det['report_line'] = years
                                            res_anl_det[years] = blank_field
                                            res_anl_det['credit'] = blank_field
                                            res_anl_det['debit'] = blank_field
                                            value[years] = res_anl_det

                            for group_anl in data.get('analytic_group_ids'):
                                for group_anl_line in group_anl.analyticnew_ids:
                                    for key, value in cek_company_detail[0].items():
                                        if key == company_detail['company_id']:
                                            if not group_anl_line.name.name in value:
                                                res_anl_det = {}
                                                res_anl_det['report_line'] = group_anl_line.name.name
                                                res_anl_det[group_anl_line.name.name] = blank_field
                                                res_anl_det['credit'] = blank_field
                                                res_anl_det['debit'] = blank_field
                                                value[group_anl_line.name.name] = res_anl_det
                    numb_rep +=1
                    children_list = _get_children_by_ord(rec_Rep['number_id'],vals_rep)
                    get_children_number = len(children_list)
                    if 'code' in rec_Rep:
                           cek = list(filter(lambda x: x['number_id'] == rec_Rep['parentid'], vals_rep))
                           cek[0]["is_parent"] = True
                    if get_children_number > 1:
                        tmp_rec_Rep = {}
                        tmp_rec_Rep_head = {}
                        tmp_rec_Rep["total_value"] = 'total'
                        for key_rec_Rep, value_rec_Rep in rec_Rep.items():
                            tmp_rec_Rep[key_rec_Rep] = value_rec_Rep
                        tmp_rec_Rep["parentid"] = tmp_rec_Rep["number_id"]
                        tmp_rec_Rep["name"] = "Total " + tmp_rec_Rep["name"]
                        tmp_rec_Rep["number_id"] = "total " + tmp_rec_Rep["number_id"]
                        if rec_Rep['parentid'] != False:
                            vals_rep.insert(numb_rep+get_children_number-1,tmp_rec_Rep)
                            if rec_Rep['level'] <= 2:
                                rec_Rep['rprt_lines'] = []
                del vals_rep[0]
                
        if (filters['currencies'])[0] != 'All':
            curr_list = [list_curr for list_curr in filters['currencies']]
        else:
            curr_list = [self.env.company.currency_id.name]

        for tmp_vals in vals_rep:
            new_vals_rep = {}
            tmp_vals_copy = copy.deepcopy(tmp_vals['rprt_lines'])
            subtotal_report_line = 0
            for curr in curr_list:
                currency_vals = self.env['res.currency'].search([('name', '=', curr)])
                rate_ids = currency_vals.rate_ids.sorted(key=lambda r: r.name)
                if tag == "Balance Sheet":
                    if data.get('date_to'):
                        rate_ids = currency_vals.rate_ids.filtered(lambda r: r.name <= fields.Date.from_string(data.get('date_to'))).sorted(key=lambda r: r.name)
                else:
                    if data.get('date_from') and data.get('date_to'):
                        rate_ids = currency_vals.rate_ids.filtered(lambda r: r.name >= fields.Date.from_string(data.get('date_from')) and r.name <= fields.Date.from_string(data.get('date_to'))).sorted(key=lambda r: r.name)
            
                if rate_ids:
                    rate_curr_ids = rate_ids[len(rate_ids)-1].rate
                else:
                    rate_curr_ids = currency_vals.rate

                len_origin = len(currency.name)
                vals = copy.deepcopy(tmp_vals_copy)
                subtotal_report_line = 0
                for comps_list in list_cop_ids:
                    if not tmp_vals_copy:
                        break
                    cek = list(filter(lambda x: x['company_id'] == comps_list, vals))
                    for value_tmp_vals in vals:
                        if comps_list in value_tmp_vals:
                            for preview in years_preview:
                                for key, val in value_tmp_vals.items():
                                    if key == comps_list:
                                        if preview in val:
                                            if filters['budget'] == 'on':
                                                if (val[preview])['planned_amount'] != False:
                                                    tmp_vals_planned_amount = float(re.sub("[.]", "", (str((val[preview])['planned_amount'])[len_origin:])))
                                                    tmp_vals_planned_amount *= rate_curr_ids
                                                    if currency_vals.position == "before":
                                                        (val[preview])['planned_amount'] = currency_vals.symbol + " " + "{:,.2f}".format(tmp_vals_planned_amount)
                                                    else:
                                                        (val[preview])['planned_amount'] = "{:,.2f}".format(tmp_vals_planned_amount) + " " + currency_vals.symbol

                                                if (val[preview])['actual_amount'] != False:
                                                    tmp_vals_actual_amount = float(re.sub("[.]", "", (str((val[preview])['actual_amount'])[len_origin:])))
                                                    tmp_vals_actual_amount *= rate_curr_ids
                                                    if currency_vals.position == "before":
                                                        (val[preview])['actual_amount'] = currency_vals.symbol + " " + "{:,.2f}".format(tmp_vals_actual_amount)
                                                    else:
                                                        (val[preview])['actual_amount'] = "{:,.2f}".format(tmp_vals_actual_amount) + " " + currency_vals.symbol
                                            if (val[preview])[preview] != False:
                                                if (str((val[preview])[preview])[-3:])[0] == ',':
                                                    tmp_vals_debit = float(re.sub("[.]", "", (str((val[preview])['debit'])[len_origin:])))
                                                    tmp_vals_debit *= rate_curr_ids
                                                    tmp_vals_credit = float(re.sub("[.]", "", (str((val[preview])['credit'])[len_origin:])))
                                                    tmp_vals_credit *= rate_curr_ids
                                                    tmp_vals_balance = float(re.sub("[.]", "", (str((val[preview])[preview])[len_origin:])))
                                                    tmp_vals_balance *= rate_curr_ids
                                                    subtotal_report_line += tmp_vals_balance
                                                    if currency_vals.position == "before":
                                                        (val[preview])['debit'] = currency_vals.symbol + " " + "{:,.2f}".format(tmp_vals_debit)
                                                        (val[preview])['credit'] = currency_vals.symbol + " " + "{:,.2f}".format(tmp_vals_credit)
                                                        (val[preview])[preview] = currency_vals.symbol + " " + "{:,.2f}".format(tmp_vals_balance)
                                                    else:
                                                        (val[preview])['debit'] = "{:,.2f}".format(tmp_vals_debit) + " " + currency_vals.symbol
                                                        (val[preview])['credit'] = "{:,.2f}".format(tmp_vals_credit) + " " + currency_vals.symbol
                                                        (val[preview])[preview] = "{:,.2f}".format(tmp_vals_balance) + " " + currency_vals.symbol
                                                if (str((val[preview])[preview])[-3:])[0] == '.':
                                                    tmp_vals_debit = float(re.sub("[,]", "", (str((val[preview])['debit'])[len_origin:])))
                                                    tmp_vals_debit *= rate_curr_ids
                                                    tmp_vals_credit = float(re.sub("[,]", "", (str((val[preview])['credit'])[len_origin:])))
                                                    tmp_vals_credit *= rate_curr_ids
                                                    tmp_vals_balance = float(re.sub("[,]", "", (str((val[preview])[preview])[len_origin:])))
                                                    tmp_vals_balance *= rate_curr_ids
                                                    subtotal_report_line += tmp_vals_balance
                                                    if currency_vals.position == "before":
                                                        (val[preview])['debit'] = currency_vals.symbol + " " + "{:,.2f}".format(tmp_vals_debit)
                                                        (val[preview])['credit'] = currency_vals.symbol + " " + "{:,.2f}".format(tmp_vals_credit)
                                                        (val[preview])[preview] = currency_vals.symbol + " " + "{:,.2f}".format(tmp_vals_balance)
                                                    else:
                                                        (val[preview])['debit'] = "{:,.2f}".format(tmp_vals_debit) + " " + currency_vals.symbol
                                                        (val[preview])['credit'] = "{:,.2f}".format(tmp_vals_credit) + " " + currency_vals.symbol
                                                        (val[preview])[preview] = "{:,.2f}".format(tmp_vals_balance) + " " + currency_vals.symbol                
                new_vals_rep[curr] = vals
            
            if currency.position == "before":
                subtotal_report_line = currency.symbol + " " + "{:,.2f}".format(subtotal_report_line)
            else:
                subtotal_report_line = "{:,.2f}".format(subtotal_report_line) + " " + currency.symbol
                
            tmp_vals['subtotal_report_line'] = subtotal_report_line
            tmp_vals['rprt_lines'] = new_vals_rep

        return {
                'name': tag,
                'type': 'ir.actions.client',
                'tag': tag,
                'filters': filters,
                'currency': currency,
                'currency_id': currency_id,
                'bs_lines': vals_rep,
                'years_preview': years_preview,
                'currency_symbol': r.report_currency_id.symbol,
                'comps_list' : list_cop_ids,
                'comp_names' : list_cop_names,
                'curr_list' : curr_list,
            }
        

    @api.model
    def _get_filter(self, option, company_id):
        data = self._get_filter_data(option, company_id)
        filters = {}
        if data.get('journal_ids'):
            filters['journals'] = self.env['account.journal'].browse(
                data.get('journal_ids')).mapped('code')
        else:
            filters['journals'] = ['All']

        if data.get('account_ids', []):
            filters['accounts'] = self.env['account.account'].browse(
                data.get('account_ids', [])).mapped('code')
        else:
            filters['accounts'] = ['All']

        if data.get('target_move'):
            filters['target_move'] = data.get('target_move')
        else:
            filters['target_move'] = 'posted'

        if data.get('date_from'):
            filters['date_from'] = data.get('date_from')
        else:
            filters['date_from'] = False

        if data.get('date_to'):
            filters['date_to'] = data.get('date_to')
        else:
            filters['date_to'] = False

        if data.get('analytic_ids', []):
            filters['analytic_ids'] = self.env['account.analytic.account'].browse(
                data.get('analytic_ids', [])).mapped('name')
        else:
            filters['analytic_ids'] = ['All']

        if data.get('account_tag_ids'):
            filters['account_tags'] = self.env['account.account.tag'].browse(
                data.get('account_tag_ids', [])).mapped('name')
        else:
            filters['account_tags'] = ['All']

        if data.get('analytic_tag_ids', []):
            filters['analytic_tag_ids'] = self.env['account.analytic.tag'].browse(
                data.get('analytic_tag_ids', [])).mapped('name')
        else:
            filters['analytic_tag_ids'] = ['All']

        if data.get('analytic_group_ids', []):
            filters['analytic_group_ids'] = self.env['account.analytic.group'].browse(
                data.get('analytic_group_ids', [])).mapped('name')
        else:
            filters['analytic_group_ids'] = ['All']

        if data.get('comparison'):
            filters['comparison'] = data.get('comparison')
        else:
            filters['comparison'] = False

        if data.get('previous'):
            filters['previous'] = data.get('previous')
        else:
            filters['previous'] = False

        if data.get('book'):
            filters['book'] = data.get('book')
        else:
            filters['book'] = 'commercial'

        if data.get('consolidate'):
            filters['consolidate'] = data.get('consolidate')
        else:
            filters['consolidate'] = 'off'

        if data.get('entities_comparison'):
            filters['entities_comparison'] = data.get('entities_comparison')
        else:
            filters['entities_comparison'] = 'off'

        if data.get('filter_budget'):
            filters['filter_budget'] = data.get('filter_budget')
        else:
            filters['filter_budget'] = False
        
        if data.get('budget'):
            filters['budget'] = data.get('budget')
        else:
            filters['budget'] = 'off'

        if data.get('debit_credit'):
            filters['debit_credit'] = data.get('debit_credit')
        else:
            filters['debit_credit'] = 'off'

        if data.get('all_account'):
            filters['all_account'] = data.get('all_account')
        else:
            filters['all_account'] = 'off'

        if data.get('currency_ids'):
            filters['currencies'] = self.env['res.currency'].browse(data.get('currency_ids')).mapped('name')
        else:
            filters['currencies'] = ['All']

        filters['company_id'] = ''
        filters['accounts_list'] = data.get('accounts_list')
        filters['journals_list'] = data.get('journals_list')
        filters['analytic_list'] = data.get('analytic_list')
        filters['account_tag_list'] = data.get('account_tag_list')
        filters['analytic_tag_list'] = data.get('analytic_tag_list')
        filters['analytic_group_list'] = data.get('analytic_group_list')
        filters['company_name'] = data.get('company_name')
        filters['target_move'] = filters.get('target_move').capitalize()
        filters['currencies_list'] = data.get('currencies_list')
        # filters['comparison'] = data.get('comparison')
        # filters['previous'] = data.get('previous')
        # filters['currencies'] = data.get('currencies')
        return filters


    @api.model
    def _get_filter_data(self, option, company_id):
        r = self.env['ctm.dynamic.balance.sheet.report'].search([('id', '=', option[0])])
        default_filters = {}
        company_domain = [('company_id', '=', company_id.id)]
        journals = r.journal_ids if r.journal_ids else self.env['account.journal'].search(company_domain)
        analytic_ids = self.analytic_ids if self.analytic_ids else self.env['account.analytic.account'].search(company_domain)
        account_tags = self.account_tag_ids if self.account_tag_ids else self.env['account.account.tag'].search([])
        analytic_tag_ids = self.analytic_tag_ids if self.analytic_tag_ids else self.env['account.analytic.tag'].sudo().search(['|', ('company_id', '=', company_id.id), ('company_id', '=', False)])
        analytic_group_ids = self.analytic_group_ids if self.analytic_group_ids else self.env['account.analytic.group'].sudo().search(['|', ('company_id', '=', company_id.id), ('company_id', '=', False)])
        accounts = self.account_ids if self.account_ids else self.env['account.account'].search(company_domain)
        currencies = r.currency_ids if r.currency_ids else  self.env['res.currency'].search([('active', '=', True)])
        if r.account_tag_ids:
            company_domain.append(('tag_ids', 'in', r.account_tag_ids.ids))

        filter_dict = {
            'journal_ids': r.journal_ids.ids,
            'account_ids': r.account_ids.ids,
            'analytic_ids': r.analytic_ids.ids,
            'company_id': company_id.id,
            'date_from': r.date_from,
            'date_to': r.date_to,
            'target_move': r.target_move,
            'journals_list': [(j.id, j.name, j.code) for j in journals],
            'accounts_list': [(a.id, a.name) for a in accounts],
            'analytic_list': [(anl.id, anl.name) for anl in analytic_ids],
            'company_name': company_id and company_id.name,
            'analytic_tag_ids': r.analytic_tag_ids.ids,
            'analytic_tag_list': [(anltag.id, anltag.name) for anltag in
                                  analytic_tag_ids],
            'analytic_group_ids': r.analytic_group_ids.ids,
            'analytic_group_list': [(anlgroup.id, anlgroup.name) for anlgroup in
                                  analytic_group_ids],
            'account_tag_ids': r.account_tag_ids.ids,
            'account_tag_list': [(a.id, a.name) for a in account_tags],
            'comparison': r.comparison,
            'previous': r.previous,
            'currencies': [{'name': currency_id.name, 'id': currency_id.id,} for currency_id in currencies],
            'consolidate': r.consolidate,
            'entities_comparison': r.entities_comparison,
            'comp_detail': r.comp_detail,
            'filter_budget': r.filter_budget,
            'budget': r.budget,
            'debit_credit': r.debit_credit,
            'all_account': r.all_account,
            'currency_ids': r.currency_ids.ids,
            'currencies_list': [(c.id, c.name, c.symbol) for c in currencies],
        }
        filter_dict.update(default_filters)
        return filter_dict

    @api.model
    def _get_report_values(self, data, company_id):
        docs = data['model']
        display_account = data['display_account']
        init_balance = True
        journals = data['journals']
        list_company=[]
        context = dict(self.env.context)
        if 'consolidate' in data:
            if data['consolidate'] == 'on':
                list_company.append(company_id.id)   
                comp_ids = self.env['account.account.map'].search([('company_id', '=', company_id.id)])
                for comp_id in comp_ids:
                    if comp_id.child_company_id:
                        if comp_id.child_company_id.id in context['allowed_company_ids']:
                            list_company.append(comp_id.child_company_id.id)
            else:
                list_company.append(company_id.id)
        else:
            list_company.append(company_id.id)

        context.update({'allowed_company_ids' : list_company})
        self.env.context = context
        comp = self.env['res.company'].search([('id', 'in', list_company)])
        self.env.companies = comp

        accounts = self.env['account.account'].search([('company_id', 'in', list_company)])
        if not accounts:
            raise UserError(_("No Accounts Found! Please Add One"))
        account_res = self._get_accounts(accounts, init_balance, display_account, data, list_company)

        debit_total = 0
        debit_total = 0
        credit_total = 0
        debit_balance = 0

        total_all = []
        debit_total = sum(x['debit'] for x in account_res)
        credit_total = sum(x['credit'] for x in account_res)
        debit_balance = round(debit_total, 2) - round(credit_total, 2)

        final_account_res = account_res
        if data['budget'] == 'on':
            final_account_res = []
            date_from = fields.Date.from_string(data['date_from'])
            date_to = fields.Date.from_string(data['date_to'])
            if data['budget'] == 'on':
                where = ''
                if data['report_name']:
                    account_plan_id = ''
                    if data['report_name'] == 'Profit and Loss':
                        account_plan_id = 'profit_lose'
                    elif data['report_name'] == 'Balance Sheet':
                        account_plan_id = 'balance_sheet'
                    if account_plan_id:
                        where = where + ' AND ' if where else ''
                        where += "account_plan_id = '%s'" % account_plan_id
                month_range = []
                if date_from and date_to:
                    month_range = self.get_month_list(date_from, date_to)
                    year_list = []
                    for month in month_range:
                        year = month.split('-')[1]
                        year_list.append(year)
                    if year_list:
                        year_list = list(set(year_list))
                        if len(year_list) == 1:
                            where = where + ' AND ' if where else ''
                            where += "year_name = '%s'" % str(year_list[0])
                        elif len(year_list) > 1:
                            where = where + ' AND ' if where else ''
                            where += "year_name in %s" % str(tuple(year_list))
                if where:
                    where = ' WHERE ' + where
                sql = '''SELECT 
                    year_name, account_id, 
                    jan_month, jan_actual, 
                    feb_month, feb_actual, 
                    march_month, march_actual,
                    april_month, april_actual,
                    may_month, may_actual,
                    june_month, june_actual,
                    july_month, july_actual,
                    august_month, august_actual,
                    sep_month, sep_actual,
                    oct_month, oct_actual,
                    nov_month, nov_actual,
                    dec_month, dec_actual
                    FROM monthly_account_budget_lines
                '''
                self.env.cr.execute(sql + where)
                budget_res = self.env.cr.dictfetchall()

                for account_line in account_res:
                    planned_amount = 0.0
                    actual_amount = 0.0
                    if not month_range:
                        planned_list = [
                            'jan_month',
                            'feb_month',
                            'march_month',
                            'april_month',
                            'may_month',
                            'june_month',
                            'july_month',
                            'august_month',
                            'sep_month',
                            'oct_month',
                            'nov_month',
                            'dec_month',
                        ]
                        actual_list = [
                            'jan_actual',
                            'feb_actual',
                            'march_actual',
                            'april_actual',
                            'may_actual',
                            'june_actual',
                            'july_actual',
                            'august_actual',
                            'sep_actual',
                            'oct_actual',
                            'nov_actual',
                            'dec_actual',
                        ]
                        for budget_line in budget_res:
                            for planned_item in planned_list:
                                planned_amount += budget_line.get(planned_item)
                            for actual_item in actual_list:
                                actual_amount += budget_line.get(actual_item)
                    if month_range:
                        for item in month_range:
                            item_split = item.split('-')
                            month_name = item_split[0]
                            year_name = item_split[1]
                            for budget_line in budget_res:
                                if budget_line.get('year_name') == year_name:
                                    if month_name == 'January':
                                        planned_amount += budget_line.get('jan_month')
                                        actual_amount += budget_line.get('jan_actual')
                                    elif month_name == 'February':
                                        planned_amount += budget_line.get('feb_month')
                                        actual_amount += budget_line.get('feb_actual')
                                    elif month_name == 'March':
                                        planned_amount += budget_line.get('march_month')
                                        actual_amount += budget_line.get('march_actual')
                                    elif month_name == 'April':
                                        planned_amount += budget_line.get('april_month')
                                        actual_amount += budget_line.get('april_actual')
                                    elif month_name == 'May':
                                        planned_amount += budget_line.get('may_month')
                                        actual_amount += budget_line.get('may_actual')
                                    elif month_name == 'June':
                                        planned_amount += budget_line.get('june_month')
                                        actual_amount += budget_line.get('june_actual')
                                    elif month_name == 'July':
                                        planned_amount += budget_line.get('july_month')
                                        actual_amount += budget_line.get('july_actual')
                                    elif month_name == 'August':
                                        planned_amount += budget_line.get('august_month')
                                        actual_amount += budget_line.get('august_actual')
                                    elif month_name == 'September':
                                        planned_amount += budget_line.get('sep_month')
                                        actual_amount += budget_line.get('sep_actual')
                                    elif month_name == 'October':
                                        planned_amount += budget_line.get('oct_month')
                                        actual_amount += budget_line.get('oct_actual')
                                    elif month_name == 'November':
                                        planned_amount += budget_line.get('nov_month')
                                        actual_amount += budget_line.get('nov_actual')
                                    elif month_name == 'December':
                                        planned_amount += budget_line.get('dec_month')
                                        actual_amount += budget_line.get('dec_actual')
                    account_line['planned_amount'] = planned_amount
                    account_line['actual_amount'] = actual_amount
                    final_account_res.append(account_line)

        res_result = {
                        'doc_ids': self.ids,
                        'docs': docs,
                        'time': time,
                        'debit_total': debit_total,
                        'credit_total': credit_total,
                        'debit_balance': debit_balance,
                        'Accounts': final_account_res,
                        'total_all': total_all,
                     }            
        return res_result

    @api.model
    def create(self, vals):
        res = super(BalanceSheetView, self).create(vals)
        return res

    
    def write(self, vals):
        if vals.get('target_move'):
            vals.update({'target_move': vals.get('target_move').lower()})
        
        if vals.get('journal_ids'):
            vals.update({'journal_ids': [(6, 0, vals.get('journal_ids'))]})

        if not vals.get('journal_ids'):
            vals.update({'journal_ids': [(5,)]})

        if vals.get('currency_ids'):
            vals.update({'currency_ids': [(6, 0, vals.get('currency_ids'))]})

        if not vals.get('currency_ids'):
            vals.update({'currency_ids': [(5,)]})

        if vals.get('account_ids'):
            vals.update({'account_ids': [(4, j) for j in vals.get('account_ids')]})

        if not vals.get('account_ids'):
            vals.update({'account_ids': [(5,)]})

        if vals.get('analytic_ids'):
            vals.update({'analytic_ids': [(4, j) for j in vals.get('analytic_ids')]})

        if not vals.get('analytic_ids'):
            vals.update({'analytic_ids': [(5,)]})

        if vals.get('account_tag_ids'):
            vals.update({'account_tag_ids': [(4, j) for j in vals.get('account_tag_ids')]})
        
        if not vals.get('account_tag_ids'):
            vals.update({'account_tag_ids': [(5,)]})

        if vals.get('analytic_tag_ids'):
            vals.update({'analytic_tag_ids': [(4, j) for j in vals.get('analytic_tag_ids')]})
        
        if not vals.get('analytic_tag_ids'):
            vals.update({'analytic_tag_ids': [(5,)]})

        if vals.get('analytic_group_ids'):
            vals.update({'analytic_group_ids': [(6, 0, vals.get('analytic_group_ids'))]})
        
        if not vals.get('analytic_group_ids'):
            vals.update({'analytic_group_ids': [(5,)]})

        if vals.get('book'):
            vals.update({'book': vals.get('book').lower()})

        if vals.get('consolidate'):
            vals.update({'consolidate': vals.get('consolidate').lower()})

        if vals.get('entities_comparison'):
            vals.update({'entities_comparison': vals.get('entities_comparison').lower()})

        if vals.get('comp_detail'):
            vals.update({'comp_detail': vals.get('comp_detail').lower()})

        if vals.get('budget'):
            vals.update({'budget': vals.get('budget').lower()})

        if vals.get('debit_credit'):
            vals.update({'debit_credit': vals.get('debit_credit').lower()})

        if vals.get('all_account'):
            vals.update({'all_account': vals.get('all_account').lower()})

        if vals.get('report_currency_id') == False:
            vals.update({'report_currency_id': self.env.company.currency_id.id})

        res = super(BalanceSheetView, self).write(vals)
        return res

    @api.model
    def getQuarterStart(self, tmp_date):
        quarterStart = date(tmp_date.year, (tmp_date.month - 1) // 3 * 3 + 1, 1)
        return quarterStart

    @api.model
    def getQuarterEnd(self, tmp_date):
        quarterStart = self.getQuarterStart(tmp_date)
        quarterEnd = quarterStart + relativedelta(months=3, days=-1)
        return quarterEnd


    def _check_last_period(self, company, date):
        cr = self.env.cr
        sql = ('''SELECT sap.date_end as date_end
                    FROM sh_account_period sap 
                    Where sap.company_id = %s and sap.valid_value = true and sap.date_end < %s and sap.code notnull and sap.fiscal_year_id notnull and (sap.special != true or sap.special isnull)
                    order by sap.date_start desc, sap.code desc 
                    limit 1'''
              )
        params = [str(company), str(date)]
        cr.execute(sql, params)
        period_line = cr.dictfetchall()
        return period_line

    @api.model
    def _get_accounts(self, accounts, init_balance, display_account, data, company_id=False):
        if company_id == False:
            company_id = [self.env.company.id]
        context = dict(self.env.context)
        context.update({'allowed_company_ids' : company_id})
        self.env.context = context
        comp = self.env['res.company'].search([('id', 'in', company_id)])
        self.env.companies = comp
        tmp_result=[]
        for comp in company_id:
            accounts = self.env['account.account'].search([('company_id', '=', comp)])
            cr = self.env.cr
            result_query =[]
            sql = ""
            params = ""
            MoveLine = self.env['account.move.line']
            MoveLine.env.context.update({'date_from':False,
                                         'date_to':False})

            move_lines = {x: [] for x in accounts.ids}

            # Prepare sql query base on selected parameters from wizard
            tables, where_clause, where_params = MoveLine._query_get()
            wheres = [""]

            # Remove branch filter from query
            pattern = r'"account_move_line__move_id"\."branch_id" in \(%s(?:,%s)*\)'
            where_clause = re.sub(pattern, '"account_move_line__move_id"."branch_id" in ()', where_clause)
            substring_to_remove = ' AND ("account_move_line__move_id"."branch_id" IS NULL  OR ("account_move_line__move_id"."branch_id" in ()))'
            where_clause = where_clause.replace(substring_to_remove, '')
            count = where_clause.count('%s')
            where_params = where_params[:count]

            if where_clause.strip():
                wheres.append(where_clause.strip())
            final_filters = " AND ".join(wheres)
            final_filters = final_filters.replace('account_move_line__move_id','m').replace('account_move_line', 'l')
            new_final_filter = final_filters

            if data.get('report_name') == "Balance Sheet":
                last_period = False
                last_period = self._check_last_period(comp, data.get('date_to'))
                # last_period = self.env['sh.account.period'].search([('company_id', '=', comp), ('valid_value', '=', True), ('date_end', '<', data.get('date_to'))])
                if last_period:
                    last_period = last_period[0]
                    last_period = (last_period['date_end'] + timedelta(days=1)).strftime("%Y-%d-%m")
                    data.update({'date_from' : last_period})

            if data['target_move'] == 'posted':
                new_final_filter += " AND m.state = 'posted'"
            else:
                new_final_filter += " AND m.state in ('draft','posted')"

            if data['book'] == 'fiscal':
                new_final_filter += " AND (m.is_fiscal_book_exclude isnull or m.is_fiscal_book_exclude = false)"\

            # if data['report_name'] == "Balance Sheet":
            #     if data['comp_detail'] == 'today':
            #         new_final_filter += " AND l.date <= '%s'" % data.get('date_to')
            #     else:
            #         if data.get('date_to'):
            #             new_final_filter += " AND l.date <= '%s'" % data.get('date_to')
            # else:
            #     if data.get('date_from'):
            #         new_final_filter += " AND l.date >= '%s'" % data.get('date_from')
            #     if data.get('date_to'):
            #         new_final_filter += " AND l.date <= '%s'" % data.get('date_to')

            if data.get('date_from'):
                new_final_filter += " AND l.date >= '%s'" % data.get('date_from')
            if data.get('date_to'):
                new_final_filter += " AND l.date <= '%s'" % data.get('date_to')


            if 'consolidate' in data:
                if data['consolidate'] != 'on':
                    if data.get('accounts'):
                        WHERE = "WHERE l.account_id IN %s" % str(
                            tuple(data.get('accounts').ids) + tuple([0]))
                    else:
                        WHERE = "WHERE l.account_id IN %s"

                    if data['journals']:
                        new_final_filter += ' AND j.id IN %s' % str(
                            tuple(data['journals'].ids) + tuple([0]))

                    if data['analytic_ids']:
                        WHERE += ' AND anlacc.id IN %s' % str(
                            tuple(data.get('analytic_ids').ids) + tuple([0]))

                    if data['analytic_tag_ids']:
                        WHERE += ' AND anltagrel.account_analytic_tag_id IN %s' % str(
                            tuple(data.get('analytic_tag_ids').ids) + tuple([0]))

                    # if data['analytic_group_ids']:
                    #     WHERE += ' AND anlgroup.id IN %s' % str(
                    #         tuple(data.get('analytic_group_ids').ids) + tuple([0]))

                    if data['analytic_ids'] or data['analytic_tag_ids'] or data['analytic_group_ids']:
                        sql = ('''SELECT l.id AS lid,m.id AS move_id, l.account_id AS account_id,
                                l.date AS ldate, j.code AS lcode, l.currency_id, l.amount_currency, l.ref AS lref,
                                l.name AS lname, 
                                COALESCE(SUM((anldis.percentage/100) * l.debit),0) AS debit, 
                                COALESCE(SUM((anldis.percentage/100) * l.credit),0) AS credit, 
                                (COALESCE(SUM((anldis.percentage/100) * l.debit),0) - COALESCE(SUM((anldis.percentage/100) * l.credit),0)) AS balance, 
                                m.name AS move_name, c.symbol AS currency_code,c.position AS currency_position, p.name AS partner_name
                                FROM account_move_line l
                                JOIN account_move m ON (l.move_id=m.id)
                                LEFT JOIN res_currency c ON (l.currency_id=c.id)
                                LEFT JOIN res_partner p ON (l.partner_id=p.id)
                                JOIN account_analytic_tag_account_move_line_rel as anltagrel ON (anltagrel.account_move_line_id = l.id) 
                                JOIN account_analytic_tag as anltag ON (anltagrel.account_analytic_tag_id = anltag.id) 
                                JOIN account_analytic_distribution as anldis ON (anltag.id = anldis.tag_id) 
                                JOIN account_analytic_group as anlgroup ON (anldis.analytic_group_id = anlgroup.id) 
                                JOIN account_analytic_account as anlacc ON  (anldis.account_id = anlacc.id) 
                                JOIN account_journal j ON (m.journal_id=j.id)
                                JOIN account_account acc ON (l.account_id = acc.id)
                                ''' + WHERE + '''
                                ''' + new_final_filter + '''
                                GROUP BY l.id, m.id,  l.account_id, l.date, j.code, l.currency_id, l.amount_currency, l.ref, l.name, m.name, c.symbol, c.position, p.name''')
                    else:
                        sql = ('''SELECT l.id AS lid,m.id AS move_id, l.account_id AS account_id,
                                  l.date AS ldate, j.code AS lcode, l.currency_id, l.amount_currency, l.ref AS lref,
                                  l.name AS lname, 
                                  COALESCE(SUM(l.debit),0) AS debit, 
                                  COALESCE(SUM(l.credit),0) AS credit, 
                                  (COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit),0)) AS balance, 
                                  m.name AS move_name, c.symbol AS currency_code,c.position AS currency_position, p.name AS partner_name
                                  FROM account_move_line l
                                  JOIN account_move m ON (l.move_id=m.id)
                                  LEFT JOIN res_currency c ON (l.currency_id=c.id)
                                  LEFT JOIN res_partner p ON (l.partner_id=p.id)
                                  JOIN account_journal j ON (m.journal_id=j.id)
                                  JOIN account_account acc ON (l.account_id = acc.id)
                                  ''' + WHERE + '''
                                  ''' + new_final_filter + '''
                                  GROUP BY l.id, m.id,  l.account_id, l.date, j.code, l.currency_id, l.amount_currency, l.ref, l.name, m.name, c.symbol, c.position, p.name''')
                    
                    if data.get('accounts'):
                        params = tuple(where_params)
                    else:
                        params = (tuple(accounts.ids),) + tuple(where_params)
                    
                else:
                    new_final_filter += " AND (m.is_intercompany_transaction = 'false') "
                    WHERE = "WHERE l.account_id IN %s"

                    sql = ('''SELECT l.id AS lid,m.id AS move_id, l.account_id AS account_id,
                            l.date AS ldate, j.code AS lcode, l.currency_id, l.amount_currency, l.ref AS lref,
                            l.name AS lname, 
                            COALESCE(SUM(l.debit),0) AS debit, 
                            COALESCE(SUM(l.credit),0) AS credit, 
                            (COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit),0)) AS balance, 
                            m.name AS move_name, c.symbol AS currency_code,c.position AS currency_position, p.name AS partner_name
                            FROM account_move_line l
                            JOIN account_move m ON (l.move_id=m.id)
                            LEFT JOIN res_currency c ON (l.currency_id=c.id)
                            LEFT JOIN res_partner p ON (l.partner_id=p.id)
                            JOIN account_journal j ON (m.journal_id=j.id)
                            JOIN account_account acc ON (l.account_id = acc.id)
                            ''' + WHERE + '''
                            ''' + new_final_filter + '''
                            GROUP BY l.id, m.id,  l.account_id, l.date, j.code, l.currency_id, l.amount_currency, l.ref, l.name, m.name, c.symbol, c.position, p.name''')
                    
                    params = (tuple(accounts.ids),) + tuple(where_params)
                    
            else:
                if data['journals']:
                    new_final_filter += ' AND j.id IN %s' % str(
                        tuple(data['journals'].ids) + tuple([0]))

                if data['analytic_ids']:
                    WHERE += ' AND anlacc.id IN %s' % str(
                        tuple(data.get('analytic_ids').ids) + tuple([0]))

                if data['analytic_tag_ids']:
                    WHERE += ' AND anltag.account_analytic_tag_id IN %s' % str(
                        tuple(data.get('analytic_tag_ids').ids) + tuple([0]))

                # if data['analytic_group_ids']:
                #     WHERE += ' AND anlgroup.id IN %s' % str(
                #         tuple(data.get('analytic_group_ids').ids) + tuple([0]))

                # Get move lines base on sql query and Calculate the total balance of move lines
                if data['analytic_ids'] or data['analytic_tag_ids'] or data['analytic_group_ids']:
                    sql = ('''SELECT l.id AS lid,m.id AS move_id, l.account_id AS account_id,
                            l.date AS ldate, j.code AS lcode, l.currency_id, l.amount_currency, l.ref AS lref,
                            l.name AS lname, 
                            COALESCE(SUM((anldis.percentage/100) * l.debit),0) AS debit, 
                            COALESCE(SUM((anldis.percentage/100) * l.credit),0) AS credit, 
                            (COALESCE(SUM((anldis.percentage/100) * l.debit),0) - COALESCE(SUM((anldis.percentage/100) * l.credit),0)) AS balance, 
                            m.name AS move_name, c.symbol AS currency_code,c.position AS currency_position, p.name AS partner_name
                            FROM account_move_line l
                            JOIN account_move m ON (l.move_id=m.id)
                            LEFT JOIN res_currency c ON (l.currency_id=c.id)
                            LEFT JOIN res_partner p ON (l.partner_id=p.id)
                            JOIN account_analytic_tag_account_move_line_rel as anltagrel ON (anltagrel.account_move_line_id = l.id) 
                            JOIN account_analytic_tag as anltag ON (anltagrel.account_analytic_tag_id = anltag.id) 
                            JOIN account_analytic_distribution as anldis ON (anltag.id = anldis.tag_id) 
                            JOIN account_analytic_group as anlgroup ON (anldis.analytic_group_id = anlgroup.id) 
                            JOIN account_analytic_account as anlacc ON  (anldis.account_id = anlacc.id) 
                            JOIN account_journal j ON (m.journal_id=j.id)
                            JOIN account_account acc ON (l.account_id = acc.id)
                            ''' + WHERE + '''
                            ''' + new_final_filter + '''
                            GROUP BY l.id, m.id,  l.account_id, l.date, j.code, l.currency_id, l.amount_currency, l.ref, l.name, m.name, c.symbol, c.position, p.name''')
                else:
                    sql = ('''SELECT l.id AS lid,m.id AS move_id, l.account_id AS account_id,
                              l.date AS ldate, j.code AS lcode, l.currency_id, l.amount_currency, l.ref AS lref,
                              l.name AS lname, 
                              COALESCE(SUM(l.debit),0) AS debit, 
                              COALESCE(SUM(l.credit),0) AS credit, 
                              (COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit),0)) AS balance, 
                              m.name AS move_name, c.symbol AS currency_code,c.position AS currency_position, p.name AS partner_name
                              FROM account_move_line l
                              JOIN account_move m ON (l.move_id=m.id)
                              LEFT JOIN res_currency c ON (l.currency_id=c.id)
                              LEFT JOIN res_partner p ON (l.partner_id=p.id)
                              JOIN account_journal j ON (m.journal_id=j.id)
                              JOIN account_account acc ON (l.account_id = acc.id)
                              ''' + WHERE + '''
                              ''' + new_final_filter + '''
                              GROUP BY l.id, m.id,  l.account_id, l.date, j.code, l.currency_id, l.amount_currency, l.ref, l.name, m.name, c.symbol, c.position, p.name''')

                if data.get('accounts'):
                    params = tuple(where_params)
                else:
                    params = (tuple(accounts.ids),) + tuple(where_params)

            cr.execute(sql, params)
            result_query = cr.dictfetchall()
            category_res = []
            move_cat=[]

            if data['report_name'] == "Balance Sheet":
                if data.get('date_from'):
                    filter_fs = ""
                    filter_fs += " AND sap.valid_value = true AND sap.date_end < '%s' " % data.get('date_from')
                    filter_fs += " AND ibl.report_name = '%s' " % data.get('report_name')
                    sql_move_lines = '''SELECT     
                                            tb.m_id as m_id,
                                            COALESCE(SUM(tb.debit),0) AS debit, 
                                            COALESCE(SUM(tb.credit),0) AS credit, 
                                            COALESCE(SUM(tb.balance),0) AS balance 
                                        from
                                            (
                                                (
                                                    SELECT 
                                                        tb.account_id as m_id, 
                                                        COALESCE(SUM(tb.debit),0) AS debit, 
                                                        COALESCE(SUM(tb.credit),0) AS credit, 
                                                        (COALESCE(SUM(tb.debit),0) - COALESCE(SUM(tb.credit),0)) AS balance 
                                                    from 
                                                        (''' + sql + ''') as tb 
                                                    where 
                                                        tb.account_id in %s 
                                                    GROUP BY tb.account_id 
                                                )
                                                UNION
                                                (
                                                    SELECT 
                                                        ibl.account_id as m_id,
                                                        ibl.debit_amount as debit,
                                                        ibl.credit_amount as credit,
                                                        ibl.balance_amount as balance
                                                    FROM sh_fiscal_year sfy 
                                                    inner join sh_account_period sap on sfy.id = sap.fiscal_year_id
                                                    inner join initial_balance_line ibl on sap.id = ibl.period_id
                                                    WHERE sfy.company_id = ''' +str(comp)+ ''' AND (ibl.debit_amount != 0 or ibl.credit_amount != 0 or ibl.balance_amount != 0) 
                                                    ''' + filter_fs + ''' 
                                                    order by sap.date_start asc
                                                )
                                            ) as tb
                                        GROUP BY tb.m_id '''
                    # param_fs = (comp, data['date_from'], data['report_name'])
                    params_move_lines = params + (tuple(move_lines),)
                else:
                    sql_move_lines = '''SELECT 
                                            tb.account_id as m_id, 
                                            COALESCE(SUM(tb.debit),0) AS debit, 
                                            COALESCE(SUM(tb.credit),0) AS credit, 
                                            (COALESCE(SUM(tb.debit),0) - COALESCE(SUM(tb.credit),0)) AS balance 
                                        from 
                                            (''' + sql + ''') as tb 
                                        where 
                                            tb.account_id in %s 
                                        GROUP BY tb.account_id '''
                    params_move_lines = params + (tuple(move_lines),)
            else:
                sql_move_lines = '''SELECT 
                                        tb.account_id as m_id, 
                                        COALESCE(SUM(tb.debit),0) AS debit, 
                                        COALESCE(SUM(tb.credit),0) AS credit, 
                                        (COALESCE(SUM(tb.debit),0) - COALESCE(SUM(tb.credit),0)) AS balance 
                                    from 
                                        (''' + sql + ''') as tb 
                                    where 
                                        tb.account_id in %s 
                                    GROUP BY tb.account_id '''
                params_move_lines = params + (tuple(move_lines),)
            cr.execute(sql_move_lines, params_move_lines)
            new_move_lines = cr.dictfetchall()

                
            # sql_move_lines = (''' SELECT tb.account_id as m_id,
            #                  COALESCE(SUM(tb.debit),0) AS debit, 
            #                  COALESCE(SUM(tb.credit),0) AS credit, 
            #                  (COALESCE(SUM(tb.debit),0) - COALESCE(SUM(tb.credit),0)) AS balance
            #                  from (''' + sql + ''') as tb where tb.account_id in %s 
            #                  GROUP BY tb.account_id ''')
            # params_move_lines = params + (tuple(move_lines),)
            # cr.execute(sql_move_lines, params_move_lines)
            # new_move_lines = cr.dictfetchall()

            for row in result_query:
                balance = 0
                move_line_value = list(filter(lambda x: x['m_id'] == row['account_id'], new_move_lines))
                row['debit'] = (round(move_line_value[0]['debit'], 2)) if move_line_value else 0
                row['credit'] = (round(move_line_value[0]['credit'], 2)) if move_line_value else 0
                row['balance'] = (round(move_line_value[0]['balance'], 2)) if move_line_value else 0
                row['m_id'] = row['account_id']
                move_lines[row.pop('account_id')].append(row)
            # Calculate the debit, credit and balance for Accounts
            account_res = []
            for account in accounts:
                currency = account.currency_id and account.currency_id or account.company_id.currency_id
                res = dict((fn, 0.0) for fn in ['debit', 'credit', 'balance'])
                res['company_id'] = comp
                res['code'] = account.code
                res['name'] = account.name
                res['id'] = account.id
                res['move_lines'] = move_lines[account.id]
                move_line_value = list(filter(lambda x: x['m_id'] == account.id, new_move_lines))
                if move_line_value :
                    res['debit'] = (round(move_line_value[0]['debit'], 2))
                    res['credit'] = (round(move_line_value[0]['credit'], 2))
                    res['balance'] = (round(move_line_value[0]['balance'], 2))
                else:
                    res['debit'] = 0
                    res['credit'] = 0
                    res['balance'] = 0
                    res['amount_currency'] = 0
                if data['all_account'] == 'on':
                    account_res.append(res)
                else:
                    if display_account == 'all':
                        account_res.append(res)
                    if display_account == 'movement' and res.get('move_lines'):
                        account_res.append(res)
                    if display_account == 'not_zero' and not currency.is_zero(res['balance']):
                        account_res.append(res)
            comp_ids = self.env['account.account.map'].search([('child_company_id', '=', comp)])
            if comp_ids:
                for comp_id in comp_ids:
                    if self.env.company.id == comp_id.company_id.id:
                        child_line = comp_id.line_ids
                        for acc_res in account_res:
                            parent = list(filter(lambda x: x['target_account'].code == acc_res['code'], child_line))
                            if parent:
                                if parent[0].account_id:
                                    acc_res['code'] = parent[0].account_id.code
                                    acc_res['name'] = parent[0].account_id.name
                                    acc_res["debit"] = acc_res["debit"] * (comp_id.ownership / 100)
                                    acc_res["credit"] = acc_res["credit"] * (comp_id.ownership / 100)
                                    acc_res["balance"] = acc_res["balance"] * (comp_id.ownership / 100)
                                    if 'move_lines' in acc_res:
                                        for mv in acc_res['move_lines']:
                                            mv['amount_currency'] = mv['amount_currency'] * (comp_id.ownership / 100)
                                            mv['debit'] = mv['debit'] * (comp_id.ownership / 100)
                                            mv['credit'] = mv['credit'] * (comp_id.ownership / 100)
                                            mv['balance'] = mv['balance'] * (comp_id.ownership / 100)
            tmp_result.append(account_res)
        result = tmp_result[0]
        if len(tmp_result) > 1:
            i = 1
            while i < len(tmp_result):
                for tmp_res in tmp_result[i]:
                    list_code_acc = list(filter(lambda x: x['code'] == tmp_res['code'], result))
                    if list_code_acc:
                        for code_acc in list_code_acc:
                            code_acc['debit'] += tmp_res['debit']
                            code_acc['credit'] += tmp_res['credit']
                            code_acc['balance'] += tmp_res['balance']
                            if "new_code" not in code_acc:
                                code_acc['new_code'] = False
                            if 'move_lines' in code_acc:
                                if 'move_lines' in tmp_res:
                                    for mv in tmp_res['move_lines']:
                                        (code_acc['move_lines']).append(mv)
                    else:
                        tmp_res['new_code'] = True
                        result.append(tmp_res)
                i += 1
        return result

    @api.model
    def _get_currency(self):
        partner_ledger = self.search([], limit=1, order="id desc")
        report_currency_id = partner_ledger.report_currency_id
        journal = self.env['account.journal'].browse(self.env.context.get('default_journal_id', False))
        
        if journal.currency_id and not report_currency_id:
            return journal.currency_id.id
        
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

    def get_space(self,level):
        space_level = ''
        for x in range(0,level):
            space_level += '    '
        return space_level

    def get_dynamic_xlsx_report(self, options, response, report_data, dfr_data):
        i_data = str(report_data)
        filters = json.loads(options)
        j_data = dfr_data
        rl_data = json.loads(j_data)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        head1 = workbook.add_format({'bold': True})
        head2 = workbook.add_format({'bold': True})
        filtermove = workbook.add_format({'bold': True})
        sub_heading = workbook.add_format({'bold': True, 'border': 1, 'border_color': 'black'})
        side_heading_main = workbook.add_format({'bold': True, 'border': 1, 'border_color': 'black'})
        side_heading_main2 = workbook.add_format({'border': 1, 'border_color': 'black'})

        side_heading_sub = workbook.add_format({'bold': True, 'border': 1, 'border_color': 'black'})
        side_heading_sub2 = workbook.add_format({'border': 1, 'border_color': 'black'})

        side_heading_sub.set_indent(1)
        txt = workbook.add_format({})
        txt_name = workbook.add_format({})
        txt_name_bold = workbook.add_format({'bold': True})
        txt_name.set_indent(2)
        txt_name_bold.set_indent(2)

        txt = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        txt2 = workbook.add_format({'border': 1, 'num_format': '#,##0.00', 'bold': True})
        borderall = workbook.add_format({'border': 1})
        
        sheet.write(1, 0, filters.get('company_name'), head1)
        sheet.write(2, 0, i_data, head2)
        sheet.write(6, 0, "Accrual Basis : " + filters.get('target_move').capitalize() + " Entry", filtermove)

        date_head = workbook.add_format({'bold': True})

        date_head.set_align('vcenter')
        date_head.set_text_wrap()
        date_head.set_shrink()
        date_head_left = workbook.add_format({'bold': True})

        date_head_right = workbook.add_format({'bold': True})

        date_head_left.set_indent(1)
        date_head_right.set_indent(1)

        sheet.set_column('A:A', 100, '')
        sheet.set_column('B:Z', 30, '')
        
        # currency = rl_data['currency_id']
        # curr = self.env['res.currency'].search([('id','=',currency)])
        # position = curr.position
        # symbol = curr.symbol
        row = 5
        row += 2
        # sheet.write(row, 0, '', sub_heading)
        # sheet.write(row, 0, 'Code/Account', sub_heading)

        tmp_col = 1 + len(rl_data['years_preview'])                
        if filters['debit_credit'] == 'on':
            tmp_col = 1 + (len(rl_data['years_preview']) * 3)
        
        if filters['budget'] == 'on':
            tmp_col = 1 + (len(rl_data['years_preview']) * 2)

        tmp_comp_list = rl_data['comps_list']
        tmp_col_total = tmp_col * len(tmp_comp_list)
        add_row = False
        col = 0
        
        if filters['entities_comparison'] == 'on':
            for cur in rl_data['curr_list']:
                add_col = 0
                for comp_name in rl_data['comp_names']:
                    add_col+=(tmp_col -1)
                    sheet.merge_range(row, col+1, row, col+add_col, comp_name + " (" + str(cur) + ")", sub_heading)
            row+=1
            for cur in rl_data['curr_list']:
                for comp_name in rl_data['comp_names']:
                    for preview in rl_data['years_preview']:
                        if filters['budget'] == 'on':
                            sheet.merge_range(row, col+1, row, col+2, preview + " (" + str(cur) + ")", sub_heading)
                            sheet.write(row+1, col+1, 'Planned Amount', sub_heading)
                            sheet.write(row+1, col+2, 'Actual Amount', sub_heading)
                            add_row = True
                            col+=2
                        elif filters['debit_credit'] == 'on':
                            sheet.merge_range(row, col+1, row, col+3, preview + " (" + str(cur) + ")", sub_heading)
                            sheet.write(row+1, col+1, 'debit', sub_heading)
                            sheet.write(row+1, col+2, 'credit', sub_heading)
                            sheet.write(row+1, col+3, 'balance', sub_heading)
                            add_row = True
                            col+=3
                        else:
                            sheet.write(row, col+1, preview + " (" + str(cur) + ")", sub_heading)
                            add_row = False
                            col+=1
        else:
            for cur in rl_data['curr_list']:
                for comp_name in rl_data['comp_names']:
                    for preview in rl_data['years_preview']:
                        if filters['budget'] == 'on':
                            sheet.merge_range(row, col+1, row, col+2, preview + " (" + str(cur) + ")", sub_heading)
                            sheet.write(row+1, col+1, 'Planned Amount', sub_heading)
                            sheet.write(row+1, col+2, 'Actual Amount', sub_heading)
                            add_row = True
                            col+=2
                        elif filters['debit_credit'] == 'on':
                            sheet.merge_range(row, col+1, row, col+3, preview + " (" + str(cur) + ")", sub_heading)
                            sheet.write(row+1, col+1, 'debit', sub_heading)
                            sheet.write(row+1, col+2, 'credit', sub_heading)
                            sheet.write(row+1, col+3, 'balance', sub_heading)
                            add_row = True
                            col+=3
                        else:
                            sheet.write(row, col+1, preview + " (" + str(cur) + ")", sub_heading)
                            add_row = False
                            col+=1

        if add_row == True:
            row+=1
        sheet.write(row, 0, '', sub_heading)
        sheet.write(row, 0, 'Code/Account', sub_heading)
        if rl_data['bs_lines']:
            for a in rl_data['bs_lines']:
                row += 1
                if 'code' in a:
                    if a['level'] == 2 or 'is_parent' in a or 'total_value' in a:
                        sheet.write(row, 0, self.get_space(a['level']) + a['code'] + ' - ' + a['name'], side_heading_sub)
                    else:
                        sheet.write(row, 0, self.get_space(a['level']) + a['code'] + ' - ' + a['name'], side_heading_sub2)
                else:
                    if a['level'] == 2 or 'is_parent' in a or 'total_value' in a:
                        sheet.write(row, 0, self.get_space(a['level']) + a['name'], side_heading_main)
                    else:
                        sheet.write(row, 0, self.get_space(a['level']) + a['name'], side_heading_main2)
                col = 0
                for cur in rl_data['curr_list']:
                    cur_id = self.env['res.currency'].search([('name','=',cur)])
                    position = cur_id.position
                    symbol = cur_id.symbol
                    for comp_list in rl_data['comps_list']:
                        if len((a['rprt_lines'])[cur]) == 0:
                            for comp_name in rl_data['comp_names']:
                                for preview in rl_data['years_preview']:
                                    if filters['budget'] == 'on':
                                        sheet.write(row, col+1, '', txt)
                                        sheet.write(row, col+2, '', txt)
                                        col+=2
                                    elif filters['debit_credit'] == 'on':
                                        sheet.write(row, col+1, '', txt)
                                        sheet.write(row, col+2, '', txt)
                                        sheet.write(row, col+3, '', txt)
                                        col+=3
                                    else:
                                        sheet.write(row, col+1, '', txt)
                                        col+=1
                                if len(rl_data['years_preview']) == 2:
                                    sheet.write(row, col+1, '%', txt)
                                    col+=1
                        else:
                            for rprt_lines in (a['rprt_lines'])[cur]:
                                if str(comp_list) in rprt_lines:
                                    for preview in rl_data['years_preview']:
                                        if preview in rprt_lines[str(comp_list)]:
                                            if filters['budget'] == 'on':
                                                planned_amount = ((rprt_lines[str(comp_list)])[preview])['planned_amount']
                                                actual_amount = ((rprt_lines[str(comp_list)])[preview])['actual_amount']
                                                planned_amount = re.sub('['+symbol+']|\s*', '', planned_amount)
                                                actual_amount = re.sub('['+symbol+']|\s*', '', actual_amount)
                                                separate = planned_amount[-3]
                                                if separate == '.':
                                                    planned_amount = re.sub(',|\s*', '', planned_amount)
                                                    actual_amount = re.sub(',|\s*', '', actual_amount)
                                                elif separate == ',':
                                                    planned_amount = re.sub('.|\s*', '', planned_amount)
                                                    actual_amount = re.sub('.|\s*', '', actual_amount)

                                                sheet.write(row, col+1, float(planned_amount),  txt2 if 'total_value' in a else txt)
                                                sheet.write(row, col+2, float(actual_amount),  txt2 if 'total_value' in a else txt)
                                                col+=2
                                            elif filters['debit_credit'] == 'on':
                                                debit = ((rprt_lines[str(comp_list)])[preview])['debit']
                                                credit = ((rprt_lines[str(comp_list)])[preview])['credit']
                                                balance = ((rprt_lines[str(comp_list)])[preview])[preview]
                                                debit = re.sub('['+symbol+']|\s*', '', debit)
                                                credit = re.sub('['+symbol+']|\s*', '', credit)
                                                balance = re.sub('['+symbol+']|\s*', '', balance)

                                                separate = balance[-3]
                                                if separate == '.':
                                                    balance = re.sub(',|\s*', '', balance)
                                                    debit = re.sub(',|\s*', '', debit)
                                                    credit = re.sub(',|\s*', '', credit)
                                                elif separate == ',':
                                                    balance = re.sub('.|\s*', '', balance)
                                                    debit = re.sub('.|\s*', '', debit)
                                                    credit = re.sub('.|\s*', '', credit)

                                                sheet.write(row, col+1, float(debit), txt2 if 'total_value' in a else txt)
                                                sheet.write(row, col+2, float(credit), txt2 if 'total_value' in a else txt)
                                                sheet.write(row, col+3, float(balance), txt2 if 'total_value' in a else txt)
                                                col+=3
                                            else:
                                                balance = ((rprt_lines[str(comp_list)])[preview])[preview]
                                                balance = re.sub('['+symbol+']|\s*', '', balance)
                                                separate = balance[-3]
                                                if separate == '.':
                                                    balance = re.sub(',|\s*', '', balance)
                                                elif separate == ',':
                                                    balance = re.sub('.|\s*', '', balance)
                                                
                                                if 'is_parent' in a:
                                                    sheet.write(row, col+1, float(balance), txt2)
                                                else:
                                                    sheet.write(row, col+1, float(balance), txt2 if 'total_value' in a else txt)
                                                col+=1
                                    if len(rl_data['years_preview']) == 2:
                                        sheet.write(row, col+1, rprt_lines['comparison_percentage'], txt)
                                        col+=1
                                    
                if a['level'] in [1,2] and 'total_value' in a:
                    row += 1
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()