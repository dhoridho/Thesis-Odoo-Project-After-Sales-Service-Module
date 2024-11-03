import base64
import random
import string
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from .privy_integration import privyIntegration


class privySendDocumentSigning(models.Model):
    _name = 'privy.send.document.signing'
    _order = 'id desc'
    
    name = fields.Char()
    file = fields.Binary(string="Document")
    document_date = fields.Date(default=datetime.now())
    document_information = fields.Text()
    sign_process = fields.Selection([('1',"Paralel"),('0','Sequential')])
    e_meterai = fields.Boolean()
    document_category = fields.Selection([('akta_pejabat','Akta Pejabat'),
                                          ('surat_berharga','Surat Berharga'),
                                          ('dokumen_transaksi','Dokumen Transaksi'),
                                          ('dokumen_lelang','Dokumen Lelang'),
                                          ('dokumen_pernyataan_jumlah_uang','Dokumen pernyataan jumlah uang lebih dari 5 juta.'),
                                          ('akta_notaris','Akta Notaris'),
                                          ('surat_perjanjian','Surat Perjanjian'),
                                          ('dokumen_lain_lain','Dokumen Lain-lain'),
                                          ('dokumen_hutang','Dokumen pelunasan utang (lebih dari 5 juta)'),
                                          ('surat_pernyataan','Surat Pernyataan'),
                                          ('dokumen_penerimaan_uang','Dokumen penerimaan uang (lebih dari 5 juta)'),
                                          ])
    doc_process = fields.Selection([('0','Signing Only'),
                                    ('1','E-meterai Only'),
                                    ('2','Signing First,then E-Meterai'),
                                    ('3','E-Meterai First,then document signing')]
                                   )
    signer_ids = fields.One2many('send.privy.signer','privy_wizard_id')
    materai_ids = fields.One2many('send.privy.meterai','privy_wizard_id')
    status = fields.Char(default='Draft')
    reference_number = fields.Char()
    channel_id = fields.Char()
    document_token = fields.Char()
    signing_url = fields.Char()
    signed_document = fields.Binary(string="Document")
    doc_name  = fields.Char(compute='_compute_doc_name')
    
    
    @api.depends('name')
    def _compute_doc_name(self):
        for data in self:
            if data.name:
                data.doc_name = data.name + ".pdf"
            else:
                data.doc_name = ''
    
    
    def generate_random_string(self,length):
        letters = string.ascii_letters  # This includes both lowercase and uppercase letters
        random_string = ''.join(random.choice(letters) for i in range(length))
        return random_string
    
    
    def check_status(self):
        payload = {"reference_number":self.reference_number,
                   "channel_id":self.channel_id,
                   "document_token":self.document_token,
                   "info":""
                   }
        response = privyIntegration().doc_status(payload)
        if response:
            status = response['data']['status']
            if response['data']['status'] == 'uploaded':
                status = 'Uploaded to Privy'
            if response['data']['status'] == 'processing':
                status = 'Processing E-Signature'
                
            if response['data']['status'] == 'processing_emeterai':
                status = 'Processing E-Meterai by Privy'
                
            if response['data']['status'] == 'completed':
                status = ' Completed'
                
            if response['data']['status'] == 'error':
                status = 'Error'
                
            if response['data']['status'] == 'waiting_otp':
                status = 'Waiting Privy OTP'
                
            self.status = status
            if response['data']['status'] == 'completed':
                self.file = response['data']['signed_document'].split(",")[1]
        
        
    
    def confirm(self):
        if not self.file:
            raise ValidationError("upload your document first")
        privy_channel_id = self.env['ir.config_parameter'].sudo().get_param('equip3_privy_integration.privy_channel_id')
        privy_enterprise_token = self.env['ir.config_parameter'].sudo().get_param('equip3_privy_integration.privy_enterprise_token')
        stamp_position= []  
        recipients = []
        payload  = {
                "reference_number": f"{self.env.company.name}{self.generate_random_string(7)}".replace(" ", ""),
                "channel_id": privy_channel_id,
                "custom_signature_placement": True,
                "info":self.document_information,
                "doc_process": self.doc_process,
                "visibility": True,
                "doc_owner": {
                    "privyId": self.env.company.privy_id,
                    "enterpriseToken": privy_enterprise_token
                },
                "document": {
                    "document_file":"data:" + "application/pdf" + ";base64," + (self.file).decode('utf-8'),
                    "document_name": f"{self.name}" + ".pdf",
                    "sign_process":self.sign_process,
                    "barcode_position": "0"
                    
                }
                
            }
        if self.signer_ids:
            for data_receipt in self.signer_ids:
                multiple_signature = []
                if data_receipt.multiple_signature_ids:
                    for signature in data_receipt.multiple_signature_ids:
                        multiple_signature.append({
                            'posX':str(signature.posx),
                            'posY':str(signature.posy),
                            'signPage':str(signature.page),
                                                   
                                                   }
                                                  
                                                  )
                receipts = {'user_type':"0",
                                'autosign':"0",
                                "id_user":data_receipt.privy_id,
                                "signer_type":"Signer",
                                "enterpriseToken":privy_enterprise_token,
                                "notify_user":"1",
                                "drag_n_drop":False if data_receipt.multiple_signature else True,
                                "detail":"1" if data_receipt.timestamp else "0",
                                "sign_positions":multiple_signature,
                                
                                }
                if not data_receipt.multiple_signature:
                    del receipts['sign_positions']
                recipients.append(receipts)
            payload['recipients'] = recipients
        
        if self.e_meterai:
            if self.materai_ids:
                for line_stamp in self.materai_ids:
                    stamp_position.append({'pos_x':line_stamp.pos_x,
                                           'pos_y':line_stamp.pos_y,
                                           'page':line_stamp.page,
                                           'dimension':line_stamp.dimension,
                                           
                                           })
            
            payload['e_meterai'] = {
                'doc_category':self.document_category,
                'stamp_position':stamp_position
                
            }
        response = privyIntegration().doc_signing(payload)
        status = response['data']['status']
        if response['data']['status'] == 'uploaded':
            status = 'Uploaded to Privy'
        if response['data']['status'] == 'processing':
            status = 'Processing E-Signature'
            
        if response['data']['status'] == 'processing_emeterai':
            status = 'Processing E-Meterai by Privy'
            
        if response['data']['status'] == 'completed':
            status = 'Completed'
            
        if response['data']['status'] == 'error':
                status = 'Error'
                
        if response['data']['status'] == 'waiting_otp':
            status = 'Waiting Privy OTP'
            
        self.status = status
        self.reference_number = response['data']['reference_number']
        self.channel_id = response['data']['channel_id']
        self.document_token = response['data']['document_token']
        self.signing_url = response['data']['signing_url']
            
    
    
    
class sendPrivyWizardSigner(models.Model):
    _name = 'send.privy.signer'
    
    privy_wizard_id = fields.Many2one('privy.send.document.signing')
    signer_id = fields.Many2one('privy.account.registration')
    privy_id = fields.Char()
    timestamp = fields.Boolean()
    multiple_signature = fields.Boolean()
    multiple_signature_ids = fields.One2many('send.privy.multiple.signature','privy_wizard_signer_id')
    
    
    @api.onchange('signer_id')
    def _onchange_signer_id(self):
        if self.signer_id:
            self.privy_id = self.signer_id.privy_id

class sendPrivyWizardMultipleSignature(models.Model):
    _name = 'send.privy.multiple.signature'
    
    privy_wizard_signer_id = fields.Many2one('send.privy.signer')
    posx = fields.Float()
    posy = fields.Float()
    page = fields.Integer()


    
class sendPrivyWizardMeterai(models.Model):
    _name = 'send.privy.meterai'

    
    privy_wizard_id = fields.Many2one('privy.send.document.signing')
    pos_x = fields.Float()
    pos_y = fields.Float()
    page = fields.Integer()
    dimension = fields.Float()