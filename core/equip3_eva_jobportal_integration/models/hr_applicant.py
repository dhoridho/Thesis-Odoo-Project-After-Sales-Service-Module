from jsonschema import ValidationError
from odoo import fields,models,api
import requests
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT,DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime


headers = {'content-type': 'application/json', 'accept': '*/*','Accept-Encoding':'gzip, deflate, br'}

class hrApplicant(models.Model):
    _inherit = 'hr.applicant'
    
    
    def eva_env(self):
        is_eva_job_portal_integration = self.env['ir.config_parameter'].sudo().get_param('equip3_eva_jobportal_integration.is_eva_job_portal_integration')
        eva_job_portal_url = self.env['ir.config_parameter'].sudo().get_param('equip3_eva_jobportal_integration.eva_job_portal_url')
        token = self.env["ir.config_parameter"].sudo().get_param('equip3_eva_jobportal_integration.eva_job_portal_token')
        return is_eva_job_portal_integration,eva_job_portal_url,token
    
    def unlink(self):
        res =  super(hrApplicant,self).unlink()
        is_eva_job_portal_integration,eva_job_portal_url,token =self.eva_env()
        headers['Authorization'] = f'Bearer {token}'
        if is_eva_job_portal_integration:
            for data in self:
                request = requests.delete(eva_job_portal_url+ '/api/v1/job-applicants/'+str(data.id),headers=headers)
        return res
    
    
    @api.model
    def create(self, vals):
        res =  super(hrApplicant,self).create(vals)
        if not self.env.context.get('is_testing'):
            is_eva_job_portal_integration,eva_job_portal_url,token =self.eva_env()
            if is_eva_job_portal_integration:
                keys = {
                    "external_id":res.id,
                    'job_position_id': f"{res.job_id.id}" if res.job_id else "",
                    'company_id': res.company_id.id if res.company_id else "",
                    'name': res.partner_name,
                    "gender":res.gender if res.gender else "",
                    "email":res.email_from if res.email_from else "",
                    "phone":res.partner_phone if res.partner_phone else "",
                    "date_of_birth":res.date_of_birth.strftime(DEFAULT_SERVER_DATE_FORMAT) if self.date_of_birth else "",
                    "age":res.birth_years,
                    "address":res.address if res.address else "-",
                    "cv":res.file_cv.decode('utf-8') if res.file_cv else "",
                    "identification_no":res.identification_no if res.identification_no else "-",
                    "working_experience":res.working_experience,
                    "expected_salary":res.salary_expected,
                    "marital_status":res.marital_status.name if res.marital_status else "-",
                    "religion":res.religion.name if res.religion else "-",
                    "degree":res.type_id.name if res.type_id else "-",
                        }
                headers['Authorization'] = f'Bearer {token}'
                request = requests.post(eva_job_portal_url+ '/api/v1/job-applicants',json=keys,headers=headers)  
                print("request")      
                print("request")      
                print(keys)      
                print(request.content)
               

        return res
    
    
    
    def write(self, vals):
        res =  super(hrApplicant,self).write(vals)
        is_eva_job_portal_integration,eva_job_portal_url,token =self.eva_env()
        if is_eva_job_portal_integration:
            keys = {
                'job_position_id': str(self.job_id.id) if self.job_id else "",
                'company_id': self.company_id.id if self.company_id else "",
                'name': self.partner_name,
                "gender":self.gender if self.gender else '',
                "email":self.email_from if self.email_from else "",
                "phone":self.partner_phone if self.partner_phone else "",
                "date_of_birth":self.date_of_birth.strftime(DEFAULT_SERVER_DATE_FORMAT) if self.date_of_birth else "",
                "age":self.birth_years,
                "address":self.address if self.address else "-",
                "cv":self.file_cv.decode('utf-8') if self.file_cv else "",
                "identification_no":self.identification_no if self.identification_no else "-",
                "working_experience":self.working_experience,
                "expected_salary":self.salary_expected,
                "marital_status":self.marital_status.name if self.marital_status else "-",
                "religion":self.religion.name if self.religion else "-",
                "degree":self.type_id.name if self.type_id else "-",
                    }
            headers['Authorization'] = f'Bearer {token}'
            request = requests.put(eva_job_portal_url+ '/api/v1/job-applicants/'+str(self.id),json=keys,headers=headers)  
            print("request")      
            print("request")      
            print(keys)      
            print(request.content)      

        return res
    
    
    