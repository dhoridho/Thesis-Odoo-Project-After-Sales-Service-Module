import base64
import random
import string
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from datetime import datetime


class sendPrivy(models.TransientModel):
    _name = 'send.privy.wizard'
    
    
    name = fields.Char()
    use_another_document = fields.Boolean()
    file = fields.Binary()
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
    contract_id = fields.Many2one('hr.contract')
    signer_ids = fields.One2many('send.privy.wizard.signer','privy_wizard_id')
    materai_ids = fields.One2many('send.privy.wizard.meterai','privy_wizard_id')
    
    @api.onchange('doc_process')
    def _onchange_doc_process(self):
        for data in self:
            if data.doc_process:
                if data.doc_process == "0":
                    data.e_meterai = False
    
    @api.onchange('contract_id')
    def _onchange_contract(self):
        if self.contract_id:
            self.signer_ids = [(0,0,{'signer_id':self.contract_id.employee_id.id,
                                     'privy_id':self.contract_id.employee_id.user_partner_id.privy_user_name
                                     })]
            if self.contract_id.contract_template.doc_process:
                self.e_meterai = True
                self.materai_ids = [(0,0,{'pos_x':self.contract_id.contract_template.pos_x,
                                     'pos_y':self.contract_id.contract_template.pos_y,
                                     'page':self.contract_id.contract_template.signature_page,
                                     'dimension':self.contract_id.contract_template.dimension,
                                     })]
    def generate_random_string(self,length):
        letters = string.ascii_letters  # This includes both lowercase and uppercase letters
        random_string = ''.join(random.choice(letters) for i in range(length))
        return random_string
    
    def submit(self):
        privy_channel_id = self.env['ir.config_parameter'].sudo().get_param('equip3_privy_integration.privy_channel_id')
        privy_enterprise_token = self.env['ir.config_parameter'].sudo().get_param('equip3_privy_integration.privy_enterprise_token')
        stamp_position= []  
        recipients = []
        if not self.use_another_document:
            if not self.contract_id.contract_template:
                raise ValidationError("'Please select contract letter first or upload your document!")
            if not self.contract_id.certificate_attachment:
                pdf = self.env.ref('equip3_hr_contract_extend.equip3_hr_contract_letter_mail')._render_qweb_pdf(self.contract_id.id)
                attachment = base64.b64encode(pdf[0])
                self.contract_id.certificate_attachment = attachment
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
                    "document_file": "data:" + "application/pdf" + ";base64," + (self.contract_id.certificate_attachment).decode('utf-8') if not self.use_another_document else "data:" + "application/pdf" + ";base64," + (self.file).decode('utf-8'),
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
                                "drag_n_drop":True if not multiple_signature else False,
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
        
            
            
        response = self.contract_id.employee_id.user_partner_id.doc_signing(payload)
        status = response['data']['status']
        if response['data']['status'] == 'uploaded':
            status = 'Uploaded to Privy'
        if response['data']['status'] == 'processing':
            status = 'Processing E-Signature'
            
        if response['data']['status'] == 'processing_emeterai':
            status = 'Processing E-Meterai by Privy'
            
        if response['data']['status'] == 'completed':
            status = ' Completed'
        
        
        self.contract_id.contract_history_ids = [(0,0,{'name':self.name +".pdf",
                                               'status':status,
                                               'reference_number':response['data']['reference_number'],
                                               'channel_id':response['data']['channel_id'],
                                               'document_token':response['data']['document_token'],
                                               'signing_url':response['data']['signing_url'] if 'signing_url' in response['data'] else '-'
                                               
                                               })]
        
        
        
    






class sendPrivyWizardSigner(models.TransientModel):
    _name = 'send.privy.wizard.signer'
    
    privy_wizard_id = fields.Many2one('send.privy.wizard')
    signer_id = fields.Many2one('hr.employee')
    privy_id = fields.Char()
    timestamp = fields.Boolean()
    multiple_signature = fields.Boolean()
    multiple_signature_ids = fields.One2many('send.privy.wizard.multiple.signature','privy_wizard_signer_id')
    
    
    @api.onchange('signer_id')
    def _onchange_signer_id(self):
        if self.signer_id:
            if self.signer_id.user_partner_id:
                self.privy_id = self.signer_id.user_partner_id.privy_user_name

class sendPrivyWizardMultipleSignature(models.TransientModel):
    _name = 'send.privy.wizard.multiple.signature'
    
    privy_wizard_signer_id = fields.Many2one('send.privy.wizard.signer')
    posx = fields.Float()
    posy = fields.Float()
    page = fields.Integer()


    
class sendPrivyWizardMeterai(models.TransientModel):
    _name = 'send.privy.wizard.meterai'

    
    privy_wizard_id = fields.Many2one('send.privy.wizard')
    pos_x = fields.Float()
    pos_y = fields.Float()
    page = fields.Integer()
    dimension = fields.Float()
    
    
    