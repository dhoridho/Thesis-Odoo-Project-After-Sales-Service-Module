from odoo import fields, models, api, _
import time
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo.tools.misc import formatLang, format_date
from odoo.tools import config, date_utils, get_lang
from babel.dates import get_quarter_names
import datetime
import io
import json
from odoo.exceptions import AccessError, UserError, AccessDenied

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class EnterprisePettycashView(models.TransientModel):
    _inherit = "account.common.report"
    _name = "account.pettycash.analysis"
    _description = "Enterprise Petty Cash Analysis"


    journal_ids = fields.Many2many('account.journal', string='Journals',  default=[])
    account_ids = fields.Many2many('account.account', string='Accounts', domain=[('internal_group', '=', 'expense')])
    display_account = fields.Selection(
        [('all', 'All'), ('movement', 'With movements'),
         ('not_zero', 'With balance is not equal to 0')],
        string='Display Accounts', default='movement')

    branch_ids = fields.Many2many('res.branch', string='Branches',)
    top_expenses = fields.Selection([('on', 'on'), ('off', 'off')], string='Top Expenses')
    date_from = fields.Date(string='Start Date' )
    date_to = fields.Date(string='End Date')
    titles = fields.Char(string='Title',  default='Petty Cash Analysis')
    entities_comparison = fields.Selection([('off', 'OFF'), ('on', 'ON')], string='Entities Comparison', default='off')
    period = fields.Integer(string="Comparison")
    years_prev = fields.Boolean(string="Years Prev", default=False)
    filter_period = fields.Selection(
                                [('today', 'Today'),
                                 ('month', 'This Month'),
                                 ('quarter', 'This Quarter'),
                                 ('year', 'This Year'),
                                 ('no', 'No'),
                                 ('last_month', 'Last Month'),
                                 ('last_quarter', 'Last Quarter'),
                                 ('last_year', 'Last Year'),
                                 ('custom', 'Custom')],
                                string='Period', default='no')
    # filter_period = fields.Selection(
    #                             [('today', 'Today'), 
    #                              ('this_month', 'This Month'),
    #                              ('this_quarter', 'This Quarter'),
    #                              ('this_year', 'This Year'),
    #                              ('last_month', 'Last Month'),
    #                              ('last_quarter', 'Last Quarter'),
    #                              ('last_year', 'Last Year'),
    #                              ('custom', 'Custom')],
    #                             string='Period', default='today')

    
    

    @api.model
    def _get_dates_period(self, options, date_from, date_to, period_type=None):
        def match(dt_from, dt_to):
            return (dt_from, dt_to) == (date_from, date_to)

        string = None
        # If no date_from or not date_to, we are unable to determine a period
        if not period_type or period_type == 'custom':
            date = date_to or date_from
            company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(date)
            if match(company_fiscalyear_dates['date_from'], company_fiscalyear_dates['date_to']):
                period_type = 'fiscalyear'
                if company_fiscalyear_dates.get('record'):
                    string = company_fiscalyear_dates['record'].name
            elif match(*date_utils.get_month(date)):
                period_type = 'month'
            elif match(*date_utils.get_quarter(date)):
                period_type = 'quarter'
            elif match(*date_utils.get_fiscal_year(date)):
                period_type = 'year'
            elif match(date_utils.get_month(date)[0], fields.Date.today()):
                period_type = 'today'
            else:
                period_type = 'custom'
        elif period_type == 'fiscalyear':
            date = date_to or date_from
            company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(date)
            record = company_fiscalyear_dates.get('record')
            string = record and record.name

        if not string:
            fy_day = self.env.company.fiscalyear_last_day
            fy_month = int(self.env.company.fiscalyear_last_month)
            if period_type == 'year' or (
                    period_type == 'fiscalyear' and (date_from, date_to) == date_utils.get_fiscal_year(date_to)):
                string = date_to.strftime('%Y')
            elif period_type == 'fiscalyear' and (date_from, date_to) == date_utils.get_fiscal_year(date_to, day=fy_day, month=fy_month):
                string = '%s - %s' % (date_to.year - 1, date_to.year)
            elif period_type == 'month':
                string = format_date(self.env, fields.Date.to_string(date_to), date_format='MMM yyyy')
            elif period_type == 'quarter':
                quarter_names = get_quarter_names('abbreviated', locale=get_lang(self.env).code)
                string = u'%s\N{NO-BREAK SPACE}%s' % (
                    quarter_names[date_utils.get_quarter_number(date_to)], date_to.year)
            else:
                dt_from_str = format_date(self.env, fields.Date.to_string(date_from))
                dt_to_str = format_date(self.env, fields.Date.to_string(date_to))
                string = _('From %s\nto  %s') % (dt_from_str, dt_to_str)

        return {
            'string': string,
            'period_type': period_type,
            'date_from': date_from and fields.Date.to_string(date_from) or False,
            'date_to': fields.Date.to_string(date_to),
        }

    @api.model
    def _get_dates_previous_period(self, options, period_vals):
        period_type = period_vals
        date_from = fields.Date.from_string(options['date_from'])
        date_to = date_from - datetime.timedelta(days=1)

        if period_type == 'fiscalyear':
            company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(date_to)
            return self._get_dates_period(options, company_fiscalyear_dates['date_from'], company_fiscalyear_dates['date_to'])
        if period_type in ('month', 'today', 'custom', 'last_month', 'no'):
            return self._get_dates_period(options, *date_utils.get_month(date_to), period_type='month')
        if period_type in ('quarter', 'last_quarter'):
            return self._get_dates_period(options, *date_utils.get_quarter(date_to), period_type='quarter')
        if period_type in ('year', 'last_year'):
            return self._get_dates_period(options, *date_utils.get_fiscal_year(date_to), period_type='year')
        return None

    @api.model
    def _get_dates_previous_year(self, options, period_vals):
        period_type = period_vals
        date_from = fields.Date.from_string(options['date_from'])
        date_from = date_from - relativedelta(years=1)
        date_to = fields.Date.from_string(options['date_to'])
        date_to = date_to - relativedelta(years=1)

        if period_type == 'month':
            date_from, date_to = date_utils.get_month(date_to)
        return self._get_dates_period(options, date_from, date_to, period_type=period_type)

    @api.model
    def _init_filter_date(self, options, prev_year=False):
        # Default values.
        # mode = self.filter_date.get('mode', 'range')
        options_filter = options['filter_period']
        date_from = fields.Date.from_string(options['date_from'])
        date_to =fields.Date.from_string(options['date_to'])
        period_type = False

        # Handle previous_options.
        if options_filter == 'custom' or options_filter == 'no':
            period_type = options_filter
            if options['date_from']:
                date_from = fields.Date.from_string(options['date_from'])
            if options['date_to']:
                date_to = fields.Date.from_string(options['date_to'])

        # Create date option for each company.
        if 'today' in options_filter:
            date_to = fields.Date.context_today(self)
            date_from = date_utils.get_month(date_to)[0]
        elif 'month' in options_filter:
            date_from, date_to = date_utils.get_month(fields.Date.context_today(self))
            period_type = 'month'
        elif 'quarter' in options_filter:
            date_from, date_to = date_utils.get_quarter(fields.Date.context_today(self))
            period_type = 'quarter'
        elif 'year' in options_filter:
            company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(fields.Date.context_today(self))
            date_from = company_fiscalyear_dates['date_from']
            date_to = company_fiscalyear_dates['date_to']
        elif not date_from:
            # options_filter == 'custom' && mode == 'single'
            date_from = date_utils.get_month(date_to)[0]

        if prev_year:
            # options['date_from'] = date_utils.get_month(fields.Date.from_string(options['date_from']))[0] - relativedelta(days=1)
            if period_type in ('month', 'last_month'):
                date_from, date_to = date_utils.get_month(fields.Date.from_string(options['date_from']))
                options['date_from'], options['date_to'] = date_utils.get_month(fields.Date.from_string(options['date_from']))
            if period_type in ('quarter', 'last_quarter'):
                date_from, date_to = date_utils.get_quarter(options['date_from'])
                options['date_from'], options['date_to'] = date_utils.get_quarter(fields.Date.from_string(options['date_from']))
            if period_type in ('year', 'last_year'):
                date_from, date_to = date_utils.get_fiscal_year(fields.Date.from_string(options['date_from']))
                options['date_from'], options['date_to'] = date_utils.get_fiscal_year(fields.Date.from_string(options['date_from']))
        
        
        if options_filter in  ['last_month' ,'last_quarter' ,'last_year']:
            options['date_from'] = date_utils.get_month(fields.Date.from_string(options['date_from']))[0]
            if prev_year:
                filter_Date = self._get_dates_previous_year(options, period_type)
                return filter_Date
            else:
                filter_Date = self._get_dates_previous_period(options, options_filter)
                return filter_Date
        else:
            if prev_year:
                filter_Date = self._get_dates_previous_year(options, period_type)
                return filter_Date
            else:
                if options['period'] == 0:
                    filter_Date = self._get_dates_period(options, date_from, date_to, period_type=period_type)
                else:
                    filter_Date = self._get_dates_previous_period(options, options_filter)
                return filter_Date



    @api.model
    def view_report(self, option):
        r = self.env['account.pettycash.analysis'].search([('id', '=', option[0])])
        journals = r.journal_ids
 
        data = {
            'display_account': r.display_account,
            'model':self,
            'journals': journals,
            'accounts': r.account_ids,
            'top_expenses': r.top_expenses,
            'branchs'   : r.branch_ids,
            'date_from': r.date_from,
            'date_to': r.date_to,
            'entities_comparison': r.entities_comparison,
            'period': r.period,
            'filter_period': r.filter_period,
            'years_prev': r.years_prev,
            
        }

        if r.filter_period == 'custom' or r.filter_period == 'no':
            date_from = r.date_from
            date_to = r.date_to
        else:
            date_from = date_to = datetime.date.today()

        # filter_date_period = self._init_filter_date(date_from, date_to, r.filter_period)

        data.update({
                        # 'date_from': filter_date_period['date_from'],
                        # 'date_to': filter_date_period['date_to'],
                        'date_from': date_from,
                        'date_to': date_to,
                    })

        
        filters = self.get_filter(option)
        records = self._get_report_values(data)
        currency = self._get_currency()



        return {
            'name': "PettyCash Analysis",
            'type': 'ir.actions.client',
            'tag': 'ent_p',
            'filters': filters,
            'report_lines': records['pettycash'],            
            'total_amount':records['total_amount'],
            'total_balance':records['total_balance'],
            'total_expenses':records['total_expenses'],
            'total_virtual':records['total_virtual'],
            'currency': currency,
            'pettycash_result': records['pettycash_result'],
            'list_periode': records['list_periode'],
            'list_total_amount' : records['list_total_amount'],
            'list_total_balance' : records['list_total_balance'],
            'list_total_expenses' : records['list_total_expenses'],
            'list_total_virtual' : records['list_total_virtual'],
        }
    

    def get_filter(self, option):
        data = self.get_filter_data(option)

        filters = {}

        # if data.get('journal_ids'):
        #     filters['journals'] = self.env['account.journal'].browse(data.get('journal_ids')).mapped('code')
        # else:
        #     filters['journals'] = ['All']

        if data.get('branchs'):
            filters['branchs'] = self.env['res.branch'].browse(
                data.get('branchs')).mapped('name')
        else:
            filters['branchs'] = ['All']  

        if data.get('account_ids', []):
            filters['accounts'] = self.env['account.account'].browse(data.get('account_ids', [])).mapped('code')
        else:
            filters['accounts'] = ['All']

        if data.get('top_expenses'):
            filters['top_expenses'] = data.get('top_expenses')
        else:
            filters['top_expenses'] = 'off'

        if data.get('date_from'):
            filters['date_from'] = data.get('date_from')
        if data.get('date_to'):
            filters['date_to'] = data.get('date_to')

        filters['company_id'] = ''
        filters['branchs_list'] = data.get('branchs_list')
        filters['accounts_list'] = data.get('accounts_list')
        filters['journals_list'] = data.get('journals_list')
        filters['company_name'] = data.get('company_name')
        filters['entities_comparison'] = data.get('entities_comparison')

        filters['period'] = data.get('period')
        filters['filter_period'] = data.get('filter_period')
        filters['years_prev'] = data.get('years_prev')
        
    
        return filters

    def get_filter_data(self, option):
        r = self.env['account.pettycash.analysis'].search([('id', '=', option[0])])
        default_filters = {}
        company_id = self.env.company
        company_domain = [('company_id', '=', company_id.id)]
        journals = r.journal_ids if r.journal_ids else self.env['account.journal'].search(company_domain)
        accounts = self.account_ids if self.account_ids else self.env['account.account'].search([('user_type_id.internal_group', '=', 'expense'),('company_id', '=', self.env.company.id)])
        branchs = r.branch_ids if r.branch_ids else self.env['res.branch'].search(company_domain)
        top_expenses = r.top_expenses if r.top_expenses else 'off'
        filter_dict = {
            'journal_ids': r.journal_ids.ids,
            'account_ids': r.account_ids.ids,
            'company_id': company_id.id,
            'date_from': r.date_from,
            'date_to': r.date_to,
            'top_expenses': top_expenses,
            'journals_list': [(j.id, j.name, j.code) for j in journals],
            'accounts_list': [(a.id, a.name) for a in accounts],
            'company_name': company_id and company_id.name,
            'branchs_list': [(b.id, b.name) for b in branchs],
            'entities_comparison': r.entities_comparison,
            'period': r.period,
            'filter_period': r.filter_period,
            'years_prev': r.years_prev,
            # 'target_move': r.target_move,
            # 'partners': r.partner_ids.ids,
            # 'reconciled': r.reconciled,
            # 'account_type': r.account_type_ids.ids,
            # 'partner_tags': r.partner_category_ids.ids,
            # 'partners_list': [(p.id, p.name) for p in partner],
            # 'category_list': [(c.id, c.name) for c in categories],
            # 'account_type_list': [(t.id, t.name) for t in account_types],

        }
        filter_dict.update(default_filters)
        return filter_dict

    def _get_report_values(self, data):
        docs = data['model']
        display_account = data['display_account']
        init_balance = True

        accounts = self.env['account.account'].search([('user_type_id.internal_group', '=', 'expense'),('company_id', '=', self.env.company.id)])
        pettycash = self.env['account.pettycash'].search([])
                    
        if not accounts:
            raise UserError(_("No Accounts Found! Please Add One"))

        period = 1
        if data.get('period'):
            period = data.get('period') + 1
        pettycash_result = {}
        list_total_amount = {}
        list_total_balance = {}
        list_total_expenses = {}
        list_total_virtual = {}
        list_periode = []
        for x in range(0, period):
            filter_date = self._init_filter_date(data, prev_year=data.get('years_prev'))
            data['date_from'] = filter_date['date_from']
            data['date_to'] = filter_date['date_to']
            result = self._get_pettycash(pettycash, accounts, init_balance, display_account, data)
            pettycash_result[filter_date['string']] = result
            list_periode.append(filter_date['string'])            
            if result:
                for p_result in pettycash_result:
                    if p_result == filter_date['string']:
                        continue
                    for result_val in result:
                        cek_id = list(filter(lambda y: y['id'] == result_val['id'], pettycash_result[p_result]))
                        if cek_id:
                            continue
                        tmp_val = {}
                        for key, value in result_val.items():
                            if key in ['amount', 'balance', 'virtual_balance', 'virtual_expenses', 'taxes', 'price', 'total', 'subtotal_taxes', 'subtotal_price', 'subtotal_expenses', 'subtotal_virtual', 'total_amount', 'total_balance', 'total_expenses', 'total_virtual']:
                                value = 0                            
                            tmp_val[key] = value
                        pettycash_result[p_result].append(tmp_val)
            
            for p_result in pettycash_result:
                if p_result == filter_date['string']:
                    continue
                for result_val in pettycash_result[p_result]:
                    cek_id = list(filter(lambda y: y['id'] == result_val['id'], pettycash_result[filter_date['string']]))
                    if cek_id:
                        continue
                    tmp_val = {}
                    for key, value in result_val.items():
                        if key in ['amount', 'balance', 'virtual_balance', 'virtual_expenses', 'taxes', 'price', 'total', 'subtotal_taxes', 'subtotal_price', 'subtotal_expenses', 'subtotal_virtual', 'total_amount', 'total_balance', 'total_expenses', 'total_virtual']:
                            value = 0                            
                        tmp_val[key] = value
                    pettycash_result[filter_date['string']].append(tmp_val)
            
            list_total_amount[filter_date['string']] = sum(list(map(lambda y: round(y['amount'],2), pettycash_result[filter_date['string']])))
            list_total_balance[filter_date['string']] = sum(list(map(lambda y: round(y['balance'],2), pettycash_result[filter_date['string']])))
            list_total_expenses[filter_date['string']] = sum(list(map(lambda y: round(y['subtotal_expenses'],2), pettycash_result[filter_date['string']])))
            list_total_virtual[filter_date['string']] = sum(list(map(lambda y: round(y['subtotal_virtual'],2), pettycash_result[filter_date['string']])))
        
        pettycash_res = pettycash_result[list_periode[0]]
        total_amount = sum(list(map(lambda y: round(y['amount'],2), pettycash_res)))
        total_balance = sum(list(map(lambda y: round(y['balance'],2), pettycash_res)))
        total_expenses = sum(list(map(lambda y: round(y['subtotal_expenses'],2), pettycash_res)))
        total_virtual = sum(list(map(lambda y: round(y['subtotal_virtual'],2), pettycash_res)))

        return {
            'doc_ids': self.ids,
            'total_amount': total_amount,
            'total_balance': total_balance,
            'total_expenses': total_expenses,
            'total_virtual': total_virtual,
            'docs': docs,
            'time': time,
            'pettycash': pettycash_res,
            'pettycash_result': pettycash_result,
            'list_periode': list_periode,
            'list_total_amount' : list_total_amount,
            'list_total_balance' : list_total_balance,
            'list_total_expenses' : list_total_expenses,
            'list_total_virtual' : list_total_virtual,
        }

    @api.model
    def create(self, vals):
        vals['target_move'] = 'posted'
        res = super(EnterprisePettycashView, self).create(vals)
        return res

    def write(self, vals):

        if vals.get('top_expenses'):
            vals.update({'top_expenses': vals.get('top_expenses').lower()})

        if vals.get('all_account'):
            vals.update({'all_account': vals.get('all_account').lower()})

        if vals.get('account_ids'):
            vals.update(
                {'account_ids': [(4, j) for j in vals.get('account_ids')]})
        if not vals.get('account_ids'):
            vals.update({'account_ids': [(5,)]})

        if vals.get('branch_ids'):
            vals.update(
                {'branch_ids': [(4, j) for j in vals.get('branch_ids')]})
        if not vals.get('branch_ids'):
            vals.update({'branch_ids': [(5,)]})

        if vals.get('entities_comparison'):
            vals.update({'entities_comparison': vals.get('entities_comparison').lower()})

        if vals.get('period'):
            vals.update({'period': vals.get('period').lower()})

        if vals.get('filter_period'):
            vals.update({'filter_period': vals.get('filter_period').lower()})

        if vals.get('years_prev'):
            vals.update({'years_prev': vals.get('years_prev')})

        res = super(EnterprisePettycashView, self).write(vals)
        return res

    def _get_pettycash(self, pettycash, accounts, init_balance, display_account, data):
        cr = self.env.cr
        move_lines = {x: [] for x in pettycash.ids}
        
        wheres = [""]
        final_filter = " AND ".join(wheres)

        final_filter += ' ap.company_id = %s' % str(self.env.company.id)
        final_filter += " AND apvw.date >= '%s'" % data.get('date_from')
        final_filter += " AND apvw.date <= '%s'" % data.get('date_to')

        if data.get('branchs'):
            final_filter += ' AND ap.branch_id IN %s' % str(tuple(data.get('branchs').ids) + tuple([0]))

        if data.get('accounts'):
            final_filter += ' AND apvwl.expense_account IN %s' % str(tuple(data.get('accounts').ids) + tuple([0]))
                
        sql = ('''
            SELECT
                ap."name" AS pettycash_name,
                ap."id" AS pettycash_id,
                ap.amount,
                ap.balance,
                ap.virtual_balance,
               (ap.amount -  ap.virtual_balance) AS virtual_expenses,
                apvw."name" AS voucher_name,
                apvw.date AS date,
                apvw.currency_id AS currency_id,
                apvw.move_id AS move_id,
                ac.symbol AS currency_code,
                ac.position AS currency_position,
                apvwl."name" AS description,
                apvwl.expense_account,
                aa."name" AS account,
                aa.code AS code,
                CONCAT(aa."name", ' (', aa.code, ')') AS account_name,
                apvwl.taxes AS taxes,
                apvwl.price_total AS price,
                apvwl.amount AS total
                
            FROM
                account_pettycash ap

            JOIN account_pettycash_voucher_wizard apvw ON (ap.ID = apvw.fund)
            JOIN account_pettycash_voucher_wizard_line apvwl ON (apvw.ID = apvwl.line_id)
            JOIN res_currency ac ON (apvw.currency_id = ac.ID)
            LEFT JOIN account_account aa ON (apvwl.expense_account = aa.ID)
        
            WHERE 
                ''' + final_filter + '''
            
            ''')
        cr.execute(sql)
        result_sql = cr.dictfetchall()

        for row in result_sql:
            row['m_id'] = row['expense_account']
            row['p_id'] = row['pettycash_id']
            # Use get method with a default value to handle missing key
            # row['balance'] = row['amount']
            # row['virtual_balance'] = row['virtual_balance']
            # row['total'] = row['total']
            # row['voucher_name'] = row['voucher_name']
            # row['account_name'] = row['account_name']
            move_lines[row.pop('pettycash_id')].append(row)
        
        pettycash_res = []
        for pettyc in pettycash:
            company_id = self.env.company
            currency = company_id.currency_id
            res = dict((fn, 0.0) for fn in ['taxes', 'price', 'total','amount','balance','virtual_balance','virtual_expenses'])
            res['currency_id'] = currency.id
            res['currency_code'] = currency.symbol
            res['currency_position'] = currency.position
            res['name'] = pettyc.name
            res['id'] = pettyc.id
            res['move_lines'] = move_lines[pettyc.id]
            # res['amount'] = pettyc.amount
            # if res.get('move_lines'):
            res['amount'] = sum(list(map(lambda y: round(y['amount'],2), res.get('move_lines'))))
            res['balance'] = sum(list(map(lambda y: round(y['balance'],2), res.get('move_lines'))))
            res['virtual_balance'] = sum(list(map(lambda y: round(y['virtual_balance'],2), res.get('move_lines'))))
            res['virtual_expenses'] = sum(list(map(lambda y: round(y['virtual_expenses'],2), res.get('move_lines'))))
            res['taxes'] = sum(list(map(lambda y: round(y['taxes'],2), res.get('move_lines'))))
            res['price'] = sum(list(map(lambda y: round(y['price'],2), res.get('move_lines'))))
            res['total'] = sum(list(map(lambda y: round(y['total'],2), res.get('move_lines'))))

            res['subtotal_taxes'] = sum(list(map(lambda y: round(y['taxes'],2), res.get('move_lines'))))
            res['subtotal_price'] = sum(list(map(lambda y: round(y['price'],2), res.get('move_lines'))))
            res['subtotal_expenses'] = sum(list(map(lambda y: round(y['total'],2), res.get('move_lines'))))
            res['subtotal_virtual'] = sum(list(map(lambda y: round(y['virtual_balance'],2), res.get('move_lines'))))        

            res['total_amount'] = sum(list(map(lambda y: round(y['amount'],2), pettycash_res))) + res['amount']
            res['total_balance'] = sum(list(map(lambda y: round(y['balance'],2), pettycash_res))) + res['balance']
            res['total_expenses'] = sum(list(map(lambda y: round(y['subtotal_expenses'],2), pettycash_res))) + res['subtotal_expenses']
            res['total_virtual'] = sum(list(map(lambda y: round(y['subtotal_virtual'],2), pettycash_res))) + res['subtotal_virtual']
            
            
            if display_account == 'all':
                pettycash_res.append(res)
            if display_account == 'movement' and res.get('move_lines'):
                pettycash_res.append(res)
            if display_account == 'not_zero' and not currency.is_zero(res['balance']):
                pettycash_res.append(res)

            if data.get('top_expenses') == 'on':
                pettycash_res = sorted(pettycash_res, key=lambda x: sum(line.get('total', 0) for line in x['move_lines'] if line.get('total') is not None), reverse=True)
        return pettycash_res


    
    def _get_partners(self, partners, accounts, init_balance, display_account, data):

        cr = self.env.cr
        move_line = self.env['account.move.line']
        move_lines = {x: [] for x in partners.ids}
        currency_id = self.env.company.currency_id

        tables, where_clause, where_params = move_line._query_get()
        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())
        final_filters = " AND ".join(wheres)
        final_filters = final_filters.replace('account_move_line__move_id', 'm').replace(
            'account_move_line', 'l')
        new_final_filter = final_filters
        # if data['target_move'] == 'posted':
        #     new_final_filter += " AND m.state = 'posted'"
        # else:
        #     new_final_filter += " AND m.state in ('draft','posted')"
        new_final_filter += " AND m.state in ('draft','posted')"
        if data.get('date_from'):
            new_final_filter += " AND l.date >= '%s'" % data.get('date_from')
        if data.get('date_to'):
            new_final_filter += " AND l.date <= '%s'" % data.get('date_to')

        if data['journals']:
            new_final_filter += ' AND j.id IN %s' % str(tuple(data['journals'].ids) + tuple([0]))

        if data.get('accounts'):
            WHERE = "WHERE l.account_id IN %s" % str(tuple(data.get('accounts').ids) + tuple([0]))
        else:
            WHERE = "WHERE l.account_id IN %s"

        if data.get('partners'):
            WHERE += ' AND p.id IN %s' % str(
                tuple(data.get('partners').ids) + tuple([0]))

        if data.get('reconciled') == 'unreconciled':
            WHERE += ' AND l.full_reconcile_id is null AND' \
                     ' l.balance != 0 AND a.reconcile is true'

        sql = ('''SELECT l.id AS lid,P.id AS pettycash_id,m.id AS move_id, 
                    l.account_id AS account_id, l.date AS ldate, j.code AS lcode, l.currency_id, 
                    l.amount_currency, l.ref AS lref, l.name AS lname, 
                    COALESCE(l.debit,0) AS debit, COALESCE(l.credit,0) AS credit, 
                    COALESCE(SUM(l.balance),0) AS balance,\
                    m.name AS move_name, c.symbol AS currency_code,c.position AS currency_position, p.name AS ppettycash_name\
                    FROM account_move_line l\
                    JOIN account_move m ON (l.move_id=m.id)\
                    JOIN account_account a ON (l.account_id=a.id)
                    LEFT JOIN res_currency c ON (l.currency_id=c.id)\
                    JOIN account_pettycash P ON ( M.pettycash_id = P.ID )\
                    JOIN account_journal j ON (l.journal_id=j.id)\
                    JOIN account_account acc ON (l.account_id = acc.id)\
                    GROUP BY l.id, m.id,  l.account_id, l.date, j.code, l.currency_id, l.amount_currency, l.ref, l.name, m.name, c.symbol, c.position,P.ID, p.name''' )
        if data.get('accounts'):
            params = tuple(where_params)
        else:
            params = (tuple(accounts.ids),) + tuple(where_params)
        cr.execute(sql)


        account_list = { x.id : {'name' : x.name, 'code': x.code} for x in accounts}

        for row in cr.dictfetchall():
            balance = 0
            if row['pettycash_id'] in move_lines:
                for line in move_lines.get(row['pettycash_id']):
                    balance += round(line['debit'], 2) - round(line['credit'], 2)
                row['balance'] = balance
                row['m_id'] = row['account_id']
                row['p_id'] = row['pettycash_id']
                # Use get method with a default value to handle missing key
                row['account_name'] = account_list.get(row['account_id'], {'name': '', 'code': ''})['name'] + "(" + \
                                    account_list.get(row['account_id'], {'name': '', 'code': ''})['code'] + ")"
                
                move_lines[row.pop('pettycash_id')].append(row)
                partner = partners.browse(row['p_id'])  # Assign the partner here

        partner_res = []
        for partner in partners:
            company_id = self.env.company
            currency = company_id.currency_id
            res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance'])
            res['name'] = partner.name
            res['id'] = partner.id
            res['move_lines'] = move_lines[partner.id]
            for line in res.get('move_lines'):
                line['currency_position'] = currency.position
                line['currency_code'] = currency.symbol
                res['debit'] += round(line['debit'], 2)
                res['credit'] += round(line['credit'], 2)
                res['balance'] = round(line['balance'], 2)
            if display_account == 'all':
                partner_res.append(res)
            if display_account == 'movement' and res.get('move_lines'):
                partner_res.append(res)
            if display_account == 'not_zero' and not currency.is_zero(
                    res['balance']):
                partner_res.append(res)
        return partner_res

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

    def get_dynamic_xlsx_report(self, data, response, report_data, dfr_data):
        report_data = json.loads(report_data)
        filters = json.loads(data)
        currency = self._get_currency()
        currency_symbol = currency[0]
        currency_position = currency[1]

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        cell_format = workbook.add_format({'bold': True, 'border': 0})
        sheet = workbook.add_worksheet()
        # Set the width of columns A to C to 15 pixels
        sheet.set_column('A:C', 25)
        head = workbook.add_format({'bold': True})
        sub_head = workbook.add_format({'bold': True})
        sheet.merge_range('A2:B2', filters.get('company_name'),head)
        sheet.merge_range('A3:C3', 'Enterprise Petty Cash Analysis',sub_head)

        txt = workbook.add_format({'border': 1})
        txt_amount = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        sub_heading_sub = workbook.add_format({'valign': 'vcenter', 'bold': True, 'border': 1,'border_color': 'black'})
        date_head = workbook.add_format({'bold': True, 'border': 1,'border_color': 'black'})
        
        parent_voucher = workbook.add_format({'bold': True, 'border': 1,'border_color': 'black'})
        amount_voucher = workbook.add_format({'bold': True, 'border': 1,'border_color': 'black', 'num_format': '#,##0.00'})

        sheet.merge_range('A8:A9', 'Code / Account',sub_heading_sub)

        last_month = datetime.date.today().replace(day=1) - relativedelta(days=1)
        first_day = last_month.replace(day=1)
        if filters.get('date_from'):
            sheet.write('B8', 'From: ' + filters.get('date_from'),date_head)
        else:
            sheet.write('B8', 'From: ' + str(first_day),date_head)
        if filters.get('date_to'):
            sheet.write('B9', 'To: ' + filters.get('date_to'),date_head)
        else:
            sheet.write('B9', 'To: ' + str(last_month),date_head)


        row = 8
        col = 0

        for report in report_data:

            row += 1
            
            sheet.write(row, col + 0, report['name'], parent_voucher)
            sheet.write(row, col + 1, '', amount_voucher)
            for r_rec in report['move_lines']:
                row += 1
                space = '           '
                sheet.write(row, col + 0, space + r_rec['voucher_name'], txt)
                sheet.write(row, col + 1, r_rec['total'], txt_amount)

            row += 1
            sheet.write(row, col + 0, 'Total Expenses', parent_voucher)
            sheet.write(row, col + 1, report['total_expenses'], amount_voucher)

            row += 1
            sheet.write(row, col + 0, 'Total Virtual', parent_voucher)
            sheet.write(row, col + 1, report['total_virtual'], amount_voucher)
            row += 1
            sheet.write(row, col + 0, 'Total Balance', parent_voucher)
            sheet.write(row, col + 1, report['total_balance'], amount_voucher)
            row += 1
        

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

   
 
       
    
        
    
        
    

    


        