from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from ...restapi.models.firebase_notification import fireBaseNotification

module = "hr.leave"
class HRLeave(models.Model):
    _inherit = 'hr.leave'

    def action_approve(self):
       
        res =  super(HRLeave,self).action_approve()
        obj = {'module':module,'id':f"{self.id}"}
        if self.employee_id.user_id.firebase_token:
            fireBaseNotification.sendPush("Approval of Leave Request","Your Leave Request has been approved.",eval(self.employee_id.user_id.firebase_token),obj) 
        return res
    
    def action_refuse(self):
        res =  super(HRLeave,self).action_refuse()
        obj = {'module':module,'id':f"{self.id}"}
        if self.employee_id.user_id.firebase_token:
            fireBaseNotification.sendPush("Rejection of Leave Request","Your request for your Leave has been rejected.",eval(self.employee_id.user_id.firebase_token),obj) 
        return res
        