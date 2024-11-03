import time
from odoo import _, models
from odoo.exceptions import UserError


class ReportFinancial(models.AbstractModel):
    _inherit = 'report.sg_account_report.report_financial'

    """Categories by account type report.

    This Report file is inherited from Base account Module to add the
    functionality of Print report as categories by Account type sorted by
    sequence.
    """

    def _compute_account_balance(self, accounts):
        """Compute Balance.

        Compute the balance, debit and credit for the provided accounts
        """
        mapping = {
            'balance':
            "COALESCE(SUM(debit),0) - COALESCE(SUM(credit), 0) as balance",
            'debit': "COALESCE(SUM(debit), 0) as debit",
            'credit': "COALESCE(SUM(credit), 0) as credit",
        }

        res = {}
        for account in accounts:
            res[account.id] = dict((fn, 0.0) for fn in mapping.keys())
        if accounts:
            tables, where_clause, where_params = \
                self.env['account.move.line']._query_get()
            tables = tables.replace('"', '') if tables else "account_move_line"
            wheres = [""]
            if where_clause.strip():
                wheres.append(where_clause.strip())
            filters = " AND ".join(wheres)
            request = "SELECT account_id as id, " + \
                ', '.join(mapping.values()) + \
                " FROM " + tables + \
                " WHERE account_id IN %s " + filters + \
                " GROUP BY account_id"
            params = (tuple(accounts._ids),) + tuple(where_params)
            self.env.cr.execute(request, params)
            for row in self.env.cr.dictfetchall():
                res[row['id']] = row
        return res

    def _compute_report_balance(self, reports):
        """Compute report balance.

        Returns a dictionary with key=the ID of a record and value=the credit,
        debit and balance amount
        """
        res = {}
        fields = ['credit', 'debit', 'balance']
        for report in reports:
            if report.id in res:
                continue
            res[report.id] = dict((fn, 0.0) for fn in fields)
            if report.type == 'accounts':
                #  it's the sum of the linked accounts
                res[report.id]['account'] = \
                    self._compute_account_balance(report.account_ids)
                for value in res[report.id]['account'].values():
                    for field in fields:
                        res[report.id][field] += value.get(field)
            elif report.type == 'account_type':
                #  it's the sum the leaf accounts with such an account type
                domain = [('user_type_id', 'in', report.account_type_ids.ids)]
                if self._context and 'company_id' in self._context:
                    domain += [('company_id', '=',
                                self._context.get('company_id'))]
                accounts = self.env['account.account'].search(domain)
                accounts = accounts.sorted(key=lambda a:
                                           (a.user_type_id.sequence))
                res[report.id]['account'] = \
                    self._compute_account_balance(accounts)
                for value in res[report.id]['account'].values():
                    for field in fields:
                        res[report.id][field] += value.get(field)
            elif report.type == 'account_report' and report.account_report_id:
                #  it's the amount of the linked report
                res2 = self._compute_report_balance(report.account_report_id)
                for key, value in res2.items():
                    for field in fields:
                        res[report.id][field] += value[field]
            elif report.type == 'sum':
                #  it's the sum of the children of this account.report
                res2 = self._compute_report_balance(report.children_ids)
                for key, value in res2.items():
                    for field in fields:
                        res[report.id][field] += value[field]
        return res

    def get_account_lines(self, data):
        lines = []
        account_report = self.env['account.financial.report'].search(
            [('id', '=', data['account_report_id'][0])])
        child_reports = account_report._get_children_by_order()
        res = self.with_context(data.get('used_context')
                                )._compute_report_balance(child_reports)
        if data['enable_filter']:
            comparison_res = self.with_context(
                data.get('comparison_context'
                         ))._compute_report_balance(child_reports)
            for report_id, value in comparison_res.items():
                res[report_id]['comp_bal'] = value['balance']
                report_acc = res[report_id].get('account')
                if report_acc:
                    for account_id, val in \
                            comparison_res[report_id].get('account').items():
                        report_acc[account_id]['comp_bal'] = val['balance']
        acc_type_name = ''
        acc_type_list = []
        parent_total = 0.0
        patent_name = ''
        for report in child_reports:
            vals = {
                'name': report.name,
                'balance': res[report.id]['balance'] * int(report.sign),
                'type': 'report',
                'level': bool(report.style_overwrite) and
                report.style_overwrite or report.level,
                #  used to underline the financial report balances
                'account_type': report.type or False,
            }
            if data['debit_credit']:
                vals['debit'] = res[report.id]['debit']
                vals['credit'] = res[report.id]['credit']

            if data['enable_filter']:
                vals['balance_cmp'] = res[report.id]['comp_bal'] * \
                    int(report.sign)

            if len(acc_type_list) > 0:
                if acc_type_name != '' and \
                        (report.type in ('sum', 'account_report') or
                            report.sign == -1):
                    value_type = {
                        'name': acc_type_name,
                        'balance': acc_type_total or 0.0,
                        'level': 3,
                        'account_typess': 'Total',
                        'user_type_id': account.user_type_id.name,
                        'user_type_sqe': account.user_type_id.sequence,
                        'debit': 0.0,
                        'credit': 0.0,
                    }
                    lines.append(value_type)
                    if patent_name != '':
                        value_par_type = {
                            'name': "Total " + patent_name,
                            'balance': parent_total or 0.0,
                            'level': 1,
                            'account_typess': 'Total',
                            'user_type_id': account.user_type_id.name,
                            'user_type_sqe': account.user_type_id.sequence,
                            'debit': 0.0,
                            'credit': 0.0,
                        }
                        lines.append(value_par_type)
            parent_total = vals['balance'] or 0.0
            patent_name = vals['name']
            lines.append(vals)
            if report.display_detail == 'no_detail':
                #  the rest of the loop is used to display the details of the
                #  financial report, so it's not needed here.
                continue
            if res[report.id].get('account'):
                sub_lines = []
                acc_type_name = ''
                acc_type_list = []
                acc_type_total = 0.0
                for account_id, value in res[report.id]['account'].items():
                    #  if there are accounts to display, we add them to the
                    #  lines with a level equals to their level in
                    #  the COA + 1 (to avoid having them with a too low level
                    #  that would conflicts with the level of data
                    #  financial reports for Assets, liabilities...)
                    flag = False
                    account = self.env['account.account'].browse(account_id)
                    vals = {
                        'name': account.code + ' ' + account.name,
                        'balance': value['balance'] * int(report.sign) or 0.0,
                        'type': 'account',
                        'level':
                        report.display_detail == 'detail_with_hierarchy' and 4,
                        'account_type': account.internal_type,
                        'user_type_id': account.user_type_id.name,
                        'user_type_sqe': account.user_type_id.sequence,
                    }
                    cur_id = account.company_id.currency_id
                    if data['debit_credit']:
                        vals['debit'] = value['debit']
                        vals['credit'] = value['credit']
                        if not cur_id.is_zero(vals['debit']) or \
                                not cur_id.is_zero(vals['credit']):
                            flag = True
                    if not cur_id.is_zero(vals['balance']):
                        flag = True
                    if data['enable_filter']:
                        vals['balance_cmp'] = value['comp_bal'] * \
                            int(report.sign)
                        if not cur_id.is_zero(vals['balance_cmp']):
                            flag = True
                    if flag:
                        if account.user_type_id.id not in acc_type_list:
                            if acc_type_name != '':
                                vals_type = {
                                    'name': acc_type_name,
                                    'balance': acc_type_total or 0.0,
                                    'level': 3,
                                    'account_typess': 'Total',
                                    'user_type_id': account.user_type_id.name,
                                    'user_type_sqe':
                                    account.user_type_id.sequence,
                                    'debit': 0.0,
                                    'credit': 0.0,
                                }
                                sub_lines.append(vals_type)
                                acc_type_total = 0.0
                            acc_type_name = "Total " + \
                                account.user_type_id.name
                            acc_type_list.append(account.user_type_id.id)
                            vals1 = {
                                'name': account.user_type_id.name,
                                'balance': 0.0,
                                'level': 3,
                                'account_typess': 'name',
                                'user_type_id': account.user_type_id.name,
                                'user_type_sqe': account.user_type_id.sequence,
                                'debit': 0.0,
                                'credit': 0.0,
                            }
                            sub_lines.append(vals1)
                        sub_lines.append(vals)
                        acc_type_total += vals['balance'] or 0.0
                lines += sorted(sub_lines,
                                key=lambda sub_line: sub_line['user_type_sqe'])
        if len(acc_type_list) > 0:
            if acc_type_name != '' and (report.type == 'sum' or
                                        int(report.sign) == -1):
                value_type = {
                    'name': acc_type_name,
                    'balance': acc_type_total or 0.0,
                    'level': 3,
                    'account_typess': 'Total',
                    'user_type_id': account.user_type_id.name,
                    'user_type_sqe': account.user_type_id.sequence,
                    'debit': 0.0,
                    'credit': 0.0,
                }
                lines.append(value_type)
                if patent_name != '':
                    value_par_type = {
                        'name': "Total " + patent_name,
                        'balance': parent_total or 0.0,
                        'level': 1,
                        'account_typess': 'Total',
                        'user_type_id': account.user_type_id.name,
                        'user_type_sqe': account.user_type_id.sequence,
                        'debit': 0.0,
                        'credit': 0.0,
                    }
                    lines.append(value_par_type)
        return lines

    def _get_report_values(self, docids, data=None):
        if not data.get('form') or \
                not self.env.context.get('active_model') or \
                not self.env.context.get('active_id'):
            raise UserError(_("Form content is missing, this report cannot \
            be printed."))
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))
        report_lines = self.get_account_lines(data.get('form'))
        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
            'time': time,
            'get_account_lines': report_lines,
        }
