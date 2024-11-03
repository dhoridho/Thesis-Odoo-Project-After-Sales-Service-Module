import re
from odoo import models, fields, api
import ast

class BalanceSheet(models.TransientModel):
    _inherit = "ctm.dynamic.balance.sheet.report"

    def view_report_pdf(self, acc, form):
        data = dict()
        report_lines = acc
        data['form'] = form

        # find the journal items of these accounts
        # journal_items = self.find_journal_items(report_lines, data['form'])

        def set_report_level(rec):
            """This function is used to set the level of each item.
            This level will be used to set the alignment in the dynamic reports."""

            level = 1
            if not rec['parent']:
                return level
            else:
                for line in report_lines:
                    key = 'a_id' if line['type'] == 'account' else 'id'
                    if line[key] == rec['parent']:
                        return level + set_report_level(line)

        # finding the root
        for item in report_lines:
            item['balance'] = round(item['balance'], 2)
            if not item['parent']:
                item['level'] = 1
                parent = item
                report_name = item['name']
                item_id = item['id']
                report_id = item['r_id']
            else:
                item['level'] = set_report_level(item)
        # data['journal_items'] = journal_items
        data['report_lines'] = report_lines
        return data

    def _compute_account_balance(self, accounts):
        """ compute the balance, debit
        and credit for the provided accounts
        """

        mapp = {
            'balance': "COALESCE(SUM(account_move_line.balance), 0) as balance",
            'debit': "COALESCE(SUM(account_move_line.debit), 0) as debit",
            'credit': "COALESCE(SUM(account_move_line.credit), 0) as credit",
        }

        mapp_analytic = {
            'balance':
                "COALESCE(SUM((anldis.percentage/100) * account_move_line.debit),0) - COALESCE(SUM((anldis.percentage/100) * account_move_line.credit), 0)"
                " as balance",
            'debit': "COALESCE(SUM((anldis.percentage/100) * account_move_line.debit), 0) as debit",
            'credit': "COALESCE(SUM((anldis.percentage/100) * account_move_line.credit), 0) as credit",
        }

        ctx = self.env.context
        if 'analytic_ids' in ctx or 'analytic_tag_ids' in ctx or 'analytic_group_ids' in ctx:
            mapping = mapp_analytic
            join_analytic =   " left join account_analytic_tag_account_move_line_rel as anltagrel ON (anltagrel.account_move_line_id = account_move_line.id) "\
                            + " left join account_analytic_tag as anltag ON (anltagrel.account_analytic_tag_id = anltag.id) "\
                            + " left join account_analytic_distribution as anldis ON (anltag.id = anldis.tag_id) "\
                            + " left join account_analytic_group as anlgroup ON (anldis.analytic_group_id = anlgroup.id) "\
                            + " left join account_analytic_account as anlacc ON  (anldis.account_id = anlacc.id) "
        else:
            mapping = mapp
            join_analytic = " "

        res = {}
        for account in accounts:
            res[account.id] = dict((fn, 0.0)for fn in mapping.keys())
        if accounts:
            tables, where_clause, where_params = (self.env['account.move.line']._query_get())
            tables = tables.replace(
                '"', '') if tables else "account_move_line"
            tables
            wheres = [""]
            if where_clause.strip():
                wheres.append(where_clause.strip())
            filters = " AND ".join(wheres)
            filters = filters.replace('account_move_line__move_id','am').replace('account_move_line', 'account_move_line')
            # filters = filters.replace('account_analytic_tag_aml_rel', 'account_analytic_tag_account_move_line_rel')
            if 'all_account' in ctx:
                if ctx['all_account'] == 'off':
                    if 'analytic_ids' in ctx:
                        if ctx['analytic_ids']:
                            filters += ' AND anlacc.id IN %s ' % str(tuple(ctx['analytic_ids'].ids) + tuple([0]))
                    if 'analytic_tag_ids' in ctx:
                        if ctx['analytic_tag_ids']:
                            filters += ' AND anltag.id IN %s ' % str(tuple(ctx['analytic_tag_ids'].ids) + tuple([0]))
                    # if 'analytic_group_ids' in ctx:
                    #     if ctx['analytic_group_ids']:
                    #         filters += ' AND anlgroup.id IN %s ' % str(tuple(ctx['analytic_group_ids'].ids) + tuple([0]))
                    filters = filters.replace('account_analytic_tag_aml_rel', 'account_analytic_tag_account_move_line_rel')
            if 'consolidate' in ctx:
                if ctx['consolidate'] == 'on':
                    filters += " AND am.is_intercompany_transaction = 'false' "
        
            request = ("SELECT account_move_line.account_id as id, " 
                       + ', '.join(mapping.values()) 
                       + " from account_move_line account_move_line "
                       + " join account_move am on (account_move_line.move_id=am.id) "
                       + " join account_account as acc on (acc.id = account_move_line.account_id) "
                       + join_analytic
                       + " WHERE account_move_line.account_id IN %s "
                       + filters
                       + " GROUP BY account_move_line.account_id")

            params = (tuple(accounts._ids),) + tuple(where_params)
            self.env.cr.execute(request, params)
            for row in self.env.cr.dictfetchall():
                res[row['id']] = row
        return res

    def _add_account_from_domain(self,domain):
        domain = ast.literal_eval(domain)
        accounts = self.env['account.account'].search(domain)
        return accounts

    def _get_financial_report_by_code(self, code):
        report_id = self.env['account.financial.report'].search([('code', '=', code)])
        return report_id

    def _split_formulas(self,formulas):
        result=[]
        formula = re.split("\-|\+|\/|\*",formulas)
        for f in formula:
            result.append(f.strip())
        return result

    def _split_operator(self,formulas):
        result=[]
        formula = re.findall("\-|\+|\/|\*",formulas)
        for f in formula:
            result.append(f.strip())
        return result

    def _compute_report_balance(self, reports):
        """returns a dictionary with key=the ID of a record and
         value=the credit, debit and balance amount
        computed for this record. If the record is of type :
        'accounts' : it's the sum of the linked accounts
        'account_type' : it's the sum of leaf accounts with
         such an account_type
        'account_report' : it's the amount of the related report
        'sum' : it's the sum of the children of this record
         (aka a 'view' record)"""


        res = {}
        fields = ['debit', 'credit', 'balance']
        for report in reports:
            if report.id in res:
                continue
            res[report.id] = dict((fn, 0.0) for fn in fields)
            if report.domain:
                acc_id_domain = self._add_account_from_domain(report.domain)
                acc_domain = self._compute_account_balance(acc_id_domain)

            if report.type in ['accounts', 'account_type']:
                accounts = report.account_ids if report.type == 'accounts' else self.env['account.account'].search([('user_type_id', 'in', report.account_type_ids.ids)])
                account_balance = self._compute_account_balance(accounts)
                res[report.id]= {'account': account_balance, 'debit': 0.0, 'credit': 0.0, 'balance': 0.0}
                dr_sum = sum([ v.get('debit', 0.0) for v in account_balance.values()])
                cr_sum = sum([ v.get('credit', 0.0) for v in account_balance.values()])
                balance_sum = sum([ v.get('balance', 0.0) for v in account_balance.values()])
                res[report.id]['debit'] = dr_sum
                res[report.id]['credit'] = cr_sum
                res[report.id]['balance'] = balance_sum
                if report.domain:
                    res[report.id]['debit'] += sum([ v.get('debit', 0.0) for v in acc_domain.values()])
                    res[report.id]['credit'] += sum([ v.get('credit', 0.0) for v in acc_domain.values()])
                    res[report.id]['balance'] += sum([ v.get('balance', 0.0) for v in acc_domain.values()])
            if report.type == 'account_report':
                res_account_report = self._compute_report_balance(report.account_report_id)
                if res_account_report:
                    res[report.id]['debit'] = res_account_report[report.account_report_id.id]['debit']
                    res[report.id]['credit'] = res_account_report[report.account_report_id.id]['credit']
                    res[report.id]['balance'] = res_account_report[report.account_report_id.id]['balance']
                    if report.domain:
                        res[report.id]['account'] = res_account_report[report.account_report_id.id]['account']
                        res[report.id]['debit'] += sum([ v.get('debit', 0.0) for v in acc_domain.values()])
                        res[report.id]['credit'] += sum([ v.get('credit', 0.0) for v in acc_domain.values()])
                        res[report.id]['balance'] += sum([ v.get('balance', 0.0) for v in acc_domain.values()])
            if report.type == 'sum':
                # it's the sum of the children of this account.report
                db_sum = cr_sum = bal_sum = 0.0
                for children_id in report.children_ids:
                    res_sum = self._compute_report_balance(children_id)                    
                    db_sum += res_sum[children_id.id]['debit']
                    cr_sum += res_sum[children_id.id]['credit']
                    bal_sum += res_sum[children_id.id]['balance']
                res[report.id]['debit'] = db_sum
                res[report.id]['credit'] = cr_sum
                res[report.id]['balance'] = bal_sum

            if report.formulas:
                formulas = report._split_formulas()                
                if report.code:
                    formula=[]
                    operator=[]
                    for v in formulas.values():
                        formula = self._split_formulas(v)
                        operator = self._split_operator(v)
                        no = 0
                        for f in formula:
                            rep_code = f.split('.')
                            rep_id = self.env['account.financial.report'].search([('code', '=', rep_code[0])])
                            if rep_id:
                                repo = self._compute_report_balance(rep_id)
                                if no == 0:
                                    res[report.id]['debit'] += repo[rep_id.id]['debit']
                                    res[report.id]['credit'] += repo[rep_id.id]['credit']
                                    res[report.id]['balance'] += repo[rep_id.id]['balance']
                                else:
                                    result_debit = str(res[report.id]['debit']) + str(operator[no-1]) + str(repo[rep_id.id]['debit'])
                                    result_credit = str(res[report.id]['credit']) + str(operator[no-1]) + str(repo[rep_id.id]['credit'])
                                    result_balance = str(res[report.id]['balance']) + str(operator[no-1]) + str(repo[rep_id.id]['balance'])
                                    res[report.id]['debit'] = eval(result_debit)
                                    res[report.id]['credit'] = eval(result_credit)
                                    res[report.id]['balance'] = eval(result_balance)
                            no += 1
            if res[report.id]['balance'] != 0:
                res[report.id]['balance'] = res[report.id]['balance'] * int(report.sign)
        return res

    def get_account_lines(self, data):
        lines = []
        account_report = data['account_report_id']
        child_reports = account_report._get_children_by_order()
        res = self.with_context(data.get('used_context'))._compute_report_balance(child_reports)
        if data['enable_filter']:
            comparison_res = self._compute_report_balance(child_reports)
            for report_id, value in comparison_res.items():
                res[report_id]['comp_bal'] = value['balance']
                report_acc = res[report_id].get('account')
                if report_acc:
                    for account_id, val in comparison_res[report_id].get('account').items():
                        report_acc[account_id]['comp_bal'] = val['balance']
        for report in child_reports:
            r_name = str(report.name)
            r_name = re.sub('[^0-9a-zA-Z]+', '', r_name)
            if report.parent_id:
                p_name = str(report.parent_id.name)
                p_name = re.sub('[^0-9a-zA-Z]+', '', p_name) + str(report.parent_id.id)
            else:
                p_name = False

            child_ids = []
            for chd in report.children_ids:
                child_ids.append(chd.id)

            vals = {
                'r_id': report.id,
                'p_id': report.parent_id.id,
                'report_type': report.type,
                'c_ids': child_ids,
                'id': r_name + str(report.id),
                'sequence': report.sequence,
                'parent': p_name,
                'name': report.name,
                'balance': res[report.id]['balance'] * int(report.sign),
                'type': 'report',
                'level': report.level,
                # 'level': bool(report.style_overwrite) and report.style_overwrite or report.level,
                'account_type': report.type or False,
                'is_present': False,
                'report_sign': report.sign,
                # used to underline the financial report balances
            }
            if data['debit_credit']:
                vals['debit'] = res[report.id]['debit']
                vals['credit'] = res[report.id]['credit']

            if data['enable_filter']:
                vals['balance_cmp'] = res[report.id]['comp_bal'] * int(report.sign)

            lines.append(vals)
            # if report.display_detail == 'no_detail':
            #     # the rest of the loop is
            #     # used to display the details of the
            #     #  financial report, so it's not needed here.
            #     continue

            if res[report.id].get('account'):
                sub_lines = []
                for account_id, value in res[report.id]['account'].items():
                    # if there are accounts to display,
                    #  we add them to the lines with a level equals
                    #  to their level in
                    # the COA + 1 (to avoid having them with a too low level
                    #  that would conflicts with the level of data
                    # financial reports for Assets, liabilities...)
                    flag = False
                    account = self.env['account.account'].browse(account_id)
                    vals = {
                        'r_id': False,
                        'p_id': report.id,
                        'report_type': 'accounts',
                        'c_ids': [],
                        'account': account.id,
                        'code': account.code,
                        'a_id': account.code + re.sub('[^0-9a-zA-Z]+', 'acnt', account.name) + str(account.id),
                        'name': account.code + '-' + account.name,
                        'balance': value['balance'] * int(report.sign) or 0.0,
                        'type': 'account',
                        'parent': r_name + str(report.id),
                        # 'level': report.level,
                        'level': (report.display_detail == 'detail_with_hierarchy' and 5),
                        'account_type': account.internal_type,
                        'report_sign': report.sign,
                    }
                    if data.get('budget') == 'on':
                        flag = True
                    if data.get('all_account') == 'on':
                        flag = True
                    if data['debit_credit']:
                        vals['debit'] = value['debit']
                        vals['credit'] = value['credit']
                        if not account.company_id.currency_id.is_zero(vals['debit']) or not account.company_id.currency_id.is_zero(vals['credit']):
                            flag = True
                    if not account.company_id.currency_id.is_zero(vals['balance']):
                        flag = True
                    if data['enable_filter']:
                        vals['balance_cmp'] = value['comp_bal'] * int(report.sign)
                        if not account.company_id.currency_id.is_zero(vals['balance_cmp']):
                            flag = True
                    if flag:
                        sub_lines.append(vals)
                lines += sorted(sub_lines,key=lambda sub_line: sub_line['name'])
        return lines

    def find_journal_items(self, report_lines, form):        
        cr = self.env.cr
        journal_items = []
        acc_list = list(filter(lambda x: x['type'] == 'account', report_lines))
        list_acc_ids = (j['account'] for j in acc_list)
        account = tuple(list_acc_ids)
        if form['target_move'] == 'posted':
            search_query = "select am.id as j_id, aml.account_id, aa.name as account_name, aml.date, aml.name as label, am.name, " \
                           + "((SELECT REGEXP_REPLACE(aa.name::text, '[^0-9a-zA-Z]+', '', 'g')) || aml.id::text) as id, " \
                           + "(aa.code || (SELECT REGEXP_REPLACE(aa.name::text, '[^0-9a-zA-Z]+', 'acnt', 'g')) || aa.id) as p_id, " \
                           + "(SELECT REPLACE (aa.id::text, aa.id::text, 'journal_item')) as type, " \
                           + "(aml.debit-aml.credit) as balance, aml.debit, aml.credit, aml.partner_id " \
                           + " from account_move_line aml " \
                           + " join account_move am on (aml.move_id=am.id and am.state=%s) " \
                           + " join account_account aa on (aml.account_id=aa.id) " \
                           + " where aml.account_id in %s " \
                           + " order by am.journal_id "
            vals = [form['target_move']]
        else:
            search_query = "select am.id as j_id, aml.account_id, aa.name as account_name, aml.date, aml.name as label, am.name, " \
                           + "((SELECT REGEXP_REPLACE(aa.name::text, '[^0-9a-zA-Z]+', '', 'g')) || aml.id::text) as id, " \
                           + "(aa.code || (SELECT REGEXP_REPLACE(aa.name::text, '[^0-9a-zA-Z]+', 'acnt', 'g')) || aa.id) as p_id, " \
                           + "(SELECT REPLACE (aa.id::text, aa.id::text, 'journal_item')) as type, " \
                           + "(aml.debit-aml.credit) as balance, aml.debit, aml.credit, aml.partner_id " \
                           + " from account_move_line aml " \
                           + " join account_move am on (aml.move_id=am.id) " \
                           + " join account_account aa on (aml.account_id=aa.id) " \
                           + " where aml.account_id in %s " \
                           + " order by am.journal_id "
            vals = []
        if form['date_from'] and form['date_to']:
            search_query += " and aml.date>=%s and aml.date<=%s"
            vals += [account, form['date_from'], form['date_to']]
        elif form['date_from']:
            search_query += " and aml.date>=%s"
            vals += [account, form['date_from']]
        elif form['date_to']:
            search_query += " and aml.date<=%s"
            vals += [account, form['date_to']]
        else:
            vals += [account]

        cr.execute(search_query, tuple(vals))
        items = cr.dictfetchall()
        journal_items += items
        return journal_items