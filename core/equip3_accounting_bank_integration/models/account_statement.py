from odoo import api, fields, models, tools, _ , exceptions
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import pytz, logging, requests, json, sys, traceback
from pytz import timezone, UTC
from lxml import etree

_logger = logging.getLogger(__name__)
headers = {'content-type': 'application/json', 'accept': 'application/json'}

class AccountBankStatementIntegrate(models.TransientModel):
    _name = "account.bank.statement.integrate"

    name = fields.Char(string="Number", default='Draft', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Bank Journal', required=True, domain=[('type','in',['bank','cash'])])
    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    status = fields.Char(string="Status", readonly=True)
    created_by = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user, readonly=True)
    created_date = fields.Date(string='Created Date', default=fields.Datetime.now, readonly=True)
    state = fields.Selection([('draft', 'Draft'),
                              ('imported', 'Imported'),
                              ('failed', 'Failed')],
                              default="draft",
                              string='state')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            seq_date = None
            if 'created_date' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['created_date']))
            vals['name'] = self.env['ir.sequence'].next_by_code('account.bank.statement.integrate.sequence', sequence_date=seq_date) or _('New')
        result = super(AccountBankStatementIntegrate, self).create(vals)
        return result

    def action_import(self):
        account_number = self.journal_id.bank_account_id.acc_number
        start_date = fields.Datetime.from_string(self.date_from).strftime('%Y-%m-%d')
        end_date = fields.Datetime.from_string(self.date_to).strftime('%Y-%m-%d')
        journal_id = str(self.journal_id.id)
        company_id = str(self.env.company.id)
        create_uid = str(self.created_by.id)

        param = {'account_number': account_number, 
                 'start_date': start_date, 
                 'end_date': end_date, 
                 'journal_id': journal_id, 
                 'company_id': company_id,
                 'create_uid' : create_uid}

        ICP = self.env['ir.config_parameter'].sudo()
        # domain = ICP.get_param('bank_integrate_url', False)
        # user = ICP.get_param('bank_integrate_username', False)
        # password = ICP.get_param('bank_integrate_password', False)
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
                    self.update({'state' : 'imported', 'status' : 'Success'})
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
                    self.update({'state' : 'failed', 'status' : 'fail'})
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
        # except:
        #     raise ValidationError("Not connect to API Chat Server. Limit reached or not active")