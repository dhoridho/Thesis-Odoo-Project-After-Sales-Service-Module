import re
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import requests
import json


class QiscusWaTemplate(models.Model):
    _name = 'qiscus.wa.template'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    @api.model
    def _get_new_category(self):
        categories = [
            ('marketing','Marketing'),
            ('utility','Utility'),
            ('authentication','Authentication')
        ]

        return categories
    
    name = fields.Char()
    namespace = fields.Char()
    reject_reason = fields.Text()
    qiscus_template_id = fields.Integer()
    content_ids = fields.One2many('qiscus.wa.template.content','template_id')
    category = fields.Selection(selection=_get_new_category,default='utility')
    status = fields.Selection([('0','Pending'),('1','Approved'),('-1','Reject')])
    channel_id = fields.Char()
    
    
    def unlink(self):
        app_id = self.env['ir.config_parameter'].sudo().get_param('qiscus.api.appid') 
        channel_id = self.env['ir.config_parameter'].sudo().get_param('qiscus.api.channel_id') 
        token = self.env['ir.config_parameter'].sudo().get_param('qiscus.api.secret_key') 
        for data in self:
            if data.channel_id == channel_id:
                header = {'Qiscus-App-Id':app_id,
                        'Qiscus-Secret-Key':token}
                delete = requests.post(f'https://multichannel.qiscus.com/api/v2/admin/hsm/delete/{data.qiscus_template_id}',headers=header,verify=True)
        res = super(QiscusWaTemplate,self).unlink()
        
        return res
    
    
    @api.model
    def ir_cron_syncronize_template_button(self): 
        self.ir_cron_syncronize_template()
                        
                        
                
    
    def ir_cron_syncronize_template(self):
        app_id = self.env['ir.config_parameter'].sudo().get_param('qiscus.api.appid') 
        channel_id = self.env['ir.config_parameter'].sudo().get_param('qiscus.api.channel_id') 
        token = self.env['ir.config_parameter'].sudo().get_param('qiscus.api.secret_key') 
        header = {'Qiscus-App-Id':app_id,
                  'Qiscus-Secret-Key':token}
        param = {
                  'limit':1000,
                  'channel_id':channel_id}
        get_template_qiscus = requests.get(f'https://multichannel.qiscus.com/api/v2/admin/hsm',headers=header,params=param,verify=True)
        response_data = json.loads(get_template_qiscus.content)
        
        if response_data['data']['hsm_templates']:
            ids = [data['id'] for data in response_data['data']['hsm_templates']]
            qiscus_template_to_delete = self.sudo().search([('qiscus_template_id','not in',ids)])
            if qiscus_template_to_delete:
                for unlink_data in qiscus_template_to_delete:
                    unlink_data.unlink()
            
        
            for data in response_data['data']['hsm_templates']:
                qiscus_template = self.sudo().search([('qiscus_template_id','=',data['id'])])
                if not qiscus_template:
                    line_ids = []
                    template_to_create = self.sudo().create({'qiscus_template_id':data['id'],'name':data['name'],'namespace':data['namespace'],'category':str(data['category']).lower()})
                    for line in data['hsm_details']:
                        placeholders_head = re.findall(r'\{.*?\}', str(line['header_content']))
                        template_to_create.reject_reason = line['rejection_reason']
                        template_to_create.status = str(line['approval_status'])
                        template_to_create.channel_id = channel_id
                        header = f"{line['header_default_value']}\n" if line['header_default_value'] else ''
                        header_content = f"{line['header_content']}\n" if line['header_content'] else ''
                        footer_content = f"{line['footer']}\n" if line['footer'] else ''
                        line_ids.append((0,0,{'language':line['language'],
                                            'content':f"""{header}{header_content}{line['content']}\n{footer_content}""",
                                            'content_id':line['id'],      
                                            'is_use_header_variable':True if placeholders_head or  line['header_default_value'] else False,
                                            'header_type':line['header_type']
                                            }))
                    template_to_create.content_ids = line_ids
                if qiscus_template:
                    qiscus_template.qiscus_template_id = data['id']
                    qiscus_template.name = data['name']
                    qiscus_template.namespace = data['namespace']
                    qiscus_template.category = str(data['category']).lower()
                    for line in data['hsm_details']:
                        line_ids = []
                        qiscus_template.reject_reason = line['rejection_reason']
                        qiscus_template.status = str(line['approval_status'])
                        qiscus_template.channel_id = channel_id
                        qiscus_template_content = self.env['qiscus.wa.template.content'].sudo().search([('template_id','=',qiscus_template.id),('content_id','=',line['id'])])
                        header = f"{line['header_default_value']}\n" if line['header_default_value'] else ''
                        header_content = f"{line['header_content']}\n" if line['header_content'] else ''
                        footer_content = f"{line['footer']}\n" if line['footer'] else ''
                        placeholders_head = re.findall(r'\{.*?\}', str(line['header_content']))
                        if qiscus_template_content:
                            qiscus_template_content.language =  line['language']
                            qiscus_template_content.content =  f"""{header}{header_content}{line['content']}\n{footer_content}"""
                            qiscus_template_content.is_use_header_variable = True if placeholders_head or  line['header_default_value'] else False  
                        else:
                            line_ids.append((0,0,{'content_id':line['id'],
                                            'language':line['language'],
                                            'content':f"""{header}{header_content}{line['content']}\n{footer_content}""",
                                            'is_use_header_variable':True if placeholders_head or  line['header_default_value'] else False,
                                            'header_type':line['header_type']
                                            }))
                            qiscus_template.content_ids = line_ids
                    ids_to_delete = [data_delete['id'] for data_delete in  data['hsm_details']]
                    qiscus_template_content_delete = self.env['qiscus.wa.template.content'].sudo().search([('template_id','=',qiscus_template.id),('content_id','not in',ids_to_delete)])
                    if qiscus_template_content_delete:
                        for delete in qiscus_template_content_delete:
                            delete.unlink()
        
      
    
    
    


class QiscusWaTemplateContent(models.Model):
    _name = 'qiscus.wa.template.content'
    _rec_name = 'name'
    
    template_id = fields.Many2one('qiscus.wa.template',ondelete="cascade")
    name = fields.Char(compute='_compute_name',store=True)
    language = fields.Char()
    content_id = fields.Integer()
    content = fields.Text()
    category = fields.Selection(related='template_id.category',default='UTILITY')
    is_use_header_variable = fields.Boolean(default=False)
    header_type = fields.Char()
    default_header_value = fields.Char()
    
    
    
    @api.depends('template_id','language')
    def _compute_name(self):
        for record in self:
            if record.template_id and record.language:
                record.name = f"{record.template_id.name} - {record.language}"
            else:
                record.name = "-"
                
    
    
        
    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, "{} - {}".format(record.template_id.name, record.language)))
        return result