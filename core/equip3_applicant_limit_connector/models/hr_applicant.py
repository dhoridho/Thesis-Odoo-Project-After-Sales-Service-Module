from odoo import models,api,fields
from odoo.exceptions import ValidationError
import requests
from requests.exceptions import ConnectionError


headers = {'content-type': 'application/json'}
domain_server = 'http://hrm.equip-onyx.com:5757'
user = 'admin'
password = 'admin'

class HrApplicantLimit(models.Model):
    _inherit='hr.applicant'
    is_blocked = fields.Boolean()
    
    
    
    def get_all_menu(self):
        if  not self.env.user.has_group('hr_recruitment.group_hr_recruitment_user'):
            job_id = self.env['hr.job'].search([])
            search_view_id= self.env.ref('hr_recruitment.hr_applicant_view_search_bis')
            data_job = []
            for record in job_id:
                data_stage = [data.stage_id.id for data in record.stage_ids.filtered(lambda line: self.env.user.id in line.user_ids.ids )]
                data_job.extend(data_stage)
            return {
            'type': 'ir.actions.act_window',
            'name': 'Applications',
            'res_model': 'hr.applicant',
            # 'view_type': 'kanban',
            'search_view_id':search_view_id.id,
            'view_mode': 'kanban,tree,form,graph,calendar,pivot,activity',
            'context':{},
            'domain': [('job_id.real_second_user_ids','in',self.env.user.id),('stage_id','in',data_job),('is_blocked','=',False)],
            }
            
        elif self.env.user.has_group('hr_recruitment.group_hr_recruitment_user') and not self.env.user.has_group('equip3_hr_accessright_settings.equip3_group_hr_recruitment_manager'):
            search_view_id= self.env.ref('hr_recruitment.hr_applicant_view_search_bis')
            return {
            'type': 'ir.actions.act_window',
            'name': 'Applications',
            'res_model': 'hr.applicant',
            # 'view_type': 'kanban',
            'search_view_id':search_view_id.id,
            'view_mode': 'kanban,tree,form,graph,calendar,pivot,activity',
            'context':{},
            'domain': [('job_id.user_ids','in',self.env.user.id),('is_blocked','=',False)]
            }
        elif  self.env.user.has_group('equip3_hr_accessright_settings.equip3_group_hr_recruitment_manager') and not self.env.user.has_group('hr_recruitment.group_hr_recruitment_manager'):
            search_view_id= self.env.ref('hr_recruitment.hr_applicant_view_search_bis')
            return {
            'type': 'ir.actions.act_window',
            'name': 'Applications',
            'res_model': 'hr.applicant',
            # 'view_type': 'kanban',
            'search_view_id':search_view_id.id,
            'view_mode': 'kanban,tree,form,graph,calendar,pivot,activity',
            'context':{},
            'domain': [('job_id.user_ids','in',self.env.user.id),('is_blocked','=',False)]
            }
        elif self.env.user.has_group('hr_recruitment.group_hr_recruitment_manager'):
            search_view_id= self.env.ref('hr_recruitment.hr_applicant_view_search_bis')
            return {
            'type': 'ir.actions.act_window',
            'name': 'Applications',
            'res_model': 'hr.applicant',
            # 'view_type': 'kanban',
            'search_view_id':search_view_id.id,
            'view_mode': 'kanban,tree,form,graph,calendar,pivot,activity',
            'context':{},
            'domain': [('is_blocked','=',False)]
            }
        
    def get_report_menu(self):
        search_view_id= self.env.ref('hr_recruitment.hr_applicant_view_search')
        views = [(self.env.ref('hr_recruitment.hr_applicant_view_graph').id, 'graph'),
                         (self.env.ref('hr_recruitment.hr_applicant_view_pivot').id, 'pivot')]
        context = {'search_default_creation_month': 1, 'search_default_job': 2}
        if  not self.env.user.has_group('hr_recruitment.group_hr_recruitment_user'):
            job_id = self.env['hr.job'].search([])
            data_job = []
            
            for record in job_id:
                data_stage = [data.stage_id.id for data in record.stage_ids.filtered(lambda line: self.env.user.id in line.user_ids.ids )]
                data_job.extend(data_stage)
            return {
            'type': 'ir.actions.act_window',
            'name': 'Recruitment Analysis',
            'res_model': 'hr.applicant',
            'view_type': 'graph',
            'views':views,
            'search_view_id':search_view_id.id,
            'view_mode': 'graph,pivot',
            'context':context,
            'domain': [('job_id.real_second_user_ids','in',self.env.user.id),('stage_id','in',data_job),('is_blocked','=',False)]
            }
        elif self.env.user.has_group('hr_recruitment.group_hr_recruitment_user') and not self.env.user.has_group('equip3_hr_accessright_settings.equip3_group_hr_recruitment_manager'):
            return {
            'type': 'ir.actions.act_window',
            'name': 'Recruitment Analysis',
            'res_model': 'hr.applicant',
            'view_type': 'graph',
            'views':views,
            'search_view_id':search_view_id.id,
            'view_mode': 'graph,pivot',
            'context':context,
            'domain': [('job_id.user_ids','in',self.env.user.id),('is_blocked','=',False)]
            }
        elif  self.env.user.has_group('equip3_hr_accessright_settings.equip3_group_hr_recruitment_manager') and not self.env.user.has_group('hr_recruitment.group_hr_recruitment_manager'):
            return {
            'type': 'ir.actions.act_window',
            'name': 'Recruitment Analysis',
            'res_model': 'hr.applicant',
            'view_type': 'graph',
            'views':views,
            'search_view_id':search_view_id.id,
            'view_mode': 'graph,pivot',
            'context':context,
            'domain': [('job_id.user_ids','in',self.env.user.id),('is_blocked','=',False)]
            }
        elif self.env.user.has_group('hr_recruitment.group_hr_recruitment_manager'):
            return {
            'type': 'ir.actions.act_window',
            'name': 'Recruitment Analysis',
            'res_model': 'hr.applicant',
            'view_type': 'graph',
            'views':views,
            'search_view_id':search_view_id.id,
            'view_mode': 'graph,pivot',
            'domain': [('is_blocked','=',False)],
            'context':context
            }
        
    
    def get_menu(self):
        if  not self.env.user.has_group('hr_recruitment.group_hr_recruitment_user'):
            search_view_id= self.env.ref('hr_recruitment.hr_applicant_view_search_bis')
            job_id = self.env['hr.job'].search([])
            data_job = []
            for record in job_id:
                data_stage = [data.stage_id.id for data in record.stage_ids.filtered(lambda line: self.env.user.id in line.user_ids.ids )]
                data_job.extend(data_stage)
        
            return {
            'type': 'ir.actions.act_window',
            'name': 'Applications',
            'res_model': 'hr.applicant',
            'view_type': 'kanban',
            'search_view_id':search_view_id.id,
            'view_mode': 'kanban,tree,form,graph,calendar,pivot',
            'context':{'search_default_job_id': self.env.context.get('active_id'), 'default_job_id': self.env.context.get('active_id')},
            'domain': [('job_id.real_second_user_ids','in',self.env.user.id),('stage_id','in',data_job),('is_blocked','=',False)]
            }
        elif self.env.user.has_group('hr_recruitment.group_hr_recruitment_user') and not self.env.user.has_group('equip3_hr_accessright_settings.equip3_group_hr_recruitment_manager'):
            search_view_id= self.env.ref('hr_recruitment.hr_applicant_view_search_bis')
            return {
            'type': 'ir.actions.act_window',
            'name': 'Applications',
            'res_model': 'hr.applicant',
            'view_type': 'kanban',
            'search_view_id':search_view_id.id,
            'view_mode': 'kanban,tree,form,graph,calendar,pivot',
            'context':{'search_default_job_id': self.env.context.get('active_id'), 'default_job_id': self.env.context.get('active_id')},
            'domain': [('job_id.user_ids','in',self.env.user.id),('is_blocked','=',False)]
            }
        elif  self.env.user.has_group('equip3_hr_accessright_settings.equip3_group_hr_recruitment_manager'):
            search_view_id= self.env.ref('hr_recruitment.hr_applicant_view_search_bis')
            return {
            'type': 'ir.actions.act_window',
            'name': 'Applications',
            'res_model': 'hr.applicant',
            'view_type': 'kanban',
            'search_view_id':search_view_id.id,
            'view_mode': 'kanban,tree,form,graph,calendar,pivot',
            'context':{'search_default_job_id': self.env.context.get('active_id'), 'default_job_id': self.env.context.get('active_id')},
            'domain': [('is_blocked','=',False)]
           
            }
    
    
    
    def get_session(self,domain):
        try:
            data = {'login': f'{user}','password':f'{password}'}
            request_server = requests.post(f'{domain}/api/v1/auth/login', json=data,headers=headers,verify=False)
        except ConnectionError:
            raise ValidationError("Not connect to API Server. Limit reached or not active")
        return request_server.status_code,request_server.cookies['session_id']
        
    
    @api.model
    def create(self, vals_list):
        res =  super(HrApplicantLimit,self).create(vals_list)
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        status_code,cookies= self.get_session(domain_server)
        if status_code == requests.codes.ok:
            # print("response")
            # print(cookies)
            data = {'domain':base_url}
            jar = requests.cookies.RequestsCookieJar()
            jar.set('session_id', cookies)
            headers['cookie'] = f'session_id={cookies}'
            # print(headers)
            request_server_limit = requests.post(f'{domain_server}/api/v1/limit', json=data,headers=headers,verify=False)
            response = request_server_limit.json()
            # print(response)
            # print(base_url)
            if 'result' in response:
                try:
                    if response['result']['status_code'] == 404:
                        raise ValidationError("Not connect to API Server. Applicant limit has been exceeded or not active. Please contact administrator! ")
                    if response['result']['content']['data']['over_limit']:
                        res.is_blocked = True
                except KeyError:
                       raise ValidationError("Not connect to API Server. API Has Error Response")
            
        else:
            raise ValidationError("Not connect to API Server")
        
        return res
    
    