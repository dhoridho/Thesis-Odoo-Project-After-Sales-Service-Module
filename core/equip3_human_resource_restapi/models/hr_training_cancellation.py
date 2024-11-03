from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from ...restapi.models.firebase_notification import fireBaseNotification

module = "hr.training.cancellation"
class HRTrainingCancellation(models.Model):
    _inherit = 'hr.training.cancellation'

    def action_approve(self):
        res =  super(HRTrainingCancellation,self).action_approve()
        obj = {'module':module,'id':f"{self.id}"}
        if self.employee_id.user_id.firebase_token:
            fireBaseNotification.sendPush("Approval of Training Cancellation","Your Training Cancellation has been Approved.",eval(self.employee_id.user_id.firebase_token),obj) 
        return res
    
    def action_reject(self):
        res =  super(HRTrainingCancellation,self).action_reject()
        obj = {'module':module,'id':f"{self.id}"}
        if self.employee_id.user_id.firebase_token:
            fireBaseNotification.sendPush("Rejection of Training Cancellation","Your Training Cancellation has been Rejected.",eval(self.employee_id.user_id.firebase_token),obj) 
        return res
        