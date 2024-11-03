from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from ...restapi.models.firebase_notification import fireBaseNotification

module = " hr.leave.allocation"
class HRLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    def action_approve(self):
        res =  super(HRLeaveAllocation,self).action_approve()
        obj = {'module':module,'id':f"{self.id}"}
        if self.employee_id.user_id.firebase_token:
            fireBaseNotification.sendPush("Approval of Allocation Request","Your Allocation Request has been approved.",eval(self.employee_id.user_id.firebase_token),obj) 
        return res
    
    def action_refuse(self):
        res =  super(HRLeaveAllocation,self).action_refuse()
        obj = {'module':module,'id':f"{self.id}"}
        if self.employee_id.user_id.firebase_token:
            fireBaseNotification.sendPush("Rejection of Allocation Request","Your Allocation Request has been rejected.",eval(self.employee_id.user_id.firebase_token),obj) 
        return res
        