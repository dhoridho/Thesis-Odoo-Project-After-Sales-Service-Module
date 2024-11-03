from odoo import fields, models, api, _
from odoo.exceptions import AccessError, UserError, AccessDenied
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.tools.misc import formatLang, format_date
from odoo.tools import config, date_utils, get_lang
from babel.dates import get_quarter_names
import time, io, json, calendar, datetime

FETCH_RANGE = 2000
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class AccountCasgFlow(models.TransientModel):
    _name = "account.cash.flow.statement"
    _inherit = "account.common.report"

    date_from = fields.Date(string="Start Date", default=date.today().replace(day=1))
    date_to = fields.Date(string="End Date", default=fields.Date.today)
    today = fields.Date("Report Date", default=fields.Date.today)
    levels = fields.Selection([('summary', 'Summary'),
                               ('consolidated', 'Consolidated'),
                               ('detailed', 'Detailed'),
                               ('very', 'Very Detailed')],
                              string='Levels', required=True, default='summary',
                              help='Different levels for cash flow statements \n'
                                   'Summary: Month wise report.\n'
                                   'Consolidated: Based on account types.\n'
                                   'Detailed: Based on accounts.\n'
                                   'Very Detailed: Accounts with their move lines')

    account_ids = fields.Many2many("account.account",string="Accounts",)
    company_ids = fields.Many2many("res.company",string="Companies")
    comparison = fields.Integer(string="Comparison")
    previous = fields.Boolean(string="Previous", default=False)
    comp_detail = fields.Selection(
        [('no', 'No'),
         ('today', 'Today'), 
         ('month', 'This Month'),
         ('quarter', 'This Quarter'),
         ('year', 'This Year'),
         ('lastmonth', 'Last Month'),
         ('lastquarter', 'Last Quarter'),
         ('lastyear', 'Last Year'),
         ('custom', 'Custom')],
        string='Comparison Detail', required=True, default='no')

    type_report = fields.Selection(
        [('indirect', 'Cash Flow Report (Indirect)'), ('direct', 'Cash Flow Report (Direct)')],
        string='Type Report', required=True, default='direct')


    @api.model
    def view_report(self, option):
        r = self.env['account.cash.flow.statement'].search([('id', '=', option[0])])

        data = {
            'model': self,
            'journals': r.journal_ids,
            'target_move': r.target_move,
            'levels': r.levels,
            'company_ids': r.company_ids,
            'comparison': r.comparison,
            'previous': r.previous,
            'comp_detail': r.comp_detail,
            'type_report': r.type_report,
        }

        if r.date_from:
            data.update({'date_from': r.date_from})
        else:
            data.update({'date_from': date.today().replace(day=1)})

        if r.date_to:
            data.update({'date_to': r.date_to})
        else:
            data.update({'date_to': date.today() + relativedelta(day=31)})

        filters = self.get_filter(option)
        report_lines = self._get_report_values(data, option)

        fetched_data = report_lines['fetched_data']
        fetched = report_lines['fetched']
        account_res = report_lines['account_res']
        journal_res = report_lines['journal_res']
        levels = report_lines['levels']
        currency = self._get_currency()

        received_customer = []
        cash_received = []
        payment_supplier = []
        cash_paid = []

        cf_operating_cashin_indirect = []
        cf_operating_cashout_indirect = []
        cf_operating_addition = []
        cf_operating_deduction = []
        net_income = []

        if r.type_report == 'indirect':
            cf_operating_cashin_indirect = self._sum_list(report_lines['cf_operating_cashin_indirect'], 'Cash in')
            cf_operating_cashout_indirect = self._sum_list(report_lines['cf_operating_cashout_indirect'], 'Cash out')
            cf_operating_addition = self._sum_list(report_lines['cf_operating_addition'], 'Addition')
            cf_operating_deduction = self._sum_list(report_lines['cf_operating_deduction'], 'Deduction')
            net_income = self._sum_list(report_lines['net_income'], 'Net Income')
            
            sum_cf_statement = self._sum_list(cf_operating_cashin_indirect + cf_operating_cashout_indirect + cf_operating_addition + cf_operating_deduction + net_income, 'Total cash flow from operating activities')
        else:
            received_customer = self._sum_list(report_lines['received_customer'],'Advance payments received from customers')
            cash_received = self._sum_list(report_lines['cash_received'],'Cash received from')
            payment_supplier = self._sum_list(report_lines['payment_supplier'],'Advance payments made to suppliers')
            cash_paid = self._sum_list(report_lines['cash_paid'],'Cash paid for')

            sum_cf_statement = self._sum_list(received_customer + cash_received + payment_supplier + cash_paid,'Total cash flow from operating activities')
        
        cf_investing = self._sum_list(report_lines['cf_investing'], "cf_investing")
        cf_finance = self._sum_list(report_lines['cf_finance'], "cf_finance")
        cf_unclass = self._sum_list(report_lines['cf_unclass'], "cf_unclass")
        sum_all_cf_statement = self._sum_list(sum_cf_statement + cf_investing + cf_finance + cf_unclass,'Net increase in cash and cash equivalents')
        cf_beginning_period = self._sum_list(report_lines['cf_beginning_period'], "Cash and cash equivalents, beginning of period")
        cf_closing_period = self._sum_list(sum_all_cf_statement + cf_beginning_period,'Cash and cash equivalents, closing of period')

        list_previews = []
        list_report_lines = []

        list_received_customer = {}
        list_cash_received = {}
        list_payment_supplier = {}
        list_cash_paid = {}
        list_sum_cf_statement = {}

        list_cf_operating_cashin_indirect = {}
        list_cf_operating_cashout_indirect = {}
        list_cf_operating_addition = {}
        list_cf_operating_deduction = {}
        list_net_income = {}

        list_cf_investing = {}
        list_cf_finance = {}
        list_cf_unclass = {}
        list_sum_all_cf_statement = {}
        list_cf_beginning_period = {}
        list_cf_closing_period = {}
        tmp_received_customer = {}
        
        numb_comp = data['comparison'] + 1
        for numb_comp in range(0,data['comparison'] + 1):
            if numb_comp > 0:
                if data.get('previous'):
                    get_filter_date = self._get_dates_previous_period(data, data.get('comp_detail'))
                else:
                    get_filter_date = self._get_dates_previous_year(data, data.get('comp_detail'))

                data.update({
                            'date_from': fields.Date.from_string(get_filter_date['date_from']),
                            'date_to': fields.Date.from_string(get_filter_date['date_to']),
                            })
                filters.update({
                                'date_from': fields.Date.from_string(get_filter_date['date_from']),
                                'date_to': fields.Date.from_string(get_filter_date['date_to']),
                            })
            else:
                get_filter_date = self._init_filter_date(data, data.get('comp_detail'))
                data.update({
                            'date_from': fields.Date.from_string(get_filter_date['date_from']),
                            'date_to': fields.Date.from_string(get_filter_date['date_to']),
                            })
                filters.update({
                                'date_from': fields.Date.from_string(get_filter_date['date_from']),
                                'date_to': fields.Date.from_string(get_filter_date['date_to']),
                            })
            list_previews += [get_filter_date['string']]

            tmp_report_lines = self._get_report_values(data, option)
            tmp_report_lines['name_filter_date'] = get_filter_date['string']
            list_report_lines.append(tmp_report_lines)

            if r.type_report == 'indirect':
                tmp_cf_operating_cashin_indirect = self._sum_list(tmp_report_lines['cf_operating_cashin_indirect'], "cf_operating_cashin_indirect")
                tmp_cf_operating_cashin_indirect_account = self.sum_tmp_account([tmp_report_lines['cf_operating_cashin_indirect_account']])
                list_cf_operating_cashin_indirect.update({get_filter_date['string'] : {"report_name" : get_filter_date['string'], 'report_lines' : tmp_cf_operating_cashin_indirect, 'report_lines_account' : tmp_cf_operating_cashin_indirect_account}})

                tmp_cf_operating_cashout_indirect = self._sum_list(tmp_report_lines['cf_operating_cashout_indirect'], "cf_operating_cashout_indirect")
                tmp_cf_operating_cashout_indirect_account = self.sum_tmp_account([tmp_report_lines['cf_operating_cashout_indirect_account']])
                list_cf_operating_cashout_indirect.update({get_filter_date['string'] : {"report_name" : get_filter_date['string'], 'report_lines' : tmp_cf_operating_cashout_indirect, 'report_lines_account' : tmp_cf_operating_cashout_indirect_account}})
                
                tmp_cf_operating_addition = self._sum_list(tmp_report_lines['cf_operating_addition'], "cf_operating_addition")
                tmp_cf_operating_addition_account = self.sum_tmp_account([tmp_report_lines['cf_operating_addition_account']])
                list_cf_operating_addition.update({get_filter_date['string'] : {"report_name" : get_filter_date['string'], 'report_lines' : tmp_cf_operating_addition, 'report_lines_account' : tmp_cf_operating_addition_account}})

                tmp_cf_operating_deduction = self._sum_list(tmp_report_lines['cf_operating_deduction'], "cf_operating_deduction")
                tmp_cf_operating_deduction_account = self.sum_tmp_account([tmp_report_lines['cf_operating_deduction_account']])
                list_cf_operating_deduction.update({get_filter_date['string'] : {"report_name" : get_filter_date['string'], 'report_lines' : tmp_cf_operating_deduction, 'report_lines_account' : tmp_cf_operating_deduction_account}})

                tmp_net_income = self._sum_list(tmp_report_lines['net_income'], "net_income")
                tmp_net_income_account = self.sum_tmp_account([tmp_report_lines['net_income_account']])
                list_net_income.update({get_filter_date['string'] : {"report_name" : get_filter_date['string'], 'report_lines' : tmp_net_income, 'report_lines_account' : tmp_net_income_account}})

                tmp_sum_cf_statement = self._sum_list(tmp_cf_operating_cashin_indirect + tmp_cf_operating_cashout_indirect + tmp_cf_operating_addition + tmp_cf_operating_deduction + tmp_net_income, 'Total cash flow from operating activities')
                tmp_sum_cf_statement_account = self.sum_tmp_account([tmp_cf_operating_cashin_indirect_account, tmp_cf_operating_cashout_indirect_account, tmp_cf_operating_addition_account, tmp_cf_operating_deduction_account, tmp_net_income_account])
            else:
                tmp_received_customer = self._sum_list(tmp_report_lines['received_customer'],'Advance payments received from customers')
                tmp_received_customer_account = self.sum_tmp_account([tmp_report_lines['received_customer_account']])
                list_received_customer.update({get_filter_date['string'] : {"report_name" : get_filter_date['string'], 'report_lines' : tmp_received_customer, 'report_lines_account' : tmp_received_customer_account}})

                tmp_cash_received = self._sum_list(tmp_report_lines['cash_received'],'Cash received from')
                tmp_cash_received_account = self.sum_tmp_account([tmp_report_lines['cash_received_account']])
                list_cash_received.update({get_filter_date['string'] : {"report_name" : get_filter_date['string'], 'report_lines' : tmp_cash_received, 'report_lines_account' : tmp_cash_received_account}})

                tmp_payment_supplier = self._sum_list(tmp_report_lines['payment_supplier'],'Advance payments made to suppliers')
                tmp_payment_supplier_account = self.sum_tmp_account([tmp_report_lines['payment_supplier_account']])
                list_payment_supplier.update({get_filter_date['string'] : {"report_name" : get_filter_date['string'], 'report_lines' : tmp_payment_supplier, 'report_lines_account' : tmp_payment_supplier_account}})

                tmp_cash_paid = self._sum_list(tmp_report_lines['cash_paid'],'Cash paid for')
                tmp_cash_paid_account = self.sum_tmp_account([tmp_report_lines['cash_paid_account']])
                list_cash_paid.update({get_filter_date['string'] : {"report_name" : get_filter_date['string'], 'report_lines' : tmp_cash_paid, 'report_lines_account' : tmp_cash_paid_account}})

                tmp_sum_cf_statement = self._sum_list(tmp_received_customer + tmp_cash_received + tmp_payment_supplier + tmp_cash_paid,'Total cash flow from operating activities')
                tmp_sum_cf_statement_account = self.sum_tmp_account([tmp_received_customer_account, tmp_cash_received_account, tmp_payment_supplier_account, tmp_cash_paid_account])

            list_sum_cf_statement.update({get_filter_date['string'] : {"report_name" : get_filter_date['string'], 'report_lines' : tmp_sum_cf_statement, 'report_lines_account' : tmp_sum_cf_statement_account}})

            tmp_cf_investing = self._sum_list(tmp_report_lines['cf_investing'], "cf_investing")
            tmp_cf_investing_account = self.sum_tmp_account([tmp_report_lines['cf_investing_account']])
            list_cf_investing.update({get_filter_date['string'] : {"report_name" : get_filter_date['string'], 'report_lines' : tmp_cf_investing, 'report_lines_account' : tmp_cf_investing_account}})

            tmp_cf_finance = self._sum_list(tmp_report_lines['cf_finance'], "cf_finance")
            tmp_cf_finance_account = self.sum_tmp_account([tmp_report_lines['cf_finance_account']])
            list_cf_finance.update({get_filter_date['string'] : {"report_name" : get_filter_date['string'], 'report_lines' : tmp_cf_finance, 'report_lines_account' : tmp_cf_finance_account}})

            tmp_cf_unclass = self._sum_list(tmp_report_lines['cf_unclass'], "cf_unclass")
            tmp_cf_unclass_account = self.sum_tmp_account([tmp_report_lines['cf_unclass_account']])
            list_cf_unclass.update({get_filter_date['string'] : {"report_name" : get_filter_date['string'], 'report_lines' : tmp_cf_unclass, 'report_lines_account' : tmp_cf_unclass_account}})

            tmp_sum_all_cf_statement = self._sum_list(tmp_sum_cf_statement + tmp_cf_investing + tmp_cf_finance + tmp_cf_unclass,'Net increase in cash and cash equivalents')
            tmp_sum_all_cf_statement_account = self.sum_tmp_account([tmp_sum_cf_statement_account, tmp_cf_investing_account, tmp_cf_finance_account, tmp_cf_unclass_account])
            list_sum_all_cf_statement.update({get_filter_date['string'] : {"report_name" : get_filter_date['string'], 'report_lines' : tmp_sum_all_cf_statement, 'report_lines_account' : tmp_sum_all_cf_statement_account}})

            tmp_cf_beginning_period = self._sum_list(tmp_report_lines['cf_beginning_period'], "Cash and cash equivalents, beginning of period")
            tmp_cf_beginning_period_account = self.sum_tmp_account([tmp_report_lines['cf_beginning_period_account']])
            list_cf_beginning_period.update({get_filter_date['string'] : {"report_name" : get_filter_date['string'], 'report_lines' : tmp_cf_beginning_period, 'report_lines_account' : tmp_cf_beginning_period_account}})

            tmp_cf_closing_period = self._sum_list(tmp_sum_all_cf_statement + tmp_cf_beginning_period,'Cash and cash equivalents, closing of period')
            tmp_cf_closing_period_account = self.sum_tmp_account([tmp_sum_all_cf_statement_account, tmp_cf_beginning_period_account])
            list_cf_closing_period.update({get_filter_date['string'] : {"report_name" : get_filter_date['string'], 'report_lines' : tmp_cf_closing_period, 'report_lines_account' : tmp_cf_closing_period_account}})
        
        return {
            'name': "Cash Flow Report",
            'type': 'ir.actions.client',
            'tag': 'c_f_s',
            'report_lines': report_lines,
            'fetched_data': fetched_data,
            'fetched': fetched,
            'account_res': account_res,
            'journal_res': journal_res,
            'levels': r.levels,
            'filters': filters,
            'currency': currency,
            'type_report': r.type_report,
            'received_customer': received_customer,
            'cash_received': cash_received,
            'payment_supplier': payment_supplier,
            'cash_paid': cash_paid,
            'cf_operating_cashin_indirect': cf_operating_cashin_indirect,
            'cf_operating_cashout_indirect': cf_operating_cashout_indirect,
            'cf_operating_addition': cf_operating_addition,
            'cf_operating_deduction': cf_operating_deduction,
            'net_income': net_income,
            'sum_cf_statement': sum_cf_statement,
            'cf_investing': cf_investing,
            'cf_finance': cf_finance,
            'cf_unclass': cf_unclass,
            'sum_all_cf_statement': sum_all_cf_statement,
            'cf_beginning_period': cf_beginning_period,
            'cf_closing_period': cf_closing_period,
            'list_previews': list_previews,
            'list_report_lines':list_report_lines,
            'list_received_customer' : list_received_customer,
            'list_cash_received' : list_cash_received,
            'list_payment_supplier' : list_payment_supplier,
            'list_cash_paid' : list_cash_paid,
            'list_cf_operating_cashin_indirect' : list_cf_operating_cashin_indirect,
            'list_cf_operating_cashout_indirect' : list_cf_operating_cashout_indirect,
            'list_cf_operating_addition' : list_cf_operating_addition,
            'list_cf_operating_deduction' : list_cf_operating_deduction,
            'list_net_income' : list_net_income,
            'list_sum_cf_statement' : list_sum_cf_statement,
            'list_cf_investing' : list_cf_investing,
            'list_cf_finance' : list_cf_finance,
            'list_cf_unclass' : list_cf_unclass,
            'list_sum_all_cf_statement' : list_sum_all_cf_statement,
            'list_cf_beginning_period' : list_cf_beginning_period,
            'list_cf_closing_period' : list_cf_closing_period,
        }

    def sum_tmp_account(self, list_acc):
        """
        Summarize temporary accounts by code.

        Args:
            list_acc (list): List of lists containing account dictionaries.

        Returns:
            list: List of summarized account dictionaries.
        """
        account_dict = {}
        for sublist in list_acc:
            for acc in sublist:
                code = acc.get('code', '')
                if code in account_dict:
                    account = account_dict[code]
                    account['debit'] += acc.get('debit', 0.0)
                    account['credit'] += acc.get('credit', 0.0)
                    account['balance'] += acc.get('balance', 0.0)
                    aml_ids = acc.get('aml_ids', []) or [acc.get('aml_id')]
                    account['aml_ids'] = list(set(account['aml_ids'] + aml_ids))  # Remove duplicates
                else:
                    account = {
                        'id': acc.get('id', 0),
                        'code': code,
                        'name': acc.get('name', ''),
                        'debit': acc.get('debit', 0.0),
                        'credit': acc.get('credit', 0.0),
                        'balance': acc.get('balance', 0.0),
                        'aml_ids': acc.get('aml_ids', []) or [acc.get('aml_id')]
                    }
                    account_dict[code] = account

        return list(account_dict.values())

    def _check_list(self,list_value):
        values=[]
        check = False
        for rec in list_value:
            if float(rec['total_debit'].replace(',', '')) > 0 or float(rec['total_credit'].replace(',', '')) > 0 or float(rec['total_balance'].replace(',', '')) > 0:
                check = True
        if check == True:
            values = list_value
        return values

    def _sum_list(self,list_value, value_name):
        values=[]
        value =  {'month_part': value_name, 
                  'year_part': 2022, 
                  'total_debit': 0.0, 
                  'total_credit': 0.0, 
                  'total_balance': 0.0}
        for rec in list_value:
            try:
                value['total_debit'] += rec['total_debit']
                value['total_credit'] += rec['total_credit']
                value['total_balance'] += rec['total_balance']
            except:
                value['total_debit'] += float(rec['total_debit'].replace(',', ''))
                value['total_credit'] += float(rec['total_credit'].replace(',', ''))
                value['total_balance'] += float(rec['total_balance'].replace(',', ''))
        value['total_debit'] = formatLang(self.env, value['total_debit'])
        value['total_credit'] = formatLang(self.env, value['total_credit'])
        value['total_balance'] = formatLang(self.env, value['total_balance'])
        values.append(value)
        return values

    def _sum_list_minus(self,list_value, value_name):
        values=[]
        value =  {'month_part': value_name, 
                  'year_part': 2022, 
                  'total_debit': 0.0, 
                  'total_credit': 0.0, 
                  'total_balance': 0.0}
        i = 0
        max_len = len(list_value)
        while i < max_len:
            if i == 0:
                value['total_debit'] = list_value[i]['total_debit']
                value['total_credit'] = list_value[i]['total_credit']
                value['total_balance'] = list_value[i]['total_balance']
                i += 1
            else:
                value['total_debit'] -= list_value[i]['total_debit']
                value['total_credit'] -= list_value[i]['total_credit']
                value['total_balance'] -= list_value[i]['total_balance']
                i += 1
        values.append(value)
        return values

    def get_filter(self, option):
        data = self.get_filter_data(option)
        filters = {}
        if data.get('journal_ids'):
            filters['journals'] = self.env['account.journal'].browse(data.get('journal_ids')).mapped('code')
        else:
            filters['journals'] = ['All']
        if data.get('account_ids', []):
            filters['accounts'] = self.env['account.account'].browse(data.get('account_ids', [])).mapped('code')
        else:
            filters['accounts'] = ['All']

        filters['company_id'] = self.env['res.company'].browse(self.env.company.ids).mapped('name')

        if data.get('target_move'):
            filters['target_move'] = data.get('target_move')
        if data.get('date_from'):
            filters['date_from'] = data.get('date_from')
        if data.get('date_to'):
            filters['date_to'] = data.get('date_to')
        if data.get('levels'):
            filters['levels'] = data.get('levels')
        if data.get('comparison'):
            filters['comparison'] = data.get('comparison')
        if data.get('previous'):
            filters['previous'] = data.get('previous')
        if data.get('comp_detail'):
            filters['comp_detail'] = data.get('comp_detail')
        if data.get('type_report'):
            filters['type_report'] = data.get('type_report')
        else:
            filters['type_report'] = 'direct'

        filters['company_id'] = self.env.company
        filters['companies_list'] = data.get('companies')
        filters['accounts_list'] = data.get('accounts_list')
        filters['journals_list'] = data.get('journals_list')
        filters['company_name'] = data.get('company_name')
        filters['target_move'] = data.get('target_move').capitalize()

        return filters

    def get_filter_data(self, option):
        r = self.env['account.cash.flow.statement'].search([('id', '=', option[0])])
        default_filters = {}
        company_id = self.env.company
        company_ids = self.env.company
        company_domain = [('company_id', '=', company_id.id)]
        
        sql = ("SELECT id, name, code from account_journal where company_id = " + str(company_id.id))
        self.env.cr.execute(sql)
        journals = r.journal_ids if r.journal_ids else self.env.cr.dictfetchall()

        sql = ("SELECT id, name from account_account where company_id = " + str(company_id.id))
        self.env.cr.execute(sql)
        accounts = self.account_ids if self.account_ids else self.env.cr.dictfetchall()

        sql = ("SELECT id, name from res_company")
        self.env.cr.execute(sql)
        companies = self.company_ids if self.company_ids else self.env.cr.dictfetchall()

        filter_dict = {
            'journal_ids': r.journal_ids.ids,
            'account_ids': self.account_ids.ids,
            'company_id': company_id.id,
            'date_from': r.date_from,
            'date_to': r.date_to,
            'levels': r.levels,
            'target_move': r.target_move,
            'journals_list': [(j['id'], j['name'], j['code']) for j in journals],
            'accounts_list': [(a['id'], a['name']) for a in accounts],
            'companies': [(c['id'], c['name']) for c in companies],
            'company_name': company_id and company_id.name,
            'previous' : r.previous,
            'comparison' : r.comparison,
            'comp_detail' : r.comp_detail,
        }
        filter_dict.update(default_filters)
        return filter_dict

    def _query_1(self, opt, state, account_type_id, data, type_payment, tag_id=False, opt2=False):        
        if not opt2:
            option = 'inner'
        else:
            option = opt2
        if not tag_id:
            tags = ""
        else:
            tags = """ and account_account_tag_id = '""" + str(tag_id) + """' """

        res = {}
        query = """ SELECT to_char(am.date, 'Month') as month_part, extract(YEAR from am.date) as year_part,
                    sum(am.debit) AS total_debit, 
                    sum(am.credit) AS total_credit,
                    sum(am.credit) - sum(am.debit) AS total_balance    
                    from (
                    select am.name as nameam, aa.code,aa.name as nameaa, aa.user_type_id, tags.name as nametags, am.date, am.id as idam, am.state, am.move_type, tg.account_account_tag_id, aml.debit, aml.credit, aml.balance
                    FROM account_move as am
                    inner join account_move_line aml ON am.id = aml.move_id AND am.state = 'posted'
                    left JOIN account_account aa ON aa.id = aml.account_id 
                    left JOIN account_account_account_tag tg on tg.account_account_id = aml.account_id
                    left JOIN account_account_tag tags on tags.id = tg.account_account_tag_id
                    WHERE am.company_id = '""" + str(self.env.company.id) + """' and am.date BETWEEN '""" + str(data.get('date_from')) + """' 
                    and '""" + str(data.get('date_to')) + """' 
                    """ + type_payment + """
                    and aml.payment_id notnull
                    and am.id in (select aml2.move_id from account_move_line aml2
                                  inner join account_account aa2 on aa2.id = aml2.account_id
                                  where aa2.user_type_id = '""" + str(account_type_id) + """'
                                  GROUP BY aml2.move_id)
                    order by am.id ASC) as am
                    where user_type_id != '""" + str(account_type_id) + """'
                    """ + tags + """
                    """ + opt + """
                    """ + state + """ 
                    GROUP BY year_part,month_part """
        cr = self._cr
        cr.execute(query)
        result = cr.dictfetchall()
        res['result'] = result
        query_account = """ 
            SELECT 
                am.account_id as id, 
                am.code as code, 
                am.nameaa as name, 
                am.debit as debit, 
                am.credit as credit, 
                am.balance as balance,
                am.aml_id  -- Added the aml_id column in the output
            from (
                select 
                    am.name as nameam, 
                    aa.id as account_id, 
                    aa.code, 
                    aa.name as nameaa, 
                    aa.user_type_id, 
                    tags.name as nametags, 
                    am.date, 
                    am.id as idam, 
                    am.state, 
                    am.move_type, 
                    tg.account_account_tag_id, 
                    aml.debit, 
                    aml.credit, 
                    aml.balance,
                    aml.id as aml_id  -- Added selection of aml.id as aml_id
                FROM 
                    account_move as am
                inner join 
                    account_move_line aml ON am.id = aml.move_id AND am.state = 'posted'
                left JOIN 
                    account_account aa ON aa.id = aml.account_id 
                left JOIN 
                    account_account_account_tag tg on tg.account_account_id = aml.account_id
                left JOIN 
                    account_account_tag tags on tags.id = tg.account_account_tag_id
                WHERE 
                    am.company_id = '""" + str(self.env.company.id) + """' 
                    and am.date BETWEEN '""" + str(data.get('date_from')) + """' 
                    and '""" + str(data.get('date_to')) + """' 
                    """ + type_payment + """
                    and aml.payment_id notnull
                    and am.id in (
                        select 
                            aml2.move_id 
                        from 
                            account_move_line aml2
                        inner join 
                            account_account aa2 on aa2.id = aml2.account_id
                        where 
                            aa2.user_type_id = '""" + str(account_type_id) + """'
                        GROUP BY 
                            aml2.move_id
                    )
                order by 
                    am.id ASC
            ) as am
            where 
                user_type_id!= '""" + str(account_type_id) + """'
                """ + tags + """
                """ + opt + """
                """ + state
        cr = self._cr
        cr.execute(query_account)
        result_account = cr.dictfetchall()
        res['result_account'] = result_account
        return res
    
    def _query_1_receipt(self, opt, state, account_type_id, data, tag_id=False, opt2=False):        
        if not opt2:
            option = 'inner'
        else:
            option = opt2
        if not tag_id:
            tags = ""
        else:
            tags = """ and account_account_tag_id = '""" + str(tag_id) + """' """

        res = {}
        query = """ SELECT to_char(am.date, 'Month') as month_part, extract(YEAR from am.date) as year_part,
                    sum(am.debit) AS total_debit, 
                    sum(am.credit) AS total_credit,
                    sum(am.credit) AS total_balance    
                    from (
                    select am.name as nameam,aj.type,aa.code,aa.name as nameaa, aa.user_type_id, tags.name as nametags, am.date, am.id as idam, am.state, am.move_type, tg.account_account_tag_id, ap.is_reconciled, ap.partner_type, ap.payment_type, aml.debit, aml.credit, aml.balance
                    FROM account_move as am
                    inner join account_move_line aml ON am.id = aml.move_id AND am.state = 'posted'
                    left JOIN account_account aa ON aa.id = aml.account_id 
                    inner join account_journal aj ON aj.id = aml.journal_id and (aj.type = 'cash' or aj.type = 'bank')
                    left JOIN account_account_account_tag tg on tg.account_account_id = aml.account_id
                    left JOIN account_account_tag tags on tags.id = tg.account_account_tag_id
                    left JOIN account_payment ap ON ap.id = aml.payment_id
                    WHERE am.company_id = '""" + str(self.env.company.id) + """' and am.date BETWEEN '""" + str(data.get('date_from')) + """' 
                    and '""" + str(data.get('date_to')) + """' and aa.internal_type = '""" + 'receivable' + """' order by am.id ASC) as am
                    where user_type_id = """ + str(account_type_id) + """
                    """ + tags + """
                    """ + state + """ 
                    GROUP BY year_part,month_part """            
        cr = self._cr
        cr.execute(query)
        result = cr.dictfetchall()
        res['result'] = result

        query_account = """ 
            SELECT 
                am.account_id as id, 
                am.code as code, 
                am.nameaa as name, 
                am.debit as debit, 
                am.credit as credit, 
                (am.credit) as balance,
                am.aml_id  -- Added the aml_id column in the output
            from (
                select 
                    am.name as nameam,
                    aj.type, 
                    aa.id as account_id,
                    aa.code,
                    aa.name as nameaa, 
                    aa.user_type_id, 
                    tags.name as nametags, 
                    am.date, 
                    am.id as idam, 
                    am.state, 
                    am.move_type, 
                    tg.account_account_tag_id, 
                    ap.is_reconciled, 
                    ap.partner_type, 
                    ap.payment_type, 
                    aml.debit, 
                    aml.credit, 
                    aml.balance,
                    aml.id as aml_id  -- Added selection of aml.id as aml_id
                FROM 
                    account_move as am
                inner join 
                    account_move_line aml ON am.id = aml.move_id AND am.state = 'posted'
                left JOIN 
                    account_account aa ON aa.id = aml.account_id 
                inner join 
                    account_journal aj ON aj.id = aml.journal_id and (aj.type = 'cash' or aj.type = 'bank')
                left JOIN 
                    account_account_account_tag tg on tg.account_account_id = aml.account_id
                left JOIN 
                    account_account_tag tags on tags.id = tg.account_account_tag_id
                left JOIN 
                    account_payment ap ON ap.id = aml.payment_id
                WHERE 
                    am.company_id = '""" + str(self.env.company.id) + """' 
                    and am.date BETWEEN '""" + str(data.get('date_from')) + """' 
                    and '""" + str(data.get('date_to')) + """' 
                    and aa.internal_type = '""" + 'receivable' + """' 
                order by 
                    am.id ASC
            ) as am
            where 
                user_type_id = """ + str(account_type_id) + """
                """ + tags + """
                """ + state

        cr = self._cr
        cr.execute(query_account)
        result_account = cr.dictfetchall()
        res['result_account'] = result_account

        return res
    
    def _query_1_payment(self, opt,  state, account_type_id, data, tag_id=False, opt2=False):        
        if not opt2:
            option = 'inner'
        else:
            option = opt2
        if not tag_id:
            tags = ""
        else:
            tags = """ and account_account_tag_id = '""" + str(tag_id) + """' """

        state = """ and state = 'posted' """

        res = {}
        query = """ SELECT to_char(am.date, 'Month') as month_part, extract(YEAR from am.date) as year_part,
                    sum(am.debit) AS total_debit, 
                    sum(am.credit) AS total_credit,
                    sum(am.credit - am.debit) AS total_balance    
                    from (
                    select am.name as nameam,aj.type,aa.code,aa.name as nameaa, aa.user_type_id, tags.name as nametags, am.date, am.id as idam, am.state, am.move_type, tg.account_account_tag_id, ap.is_reconciled, ap.partner_type, ap.payment_type, aml.debit, aml.credit, aml.balance
                    FROM account_move as am
                    inner join account_move_line aml ON am.id = aml.move_id AND am.state = 'posted'
                    left JOIN account_account aa ON aa.id = aml.account_id 
                    inner join account_journal aj ON aj.id = aml.journal_id and (aj.type = 'cash' or aj.type = 'bank')
                    left JOIN account_account_account_tag tg on tg.account_account_id = aml.account_id
                    left JOIN account_account_tag tags on tags.id = tg.account_account_tag_id
                    left JOIN account_payment ap ON ap.id = aml.payment_id
                    WHERE am.company_id = '""" + str(self.env.company.id) + """' and am.date BETWEEN '""" + str(data.get('date_from')) + """' 
                    and '""" + str(data.get('date_to')) + """' and aa.internal_type = '""" + 'payable' + """' order by am.id ASC) as am
                    where user_type_id = """ + str(account_type_id) + """
                    """ + tags + """
                    """ + state + """ 
                    GROUP BY year_part,month_part """            
        cr = self._cr
        cr.execute(query)
        result = cr.dictfetchall()
        res['result'] = result

        query_account = """ 
            SELECT 
                am.account_id as id, 
                am.code as code, 
                am.nameaa as name, 
                am.debit as debit, 
                am.credit as credit, 
                (am.credit - am.debit) as balance,
                am.aml_id  -- Added the aml_id column in the output
            from (
                select 
                    am.name as nameam,
                    aj.type, 
                    aa.id as account_id,
                    aa.code,
                    aa.name as nameaa, 
                    aa.user_type_id, 
                    tags.name as nametags, 
                    am.date, 
                    am.id as idam, 
                    am.state, 
                    am.move_type, 
                    tg.account_account_tag_id, 
                    ap.is_reconciled, 
                    ap.partner_type, 
                    ap.payment_type, 
                    aml.debit, 
                    aml.credit, 
                    aml.balance,
                    aml.id as aml_id  -- Added selection of aml.id as aml_id
                FROM 
                    account_move as am
                inner join 
                    account_move_line aml ON am.id = aml.move_id AND am.state = 'posted'
                left JOIN 
                    account_account aa ON aa.id = aml.account_id 
                inner join 
                    account_journal aj ON aj.id = aml.journal_id and (aj.type = 'cash' or aj.type = 'bank')
                left JOIN 
                    account_account_account_tag tg on tg.account_account_id = aml.account_id
                left JOIN 
                    account_account_tag tags on tags.id = tg.account_account_tag_id
                left JOIN 
                    account_payment ap ON ap.id = aml.payment_id
                WHERE 
                    am.company_id = '""" + str(self.env.company.id) + """' 
                    and am.date BETWEEN '""" + str(data.get('date_from')) + """' 
                    and '""" + str(data.get('date_to')) + """' 
                    and aa.internal_type = '""" + 'payable' + """' 
                order by 
                    am.id ASC
            ) as am
            where 
                user_type_id = """ + str(account_type_id) + """
                """ + tags + """
                """ + state

        cr = self._cr
        cr.execute(query_account)
        result_account = cr.dictfetchall()
        res['result_account'] = result_account

        return res

    def _query_2_receipt(self, opt, state, account_type_ids, data, tag_id=False, opt2=False):        
        if not opt2:
            option = 'inner'
        else:
            option = opt2
        if not tag_id:
            tags = ''
        else:
            tags = """ and account_account_tag_id = '""" + str(tag_id) + """' """

        account_type_receipt = self.env.ref('account.data_account_type_receivable').id
        
        res = {}
        query = """ SELECT to_char(am.date, 'Month') as month_part, extract(YEAR from am.date) as year_part,
                    sum(am.debit) AS total_debit, 
                    sum(am.credit) AS total_credit,
                    sum(am.credit) AS total_balance
                    from (
                    select am.name as nameam, aa.code,aa.name as nameaa, aa.user_type_id, tags.name as nametags, am.date, am.id as idam, am.state, am.move_type, tg.account_account_tag_id, aml.debit, aml.credit, aml.balance
                    FROM account_move as am
                    inner join account_move_line aml ON am.id = aml.move_id AND am.state = 'posted'
                    left JOIN account_account aa ON aa.id = aml.account_id 
                    inner join account_journal aj ON aj.id = aml.journal_id and (aj.type = 'cash' or aj.type = 'bank')
                    left JOIN account_account_account_tag tg on tg.account_account_id = aml.account_id
                    left JOIN account_account_tag tags on tags.id = tg.account_account_tag_id
                    WHERE am.company_id = '""" + str(self.env.company.id) + """' and am.date BETWEEN '""" + str(data.get('date_from')) + """' 
                    and '""" + str(data.get('date_to')) + """' 
                    """ + opt + """
                    and am.id in (select aml2.move_id from account_move_line aml2
                                  inner join account_account aa2 on aa2.id = aml2.account_id
                                  where aa2.user_type_id in """ + str(tuple(account_type_ids)) + """
                                  and aml2.credit != 0
                                  GROUP BY aml2.move_id)
                    order by am.id ASC) as am
                    where user_type_id in """ + str(tuple(account_type_ids)) + """
                    """ + tags + """
                    """ + state + """ 
                    GROUP BY year_part,month_part """
        cr = self._cr
        cr.execute(query)
        result = cr.dictfetchall()
        res['result'] = result
        query_account = """ 
            SELECT 
                am.account_id as id, 
                am.code as code, 
                am.nameaa as name, 
                am.debit as debit, 
                am.credit as credit, 
                am.credit as balance,
                am.aml_id  -- Added the aml_id column in the output
            from (
                select 
                    am.name as nameam, 
                    aa.id as account_id, 
                    aa.code,
                    aa.name as nameaa, 
                    aa.user_type_id, 
                    tags.name as nametags, 
                    am.date, 
                    am.id as idam, 
                    am.state, 
                    am.move_type, 
                    tg.account_account_tag_id, 
                    aml.debit, 
                    aml.credit, 
                    aml.balance,
                    aml.id as aml_id  -- Added selection of aml.id as aml_id
                FROM 
                    account_move as am
                inner join 
                    account_move_line aml ON am.id = aml.move_id AND am.state = 'posted'
                left JOIN 
                    account_account aa ON aa.id = aml.account_id 
                inner join 
                    account_journal aj ON aj.id = aml.journal_id and (aj.type = 'cash' or aj.type = 'bank')
                left JOIN 
                    account_account_account_tag tg on tg.account_account_id = aml.account_id
                left JOIN 
                    account_account_tag tags on tags.id = tg.account_account_tag_id
                WHERE 
                    am.company_id = '""" + str(self.env.company.id) + """' 
                    and am.date BETWEEN '""" + str(data.get('date_from')) + """' 
                    and '""" + str(data.get('date_to')) + """' 
                    """ + opt + """
                    and am.id in (
                        select 
                            aml2.move_id 
                        from 
                            account_move_line aml2
                        inner join 
                            account_account aa2 on aa2.id = aml2.account_id
                        where 
                            aa2.user_type_id in """ + str(tuple(account_type_ids)) + """
                            and aml2.credit!= 0
                        GROUP BY 
                            aml2.move_id
                    )
                order by 
                    am.id ASC
            ) as am
            where 
                user_type_id in """ + str(tuple(account_type_ids)) + """
                """ + tags + """
                """ + state

        cr = self._cr
        cr.execute(query_account)
        result_account = cr.dictfetchall()
        res['result_account'] = result_account

        return res

    def _query_2_paid(self, opt, state, account_type_ids, data, tag_id=False, opt2=False):        
        if not opt2:
            option = 'inner'
        else:
            option = opt2
        if not tag_id:
            tags = ''
        else:
            tags = """ and account_account_tag_id = '""" + str(tag_id) + """' """

        res = {}
        query = """ SELECT to_char(am.date, 'Month') as month_part, extract(YEAR from am.date) as year_part,
                    sum(am.debit) AS total_debit, 
                    sum(am.credit) AS total_credit,
                    -sum(am.balance) AS total_balance    
                    from (
                    select am.name as nameam,aa.code,aa.name as nameaa, aa.user_type_id, tags.name as nametags, am.date, am.id as idam, am.state, am.move_type, tg.account_account_tag_id, aml.debit, aml.credit, aml.balance
                    FROM account_move as am
                    inner join account_move_line aml ON am.id = aml.move_id AND am.state = 'posted'
                    left JOIN account_account aa ON aa.id = aml.account_id 
                    inner join account_journal aj ON aj.id = aml.journal_id and (aj.type = 'cash' or aj.type = 'bank')
                    left JOIN account_account_account_tag tg on tg.account_account_id = aml.account_id
                    left JOIN account_account_tag tags on tags.id = tg.account_account_tag_id
                    WHERE am.company_id = '""" + str(self.env.company.id) + """' and am.date BETWEEN '""" + str(data.get('date_from')) + """' 
                    and '""" + str(data.get('date_to')) + """' 
                    """ + opt + """
                    and am.id in (select aml2.move_id from account_move_line aml2
                                  inner join account_account aa2 on aa2.id = aml2.account_id
                                  where aa2.user_type_id in """ + str(tuple(account_type_ids)) + """
                                  and aml2.debit != 0
                                  GROUP BY aml2.move_id)
                    order by am.id ASC) as am
                    where user_type_id in """ + str(tuple(account_type_ids)) + """
                    """ + tags + """
                    """ + state + """ 
                    GROUP BY year_part,month_part """
        cr = self._cr
        cr.execute(query)
        result = cr.dictfetchall()
        res['result'] = result
        query_account = """ 
            SELECT 
                am.account_id as id, 
                am.code as code, 
                am.nameaa as name, 
                am.debit as debit, 
                am.credit as credit, 
                -am.balance as balance,
                am.aml_id  -- Added the aml_id column in the output
            from (
                select 
                    am.name as nameam, 
                    aa.id as account_id, 
                    aa.code,
                    aa.name as nameaa, 
                    aa.user_type_id, 
                    tags.name as nametags, 
                    am.date, 
                    am.id as idam, 
                    am.state, 
                    am.move_type, 
                    tg.account_account_tag_id, 
                    aml.debit, 
                    aml.credit, 
                    aml.balance,
                    aml.id as aml_id  -- Added selection of aml.id as aml_id
                FROM 
                    account_move as am
                inner join 
                    account_move_line aml ON am.id = aml.move_id AND am.state = 'posted'
                left JOIN 
                    account_account aa ON aa.id = aml.account_id 
                inner join 
                    account_journal aj ON aj.id = aml.journal_id and (aj.type = 'cash' or aj.type = 'bank')
                left JOIN 
                    account_account_account_tag tg on tg.account_account_id = aml.account_id
                left JOIN 
                    account_account_tag tags on tags.id = tg.account_account_tag_id
                WHERE 
                    am.company_id = '""" + str(self.env.company.id) + """' 
                    and am.date BETWEEN '""" + str(data.get('date_from')) + """' 
                    and '""" + str(data.get('date_to')) + """' 
                    """ + opt + """
                    and am.id in (
                        select 
                            aml2.move_id 
                        from 
                            account_move_line aml2
                        inner join 
                            account_account aa2 on aa2.id = aml2.account_id
                        where 
                            aa2.user_type_id in """ + str(tuple(account_type_ids)) + """
                            and aml2.debit!= 0
                        GROUP BY 
                            aml2.move_id
                    )
                order by 
                    am.id ASC
            ) as am
            where 
                user_type_id in """ + str(tuple(account_type_ids)) + """
                """ + tags + """
                """ + state

        cr = self._cr
        cr.execute(query_account)
        result_account = cr.dictfetchall()
        res['result_account'] = result_account

        return res

    def _query_3(self, opt, state, account_type_id, data, tag_id=False, opt2=False):        
        if not opt2:
            option = 'inner'
        else:
            option = opt2
        if not tag_id:
            tags = ''
        else:
            tags = """ and account_account_tag_id = '""" + str(tag_id) + """' """
        
        res = {}
        query = """ SELECT to_char(am.date, 'Month') as month_part, extract(YEAR from am.date) as year_part,
                    -sum(am.debit) AS total_credit, 
                    sum(am.credit) AS total_debit,
                    sum(am.credit) - sum(am.debit) AS total_balance    
                    from (
                    select am.name as nameam, aa.code,aa.name as nameaa, aa.user_type_id, tags.name as nametags, am.date, am.id as idam, am.state, am.move_type, tg.account_account_tag_id, aml.debit, aml.credit, aml.balance
                    FROM account_move as am
                    inner join account_move_line aml ON am.id = aml.move_id AND am.state = 'posted'
                    left JOIN account_account aa ON aa.id = aml.account_id 
                    left JOIN account_account_account_tag tg on tg.account_account_id = aml.account_id
                    left JOIN account_account_tag tags on tags.id = tg.account_account_tag_id
                    WHERE am.company_id = '""" + str(self.env.company.id) + """' and am.date BETWEEN '""" + str(data.get('date_from')) + """' 
                    and '""" + str(data.get('date_to')) + """' 
                    and am.id in (select aml2.move_id from account_move_line aml2
                                          inner join account_account aa2 on aa2.id = aml2.account_id
                                          where aa2.user_type_id = '""" + str(account_type_id) + """'
                                          GROUP BY aml2.move_id)
                    order by am.id ASC) as am
                    where user_type_id != '""" + str(account_type_id) + """'
                    """ + tags + """
                    """ + opt + """
                    """ + state + """ 
                    GROUP BY year_part,month_part """

        cr = self._cr
        cr.execute(query)
        result = cr.dictfetchall()
        res['result'] = result
        query_account = """ 
            SELECT 
                am.account_id as id, 
                am.code as code, 
                am.nameaa as name, 
                -am.debit as credit, 
                am.credit as debit, 
                (am.credit - am.debit) as balance,
                am.aml_id  -- Added the aml_id column in the output
            from (
                select 
                    am.name as nameam, 
                    aa.id as account_id, 
                    aa.code,
                    aa.name as nameaa, 
                    aa.user_type_id, 
                    tags.name as nametags, 
                    am.date, 
                    am.id as idam, 
                    am.state, 
                    am.move_type, 
                    tg.account_account_tag_id, 
                    aml.debit, 
                    aml.credit, 
                    aml.balance,
                    aml.id as aml_id  -- Added selection of aml.id as aml_id
                FROM 
                    account_move as am
                inner join 
                    account_move_line aml ON am.id = aml.move_id AND am.state = 'posted'
                left JOIN 
                    account_account aa ON aa.id = aml.account_id 
                left JOIN 
                    account_account_account_tag tg on tg.account_account_id = aml.account_id
                left JOIN 
                    account_account_tag tags on tags.id = tg.account_account_tag_id
                WHERE 
                    am.company_id = '""" + str(self.env.company.id) + """' 
                    and am.date BETWEEN '""" + str(data.get('date_from')) + """' 
                    and '""" + str(data.get('date_to')) + """' 
                    and am.id in (
                        select 
                            aml2.move_id 
                        from 
                            account_move_line aml2
                        inner join 
                            account_account aa2 on aa2.id = aml2.account_id
                        where 
                            aa2.user_type_id = '""" + str(account_type_id) + """'
                        GROUP BY 
                            aml2.move_id
                    )
                order by 
                    am.id ASC
            ) as am
            where 
                user_type_id!= '""" + str(account_type_id) + """'
                """ + tags + """
                """ + opt + """
                """ + state

        cr = self._cr
        cr.execute(query_account)
        result_account = cr.dictfetchall()
        res['result_account'] = result_account

        return res
    
    def _query_4(self, opt, state, account_type_id, data, tag_id=False, opt2=False):        
        if not opt2:
            option = 'inner'
        else:
            option = opt2
        if not tag_id:
            tags = ''
        else:
            tags = """ and account_account_tag_id = '""" + str(tag_id) + """' """
        
        res = {}
        query = """ SELECT to_char(am.date, 'Month') as month_part, extract(YEAR from am.date) as year_part,
                    -sum(am.debit) AS total_credit, 
                    sum(am.credit) AS total_debit,
                    sum(am.credit) - sum(am.debit) AS total_balance    
                    from (
                    select am.name as nameam, aa.code,aa.name as nameaa, aa.user_type_id, tags.name as nametags, am.date, am.id as idam, am.state, am.move_type, tg.account_account_tag_id, aml.debit, aml.credit, aml.balance
                    FROM account_move as am
                    inner join account_move_line aml ON am.id = aml.move_id AND am.state = 'posted'
                    left JOIN account_account aa ON aa.id = aml.account_id 
                    left JOIN account_account_account_tag tg on tg.account_account_id = aml.account_id
                    left JOIN account_account_tag tags on tags.id = tg.account_account_tag_id
                    WHERE am.company_id = '""" + str(self.env.company.id) + """' and am.date BETWEEN '""" + str(data.get('date_from')) + """' 
                    and '""" + str(data.get('date_to')) + """' 
                    and am.id in (select aml2.move_id from account_move_line aml2
                                  inner join account_account aa2 on aa2.id = aml2.account_id
                                  where aa2.user_type_id = '""" + str(account_type_id) + """'
                                  GROUP BY aml2.move_id)
                    order by am.id ASC) as am
                    where user_type_id != '""" + str(account_type_id) + """'
                    """ + tags + """
                    """ + opt + """
                    """ + state + """ 
                    GROUP BY year_part,month_part """

        cr = self._cr
        cr.execute(query)
        result = cr.dictfetchall()
        res['result'] = result
        query_account = """ 
            SELECT 
                am.account_id as id, 
                am.code as code, 
                am.nameaa as name, 
                -am.debit as credit, 
                am.credit as debit, 
                (am.credit - am.debit) as balance,
                am.aml_id  -- Added the aml_id column in the output
            from (
                select 
                    am.name as nameam, 
                    aa.id as account_id, 
                    aa.code,
                    aa.name as nameaa, 
                    aa.user_type_id, 
                    tags.name as nametags, 
                    am.date, 
                    am.id as idam, 
                    am.state, 
                    am.move_type, 
                    tg.account_account_tag_id, 
                    aml.debit, 
                    aml.credit, 
                    aml.balance,
                    aml.id as aml_id  -- Added selection of aml.id as aml_id
                FROM 
                    account_move as am
                inner join 
                    account_move_line aml ON am.id = aml.move_id AND am.state = 'posted'
                left JOIN 
                    account_account aa ON aa.id = aml.account_id 
                left JOIN 
                    account_account_account_tag tg on tg.account_account_id = aml.account_id
                left JOIN 
                    account_account_tag tags on tags.id = tg.account_account_tag_id
                WHERE 
                    am.company_id = '""" + str(self.env.company.id) + """' 
                    and am.date BETWEEN '""" + str(data.get('date_from')) + """' 
                    and '""" + str(data.get('date_to')) + """' 
                    and am.id in (
                        select 
                            aml2.move_id 
                        from 
                            account_move_line aml2
                        inner join 
                            account_account aa2 on aa2.id = aml2.account_id
                        where 
                            aa2.user_type_id = '""" + str(account_type_id) + """'
                        GROUP BY 
                            aml2.move_id
                    )
                order by 
                    am.id ASC
            ) as am
            where 
                user_type_id!= '""" + str(account_type_id) + """'
                """ + tags + """
                """ + opt + """
                """ + state

        cr = self._cr
        cr.execute(query_account)
        result_account = cr.dictfetchall()
        res['result_account'] = result_account

        return res

    def _query_8(self, opt, state, account_type_ids, data, tag_id=False, opt2=False):
        if not opt2:
            option = 'inner'
        else:
            option = opt2
        if not tag_id:
            tags = ''
        else:
            tags = """ and account_account_tag_id = '""" + str(tag_id) + """' """
      
        cr = self._cr
        res = {}
      
        query = """ SELECT to_char(am.date, 'Month') as month_part, extract(YEAR from am.date) as year_part,
                    sum(am.debit) AS total_debit, 
                    sum(am.credit) AS total_credit,
                    sum(am.credit) AS total_balance
                    from (
                    select am.name as nameam, aa.code,aa.name as nameaa, aa.user_type_id, tags.name as nametags, am.date, am.id as idam, am.state, am.move_type, tg.account_account_tag_id, aml.debit, aml.credit, aml.balance
                    FROM account_move as am
                    inner join account_move_line aml ON am.id = aml.move_id AND am.state = 'posted'
                    left JOIN account_account aa ON aa.id = aml.account_id
                    inner join account_journal aj ON aj.id = aml.journal_id and (aj.type = 'cash' or aj.type = 'bank')
                    left JOIN account_account_account_tag tg on tg.account_account_id = aml.account_id
                    left JOIN account_account_tag tags on tags.id = tg.account_account_tag_id
                    WHERE am.company_id = '""" + str(self.env.company.id) + """' and am.date BETWEEN '""" + str(data.get('date_from')) + """' 
                    and '""" + str(data.get('date_to')) + """' 
                    and am.id in (select aml2.move_id from account_move_line aml2
                                  inner join account_account aa2 on aa2.id = aml2.account_id
                                  GROUP BY aml2.move_id)
                    and aml.credit != 0
                    order by am.id ASC) as am
                    where user_type_id in """ + str(tuple(account_type_ids)) + """
                    """ + tags + """
                    """ + opt + """
                    """ + state + """
                    GROUP BY year_part,month_part """

        cr.execute(query)
        result = cr.dictfetchall()
        res['result'] = result

        query_account = """ 
            SELECT 
                am.account_id as id, 
                am.code as code, 
                am.nameaa as name, 
                am.debit as debit, 
                am.credit as credit, 
                am.credit as balance,
                am.aml_id  -- Added the aml_id column in the output
            from (
                select 
                    am.name as nameam, 
                    aa.id as account_id, 
                    aa.code,
                    aa.name as nameaa, 
                    aa.user_type_id, 
                    tags.name as nametags, 
                    am.date, 
                    am.id as idam, 
                    am.state, 
                    am.move_type, 
                    tg.account_account_tag_id, 
                    aml.debit, 
                    aml.credit, 
                    aml.balance,
                    aml.id as aml_id  -- Added selection of aml.id as aml_id
                FROM 
                    account_move as am
                inner join 
                    account_move_line aml ON am.id = aml.move_id AND am.state = 'posted'
                left JOIN 
                    account_account aa ON aa.id = aml.account_id 
                inner join 
                    account_journal aj ON aj.id = aml.journal_id and (aj.type = 'cash' or aj.type = 'bank')
                left JOIN 
                    account_account_account_tag tg on tg.account_account_id = aml.account_id
                left JOIN 
                    account_account_tag tags on tags.id = tg.account_account_tag_id
                WHERE 
                    am.company_id = '""" + str(self.env.company.id) + """' 
                    and am.date BETWEEN '""" + str(data.get('date_from')) + """' 
                    and '""" + str(data.get('date_to')) + """' 
                    and am.id in (
                        select 
                            aml2.move_id 
                        from 
                            account_move_line aml2
                        inner join 
                            account_account aa2 on aa2.id = aml2.account_id
                        GROUP BY 
                            aml2.move_id
                    )
                    and aml.credit!= 0
                order by 
                    am.id ASC
            ) as am
            where 
                user_type_id in """ + str(tuple(account_type_ids)) + """
                """ + tags + """
                """ + opt + """
                """ + state

        cr.execute(query_account)
        result_account = cr.dictfetchall()
        res['result_account'] = result_account

        return res

    def _query_9(self, opt, state, account_type_ids, data, tag_id=False, opt2=False):
        if not opt2:
            option = 'inner'
        else:
            option = opt2
        if not tag_id:
            tags = ''
        else:
            tags = """ and account_account_tag_id = '""" + str(tag_id) + """' """
      
        cr = self._cr
        res = {}
      
        query = """ SELECT to_char(am.date, 'Month') as month_part, extract(YEAR from am.date) as year_part,
                    sum(am.debit) AS total_debit, 
                    sum(am.credit) AS total_credit,
                    sum(-am.debit) AS total_balance
                    from (
                    select am.name as nameam, aa.code,aa.name as nameaa, aa.user_type_id, tags.name as nametags, am.date, am.id as idam, am.state, am.move_type, tg.account_account_tag_id, aml.debit, aml.credit, aml.balance
                    FROM account_move as am
                    inner join account_move_line aml ON am.id = aml.move_id AND am.state = 'posted'
                    left JOIN account_account aa ON aa.id = aml.account_id
                    inner join account_journal aj ON aj.id = aml.journal_id and (aj.type = 'cash' or aj.type = 'bank')
                    left JOIN account_account_account_tag tg on tg.account_account_id = aml.account_id
                    left JOIN account_account_tag tags on tags.id = tg.account_account_tag_id
                    WHERE am.company_id = '""" + str(self.env.company.id) + """' and am.date BETWEEN '""" + str(data.get('date_from')) + """' 
                    and '""" + str(data.get('date_to')) + """' 
                    and am.id in (select aml2.move_id from account_move_line aml2
                                  inner join account_account aa2 on aa2.id = aml2.account_id
                                  GROUP BY aml2.move_id)
                    and aml.debit != 0
                    order by am.id ASC) as am
                    where user_type_id in """ + str(tuple(account_type_ids)) + """
                    """ + tags + """
                    """ + opt + """
                    """ + state + """
                    GROUP BY year_part,month_part """

        cr.execute(query)
        result = cr.dictfetchall()
        res['result'] = result

        query_account = """ 
            SELECT 
                am.account_id as id, 
                am.code as code, 
                am.nameaa as name, 
                am.debit as debit, 
                am.credit as credit, 
                -am.debit as balance,
                am.aml_id  -- Added the aml_id column in the output
            from (
                select 
                    am.name as nameam, 
                    aa.id as account_id, 
                    aa.code,
                    aa.name as nameaa, 
                    aa.user_type_id, 
                    tags.name as nametags, 
                    am.date, 
                    am.id as idam, 
                    am.state, 
                    am.move_type, 
                    tg.account_account_tag_id, 
                    aml.debit, 
                    aml.credit, 
                    aml.balance,
                    aml.id as aml_id  -- Added selection of aml.id as aml_id
                FROM 
                    account_move as am
                inner join 
                    account_move_line aml ON am.id = aml.move_id AND am.state = 'posted'
                left JOIN 
                    account_account aa ON aa.id = aml.account_id 
                inner join 
                    account_journal aj ON aj.id = aml.journal_id and (aj.type = 'cash' or aj.type = 'bank')
                left JOIN 
                    account_account_account_tag tg on tg.account_account_id = aml.account_id
                left JOIN 
                    account_account_tag tags on tags.id = tg.account_account_tag_id
                WHERE 
                    am.company_id = '""" + str(self.env.company.id) + """' 
                    and am.date BETWEEN '""" + str(data.get('date_from')) + """' 
                    and '""" + str(data.get('date_to')) + """' 
                    and am.id in (
                        select 
                            aml2.move_id 
                        from 
                            account_move_line aml2
                        inner join 
                            account_account aa2 on aa2.id = aml2.account_id
                        GROUP BY 
                            aml2.move_id
                    )
                    and aml.debit!= 0
                order by 
                    am.id ASC
            ) as am
            where 
                user_type_id in """ + str(tuple(account_type_ids)) + """
                """ + tags + """
                """ + opt + """
                """ + state

        cr.execute(query_account)
        result_account = cr.dictfetchall()
        res['result_account'] = result_account

        return res

    def _query_addition(self, opt, state, account_type_ids, data, tag_id=False, opt2=False):
        if not opt2:
            option = 'inner'
        else:
            option = opt2
        if not tag_id:
            tags = ''
        else:
            tags = """ and account_account_tag_id = '""" + str(tag_id) + """' """
      
        cr = self._cr
        res = {}
      
        query = """ SELECT to_char(am.date, 'Month') as month_part, extract(YEAR from am.date) as year_part,
                    sum(am.debit) AS total_debit, 
                    sum(am.credit) AS total_credit,
                    sum(am.credit) AS total_balance
                    from (
                    select am.name as nameam, aa.code,aa.name as nameaa, aa.user_type_id, tags.name as nametags, am.date, am.id as idam, am.state, am.move_type, tg.account_account_tag_id, aml.debit, aml.credit, aml.balance
                    FROM account_move as am
                    inner join account_move_line aml ON am.id = aml.move_id AND am.state = 'posted'
                    left JOIN account_account aa ON aa.id = aml.account_id
                    inner join account_journal aj ON aj.id = aml.journal_id and (aj.type = 'sale' or aj.type = 'purchase' or aj.type = 'general')
                    left JOIN account_account_account_tag tg on tg.account_account_id = aml.account_id
                    left JOIN account_account_tag tags on tags.id = tg.account_account_tag_id
                    WHERE am.company_id = '""" + str(self.env.company.id) + """' and am.date BETWEEN '""" + str(data.get('date_from')) + """' 
                    and '""" + str(data.get('date_to')) + """' 
                    and am.id in (select aml2.move_id from account_move_line aml2
                                  inner join account_account aa2 on aa2.id = aml2.account_id
                                  GROUP BY aml2.move_id)
                    and aml.credit != 0
                    order by am.id ASC) as am
                    where user_type_id in """ + str(tuple(account_type_ids)) + """
                    """ + tags + """
                    """ + opt + """
                    """ + state + """
                    GROUP BY year_part,month_part """

        cr.execute(query)
        result = cr.dictfetchall()
        res['result'] = result

        query_account = """ 
            SELECT 
                am.account_id as id, 
                am.code as code, 
                am.nameaa as name, 
                am.debit as debit, 
                am.credit as credit, 
                am.credit as balance,
                am.aml_id  -- Added the aml_id column in the output
            from (
                select 
                    am.name as nameam, 
                    aa.id as account_id, 
                    aa.code,
                    aa.name as nameaa, 
                    aa.user_type_id, 
                    tags.name as nametags, 
                    am.date, 
                    am.id as idam, 
                    am.state, 
                    am.move_type, 
                    tg.account_account_tag_id, 
                    aml.debit, 
                    aml.credit, 
                    aml.balance,
                    aml.id as aml_id  -- Added selection of aml.id as aml_id
                FROM 
                    account_move as am
                inner join 
                    account_move_line aml ON am.id = aml.move_id AND am.state = 'posted'
                left JOIN 
                    account_account aa ON aa.id = aml.account_id 
                inner join 
                    account_journal aj ON aj.id = aml.journal_id and (aj.type = 'sale' or aj.type = 'purchase' or aj.type = 'general')
                left JOIN 
                    account_account_account_tag tg on tg.account_account_id = aml.account_id
                left JOIN 
                    account_account_tag tags on tags.id = tg.account_account_tag_id
                WHERE 
                    am.company_id = '""" + str(self.env.company.id) + """' 
                    and am.date BETWEEN '""" + str(data.get('date_from')) + """' 
                    and '""" + str(data.get('date_to')) + """' 
                    and am.id in (
                        select 
                            aml2.move_id 
                        from 
                            account_move_line aml2
                        inner join 
                            account_account aa2 on aa2.id = aml2.account_id
                        GROUP BY 
                            aml2.move_id
                    )
                    and aml.credit!= 0
                order by 
                    am.id ASC
            ) as am
            where 
                user_type_id in """ + str(tuple(account_type_ids)) + """
                """ + tags + """
                """ + opt + """
                """ + state

        cr.execute(query_account)
        result_account = cr.dictfetchall()
        res['result_account'] = result_account

        # Add Loss on Sale & Depreciation account into Addition
        account_type_expenses = self.env.ref('account.data_account_type_expenses').id
        account_type_depreciation = self.env.ref('account.data_account_type_depreciation').id
        new_account_type_ids = [account_type_expenses, account_type_depreciation]

        query = """ SELECT to_char(am.date, 'Month') as month_part, extract(YEAR from am.date) as year_part,
                    sum(am.debit) AS total_debit, 
                    sum(am.credit) AS total_credit,
                    sum(am.debit - am.credit) AS total_balance
                    from (
                    select am.name as nameam, aa.code,aa.name as nameaa, aa.user_type_id, tags.name as nametags, am.date, am.id as idam, am.state, am.move_type, tg.account_account_tag_id, aml.debit, aml.credit, aml.balance
                    FROM account_move as am
                    inner join account_move_line aml ON am.id = aml.move_id AND am.state = 'posted'
                    left JOIN account_account aa ON aa.id = aml.account_id
                    inner join account_journal aj ON aj.id = aml.journal_id
                    left JOIN account_account_account_tag tg on tg.account_account_id = aml.account_id
                    left JOIN account_account_tag tags on tags.id = tg.account_account_tag_id
                    WHERE am.company_id = '""" + str(self.env.company.id) + """' and am.date BETWEEN '""" + str(data.get('date_from')) + """' 
                    and '""" + str(data.get('date_to')) + """' 
                    and am.id in (select aml2.move_id from account_move_line aml2
                                  inner join account_account aa2 on aa2.id = aml2.account_id
                                  GROUP BY aml2.move_id)
                    order by am.id ASC) as am
                    where user_type_id in """ + str(tuple(new_account_type_ids)) + """
                    """ + tags + """
                    """ + opt + """
                    """ + state + """
                    GROUP BY year_part,month_part """

        cr.execute(query)
        result = cr.dictfetchall()
        res['result'] += result

        query_account = """ 
            SELECT 
                am.account_id as id, 
                am.code as code, 
                am.nameaa as name, 
                am.debit as debit, 
                am.credit as credit, 
                (am.debit-am.credit) as balance,
                am.aml_id  -- Added the aml_id column in the output
            from (
                select 
                    am.name as nameam, 
                    aa.id as account_id, 
                    aa.code,
                    aa.name as nameaa, 
                    aa.user_type_id, 
                    tags.name as nametags, 
                    am.date, 
                    am.id as idam, 
                    am.state, 
                    am.move_type, 
                    tg.account_account_tag_id, 
                    aml.debit, 
                    aml.credit, 
                    aml.balance,
                    aml.id as aml_id  -- Added selection of aml.id as aml_id
                FROM 
                    account_move as am
                inner join 
                    account_move_line aml ON am.id = aml.move_id AND am.state = 'posted'
                left JOIN 
                    account_account aa ON aa.id = aml.account_id 
                inner join 
                    account_journal aj ON aj.id = aml.journal_id
                left JOIN 
                    account_account_account_tag tg on tg.account_account_id = aml.account_id
                left JOIN 
                    account_account_tag tags on tags.id = tg.account_account_tag_id
                WHERE 
                    am.company_id = '""" + str(self.env.company.id) + """' 
                    and am.date BETWEEN '""" + str(data.get('date_from')) + """' 
                    and '""" + str(data.get('date_to')) + """' 
                    and am.id in (
                        select 
                            aml2.move_id 
                        from 
                            account_move_line aml2
                        inner join 
                            account_account aa2 on aa2.id = aml2.account_id
                        GROUP BY 
                            aml2.move_id
                    )
                order by 
                    am.id ASC
            ) as am
            where 
                user_type_id in """ + str(tuple(new_account_type_ids)) + """
                """ + tags + """
                """ + opt + """
                """ + state

        cr.execute(query_account)
        result_account = cr.dictfetchall()
        res['result_account'] += result_account

        return res

    def _query_deduction(self, opt, state, account_type_ids, data, tag_id=False, opt2=False):
        if not opt2:
            option = 'inner'
        else:
            option = opt2
        if not tag_id:
            tags = ''
        else:
            tags = """ and account_account_tag_id = '""" + str(tag_id) + """' """
      
        cr = self._cr
        res = {}
      
        query = """ SELECT to_char(am.date, 'Month') as month_part, extract(YEAR from am.date) as year_part,
                    sum(am.debit) AS total_debit, 
                    sum(am.credit) AS total_credit,
                    sum(-am.debit) AS total_balance
                    from (
                    select am.name as nameam, aa.code,aa.name as nameaa, aa.user_type_id, tags.name as nametags, am.date, am.id as idam, am.state, am.move_type, tg.account_account_tag_id, aml.debit, aml.credit, aml.balance
                    FROM account_move as am
                    inner join account_move_line aml ON am.id = aml.move_id AND am.state = 'posted'
                    left JOIN account_account aa ON aa.id = aml.account_id
                    inner join account_journal aj ON aj.id = aml.journal_id and (aj.type = 'sale' or aj.type = 'purchase' or aj.type = 'general')
                    left JOIN account_account_account_tag tg on tg.account_account_id = aml.account_id
                    left JOIN account_account_tag tags on tags.id = tg.account_account_tag_id
                    WHERE am.company_id = '""" + str(self.env.company.id) + """' and am.date BETWEEN '""" + str(data.get('date_from')) + """' 
                    and '""" + str(data.get('date_to')) + """' 
                    and am.id in (select aml2.move_id from account_move_line aml2
                                  inner join account_account aa2 on aa2.id = aml2.account_id
                                  GROUP BY aml2.move_id)
                    and aml.debit != 0
                    order by am.id ASC) as am
                    where user_type_id in """ + str(tuple(account_type_ids)) + """
                    """ + tags + """
                    """ + opt + """
                    """ + state + """
                    GROUP BY year_part,month_part """

        cr.execute(query)
        result = cr.dictfetchall()
        res['result'] = result

        query_account = """ 
            SELECT 
                am.account_id as id, 
                am.code as code, 
                am.nameaa as name, 
                am.debit as debit, 
                am.credit as credit, 
                -am.debit as balance,
                am.aml_id  -- Added the aml_id column in the output
            from (
                select 
                    am.name as nameam, 
                    aa.id as account_id, 
                    aa.code,
                    aa.name as nameaa, 
                    aa.user_type_id, 
                    tags.name as nametags, 
                    am.date, 
                    am.id as idam, 
                    am.state, 
                    am.move_type, 
                    tg.account_account_tag_id, 
                    aml.debit, 
                    aml.credit, 
                    aml.balance,
                    aml.id as aml_id  -- Added selection of aml.id as aml_id
                FROM 
                    account_move as am
                inner join 
                    account_move_line aml ON am.id = aml.move_id AND am.state = 'posted'
                left JOIN 
                    account_account aa ON aa.id = aml.account_id 
                inner join 
                    account_journal aj ON aj.id = aml.journal_id and (aj.type = 'sale' or aj.type = 'purchase' or aj.type = 'general')
                left JOIN 
                    account_account_account_tag tg on tg.account_account_id = aml.account_id
                left JOIN 
                    account_account_tag tags on tags.id = tg.account_account_tag_id
                WHERE 
                    am.company_id = '""" + str(self.env.company.id) + """' 
                    and am.date BETWEEN '""" + str(data.get('date_from')) + """' 
                    and '""" + str(data.get('date_to')) + """' 
                    and am.id in (
                        select 
                            aml2.move_id 
                        from 
                            account_move_line aml2
                        inner join 
                            account_account aa2 on aa2.id = aml2.account_id
                        GROUP BY 
                            aml2.move_id
                    )
                    and aml.debit!= 0
                order by 
                    am.id ASC
            ) as am
            where 
                user_type_id in """ + str(tuple(account_type_ids)) + """
                """ + tags + """
                """ + opt + """
                """ + state

        cr.execute(query_account)
        result_account = cr.dictfetchall()
        res['result_account'] = result_account

        # Add Gain on Sale account into Deduction
        account_type_other_income = self.env.ref('account.data_account_type_other_income').id

        query = """ SELECT to_char(am.date, 'Month') as month_part, extract(YEAR from am.date) as year_part,
                    sum(am.debit) AS total_debit, 
                    sum(am.credit) AS total_credit,
                    sum(am.debit - am.credit) AS total_balance
                    from (
                    select am.name as nameam, aa.code,aa.name as nameaa, aa.user_type_id, tags.name as nametags, am.date, am.id as idam, am.state, am.move_type, tg.account_account_tag_id, aml.debit, aml.credit, aml.balance
                    FROM account_move as am
                    inner join account_move_line aml ON am.id = aml.move_id AND am.state = 'posted'
                    left JOIN account_account aa ON aa.id = aml.account_id
                    inner join account_journal aj ON aj.id = aml.journal_id
                    left JOIN account_account_account_tag tg on tg.account_account_id = aml.account_id
                    left JOIN account_account_tag tags on tags.id = tg.account_account_tag_id
                    WHERE am.company_id = '""" + str(self.env.company.id) + """' and am.date BETWEEN '""" + str(data.get('date_from')) + """' 
                    and '""" + str(data.get('date_to')) + """' 
                    and am.id in (select aml2.move_id from account_move_line aml2
                                  inner join account_account aa2 on aa2.id = aml2.account_id
                                  GROUP BY aml2.move_id)
                    order by am.id ASC) as am
                    where user_type_id = '""" + str(account_type_other_income) + """'
                    """ + tags + """
                    """ + opt + """
                    """ + state + """
                    GROUP BY year_part,month_part """

        cr.execute(query)
        result = cr.dictfetchall()
        res['result'] += result

        query_account = """ 
            SELECT 
                am.account_id as id, 
                am.code as code, 
                am.nameaa as name, 
                am.debit as debit, 
                am.credit as credit, 
                (am.debit-am.credit) as balance,
                am.aml_id  -- Added the aml_id column in the output
            from (
                select 
                    am.name as nameam, 
                    aa.id as account_id, 
                    aa.code,
                    aa.name as nameaa, 
                    aa.user_type_id, 
                    tags.name as nametags, 
                    am.date, 
                    am.id as idam, 
                    am.state, 
                    am.move_type, 
                    tg.account_account_tag_id, 
                    aml.debit, 
                    aml.credit, 
                    aml.balance,
                    aml.id as aml_id  -- Added selection of aml.id as aml_id
                FROM 
                    account_move as am
                inner join 
                    account_move_line aml ON am.id = aml.move_id AND am.state = 'posted'
                left JOIN 
                    account_account aa ON aa.id = aml.account_id 
                inner join 
                    account_journal aj ON aj.id = aml.journal_id
                left JOIN 
                    account_account_account_tag tg on tg.account_account_id = aml.account_id
                left JOIN 
                    account_account_tag tags on tags.id = tg.account_account_tag_id
                WHERE 
                    am.company_id = '""" + str(self.env.company.id) + """' 
                    and am.date BETWEEN '""" + str(data.get('date_from')) + """' 
                    and '""" + str(data.get('date_to')) + """' 
                    and am.id in (
                        select 
                            aml2.move_id 
                        from 
                            account_move_line aml2
                        inner join 
                            account_account aa2 on aa2.id = aml2.account_id
                        GROUP BY 
                            aml2.move_id
                    )
                order by 
                    am.id ASC
            ) as am
            where 
                user_type_id = '""" + str(account_type_other_income) + """'
                """ + tags + """
                """ + opt + """
                """ + state

        cr.execute(query_account)
        result_account = cr.dictfetchall()
        res['result_account'] += result_account

        return res

    def _query_10(self, opt, state, account_type_id, data, tag_id=False, opt2=False):
        if not opt2:
            option = 'inner'
        else:
            option = opt2
        if not tag_id:
            tags = ''
        else:
            tags = """ and account_account_tag_id = '""" + str(tag_id) + """' """
      
        cr = self._cr
        res = {}

        query = """ 
            SELECT 
                to_char(am.date, 'Month') as month_part, 
                extract(YEAR from am.date) as year_part,
                sum(am.debit) AS total_debit, 
                sum(am.credit) AS total_credit,
                sum(am.credit) - sum(am.debit) AS total_balance,
                am.aml_id  -- Added the aml_id column in the output
            from (
                select 
                    aa.code, 
                    aa.name as nameaa, 
                    aa.user_type_id, 
                    am.date, 
                    am.id as idam, 
                    am.state, 
                    aml.debit, 
                    aml.credit, 
                    aml.balance,
                    aml.id as aml_id  -- Added selection of aml.id as aml_id
                FROM 
                    account_move as am
                inner join 
                    account_move_line aml ON am.id = aml.move_id AND am.state = 'posted'
                left JOIN 
                    account_account aa ON aa.id = aml.account_id 
                WHERE 
                    am.company_id = '""" + str(self.env.company.id) + """' 
                    and am.date BETWEEN '""" + str(data.get('date_from')) + """' 
                    and '""" + str(data.get('date_to')) + """' 
                    and am.id in (
                        select 
                            aml2.move_id 
                        from 
                            account_move_line aml2
                        inner join 
                            account_account aa2 on aa2.id = aml2.account_id
                        GROUP BY 
                            aml2.move_id
                    )
                order by 
                    am.id ASC
            ) as am
            where 
                user_type_id!= '""" + str(account_type_id) + """'
                """ + tags + """
                """ + opt + """
                """ + state + """
            GROUP BY 
                year_part,
                month_part,
                am.aml_id  -- Added aml_id to the GROUP BY clause
        """

        cr.execute(query)
        result = cr.dictfetchall()
        res['result'] = result

        query_account = """ 
            SELECT 
                am.account_id as id, 
                am.code as code, 
                am.nameaa as name, 
                am.debit as debit, 
                am.credit as credit, 
                (am.credit - am.debit) as balance,
                am.aml_id  -- Added the aml_id column in the output
            from (
                select 
                    aa.id as account_id,
                    aa.code, 
                    aa.name as nameaa, 
                    aa.user_type_id, 
                    am.date, 
                    am.id as idam, 
                    am.state, 
                    aml.debit, 
                    aml.credit, 
                    aml.balance,
                    aml.id as aml_id  -- Added selection of aml.id as aml_id
                FROM 
                    account_move as am
                inner join 
                    account_move_line aml ON am.id = aml.move_id AND am.state = 'posted'
                left JOIN 
                    account_account aa ON aa.id = aml.account_id 
                WHERE 
                    am.company_id = '""" + str(self.env.company.id) + """' 
                    and am.date BETWEEN '""" + str(data.get('date_from')) + """' 
                    and '""" + str(data.get('date_to')) + """' 
                    and am.id in (
                        select 
                            aml2.move_id 
                        from 
                            account_move_line aml2
                        inner join 
                            account_account aa2 on aa2.id = aml2.account_id
                        GROUP BY 
                            aml2.move_id
                    )
                order by 
                    am.id ASC
            ) as am
            where 
                user_type_id!= '""" + str(account_type_id) + """'
                """ + tags + """
                """ + opt + """
                """ + state

        cr.execute(query_account)
        result_account = cr.dictfetchall()
        res['result_account'] = result_account

        return res

    def _query_net_income(self, opt, state, account_type_id, data, tag_id=False, opt2=False):
        if not opt2:
            option = 'inner'
        else:
            option = opt2
        if not tag_id:
            tags = ''
        else:
            tags = """ and account_account_tag_id = '""" + str(tag_id) + """' """
      
        cr = self._cr

        merged_result = []
        merged_result_account = []

        acc_fn_profitandloss_id = self.env.ref('equip3_accounting_reports_template.acc_fn_profitandloss').id
        acc_profitandloss = self.env['account.financial.report'].browse(acc_fn_profitandloss_id)

        count = 0
        for child1 in acc_profitandloss.children_ids:
            count += 1
            for child2 in child1.children_ids:
                if not child2.formulas:
                    if len(child2.account_type_ids.ids) > 1:
                        opt = """ and user_type_id in """ + str(tuple(child2.account_type_ids.ids))
                    else:
                        opt = """ and user_type_id = '""" + str(child2.account_type_ids.id) + """'""" 
                    
                    res = self._query_10(opt, state, account_type_id, data)

                    merged_result += res['result']
                    merged_result_account += res['result_account']

        merged_data = {}
        for item in merged_result:
            key = (item['month_part'], item['year_part'])
            if key in merged_data:
                merged_data[key]['total_debit'] += item['total_debit']
                merged_data[key]['total_credit'] += item['total_credit']
                merged_data[key]['total_balance'] += item['total_balance']
                merged_data[key]['aml_ids'].append(item['aml_id'])
            else:
                aml_id = item.get('aml_id')
                if aml_id:
                    del item['aml_id']
                merged_data[key] = item
                if aml_id:
                    merged_data[key]['aml_ids'] = [aml_id]
        merged_result = list(merged_data.values())

        merged_data = {}
        for item in merged_result_account:
            key = item['code']
            if key in merged_data:
                merged_data[key]['debit'] += item['debit']
                merged_data[key]['credit'] += item['credit']
                merged_data[key]['balance'] += item['balance']
                merged_data[key]['aml_ids'].append(item['aml_id'])
            else:
                aml_id = item.get('aml_id')
                if aml_id:
                    del item['aml_id']
                merged_data[key] = item
                if aml_id:
                    merged_data[key]['aml_ids'] = [aml_id]
        merged_result_account = list(merged_data.values())
      
        res = {
            'result': merged_result,
            'result_account': merged_result_account
        }

        return res

    def _query_unclass(self, opt, state, account_type_id, data, tag_id=False, opt2=False):        
        if not opt2:
            option = 'inner'
        else:
            option = opt2
        if not tag_id:
            tags = ''
        else:
            tags = """ and account_account_tag_id = '""" + str(tag_id) + """' """
        
        res = {}
        query = """ SELECT to_char(am.date, 'Month') as month_part, extract(YEAR from am.date) as year_part,
                    -sum(am.debit) AS total_debit,
                    sum(am.credit) AS total_credit,
                    sum(am.credit) - sum(am.debit) AS total_balance 
                    from (
                    select am.name as nameam, aa.code,aa.name as nameaa, aa.user_type_id, tags.name as nametags, am.date, am.id as idam, am.state, am.move_type, tg.account_account_tag_id, aml.debit, aml.credit, aml.balance
                    FROM account_move as am
                    inner join account_move_line aml ON am.id = aml.move_id AND am.state = 'posted'
                    left JOIN account_account aa ON aa.id = aml.account_id 
                    inner join account_journal aj ON aj.id = aml.journal_id and (aj.type = 'bank' or aj.type = 'cash')
                    left JOIN account_account_account_tag tg on tg.account_account_id = aml.account_id
                    left JOIN account_account_tag tags on tags.id = tg.account_account_tag_id
                    WHERE am.company_id = '""" + str(self.env.company.id) + """' and am.date BETWEEN '""" + str(data.get('date_from')) + """' 
                    and '""" + str(data.get('date_to')) + """' 
                    and am.id in (select aml2.move_id from account_move_line aml2
                                  inner join account_account aa2 on aa2.id = aml2.account_id
                                  where aa2.user_type_id = '""" + str(account_type_id) + """'
                                  GROUP BY aml2.move_id)
                    order by am.id ASC) as am
                    where user_type_id != '""" + str(account_type_id) + """'
                    and account_account_tag_id isnull
                    """ + state + """
                    GROUP BY year_part,month_part  """

        cr = self._cr
        cr.execute(query)
        result = cr.dictfetchall()
        res['result'] = result
        query_account = """ 
            SELECT 
                am.account_id as id, 
                am.code as code, 
                am.nameaa as name, 
                -am.debit as debit, 
                am.credit as credit, 
                (am.credit - am.debit) as balance,
                am.aml_id  -- Added the aml_id column in the output
            from (
                select 
                    am.name as nameam, 
                    aa.id as account_id, 
                    aa.code,
                    aa.name as nameaa, 
                    aa.user_type_id, 
                    tags.name as nametags, 
                    am.date, 
                    am.id as idam, 
                    am.state, 
                    am.move_type, 
                    tg.account_account_tag_id, 
                    aml.debit, 
                    aml.credit, 
                    aml.balance,
                    aml.id as aml_id  -- Added selection of aml.id as aml_id
                FROM 
                    account_move as am
                inner join 
                    account_move_line aml ON am.id = aml.move_id AND am.state = 'posted'
                left JOIN 
                    account_account aa ON aa.id = aml.account_id 
                inner join 
                    account_journal aj ON aj.id = aml.journal_id and (aj.type = 'bank' or aj.type = 'cash')
                left JOIN 
                    account_account_account_tag tg on tg.account_account_id = aml.account_id
                left JOIN 
                    account_account_tag tags on tags.id = tg.account_account_tag_id
                left JOIN 
                    account_payment ap ON ap.id = aml.payment_id
                WHERE 
                    am.company_id = '""" + str(self.env.company.id) + """' 
                    and am.date BETWEEN '""" + str(data.get('date_from')) + """' 
                    and '""" + str(data.get('date_to')) + """' 
                    and am.id in (
                        select 
                            aml2.move_id 
                        from 
                            account_move_line aml2
                        inner join 
                            account_account aa2 on aa2.id = aml2.account_id
                        where 
                            aa2.user_type_id = '""" + str(account_type_id) + """'
                        GROUP BY 
                            aml2.move_id
                    )
                order by 
                    am.id ASC
            ) as am
            where 
                user_type_id!= '""" + str(account_type_id) + """'
                and account_account_tag_id isnull
                """ + state

        cr = self._cr
        cr.execute(query_account)
        result_account = cr.dictfetchall()
        res['result_account'] = result_account
        return res

    def _query_all(self, opt, state, account_type_id, data, tag_id=False, opt2=False):        
        if not opt2:
            option = 'inner'
        else:
            option = opt2
        if not tag_id:
            tags = ''
        else:
            tags = """ AND tg.account_account_tag_id = '""" + str(tag_id) + """' """

        res = {}
        query = """ SELECT to_char(am.date, 'Month') as month_part, extract(YEAR from am.date) as year_part,
                    sum(am.debit) AS total_credit, 
                    sum(am.credit) AS total_debit,
                    sum(am.credit) - sum(am.debit) AS total_balance         
                    from ( select am.date, am.debit, am.credit, am.balance, am.account_account_tag_id, am.state FROM 
                    (select am.name, aa.code,aa.name,tags.name, am.date, am.id, am.state, am.move_type, tg.account_account_tag_id, aml.debit, aml.credit, aml.balance
                        FROM account_move as am
                        left join account_move_line aml ON am.id = aml.move_id
                        left JOIN account_account aa ON aa.id = aml.account_id
                        left JOIN account_account_account_tag tg on tg.account_account_id = aml.account_id
                        left JOIN account_account_tag tags on tags.id = tg.account_account_tag_id
                        WHERE am.company_id = '""" + str(self.env.company.id) + """' and am.date BETWEEN '""" + str(
                        data.get('date_from')) + """' and '""" + str(
                        data.get('date_to')) + """' AND move_type = 'entry' 
                        and am.id in (select aml2.move_id from account_move_line aml2
                                      inner join account_account aa2 on aa2.id = aml2.account_id
                                      where aa2.user_type_id = '""" + str(account_type_id) + """'
                                      GROUP BY aml2.move_id)
                          ) as am  
                        left join account_move_line aml ON am.id = aml.move_id
                        left JOIN account_account aa ON aa.id = aml.account_id
                        left JOIN account_account_account_tag tg on tg.account_account_id = aml.account_id
                        left JOIN account_account_tag tags on tags.id = tg.account_account_tag_id
                        WHERE am.date BETWEEN '""" + str(
                        data.get('date_from')) + """' and '""" + str(
                        data.get('date_to')) + """'
                        AND am.account_account_tag_id is not null ) as am
                        where am.account_account_tag_id is not null
                        """ + state + """
                        GROUP BY year_part,month_part """
        cr = self._cr
        cr.execute(query)
        result = cr.dictfetchall()
        res['result'] = result
        query_account = """ 
            SELECT 
                am.id as id, 
                am.code as code, 
                am.nameaa as name, 
                am.debit as debit, 
                am.credit as credit, 
                am.balance as balance,
                am.aml_id  -- Added the aml_id column in the output
            from (
                select 
                    am.account_id as id, 
                    am.date, 
                    am.debit, 
                    am.credit, 
                    am.balance, 
                    am.account_account_tag_id, 
                    am.state,
                    aml.id as aml_id  -- Added selection of aml.id as aml_id
                FROM 
                    (
                        select 
                            am.name, 
                            aa.id as account_id,
                            aa.code,
                            aa.name,
                            tags.name, 
                            am.date, 
                            am.id, 
                            am.state, 
                            am.move_type, 
                            tg.account_account_tag_id, 
                            aml.debit, 
                            aml.credit, 
                            aml.balance
                        FROM 
                            account_move as am
                        left join 
                            account_move_line aml ON am.id = aml.move_id
                        left JOIN 
                            account_account aa ON aa.id = aml.account_id
                        left JOIN 
                            account_account_account_tag tg on tg.account_account_id = aml.account_id
                        left JOIN 
                            account_account_tag tags on tags.id = tg.account_account_tag_id
                        WHERE 
                            am.company_id = '""" + str(self.env.company.id) + """' 
                            and am.date BETWEEN '""" + str(data.get('date_from')) + """' 
                            and '""" + str(data.get('date_to')) + """' 
                            AND move_type = 'entry' 
                            and am.id in (
                                select 
                                    aml2.move_id 
                                from 
                                    account_move_line aml2
                                inner join 
                                    account_account aa2 on aa2.id = aml2.account_id
                                where 
                                    aa2.user_type_id = '""" + str(account_type_id) + """'
                                GROUP BY 
                                    aml2.move_id
                            )
                    ) as am  
                    left join 
                        account_move_line aml ON am.id = aml.move_id
                    left JOIN 
                        account_account aa ON aa.id = aml.account_id
                    left JOIN 
                        account_account_account_tag tg on tg.account_account_id = aml.account_id
                    left JOIN 
                        account_account_tag tags on tags.id = tg.account_account_tag_id
                    WHERE 
                        am.date BETWEEN '""" + str(data.get('date_from')) + """' 
                        and '""" + str(data.get('date_to')) + """'
                        AND am.account_account_tag_id is not null 
            ) as am
            where 
                am.account_account_tag_id is not null
                """ + state

        cr = self._cr
        cr.execute(query_account)
        result_account = cr.dictfetchall()
        res['result_account'] = result_account

        return res

    def _query_7(self, opt, state, account_type_id, data, tag_id=False, opt2=False):        
        res = {}
        query = """ SELECT to_char(am.date, 'Month') as month_part, extract(YEAR from am.date) as year_part,
                    sum(am.debit) AS total_credit, 
                    sum(am.credit) AS total_debit,
                    sum(am.credit) - sum(am.debit) AS total_balance    
                    from (
                    select am.name as nameam, aa.code,aa.name as nameaa, aa.user_type_id, tags.name as nametags, am.date, am.id as idam, am.state, am.move_type, tg.account_account_tag_id, aml.debit, aml.credit, aml.balance
                    FROM account_move as am
                    inner join account_move_line aml ON am.id = aml.move_id AND am.state = 'posted'
                    left JOIN account_account aa ON aa.id = aml.account_id 
                    left JOIN account_account_account_tag tg on tg.account_account_id = aml.account_id
                    left JOIN account_account_tag tags on tags.id = tg.account_account_tag_id
                    WHERE am.company_id = '""" + str(self.env.company.id) + """' and am.date < '""" + str(data.get('date_from')) + """' 
                    and am.id in (select aml2.move_id from account_move_line aml2
                                  inner join account_account aa2 on aa2.id = aml2.account_id
                                  where aa2.user_type_id = '""" + str(account_type_id) + """'
                                  GROUP BY aml2.move_id)
                    order by am.id ASC) as am
                    where user_type_id = '""" + str(account_type_id) + """'
                    """ + state + """
                    GROUP BY year_part,month_part  """
        cr = self._cr
        cr.execute(query)
        result = cr.dictfetchall()
        res['result'] = result
        query_account = """ 
            SELECT 
                am.account_id as id, 
                am.code as code, 
                am.nameaa as name, 
                am.debit as debit, 
                am.credit as credit, 
                am.balance as balance,
                am.aml_id  -- Added the aml_id column in the output
            from (
                select 
                    am.name as nameam, 
                    aa.id as account_id, 
                    aa.code,
                    aa.name as nameaa, 
                    aa.user_type_id, 
                    tags.name as nametags, 
                    am.date, 
                    am.id as idam, 
                    am.state, 
                    am.move_type, 
                    tg.account_account_tag_id, 
                    aml.debit, 
                    aml.credit, 
                    aml.balance,
                    aml.id as aml_id  -- Added selection of aml.id as aml_id
                FROM 
                    account_move as am
                inner join 
                    account_move_line aml ON am.id = aml.move_id AND am.state = 'posted'
                left JOIN 
                    account_account aa ON aa.id = aml.account_id 
                left JOIN 
                    account_account_account_tag tg on tg.account_account_id = aml.account_id
                left JOIN 
                    account_account_tag tags on tags.id = tg.account_account_tag_id
                WHERE 
                    am.company_id = '""" + str(self.env.company.id) + """' 
                    and am.date < '""" + str(data.get('date_from')) + """' 
                    and am.id in (
                        select 
                            aml2.move_id 
                        from 
                            account_move_line aml2
                        inner join 
                            account_account aa2 on aa2.id = aml2.account_id
                        where 
                            aa2.user_type_id = '""" + str(account_type_id) + """'
                        GROUP BY 
                            aml2.move_id
                    )
                order by 
                    am.id ASC
            ) as am
            where 
                user_type_id = '""" + str(account_type_id) + """'
                """ + state

        cr = self._cr
        cr.execute(query_account)
        result_account = cr.dictfetchall()
        res['result_account'] = result_account

        return res

    def _get_report_values(self, data, option):
        company_ids = self.env.company.ids
        cr = self.env.cr
        company_id = self.env.company
        currency = company_id.currency_id
        symbol = company_id.currency_id.symbol
        rounding = company_id.currency_id.rounding
        position = company_id.currency_id.position

        fetched_data = []
        account_res = []
        journal_res = []
        fetched = []

        received_customer = []
        cash_received = []
        payment_supplier = []
        cash_paid = []

        cf_operating_cashin_indirect = []
        cf_operating_cashout_indirect = []
        cf_operating_addition = []
        cf_operating_deduction = []
        net_income = []

        cf_investing = []
        cf_finance = []
        cf_unclass = []
        cf_beginning_period = []

        received_customer_account = []
        cash_received_account = []
        payment_supplier_account = []
        cash_paid_account = []

        cf_operating_cashin_indirect_account = []
        cf_operating_cashout_indirect_account = []
        cf_operating_addition_account = []
        cf_operating_deduction_account = []
        net_income_account = []

        cf_investing_account = []
        cf_finance_account = []
        cf_unclass_account = []
        cf_beginning_period_account = []

        account_type_receipt = self.env.ref('account.data_account_type_receivable').id
        account_type_payable = self.env.ref('account.data_account_type_payable').id
        account_type_other_income = self.env.ref('account.data_account_type_other_income').id
        account_type_expense = self.env.ref('account.data_account_type_expenses').id

        account_type_id = self.env.ref('account.data_account_type_liquidity').id
        account_tag_financing_id = self.env.ref('account.account_tag_financing').id
        account_tag_investing_id = self.env.ref('account.account_tag_investing').id
        account_type_current_assets = self.env.ref('account.data_account_type_current_assets').id
        account_type_current_liabilities = self.env.ref('account.data_account_type_current_liabilities').id
        account_type_revenue = self.env.ref('account.data_account_type_revenue').id
        model = self.env.context.get('active_model')

        state = """ and state = 'posted' """ if data.get('target_move') == 'Posted' else ''

        if data['type_report'] == 'indirect':
            account_tag_operating_indirect_id = False
            account_type_depreciation = self.env.ref('account.data_account_type_depreciation').id
            account_type_prepayments = self.env.ref('account.data_account_type_prepayments').id

            cashin_account_type_ids = [account_type_current_assets, account_type_current_liabilities, account_type_receipt, account_type_payable]
            cashout_account_type_ids = [account_type_current_assets, account_type_current_liabilities, account_type_payable]
            addition_account_type_ids = [account_type_expense, account_type_current_assets, account_type_current_liabilities, account_type_prepayments, account_type_payable]
            deduction_account_type_ids = [account_type_other_income, account_type_current_assets, account_type_current_liabilities, account_type_receipt, account_type_payable]

            opt = "" 

            query8 = self._query_8(opt, state, cashin_account_type_ids, data, account_tag_operating_indirect_id)
            cf_operating_cashin_indirect = query8['result']
            cf_operating_cashin_indirect_account = query8['result_account']

            query9 = self._query_9(opt, state, cashout_account_type_ids, data, account_tag_operating_indirect_id)
            cf_operating_cashout_indirect = query9['result']
            cf_operating_cashout_indirect_account = query9['result_account']

            query_addition = self._query_addition(opt, state, addition_account_type_ids, data, account_tag_operating_indirect_id)
            cf_operating_addition = query_addition['result']
            cf_operating_addition_account = query_addition['result_account']

            query_deduction = self._query_deduction(opt, state, deduction_account_type_ids, data, account_tag_operating_indirect_id)
            cf_operating_deduction = query_deduction['result']
            cf_operating_deduction_account = query_deduction['result_account']

            query_net_income = self._query_net_income(opt, state, account_type_id, data)
            net_income = query_net_income['result']
            net_income_account = query_net_income['result_account']

        else:
            account_tag_operating_id = self.env.ref('account.account_tag_operating').id
            account_type_inventory = self.env.ref('equip3_accounting_masterdata.data_acc_t_inventory').id

            account_type_ids = [account_type_id, account_type_receipt, account_type_payable]
            received_customer_account_type_id = account_type_receipt
            cash_received_account_type_ids = [account_type_inventory, account_type_current_assets, account_type_current_liabilities, account_type_revenue, account_type_other_income]
            payment_supplier_account_type_id = account_type_payable
            cash_paid_account_type_ids = [account_type_inventory, account_type_current_assets, account_type_current_liabilities, account_type_expense]

            opt = ""
            # opt = """ and is_reconciled = true AND partner_type = 'customer' and payment_type = 'inbound' """
            # query1 = self._query_1(opt, state, account_type_id, data, account_tag_operating_id)
            # received_customer = query1
            query1 = self._query_1_receipt(opt, state, received_customer_account_type_id, data, account_tag_operating_id)
            received_customer = query1['result']
            received_customer_account = query1['result_account']

            # opt = """ and aa.user_type_id != """ + str(account_type_payable)
            query3 = self._query_2_receipt(opt, state, cash_received_account_type_ids, data, account_tag_operating_id)
            # cash_received = query3
            cash_received = query3['result']
            cash_received_account = query3['result_account']        

            # opt = """ and is_reconciled = true AND partner_type = 'supplier' and payment_type = 'outbound' """
            # query3 = self._query_1(opt, state, account_type_id, data, account_tag_operating_id)
            # payment_supplier = query3
            query3 = self._query_1_payment(opt, state, payment_supplier_account_type_id, data, account_tag_operating_id)
            payment_supplier = query3['result']
            payment_supplier_account = query3['result_account']

            # opt = """ and aa.user_type_id not in """ + str(tuple([account_type_receipt, account_type_payable]))
            query3 = self._query_2_paid(opt, state, cash_paid_account_type_ids, data, account_tag_operating_id)
            # cash_paid = query3
            cash_paid = query3['result']
            cash_paid_account = query3['result_account']

        opt = ""
        query1 = self._query_3(opt, state,account_type_id, data, account_tag_investing_id)
        # cf_investing = query1
        cf_investing = query1['result']
        cf_investing_account = query1['result_account']

        query2 = self._query_4(opt, state, account_type_id, data, account_tag_financing_id)
        # cf_finance = query2
        cf_finance = query2['result']
        cf_finance_account = query2['result_account']

        query3 = self._query_unclass(opt, state, account_type_id, data, account_tag_financing_id)
        # cf_unclass = query3
        cf_unclass = query3['result']
        cf_unclass_account = query3['result_account']

        query3 = self._query_7(opt, state, account_type_id, data)
        # cf_beginning_period = query3
        cf_beginning_period = query3['result']
        cf_beginning_period_account = query3['result_account']
        
        return {
            'date_from': data.get('date_from'),
            'date_to': data.get('date_to'),
            'levels': data.get('level'),
            'doc_ids': self.ids,
            'doc_model': model,
            'fetched_data': fetched_data,
            'account_res': account_res,
            'journal_res': journal_res,
            'fetched': fetched,
            'company_currency_id': currency,
            'company_currency_symbol': symbol,
            'company_currency_position': position,
            'received_customer': received_customer,
            'cash_received': cash_received,
            'payment_supplier': payment_supplier,
            'cash_paid': cash_paid,
            'cf_investing': cf_investing,
            'cf_finance': cf_finance,
            'cf_unclass': cf_unclass,
            'cf_beginning_period': cf_beginning_period,
            'received_customer_account' : received_customer_account,
            'cash_received_account' : cash_received_account,
            'payment_supplier_account' : payment_supplier_account,
            'cash_paid_account' : cash_paid_account,
            'cf_investing_account' : cf_investing_account,
            'cf_finance_account' : cf_finance_account,
            'cf_unclass_account' : cf_unclass_account,
            'cf_beginning_period_account' : cf_beginning_period_account,
            'cf_operating_cashin_indirect' : cf_operating_cashin_indirect,
            'cf_operating_cashin_indirect_account' : cf_operating_cashin_indirect_account,
            'cf_operating_cashout_indirect' : cf_operating_cashout_indirect,
            'cf_operating_cashout_indirect_account' : cf_operating_cashout_indirect_account,
            'cf_operating_addition' : cf_operating_addition,
            'cf_operating_addition_account' : cf_operating_addition_account,
            'cf_operating_deduction' : cf_operating_deduction,
            'cf_operating_deduction_account' : cf_operating_deduction_account,
            'net_income' : net_income,
            'net_income_account' : net_income_account,
        }

    def _get_lines(self, account, data):
        account_type_id = self.env.ref(
            'account.data_account_type_liquidity').id
        state = """AND am.state = 'posted' """ if data.get('target_move') == 'posted' else ''
        query = """SELECT aml.account_id,aj.id as j_id,aj.name,am.id, am.name as move_name, sum(aml.debit) AS total_debit, 
                    sum(aml.credit) AS total_credit, COALESCE(SUM(aml.debit - aml.credit),0) AS balance FROM (SELECT am.* FROM account_move as am
                    LEFT JOIN account_move_line aml ON aml.move_id = am.id
                    LEFT JOIN account_account aa ON aa.id = aml.account_id
                    LEFT JOIN account_account_type aat ON aat.id = aa.user_type_id
                    WHERE am.date BETWEEN '""" + str(
            data.get('date_from')) + """' and '""" + str(
            data.get('date_to')) + """' AND aat.id='""" + str(
            account_type_id) + """' """ + state + """) am
                                        LEFT JOIN account_move_line aml ON aml.move_id = am.id
                                        LEFT JOIN account_account aa ON aa.id = aml.account_id
                                        LEFT JOIN account_journal aj ON aj.id = am.journal_id
                                        WHERE aa.id = """ + str(account.id) + """
                                        GROUP BY am.name, aml.account_id, aj.id, aj.name, am.id"""

        cr = self._cr
        cr.execute(query)
        fetched_data = cr.dictfetchall()

        sql2 = """SELECT aa.name as account_name,aa.id as account_id, aj.id, aj.name, sum(aml.debit) AS total_debit,
                        sum(aml.credit) AS total_credit, sum(aml.balance) AS total_balance FROM (SELECT am.* FROM account_move as am
                            LEFT JOIN account_move_line aml ON aml.move_id = am.id
                            LEFT JOIN account_account aa ON aa.id = aml.account_id
                            LEFT JOIN account_account_type aat ON aat.id = aa.user_type_id
                            WHERE am.date BETWEEN '""" + str(
            data.get('date_from')) + """' and '""" + str(
            data.get('date_to')) + """' AND aat.id='""" + str(
            account_type_id) + """' """ + state + """) am
                                                LEFT JOIN account_move_line aml ON aml.move_id = am.id
                                                LEFT JOIN account_account aa ON aa.id = aml.account_id
                                                LEFT JOIN account_journal aj ON aj.id = am.journal_id
                                                WHERE aa.id = """ + str(
            account.id) + """
                                                GROUP BY aa.name, aj.name, aj.id,aa.id"""

        cr = self._cr
        cr.execute(sql2)
        fetch_data = cr.dictfetchall()
        if fetched_data:
            return {
                'account': account.name,
                'id': account.id,
                'code': account.code,
                'move_lines': fetched_data,
                'journal_lines': fetch_data,
            }


    def get_journal_lines(self, account, data, offset=0, fetch_range=FETCH_RANGE):
        account_type_id = self.env.ref(
            'account.data_account_type_liquidity').id
        offset_count = offset * fetch_range
        state = """AND am.state = 'posted' """ if data.get('target_move') == 'posted' else ''
        sql2 = """SELECT aa.name as account_name, aj.name, sum(aml.debit) AS total_debit,
         sum(aml.credit) AS total_credit, COALESCE(SUM(aml.debit - aml.credit),0) AS balance FROM (SELECT am.* FROM account_move as am
             LEFT JOIN account_move_line aml ON aml.move_id = am.id
             LEFT JOIN account_account aa ON aa.id = aml.account_id
             LEFT JOIN account_account_type aat ON aat.id = aa.user_type_id
             WHERE am.date BETWEEN '""" + str(
            data.get('date_from')) + """' and '""" + str(
            data.get('date_to')) + """' AND aat.id='""" + str(
            account_type_id) + """' """ + state + """) am
                                 LEFT JOIN account_move_line aml ON aml.move_id = am.id
                                 LEFT JOIN account_account aa ON aa.id = aml.account_id
                                 LEFT JOIN account_journal aj ON aj.id = am.journal_id
                                 WHERE aa.id = """ + str(account.id) + """
                                 GROUP BY aa.name, aj.name"""

        cr = self._cr
        cr.execute(sql2)
        fetched_data = cr.dictfetchall()
        if fetched_data:
            return {
                'account': account.name,
                'id': account.id,
                'journal_lines': fetched_data,
                'offset': offset_count,
            }




    @api.model
    def create(self, vals):
        vals['target_move'] = 'posted'
        res = super(AccountCasgFlow, self).create(vals)
        return res

    def write(self, vals):
        if vals.get('target_move'):
            vals.update({'target_move': vals.get('target_move').lower()})
        if vals.get('journal_ids'):
            vals.update({'journal_ids': [(6, 0, vals.get('journal_ids'))]})
        if vals.get('journal_ids') == []:
            vals.update({'journal_ids': [(5,)]})
        if vals.get('account_ids'):
            vals.update({'account_ids': [(4, j) for j in vals.get('account_ids')]})
        if vals.get('account_ids') == []:
            vals.update({'account_ids': [(5,)]})
        if not vals.get('company_ids'):
            vals.update({'company_ids': [(5,)]})
        if vals.get('type_report'):
            vals.update({'type_report': vals.get('type_report').lower()})

        vals.update({'company_ids': [(4, j) for j in self.env.company.ids]})
        res = super(AccountCasgFlow, self).write(vals)
        return res

    @api.model
    def _get_currency(self):
        journal = self.env['account.journal'].browse(
            self.env.context.get('default_journal_id', False))
        if journal.currency_id:
            return journal.currency_id.id
        lang = self.env.user.lang
        if not lang:
            lang = 'en_US'
        lang = lang.replace("_", '-')
        currency_array = [self.env.company.currency_id.symbol,
                          self.env.company.currency_id.position, lang]
        return currency_array

    @api.model
    def _get_dates_previous_year(self, data, period_vals):
        period_type = period_vals
        mode = "cash flow"
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
        mode = "cash flow"
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
        if period_type in ('custom','no','today'):
            return self._get_dates_period(data, date_from, date_to, mode, period_type='custom', strict_range=strict_range)
        return None

    @api.model
    def _init_filter_date(self, data, previous_options=None):
        if data.get('date_from') is False or data.get('date_to') is False:
            return

        mode = "cash flow"
        options_filter = data.get('comp_detail') or 'today'
        date_from = data.get('date_from') and fields.Date.from_string(data['date_from'])
        date_to = data.get('date_to') and fields.Date.from_string(data['date_to'])
        strict_range = False
        if previous_options and (data.get('date_from') and data.get('date_to')) and data.get('comp_detail') and not (data.get('comp_detail') == 'today'):

            options_filter = previous_options
            if options_filter == 'custom' or options_filter == 'no' :
                if data.get('date_from'):
                    date_from = fields.Date.from_string(data.get('date_from'))
                if data.get('date_to'):
                    date_to = fields.Date.from_string(data.get('date_to'))

        if options_filter in ['today']:
            
            date_from = fields.Date.context_today(self)
            date_to = date_from
            # date_from = date_utils.get_month(date_to)[0]
            # date_to = fields.Date.context_today(self)
        elif options_filter in ['month','lastmonth']:
            date_from, date_to = date_utils.get_month(fields.Date.context_today(self))
        elif options_filter in ['quarter','lastquarter']:
            date_from, date_to = date_utils.get_quarter(fields.Date.context_today(self))
        elif options_filter in ['year','lastyear']:
            company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(fields.Date.context_today(self))
            date_from = company_fiscalyear_dates['date_from']
            date_to = company_fiscalyear_dates['date_to']
        elif not date_from:
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
            if period_type in ['year','lastyear'] or (period_type in ['year','lastyear'] and (date_from, date_to) == date_utils.get_fiscal_year(date_to)):
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


    def get_dynamic_xlsx_report(self, data, response, report_data, dfr_data):
        report_main_data = json.loads(dfr_data)
        data = json.loads(data)
        report_data = report_main_data.get('report_lines')
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        fetched_data = report_data.get('fetched_data')
        account_res = report_data.get('account_res')
        journal_res = report_data.get('journal_res')
        fetched = report_data.get('fetched')
        account_type_id = self.env.ref('account.data_account_type_liquidity').id
        currency_symbol = self.env.company.currency_id.symbol
        type_report = report_main_data.get('type_report')

        received_customer = []
        cash_received = []
        payment_supplier = []
        cash_paid = []

        cf_operating_cashin_indirect = []
        cf_operating_cashout_indirect = []
        cf_operating_addition = []
        cf_operating_deduction = []
        net_income = []

        if type_report == 'indirect':
            cf_operating_cashin_indirect = self._sum_list(report_data.get('cf_operating_cashin_indirect'),'Cash In')
            cf_operating_cashout_indirect = self._sum_list(report_data.get('cf_operating_cashout_indirect'),'Cash Out')
            cf_operating_addition = self._sum_list(report_data.get('cf_operating_addition'),'Addition')
            cf_operating_deduction = self._sum_list(report_data.get('cf_operating_deduction'),'Deduction')
            net_income = self._sum_list(report_data.get('net_income'),'Net Income')
            sum_cf_statement = self._sum_list(cf_operating_cashin_indirect + cf_operating_cashout_indirect + cf_operating_addition + cf_operating_deduction + net_income,'Total cash flow from operating activities')
        else:
            received_customer = self._sum_list(report_data.get('received_customer'),'Advance payments received from customers')
            cash_received = self._sum_list(report_data.get('cash_received'),'Cash received from')
            payment_supplier = self._sum_list(report_data.get('payment_supplier'),'Advance payments made to suppliers')
            cash_paid = self._sum_list(report_data.get('cash_paid'),'Cash paid for')
            sum_cf_statement = self._sum_list(received_customer + cash_received + payment_supplier + cash_paid,'Total cash flow from operating activities')

        cf_investing = self._sum_list(report_data.get('cf_investing'), "cf_investing")
        cf_finance = self._sum_list(report_data.get('cf_finance'), "cf_finance")
        cf_unclass = self._sum_list(report_data.get('cf_unclass'), "cf_unclass")
        sum_all_cf_statement = self._sum_list(sum_cf_statement + cf_investing + cf_finance + cf_unclass,'Net increase in cash and cash equivalents')
        cf_beginning_period = self._sum_list(report_data.get('cf_beginning_period'), "Cash and cash equivalents, beginning of period")
        cf_closing_period = self._sum_list(sum_all_cf_statement + cf_beginning_period,'Cash and cash equivalents, closing of period')

        list_previews = []
        list_received_customer = {}
        list_cash_received = {}
        list_payment_supplier = {}
        list_cash_paid = {}
        list_cf_operating_cashin_indirect = {}
        list_cf_operating_cashout_indirect = {}
        list_cf_operating_addition = {}
        list_cf_operating_deduction = {}
        list_net_income = {}
        list_sum_cf_statement = {}
        list_cf_investing = {}
        list_cf_finance = {}
        list_cf_unclass = {}
        list_sum_all_cf_statement = {}
        list_cf_beginning_period = {}
        list_cf_closing_period = {}

        list_report_lines = report_main_data.get('list_report_lines')

        for tmp_report_lines in list_report_lines:
            list_previews += [tmp_report_lines['name_filter_date']]

            if type_report == 'indirect':
                tmp_cf_operating_cashin_indirect = self._sum_list(tmp_report_lines['cf_operating_cashin_indirect'],'Cash In')
                list_cf_operating_cashin_indirect.update({tmp_report_lines['name_filter_date'] : {"report_name" : tmp_report_lines['name_filter_date'], 'report_lines' : tmp_cf_operating_cashin_indirect}})

                tmp_cf_operating_cashout_indirect = self._sum_list(tmp_report_lines['cf_operating_cashout_indirect'],'Cash Out')
                list_cf_operating_cashout_indirect.update({tmp_report_lines['name_filter_date'] : {"report_name" : tmp_report_lines['name_filter_date'], 'report_lines' : tmp_cf_operating_cashout_indirect}})

                tmp_cf_operating_addition = self._sum_list(tmp_report_lines['cf_operating_addition'],'Addition')
                list_cf_operating_addition.update({tmp_report_lines['name_filter_date'] : {"report_name" : tmp_report_lines['name_filter_date'], 'report_lines' : tmp_cf_operating_addition}})

                tmp_cf_operating_deduction = self._sum_list(tmp_report_lines['cf_operating_deduction'],'Deduction')
                list_cf_operating_deduction.update({tmp_report_lines['name_filter_date'] : {"report_name" : tmp_report_lines['name_filter_date'], 'report_lines' : tmp_cf_operating_deduction}})

                tmp_net_income = self._sum_list(tmp_report_lines['net_income'],'Net Income')
                list_net_income.update({tmp_report_lines['name_filter_date'] : {"report_name" : tmp_report_lines['name_filter_date'], 'report_lines' : tmp_net_income}})

                tmp_sum_cf_statement = self._sum_list(tmp_cf_operating_cashin_indirect + tmp_cf_operating_cashout_indirect + tmp_cf_operating_addition + tmp_cf_operating_deduction + tmp_net_income,'Total cash flow from operating activities')
            else:
                tmp_received_customer = self._sum_list(tmp_report_lines['received_customer'],'Advance payments received from customers')
                list_received_customer.update({tmp_report_lines['name_filter_date'] : {"report_name" : tmp_report_lines['name_filter_date'], 'report_lines' : tmp_received_customer}})

                tmp_cash_received = self._sum_list(tmp_report_lines['cash_received'],'Cash received from')
                list_cash_received.update({tmp_report_lines['name_filter_date'] : {"report_name" : tmp_report_lines['name_filter_date'], 'report_lines' : tmp_cash_received}})

                tmp_payment_supplier = self._sum_list(tmp_report_lines['payment_supplier'],'Advance payments made to suppliers')
                list_payment_supplier.update({tmp_report_lines['name_filter_date'] : {"report_name" : tmp_report_lines['name_filter_date'], 'report_lines' : tmp_payment_supplier}})

                tmp_cash_paid = self._sum_list(tmp_report_lines['cash_paid'],'Cash paid for')
                list_cash_paid.update({tmp_report_lines['name_filter_date'] : {"report_name" : tmp_report_lines['name_filter_date'], 'report_lines' : tmp_cash_paid}})

                tmp_sum_cf_statement = self._sum_list(tmp_received_customer + tmp_cash_received + tmp_payment_supplier + tmp_cash_paid,'Total cash flow from operating activities')
            
            list_sum_cf_statement.update({tmp_report_lines['name_filter_date'] : {"report_name" : tmp_report_lines['name_filter_date'], 'report_lines' : tmp_sum_cf_statement}})

            tmp_cf_investing = self._sum_list(tmp_report_lines['cf_investing'], "cf_investing")
            list_cf_investing.update({tmp_report_lines['name_filter_date'] : {"report_name" : tmp_report_lines['name_filter_date'], 'report_lines' : tmp_cf_investing}})

            tmp_cf_finance = self._sum_list(tmp_report_lines['cf_finance'], "cf_finance")
            list_cf_finance.update({tmp_report_lines['name_filter_date'] : {"report_name" : tmp_report_lines['name_filter_date'], 'report_lines' : tmp_cf_finance}})

            tmp_cf_unclass = self._sum_list(tmp_report_lines['cf_unclass'], "cf_unclass")
            list_cf_unclass.update({tmp_report_lines['name_filter_date'] : {"report_name" : tmp_report_lines['name_filter_date'], 'report_lines' : tmp_cf_unclass}})

            tmp_sum_all_cf_statement = self._sum_list(tmp_sum_cf_statement + tmp_cf_investing + tmp_cf_finance + tmp_cf_unclass,'Net increase in cash and cash equivalents')
            list_sum_all_cf_statement.update({tmp_report_lines['name_filter_date'] : {"report_name" : tmp_report_lines['name_filter_date'], 'report_lines' : tmp_sum_all_cf_statement}})

            tmp_cf_beginning_period = self._sum_list(tmp_report_lines['cf_beginning_period'], "Cash and cash equivalents, beginning of period")
            list_cf_beginning_period.update({tmp_report_lines['name_filter_date'] : {"report_name" : tmp_report_lines['name_filter_date'], 'report_lines' : tmp_cf_beginning_period}})

            tmp_cf_closing_period = self._sum_list(tmp_sum_all_cf_statement + tmp_cf_beginning_period,'Cash and cash equivalents, closing of period')
            list_cf_closing_period.update({tmp_report_lines['name_filter_date'] : {"report_name" : tmp_report_lines['name_filter_date'], 'report_lines' : tmp_cf_closing_period}})

        logged_users = self.env['res.company']._company_default_get('account.account')
        sheet = workbook.add_worksheet()
        bold = workbook.add_format({'border': 1, 'bold': True})
        date = workbook.add_format({})
        cell_format = workbook.add_format({'bold': True,})
        head = workbook.add_format({'bold': True})
        txt = workbook.add_format({})
        txt_left = workbook.add_format({'border': 1})
        txt_center = workbook.add_format({'border': 1})
        amount = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        amount_bold = workbook.add_format({'border': 1, 'bold': True, 'num_format': '#,##0.00'})
        txt_bold = workbook.add_format({'border': 1, 'bold': True})
        borderall = workbook.add_format({'border': 1})
        head1 = workbook.add_format({'bold': True})
        head2 = workbook.add_format({'bold': True})
        filtermove = workbook.add_format({'bold': True})

        sheet.set_column('A:A', 70, cell_format)
        sheet.set_column('B:Z', 30, cell_format)

        sheet.write(1, 0, data.get('company_name'), head1)
        if type_report == 'indirect':
            sheet.write(2, 0, 'CASH FLOW REPORT (INDIRECT)', head2)
        else:
            sheet.write(2, 0, 'CASH FLOW REPORT (DIRECT)', head2)
        sheet.write(4, 0, "Accrual Basis : " + data.get('target_move').capitalize() + " Entry", filtermove)

        row_num = 4
        col_num = 0
        received_customer_list = received_customer
        cash_received_list = cash_received
        payment_supplier_list = payment_supplier
        cash_paid_list = cash_paid
        cf_operating_cashin_indirect_list = cf_operating_cashin_indirect
        cf_operating_cashout_indirect_list = cf_operating_cashout_indirect
        cf_operating_addition_list = cf_operating_addition
        cf_operating_deduction_list = cf_operating_deduction
        net_income_list = net_income
        sum_cf_statement_list = sum_cf_statement
        cf_investing_list = cf_investing
        cf_finance_list = cf_finance
        cf_unclass_list = cf_unclass
        sum_all_cf_statement_list = sum_all_cf_statement
        cf_beginning_period_list = cf_beginning_period
        cf_closing_period_list = cf_closing_period

        line_received_customer_list = list_received_customer
        line_cash_received_list = list_cash_received
        line_payment_supplier_list = list_payment_supplier
        line_cash_paid_list = list_cash_paid
        line_cf_operating_cashin_indirect_list = list_cf_operating_cashin_indirect
        line_cf_operating_cashout_indirect_list = list_cf_operating_cashout_indirect
        line_cf_operating_addition_list = list_cf_operating_addition
        line_cf_operating_deduction_list = list_cf_operating_deduction
        line_net_income_list = list_net_income
        line_sum_cf_statement_list = list_sum_cf_statement
        line_cf_investing_list = list_cf_investing
        line_cf_finance_list = list_cf_finance
        line_cf_unclass_list = list_cf_unclass
        line_sum_all_cf_statement_list = list_sum_all_cf_statement
        line_cf_beginning_period_list = list_cf_beginning_period
        line_cf_closing_period_list = list_cf_closing_period

        sheet.write(row_num + 1, col_num, "Name", bold)
        n_p = 0
        for previews in list_previews:
            sheet.write(row_num + 1, col_num + 1 + n_p, str(previews), bold)
            n_p+=1

        row_num += 1
        sheet.write(row_num + 1, col_num, 'Cash flow from operating activities', txt_bold)
        sheet.write(row_num + 1, col_num + 1, '', txt_bold)
        row_num += 1

        if type_report == 'indirect':
            for i_rec in net_income_list:
                sheet.write(row_num + 1, col_num, "Net Income", txt_left)
                n_p = 0
                for previews in list_previews:
                    sheet.write(row_num + 1, col_num + 1 + n_p, (((line_net_income_list[previews])['report_lines'])[0])['total_balance'], amount)
                    n_p+=1
                row_num = row_num + 1
            for i_rec in cf_operating_addition_list:
                sheet.write(row_num + 1, col_num, "Addition", txt_left)
                n_p = 0
                for previews in list_previews:
                    sheet.write(row_num + 1, col_num + 1 + n_p, (((line_cf_operating_addition_list[previews])['report_lines'])[0])['total_balance'], amount)
                    n_p+=1
                row_num = row_num + 1
            for i_rec in cf_operating_deduction_list:
                sheet.write(row_num + 1, col_num, "Deduction", txt_left)
                n_p = 0
                for previews in list_previews:
                    sheet.write(row_num + 1, col_num + 1 + n_p, (((line_cf_operating_deduction_list[previews])['report_lines'])[0])['total_balance'], amount)
                    n_p+=1
                row_num = row_num + 1
            for i_rec in cf_operating_cashin_indirect_list:
                sheet.write(row_num + 1, col_num, "Cash In", txt_left)
                n_p = 0
                for previews in list_previews:
                    sheet.write(row_num + 1, col_num + 1 + n_p, (((line_cf_operating_cashin_indirect_list[previews])['report_lines'])[0])['total_balance'], amount)
                    n_p+=1
                row_num = row_num + 1
            for i_rec in cf_operating_cashout_indirect_list:
                sheet.write(row_num + 1, col_num, "Cash Out", txt_left)
                n_p = 0
                for previews in list_previews:
                    sheet.write(row_num + 1, col_num + 1 + n_p, (((line_cf_operating_cashout_indirect_list[previews])['report_lines'])[0])['total_balance'], amount)
                    n_p+=1
                row_num = row_num + 1
        else:
            for i_rec in received_customer_list:
                sheet.write(row_num + 1, col_num, str(i_rec['month_part']), txt_left)
                n_p = 0
                for previews in list_previews:
                    sheet.write(row_num + 1, col_num + 1 + n_p, (((line_received_customer_list[previews])['report_lines'])[0])['total_balance'], amount)
                    n_p+=1
                row_num = row_num + 1
            for i_rec in cash_received_list:
                sheet.write(row_num + 1, col_num, str(i_rec['month_part']), txt_left)
                n_p = 0
                for previews in list_previews:
                    sheet.write(row_num + 1, col_num + 1 + n_p, (((line_cash_received_list[previews])['report_lines'])[0])['total_balance'], amount)
                    n_p+=1
                row_num = row_num + 1
            for i_rec in payment_supplier_list:
                sheet.write(row_num + 1, col_num, str(i_rec['month_part']), txt_left)
                n_p = 0
                for previews in list_previews:
                    sheet.write(row_num + 1, col_num + 1 + n_p, (((line_payment_supplier_list[previews])['report_lines'])[0])['total_balance'], amount)
                    n_p+=1
                row_num = row_num + 1
            for i_rec in cash_paid_list:
                sheet.write(row_num + 1, col_num, str(i_rec['month_part']), txt_left)
                n_p = 0
                for previews in list_previews:
                    sheet.write(row_num + 1, col_num + 1 + n_p, (((line_cash_paid_list[previews])['report_lines'])[0])['total_balance'], amount)
                    n_p+=1
                row_num = row_num + 1

        for i_rec in sum_cf_statement_list:
            sheet.write(row_num + 1, col_num, str(i_rec['month_part']), txt_left)
            n_p = 0
            for previews in list_previews:
                sheet.write(row_num + 1, col_num + 1 + n_p, (((line_sum_cf_statement_list[previews])['report_lines'])[0])['total_balance'], amount)
                n_p+=1
            row_num = row_num + 1
        row_num += 1
        sheet.write(row_num + 1, col_num, 'Cash flow from investing and extraordinary activities', txt_bold)
        sheet.write(row_num + 1, col_num + 1, '', txt_bold)
        row_num += 1
        for i_rec in cf_investing_list:
            sheet.write(row_num + 1, col_num, "Cash In", txt_left)
            n_p = 0
            for previews in list_previews:
                sheet.write(row_num + 1, col_num + 1 + n_p, (((line_cf_investing_list[previews])['report_lines'])[0])['total_debit'], amount)
                n_p+=1
            row_num = row_num + 1
        for i_rec in cf_investing_list:
            sheet.write(row_num + 1, col_num, "Cash Out", txt_left)
            n_p = 0
            for previews in list_previews:
                sheet.write(row_num + 1, col_num + 1 + n_p, (((line_cf_investing_list[previews])['report_lines'])[0])['total_credit'], amount)
                n_p+=1
            row_num = row_num + 1
        for i_rec in cf_investing_list:
            sheet.write(row_num + 1, col_num, "Total cash flow from financing activities", txt_left)
            n_p = 0
            for previews in list_previews:
                sheet.write(row_num + 1, col_num + 1 + n_p, (((line_cf_investing_list[previews])['report_lines'])[0])['total_balance'], amount)
                n_p+=1
            row_num = row_num + 1
        row_num += 1
        sheet.write(row_num + 1, col_num, 'Cash flow from financing activities', txt_bold)
        sheet.write(row_num + 1, col_num + 1, '', txt_bold)
        row_num += 1
        for i_rec in cf_finance_list:
            sheet.write(row_num + 1, col_num, "Cash In", txt_left)
            n_p = 0
            for previews in list_previews:
                sheet.write(row_num + 1, col_num + 1 + n_p, (((line_cf_finance_list[previews])['report_lines'])[0])['total_debit'], amount)
                n_p+=1
            row_num = row_num + 1
        for i_rec in cf_finance_list:
            sheet.write(row_num + 1, col_num, "Cash Out", txt_left)
            n_p = 0
            for previews in list_previews:
                sheet.write(row_num + 1, col_num + 1 + n_p, (((line_cf_finance_list[previews])['report_lines'])[0])['total_credit'], amount)
                n_p+=1
            row_num = row_num + 1
        for i_rec in cf_finance_list:
            sheet.write(row_num + 1, col_num, "Total cash flow from financing activities", txt_left)
            n_p = 0
            for previews in list_previews:
                sheet.write(row_num + 1, col_num + 1 + n_p, (((line_cf_finance_list[previews])['report_lines'])[0])['total_balance'], amount)
                n_p+=1
            row_num = row_num + 1
        if len(cf_unclass_list) > 0:
            row_num += 1
            sheet.write(row_num + 1, col_num, 'Cash flow from unclassified activities', txt_bold)
            sheet.write(row_num + 1, col_num + 1, '', txt_bold)
            row_num += 1
            for i_rec in cf_unclass_list:
                sheet.write(row_num + 1, col_num, "Cash In", txt_left)
                n_p = 0
                for previews in list_previews:
                    sheet.write(row_num + 1, col_num + 1 + n_p, (((line_cf_unclass_list[previews])['report_lines'])[0])['total_debit'], amount)
                    n_p+=1
                row_num = row_num + 1
            for i_rec in cf_unclass_list:
                sheet.write(row_num + 1, col_num, "Cash Out", txt_left)
                n_p = 0
                for previews in list_previews:
                    sheet.write(row_num + 1, col_num + 1 + n_p, (((line_cf_unclass_list[previews])['report_lines'])[0])['total_credit'], amount)
                    n_p+=1
                row_num = row_num + 1
            for i_rec in cf_unclass_list:
                sheet.write(row_num + 1, col_num, "Total cash flow from unclassified activities", txt_left)
                n_p = 0
                for previews in list_previews:
                    sheet.write(row_num + 1, col_num + 1 + n_p, (((line_cf_unclass_list[previews])['report_lines'])[0])['total_balance'], amount)
                    n_p+=1
                row_num = row_num + 1
        row_num += 1
        sheet.write(row_num + 1, col_num, 'Net increase in cash and cash equivalents', txt_bold)
        sheet.write(row_num + 1, col_num + 1, '', txt_bold)
        row_num += 1
        for i_rec in sum_all_cf_statement_list:
            sheet.write(row_num + 1, col_num, str(i_rec['month_part']), txt_left)
            n_p = 0
            for previews in list_previews:
                sheet.write(row_num + 1, col_num + 1 + n_p, (((line_sum_all_cf_statement_list[previews])['report_lines'])[0])['total_balance'], amount)
                n_p+=1
            row_num = row_num + 1
        row_num += 1
        sheet.write(row_num + 1, col_num, 'Cash and cash equivalents', txt_bold)
        sheet.write(row_num + 1, col_num + 1, '', txt_bold)
        row_num += 1
        for i_rec in cf_beginning_period_list:
            sheet.write(row_num + 1, col_num, str(i_rec['month_part']), txt_left)
            n_p = 0
            for previews in list_previews:
                sheet.write(row_num + 1, col_num + 1 + n_p, (((line_cf_beginning_period_list[previews])['report_lines'])[0])['total_balance'], amount)
                n_p+=1
            row_num = row_num + 1
        for i_rec in cf_closing_period_list:
            sheet.write(row_num + 1, col_num, str(i_rec['month_part']), txt_left)
            n_p = 0
            for previews in list_previews:
                sheet.write(row_num + 1, col_num + 1 + n_p, (((line_cf_closing_period_list[previews])['report_lines'])[0])['total_balance'], amount)
                n_p+=1
            row_num = row_num + 1

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()