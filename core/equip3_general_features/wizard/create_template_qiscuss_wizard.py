import base64
import json
import os
import re
from odoo import fields, models, api
import requests
from odoo.exceptions import ValidationError
from odoo.modules import get_module_path

class createTemplateQiscuss(models.TransientModel):
    _name = 'create.template.qiscuss'
    
    name = fields.Char()
    category = fields.Selection([('marketing','Marketing'),('utility','Utility'),('authentication','Authentication')],default='utility')
    content_ids = fields.One2many('create.template.qiscuss.line','create_template_id')
    
    def submit(self):
        app_id = self.env['ir.config_parameter'].sudo().get_param('qiscus.api.appid') 
        channel_id = self.env['ir.config_parameter'].sudo().get_param('qiscus.api.channel_id') 
        token = self.env['ir.config_parameter'].sudo().get_param('qiscus.api.secret_key') 
        header = {'Qiscus-App-Id':app_id,
                  'Qiscus-Secret-Key':token}
        header_file = {'qiscus_sdk_app_id':app_id,
                  'qiscus_sdk_secret':token}
        line_ids = []
        for data in self.content_ids:
            placeholders_body = re.findall(r'\{.*?\}', data.body)
            content_ids = {'content':data.body,
                            'language':data.language_id.iso_code
                            }
            if placeholders_body:
                body_sample = []
                num = 0
                for pb in placeholders_body:
                    num +=1
                    body_sample.append(f'bodysample{num}')
                content_ids['body_sample'] = body_sample
                    
            if data.use_header:
                if data.header_type == 'text':
                    content_ids['header_type'] = data.header_type
                    content_ids['header_content'] = data.header_text
                    content_ids['header_default_value'] = None
                    placeholders_head = re.findall(r'\{.*?\}', data.header_text)
                    if placeholders_head:
                        content_ids['header_sample'] = ["Lala"]
                    
                elif data.header_type == 'media':
                    if data.file_type == 'image':
                        file_base64 = data.image_file
                    elif data.file_type == 'document':
                        file_base64 = data.document_file
                    elif data.file_type == 'video':
                        file_base64 = data.video_file
                    module_path = get_module_path('equip3_general_features')
                    fpath = module_path + '/generated_files'
                    file_path = os.path.join(fpath, data.file_name)
                    if not os.path.isdir(fpath):
                        os.mkdir(fpath)
                    file_data = base64.b64decode(file_base64)
                    
                    
                    with open(file_path, 'wb') as file:
                        file.write(file_data)
                        
                    
                    files = {
                        'file': open(file_path, 'rb')  # replace with the correct file path
                    }
                    request_file = requests.post('https://api3.qiscus.com/api/v2/sdk/upload', headers=header_file, files=files)
                    response_file = request_file.json()                
                    content_ids['header_type'] = data.file_type
                    content_ids['header_default_value'] =response_file['results']['file']['url']
                    if response_file['results']['file']['url']:
                        try:
                            os.remove(file_path)
                        except OSError as e:
                            pass
            
            
            button = []
            
            if data.button_1:
                butt = {'type':str(data.button_type).upper(),
                               'text':data.button_1_text,
                               
                               }
                if data.button_type == 'url':
                    butt['url'] = data.button_1_url
                    butt['example'] = data.button_1_url + "test"
                    
                elif data.button_type == 'phone_number':
                    butt['phone_number'] = data.button_1_phone_number
                    butt['example'] = data.phone_number
                
                button.append(butt)
                
            if data.button_2:
                butt = {'type':str(data.button_type).upper(),
                               'text':data.button_2_text,
                               
                               }
                if data.button_type == 'url':
                    butt['url'] = data.button_2_url
                    butt['example'] = data.button_2_url + "test"
                    
                elif data.button_type == 'phone_number':
                    butt['phone_number'] = data.button_1_phone_number
                    butt['example'] = data.phone_number
                
                
                button.append(butt)
                
            if data.button_3:
                butt = {'type':str(data.button_type).upper(),
                               'text':data.button_3_text,
                               
                               }
                if data.button_type == 'url':
                    butt['url'] = data.button_3_url
                    butt['example'] = data.button_3_url + "test"
                    
                elif data.button_type == 'phone_number':
                    butt['phone_number'] = data.button_3_phone_number
                    butt['example'] = data.phone_number
                
                
                button.append(butt)
                
            if data.use_button:
                content_ids['buttons'] =  button
                    
            if data.is_use_footer:
                content_ids['footer'] = data.footer
                          
            line_ids.append(content_ids)
        
        
        payload = {'have_template':False,
                   'name':self.name,
                #    "header_sample":["sample"],
                #    "body_sample":["body_sample"],
                   'category':str(self.category).upper(),
                   'channel_id':channel_id,
                   "hsm_details":line_ids
                   
                   }
        
        create_template_qiscus = requests.post(f'https://multichannel.qiscus.com/api/v3/admin/hsm/create',headers=header,json=payload,verify=True)
        response_data = create_template_qiscus.json()
        if create_template_qiscus.status_code != 200:
            raise ValidationError(response_data['errors']['message'])
        
        syncron = self.env['qiscus.wa.template'].search([],limit=1)
        if syncron:
            syncron.ir_cron_syncronize_template()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    
    




class createTemplateQiscussLine(models.TransientModel):
    _name = 'create.template.qiscuss.line'
    
    create_template_id = fields.Many2one('create.template.qiscuss')
    language_id = fields.Many2one('res.lang')
    content = fields.Text(compute='_compute_content')
    use_header = fields.Boolean()
    header_type = fields.Selection([('text','Text'),('media','Media')])
    header_text = fields.Text()
    link_file = fields.Char()
    file_type = fields.Selection([('image','Image'),('document','Document'),('video','Video')])
    body = fields.Text()
    is_use_footer = fields.Boolean()
    footer = fields.Text()
    use_button =  fields.Boolean()
    button_type = fields.Selection([('phone_number','Phone Number'),('url','URL'),('quick_reply','Quick Reply')])
    button_1 = fields.Boolean()
    button_1_url = fields.Char()
    button_1_phone_number = fields.Char()
    button_1_text = fields.Text()
    button_2 = fields.Boolean()
    button_2_url = fields.Char()
    button_2_phone_number = fields.Char()
    button_2_text = fields.Text()
    button_3 = fields.Boolean()
    button_3_text = fields.Text()
    button_3_url = fields.Char()
    button_3_phone_number = fields.Char()
    image_file = fields.Binary("Choose JPG or PNG File Max 5MB")
    document_file = fields.Binary("Choose PDF File Max 100MB")
    video_file = fields.Binary("Choose MP4 File Max 16MB")
    file_name = fields.Char()
    
    def _check_image_file_extension(self, file_name):
        allowed_extensions = ['.png', '.jpg', '.jpeg']
        if not any(file_name.lower().endswith(ext) for ext in allowed_extensions):
            raise ValidationError("Invalid file format! Only PNG or JPG files are allowed.")
        
    def _check_document_file_extension(self, file_name):
        allowed_extensions = ['.pdf']
        if not any(file_name.lower().endswith(ext) for ext in allowed_extensions):
            raise ValidationError("Invalid file format! Only PDF files are allowed.")
        
    def _check_video_file_extension(self, file_name):
        allowed_extensions = ['.mp4']
        if not any(file_name.lower().endswith(ext) for ext in allowed_extensions):
            raise ValidationError("Invalid file format! Only MP4 files are allowed.")
    
    
    @api.model
    def create(self, vals):
        # Check file size before creating record
        if 'image_file' in vals and vals['image_file']:
            file_data = base64.b64decode(vals['image_file'])  # Decoding base64 to get actual size
            file_size = len(file_data)
            max_size = 5 * 1024 * 1024  # Set limit to 5MB
            if file_size > max_size:
                raise ValidationError("The file size cannot exceed 5 MB.")
            self._check_image_file_extension(vals['file_name'])
            
        if 'document_file' in vals and vals['document_file']:
            file_data = base64.b64decode(vals['document_file'])  # Decoding base64 to get actual size
            file_size = len(file_data)
            max_size = 100 * 1024 * 1024  # Set limit to 5MB
            if file_size > max_size:
                raise ValidationError("The file size cannot exceed 5 MB.")
            self._check_document_file_extension(vals['file_name'])
            
        if 'video_file' in vals and vals['video_file']:
            file_data = base64.b64decode(vals['video_file'])  # Decoding base64 to get actual size
            file_size = len(file_data)
            max_size = 16 * 1024 * 1024  # Set limit to 5MB
            if file_size > max_size:
                raise ValidationError("The file size cannot exceed 5 MB.")
            self._check_video_file_extension(vals['file_name'])

        return super(createTemplateQiscussLine, self).create(vals)
    
    
    
    @api.depends('body','header_text','footer','button_1_text','button_2_text','button_3_text')
    def _compute_content(self):
        for data in self:
            media_header = "MEDIA"
            if data.body:
                data.content = f"""{media_header if data.header_type == 'media' else ''} {data.header_text if data.header_text  and data.header_type == 'text' else ''}\n{data.body}\n{data.footer if data.footer else ''}\n{data.button_1_text if data.button_1_text else ''}\n{data.button_2_text if data.button_2_text else ''}\n{data.button_3_text if data.button_3_text else ''}\n"""
            else:
                data.content = ''