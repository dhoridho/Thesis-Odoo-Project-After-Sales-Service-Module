import time
from odoo import fields, models, api, _

import io
import json
from odoo.exceptions import AccessError, UserError, AccessDenied
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter

class EquityMoveView(models.TransientModel):
    _inherit = "account.common.report"
    _name = 'account.equity.move'

    display_account = fields.Selection(
        [('all', 'All'), ('movement', 'With movements'),
         ('not_zero', 'With balance is not equal to 0')],
        string='Display Accounts', required=True, default='movement')

    @api.model
    def view_report(self, option):
        r = self.env['account.equity.move'].search([('id', '=', option[0])])
        data = {
            'display_account': r.display_account,
            'model':self,
            'target_move': r.target_move,
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
        records = self._get_report_values(data)
        currency = self._get_currency()
        
        return {
            'name': "Equity Movement",
            'type': 'ir.actions.client',
            'tag': 'e_m',
            'filters': filters,            
            'report_lines': records['Accounts'],
            'debit_total': records['debit_total'],
            'credit_total': records['credit_total'],
            'balance_total': records['balance_total'],
            'currency': currency,
            'account_equity_filtered': records['account_equity_filtered'],
            'account_equity': records['account_equity'],
            'account_retained_earnings': records['account_retained_earnings'],
            'account_current_earnings': records['account_current_earnings'],
            'account_prive': records['account_prive'],
            'records': records,
        }
    
    def get_filter(self, option):
        data = self.get_filter_data(option)
        filters = {}
        if data.get('target_move'):
            filters['target_move'] = data.get('target_move')
        if data.get('date_from'):
            filters['date_from'] = data.get('date_from')
        if data.get('date_to'):
            filters['date_to'] = data.get('date_to')

        filters['company_id'] = data.get('company_id')
        filters['company_name'] = data.get('company_name')
        filters['target_move'] = data.get('target_move').capitalize()

        return filters
    
    def get_filter_data(self, option):
        r = self.env['account.equity.move'].search([('id', '=', option[0])])
        default_filters = {}
        company_id = self.env.company
        company_domain = [('company_id', '=', company_id.id)]

        filter_dict = {
            'company_id': company_id.id,
            'date_from': r.date_from,
            'date_to': r.date_to,
            'target_move': r.target_move,
            'company_name': company_id and company_id.name,
        }
        filter_dict.update(default_filters)
        return filter_dict
    
    def _get_report_values(self, data):
        docs = data['model']
        display_account = data['display_account']

        account_types = self.env['account.account.type'].search([])
        if not account_types:
            raise UserError(_("No Account Types Found! Please Add One"))

        accounts = self.env['account.account'].search([])
        if not accounts:
            raise UserError(_("No Accounts Found! Please Add One"))

        account_res = self._get_accounts(accounts, display_account, data)
        account_res_all = self._get_accounts_init(accounts, display_account, data)
        account_equity_filtered = self._get_account_types(account_res_all, display_account, data, ['Equity']) 
        account_equity = []
        if data.get('date_from'):
            account_equity = self._get_account_types(account_res, display_account, data, ['Equity'])
            # account_equity = self._get_additional(account_equity, account_equity_filtered)
        else:
            res = {}
            res['debit'] = 0
            res['credit'] = 0
            res['balance'] = 0
            res['type_id'] = '0000001'
            res['type_name'] = 'null'
            account_equity.append(res)
        
        account_retained_earnings = self._get_account_types(account_res, display_account, data, ['Retained Earnings'])
        type_ids = []

        fin_report = self.env['account.financial.report'].search([('name', '=', 'Profit and Loss')])
        report_PL = fin_report._get_children_by_order()
        for rep_pl_dt in report_PL:
            if rep_pl_dt.account_type_ids:
                for typeid in rep_pl_dt.account_type_ids:
                    type_ids.append(typeid.name)
        
        current_earnings = self._get_account_types(account_res, display_account, data, type_ids)
        account_current_earnings = self._get_total(current_earnings)
        account_prive = self._get_account_types(account_res, display_account, data, ['Prive'])
        debit_total = sum(x['debit'] for x in account_equity_filtered) + sum(x['debit'] for x in account_equity) + sum(x['debit'] for x in account_retained_earnings) + sum(x['debit'] for x in account_current_earnings) + sum(x['debit'] for x in account_prive)
        credit_total = sum(x['credit'] for x in account_equity_filtered) + sum(x['credit'] for x in account_equity) + sum(x['credit'] for x in account_retained_earnings) + sum(x['credit'] for x in account_current_earnings) + sum(x['credit'] for x in account_prive)
        balance_total = sum(x['balance'] for x in account_equity_filtered) + sum(x['balance'] for x in account_equity) + sum(x['balance'] for x in account_retained_earnings) + sum(x['balance'] for x in account_current_earnings) + sum(x['balance'] for x in account_prive)
        

        return {
            'doc_ids': self.ids,
            'debit_total': debit_total,
            'credit_total': credit_total,
            'balance_total': balance_total,
            'docs': docs,
            'time': time,
            'Accounts': account_res,
            'account_equity_filtered': account_equity_filtered,
            'account_equity': account_equity,
            'account_retained_earnings': account_retained_earnings,
            'account_current_earnings': account_current_earnings,
            'account_prive': account_prive,
        }

    # def _get_additional(self,equity, auth):
    #     result = []
    #     res={}
    #     res['debit'] = equity[0]['debit'] - auth[0]['debit']
    #     res['credit'] = equity[0]['credit'] - auth[0]['credit']
    #     res['balance'] = equity[0]['balance'] - auth[0]['balance']
    #     res['type_id'] = equity[0]['type_id']
    #     res['type_name'] = equity[0]['type_name']
    #     result.append(res)
        return result

    def _get_total(self,acc_type):
        result = []
        res={}
        res['debit'] = 0
        res['credit'] = 0
        res['balance'] = 0
        res['type_id'] = '0000001'
        res['type_name'] = 'Current Year Earnings'
        for res_type in acc_type:
            res['debit'] += res_type['debit']
            res['credit'] += res_type['credit']
            res['balance'] += res_type['balance']
        result.append(res)
        return result

    def _get_accounts(self, accounts, display_account, data):
        account_result = {}
        # Prepare sql query base on selected parameters from wizard
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        tables = tables.replace('"', '')
        if not tables:
            tables = 'account_move_line'
        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())
        filters = " AND ".join(wheres)
        if data['target_move'] == 'posted':
            filters += " AND account_move_line__move_id.state = 'posted'"
        else:
            filters += " AND account_move_line__move_id.state in ('draft','posted')"
        if data.get('date_from'):
            filters += " AND account_move_line.date >= '%s'" % data.get('date_from')
        if data.get('date_to'):
            filters += " AND account_move_line.date <= '%s'" % data.get('date_to')
        # compute the balance, debit and credit for the provided accounts
        request = (
                    "SELECT account_id AS id, SUM(debit) AS debit, SUM(credit) AS credit, (SUM(debit) - SUM(credit)) AS balance" + \
                    " FROM " + tables + " WHERE account_id IN %s " + filters + " GROUP BY account_id")
        params = (tuple(accounts.ids),) + tuple(where_params)
        self.env.cr.execute(request, params)

        value_fetch = self.env.cr.dictfetchall()        
        for row in value_fetch:        
            account_result[row.pop('id')] = row
        
        account_res = []
        for account in accounts:
            res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance'])
            currency = account.currency_id and account.currency_id or account.company_id.currency_id
            res['code'] = account.code
            res['name'] = account.name
            res['id'] = account.id
            res['type_id'] = account.user_type_id.id
            res['type_name'] = account.user_type_id.name
            if data.get('date_from'):
                res['Init_balance'] = self.get_init_bal(account, display_account, data)
            if account.id in account_result:
                res['debit'] = account_result[account.id].get('debit')
                res['credit'] = account_result[account.id].get('credit')
                res['balance'] = account_result[account.id].get('balance')
            if display_account == 'all':
                account_res.append(res)
            if display_account == 'not_zero' and not currency.is_zero(
                    res['balance']):
                account_res.append(res)
            if display_account == 'movement' and (
                    not currency.is_zero(res['debit']) or not currency.is_zero(
                    res['credit'])):
                account_res.append(res)
        return account_res

    def _get_accounts_init(self, accounts, display_account, data):
        account_result = {}
        # Prepare sql query base on selected parameters from wizard
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        tables = tables.replace('"', '')
        if not tables:
            tables = 'account_move_line'
        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())
        filters = " AND ".join(wheres)
        if data['target_move'] == 'posted':
            filters += " AND account_move_line__move_id.state = 'posted'"
        else:
            filters += " AND account_move_line__move_id.state in ('draft','posted')"
        if data.get('date_from'):
            filters += " AND account_move_line.date < '%s'" % data.get('date_from')
        
        # compute the balance, debit and credit for the provided accounts
        request = (
                    "SELECT account_id AS id, SUM(debit) AS debit, SUM(credit) AS credit, (SUM(debit) - SUM(credit)) AS balance" + \
                    " FROM " + tables + " WHERE account_id IN %s " + filters + " GROUP BY account_id")
        params = (tuple(accounts.ids),) + tuple(where_params)
        self.env.cr.execute(request, params)

        value_fetch = self.env.cr.dictfetchall()        
        for row in value_fetch:        
            account_result[row.pop('id')] = row
        
        account_res = []
        for account in accounts:
            res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance'])
            currency = account.currency_id and account.currency_id or account.company_id.currency_id
            res['code'] = account.code
            res['name'] = account.name
            res['id'] = account.id
            res['type_id'] = account.user_type_id.id
            res['type_name'] = account.user_type_id.name
            if data.get('date_from'):
                res['Init_balance'] = self.get_init_bal(account, display_account, data)
            if account.id in account_result:
                res['debit'] = account_result[account.id].get('debit')
                res['credit'] = account_result[account.id].get('credit')
                res['balance'] = account_result[account.id].get('balance')
            if display_account == 'all':
                account_res.append(res)
            if display_account == 'not_zero' and not currency.is_zero(
                    res['balance']):
                account_res.append(res)
            if display_account == 'movement' and (
                    not currency.is_zero(res['debit']) or not currency.is_zero(
                    res['credit'])):
                account_res.append(res)
        return account_res
    
    def get_init_bal(self, account, display_account, data):            
        if data.get('date_from'):
            tables, where_clause, where_params = self.env[
                'account.move.line']._query_get()
            tables = tables.replace('"', '')
            if not tables:
                tables = 'account_move_line'
            wheres = [""]
            if where_clause.strip():
                wheres.append(where_clause.strip())
            filters = " AND ".join(wheres)
            if data['target_move'] == 'posted':
                filters += " AND account_move_line__move_id.state = 'posted'"
            else:
                filters += " AND account_move_line__move_id.state in ('draft','posted')"
            if data.get('date_from'):
                filters += " AND account_move_line.date < '%s'" % data.get('date_from')

            # compute the balance, debit and credit for the provided accounts
            request = (
                    "SELECT account_id AS id, SUM(debit) AS debit, SUM(credit) AS credit, (SUM(debit) - SUM(credit)) AS balance" + \
                    " FROM " + tables + " WHERE account_id = %s" % account.id + filters + " GROUP BY account_id")
            params = tuple(where_params)
            self.env.cr.execute(request, params)

            value_fetch = self.env.cr.dictfetchall()           
            for row in value_fetch:
                return row
    
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
                          self.env.company.currency_id.position,
                          lang]
        return currency_array
    
    def _get_account_types(self, accounts, display_account, data, account_types):
        account_type_res = []
        for account in accounts:                        
            res = dict((fn, 0.0) for fn in ['balance'])
            if account['type_name'] in account_types:
                x = list(filter(lambda a: a['type_name'] == account['type_name'], account_type_res))
                if len(x) > 0:
                    x[0]['debit'] += account['debit']
                    x[0]['credit'] += account['credit']
                    x[0]['balance'] += account['balance']
                    if data.get('date_from'):
                        balance = account['Init_balance']
                        if balance != None:
                            if 'Init_balance' not in res:
                                res['Init_balance'] = 0         
                            res['Init_balance'] += balance['balance']
                        else:
                            res['Init_balance'] = balance
                    
                else:
                    res['debit'] = account['debit']
                    res['credit'] = account['credit']
                    res['balance'] = account['balance']
                    res['type_id'] = account['type_id']
                    res['type_name'] = account['type_name']

                    if data.get('date_from'):
                        balance = account['Init_balance']
                        if balance != None:
                            res['Init_balance'] = {'debit' : balance['debit'],
                                                   'credit' : balance['credit'],
                                                   'balance' : balance['balance'],}
                        else:
                            res['Init_balance'] = balance
                    account_type_res.append(res)
        if len(account_type_res)==0:
            res = {}
            res['debit'] = 0
            res['credit'] = 0
            res['balance'] = 0
            res['type_id'] = '0000001'
            res['type_name'] = 'null'
            account_type_res.append(res)

        for acc in account_type_res:
            acc['balance'] = -acc['balance'] 
            
        return account_type_res
    
    @api.model
    def create(self, vals):
        vals['target_move'] = 'posted'
        res = super(EquityMoveView, self).create(vals)
        return res

    def write(self, vals):
        if vals.get('target_move'):
            vals.update({'target_move': vals.get('target_move').lower()})
        res = super(EquityMoveView, self).write(vals)
        return res
    
    def get_dynamic_xlsx_report(self, data, response ,report_data, dfr_data):
        report_data_main = json.loads(report_data)
        output = io.BytesIO()
        total = json.loads(dfr_data)
        filters = json.loads(data)
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        head = workbook.add_format({'bold': True})
        sub_heading = workbook.add_format({'bold': True, 'border': 1, 'border_color': 'black'})
        txt = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        txt_l = workbook.add_format({'border': 1, 'bold': True, 'num_format': '#,##0.00'})
        sheet.merge_range('A1:D3', filters.get('company_name') + ':' + ' Equity Movement Report', head)
        date_head = workbook.add_format({'bold': True})
        date_style = workbook.add_format({})
        if filters.get('date_from'):
            sheet.merge_range('A4:B4', 'From: '+filters.get('date_from') , date_head)
        if filters.get('date_to'):
            sheet.merge_range('C4:D4', 'To: '+ filters.get('date_to'), date_head)
        sheet.merge_range('A5:D5', 'Target Moves: '+ filters.get('target_move'), date_head)        
        sheet.write('A7', 'Account', sub_heading)
        sheet.write('B7', 'Debit', sub_heading)
        sheet.write('C7', 'Credit', sub_heading)
        sheet.write('D7', 'Balance', sub_heading)

        row = 6
        col = 0
        sheet.set_column('A:A', 40, '')
        sheet.set_column('B:B', 25, '')
        sheet.set_column('C:C', 25, '')
        sheet.set_column('D:D', 25, '')
        sheet.set_column('E:E', 25, '')
            
        for rec_data in report_data_main['account_equity_filtered']:
            row += 1
            sheet.write(row, col, "Authorized capital", txt)
            sheet.write(row, col + 1, rec_data['debit'], txt)
            sheet.write(row, col + 2, rec_data['credit'], txt)
            sheet.write(row, col + 3, rec_data['balance'], txt)
        for rec_data in report_data_main['account_equity']:
            row += 1
            sheet.write(row, col, "Additional paid in capital", txt)
            sheet.write(row, col + 1, rec_data['debit'], txt)
            sheet.write(row, col + 2, rec_data['credit'], txt)
            sheet.write(row, col + 3, rec_data['balance'], txt)
        for rec_data in report_data_main['account_retained_earnings']:
            row += 1
            sheet.write(row, col, "Retained Earning", txt)
            sheet.write(row, col + 1, rec_data['debit'], txt)
            sheet.write(row, col + 2, rec_data['credit'], txt)
            sheet.write(row, col + 3, rec_data['balance'], txt)
        for rec_data in report_data_main['account_current_earnings']:
            row += 1
            sheet.write(row, col, "Profit & Loss", txt)
            sheet.write(row, col + 1, rec_data['debit'], txt)
            sheet.write(row, col + 2, rec_data['credit'], txt)
            sheet.write(row, col + 3, rec_data['balance'], txt)
        for rec_data in report_data_main['account_prive']:
            row += 1
            sheet.write(row, col, "Prive", txt)
            sheet.write(row, col + 1, rec_data['debit'], txt)
            sheet.write(row, col + 2, rec_data['credit'], txt)
            sheet.write(row, col + 3, rec_data['balance'], txt)
            
        sheet.write(row + 1, col, 'Total Equity', sub_heading)
        sheet.write(row + 1, col + 1, total.get('debit_total'), txt_l)
        sheet.write(row + 1, col + 2, total.get('credit_total'), txt_l)
        sheet.write(row + 1, col + 3, total.get('balance_total'), txt_l)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()