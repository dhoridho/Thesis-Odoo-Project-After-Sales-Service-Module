from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
import pytz
from ...restapi.models.firebase_notification import fireBaseNotification

class HrOvertimeApprovalWizard(models.TransientModel):
    _inherit = 'hr.overtime.actual.approval.wizard'
    
    
    
    def submit(self):
        res =  super(HrOvertimeApprovalWizard,self).submit()
        obj = {'module':'hr.overtime.actual','id':f"{self.overtime_id.id}"}
        if self.overtime_id.employee_id.user_id.firebase_token:
            if self.state == "approved":
                fireBaseNotification.sendPush("Approval of Actual Overtime Request","Your overtime request has been approved",eval(self.overtime_id.employee_id.user_id.firebase_token),obj) 
                            
            if self.state == "rejected":
                fireBaseNotification.sendPush("Rejection of Actual Overtime Request","Your overtime request has been rejected.",eval(self.overtime_id.employee_id.user_id.firebase_token),obj)
        return res