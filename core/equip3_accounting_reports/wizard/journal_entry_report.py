import time
from odoo import fields, models, api, _
import io
import json
from odoo.exceptions import AccessError, UserError, AccessDenied
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class JournalEntryView(models.TransientModel):
    _name = 'journal.entry.report'

    company_id = fields.Many2one('res.company', required=True,
                                 default=lambda self: self.env.company)
    journal_ids = fields.Many2many('account.journal',
                                   string='Journals', required=True,
                                   default=[])
    account_ids = fields.Many2many("account.account", string="Accounts")    
    display_account = fields.Selection([('all', 'All'), ('movement', 'With movements'),('not_zero', 'With balance is not equal to 0')],
        string='Display Accounts', required=True, default='movement')
    target_move = fields.Selection([('all', 'All'), ('posted', 'Posted')],string='Target Move', required=True, default='posted')
    date_from = fields.Date(string="Start date")
    date_to = fields.Date(string="End date")
    move_ids = fields.Many2many("account.move", string="Moves")

    @api.model
    def view_report(self, option, tag, move_ids):
        moves_id = self.env['account.move'].search([('id','in',move_ids)])
        r = self.env['journal.entry.report'].search([('id', '=', option[0])])
        data = {
            'display_account': r.display_account,
            'model': self,
            'journals': r.journal_ids,
            'target_move': r.target_move,
            'accounts': r.account_ids,            
            'date_from': r.date_from,
            'date_to': r.date_to,
            'moves': moves_id,
            'report_name': tag,

        }
        # Updating context with applied filter values
        self = self.with_context(data)
        if r.date_from:
            data.update({
                'date_from': r.date_from,
            })
        else:
            data.update({
                'date_from': date.today().replace(day=1),
            })
        if r.date_to:
            data.update({
                'date_to': r.date_to,
            })
        else:
            data.update({
                'date_to': date.today() + relativedelta(day=31),
            })
            

        company_id = self.env.company
        company_domain = [('company_id', '=', company_id.id)]
        if r.account_ids:
            company_domain.append(('id', 'in', r.account_ids.ids))

        new_account_ids = self.env['account.account'].search(company_domain)
        data.update({'accounts': new_account_ids,})
        
        filters = self.get_filter(option)
        current_date = date.today()
        records = self._get_report_values(data)

        return {
            'name': tag,
            'type': 'ir.actions.client',
            'tag': tag,
            'filters': filters,
            'je_lines': records['Accounts'],
        }

    def get_filter(self, option):
        data = self.get_filter_data(option)
        filters = {}
        if data.get('journal_ids'):
            filters['journals'] = self.env['account.journal'].browse(
                data.get('journal_ids')).mapped('code')
        else:
            filters['journals'] = ['All']

        if data.get('move_ids'):
            filters['moves'] = self.env['account.move'].browse(
                data.get('move_ids')).mapped('id')
        else:
            filters['moves'] = ['All']

        if data.get('account_ids', []):
            filters['accounts'] = self.env['account.account'].browse(
                data.get('account_ids', [])).mapped('code')
        else:
            filters['accounts'] = ['All']
        if data.get('target_move'):
            filters['target_move'] = data.get('target_move')
        else:
            filters['target_move'] = 'posted'
        if data.get('date_from'):
            filters['date_from'] = data.get('date_from')
        else:
            filters['date_from'] = False
        if data.get('date_to'):
            filters['date_to'] = data.get('date_to')
        else:
            filters['date_to'] = False

        filters['accounts_list'] = data.get('accounts_list')
        filters['journals_list'] = data.get('journals_list')
        filters['moves_list'] = data.get('moves_list')
        filters['company_name'] = data.get('company_name')
        filters['target_move'] = filters.get('target_move').capitalize()
        return filters

    def get_filter_data(self, option):
        r = self.env['journal.entry.report'].search([('id', '=', option[0])])
        default_filters = {}
        company_id = self.env.company
        company_domain = [('company_id', '=', company_id.id)]
        journals = r.journal_ids if r.journal_ids else self.env['account.journal'].search(company_domain)
        moves = r.move_ids if r.move_ids else self.env['account.move'].search(company_domain)
        currency_ids = self.env['res.currency'].search([('active', '=', True)])
        accounts = self.account_ids if self.account_ids else self.env['account.account'].search(company_domain)
        
        filter_dict = {
            'journal_ids': r.journal_ids.ids,
            'move_ids': r.move_ids.ids,
            'account_ids': r.account_ids.ids,
            'company_id': company_id.id,
            'date_from': r.date_from,
            'date_to': r.date_to,
            'target_move': r.target_move,
            'journals_list': [(j.id, j.name, j.code) for j in journals],
            'moves_list': [(m.id, m.name) for m in moves],
            'accounts_list': [(a.id, a.name) for a in accounts],            
            'company_name': company_id and company_id.name,
        }
        filter_dict.update(default_filters)
        return filter_dict

    def _get_report_values(self, data):
        docs = data['model']
        display_account = data['display_account']
        init_balance = True
        accounts = self.env['account.account'].search([])
        if not accounts:
            raise UserError(_("No Accounts Found! Please Add One"))
        account_res = self._get_accounts(accounts, init_balance,display_account, data)
        return {
            'doc_ids': self.ids,
            'docs': docs,
            'time': time,
            'Accounts': account_res,
        }

    @api.model
    def create(self, vals):
        vals['target_move'] = 'posted'
        res = super(JournalEntryView, self).create(vals)
        return res

    def write(self, vals):
        if vals.get('target_move'):
            vals.update({'target_move': vals.get('target_move').lower()})
        if vals.get('journal_ids'):
            vals.update({'journal_ids': [(6, 0, vals.get('journal_ids'))]})
        if not vals.get('journal_ids'):
            vals.update({'journal_ids': [(5,)]})
        if vals.get('move_ids'):
            vals.update({'move_ids': [(6, 0, vals.get('move_ids'))]})
        if not vals.get('move_ids'):
            vals.update({'move_ids': [(5,)]})
        if vals.get('account_ids'):
            vals.update({'account_ids': [(4, j) for j in vals.get('account_ids')]})
        if not vals.get('account_ids'):
            vals.update({'account_ids': [(5,)]})

        res = super(JournalEntryView, self).write(vals)
        return res

    def _get_accounts(self, accounts, init_balance, display_account, data):
        moveids = self.env['account.move']
        domain = [('company_id', '=', self.env.company.id)]

        if data['target_move'] == 'posted':
            domain.append(('state', '=', 'posted'))
        else:
            domain.append(('state', 'in', ['draft','posted']))

        if data.get('date_from'):
            domain.append(('date', '>=', data.get('date_from')))
        if data.get('date_to'):
            domain.append(('date', '<=', data.get('date_to')))

        if data['journals']:
            domain.append(('journal_id', 'in', str(tuple(data['journals'].ids) + tuple([0]))))

        if data['moves']:
            domain.append(('id', 'in', tuple(data['moves'].ids) + tuple([0])))

        # self.env['account.move'].search_read(domain, ['id'])
        result_query = self.env['account.move'].search_read(domain, ['id','name','journal_id','date','partner_id','ref','line_ids'])
        for line_result in result_query:
            if line_result['line_ids']:
                move_lines =[]
                for line in line_result['line_ids']:
                    line_res = self.env['account.move.line'].search_read([('id', '=', line)], ['id','account_id','name','journal_id','date','analytic_account_id','partner_id','ref','debit','credit','currency_id'])
                    cek1 = self.env['account.move.line'].search([('id','=',str(line_res[0]['id']))])
                    line_res[0]['currency_id'] = {'id':cek1.currency_id.id, 'name' : cek1.currency_id.name, 'decimal_places' : cek1.currency_id.decimal_places}
                    move_lines.append(line_res[0])
                line_result['move_lines'] = move_lines
        return result_query

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

    def get_dynamic_xlsx_report(self, options, response, report_data, dfr_data):
        i_data = str(report_data)
        filters = json.loads(options)
        j_data = dfr_data
        rl_data = json.loads(j_data)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        head = workbook.add_format({'bold': True})
        side_heading_main = workbook.add_format({'bold': True})
        side_heading_main1 = workbook.add_format({})
        
        txt_name_bold = workbook.add_format({'bold': True, 'border': 1,'border_color': 'black'})
        txt_name = workbook.add_format({'border': 1,'border_color': 'black'})
        txt = workbook.add_format({'num_format': '#,##0.00', 'border': 1,'border_color': 'black'})
        sheet.merge_range('A2:G3', filters.get('company_name') + ' : ' + i_data, head)
        
        #row A5
        if rl_data['je_lines']:
            row = 5
            col = 0
            for a in rl_data['je_lines']:
                sheet.write(row, col, a['name'], side_heading_main)
                row+=1
                sheet.write(row, col, 'Journal', side_heading_main)
                sheet.write(row, col+1, (a['journal_id'])[1], side_heading_main1)
                sheet.write(row, col+3, 'Partner', side_heading_main)
                sheet.write(row, col+4, (a['partner_id'])[1] if a['partner_id'] else '-', side_heading_main1)
                row+=1
                sheet.write(row, col, 'Date', side_heading_main)
                sheet.write(row, col+1, a['date'], side_heading_main1)
                sheet.write(row, col+3, 'Reference', side_heading_main)
                sheet.write(row, col+4, a['ref'], side_heading_main1)
                row+=1
                sheet.write(row, 0, 'Account', txt_name_bold)
                sheet.write(row, 1, 'Date', txt_name_bold)
                sheet.write(row, 2, 'Partner', txt_name_bold)
                sheet.write(row, 3, 'Label', txt_name_bold)
                sheet.write(row, 4, 'Analytic Account', txt_name_bold)
                sheet.write(row, 5, 'Debit', txt_name_bold)
                sheet.write(row, 6, 'Credit', txt_name_bold)
                row+=1
                for b in a['move_lines']:
                    sheet.write(row, 0, (b['account_id'])[1], txt_name)
                    sheet.write(row, 1, b['date'], txt_name)
                    sheet.write(row, 2, (b['partner_id'])[1] if b['partner_id'] else '-', txt_name)
                    sheet.write(row, 3, b['ref'], txt_name)
                    sheet.write(row, 4, (b['analytic_account_id'])[1] if b['analytic_account_id'] else '-', txt_name)
                    sheet.write(row, 5, b['debit'], txt)
                    sheet.write(row, 6, b['credit'], txt)
                    row+=1
                row+=2
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

        