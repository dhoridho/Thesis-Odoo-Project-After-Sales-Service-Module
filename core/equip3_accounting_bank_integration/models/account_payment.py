from odoo import api, fields, models, tools, _ , exceptions
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import pytz, logging, requests, json, sys, traceback
from pytz import timezone, UTC
from lxml import etree

_logger = logging.getLogger(__name__)
headers = {'content-type': 'application/json', 'accept': 'application/json'}


class Accountaccount(models.Model):
    _inherit = "account.move"

    state = fields.Selection(selection=[
            ('draft', 'Draft'),
            ('to_approve', 'Waiting For Approval'),
            ('confirmed', 'Confirmed'),
            ('posted', 'Posted'),
            ('cancel', 'Cancelled'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('expired', 'Expired'),
            ('failed', 'Payment Failed')
        ], string='Status', required=True, readonly=True, copy=False, tracking=True,
        default='draft')


    def action_confirm(self):
        for record in self:
            record.state = 'confirmed'

class AccountPayment(models.Model):
    _inherit = "account.payment"

    online_payment_status = fields.Char('Online Payment Status', readonly=True)

    @api.model
    def _get_method_codes_for_api(self):
        return ['online_transfer','llg','rtgs']

    @api.model
    def _get_method_codes_using_bank_account(self):
        res = super(AccountPayment, self)._get_method_codes_using_bank_account()
        res.extend(self._get_method_codes_for_api())
        return res
    
    def action_post(self):
        super(AccountPayment, self).action_post()
        msg = self._integrate_api()
        if msg != None:
            response = json.loads(msg.text)
            if 'errors' in response:
                # text= str(response["message"]) + '\n'
                # for key, value in response["errors"].items():
                #     text += str(key) + ' : ' + str(value) + '\n'
                # raise UserError(text)
                self.update({'state' : 'failed', 'online_payment_status' : msg.text})            
            else:
                type_message = 'success' if self.online_payment_status == 'Success' else 'danger'
                if type_message == 'danger':
                    raise ValidationError(self.online_payment_status)
                return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'type': type_message,
                            'message': _(self.online_payment_status),
                            'next': {'type': 'ir.actions.act_window_close'},
                            'sticky': False if self.online_payment_status == 'Success' else True,
                        }
                    }        

    @api.model
    def _integrate_api(self):
        if self.state == 'posted' and self.payment_method_id.code in self._get_method_codes_for_api():
            transfer_type=False
            if self.journal_id.bank_id.id == self.partner_bank_id.bank_id.id:
                transfer_type = 0
            else:
                if self.payment_method_id.code == 'online_transfer':
                    transfer_type = 1
                elif self.payment_method_id.code == 'llg':
                    transfer_type = 2
                elif self.payment_method_id.code == 'rtgs':
                    transfer_type = 3
            param = {'receiver_account_number': self.partner_bank_id.acc_number,
                     'receiver_account_name': self.partner_bank_id.acc_holder_name,
                     'receiver_account_email': self.partner_bank_id.acc_holder_email,
                     'receiver_bank_code': self.partner_bank_id.bank_id.code,
                     'receiver_account_bank': self.partner_bank_id.bank_id.name,
                     'sender': self.journal_id.bank_account_id.acc_number,
                     'amount' : "{:.0f}".format(self.amount),
                     'first_remark' : self.name if len(self.name) <=18 else self.name[:18],
                     'second_remark' : False,
                     'transfer_type' : transfer_type,
                     'beneficiary_cust_type' : self.partner_bank_id.acc_holder_type,
                     'beneficiary_cust_residence' : self.partner_bank_id.acc_holder_resident,
                     'beneficiary_cust_address' : self.partner_bank_id.acc_holder_resident,
                     'currency' : self.currency_id.name,
                    }

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
                request_server_login = requests.post(f'{domain+"api/v1/login"}', params=param_login, headers=headers, verify=False)
                response_login = json.loads(request_server_login.text)
                if request_server_login.status_code == 200:
                    headers['authorization'] = response_login['type'] + ' ' + response_login['token']
                    request_server = requests.post(f'{domain+"api/v1/transfer"}', params=param, headers=headers, verify=False)
                    response = json.loads(request_server.text)
                    if request_server.status_code == 200:
                        self.update({'online_payment_status' : 'Success'})
                        return request_server
                    else:
                        self.action_draft()
                        self.update({'state' : 'failed', 'online_payment_status' : response['message']})
                        return request_server
                else:
                    if 'errors' in response_login:
                        text= str(response_login["message"]) + '\n'
                        for key, value in response_login["errors"].items():
                            text += str(key) + ' : ' + str(value) + '\n'
                        raise UserError(text)
                    raise UserError(response_login)
            except Exception as e:
                tb = sys.exc_info()
                raise UserError(e.with_traceback(tb[2]))
            # except:
            #     raise ValidationError("Not connect to API Chat Server. Limit reached or not active")