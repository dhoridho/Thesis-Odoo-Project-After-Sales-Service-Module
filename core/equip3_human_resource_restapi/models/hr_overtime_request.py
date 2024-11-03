from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from ...restapi.models.firebase_notification import fireBaseNotification


class HROvertimeRequestApprovalWizard(models.TransientModel):
    _inherit = 'hr.overtime.approval.wizard'

    def submit(self):
        res =  super(HROvertimeRequestApprovalWizard,self).submit()
        obj = {'module':'hr.overtime.request','id':f"{self.overtime_id.id}"}
        if self.overtime_id.employee_id.user_id.firebase_token:
            if self.state == "rejected":
                fireBaseNotification.sendPush("Rejection of Overtime Request","Your overtime request has been rejected.",eval(self.overtime_id.employee_id.user_id.firebase_token),obj)

            if self.state == "approved":
                fireBaseNotification.sendPush("Approval of Overtime Request","Your overtime request has been approved.",eval(self.overtime_id.employee_id.user_id.firebase_token),obj) 
                            
        return res