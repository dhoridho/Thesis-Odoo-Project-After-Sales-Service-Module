from odoo import api, fields, models, tools, _ , exceptions
from odoo.exceptions import UserError, ValidationError
import pytz, logging, requests, json, sys, traceback, re
from datetime import datetime, date, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from pytz import timezone, UTC
from dateutil.relativedelta import relativedelta



_logger = logging.getLogger(__name__)
headers = {'content-type': 'application/json', 'accept': 'application/json'}


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    transaction_date = fields.Date(string='Date')

    @api.model
    def default_get(self, fields):
        res = super(AccountBankStatementLine, self).default_get(fields)
        print(res)
        if 'company_id' in fields:
            res['company_id'] = self.statement_id.company_id.id or self.env.company.id
        if 'currency_id' in fields:
            res['currency_id'] = self.statement_id.company_id.currency_id.id or self.env.company.currency_id.id
        return res

    @api.onchange('foreign_currency_id', 'amount_currency', 'date')
    def _onchange_foreign_currency_currency(self):
        for rec in self:
            if rec.foreign_currency_id:
                if rec.amount_currency:
                    balance = rec.foreign_currency_id._convert(rec.amount_currency, rec.currency_id, self.env.company, rec.date or fields.Date.context_today(rec))
                    rec.amount = balance

    @api.model
    def scheduler_queue_generate_bank_statement_journal(self):
        self._cr.execute('''
            SELECT l.id, l.amount, l.payment_ref, s.date, s.journal_id, 
                    j.default_account_id, j.suspense_account_id, j.company_id
            FROM account_bank_statement_line l
            LEFT JOIN account_bank_statement s ON (l.statement_id = s.id)
            LEFT JOIN account_journal j ON (s.journal_id = j.id)
            WHERE l.statement_id IS NOT NULL
            AND l.move_id IS NULL
            AND j.default_account_id IS NOT NULL
            AND j.suspense_account_id IS NOT NULL''')
        account_bank_statement_lines = self._cr.dictfetchall()

        account_bank_statement_line_ids = []
        for line in account_bank_statement_lines: 
            vals = {
                'name': '/',
                'ref': line['payment_ref'] or '',
                'date': line['date'],
                'journal_id': line['journal_id'],
            }
            
            company_id = self.env['res.company'].browse(line['company_id'])
            default_account_id = self.env['account.account'].browse(line['default_account_id'])
            suspense_account_id = self.env['account.account'].browse(line['suspense_account_id'])
      
            if default_account_id and suspense_account_id:
                first_currency = default_account_id and default_account_id.currency_id or company_id.currency_id
                second_currency = suspense_account_id and suspense_account_id.currency_id or company_id.currency_id
                
                first_payment_rate = self.env['res.currency']._get_conversion_rate(
                            company_id.currency_id,
                            first_currency,
                            company_id,
                            line['date'],
                        )

                second_payment_rate = self.env['res.currency']._get_conversion_rate(
                            company_id.currency_id,
                            second_currency,
                            company_id,
                            line['date'],
                        )

                first_vals = {
                    'debit' : line['amount'] > 0 and abs(line['amount']) or 0.0, 
                    'credit' : line['amount'] < 0 and abs(line['amount']) or 0.0, 
                    'name' : line['payment_ref'] or '', 
                    'date' : line['date'],
                    'journal_id' : line['journal_id'],
                    'account_id' : line['default_account_id'],
                    'currency_id' : first_currency.id or None,
                    'company_currency_id' : company_id.currency_id.id or None, 
                    'amount_currency' : line['amount']*first_payment_rate or 0.0,
                    'company_id' : company_id.id,
                }

                second_vals = {
                    'debit' : line['amount'] < 0 and abs(line['amount']) or 0.0, 
                    'credit' : line['amount'] > 0 and abs(line['amount']) or 0.0, 
                    'name' : line['payment_ref'] or '', 
                    'date' : line['date'],
                    'journal_id' : line['journal_id'],
                    'account_id' : line['suspense_account_id'],
                    'currency_id' : second_currency.id or None,
                    'company_currency_id' : company_id.currency_id.id or None, 
                    'amount_currency' : -line['amount']*second_payment_rate or 0.0,
                    'company_id' : company_id.id,
                }
 
                vals.update({'line_ids' : [(0,0, first_vals),(0,0, second_vals)]})

                move_id = self.env['account.move'].create(vals)

                last_move_lines = self.env['account.move.line'].sudo().search([('move_id', '=', move_id.id)], order='id asc')
                for l in last_move_lines:
                    l._compute_balance()
                    
                bank_statement_line = self.env['account.bank.statement.line'].browse(line['id'])

                bank_statement_line.sudo().write({'move_id' : move_id.id})
                account_bank_statement_line_ids.append(line['id'])
                
        return account_bank_statement_line_ids


class AccountBankStatement(models.Model):
    _inherit = "account.bank.statement"
    

    date_from = fields.Date(string='From Date', default = date.today() - timedelta(days=30))
    date_to = fields.Date(string='To Date', default = date.today())
    hide_mutation_button = fields.Boolean(default=True, compute='check_Journal_setting')

    @api.onchange('journal_id')
    def check_Journal_setting(self):
        hide_mutation_button = True
        domain = self.env.company.bank_integrate_url
        user = self.env.company.bank_integrate_username
        password = self.env.company.bank_integrate_password
        if self.journal_id:
            for payment_method in self.journal_id.outbound_payment_method_ids:
                if payment_method.code in ['online_transfer','llg','rtgs']:
                    if domain and user and password:
                        hide_mutation_button = False
                    break
        self.hide_mutation_button = hide_mutation_button


    @api.onchange('date_from')
    def onchange_date_from(self):
        range_date = (fields.Date.context_today(self) - fields.Date.from_string(self.date_from)).days
        if range_date > 30:
            self.date_from = fields.Date.context_today(self) - relativedelta(days=30)
    
    def action_get_mutation_data(self):
        account_number = self.journal_id.bank_account_id.acc_number
        start_date = fields.Datetime.from_string(self.date_from).strftime('%Y-%m-%d')
        end_date = fields.Datetime.from_string(self.date_to).strftime('%Y-%m-%d')
        journal_id = str(self.journal_id.id)
        company_id = str(self.company_id.id)
        create_uid = str(self.user_id.id)

        param = {'account_number': account_number, 
                 'start_date': start_date, 
                 'end_date': end_date, 
                 'journal_id': journal_id, 
                 'company_id': company_id,
                 'create_uid' : create_uid}

        ICP = self.env['ir.config_parameter'].sudo()
        domain = self.env.company.bank_integrate_url
        user = self.env.company.bank_integrate_username
        password = self.env.company.bank_integrate_password
        try:
            param_login = {
                          'email': user,
                          'password': password
                        }
            
            headers['Content-Type'] = 'application/json'
            request_server_login = requests.post(f'{domain+"api/v1/login"}', params=param_login, headers=headers, verify=False)
            response_login = json.loads(request_server_login.text)
            if request_server_login.status_code == 200:
                headers['authorization'] = response_login['type'] + ' ' + response_login['token']
                request_server = requests.post(f'{domain+"api/v1/account-bank-statement"}', params=param, headers=headers, verify=False)
                response = json.loads(request_server.text)
                if request_server.status_code == 200:
                    data = (((response['data'])['response'])['data'])['Data']
                    self.update({'line_ids' : [(5,)]})
                    line_ids = []
                    star_balance = (((response['data'])['response'])['data'])['StartBalance']
                    # currency_id = self.env.company.currency_id
                    # if (((response['data'])['response'])['data'])['Currency']:
                    #     currency_id = self.env['res.currency'].search([('name', '=' , (((response['data'])['response'])['data'])['Currency'])])
                    #     if len(currency_id) != 1:
                    #         currency_id = self.env.company.currency_id
                    for x in data:
                        line_id={}
                        date_object = fields.Datetime.from_string(datetime.strptime(x['TransactionDate'] +'/'+ str(self.date.year), '%d/%m/%Y'))
                        line_id['date'] = date_object
                        line_id['payment_ref'] = re.sub(' +', ' ', x['Trailer'])
                        line_id['partner_id'] = False if x['TransactionName'] else x['TransactionName']
                        line_id['ref'] = re.sub(' +', ' ', x['Trailer'])
                        line_id['transaction_type'] = x['TransactionType']
                        line_id['amount'] = -x['TransactionAmount'] if x['TransactionType'] == 'D' else x['TransactionAmount']
                        line_ids.append((0,0,line_id))
                    self.write({'line_ids' : line_ids,
                                'balance_start' : star_balance
                                })
                    return {
                                'type': 'ir.actions.client',
                                'tag': 'display_notification',
                                'params': {
                                    'type': 'success',
                                    'message': _('Success'),
                                    'next': {'type': 'ir.actions.act_window_close'},
                                }
                            }
                else:
                    return {
                                'type': 'ir.actions.client',
                                'tag': 'display_notification',
                                'params': {
                                    'type': 'danger',
                                    'message': _(response['message']),
                                    'next': {'type': 'ir.actions.act_window_close'},
                                    'sticky': True,
                                }
                            }
            else:
                raise UserError(response_login)
        except Exception as e:
            tb = sys.exc_info()
            raise UserError(e.with_traceback(tb[2]))