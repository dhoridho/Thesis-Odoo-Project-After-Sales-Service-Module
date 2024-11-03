from jsonschema import ValidationError
from odoo import fields,models,api,_
import requests
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime


headers = {'content-type': 'application/json', 'accept': '*/*','Accept-Encoding':'gzip, deflate, br'}

class hrJob(models.Model):
    _inherit = 'hr.job'
    
    industry_id = fields.Many2one('res.partner.industry')
    job_category_id = fields.Many2one('job.category')
    job_type = fields.Selection([('full_time','Full Time'),('part_time','Part Time'),('freelancer','Freelancer')])
    workplace_type = fields.Selection([('remote','Remote'),('onsite','On-site'),('hybrid','Hybrid')])
    scheduled_pay = fields.Selection([('annually','Annually'),('monthly','Monthly'),('hourly','Hourly')],default='monthly')
    vacancy_deadline = fields.Datetime()
    experience_level = fields.Selection([('internship','Internship'),('entry_level','Entry Level'),('associate','Associate'),('mid_level','Mid Level'),('director','Director'),('executive','Executive')])
    minimum_salary = fields.Float()
    maximum_salary = fields.Float()
    currency_job_id = fields.Many2one('res.currency',default=lambda self:self.env.ref('base.IDR').id)
    is_salary_confidential = fields.Boolean()
    is_published_clone = fields.Boolean(default=False)
    experience_length = fields.Selection([('less_than_1_year','Less than 1 year'),('1_3_years','1 - 3 years'),('3_5_years','3 - 5 years'),('5_10_years','5 - 10 years'),('more_than_10_years','more than 10 years')])
    update_eva_failed = fields.Boolean(default=False)
    create_eva_failed = fields.Boolean(default=False)
    
    @api.constrains('minimum_salary','maximum_salary')
    def _constrain_minimum_salary(self):
        for data in self:
            if data.minimum_salary and data.maximum_salary:
                if data.minimum_salary >= data.maximum_salary:
                    raise UserError(_("Minimum Salary should be less than Maximum Salary"))
    
    
    def eva_env(self):
        is_eva_job_portal_integration = self.env['ir.config_parameter'].sudo().get_param('equip3_eva_jobportal_integration.is_eva_job_portal_integration')
        eva_job_portal_url = self.env['ir.config_parameter'].sudo().get_param('equip3_eva_jobportal_integration.eva_job_portal_url')
        token = self.env["ir.config_parameter"].sudo().get_param('equip3_eva_jobportal_integration.eva_job_portal_token')
        return is_eva_job_portal_integration,eva_job_portal_url,token
    
    def unlink(self):
        res =  super(hrJob,self).unlink()
        is_eva_job_portal_integration,eva_job_portal_url,token =self.eva_env()
        if is_eva_job_portal_integration:
            headers['Authorization'] = f'Bearer {token}'
            request = requests.delete(eva_job_portal_url+ '/api/v1/job-positions/'+str(self.id),headers=headers)
        return res
    
    
    @api.model
    def create(self, vals_list):
        res =  super(hrJob,self).create(vals_list)
        is_eva_job_portal_integration,eva_job_portal_url,token =self.eva_env()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', default='')
        
        if is_eva_job_portal_integration:
            keys = {
                "external_id":res.id,
                'job_title': res.name,
                    'job_description':res.description if res.description else "", 
                    'vacancy_deadline':res.vacancy_deadline.strftime(DEFAULT_SERVER_DATETIME_FORMAT) if self.vacancy_deadline else datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'is_published':res.is_published,
                    'is_salary_confidential':res.is_salary_confidential,
                    'minimum_salary':res.minimum_salary,
                    'maximum_salary':res.maximum_salary,
                    'experience_level':res.experience_level if res.experience_level  else "",
                    'experience_length':res.experience_length if res.experience_length else "",
                    'workplace_type':res.workplace_type if res.workplace_type else "",
                    'job_type':res.job_type if res.job_type else "",
                    'website_description':res.website_description,
                    'company_id':res.company_id.id if res.company_id else "",
                    'work_location':res.custom_work_location_id.name if res.custom_work_location_id else "",
                    'currency':res.currency_job_id.name if res.currency_job_id else "",
                    'scheduled_pay':res.scheduled_pay,
                    'job_apply_url':  base_url + '/jobs/apply/' + str(res.id)
                    }
                            
            headers['Authorization'] = f'Bearer {token}'
            request = requests.post(eva_job_portal_url+ '/api/v1/job-positions',json=keys,headers=headers)
            try:
                if request.status_code != 200:
                    self.create_eva_failed = True
            except Exception as e:
                self.create_eva_failed = True
        
        
        return  res
    
    
    def write(self, vals):
        res =  super(hrJob,self).write(vals)
        is_eva_job_portal_integration,eva_job_portal_url,token =self.eva_env()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', default='')
        if is_eva_job_portal_integration:
            keys = {'job_title': self.name,
                    'job_description':self.description,
                    'vacancy_deadline':self.vacancy_deadline.strftime(DEFAULT_SERVER_DATETIME_FORMAT) if self.vacancy_deadline else "",
                    'is_published':self.is_published,
                    'is_salary_confidential':self.is_salary_confidential,
                    'minimum_salary':self.minimum_salary,
                    'maximum_salary':self.maximum_salary,
                    'experience_level':self.experience_level,
                    'experience_length':self.experience_length,
                    'workplace_type':self.workplace_type,
                    'job_type':self.job_type,
                    'website_description':self.website_description,
                    'company_id':self.company_id.id,
                    'work_location':self.custom_work_location_id.name,
                    'currency':self.currency_job_id.name,
                    'scheduled_pay':self.scheduled_pay,
                    'job_apply_url':  base_url + '/jobs/apply/' + str(self.id)
                    }
            headers['Authorization'] = f'Bearer {token}'
            request = requests.put(eva_job_portal_url+ '/api/v1/job-positions/'+str(self.id),json=keys,headers=headers)        

        return res
    
    @api.onchange('is_published_clone')
    def _onchange_is_published_clone(self):
        for data in self:
            if data.is_published_clone:
                data.write({'is_published':data.is_published_clone})
            elif not data.is_published_clone:
                data.write({'is_published':False})
                
                
    @api.onchange('is_published')
    def _onchange_is_published_eva(self):
        for data in self:
            if data.is_published:
                data.is_published_clone = data.is_published
            if not data.is_published:
                data.is_published_clone = False