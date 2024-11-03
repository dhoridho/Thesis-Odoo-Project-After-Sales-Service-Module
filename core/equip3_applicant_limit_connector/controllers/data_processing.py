# -*- coding: utf-8 -*-

from .encryption import *
from .response import APIResponse
from odoo import http
import json




class APIApplicantLimit(APIResponse):
    def update_applicant(self,body):
        applicant_model = request.env['hr.applicant']
        applicant_to_update = applicant_model.sudo().search([('is_blocked','=',True)],limit=int(body['limit']),order='id asc')
        if applicant_to_update:
            applicant_to_update.is_blocked = False
            self.set_status_code(200)
            self.set_content({'state':True,'update_applicant':len(applicant_to_update)})
        else:
            self.set_not_found()
        return self.get_response()
        
            
        
    
    
    