
import time
from datetime import datetime

from dateutil.relativedelta import relativedelta
from odoo import fields, models, api, _
from odoo.tools import float_is_zero

import io
import json

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter



class AgeingView(models.TransientModel):
    _inherit = "account.partner.ageing"

    section_num = fields.Integer('Section Number', default=4)
    result_selection = fields.Selection([('customer', 'Receivable Accounts'),
                                         ('supplier', 'Payable Accounts'),
                                         ('customer_supplier', 'Receivable and Payable Accounts')
                                         ], string="Partner's", required=True,
                                        default='customer_supplier')
    branch_ids = fields.Many2many('res.branch', string='Branches',)

    @api.model
    def view_report(self, option):
        r = self.env['account.partner.ageing'].search([('id', '=', option[0])])

        section_list = []
        section_sub_list = []
        for i in reversed(range(r.section_num + 1)):
            section_list.append(i)

        for i in reversed(range(r.section_num + 2)):
            section_sub_list.append('period' + str(i+1))

        data = {
            'result_selection': r.result_selection,
            'model': self,
            'journals': r.journal_ids,
            'target_move': r.target_move,
            'period_length': r.period_length,
            'partners': r.partner_ids,
            'partner_tags': r.partner_category_ids,
            'section_num': r.section_num,
            'branchs': r.branch_ids,
        }
        if r.date_from:
            data.update({
                'date_from': r.date_from,
            })

        filters = self.get_filter(option)
        records = self._get_report_values(data)
        currency = self._get_currency()

        res = {
            'name': "Partner Aging",
            'type': 'ir.actions.client',
            'tag': 'p_a',
            'filters': filters,
            'report_lines': records['Partners'],
            'currency': currency,
            'section_list': section_list,
            'section_sub_list': section_sub_list,
        }

        currency_ids = self.env['res.currency'].search([('active', '=', True)])
        res['currencies'] = [{
            'name': currency_id.name,
            'id': currency_id.id,
        } for currency_id in currency_ids]
        return res

    def _get_partner_move_lines(self, data, partners, date_from, target_move, account_type, period_length):
        if not data.get('partners'):
            partners = self.env['res.partner'].search([], limit=50, order="id desc")
        periods = {}
        section_num = data['section_num']
        # self.env['res.branch'].browse(data.get('branchs')).mapped('name')
        branchs = data.get('branchs')
        branch_ids = branchs.ids
        if section_num == 0:
            section_num = 4

        ageing_report = self.search([], limit=1, order="id desc")
        report_currency_id = ageing_report.report_currency_id
        currency_rate = 0
        start = datetime.strptime(date_from, "%Y-%m-%d")
        date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
        for i in range(section_num + 1)[::-1]:
            stop = start - relativedelta(days=period_length)
            period_name = str(((section_num + 1) - (i + 1)) * period_length + 1) + '-' + str(
                ((section_num + 1) - i) * period_length)
            period_stop = (start - relativedelta(days=1)).strftime('%Y-%m-%d')
            if i == 0:
                period_name = '+' + str(section_num * period_length)
            periods[str(i)] = {
                'name': period_name,
                'stop': period_stop,
                'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
            }
            start = stop

        res = []
        total = []
        cr = self.env.cr
        user_company = self.env.company

        user_currency = user_company.currency_id

        if date_from and report_currency_id:
            rate_ids = report_currency_id.rate_ids.filtered(lambda r: r.name >= date_from).sorted(key=lambda r: r.name)
            if rate_ids:
                currency_rate = rate_ids[-1].mr_rate
            else:
                currency_rate = report_currency_id.rate

        ResCurrency = self.env['res.currency'].with_context(date=date_from)
        company_ids = self._context.get('company_ids') or [user_company.id]
        move_state = ['draft', 'posted']
        if target_move == 'posted':
            move_state = ['posted']
        # ['payable', 'receivable']
        invbill = []
        if 'payable' in account_type:
            invbill.append('in_invoice')
        if 'receivable' in account_type:
            invbill.append('out_invoice')

        arg_list = (tuple(move_state), tuple(account_type), tuple(invbill))
        reconciliation_clause = '(l.reconciled IS FALSE)'
        cr.execute(
            'SELECT debit_move_id, credit_move_id FROM account_partial_reconcile where max_date > %s',
            (date_from,))
        reconciled_after_date = []
        for row in cr.fetchall():
            reconciled_after_date += [row[0], row[1]]
        if reconciled_after_date:
            reconciliation_clause = '(l.reconciled IS FALSE OR l.id IN %s)'
            arg_list += (tuple(reconciled_after_date),)

        arg_list += (date_from, tuple(company_ids),)
        partner_list = '(l.partner_id IS NOT  NULL)'
        if partners:
            list = tuple(partners.ids) + tuple([0])
            if list:
                partner_list = '(l.partner_id IS NULL OR l.partner_id IN %s)'
                arg_list += (tuple(list),)
        
        add_string = " "
        if data.get('branchs'):
            list_branch = tuple(branchs.ids)
            if list_branch:
                add_string = ' AND (am.branch_id IN (%s)) '
                arg_list += list_branch

        query = '''
                    SELECT DISTINCT l.partner_id, UPPER(res_partner.name)
                    FROM account_move_line AS l left join res_partner on l.partner_id = res_partner.id, account_account, account_move am
                    WHERE (l.account_id = account_account.id)
                        AND (l.move_id = am.id)
                        AND (am.state IN %s)
                        AND (account_account.internal_type IN %s)
                        AND (am.move_type IN %s)
                        AND ''' + reconciliation_clause + '''          
                        AND (l.date <= %s)
                        AND l.company_id IN %s
                        AND ''' + partner_list + '''
                        ''' + add_string + '''                           
                    ORDER BY UPPER(res_partner.name)'''
        cr.execute(query, arg_list)


        partners = cr.dictfetchall()

        # put a total of 0
        for i in range(section_num + 3):
            total.append(0)

        # Build a string like (1,2,3) for easy use in SQL query
        partner_ids = [partner['partner_id'] for partner in partners if partner['partner_id']]
        lines = dict((partner['partner_id'] or False, []) for partner in partners)
        if not partner_ids:
            return [], [], {}

        # This dictionary will store the not due amount of all partners
        undue_amounts = {}
        params = (tuple(move_state), tuple(account_type), tuple(invbill), date_from, tuple(partner_ids), date_from, tuple(company_ids))
        
        add_string = " "
        if data.get('branchs'):
            add_string = ''' AND (am.branch_id IN (%s)) '''
            params += tuple(branch_ids)
        query = '''SELECT l.id
                        FROM account_move_line AS l, account_account, account_move am
                        WHERE (l.account_id = account_account.id) AND (l.move_id = am.id)
                            AND (am.state IN %s)
                            AND (account_account.internal_type IN %s)
                            AND (am.move_type IN %s)
                            AND (COALESCE(l.date_maturity,l.date) >= %s)
                            AND ((l.partner_id IN %s) OR (l.partner_id IS NULL))
                            AND (l.date <= %s)
                            AND l.company_id IN %s ''' + add_string + '''
                            '''
        cr.execute(query, params)

        aml_ids = cr.fetchall()
        aml_ids = aml_ids and [x[0] for x in aml_ids] or []
        for line in self.env['account.move.line'].search([('id', 'in', aml_ids)]):
            if data.get('date_from'):
                if not line.date_maturity:
                    continue
                # if line.date_maturity > data.get('date_from'):
                #     continue
            partner_id = line.partner_id.id or False
            move_id = line.move_id.id
            move_name = line.move_id.name
            date_maturity = line.date_maturity
            account_id = line.account_id.name
            account_code = line.account_id.code
            jrnl_id = line.journal_id.name
            if report_currency_id:
                currency_id = report_currency_id.position
                currency_symbol = report_currency_id.symbol
            else:
                currency_id = line.company_id.currency_id.position
                currency_symbol = line.company_id.currency_id.symbol

            if partner_id not in undue_amounts:
                undue_amounts[partner_id] = 0.0
            line_amount = ResCurrency._compute(line.company_id.currency_id,
                                               user_currency, line.balance)
            if user_currency.is_zero(line_amount):
                continue
            for partial_line in line.matched_debit_ids:
                if partial_line.max_date <= date_from:
                    line_amount += ResCurrency._compute(
                        partial_line.company_id.currency_id, user_currency,
                        partial_line.amount)
            for partial_line in line.matched_credit_ids:
                if partial_line.max_date <= date_from:
                    line_amount -= ResCurrency._compute(
                        partial_line.company_id.currency_id, user_currency,
                        partial_line.amount)
            if not self.env.company.currency_id.is_zero(line_amount):
                if currency_rate > 0:
                    line_amount *= currency_rate
                undue_amounts[partner_id] += line_amount
                if partner_id:
                    period_name = 'period' + str(section_num + 2)
                    lines[partner_id].append({
                        'line': line,
                        'partner_id': partner_id,
                        'move': move_name,
                        'jrnl': jrnl_id,
                        'currency': currency_id,
                        'symbol': currency_symbol,
                        'acc_name': account_id,
                        'mov_id': move_id,
                        'acc_code': account_code,
                        'date': date_maturity,
                        'amount': line_amount,
                        period_name: section_num + 2,
                    })

        # Use one query per period and store results in history (a list variable)
        # Each history will contain: history[1] = {'<partner_id>': <partner_debit-credit>}
        history = []
        for i in range(section_num + 1):
            args_list = (
                tuple(move_state), tuple(account_type), tuple(invbill), tuple(partner_ids),)
            dates_query = '(COALESCE(l.date_maturity,l.date)'

            if periods[str(i)]['start'] and periods[str(i)]['stop']:
                dates_query += ' BETWEEN %s AND %s)'

                args_list += (
                    periods[str(i)]['start'], periods[str(i)]['stop'])
            elif periods[str(i)]['start']:
                dates_query += ' >= %s)'

                args_list += (periods[str(i)]['start'],)
            else:
                dates_query += ' <= %s)'
                args_list += (periods[str(i)]['stop'],)

            args_list += (date_from, tuple(company_ids))
            
            add_string = " "
            if data.get('branchs'):
                add_string = ''' AND (am.branch_id IN (%s)) '''
                args_list += tuple(branch_ids)

            query = '''SELECT l.id
                            FROM account_move_line AS l, account_account, account_move am
                            WHERE (l.account_id = account_account.id) AND (l.move_id = am.id)
                                AND (am.state IN %s)
                                AND (account_account.internal_type IN %s)
                                AND (am.move_type IN %s)
                                AND ((l.partner_id IN %s) OR (l.partner_id IS NULL))
                                AND ''' + dates_query + '''
                            AND (l.date <= %s)
                            AND l.company_id IN %s''' + add_string + '''
                            '''
            cr.execute(query, args_list)

            partners_amount = {}
            aml_ids = cr.fetchall()
            aml_ids = aml_ids and [x[0] for x in aml_ids] or []
            for line in self.env['account.move.line'].search([('id', 'in', aml_ids)]):
                if data.get('date_from'):
                    if not line.date_maturity:
                        continue
                    if line.date_maturity > data.get('date_from'):
                        continue
                partner_id = line.partner_id.id or False
                move_id = line.move_id.id
                move_name = line.move_id.name
                date_maturity = line.date_maturity
                account_id = line.account_id.name
                account_code = line.account_id.code
                jrnl_id = line.journal_id.name
                if report_currency_id:
                    currency_id = report_currency_id.position
                    currency_symbol = report_currency_id.symbol
                else:
                    currency_id = line.company_id.currency_id.position
                    currency_symbol = line.company_id.currency_id.symbol
                if partner_id not in partners_amount:
                    partners_amount[partner_id] = 0.0
                line_amount = ResCurrency._compute(line.company_id.currency_id,
                                                   user_currency, line.balance)
                if user_currency.is_zero(line_amount):
                    continue
                for partial_line in line.matched_debit_ids:
                    if partial_line.max_date <= date_from:
                        line_amount += ResCurrency._compute(
                            partial_line.company_id.currency_id, user_currency,
                            partial_line.amount)
                for partial_line in line.matched_credit_ids:
                    if partial_line.max_date <= date_from:
                        line_amount -= ResCurrency._compute(
                            partial_line.company_id.currency_id, user_currency,
                            partial_line.amount)

                if not self.env.company.currency_id.is_zero(
                        line_amount):
                    if currency_rate > 0:
                        line_amount *= currency_rate
                    partners_amount[partner_id] += line_amount
                    # if i + 1 == 5:
                    #     period5 = i + 1
                    #     if partner_id:
                    #         lines[partner_id].append({
                    #             'period5': period5,
                    #             'line': line,
                    #             'partner_id': partner_id,
                    #             'move': move_name,
                    #             'currency': currency_id,
                    #             'symbol': currency_symbol,
                    #             'jrnl': jrnl_id,
                    #             'acc_name': account_id,
                    #             'mov_id': move_id,
                    #             'acc_code': account_code,
                    #             'date': date_maturity,
                    #             'amount': line_amount,
                    #         })
                    # elif i + 1 == 4:
                    #     period4 = i + 1
                    #     if partner_id:
                    #         lines[partner_id].append({

                    #             'period4': period4,
                    #             'line': line,
                    #             'partner_id': partner_id,
                    #             'move': move_name,
                    #             'jrnl': jrnl_id,
                    #             'acc_name': account_id,
                    #             'currency': currency_id,
                    #             'symbol': currency_symbol,
                    #             'mov_id': move_id,
                    #             'acc_code': account_code,
                    #             'date': date_maturity,
                    #             'amount': line_amount,
                    #         })
                    # elif i + 1 == 3:
                    #     period3 = i + 1
                    #     if partner_id:
                    #         lines[partner_id].append({

                    #             'period3': period3,
                    #             'line': line,
                    #             'partner_id': partner_id,
                    #             'move': move_name,
                    #             'jrnl': jrnl_id,
                    #             'acc_name': account_id,
                    #             'currency': currency_id,
                    #             'symbol': currency_symbol,
                    #             'mov_id': move_id,
                    #             'acc_code': account_code,
                    #             'date': date_maturity,
                    #             'amount': line_amount,
                    #         })
                    # elif i + 1 == 2:
                    #     period2 = i + 1
                    #     if partner_id:
                    #         lines[partner_id].append({

                    #             'period2': period2,
                    #             'line': line,
                    #             'partner_id': partner_id,
                    #             'move': move_name,
                    #             'jrnl': jrnl_id,
                    #             'acc_name': account_id,
                    #             'currency': currency_id,
                    #             'symbol': currency_symbol,
                    #             'mov_id': move_id,
                    #             'acc_code': account_code,
                    #             'date': date_maturity,
                    #             'amount': line_amount,
                    #         })
                    # else:
                    #     period1 = i + 1
                    #     if partner_id:
                    #         lines[partner_id].append({

                    #             'period1': period1,
                    #             'line': line,
                    #             'partner_id': partner_id,
                    #             'move': move_name,
                    #             'jrnl': jrnl_id,
                    #             'acc_name': account_id,
                    #             'currency': currency_id,
                    #             'symbol': currency_symbol,
                    #             'mov_id': move_id,
                    #             'acc_code': account_code,
                    #             'date': date_maturity,
                    #             'amount': line_amount,
                    #         })

                    for j in range(section_num + 1):
                        j += 1
                        if i + 1 == j:
                            period_j = i + 1
                            if partner_id:
                                period_name = 'period' + str(j)
                                lines[partner_id].append({
                                    period_name: period_j,
                                    'line': line,
                                    'partner_id': partner_id,
                                    'move': move_name,
                                    'currency': currency_id,
                                    'symbol': currency_symbol,
                                    'jrnl': jrnl_id,
                                    'acc_name': account_id,
                                    'mov_id': move_id,
                                    'acc_code': account_code,
                                    'date': date_maturity,
                                    'amount': line_amount,
                                })

            history.append(partners_amount)

        for partner in partners:
            if partner['partner_id'] is None:
                partner['partner_id'] = False
            at_least_one_amount = False
            values = {}
            undue_amt = 0.0
            if partner[
                'partner_id'] in undue_amounts:  # Making sure this partner actually was found by the query
                undue_amt = undue_amounts[partner['partner_id']]

            total[section_num + 2] += undue_amt
            values['direction'] = undue_amt
            for rec in lines:
                if partner['partner_id'] == rec:
                    child_lines = lines[rec]
            values['child_lines'] = child_lines
            if not float_is_zero(values['direction'],
                                 precision_rounding=self.env.company.currency_id.rounding):
                at_least_one_amount = True

            for i in range(section_num + 1):
                during = False
                if partner['partner_id'] in history[i]:
                    during = [history[i][partner['partner_id']]]
                # Adding counter
                total[(i)] = total[(i)] + (during and during[0] or 0)
                values[str(i)] = during and during[0] or 0.0
                if not float_is_zero(values[str(i)],
                                     precision_rounding=self.env.company.currency_id.rounding):
                    at_least_one_amount = True
            values['total'] = sum(
                [values['direction']] + [values[str(i)] for i in range(section_num + 1)])
            ## Add for total
            total[(i + 1)] += values['total']
            values['partner_id'] = partner['partner_id']
            if partner['partner_id']:
                browsed_partner = self.env['res.partner'].browse(
                    partner['partner_id'])
                values['name'] = browsed_partner.name and len(
                    browsed_partner.name) >= 45 and browsed_partner.name[
                                                    0:40] + '...' or browsed_partner.name
                values['trust'] = browsed_partner.trust
            else:
                values['name'] = _('Unknown Partner')
                values['trust'] = False

            values['period_length'] = period_length

            if at_least_one_amount or (
                    self._context.get('include_nullified_amount') and lines[
                partner['partner_id']]):
                res.append(values)
        return res, total, lines

    @api.model
    def _get_currency(self):
        ageing_report = self.search([], limit=1, order="id desc")
        report_currency_id = ageing_report.report_currency_id
        journal = self.env['account.journal'].browse(
            self.env.context.get('default_journal_id', False))
        if journal.currency_id and not report_currency_id:
            return journal.currency_id.id
        lang = self.env.user.lang
        if not lang:
            lang = 'en_US'
        lang = lang.replace("_", '-')
        if not report_currency_id:
            currency_array = [self.env.company.currency_id.symbol, self.env.company.currency_id.position, lang]
        else:
            currency_array = [report_currency_id.symbol, report_currency_id.position, lang]
        return currency_array


    def get_filter(self, option):
        res = super(AgeingView, self).get_filter(option)
        data = self.get_filter_data(option)
        
        if data.get('period_length'):
            res['period_length'] = data.get('period_length')
        else:
            res['period_length'] = 30
        if data.get('section_num'):
            res['section_num'] = data.get('section_num')
        else:
            res['section_num'] = 4
        
        if data.get('branchs'):
            res['branchs'] = self.env['res.branch'].browse(data.get('branchs')).mapped('name')
        else:
            res['branchs'] = ['All']

        res['branch_list'] = data.get('branch_list')
        return res


    def get_filter_data(self, option):
        res = super(AgeingView, self).get_filter_data(option)
        r = self.env['account.partner.ageing'].search([('id', '=', option[0])])
        company_ids = self._context.get('company_ids') or self.env.company.ids
        company_domain = [('company_id', 'in', company_ids)]
        branch = r.branch_ids if r.branch_ids else self.env['res.branch'].search(company_domain)

        res['period_length'] = r.period_length
        res['section_num'] = r.section_num
        res['branch_list'] = [(b.id, b.name) for b in branch]
        return res

    
    def write(self, vals):
        if vals.get('branch_ids'):
            vals.update({'branch_ids': [(6, 0, vals.get('branch_ids'))]})
        if not vals.get('branch_ids'):
            vals.update({'branch_ids': [(5,)]})
        res = super(AgeingView, self).write(vals)
        return res


    def get_dynamic_xlsx_report(self, data, response, report_data, dfr_data ):

        report_data_main = json.loads(report_data)
        output = io.BytesIO()
        filters = json.loads(data)
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        head = workbook.add_format({'bold': True})
        sub_heading = workbook.add_format({'bold': True, 'border': 1, 'border_color': 'black'})
        heading = workbook.add_format({'bold': True, 'border': 2, 'border_color': 'black'})
        txt = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        txt_l = workbook.add_format({'border': 1, 'bold': True, 'num_format': '#,##0.00'})
        txt_v = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        sheet.merge_range('A2:H3',
                          filters.get('company_name') + ':' + ' Partner Aging',
                          head)
        date_head = workbook.add_format({'bold': True})
        date_style = workbook.add_format({})
        if filters.get('date_from'):
            sheet.merge_range('A4:B4',
                              'As On Date: ' + filters.get('date_from'),
                              date_head)
        sheet.merge_range('C4:E4',
                          'Account Type: ' + filters.get('result_selection'),
                          date_head)
        sheet.merge_range('A5:B5',
                          'Target Moves: ' + filters.get('target_move'),
                          date_head)
        sheet.merge_range('D5:F5', '  Partners: ' + ', '.join(
            [lt or '' for lt in
             filters['partners']]), date_head)
        sheet.merge_range('G5:H5', ' Partner Type: ' + ', '.join(
            [lt or '' for lt in
             filters['partner_tags']]),
                          date_head)

        sheet.merge_range('A7:C7', 'Partner', heading)
        sheet.write('D7', 'Total', heading)
        sheet.write('E7', 'Not Due', heading)
        sheet.write('F7', '1-30', heading)
        sheet.write('G7', '30-60', heading)
        sheet.write('H7', '60-90', heading)
        sheet.write('I7', '90-120', heading)
        sheet.write('J7', '120+', heading)

        lst = []
        for rec in report_data_main[0]:
            lst.append(rec)
        row = 6
        col = 0
        sheet.set_column(5, 0, 15)
        sheet.set_column(6, 1, 15)
        sheet.set_column(7, 2, 15)
        sheet.set_column(8, 3, 15)
        sheet.set_column(9, 4, 15)
        sheet.set_column(10, 5, 15)
        sheet.set_column(11, 6, 15)

        for rec_data in report_data_main[0]:
            one_lst = []
            two_lst = []

            row += 1
            sheet.merge_range(row, col, row, col + 2, rec_data['name'], txt_l)
            sheet.write(row, col + 3, rec_data['total'], txt_l)
            sheet.write(row, col + 4, rec_data['direction'], txt_l)
            sheet.write(row, col + 5, rec_data['4'], txt_l)
            sheet.write(row, col + 6, rec_data['3'], txt_l)
            sheet.write(row, col + 7, rec_data['2'], txt_l)
            sheet.write(row, col + 8, rec_data['1'], txt_l)
            sheet.write(row, col + 9, rec_data['0'], txt_l)
            
            if rec_data['child_lines']:
                row += 1
                sheet.write(row, col, 'Entry Label', sub_heading)
                sheet.write(row, col + 1, 'Due Date', sub_heading)
                sheet.write(row, col + 2, 'Journal', sub_heading)
                sheet.write(row, col + 3, 'Account', sub_heading)
                sheet.write(row, col + 4, 'Not Due', sub_heading)
                sheet.write(row, col + 5, '1 - 30', sub_heading)
                sheet.write(row, col + 6, '30 - 60', sub_heading)
                sheet.write(row, col + 7, '60 - 90', sub_heading)
                sheet.write(row, col + 8, '90 - 120', sub_heading)
                sheet.write(row, col + 9, '120 +', sub_heading)

                for line_data in rec_data['child_lines']:
                    row += 1
                    sheet.write(row, col, line_data.get('move'), txt)
                    sheet.write(row, col + 1, line_data.get('date'), txt)
                    sheet.write(row, col + 2, line_data.get('jrnl'), txt)
                    sheet.write(row, col + 3, line_data.get('acc_code'), txt)
                    if line_data.get('period6'):
                        sheet.write(row, col + 4, line_data.get('amount'), txt)
                    else:
                        sheet.write(row, col + 4, 0, txt_v)
                    if line_data.get('period5'):
                        sheet.write(row, col + 5, line_data.get('amount'), txt)
                    else:
                        sheet.write(row, col + 5, 0, txt_v)
                    if line_data.get('period4'):
                        sheet.write(row, col + 6, line_data.get('amount'), txt)
                    else:
                        sheet.write(row, col + 6, 0, txt_v)
                    if line_data.get('period3'):
                        sheet.write(row, col + 7, line_data.get('amount'), txt)
                    else:
                        sheet.write(row, col + 7, 0, txt_v)
                    if line_data.get('period2'):
                        sheet.write(row, col + 8, line_data.get('amount'), txt)
                    else:
                        sheet.write(row, col + 8, 0, txt_v)
                    if line_data.get('period1'):
                        sheet.write(row, col + 9, line_data.get('amount'), txt)
                    else:
                        sheet.write(row, col + 9, 0, txt_v)
        row += 1
        sheet.merge_range(row, col, row, col + 2, "Total", txt_l)
        sheet.write(row, col + 3, report_data_main[1][5], txt_l)
        sheet.write(row, col + 4, report_data_main[1][6], txt_l)
        sheet.write(row, col + 5, report_data_main[1][4], txt_l)
        sheet.write(row, col + 6, report_data_main[1][3], txt_l)
        sheet.write(row, col + 7, report_data_main[1][2], txt_l)
        sheet.write(row, col + 8, report_data_main[1][1], txt_l)
        sheet.write(row, col + 9, report_data_main[1][0], txt_l)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()