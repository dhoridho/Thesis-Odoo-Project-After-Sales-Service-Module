from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from ...restapi.models.firebase_notification import fireBaseNotification

module = "training.request"
class HRTrainingRequest(models.Model):
    _inherit = 'training.request'

    def action_approve(self):
        res =  super(HRTrainingRequest,self).action_approve()
        obj = {'module':module,'id':f"{self.id}"}
        if self.employee_id.user_id.firebase_token:
            fireBaseNotification.sendPush("Approval of Training Request","Your Training Request has been Approved.",eval(self.employee_id.user_id.firebase_token),obj) 
        return res
    
    def action_reject(self):
        res =  super(HRTrainingRequest,self).action_reject()
        obj = {'module':module,'id':f"{self.id}"}
        if self.employee_id.user_id.firebase_token:
            fireBaseNotification.sendPush("Rejection of Training Request","Your Training Request has been Rejected.",eval(self.employee_id.user_id.firebase_token),obj) 
        return res
    