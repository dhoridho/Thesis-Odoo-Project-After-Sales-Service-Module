from odoo import fields, models, api, _
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
import datetime
from odoo.exceptions import UserError
import time, json, io
from odoo.exceptions import AccessError, UserError, AccessDenied

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class GeneralView(models.TransientModel):
    _inherit = 'account.general.ledger'

    all_account = fields.Selection([('off', 'OFF'), ('on', 'ON')], string='show all Account', required=True, default='off')
    filter_detail = fields.Selection(
        [('custom', 'custom'),
         ('today', 'Today'), 
         ('this_month', 'This Month'),
         ('this_quarter', 'This Quarter'),
         ('this_financial_year', 'This Year'),
         ('last_month', 'Last Month'),
         ('last_quarter', 'Last Quarter'),
         ('last_year', 'Last Year')],
        string='Filter Detail')
    expand = fields.Boolean(string="Expand", default=False)

    @api.model
    def view_report(self, option, title, show_account_id=False):
        r = self.env['account.general.ledger'].search([('id', '=', option[0])])
        new_title = ''
        ctx = self.env.context
        journals = r.journal_ids
        if title == 'General Ledger':
            journals = r.journal_ids
            new_title = 'General Ledger'
        if title == 'Bank and Cash Book':
            journals = self.env['account.journal'].search([('type', 'in', ['bank','cash'])])
            new_title = 'Bank and Cash Book'
        if title == 'Cash Book':
            journals = self.env['account.journal'].search([('type', '=', 'cash')])
            new_title = 'Cash Book'
        r.write({
            'titles': new_title,
        })
        data = {
            'display_account': r.display_account,
            'model':self,
            'journals': journals,
            'target_move': r.target_move,
            'accounts': r.account_ids,
            'account_tags': r.account_tag_ids,
            'analytics': r.analytic_ids,
            'analytic_tags': r.analytic_tag_ids,
            'titles': new_title,
            'show_account_id' : show_account_id or False,
            'all_account': r.all_account,
            'custom_data': ctx.get('custom_data')

        }
        # if r.date_from:
        #     data.update({
        #         'date_from': r.date_from,
        #     })
        # if r.date_to:
        #     data.update({
        #         'date_to': r.date_to,
        #     })

        if r.date_from:
            data.update({'date_from': r.date_from})
        else:
            data.update({'date_from': date.today().replace(day=1)})

        if r.date_to:
            data.update({'date_to': r.date_to})
        else:
            data.update({'date_to': date.today() + relativedelta(day=31)})

        
        if data.get('show_account_id'):
            acc = self.env['account.account'].browse(show_account_id)
            data.update({
                'accounts': acc,
            })


        filters = self.get_filter(option)
        records = self._get_report_values(data)
        currency = self._get_currency()

        return {
            'name': new_title,
            'type': 'ir.actions.client',
            'tag': 'g_l',
            'filters': filters,
            'report_lines': records['Accounts'],
            'debit_total': records['debit_total'],
            'credit_total': records['credit_total'],
            'debit_balance': records['debit_balance'],
            'currency': currency,
        }

    def get_filter(self, option):
        result = super(GeneralView, self).get_filter(option)
        data = self.get_filter_data(option)
        
        if data.get('all_account'):
            result.update({'all_account'  : data.get('all_account')})
        else:
            result.update({'all_account'  : 'off'})

        return result

    def get_filter_data(self, option):
        result = super(GeneralView, self).get_filter_data(option)
        r = self.env['account.trial.balance'].search([('id', '=', option[0])])

        result.update({ 'all_account'  : r.all_account}) 
        return result

    @api.model
    def create(self, vals):
        vals['all_account'] = 'off'
        vals['expand'] = False
        res = super(GeneralView, self).create(vals)
        return res

    def write(self, vals):
        if vals.get('all_account'):
            vals.update({'all_account': vals.get('all_account').lower()})
        res = super(GeneralView, self).write(vals)
        return res

    def _get_report_values(self, data):
        docs = data['model']
        display_account = data['display_account']
        init_balance = True
        accounts = self.env['account.account'].search([])
        currency = self._get_currency()
        custom_data = data.get('custom_data')
        account_line = {}
        aml_ids = self.env['account.move.line']
        if custom_data:
            account_line = custom_data.get('account_line')
            aml_ids = aml_ids.browse(account_line.get('aml_ids'))

        if data.get('titles') == 'Bank and Cash Book':
            bank_and_cash_account_type_id = self.env.ref('account.data_account_type_liquidity').id
            accounts = self.env['account.account'].search([('user_type_id','=',bank_and_cash_account_type_id)])

        if not accounts:
            raise UserError(_("No Accounts Found! Please Add One"))

        account_res = []

        if custom_data and account_line and aml_ids:
            debit_total = sum(x['debit'] for x in aml_ids)
            credit_total = sum(x['credit'] for x in aml_ids)
        else:
            account_res = self._get_accounts(accounts, init_balance, display_account, data)
            debit_total = sum(x['debit'] for x in account_res)
            credit_total = sum(x['credit'] for x in account_res)
        debit_balance = round(debit_total,2) - round(credit_total,2)

        if custom_data and account_line and aml_ids:
            res = {}
            res['credit'] = credit_total
            res['debit'] = debit_total
            res['balance'] = debit_balance
            res['code'] = account_line.get('code')
            res['name'] = account_line.get('name')
            res['id'] = account_line.get('id')
            res['amount_currency_format'] = "0.00"
            res['amount_currency'] = 0.0
            res['move_lines'] = [
                {
                    "lid" : acc.id,
                    "move_id" : acc.move_id.id,
                    "ldate" : acc.date,
                    "lcode" : acc.journal_id.code,
                    "currency_id" : acc.currency_id.id,
                    "amount_currency" : acc.amount_currency,
                    "lref" : acc.ref,
                    "lname" : acc.name,
                    "debit" : acc.debit,
                    "credit" : acc.credit,
                    "balance" : acc.balance,
                    "move_name" : acc.move_name,
                    "currency_code" : currency[0],
                    "partner_name" : acc.partner_id.name,
                    "m_id" : acc.id
                } for acc in aml_ids
            ]

            account_res.append(res)

        else:
            for acc in accounts:
                if acc.user_type_id.type in ['receivable', 'payable']:
                    continue
                check = list(filter(lambda x: x['code'] == acc.code, account_res))
                if not check:
                    res={}
                    res['credit'] = 0.0
                    res['debit'] = 0.0
                    res['balance'] = 0.0
                    res['code'] = acc.code
                    res['name'] = acc.name
                    res['id'] = acc.id
                    res['amount_currency_format'] = "0.00"
                    res['amount_currency'] = 0.0
                    res['move_lines'] = [
                                            {
                                               "lid" : 0,
                                               "move_id" : 0,
                                               "ldate" : "None",
                                               "lcode" : "",
                                               "currency_id" : self.env.company.currency_id.id,
                                               "amount_currency" : 0.0,
                                               "lref" : "",
                                               "lname" : "",
                                               "debit" : 0.0,
                                               "credit" : 0.0,
                                               "balance" : 0.0,
                                               "move_name" : "",
                                               "currency_code" : currency[0],
                                               "partner_name" : "",
                                               "m_id" : acc.id
                                            }
                                          ]
                    account_res.append(res)
        if data.get('all_account') == 'off':
            account_res = list(filter(lambda x: (x['credit'] != 0 or x['debit'] != 0), account_res))

        account_res = sorted(account_res, key=lambda d: d['code'])

        return {
            'doc_ids': self.ids,
            'debit_total': debit_total,
            'credit_total': credit_total,
            'debit_balance':debit_balance,
            'docs': docs,
            'time': time,
            'Accounts': account_res,
        }

    def _get_accounts(self, accounts, init_balance, display_account, data):
        cr = self.env.cr
        MoveLine = self.env['account.move.line']
        move_lines = {x: [] for x in accounts.ids}

        # Prepare initial sql query and Get the initial move lines
        if init_balance and data.get('date_from'):
            init_tables, init_where_clause, init_where_params = MoveLine.with_context(
                date_from=self.env.context.get('date_from'), date_to=False,
                initial_bal=True)._query_get()
            init_wheres = [""]
            if init_where_clause.strip():
                init_wheres.append(init_where_clause.strip())
            init_filters = " AND ".join(init_wheres)
            filters = init_filters.replace('account_move_line__move_id',
                                           'm').replace('account_move_line',
                                                        'l')
            new_filter = filters
            if data['target_move'] == 'posted':
                new_filter += " AND m.state = 'posted'"
            else:
                new_filter += " AND m.state in ('draft','posted')"
            if data.get('date_from'):
                new_filter += " AND l.date < '%s'" % data.get('date_from')
            if data['journals']:
                new_filter += ' AND j.id IN %s' % str(tuple(data['journals'].ids) + tuple([0]))
            if data.get('accounts'):
                WHERE = "WHERE l.account_id IN %s" % str(tuple(data.get('accounts').ids) + tuple([0]))
            else:
                WHERE = "WHERE l.account_id IN %s"
            if data.get('analytics'):
                WHERE += ' AND anl.id IN %s' % str(tuple(data.get('analytics').ids) + tuple([0]))
            if data.get('analytic_tags'):
                WHERE += ' AND anltag.account_analytic_tag_id IN %s' % str(
                    tuple(data.get('analytic_tags').ids) + tuple([0]))

            if data.get('analytic_tags') or data.get('analytics'):
                sql = ("""SELECT 0 AS lid, l.account_id AS account_id, '' AS ldate, '' AS lcode, 0.0 AS amount_currency, '' AS lref, 'Initial Balance' AS lname, COALESCE(SUM(l.debit),0.0) AS debit, COALESCE(SUM(l.credit),0.0) AS credit, COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) as balance, '' AS lpartner_id,\
                            '' AS move_name, '' AS mmove_id, '' AS currency_code, '' AS currency_position,\
                            NULL AS currency_id,\
                            '' AS invoice_id, '' AS invoice_type, '' AS invoice_number,\
                            '' AS partner_name\
                            FROM account_move_line l\
                            LEFT JOIN account_move m ON (l.move_id=m.id)\
                            LEFT JOIN res_currency c ON (l.currency_id=c.id)\
                            LEFT JOIN res_partner p ON (l.partner_id=p.id)\
                            LEFT JOIN account_move i ON (m.id =i.id)\
                            LEFT JOIN account_account_tag_account_move_line_rel acc ON (acc.account_move_line_id=l.id)
                            LEFT JOIN account_analytic_account anl ON (l.analytic_account_id=anl.id)
                            LEFT JOIN account_analytic_tag_account_move_line_rel anltag ON (anltag.account_move_line_id=l.id)
                            left JOIN account_journal j ON (l.journal_id=j.id)"""
                            + WHERE + new_filter + ' GROUP BY l.account_id')
            else:
                sql = ("""SELECT 0 AS lid, l.account_id AS account_id, '' AS ldate, '' AS lcode, 0.0 AS amount_currency, '' AS lref, 'Initial Balance' AS lname, COALESCE(SUM(l.debit),0.0) AS debit, COALESCE(SUM(l.credit),0.0) AS credit, COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) as balance, '' AS lpartner_id,\
                            '' AS move_name, '' AS mmove_id, '' AS currency_code, '' AS currency_position,\
                            NULL AS currency_id,\
                            '' AS invoice_id, '' AS invoice_type, '' AS invoice_number,\
                            '' AS partner_name\
                            FROM account_move_line l\
                            LEFT JOIN account_move m ON (l.move_id=m.id)\
                            LEFT JOIN res_currency c ON (l.currency_id=c.id)\
                            LEFT JOIN res_partner p ON (l.partner_id=p.id)\
                            LEFT JOIN account_move i ON (m.id =i.id)\
                            -- LEFT JOIN account_account_tag_account_move_line_rel acc ON (acc.account_move_line_id=l.id)
                            -- LEFT JOIN account_analytic_account anl ON (l.analytic_account_id=anl.id)
                            -- LEFT JOIN account_analytic_tag_account_move_line_rel anltag ON (anltag.account_move_line_id=l.id)
                            left JOIN account_journal j ON (l.journal_id=j.id)"""
                            + WHERE + new_filter + ' GROUP BY l.account_id')
            if data.get('accounts'):
                params = tuple(init_where_params)
            else:
                params = (tuple(accounts.ids),) + tuple(init_where_params)
            cr.execute(sql, params)
            for row in cr.dictfetchall():
                row['m_id'] = row['account_id']
                move_lines[row.pop('account_id')].append(row)

        tables, where_clause, where_params = MoveLine._query_get()
        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())
        final_filters = " AND ".join(wheres)
        final_filters = final_filters.replace('account_move_line__move_id', 'm').replace(
            'account_move_line', 'l')
        new_final_filter = final_filters
        if data['target_move'] == 'posted':
            new_final_filter += " AND m.state = 'posted'"
        else:
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
        if data.get('analytics'):
            WHERE += ' AND anl.id IN %s' % str(tuple(data.get('analytics').ids) + tuple([0]))

        if data.get('analytic_tags'):
            WHERE += ' AND anltag.account_analytic_tag_id IN %s' % str(
                tuple(data.get('analytic_tags').ids) + tuple([0]))

        if data.get('analytic_tags') or data.get('analytics'):
            if data.get('show_account_id'):
                # Get move lines base on sql query and Calculate the total balance of move lines
                sql = ('''SELECT l.id AS lid,m.id AS move_id, l.account_id AS account_id, l.date AS ldate, j.code AS lcode, l.currency_id, l.amount_currency, l.ref AS lref, l.name AS lname, COALESCE(l.debit,0) AS debit, COALESCE(l.credit,0) AS credit, COALESCE(SUM(l.balance),0) AS balance,\
                            m.name AS move_name, c.symbol AS currency_code, c.position AS currency_position, p.name AS partner_name\
                            FROM account_move_line l\
                            JOIN account_move m ON (l.move_id=m.id)\
                            LEFT JOIN res_currency c ON (l.currency_id=c.id)\
                            LEFT JOIN res_partner p ON (l.partner_id=p.id)\
                            LEFT JOIN account_analytic_account anl ON (l.analytic_account_id=anl.id)
                            LEFT JOIN account_account_tag_account_move_line_rel acc ON (acc.account_move_line_id=l.id)
                            LEFT JOIN account_analytic_tag_account_move_line_rel anltag ON (anltag.account_move_line_id=l.id)
                            left JOIN account_journal j ON (l.journal_id=j.id)\
                            JOIN account_account a ON (l.account_id = a.id) '''
                            + WHERE + new_final_filter + ''' GROUP BY l.id, m.id,  l.account_id, l.date, j.code, l.currency_id, l.amount_currency, l.ref, l.name, m.name, c.symbol, c.position, p.name order by ldate ASC''' )
            else:
                sql = ('''SELECT 0 AS lid,0 AS move_id, l.account_id AS account_id, null AS ldate, '' AS lcode, l.currency_id, 0.0 as amount_currency, '' AS lref, '' AS lname, COALESCE(sum(l.debit),0) AS debit, COALESCE(sum(l.credit),0) AS credit, COALESCE(SUM(l.balance),0) AS balance,\
                            '' AS move_name, c.symbol AS currency_code, c.position AS currency_position, '' AS partner_name\
                            FROM account_move_line l\
                            JOIN account_move m ON (l.move_id=m.id)\
                            LEFT JOIN res_currency c ON (l.currency_id=c.id)\
                            LEFT JOIN res_partner p ON (l.partner_id=p.id)\
                            LEFT JOIN account_analytic_account anl ON (l.analytic_account_id=anl.id)
                            LEFT JOIN account_account_tag_account_move_line_rel acc ON (acc.account_move_line_id=l.id)
                            LEFT JOIN account_analytic_tag_account_move_line_rel anltag ON (anltag.account_move_line_id=l.id)
                            left JOIN account_journal j ON (l.journal_id=j.id)\
                            JOIN account_account a ON (l.account_id = a.id) '''
                            + WHERE + new_final_filter + ''' GROUP BY l.account_id, l.currency_id, c.symbol, c.position''' )
        else:
            if data.get('show_account_id'):
                # Get move lines base on sql query and Calculate the total balance of move lines
                sql = ('''SELECT l.id AS lid,m.id AS move_id, l.account_id AS account_id, l.date AS ldate, j.code AS lcode, l.currency_id, l.amount_currency, l.ref AS lref, l.name AS lname, COALESCE(l.debit,0) AS debit, COALESCE(l.credit,0) AS credit, COALESCE(SUM(l.balance),0) AS balance,\
                            m.name AS move_name, c.symbol AS currency_code, c.position AS currency_position, p.name AS partner_name\
                            FROM account_move_line l\
                            JOIN account_move m ON (l.move_id=m.id)\
                            LEFT JOIN res_currency c ON (l.currency_id=c.id)\
                            LEFT JOIN res_partner p ON (l.partner_id=p.id)\
                            -- LEFT JOIN account_analytic_account anl ON (l.analytic_account_id=anl.id)
                            -- LEFT JOIN account_account_tag_account_move_line_rel acc ON (acc.account_move_line_id=l.id)
                            -- LEFT JOIN account_analytic_tag_account_move_line_rel anltag ON (anltag.account_move_line_id=l.id)
                            left JOIN account_journal j ON (l.journal_id=j.id)\
                            JOIN account_account a ON (l.account_id = a.id) '''
                            + WHERE + new_final_filter + ''' GROUP BY l.id, m.id,  l.account_id, l.date, j.code, l.currency_id, l.amount_currency, l.ref, l.name, m.name, c.symbol, c.position, p.name order by ldate ASC''' )
            else:
                sql = ('''SELECT 0 AS lid,0 AS move_id, l.account_id AS account_id, null AS ldate, '' AS lcode, l.currency_id, 0.0 as amount_currency, '' AS lref, '' AS lname, COALESCE(sum(l.debit),0) AS debit, COALESCE(sum(l.credit),0) AS credit, COALESCE(SUM(l.balance),0) AS balance,\
                            '' AS move_name, c.symbol AS currency_code, c.position AS currency_position, '' AS partner_name\
                            FROM account_move_line l\
                            JOIN account_move m ON (l.move_id=m.id)\
                            LEFT JOIN res_currency c ON (l.currency_id=c.id)\
                            LEFT JOIN res_partner p ON (l.partner_id=p.id)\
                            -- LEFT JOIN account_analytic_account anl ON (l.analytic_account_id=anl.id)
                            -- LEFT JOIN account_account_tag_account_move_line_rel acc ON (acc.account_move_line_id=l.id)
                            -- LEFT JOIN account_analytic_tag_account_move_line_rel anltag ON (anltag.account_move_line_id=l.id)
                            left JOIN account_journal j ON (l.journal_id=j.id)\
                            JOIN account_account a ON (l.account_id = a.id) '''
                            + WHERE + new_final_filter + ''' GROUP BY l.account_id, l.currency_id, c.symbol, c.position''' )
        if data.get('accounts'):
            params = tuple(where_params)
        else:
            params = (tuple(accounts.ids),) + tuple(where_params)
        cr.execute(sql, params)
        cek = cr.dictfetchall()
        
        for row in cek:
            balance = 0
            # balance = sum(list(map(lambda y: round(y['debit'],2) - round(y['credit'],2), move_lines.get(row['account_id']))))
            # row['balance'] += round(balance,2)
            row['m_id'] = row['account_id']
            move_lines[row.pop('account_id')].append(row)

        # Calculate the debit, credit and balance for Accounts
        account_res = []
        # company_curr = self._get_currency()
        for account in accounts:
            currency = account.currency_id and account.currency_id or account.company_id.currency_id
            res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance'])
            res['code'] = account.code
            res['name'] = account.name
            res['id'] = account.id
            res['move_lines'] = move_lines[account.id]
            debit = sum(list(map(lambda y: round(y['debit'],2),res.get('move_lines'))))
            credit = sum(list(map(lambda y: round(y['credit'],2), res.get('move_lines'))))
            balance = sum(list(map(lambda y: round(y['debit'],2) - round(y['credit'],2), res.get('move_lines'))))
            res['debit'] += round(debit,2)
            res['credit'] += round(credit,2)
            res['balance'] += round(balance,2)
            if display_account == 'all':
                account_res.append(res)
            if display_account == 'movement' and res.get('move_lines'):
                account_res.append(res)
            if display_account == 'not_zero' and not currency.is_zero(
                    res['balance']):
                account_res.append(res)
        return account_res

    def get_alfabet(self, value):
        alfabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if value:
            return alfabet[value]
        return False

    def get_dynamic_xlsx_report(self, data, response ,report_data, dfr_data):
        report_data_main = json.loads(report_data)
        output = io.BytesIO()
        name_data = json.loads(dfr_data)
        filters = json.loads(data)
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        head = workbook.add_format({'bold': True})
        sub_heading = workbook.add_format({'bold': True, 'border': 1, 'border_color': 'black', 'num_format': '#,##0.00'})
        txt = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        txt_num = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        txt_l = workbook.add_format({'border': 1, 'bold': True})
        txt_l_num = workbook.add_format({'border': 1, 'bold': True, 'num_format': '#,##0.00'})
        sheet.merge_range('A2:J3', filters.get('company_name') + ':' + name_data.get('name'), head)
        date_head = workbook.add_format({'bold': True})
        date_style = workbook.add_format({})
        if filters.get('date_from'):
            sheet.merge_range('B4:C4', 'From: ' + filters.get('date_from'), date_head)
        if filters.get('date_to'):
            sheet.merge_range('H4:I4', 'To: ' + filters.get('date_to'), date_head)
        # sheet.merge_range('A5:J6', 'Journals: ' + ', '.join(
        #     [lt or '' for lt in filters['journals']]) + '  Target Moves: ' + filters.get('target_move'), date_head)

        sheet.merge_range('A5:J6', '  Journals: ' + ', '.join(
            [lt or '' for lt in
             filters['journals']]) + '  Accounts: ' + ', '.join(
            [lt or '' for lt in
             filters['accounts']]) + '  Account Tags: ' + ', '.join(
            [lt or '' for lt in
             filters['analytic_tags']]) + '  Analytic: ' + ', '.join(
            [at or '' for at in
             filters['analytics']]) + '  Target Moves : ' + filters.get('target_move'),
                          date_head)


        sheet.write('A8', 'Code', sub_heading)
        sheet.merge_range('B8:E8', 'Name', sub_heading)
        sheet.write('F8', 'Debit', sub_heading)
        sheet.write('G8', 'Credit', sub_heading)
        sheet.write('H8', 'Balance', sub_heading)

        row = 6
        col = 0
        sheet.set_column('A:A', 15, '')
        sheet.set_column('B:B', 15, '')
        sheet.set_column('C:C', 20, '')
        sheet.set_column('D:D', 20, '')
        sheet.set_column('E:E', 50, '')
        sheet.set_column('F:F', 20, '')
        sheet.set_column('G:G', 20, '')
        sheet.set_column('H:H', 20, '')
        sheet.set_column('I:I', 20, '')

        for rec_data in report_data_main:
            row += 1
            sheet.write(row + 1, col, rec_data['code'], sub_heading if filters.get('expand') else txt)
            rowcol = 'B'+str(row + 2)+':'+self.get_alfabet(col+4)+str(row + 2)
            sheet.merge_range(rowcol, rec_data['name'], sub_heading if filters.get('expand') else txt)
            sheet.write(row + 1, col + 5, rec_data['debit'], sub_heading if filters.get('expand') else txt)
            sheet.write(row + 1, col + 6, rec_data['credit'], sub_heading if filters.get('expand') else txt)
            sheet.write(row + 1, col + 7, rec_data['balance'], sub_heading if filters.get('expand') else txt)
            
            if len(rec_data['move_lines']) > 0:
                row += 1
                sheet.write(row + 1, col, "Date", sub_heading)
                sheet.write(row + 1, col + 1, "Journal", sub_heading)
                sheet.write(row + 1, col + 2, "Partner", sub_heading)
                sheet.write(row + 1, col + 3, "Move", sub_heading)
                sheet.write(row + 1, col + 4, "Entry Label", sub_heading)
                sheet.write(row + 1, col + 5, "Debit", sub_heading)
                sheet.write(row + 1, col + 6, "Credit", sub_heading)
                sheet.write(row + 1, col + 7, "Balance", sub_heading)
            for line_data in rec_data['move_lines']:
                row += 1
                sheet.write(row + 1, col, line_data.get('ldate'), txt)
                sheet.write(row + 1, col + 1, line_data.get('lcode'), txt)
                sheet.write(row + 1, col + 2, line_data.get('partner_name'), txt)
                sheet.write(row + 1, col + 3, line_data.get('move_name'), txt)
                sheet.write(row + 1, col + 4, line_data.get('lname'), txt)
                sheet.write(row + 1, col + 5, line_data.get('debit'), txt_num)
                sheet.write(row + 1, col + 6, line_data.get('credit'), txt_num)
                sheet.write(row + 1, col + 7, line_data.get('balance'), txt_num)



        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()