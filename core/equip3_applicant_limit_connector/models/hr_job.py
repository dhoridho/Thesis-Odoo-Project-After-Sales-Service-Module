from odoo import models,api,fields
from odoo.exceptions import ValidationError
import requests
from requests.exceptions import ConnectionError



class HrJobLimit(models.Model):
    _inherit='hr.job'
    
    
    
    def _compute_all_application_count(self):
        read_group_result = self.env['hr.applicant'].with_context(active_test=False).read_group([('job_id', 'in', self.ids),('is_blocked','=',False)], ['job_id'], ['job_id'])
        result = dict((data['job_id'][0], data['job_id_count']) for data in read_group_result)
        for job in self:
            job.all_application_count = result.get(job.id, 0)