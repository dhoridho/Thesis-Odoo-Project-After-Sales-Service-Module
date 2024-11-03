import time
from odoo import fields, models, api, _

import io
import json
from odoo.exceptions import AccessError, UserError, AccessDenied
import datetime
from dateutil.relativedelta import relativedelta

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter

class AccountTrialBalance(models.TransientModel):
    _inherit = 'account.trial.balance'

    consolidate = fields.Selection(
        [('off', 'Consolidate OFF'), ('on', 'Consolidate On')],
        string='Consolidate', required=True, default='off')
    all_account = fields.Selection([('off', 'OFF'), ('on', 'ON')], string='show all Account', required=True, default='off')

    @api.model
    def view_report(self, option, **kw):
        result = super(AccountTrialBalance, self).view_report(option)
        r = self.env['account.trial.balance'].search([('id', '=', option[0])])
        data = {
            'display_account': r.display_account,
            'model':self,
            'journals': r.journal_ids,
            'target_move': r.target_move,
            'consolidate': r.consolidate,
            'all_account': r.all_account,
        }
        if r.date_from:
            data.update({
                'date_from':r.date_from,
            })
        else:
            data.update({
                'date_from': datetime.datetime.now().replace(day=1),
            })
        if r.date_to:
            data.update({
                'date_to':r.date_to,
            })
        else:
            data.update({
                'date_to': datetime.datetime.now() + relativedelta(day=31),
            })
        records = self._get_report_values(data)

        sort = kw.get('sort')
        sort_type = kw.get('sort_type')
        if sort:
            if sort_type == 'desc':
                records['Accounts'] = sorted(records['Accounts'], key=lambda d: d[sort], reverse=True)
            else:
                records['Accounts'] = sorted(records['Accounts'], key=lambda d: d[sort])
        
        result.update({'opening_debit_total'    : records['opening_debit_total'],
                        'opening_credit_total' : records['opening_credit_total'],
                        'ending_debit_total'   : records['ending_debit_total'],
                        'ending_credit_total'  : records['ending_credit_total'],
                        'ending_balance_total'  : records['ending_balance_total'],
                        'ending_balance_debit_total'  : records['ending_balance_debit_total'],
                        'ending_balance_credit_total'  : records['ending_balance_credit_total'],
                        'report_lines' : records['Accounts'],
                        "debit_total":records['debit_total'],
                        "credit_total":records['credit_total']
                        })
        return result

    def _get_report_values(self, data):
        docs = data['model']
        display_account = data['display_account']
        journals = data['journals']
        list_company=[]
        if 'consolidate' in data:
            if data['consolidate'] == 'on':
                list_company.append(self.env.company.id)
                arg_list = (tuple(str(self.env.company.id)))
                sql = ('''
                    SELECT child_company_id
                    FROM account_account_map
                    WHERE company_id = %s AND child_company_id IS NOT NULL
                ''')
                self.env.cr.execute(sql, arg_list)
                comp_ids = self.env.cr.dictfetchall()
                for comp_id in comp_ids:
                    context = dict(self.env.context)
                    if comp_id.child_company_id.id in context['allowed_company_ids']:
                        list_company.append(comp_id.child_company_id.id)
            else:
                list_company.append(self.env.company.id)
        else:
            list_company.append(self.env.company.id)

        accounts = self.env['account.account'].search([('company_id', 'in', list_company)])
        if not accounts:
            raise UserError(_("No Accounts Found! Please Add One"))
        account_res = self._get_accounts_consolidate(accounts, display_account, data, list_company)
        debit_total = 0
        debit_total = sum(x['debit'] for x in account_res)
        credit_total = sum(x['credit'] for x in account_res)
        opening_debit_total = opening_credit_total = 0.00
        ending_debit_total = ending_credit_total = ending_balance_total = ending_balance_debit_total = ending_balance_credit_total = 0.00
        for res in account_res:
            init_balance = res.get('Init_balance',{})
            if init_balance:
                opening_debit_total += init_balance.get('debit',0.00)
                opening_credit_total += init_balance.get('credit',0.00)
            ending_debit_total += res.get('ending_debit')
            ending_credit_total += res.get('ending_credit')
            ending_balance_total += (res.get('ending_debit') - res.get('ending_credit'))
            ending_balance_debit_total += (res.get('ending_debit') - res.get('ending_credit')) if (res.get('ending_debit') - res.get('ending_credit')) > 0 else 0
            ending_balance_credit_total += (res.get('ending_debit') - res.get('ending_credit')) if (res.get('ending_debit') - res.get('ending_credit')) < 0 else 0

        for acc in accounts:
            check = list(filter(lambda x: x['code'] == acc.code, account_res))
            if not check:
                res={}
                res['credit'] = 0.0
                res['debit'] = 0.0
                res['balance'] = 0.0
                res['code'] = acc.code
                res['name'] = acc.name
                res['id'] = acc.id
                res['ending_debit'] = 0.0
                res['ending_credit'] = 0.0
                res['ending_balance'] = 0.0
                res['ending_balance_debit'] = 0.0
                res['ending_balance_credit'] = 0.0
                res['opening_debit'] = 0.0
                res['opening_credit'] = 0.0
                account_res.append(res)
        if data.get('all_account') == 'off':
            account_res = list(filter(lambda x: x['opening_debit'] != 0 or x['opening_credit'] != 0 or x['credit'] != 0 or x['debit'] != 0 or x['ending_balance_debit'] != 0 or x['ending_balance_credit'] != 0 , account_res))

        account_res = sorted(account_res, key=lambda d: d['code'])
        return {
            'doc_ids': self.ids,
            'debit_total': debit_total,
            'credit_total': credit_total,
            'docs': docs,
            'time': time,
            'Accounts': account_res,
            'opening_debit_total' : opening_debit_total,
            'opening_credit_total': opening_credit_total,
            'ending_debit_total'  : ending_debit_total,
            'ending_credit_total' : ending_credit_total,
            'ending_balance_total' : ending_balance_total,
            'ending_balance_debit_total' : ending_balance_debit_total,
            'ending_balance_credit_total' : -ending_balance_credit_total,
        }
        return result
    
    def get_filter(self, option):
        result = super(AccountTrialBalance, self).get_filter(option)
        data = self.get_filter_data(option)
        if data.get('consolidate'):
            result.update({'consolidate'  : data.get('consolidate')})
        
        if data.get('all_account'):
            result.update({'all_account'  : data.get('all_account')})
        else:
            result.update({'all_account'  : 'off'})

        return result

    def get_filter_data(self, option):
        result = super(AccountTrialBalance, self).get_filter_data(option)
        r = self.env['account.trial.balance'].search([('id', '=', option[0])])

        result.update({ 'consolidate'  : r.consolidate,
                        'all_account'  : r.all_account,
                      }) 
        return result

    @api.model
    def create(self, vals):
        vals['consolidate'] = 'off'
        vals['all_account'] = 'on'
        res = super(AccountTrialBalance, self).create(vals)
        return res

    def write(self, vals):
        if vals.get('consolidate'):
            vals.update({'consolidate': vals.get('consolidate').lower()})
        if vals.get('all_account'):
            vals.update({'all_account': vals.get('all_account').lower()})
        
        res = super(AccountTrialBalance, self).write(vals)
        return res

    
    def _get_accounts(self, accounts, display_account, data):
        result = super(AccountTrialBalance, self)._get_accounts(accounts, display_account, data)
        for res in result:
            init_balance = res.get('Init_balance',{})
            opening_debit_total = init_balance and init_balance.get('debit',0.00) or 0.00
            opening_credit_total = init_balance and init_balance.get('credit',0.00) or 0.00
            ending_debit_total = (init_balance and init_balance.get('debit',0.00) or 0.00) + res.get('debit', 0.00)
            ending_credit_total = (init_balance and init_balance.get('credit',0.00) or 0.00) + res.get('credit', 0.00)
            ending_balance_total = ending_debit_total - ending_credit_total
            ending_balance_debit_total = ending_debit_total if ending_debit_total > 0 else -ending_debit_total
            ending_balance_credit_total = -ending_credit_total if ending_credit_total < 0 else ending_credit_total
            
            res.update({'ending_debit'  : ending_debit_total,
                        'ending_credit' : ending_credit_total,
                        'ending_balance'  : ending_balance_total,
                        'ending_balance_debit'  : ending_balance_debit_total,
                        'ending_balance_credit'  : ending_balance_credit_total,
                        'opening_debit'  : opening_debit_total,
                        'opening_credit' : opening_credit_total,
                        })
            
        return result

    
    def _get_accounts_consolidate(self, accounts, display_account, data, company_id):
        acc_result=[]
        context = dict(self.env.context)
        context.update({'allowed_company_ids' : company_id})
        self.env.context = context
        comp = self.env['res.company'].search([('id', 'in', company_id)])
        self.env.companies = comp
        for comp in company_id:
            request = ("SELECT id, currency_id, code, name from account_account where company_id = " + str(comp) + " order by code ASC")
            self.env.cr.execute(request)
            rec_report = self.env.cr.dictfetchall()
            account_result = {}
            # Prepare sql query base on selected parameters from wizard       
            tables, where_clause, where_params = self.env['account.move.line']._query_get()
            # replace first value
            where_params[0] = comp
            if where_params[len(where_params)-1] == where_params[0]:
                where_params[len(where_params)-1] = comp
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
                filters += " AND account_move_line__move_id.date >= '%s'" % data.get('date_from')
            if data.get('date_to'):
                filters += " AND account_move_line__move_id.date <= '%s'" % data.get('date_to')

            if 'consolidate' in data:
                if data['consolidate'] == 'on':
                    # filters += " AND (m.is_intercompany_transaction = 'false' or m.is_intercompany_transaction isnull) "
                    filters += " AND (account_move_line__move_id.is_intercompany_transaction = 'false') "

            if data['journals']:
                if 'consolidate' in data:
                    if data['consolidate'] != 'on':
                        filters += ' AND jrnl.id IN %s' % str(tuple(data['journals'].ids) + tuple([0]))
                else: 
                   filters += ' AND jrnl.id IN %s' % str(tuple(data['journals'].ids) + tuple([0]))
            tables += 'JOIN account_journal jrnl ON (account_move_line__move_id.journal_id=jrnl.id)'
            # compute the balance, debit and credit for the provided accounts
            request = (
                        "SELECT account_id AS id, SUM(debit) AS debit, SUM(credit) AS credit, (SUM(debit) - SUM(credit)) AS balance" + \
                        " FROM " + tables + " WHERE account_id IN %s " + filters + " GROUP BY account_id")
            params = (tuple(acc_id['id'] for acc_id in rec_report),) + tuple(where_params)
            self.env.cr.execute(request, params)
            for row in self.env.cr.dictfetchall():
                account_result[row.pop('id')] = row

            account_res = []
            for account in rec_report:
                res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance'])
                currency_id = self.env['res.currency'].search([('id', '=', account['currency_id'])])
                currency = currency_id and currency_id or self.env['res.company'].search([('id', '=', comp)]).currency_id
                res['code'] = account['code']
                res['name'] = account['name']
                res['id'] = account['id']
                if data.get('date_from'):
                    res['Init_balance'] = self.get_init_bal_consolidate(account, display_account, data, comp)
                if account['id'] in account_result:
                    res['debit'] = account_result[account['id']].get('debit')
                    res['credit'] = account_result[account['id']].get('credit')
                    res['balance'] = account_result[account['id']].get('balance')
                if display_account == 'all':
                    account_res.append(res)
                if display_account == 'not_zero' and not currency.is_zero(res['balance']):
                    account_res.append(res)
                # if display_account == 'movement' and (not currency.is_zero(res['debit']) or not currency.is_zero(res['credit'])    ):
                if display_account == 'movement':
                    account_res.append(res)

            for res in account_res:
                init_balance = res.get('Init_balance',{})
                opening_debit_total = init_balance and init_balance.get('debit',0.00) or 0.00
                opening_credit_total = init_balance and init_balance.get('credit',0.00) or 0.00
                ending_debit_total = (init_balance and init_balance.get('debit',0.00) or 0.00) + res.get('debit', 0.00)
                ending_credit_total = (init_balance and init_balance.get('credit',0.00) or 0.00) + res.get('credit', 0.00)
                ending_balance_total = ending_debit_total - ending_credit_total
                ending_balance_debit_total = ending_debit_total if ending_debit_total > 0 else -ending_debit_total
                ending_balance_credit_total = -ending_credit_total if ending_credit_total < 0 else ending_credit_total
                
                res.update({'ending_debit'          : ending_debit_total,
                            'ending_credit'         : ending_credit_total,
                            'ending_balance'        : ending_balance_total,
                            'ending_balance_debit'  : ending_balance_debit_total,
                            'ending_balance_credit' : ending_balance_credit_total,
                            'opening_debit'         : opening_debit_total,
                            'opening_credit'        : opening_credit_total,
                            })
            arg_list = (tuple(str(self.env.company.id)), tuple(str(comp)))
            sql = ('''
                SELECT
                    id,
                    ownership
                FROM account_account_map
                WHERE company_id = %s AND child_company_id = %s
            ''')
            self.env.cr.execute(sql, arg_list)
            comp_ids = self.env.cr.dictfetchall()

            for comp_id in comp_ids:
                child_line = self.env['account.account.map.line'].search([('map_id', '=', comp_id['id'])])
                for acc_res in account_res:
                    parent = list(filter(lambda x: x['target_account'].code == acc_res['code'], child_line))
                    if parent:
                        if parent[0].account_id:
                            acc_res['code'] = parent[0].account_id.code
                            acc_res['name'] = parent[0].account_id.name
                            acc_res["credit"] = acc_res["credit"] * (comp_id['ownership'] / 100)
                            acc_res["debit"] = acc_res["debit"] * (comp_id['ownership'] / 100)
                            acc_res["balance"] = acc_res["balance"] * (comp_id['ownership'] / 100)
                            acc_res["ending_debit"] = acc_res["ending_debit"] * (comp_id['ownership'] / 100)
                            acc_res["ending_credit"] = acc_res["ending_credit"] * (comp_id['ownership'] / 100)
                            acc_res["ending_balance"] = acc_res["ending_balance"] * (comp_id['ownership'] / 100)
                            acc_res["ending_balance_debit"] = acc_res["ending_balance_debit"] * (comp_id['ownership'] / 100)
                            acc_res["ending_balance_credit"] = acc_res["ending_balance_credit"] * (comp_id['ownership'] / 100)
                            acc_res["opening_debit"] = acc_res["opening_debit"] * (comp_id['ownership'] / 100)
                            acc_res["opening_credit"] = acc_res["opening_credit"] * (comp_id['ownership'] / 100)
                            if 'Init_balance' in acc_res:
                                if acc_res['Init_balance'] == None:
                                    continue
                                (acc_res['Init_balance'])['debit'] = (acc_res['Init_balance'])['debit'] * (comp_id['ownership'] / 100)
                                (acc_res['Init_balance'])['credit'] = (acc_res['Init_balance'])['credit'] * (comp_id['ownership'] / 100)
                                (acc_res['Init_balance'])['balance'] = (acc_res['Init_balance'])['balance'] * (comp_id['ownership'] / 100)
                        else:
                            account_res = list(filter(lambda i: i != acc_res, account_res))
                    else:
                        account_res = list(filter(lambda i: i != acc_res, account_res))


            acc_result.append(account_res)
        result = acc_result[0]
        if len(acc_result) > 1:
            i = 1
            while i < len(acc_result):
                for tmp_res in acc_result[i]:
                    code_acc = list(filter(lambda x: x['code'] == tmp_res['code'], result))
                    if code_acc:
                        code_acc[0]['credit'] += tmp_res['credit']
                        code_acc[0]['debit'] += tmp_res['debit']
                        code_acc[0]['balance'] += tmp_res['balance']
                        code_acc[0]['ending_debit'] += tmp_res['ending_debit']
                        code_acc[0]['ending_credit'] += tmp_res['ending_credit']
                        code_acc[0]['ending_balance'] += tmp_res['ending_balance']
                        code_acc[0]['ending_balance_debit'] += tmp_res['ending_balance_debit']
                        code_acc[0]['ending_balance_credit'] += tmp_res['ending_balance_credit']
                        code_acc[0]['opening_debit'] += tmp_res['opening_debit']
                        code_acc[0]['opening_credit'] += tmp_res['opening_credit']
                        if 'Init_balance' in code_acc[0]:
                            if code_acc[0]['Init_balance'] == None:
                                continue
                            if tmp_res['Init_balance'] == None:
                                tmp_debit = 0
                                tmp_credit = 0
                                tmp_balance = 0
                            else:
                                tmp_debit = (tmp_res['Init_balance'])['debit']
                                tmp_credit =(tmp_res['Init_balance'])['credit']
                                tmp_balance = (tmp_res['Init_balance'])['balance']

                            (code_acc[0]['Init_balance'])['debit'] += tmp_debit
                            (code_acc[0]['Init_balance'])['credit'] += tmp_credit
                            (code_acc[0]['Init_balance'])['balance'] += tmp_balance
                    else:
                        res_update={}
                        res_update['credit'] = tmp_res['credit']
                        res_update['debit'] = tmp_res['debit']
                        res_update['balance'] = tmp_res['balance']
                        res_update['code'] = tmp_res['code']
                        res_update['name'] = tmp_res['name']
                        res_update['id'] = tmp_res['id']
                        res_update['ending_debit'] = tmp_res['ending_debit']
                        res_update['ending_credit'] = tmp_res['ending_credit']
                        res_update['ending_balance'] = tmp_res['ending_balance']
                        res_update['ending_balance_debit'] = tmp_res['ending_balance_debit']
                        res_update['ending_balance_credit'] = tmp_res['ending_balance_credit']
                        res_update['opening_debit'] = tmp_res['opening_debit']
                        res_update['opening_credit'] = tmp_res['opening_credit']
                        if 'Init_balance' in tmp_res:
                            res_update['Init_balance'] = tmp_res['Init_balance']
                        result.append(res_update)
                i += 1
        return result

    def get_init_bal_consolidate(self, account, display_account, data, company_id):
        if data.get('date_from'):
            tables, where_clause, where_params = self.env[
                'account.move.line']._query_get()
            where_params[0] = company_id
            if where_params[len(where_params)-1] == where_params[0]:
                where_params[len(where_params)-1] = company_id
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
                filters += " AND account_move_line__move_id.date < '%s'" % data.get('date_from')
            
            if 'consolidate' in data:
                if data['consolidate'] == 'on':
                    # filters += " AND (m.is_intercompany_transaction = 'false' or m.is_intercompany_transaction isnull) "
                    filters += " AND (account_move_line__move_id.is_intercompany_transaction = 'false') "

            if data['journals']:
                if 'consolidate' in data:
                    if data['consolidate'] != 'on':
                        filters += ' AND jrnl.id IN %s' % str(tuple(data['journals'].ids) + tuple([0]))
                else:
                    filters += ' AND jrnl.id IN %s' % str(tuple(data['journals'].ids) + tuple([0]))
            tables += 'JOIN account_journal jrnl ON (account_move_line__move_id.journal_id=jrnl.id)'

            # compute the balance, debit and credit for the provided accounts
            request = (
                    "SELECT account_id AS id, SUM(debit) AS debit, SUM(credit) AS credit, (SUM(debit) - SUM(credit)) AS balance" + \
                    " FROM " + tables + " WHERE account_id = %s" % account['id'] + filters + " GROUP BY account_id")
            params = tuple(where_params)
            self.env.cr.execute(request, params)
            for row in self.env.cr.dictfetchall():
                return row


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
                filters += " AND account_move_line__move_id.date < '%s'" % data.get('date_from')

            if 'consolidate' in data:
                if data['consolidate'] == 'on':
                    # filters += " AND (m.is_intercompany_transaction = 'false' or m.is_intercompany_transaction isnull) "
                    filters += " AND (account_move_line__move_id.is_intercompany_transaction = 'false') "

            if data['journals']:
                filters += ' AND jrnl.id IN %s' % str(tuple(data['journals'].ids) + tuple([0]))
            tables += 'JOIN account_journal jrnl ON (account_move_line__move_id.journal_id=jrnl.id)'

            # compute the balance, debit and credit for the provided accounts
            request = (
                    "SELECT account_id AS id, SUM(debit) AS debit, SUM(credit) AS credit, (SUM(debit) - SUM(credit)) AS balance" + \
                    " FROM " + tables + " WHERE account_id = %s" % account.id + filters + " GROUP BY account_id")
            params = tuple(where_params)
            self.env.cr.execute(request, params)
            for row in self.env.cr.dictfetchall():
                return row
    
    
    
    def get_dynamic_xlsx_report(self, data, response ,report_data, dfr_data):
        report_data_main = json.loads(report_data)
        output = io.BytesIO()
        total = json.loads(dfr_data)
        filters = json.loads(data)
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        head = workbook.add_format({'align': 'center', 'bold': True})
        sub_heading = workbook.add_format({'align': 'center', 'bold': True, 'border': 1, 'border_color': 'black'})
        txt = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        txt_l = workbook.add_format({'border': 1, 'bold': True, 'num_format': '#,##0.00'})
        sheet.merge_range('A2:D3', filters.get('company_name') + ':' + ' Trial Balance', head)
        date_head = workbook.add_format({'align': 'center', 'bold': True})
        date_style = workbook.add_format({'align': 'center'})
        if filters.get('date_from'):
            sheet.merge_range('A4:B4', 'From: '+filters.get('date_from') , date_head)
        if filters.get('date_to'):
            sheet.merge_range('C4:D4', 'To: '+ filters.get('date_to'), date_head)
        sheet.merge_range('A5:D6', 'Journals: ' + ', '.join([ lt or '' for lt in filters['journals'] ]) + '  Target Moves: '+ filters.get('target_move'), date_head)
        sheet.merge_range('A7:A8', 'Code', sub_heading)
        sheet.merge_range('B7:B8', 'Account', sub_heading)
        sheet.merge_range('C7:D7', 'Opening Balance', sub_heading)
        sheet.merge_range('E7:F7', 'Change', sub_heading)
        sheet.merge_range('G7:H7', 'Ending Balance', sub_heading)
        sheet.write('C8', 'Debit', sub_heading)
        sheet.write('D8', 'Credit', sub_heading)
        sheet.write('E8', 'Debit', sub_heading)
        sheet.write('F8', 'Credit', sub_heading)
        sheet.write('G8', 'Debit', sub_heading)
        sheet.write('H8', 'Credit', sub_heading)
        # sheet.write('G8', 'Ending Balance', sub_heading)

        row = 7
        col = 0

        sheet.set_column('A:A', 15, '')
        sheet.set_column('B:B', 35, '')
        sheet.set_column('C:Z', 20, '')

        for rec_data in report_data_main:
            row += 1
            sheet.write(row, col, rec_data['code'], txt)
            sheet.write(row, col + 1, rec_data['name'], txt)
            sheet.write(row, col + 2, rec_data['opening_debit'], txt)
            sheet.write(row, col + 3, rec_data['opening_credit'], txt)
            sheet.write(row, col + 4, rec_data['debit'], txt)
            sheet.write(row, col + 5, rec_data['credit'], txt)
            sheet.write(row, col + 6, rec_data['ending_balance_debit'], txt)
            sheet.write(row, col + 7, rec_data['ending_balance_credit'], txt)
            # sheet.write(row, col + 6, rec_data['ending_balance'], txt)
            
        sheet.merge_range(row + 1, col, row + 1, col+1, 'Total', sub_heading)
        sheet.write(row + 1, col + 2, total.get('opening_debit_total'), txt_l)
        sheet.write(row + 1, col + 3, total.get('opening_credit_total'), txt_l)
        sheet.write(row + 1, col + 4, total.get('debit_total'), txt_l)
        sheet.write(row + 1, col + 5, total.get('credit_total'), txt_l)
        sheet.write(row + 1, col + 6, total.get('ending_balance_debit_total'), txt_l)
        sheet.write(row + 1, col + 7, total.get('ending_balance_credit_total'), txt_l)
        # sheet.write(row + 1, col + 6, total.get('ending_balance_total'), txt_l)


        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()