import time
from odoo import fields, models, api, _
import io
import json
from odoo.exceptions import Warning
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter
import datetime


class DebtCollectionReport(models.TransientModel):
    _inherit = "account.common.report"
    _name = 'debt.collection.report'
    _description = 'Debt Collection Report'

 
    partner_ids = fields.Many2many("res.partner", string="Customer")
    user_ids = fields.Many2many("res.users", string="Person in Charge")
    journal_ids = fields.Many2many("account.journal", string="Payment Method")
    state = fields.Selection([
            ('all', 'All'),
            ('on_progress', 'On Progress'),
            ('wait_for_payment', 'Collection Payment'),
            ('done', 'Done'),
        ], string='Status', default='all')


    @api.model
    def view_report(self, option, title):
        r = self.env['debt.collection.report'].search([('id', '=', option[0])])
        data = {
            'model': self,
            'partners': r.partner_ids,
            'users': r.user_ids,
            'journals': r.journal_ids,
            'state': r.state,
        }

        if r.date_from:
            data.update({
                'date_from': r.date_from,
            })
        if r.date_to:
            data.update({
                'date_to': r.date_to,
            })

        filters = self.get_filter(option)
        records = self._get_report_values(data)
        currency = self._get_currency()

        return {
            'name': 'Debt Collection Report',
            'type': 'ir.actions.client',
            'tag': 'g_l',
            'filters': filters,
            'report_lines': records['Partners'],
            'currency': currency,
        }

    def get_filter(self, option):
        data = self.get_filter_data(option)

        filters = {
            'partners': ['All'],
            'users': ['All'],
            'journals': ['All'],
            'state': 'All',
            'partners_list': data.get('partners_list'),
            'users_list': data.get('users_list'),
            'journals_list': data.get('journals_list'),
            'company_name': data.get('company_name'),
        }

        if data.get('date_from'):
            filters['date_from'] = data.get('date_from')
        if data.get('date_to'):
            filters['date_to'] = data.get('date_to')

        if data.get('partner_ids'):
            filters['partners'] = self.env['res.partner'].browse(data.get('partner_ids').ids).mapped('name')

        if data.get('user_ids'):
            filters['users'] = self.env['res.users'].browse(data.get('user_ids').ids).mapped('name')

        if data.get('journal_ids'):
            filters['journals'] = self.env['account.journal'].browse(data.get('journal_ids').ids).mapped('name')

        if data.get('state') and data.get('state') != 'all':
            if data.get('state') == 'on_progress':
                filters['state'] = 'On Progress'
            elif data.get('state') == 'wait_for_payment':
                filters['state'] = 'Collection Payment'
            elif data.get('state') == 'done':
                filters['state'] = 'Done'

        return filters


    def get_filter_data(self, option):
        r = self.env['debt.collection.report'].search([('id', '=', option[0])])

        AccountDebtCollectionLine = self.env['account.debt.collection.line'].search([('debt_collection_id.state','in',['on_progress','wait_for_payment','done']),('invoice_id.branch_id','in',[self.env.branch.id, False])])
        
        company_id = self.env.company
        company_domain = [('company_id', '=', company_id.id)]
        partners = r.partner_ids if r.partner_ids else AccountDebtCollectionLine.mapped('debt_collection_id.partner_id')
        users = r.user_ids if r.user_ids else AccountDebtCollectionLine.mapped('debt_collection_id.person_in_charge')
        journals = r.journal_ids if r.journal_ids else AccountDebtCollectionLine.mapped('journal_id')

        filter_dict = {
            'partner_ids': r.partner_ids,
            'user_ids': r.user_ids,
            'journal_ids': r.journal_ids,
            'date_from': r.date_from,
            'date_to': r.date_to,
            'partners_list': [(j.id, j.name) for j in partners],
            'users_list': [(j.id, j.name) for j in users],
            'journals_list': [(j.id, j.name) for j in journals],
            'state': r.state,
            'company_id': company_id.id,
            'company_name': company_id and company_id.name,
        }

        return filter_dict


    def _get_report_values(self, data):
        docs = data['model']

        domain = [('debt_collection_id.state','in',['on_progress','wait_for_payment','done']),('invoice_id.branch_id','in',[self.env.branch.id, False])]
        
        partners = data['partners']
        if partners:
            domain += [('debt_collection_id.partner_id','in',partners.ids)]

        users = data['users']
        if users:
            domain += [('debt_collection_id.person_in_charge','in',users.ids)]

        journals = data['journals']
        if journals:
            domain += [('journal_id','in',journals.ids)]

        state = data['state']
        if state and state != 'all':
            domain += [('debt_collection_id.state','=',state)]

        if not 'date_from' in data:
            data.update({
                'date_from': datetime.date(datetime.date.today().year, 1, 1)
            })

        if not 'date_to' in data:
            data.update({
                'date_to': datetime.date(datetime.date.today().year, 12, 31)
            })
        
        AccountDebtCollectionLine = self.env['account.debt.collection.line'].search(domain)

        partner_ids = AccountDebtCollectionLine.mapped('debt_collection_id.partner_id')
        pic_ids = AccountDebtCollectionLine.mapped('debt_collection_id.person_in_charge')
        journal_ids = AccountDebtCollectionLine.mapped('journal_id')

        partner_res = self._get_partners(partner_ids, pic_ids, data)

        return {
            'doc_ids': self.ids,
            'docs': docs,
            'time': time,
            'Partners': partner_res,
        }


    def write(self, vals):
        if vals.get('partner_ids'):
            vals.update({'partner_ids': [(6, 0, vals.get('partner_ids'))]})
        elif vals.get('partner_ids') == []:
            vals.update({'partner_ids': [(5,)]})

        if vals.get('user_ids'):
            vals.update({'user_ids': [(6, 0, vals.get('user_ids'))]})
        elif vals.get('user_ids') == []:
            vals.update({'user_ids': [(5,)]})

        if vals.get('journal_ids'):
            vals.update({'journal_ids': [(6, 0, vals.get('journal_ids'))]})
        elif vals.get('journal_ids') == []:
            vals.update({'journal_ids': [(5,)]})

        if vals.get('state'):
            vals.update({'state': vals.get('state').lower()})

        res = super(DebtCollectionReport, self).write(vals)
        return res


    def _get_partners(self, partner_ids, pic_ids, data):
        partner_res = []
        for partner in partner_ids:
            for pic in pic_ids:
                domain = [('debt_collection_id.partner_id','=',partner.id),('debt_collection_id.person_in_charge','=',pic.id),('debt_collection_id.state','in',['on_progress','wait_for_payment','done']),('invoice_id.branch_id','in',[self.env.branch.id, False])]
                
                if data['journals']:
                    domain += [('journal_id','in',data['journals'].ids)]
                if data['state'] and data['state'] != 'all':
                    domain += [('debt_collection_id.state','=',data['state'])]
                if data['date_from']:
                    domain += [('invoice_date','>=',data['date_from'])]
                if data['date_to']:
                    domain += [('invoice_date','<=',data['date_to'])]

                AccountDebtCollectionLine = self.env['account.debt.collection.line'].search(domain)

                if AccountDebtCollectionLine:
                    res = {
                        'id': str(partner.id) + str(pic.id),
                        'name': partner.name,
                        'person_in_charge': pic.name,
                        'invoice_amount': sum(AccountDebtCollectionLine.mapped('amount_invoice')),
                        'total_collection_amount': sum(AccountDebtCollectionLine.mapped('amount')),
                        'debt_amount_due': sum(AccountDebtCollectionLine.mapped('amount_residual')),
                        'debt_lines': []
                    }

                    for debt_line in AccountDebtCollectionLine:
                        state = ''
                        if debt_line.debt_collection_id.state == 'on_progress':
                            state = 'On Progress'
                        elif debt_line.debt_collection_id.state == 'wait_for_payment':
                            state = 'Collection Payment'
                        elif debt_line.debt_collection_id.state == 'done':
                            state = 'Done'

                        lines = {
                            'partner': partner.name,
                            'date': debt_line.invoice_date,
                            'invoice_name': debt_line.invoice_id.name,
                            'invoice_id': debt_line.invoice_id.id,
                            'person_in_charge': pic.name,
                            'invoice_amount': debt_line.amount_invoice,
                            'debt_amount_due': debt_line.amount_residual,
                            'total_collection_amount': debt_line.amount,
                            'payment_method': debt_line.journal_id.name or '',
                            'collection_date': debt_line.date or '',
                            'state': state or '',
                        }

                        res['debt_lines'].append(lines)

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
                          self.env.company.currency_id.position,lang]
        return currency_array


    def get_dynamic_xlsx_report(self, data, response ,report_data, dfr_data):
        report_data_main = json.loads(report_data)
        output = io.BytesIO()
        name_data = json.loads(dfr_data)
        filters = json.loads(data)
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        head = workbook.add_format({'bold': True})
        sub_heading = workbook.add_format({'bold': True, 'border': 1, 'border_color': 'black'})
        txt = workbook.add_format({'border': 1})
        txt_l = workbook.add_format({'border': 1, 'bold': True})
        sheet.merge_range('A2:J3', filters.get('company_name') + ':' + name_data.get('name'), head)
        date_head = workbook.add_format({'bold': True})
        date_style = workbook.add_format({})
        if filters.get('date_from'):
            sheet.merge_range('B4:C4', 'From: ' + filters.get('date_from'), date_head)
        if filters.get('date_to'):
            sheet.merge_range('H4:I4', 'To: ' + filters.get('date_to'), date_head)

        sheet.merge_range('A5:J6', 
            '  Person in Charge: ' + ', '.join([lt or '' for lt in filters['users']]) + 
            '  Payment Method: ' + ', '.join([lt or '' for lt in filters['journals']]) + 
            '  Customer: ' + ', '.join([lt or '' for lt in filters['partners']]) + 
            '  Status : ' + filters.get('state'),
            date_head)

        sheet.write('A8', 'Customer', sub_heading)
        sheet.write('B8', 'Person in Charge', sub_heading)
        sheet.write('C8', 'Date', sub_heading)
        sheet.write('D8', 'Invoice', sub_heading)
        sheet.write('E8', 'Invoice Amount', sub_heading)
        sheet.write('F8', 'Debt Amount Due', sub_heading)
        sheet.write('G8', 'Total Collection Amount', sub_heading)
        sheet.write('H8', 'Payment Method', sub_heading)
        sheet.write('I8', 'Collection Date', sub_heading)
        sheet.write('J8', 'Status', sub_heading)

        row = 6
        col = 0

        sheet.set_column(8, 0, 15)
        sheet.set_column('B:B', 40)
        sheet.set_column(8, 2, 15)
        sheet.set_column(8, 3, 15)
        sheet.set_column(8, 4, 15)
        sheet.set_column(8, 5, 15)
        sheet.set_column(8, 6, 50)
        sheet.set_column(8, 7, 26)
        sheet.set_column(8, 8, 15)
        sheet.set_column(8, 9, 15)

        for rec_data in report_data_main:
            row += 1
            sheet.write(row + 1, col, rec_data['name'], txt)
            sheet.write(row + 1, col + 1, rec_data['person_in_charge'], txt)
            sheet.write(row + 1, col + 2, '', txt)
            sheet.write(row + 1, col + 3, '', txt)
            sheet.write(row + 1, col + 4, rec_data['invoice_amount'], txt)
            sheet.write(row + 1, col + 5, rec_data['debt_amount_due'], txt)
            sheet.write(row + 1, col + 6, rec_data['total_collection_amount'], txt)
            sheet.write(row + 1, col + 7, '', txt)
            sheet.write(row + 1, col + 8, '', txt)
            sheet.write(row + 1, col + 9, '', txt)

            for line_data in rec_data['debt_lines']:
                row += 1
                sheet.write(row + 1, col, '', txt)
                sheet.write(row + 1, col + 1, '', txt)
                sheet.write(row + 1, col + 2, line_data.get('date'), txt)
                sheet.write(row + 1, col + 3, line_data.get('invoice_name'), txt)
                sheet.write(row + 1, col + 4, line_data.get('invoice_amount'), txt)
                sheet.write(row + 1, col + 5, line_data.get('debt_amount_due'), txt)
                sheet.write(row + 1, col + 6, line_data.get('total_collection_amount'), txt)
                sheet.write(row + 1, col + 7, line_data.get('payment_method'), txt)
                sheet.write(row + 1, col + 8, line_data.get('collection_date'), txt)
                sheet.write(row + 1, col + 9, line_data.get('state'), txt)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()