import time
from odoo import fields, models, api, _

import io
import json
from datetime import date
from odoo.exceptions import AccessError, UserError, AccessDenied

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class CustomerStatement(models.Model):
    _inherit = ['account.common.report', 'portal.mixin', 'mail.thread', 'mail.activity.mixin', 'sequence.mixin']
    _name = 'customer.statement'
    _mail_post_access = 'read'

    name = fields.Text(string='name')
    partner_ids = fields.Many2many('res.partner', string='Partner')
    overdue_template = fields.Text(string='Template')
    company_ids = fields.Many2many('res.company', string='Companies')
    report_currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    def get_mail_template (self,partner_id):
        partner_id = self.env['res.partner'].browse(partner_id)

        today = fields.Date.today()
        move_ids = self.env['account.move'].search([
            ('invoice_date', '<=', today),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('partner_id', '=', partner_id.id),
            ('payment_state', 'in', ('not_paid', 'in_payment', 'partial')),
        ])

        if move_ids:
            temp_inv = self.env['followup.invoice.tmp'].create({
                'partner_id' : partner_id.id,
                'move_id' : move_ids,
                'date' : today,
            })
            return {
                'context' : {
                    "default_template_id" : self.env.ref(
                        "equip3_accounting_operation.email_template_invoice_followup_notification"
                    ).id,
                    "overdue_template" : temp_inv.overdue_template,
                    "email_from" : self.env.company.email,
                    "date" : today,
                    "email_to" : temp_inv.partner_id.email,
                }
            }
            
    @api.model
    def view_report(self, option):
        r = self.env['customer.statement'].search([('id', '=', option[0])])
        data = {
            'model': self,
            'partners': r.partner_ids,
            'overdue_template':r.overdue_template,
            'companies' : r.company_ids,
            'currency_id': r.report_currency_id,
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
        
    

        return {
            'name': "Customer Statement",
            'type': 'ir.actions.client',
            'tag': 'cust_statement',
            'filters': filters,
            'report_lines': records['Partners'],
            'currency': currency
        }

    def get_filter(self, option):
        data = self.get_filter_data(option)
        filters = {}
        if data.get('date_from'):
            filters['date_from'] = data.get('date_from')
        if data.get('date_to'):
            filters['date_to'] = data.get('date_to')

        filters['company_id'] = data.get('company_id')
        filters['company_name'] = data.get('company_name')

        if data.get('partners'):
            filters['partners'] = self.env['res.partner'].browse(
                data.get('partners')).mapped('name')
        else:
            filters['partners'] = ['All']

        filters['partners_list'] = data.get('partners_list')

        if data.get('companies'):
            filters['companies'] = self.env['res.company'].browse(
                data.get('companies')).mapped('name')
        else:
            filters['companies'] = ['All']

        filters['companies_list'] = data.get('companies_list')
        filters['currencies'] = data.get('currencies')
        return filters

    def get_filter_data(self, option):
        r = self.env['customer.statement'].search([('id', '=', option[0])])
        default_filters = {}
        company_id = self.env.company
        company_domain = [('company_id', '=', company_id.id)]
        partner = r.partner_ids if r.partner_ids else self.env[
            'res.partner'].search([])
        company = r.company_ids if r.company_ids else self.env[
            'res.company'].search([])
        currency_ids = self.env['res.currency'].search([('active', '=', True)])

        filter_dict = {
            'company_id': company_id.id,
            'date_from': r.date_from,
            'date_to': r.date_to,
            'company_name': company_id and company_id.name,
            'partners': r.partner_ids.ids,
            'partners_list': [(p.id, p.name) for p in partner],
            'companies': r.company_ids.ids,
            'companies_list': [(p.id, p.name) for p in company],
            'currencies': [{'name': currency_id.name, 'id': currency_id.id,} for currency_id in currency_ids]
        }
        filter_dict.update(default_filters)
        return filter_dict

    def _get_report_values(self, data):
        docs = data['model']
        partner_res = self._get_partners(data)

        return {
            'doc_ids': self.ids,
            'docs': docs,
            'time': time,
            'Partners': partner_res,
        }

    @api.model
    def create(self, vals):
        vals['overdue_template'] = self.env['ir.config_parameter'].sudo().get_param('overdue_template', False)
        res = super(CustomerStatement, self).create(vals)
        return res

    def write(self, vals):
        if vals.get('partner_ids'):
            vals.update(
                {'partner_ids': [(4, j) for j in vals.get('partner_ids')]})
        if not vals.get('partner_ids'):
            vals.update({'partner_ids': [(5,)]})

        if vals.get('company_ids'):
            vals.update(
                {'company_ids': [(4, k) for k in vals.get('company_ids')]})
        if not vals.get('company_ids'):
            vals.update({'company_ids': [(5,)]})
        res = super(CustomerStatement, self).write(vals)
        return res


    def _get_partners(self, data):
        cr = self.env.cr
        move_line = self.env['account.move.line']
        # currency_id = self.env.company.currency_id
        # symbol = currency_id.symbol
        # rounding = currency_id.rounding
        # position = currency_id.position
        company_id = self.env.company
        curr_currency = data['currency_id']
        symbol = curr_currency.symbol
        rounding = curr_currency.rounding
        position = curr_currency.position

        currency_rate = 0
        currency_id = curr_currency
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
            rate_ids = currency_id.rate_ids.filtered(lambda r: r.name <= date.today()).sorted(key=lambda r: r.name)
            if rate_ids:
                currency_rate = rate_ids[-1].mr_rate
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

        if data.get('companies'):
            i = 0
            s = '%s'
            while i < len(data.get('companies')):
                if i !=0:
                    where_params.insert(0,data.get('companies')[i].id)
                    where_params.insert(len(where_params)-1,data.get('companies')[i].id)
                    s += ',%s'
                else:
                    where_params[0] = data.get('companies')[i].id
                    where_params[len(where_params)-1] = data.get('companies')[i].id
                i+=1
            new_final_filter = new_final_filter.replace('("l"."company_id" in (%s))', '("l"."company_id" in ('+ s +'))')
            c_ids = [k.id for k in data.get('companies')]
        else:
            c_ids = [self.env.company.id]

        request = "SELECT a.id from account_account as a \
                   inner join account_account_type as b on a.user_type_id = b.id \
                   where b.type in ('receivable', 'payable') and a.company_id in %s" % str(tuple(c_ids) + tuple([0]))
        self.env.cr.execute(request)
        accounts = self.env.cr.dictfetchall()

        WHERE = "WHERE l.account_id IN %s" % str(tuple(acc_id['id'] for acc_id in accounts) + tuple([0]))

        if data.get('date_from'):
            new_final_filter += " AND l.date >= '%s'" % data.get('date_from')
        if data.get('date_to'):
            new_final_filter += " AND l.date <= '%s'" % data.get('date_to')

        if data.get('partners'):
            WHERE += ' AND p.id IN %s' % str(
                tuple(data.get('partners').ids) + tuple([0]))

        sql = ('''SELECT l.id AS lid,l.partner_id AS partner_id,m.id AS move_id, 
                    l.account_id AS account_id, l.date AS ldate, j.code AS lcode, l.currency_id, 
                    l.amount_currency, l.ref AS lref, l.name AS lname, 
                    COALESCE(l.debit,0) AS debit, COALESCE(l.credit,0) AS credit, 
                    COALESCE(SUM(l.balance),0) AS balance,
                    m.name AS move_name, c.symbol AS currency_code,c.position AS currency_position, p.name AS partner_name, p.email as partner_email,
                    m.date as date,
                    m.invoice_date_due as due_date,
                    m.payment_reference as communication
                    FROM account_move_line l
                    JOIN account_move m ON (l.move_id=m.id and m.move_type ='out_invoice' and m.state = 'posted')
                    JOIN account_account a ON (l.account_id=a.id)
                    LEFT JOIN res_currency c ON (l.currency_id=c.id)
                    LEFT JOIN res_partner p ON (l.partner_id=p.id)
                    JOIN account_journal j ON (l.journal_id=j.id)
                    JOIN account_account acc ON (l.account_id = acc.id) '''
                    + WHERE + new_final_filter + ''' and m.payment_state !='paid' GROUP BY l.id, m.id,  l.account_id, l.date, j.code, l.currency_id, l.amount_currency, l.ref, l.name, m.name, c.symbol, c.position, p.name, p.email, m.payment_reference, m.date, m.invoice_date_due''' )
        
        params = tuple(where_params)
        cr.execute(sql, params)

        partner_res = []
        numb = 0

        for row in cr.dictfetchall():
            partner_id = list(filter(lambda x: x['partner_id'] == row['partner_id'], partner_res))
            today = fields.Date.today()
            if partner_id:
                partner_id[0]['lines'].append(row)
                partner_id[0]['total_amount_residual'] = partner_id[0]['total_amount_residual'] + row['balance']
                if row['due_date']:
                    due_date = row['due_date']
                    if due_date < today:
                        partner_id[0]['overdue_balance'] = partner_id[0]['overdue_balance'] + row['balance']
                    if due_date > today:
                        partner_id[0]['upcoming_balance'] = partner_id[0]['upcoming_balance'] + row['balance']
            else:
                partner = self.env['res.partner'].search([('id', '=', row['partner_id'])])
                company_address = self.address()
                partner_address = self.partner_address(partner)
                template_id = self.env.ref('equip3_accounting_reports.email_template_customer_statement', raise_if_not_found=False).id
                res={}
                res['number'] = numb
                res['partner_id'] = row['partner_id']
                res['partner_name'] = row['partner_name']
                res['partner_email'] = row['partner_email']
                res['partner'] = partner
                res['partner_address'] = partner_address
                res['company_address'] = company_address
                res['overdue_template'] = data['overdue_template']
                res['template_id'] = template_id
                res['total_amount_residual'] = row['balance']
                if row['due_date']:
                    due_date = row['due_date']
                    if due_date < today:
                        res['overdue_balance'] = row['balance']
                        res['upcoming_balance'] = 0.0
                    elif due_date > today:
                        res['overdue_balance'] = 0.0
                        res['upcoming_balance'] = row['balance']
                    else:
                        res['overdue_balance'] = 0.0
                        res['upcoming_balance'] = 0.0
                else:
                    res['overdue_balance'] = 0.0
                    res['upcoming_balance'] = 0.0
                res['lines'] = [row]
                partner_res.append(res)
                numb = numb + 1

        for tmp_partner in partner_res:
            tmp_partner['total_amount_residual'] = round(tmp_partner['total_amount_residual'] * currency_rate, 2)
            tmp_partner['overdue_balance'] = round(tmp_partner['overdue_balance'] * currency_rate, 2)
            tmp_partner['upcoming_balance'] = round(tmp_partner['upcoming_balance'] * currency_rate, 2)
            if position == "before":
                tmp_partner['total_amount_residual'] = symbol + " " + "{:,.2f}".format(tmp_partner['total_amount_residual'])
                tmp_partner['overdue_balance'] = symbol + " " + "{:,.2f}".format(tmp_partner['overdue_balance'])
                tmp_partner['upcoming_balance'] = symbol + " " + "{:,.2f}".format(tmp_partner['upcoming_balance'])
            else:
                tmp_partner['total_amount_residual'] = "{:,.2f}".format(tmp_partner['total_amount_residual']) + " " + symbol
                tmp_partner['overdue_balance'] = "{:,.2f}".format(tmp_partner['overdue_balance']) + " " + symbol
                tmp_partner['upcoming_balance'] = "{:,.2f}".format(tmp_partner['upcoming_balance']) + " " + symbol
            for tmp_rec in tmp_partner['lines']:
                tmp_rec['debit'] = round(tmp_rec['debit'] * currency_rate, 2)
                tmp_rec['credit'] = round(tmp_rec['credit'] * currency_rate, 2)
                tmp_rec['balance'] = round(tmp_rec['balance'] * currency_rate, 2)
                if position == "before":
                    tmp_rec['debit'] = symbol + " " + "{:,.2f}".format(tmp_rec['debit'])
                    tmp_rec['credit'] = symbol + " " + "{:,.2f}".format(tmp_rec['credit'])
                    tmp_rec['balance'] = symbol + " " + "{:,.2f}".format(tmp_rec['balance'])
                else:
                    tmp_rec['debit'] = "{:,.2f}".format(tmp_rec['debit']) + " " + symbol
                    tmp_rec['credit'] = "{:,.2f}".format(tmp_rec['credit']) + " " + symbol
                    tmp_rec['balance'] = "{:,.2f}".format(tmp_rec['balance']) + " " + symbol
        return partner_res

    def address(self):
        address = ((self.env.company.street + "\n" if self.env.company.street else "") 
                  + (self.env.company.street2 + '\n' if self.env.company.street2 else "") 
                  + (self.env.company.city + " " if self.env.company.city else "") 
                  + (self.env.company.state_id.name + " " if self.env.company.state_id else "") 
                  + (self.env.company.country_id.name + " " if self.env.company.country_id else "")
                  + (self.env.company.zip + " " if self.env.company.zip else ""))
        return address

    def partner_address(self, partner_id):
        address = ((partner_id.street + "\n" if partner_id.street else "") 
                  + (partner_id.street2 + '\n' if partner_id.street2 else "") 
                  + (partner_id.city + " " if partner_id.city else "") 
                  + (partner_id.state_id.name + " " if partner_id.state_id else "") 
                  + (partner_id.country_id.name + " " if partner_id.country_id else "")
                  + (partner_id.zip + " " if partner_id.zip else ""))
        return address

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

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        cell_format = workbook.add_format({'bold': True, 'border': 0})
        sheet = workbook.add_worksheet()
        head = workbook.add_format({'bold': True})

        txt = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        sub_heading_sub = workbook.add_format({'bold': True, 'border': 1, 'border_color': 'black'})
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

        sheet.merge_range('A5:E5', 'Partner', cell_format)
        sheet.write('F5', 'Debit', cell_format)
        sheet.write('G5', 'Credit', cell_format)
        sheet.write('H5', 'Balance', cell_format)

        row = 4
        col = 0

        sheet.set_column(0, 0, 15)
        sheet.set_column(1, 1, 15)
        sheet.set_column(2, 2, 25)
        sheet.set_column(3, 3, 15)
        sheet.set_column(4, 4, 36)
        sheet.set_column(5, 5, 15)
        sheet.set_column(6, 6, 15)
        sheet.set_column(7, 7, 15)

        for report in report_data:

            row += 1
            sheet.merge_range(row, col + 0, row, col + 4, report['name'],
                              sub_heading_sub)
            sheet.write(row, col + 5, report['debit'], sub_heading_sub)
            sheet.write(row, col + 6, report['credit'], sub_heading_sub)
            sheet.write(row, col + 7, report['balance'], sub_heading_sub)
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


class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'


    @api.model
    def get_record_data(self, values):
        result = super(MailComposer, self).get_record_data(values)
        if 'default_subject' in self._context:
            result['subject'] = self._context.get('default_subject')
        return result

# class CustomerStatementLine(models.Model):
#     _name = 'customer.statement.line'
#     _description = 'Customer Statment Line'
    
#     line_id = fields.Many2one('customer.statement', string='Customer Statement')
#     invoice_id = fields.Many2one('account.move', string="Invoice")
#     reference_number = fields.Char(string='Reference Number', related='invoice_id.name')
#     date = fields.Date(string="Date", related='invoice_id.date')
#     due_date = fields.Date(string="Due Date", related='invoice_id.invoice_date_due')
#     communication = fields.Char(string='Reference Number', related='invoice_id.payment_reference')
#     expected_date = fields.Date(string="Expected Date")
#     excluded = fields.Boolean(string="Excluded")
#     currency_id = fields.Many2one('res.currency', string='Currency', related='invoice_id.currency_id')
#     amount_residual = fields.Monetary(string='Amount Due', related='invoice_id.amount_residual')


    