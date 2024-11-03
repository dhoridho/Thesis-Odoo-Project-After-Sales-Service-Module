from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from ...restapi.models.firebase_notification import fireBaseNotification


module = "hr.leave.cancelation"
class HRLeaveCancellation(models.Model):
    _inherit = 'hr.leave.cancelation'

    def action_approve(self):
        res =  super(HRLeaveCancellation,self).action_approve()
        obj = {'module':module,'id':f"{self.id}"}
        if self.employee_id.user_id.firebase_token:
            fireBaseNotification.sendPush("Approval of Leave Cancellation","Your Leave Cancellation has been approved.",eval(self.employee_id.user_id.firebase_token),obj) 
        return res
    
    def action_refuse(self):
        res =  super(HRLeaveCancellation,self).action_refuse()
        obj = {'module':module,'id':f"{self.id}"}
        if self.employee_id.user_id.firebase_token:
            fireBaseNotification.sendPush("Rejection of Leave Cancellation","Your Leave Cancellation has been rejected.",eval(self.employee_id.user_id.firebase_token),obj) 
        return res
        