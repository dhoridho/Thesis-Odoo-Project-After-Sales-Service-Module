from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import base64


class HrContractInherit(models.Model):
    _inherit = 'hr.contract'
    
    contract_history_ids = fields.One2many('hr.contract.history','contract_id')
    
    def action_send_privy(self):
        return {
                'name': _('Send To Privy'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'send.privy.wizard',
                'target': 'new',
                'context': {'default_contract_id':self.id},
            }
        
    
    
     


class hrContractHistory(models.Model):
    _name = 'hr.contract.history'
    
    contract_id = fields.Many2one('hr.contract')
    name = fields.Char()
    document_date = fields.Date(default=datetime.now())
    status = fields.Char()
    signed_document = fields.Binary()
    reference_number = fields.Char()
    channel_id = fields.Char()
    document_token = fields.Char()
    signing_url = fields.Char()
    
    
    def check_status(self):
        response = self.contract_id.employee_id.user_partner_id.check_status_contract(self.reference_number,self.channel_id,self.document_token,f"checkstatus{self.id}")
        if response:
            status = ''
            if response['data']['status'] == 'uploaded':
                status = 'Uploaded to Privy'
            if response['data']['status'] == 'processing':
                status = 'Processing E-Signature'
                
            if response['data']['status'] == 'processing_emeterai':
                status = 'Processing E-Meterai by Privy'
                
            if response['data']['status'] == 'completed':
                status = ' Completed'
            self.status = status
            if response['data']['status'] == 'completed':
                self.signed_document = response['data']['signed_document'].split(",")[1]
    
    