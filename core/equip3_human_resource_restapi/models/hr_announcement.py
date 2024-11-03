from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from ...restapi.models.firebase_notification import fireBaseNotification

class HRAnnountcement(models.Model):
    _inherit = 'hr.announcement'
    
    

    def submit(self):
        res =  super(HRAnnountcement,self).submit()
        if not self.is_announcement:
            query_params = []
            or_query = ""
            query_employee = ""
            query_department = ""
            query_job = ""
            if self.employee_ids:
                query_employee = "he2.id in %s"
                query_params.append(tuple(self.employee_ids.ids))
            if self.department_ids:
                if self.employee_ids:
                    or_query = "or"
                query_department = f"{or_query} he2.department_id in %s"
                query_params.append(tuple(self.department_ids.ids))
                
            if self.position_ids:
                if self.employee_ids or self.department_ids:
                    or_query = "or"
                query_job = f"{or_query} he2.job_id in %s"
                query_params.append(tuple(self.position_ids.ids))
                
                
            query = f"""
                select ru.firebase_token  from hr_employee he left join res_users ru on he.user_id = ru.id where ru.firebase_token is  not null and 
                he.id in (select he2.id from hr_employee he2 where {query_employee} {query_department}  {query_job})
                """

            self._cr.execute(query, query_params)
            data_result_ids = self.env.cr.dictfetchall()
        else:
            query_params = []
            query = f"""
                select ru.firebase_token  from hr_employee he left join res_users ru on he.user_id = ru.id where ru.firebase_token is  not null 
                """
            self._cr.execute(query, query_params)
            data_result_ids = self.env.cr.dictfetchall()
            
        if data_result_ids:
            obj = {'module':self._name,'id':f"{self.id}"}
            fb_token = []
            for data in data_result_ids:
                try:
                    fb_token.extend(eval(data['firebase_token']))
                except SyntaxError:
                    fb_token.append(data['firebase_token'])
            if fb_token:
                fireBaseNotification.sendPush("Announcement"," There is a new Announcement for you",fb_token,obj) 
            
        return res
    

        