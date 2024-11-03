import base64
import requests
from odoo.http import request
from odoo.exceptions import ValidationError
import re

headers = {'content-type': 'application/json'}

class EmailParam(object):
    def __init__(self):
        self.email_to = None
        self.stage_now = None
        self.name = None
        self.job_position = None
        self.company_id = None
        self.stage_before = None
        self.job_url = None
        self.next_stage = None
        self.title = None,
        self.work_location = None
        self.url_test = None
        self.recruiter_email = None
        self.recruiter_name = None
        
    def set_email(self, email=None):
        self.email_to = email
        
    def set_stage_now(self, stage_now=None):
        self.stage_now = stage_now
        
    def set_name(self, name=None):
        self.name = name
        
    def set_job_position(self, job_position = None):
        self.job_position = job_position
        
        
    def set_company_id(self, company_id = None ):
        self.company_id = company_id
        
        
    def set_stage_before(self, stage_before = None):
        self.stage_before = stage_before
        
    def set_job_url(self, job_url = None):
        self.job_url = job_url
        
    def set_next_stage(self, next_stage = None):
        self.next_stage = next_stage
        
    def set_title(self, title = None):
        self.title = title
        
    def set_work_location(self, work_location = None):
        self.work_location = work_location
        
    def set_url_test(self, url_test):
        self.url_test = url_test
        
    def set_recruiter_email(self, recruiter_email = None):
        self.recruiter_email = recruiter_email
        
    def set_recruiter_name(self, recruiter_name = None):
        self.recruiter_name = recruiter_name
  
                
    def get_context(self):
        context =  {'email_to':self.email_to,
                        'stage_now':self.stage_now,
                        'name':self.name,
                        'job_position':self.job_position,
                        'company_id':self.company_id,
                        'stage_before':self.stage_before,
                        'job_url':self.job_url,
                        'title':self.title,
                        'work_location':self.work_location,
                        'next_stage':self.next_stage,
                        'url_test':self.url_test,
                        'recruiter_email':self.recruiter_email
                        
                    }
        return context
    
    


class waParam(object):
    def __init__(self,):
        self.wa_string = None
        self.special_var = None
        self.app_id = request.env['ir.config_parameter'].sudo().get_param('qiscus.api.appid') 
        self.domain = request.env['ir.config_parameter'].sudo().get_param('qiscus.api.url') 
        self.token = request.env['ir.config_parameter'].sudo().get_param('qiscus.api.secret_key') 
        self.channel_id = request.env['ir.config_parameter'].sudo().get_param('qiscus.api.channel_id') 
        self.name_space = request.env['ir.config_parameter'].sudo().get_param('qiscus.api.name_space') 
        self.template_name = request.env['ir.config_parameter'].sudo().get_param('qiscus.api.template_name')
        
    def set_wa_string(self,wa_string='',template_model='',template_id=None,domain = None,token = None,app_id = None,channel_id = None,name_space = None,template_name = None):
        self.wa_string = wa_string
        self.template_model = template_model
        self.template_id = template_id
        try:
            self.app_id = request.env['ir.config_parameter'].sudo().get_param('qiscus.api.appid')
            self.domain = request.env['ir.config_parameter'].sudo().get_param('qiscus.api.url') 
            self.token = request.env['ir.config_parameter'].sudo().get_param('qiscus.api.secret_key') 
            self.channel_id = request.env['ir.config_parameter'].sudo().get_param('qiscus.api.channel_id') 
            self.name_space = request.env['ir.config_parameter'].sudo().get_param('qiscus.api.name_space') 
            self.template_name = request.env['ir.config_parameter'].sudo().get_param('qiscus.api.template_name') 
        except RuntimeError:
           self.domain = domain
           self.token = token
           self.channel_id = channel_id
           self.app_id = app_id
           self.name_space = name_space
           self.template_name = template_name
           
        
    def get_body(self):
        if "${br}" in self.wa_string:
            self.wa_string = str(self.wa_string).replace("${br}",f"\n")
        return self.wa_string
    
    # def check_file_is_exist(self,phone_number):
    #     if self.template_model != '' and self.template_id:
    #         attachment_ids = request.env['ir.attachment'].search([('res_model','=',self.template_model),('res_id','=',self.template_id)])
    #         if attachment_ids:
    #             for data in attachment_ids:
    #                 self.send_wa_file(phone_number,data.datas,data.name)
    
    
    def set_special_variable(self,var):
        self.special_var = var
        
    
    def parsing_special_var(self,data,message):
        if data and message and self.special_var:
            for var in self.special_var:
                if var['variable'] == data.name:
                    message = message.replace(var['variable'],str(var['value']))
        
        return message
    
    
    
    def send_wa_qiscuss(self,obj_line,obj_model,template,phone_num=None) :
        if not phone_num:
            phone_num = str(obj_model.partner_mobile)
            
        if "+" in phone_num:
            phone_num =  phone_num.replace(" ","")
            phone_num =  phone_num.replace("+","")
            try:
                phone_num =  int(phone_num)
            except:
                phone_num = str(phone_num)
        parameter = []
        if obj_line:
            for line in obj_line:
                message = str(line.message)
                placeholders = re.findall(r'\{.*?\}', line.message)
                if placeholders:

                    for var in placeholders:
                        if line.template_id.wa_variable_ids:
                            var_data = line.template_id.wa_variable_ids.filtered(lambda line_var:line_var.model_id.model == obj_model._name and line_var.name == var and not line_var.special_var)
                            var_data_special = line.template_id.wa_variable_ids.filtered(lambda line_var:line_var.special_var)

                            if var_data:
                                if var_data.field_id.ttype == 'many2one':
                                    model_obj =  request.env[var_data.field_id.relation].sudo().search([],limit=1)
                                    message = message.replace(var_data[0].name,str(obj_model[var_data.field_id.name][model_obj._rec_name]))
                                else:
                                    message = message.replace(var_data[0].name,str(obj_model[var_data.field_id.name]))
                                    
                            if var_data_special:
                                for line_data in var_data_special:
                                    message = self.parsing_special_var(line_data,message)
                                
                                    
                parameter.append({'type':"text",
                                  "text":message
                                  })

                
        param = {
            "to":phone_num,
            "type":"template",
            "template": {
            "namespace":template.broadcast_template_id.template_id.namespace,
            "name": template.broadcast_template_id.template_id.name,
            "language": {
                "policy": "deterministic",
                "code": template.broadcast_template_id.language
            },
                "components": [
                {
                    "type" : "body",
                    "parameters": parameter
                }
            ]
            }
            }
        
        if template.use_header:
            if template.header_type == 'media':
                param['template']['components'].append({
                            "type": "header",
                            "parameters": [
                            {
                                "type": template.file_type,
                                f"{template.file_type}": {
                                "link": template.link_file
                                }
                            }
                            ]
                        })
                
            if template.header_type == 'text':
                param['template']['components'].append({
                            "type": "header",
                            "parameters": [
                            {
                                "type":"text",
                               "text": template.header_text
                                
                            }
                            ]
                        })
                
        

        try:
            headers['Qiscus-App-Id'] = self.app_id
            headers['Qiscus-Secret-Key'] = self.token
            request_server = requests.post(f'{self.domain}{self.app_id}/{self.channel_id}/messages', json=param,headers=headers,verify=True)
            if request_server.status_code != 200:
                data = request_server.json()

                raise  ValidationError(f"""{data["error"]["message"]}. Please contact your administrator. \n {param}""")
        except ConnectionError:
            raise ValidationError("Not connect to API Chat Server. Limit reached or not active")
        
    
    def send_wa(self,phone_number):
        phone_num = str(phone_number)
        if "+" in phone_num:
            phone_num =  phone_num.replace(" ","")
            phone_num =  phone_num.replace("+","")
            try:
                phone_num =  int(phone_num)
            except:
                phone_num = str(phone_num)
                
        param = {
            "to":phone_num,
            "type":"template",
            "template": {
            "namespace":self.template_id.broadcast_template_id.template_id.namespace,
            "name": self.template_id.broadcast_template_id.template_id.name,
            "language": {
                "policy": "deterministic",
                "code": self.template_id.broadcast_template_id.language
            },
                "components": [
                {
                    "type" : "body",
                    "parameters": [
                        {
                            "type": "text",
                            "text": f"{self.get_body()}"
                        }  
                    ]
                }
            ]
            }
            }
        try:
            headers['Qiscus-App-Id'] = self.app_id
            headers['Qiscus-Secret-Key'] = self.token
            request_server = requests.post(f'{self.domain}{self.app_id}/{self.channel_id}/messages', json=param,headers=headers,verify=True)

        except ConnectionError:
            raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

        
    def send_wa_file(self,phone_number,file,file_name):
        phone_num = str(phone_number)
        if "+" in phone_num:
            phone_num =  int(phone_num.replace("+",""))
        try:
            attachment = base64.b64encode(file[0])
        except TypeError:
            attachment = file
        param_file = {'body': "data:application/pdf;base64," + attachment.decode('ascii') , 'phone': phone_num,'filename':file_name +'.pdf'}
        try:
            send_file = requests.post(f'{self.domain}/sendFile?token={self.token}',json=param_file,headers=headers, verify=True)
        except ConnectionError:
            raise ValidationError("Not connect to API Chat Server. Limit reached or not active")
        