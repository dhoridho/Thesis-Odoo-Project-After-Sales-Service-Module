from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from ...restapi.models.firebase_notification import fireBaseNotification

module = "travel.request"
class HRTravelRequest(models.Model):
    _inherit = 'travel.request'

    def action_approve(self):
        res =  super(HRTravelRequest,self).action_approve()
        obj = {'module':module,'id':f"{self.id}"}
        if self.employee_id.user_id.firebase_token:
            fireBaseNotification.sendPush("Approval of Travel Request","Your Travel Request has been Approved.",eval(self.employee_id.user_id.firebase_token),obj) 
        return res
    
    def action_reject(self):
        res =  super(HRTravelRequest,self).action_reject()
        obj = {'module':module,'id':f"{self.id}"}
        if self.employee_id.user_id.firebase_token:
            fireBaseNotification.sendPush("Rejection of Travel Request","Your Travel Request has been Rejected.",eval(self.employee_id.user_id.firebase_token),obj) 
        return res
        