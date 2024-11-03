
from odoo import fields, models, api, _
import io
import json
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class PartnerView(models.TransientModel):
    _inherit = "account.partner.ledger"


    show_all_transaction = fields.Selection([
        ('off', 'Off'),
        ('on', 'On')
    ], string='Show Outstanding Ledger Only', default='off')
    expand = fields.Boolean(string="Expand", default=False)


    @api.model
    def create(self, vals):
        vals['expand'] = False
        res = super(PartnerView, self).create(vals)
        return res

    def write(self, vals):
        if vals.get('show_all_transaction'):
            vals.update({'show_all_transaction': vals.get('show_all_transaction').lower()})
      
        res = super(PartnerView, self).write(vals)
        return res

    # @api.model
    # def view_report(self, option):
    #     res = super(PartnerView, self).view_report(option)
    #     currency_ids = self.env['res.currency'].search([('active', '=', True)])
    #     res['currencies'] = [{
    #         'name': currency_id.name,
    #         'id': currency_id.id,
    #     } for currency_id in currency_ids]
    #     return res

    @api.model
    def view_report(self, option):
        r = self.env['account.partner.ledger'].search([('id', '=', option[0])])
        data = {
            'display_account': r.display_account,
            'model': self,
            'journals': r.journal_ids,
            'accounts': r.account_ids,
            'target_move': r.target_move,
            'partners': r.partner_ids,
            'reconciled': r.reconciled,
            'account_type': r.account_type_ids,
            'partner_tags': r.partner_category_ids,
            'show_all_transaction': r.show_all_transaction,
        }

        if r.date_from:
            data.update({
                'date_from':r.date_from,
            })
        if r.date_to:
            data.update({
                'date_to':r.date_to,
            })

        filters = self.get_filter(option)
        records = self._get_report_values(data)
        currency = self._get_currency()
        currency_ids = self.env['res.currency'].search([('active', '=', True)])

        return {
            'name': "partner Ledger",
            'type': 'ir.actions.client',
            'tag': 'p_l',
            'filters': filters,
            'report_lines': records['Partners'],
            'debit_total': records['debit_total'],
            'credit_total': records['credit_total'],
            'debit_balance': records['debit_balance'],
            'currency': currency,
            'currencies': [{
                'name': currency_id.name,
                'id': currency_id.id,
            } for currency_id in currency_ids],
        }

    def _get_partners(self, partners, accounts, init_balance, display_account, data):

        cr = self.env.cr
        move_line = self.env['account.move.line']
        move_lines = {x: [] for x in partners.ids}
        partner_ledger = self.search([], limit=1, order="id desc")
        report_currency_id = partner_ledger.report_currency_id
        currency_rate = 0
        if not report_currency_id:
            currency_id = self.env.company.currency_id
        else:
            currency_id = report_currency_id
            if data.get('date_from') and data.get('date_to'):
                rate_ids = currency_id.rate_ids.filtered(lambda r: r.name >= data.get('date_from') and r.name <= data.get('date_to')).sorted(key=lambda r: r.name)
                if rate_ids:
                    currency_rate = rate_ids[-1].mr_rate
                else:
                    currency_rate = currency_id.rate
            elif data.get('date_from'):
                rate_ids = currency_id.rate_ids.filtered(lambda r: r.name >= data.get('date_from')).sorted(key=lambda r: r.name)
                if rate_ids:
                    currency_rate = rate_ids[-1].mr_rate
                else:
                    currency_rate = currency_id.rate
            elif data.get('date_to'):
                rate_ids = currency_id.rate_ids.filtered(lambda r: r.name <= data.get('date_to')).sorted(key=lambda r: r.name)
                if rate_ids:
                    currency_rate = rate_ids[-1].mr_rate
                else:
                    currency_rate = currency_id.rate
            else:
                currency_rate = currency_id.rate
        tables, where_clause, where_params = move_line._query_get()
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

        if data.get('partners'):
            WHERE += ' AND p.id IN %s' % str(
                tuple(data.get('partners').ids) + tuple([0]))
        
        if data.get('show_all_transaction') == 'on':
            WHERE += ' AND l.reconciled = false'

        # if data.get('reconciled') == 'unreconciled':
        #     WHERE += ' AND l.full_reconcile_id is null AND' \
        #              ' l.balance != 0 AND a.reconcile is true'

        sql = ('''SELECT l.id AS lid,l.partner_id AS partner_id,m.id AS move_id, 
                    l.account_id AS account_id, l.date AS ldate, j.code AS lcode, l.currency_id, 
                    l.amount_currency, l.ref AS lref, l.name AS lname, 
                    concat(a.name, '+(', a.code, ')') as account_name,
                    l.account_id AS m_id,
                    COALESCE(l.debit,0) AS debit, COALESCE(l.credit,0) AS credit, 
                    COALESCE(SUM(l.balance),0) AS balance,\
                    m.name AS move_name, c.symbol AS currency_code,c.position AS currency_position, p.name AS partner_name\
                    FROM account_move_line l\
                    JOIN account_move m ON (l.move_id=m.id)\
                    JOIN account_account a ON (l.account_id=a.id)
                    LEFT JOIN res_currency c ON (l.currency_id=c.id)\
                    LEFT JOIN res_partner p ON (l.partner_id=p.id)\
                    JOIN account_journal j ON (l.journal_id=j.id)\
                    JOIN account_account acc ON (l.account_id = acc.id) '''
                    + WHERE + new_final_filter + ''' GROUP BY l.id, m.id,  l.account_id, l.date, j.code, l.currency_id, l.amount_currency, l.ref, l.name, m.name, c.symbol, c.position, p.name, a.name, a.code''' )
        if data.get('accounts'):
            params = tuple(where_params)
        else:
            params = (tuple(accounts.ids),) + tuple(where_params)
        cr.execute(sql, params)

        account_list = { x.id : {'name' : x.name, 'code': x.code} for x in accounts}

        for row in cr.dictfetchall():
            # balance = 0
            if row['partner_id'] in move_lines:
                # for line in move_lines.get(row['partner_id']):
                #     balance += round(line['debit'],2) - round(line['credit'],2)
                # row['balance'] += (round(balance, 2))
                # row['m_id'] = row['account_id']
                # row['account_name'] = account_list[row['account_id']]['name'] + "(" +account_list[row['account_id']]['code'] + ")"
                move_lines[row.pop('partner_id')].append(row)

        partner_res = []
        for partner in partners:
            company_id = self.env.company
            if not report_currency_id:
                currency = company_id.currency_id
            else:
                currency = report_currency_id
            res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance'])
            res['name'] = partner.name
            res['id'] = partner.id
            res['move_lines'] = move_lines[partner.id]
            for line in res.get('move_lines'):
                line['currency_position'] = currency.position
                line['currency_code'] = currency.symbol
                if currency_rate > 0:
                    line['debit'] = round(line['debit'] * currency_rate, 2)
                    line['credit'] = round(line['credit'] * currency_rate, 2)
                    line['balance'] = round(line['balance'] * currency_rate, 2)

                res['debit'] += round(line['debit'], 2)
                res['credit'] += round(line['credit'], 2)
                res['balance'] = res['debit'] - res['credit']

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
        partner_ledger = self.search([], limit=1, order="id desc")
        report_currency_id = partner_ledger.report_currency_id
        journal = self.env['account.journal'].browse(
            self.env.context.get('default_journal_id', False))
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

    def get_dynamic_xlsx_report(self, data, response, report_data, dfr_data):
        report_data = json.loads(report_data)
        filters = json.loads(data)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        cell_format = workbook.add_format({'bold': True,'border': 0})
        sheet = workbook.add_worksheet()
        head = workbook.add_format({'bold': True})
        txt = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        sub_heading_sub = workbook.add_format({'bold': True, 'border': 1, 'border_color': 'black', 'num_format': '#,##0.00'})
        sheet.merge_range('A1:H2',
                          filters.get('company_name') + ':' + 'Partner Ledger',
                          head)
        date_head = workbook.add_format({'bold': True})
        sheet.merge_range('A4:B4',
                          'Target Moves: ' + filters.get('target_move'),
                          date_head)
        sheet.merge_range('C4:D4', 'Account Type: ' + ', ' .join(
            [lt or '' for lt in
             filters['account_type']]),
                          date_head)
        sheet.merge_range('E3:F3', ' Partners: ' + ', '.join(
            [lt or '' for lt in
             filters['partners']]), date_head)
        sheet.merge_range('G3:H3', ' Partner Tags: ' + ', '.join(
            [lt or '' for lt in
             filters['partner_tags']]),
                          date_head)
        sheet.merge_range('A3:B3', ' Journals: ' + ', '.join(
            [lt or '' for lt in
             filters['journals']]),
                          date_head)
        sheet.merge_range('C3:D3', ' Accounts: ' + ', '.join(
            [lt or '' for lt in
             filters['accounts']]),
                          date_head)

        if filters.get('date_from') and filters.get('date_to'):
            sheet.merge_range('E4:F4', 'From: ' + filters.get('date_from'),
                              date_head)
            sheet.merge_range('G4:H4', 'To: ' + filters.get('date_to'),
                              date_head)
        elif filters.get('date_from'):
            sheet.merge_range('E4:F4', 'From: ' + filters.get('date_from'),
                              date_head)
        elif filters.get('date_to'):
            sheet.merge_range('E4:F4', 'To: ' + filters.get('date_to'),
                              date_head)

        sheet.merge_range('A5:E5', 'Partner', sub_heading_sub)
        sheet.write('F5', 'Debit', sub_heading_sub)
        sheet.write('G5', 'Credit', sub_heading_sub)
        sheet.write('H5', 'Balance', sub_heading_sub)

        row = 4
        col = 0

        sheet.set_column('A:A', 15, '')
        sheet.set_column('B:B', 15, '')
        sheet.set_column('C:C', 30, '')
        sheet.set_column('D:D', 25, '')
        sheet.set_column('E:E', 70, '')
        sheet.set_column('F:F', 20, '')
        sheet.set_column('G:G', 20, '')
        sheet.set_column('H:H', 20, '')
        sheet.set_column('I:I', 20, '')

        for report in report_data:
            row += 1
            sheet.merge_range(row, col + 0, row, col + 4, report['name'],sub_heading_sub if filters.get('expand') else txt)
            sheet.write(row, col + 5, report['debit'], sub_heading_sub if filters.get('expand') else txt)
            sheet.write(row, col + 6, report['credit'], sub_heading_sub if filters.get('expand') else txt)
            sheet.write(row, col + 7, report['balance'], sub_heading_sub if filters.get('expand') else txt)
            
            if len(report['move_lines']) > 0:
                row += 1
                sheet.write(row, col + 0, 'Date', cell_format)
                sheet.write(row, col + 1, 'JRNL', cell_format)
                sheet.write(row, col + 2, 'Account', cell_format)
                sheet.write(row, col + 3, 'Move', cell_format)
                sheet.write(row, col + 4, 'Entry Label', cell_format)
                sheet.write(row, col + 5, 'Debit', cell_format)
                sheet.write(row, col + 6, 'Credit', cell_format)
                sheet.write(row, col + 7, 'Balance', cell_format)
            
            for r_rec in report['move_lines']:
                row += 1
                sheet.write(row, col + 0, r_rec['ldate'], txt)
                sheet.write(row, col + 1, r_rec['lcode'], txt)
                sheet.write(row, col + 2, r_rec['account_name'], txt)
                sheet.write(row, col + 3, r_rec['move_name'], txt)
                sheet.write(row, col + 4, r_rec['lname'], txt)
                sheet.write(row, col + 5, r_rec['debit'], txt)
                sheet.write(row, col + 6, r_rec['credit'], txt)
                sheet.write(row, col + 7, r_rec['balance'], txt)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()