from odoo import api, fields, models, _
import pytz, logging, requests, json, sys, traceback
from odoo.exceptions import UserError, ValidationError
import requests


_logger = logging.getLogger(__name__)
headers = {'content-type': 'application/json', 'accept': 'application/json'}

class ResConfigSettingsAccountingEfaktur(models.TransientModel):
    _inherit = 'res.config.settings'

    is_pajak_express_integration = fields.Boolean(config_parameter='equip3_accounting_efaktur.is_pajak_express_integration',string="Pajak Express Integration")
    pajak_express_url = fields.Char(string='URL',config_parameter='equip3_accounting_efaktur.pajak_express_url')
    pajak_express_transaction_url = fields.Char(string='Transaction URL',config_parameter='equip3_accounting_efaktur.pajak_express_transaction_url')
    pajak_express_username = fields.Char(string='Username',config_parameter='equip3_accounting_efaktur.pajak_express_username')
    pajak_express_password = fields.Char(string='Password',config_parameter='equip3_accounting_efaktur.pajak_express_password')
    validate_api_first = fields.Boolean(config_parameter='equip3_accounting_efaktur.validate_api_first')
    validate_api_express = fields.Boolean(config_parameter='equip3_accounting_efaktur.validate_api_express')
    validate_api_express_fail = fields.Boolean(config_parameter='equip3_accounting_efaktur.validate_api_express_fail')
    group_is_pajak_express_integration = fields.Boolean(string="Group PJAP Integration",
        implied_group='equip3_accounting_efaktur.group_is_pajak_express_integration')
    
    
    def cek_pajak_express_credential(self):
        is_pajak_express_integration = self.env['ir.config_parameter'].sudo().get_param('equip3_accounting_efaktur.is_pajak_express_integration')
        pajak_express_url = self.env['ir.config_parameter'].sudo().get_param('equip3_accounting_efaktur.pajak_express_url')
        pajak_express_username = self.env['ir.config_parameter'].sudo().get_param('equip3_accounting_efaktur.pajak_express_username')
        pajak_express_password = self.env['ir.config_parameter'].sudo().get_param('equip3_accounting_efaktur.pajak_express_password')
        payload = {'email':pajak_express_username,'password':pajak_express_password}
        if is_pajak_express_integration:
            try:
                login = requests.post(pajak_express_url + '/api/login',data=payload)
                if login.status_code == 200:
                    self.env["ir.config_parameter"].sudo().set_param('equip3_accounting_efaktur.validate_api_first', True)
                    self.env["ir.config_parameter"].sudo().set_param('equip3_accounting_efaktur.validate_api_express', True)
                    self.env["ir.config_parameter"].sudo().set_param('equip3_accounting_efaktur.validate_api_express_fail', False)
                else:
                    self.env["ir.config_parameter"].sudo().set_param('equip3_accounting_efaktur.validate_api_first', True)
                    self.env["ir.config_parameter"].sudo().set_param('equip3_accounting_efaktur.validate_api_express', False)
                    self.env["ir.config_parameter"].sudo().set_param('equip3_accounting_efaktur.validate_api_express_fail', True)
            except Exception as e:
                tb = sys.exc_info()
                raise UserError(e.with_traceback(tb[2]))
    
    @api.onchange('is_pajak_express_integration')
    def onchange_matrix(self):
        self.group_is_pajak_express_integration = self.is_pajak_express_integration