from odoo import api, fields, models, _
import pytz, logging, requests, json, sys, traceback
from odoo.exceptions import UserError, ValidationError
import requests


_logger = logging.getLogger(__name__)
headers = {'content-type': 'application/json', 'accept': 'application/json'}

class ResConfigSettingsAccountingEfaktur(models.TransientModel):
    _inherit = 'res.config.settings'

    # is_pajak_express_integration = fields.Boolean(config_parameter='equip3_accounting_efaktur.is_pajak_express_integration',string="Pajak Express Integration")
    lhdn_url = fields.Char(string='URL',config_parameter='equip3_einvoice_integration_my.lhdn_url')
    valid_lhdn = fields.Boolean(default=False,config_parameter='equip3_einvoice_integration_my.valid_lhdn')
    invalid_lhdn = fields.Boolean(default=False,config_parameter='equip3_einvoice_integration_my.invalid_lhdn')
    # pajak_express_transaction_url = fields.Char(string='Transaction URL',config_parameter='equip3_accounting_efaktur.pajak_express_transaction_url')
    lhdn_client_id = fields.Char(string='Client ID',config_parameter='equip3_einvoice_integration_my.lhdn_client_id')
    lhdn_client_secret = fields.Char(string='Client Secret',config_parameter='equip3_einvoice_integration_my.lhdn_client_secret')
    
    
    
    def cek_lhdn_credential(self):
        lhdn_url = self.env['ir.config_parameter'].sudo().get_param('equip3_einvoice_integration_my.lhdn_url')
        lhdn_client_id = self.env['ir.config_parameter'].sudo().get_param('equip3_einvoice_integration_my.lhdn_client_id')
        lhdn_client_secret = self.env['ir.config_parameter'].sudo().get_param('equip3_einvoice_integration_my.lhdn_client_secret')
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
                }
        data = {
            'client_id': lhdn_client_id,
            'client_secret': lhdn_client_secret,
            'grant_type':'client_credentials',
            'scope':'InvoicingAPI'
            # Add other key-value pairs as needed
            }
        # response = requests.post(lhdn_url, headers=headers, data=data)
        
        # payload = {'email':pajak_express_username,'password':pajak_express_password}
        # if is_pajak_express_integration:
        print(data)
        try:
            response = requests.post(lhdn_url+'/connect/token', headers=headers, data=data)
            print("response.json()")
            print(response.json())
            # err
            if response.status_code == 200:
                self.env["ir.config_parameter"].sudo().set_param('equip3_einvoice_integration_my.valid_lhdn', True)
                self.env["ir.config_parameter"].sudo().set_param('equip3_einvoice_integration_my.invalid_lhdn', False)
            #     self.env["ir.config_parameter"].sudo().set_param('equip3_accounting_efaktur.validate_api_express', True)
            #     self.env["ir.config_parameter"].sudo().set_param('equip3_accounting_efaktur.validate_api_express_fail', False)
            else:
                self.env["ir.config_parameter"].sudo().set_param('equip3_einvoice_integration_my.invalid_lhdn', True)
                self.env["ir.config_parameter"].sudo().set_param('equip3_einvoice_integration_my.valid_lhdn', False)
            #     self.env["ir.config_parameter"].sudo().set_param('equip3_accounting_efaktur.validate_api_express', False)
            #     self.env["ir.config_parameter"].sudo().set_param('equip3_accounting_efaktur.validate_api_express_fail', True)
        except Exception as e:
            tb = sys.exc_info()
            raise UserError(e.with_traceback(tb[2]))
    
    # @api.onchange('is_pajak_express_integration')
    # def onchange_matrix(self):
    #     self.group_is_pajak_express_integration = self.is_pajak_express_integration