from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from ...restapi.models.firebase_notification import fireBaseNotification


class HRAttendanceChangeRequest(models.Model):
    _inherit = 'hr.attendance.change'

    def action_approve(self):
        res =  super(HRAttendanceChangeRequest,self).action_approve()
        obj = {'module':'hr.attendance.change','id':f"{self.id}"}
        if self.employee_id.user_id.firebase_token:
            fireBaseNotification.sendPush("Approval of Attendance Change Request","Your attendance change request has been approved.",eval(self.employee_id.user_id.firebase_token),obj) 
        return res
    
    def action_refuse(self):
        res =  super(HRAttendanceChangeRequest,self).action_refuse()
        obj = {'module':'hr.attendance.change','id':f"{self.id}"}
        if self.employee_id.user_id.firebase_token:
            fireBaseNotification.sendPush("Rejection of Attendance Change Request","Your attendance change request has been rejected.",eval(self.employee_id.user_id.firebase_token),obj) 
        return res
        