from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from ...restapi.models.firebase_notification import fireBaseNotification

module = "hr.employee.change.request"
class EmployeeChangeApprovalWizard(models.TransientModel):
    _inherit = 'employee.change.approval.wizard'

    def submit(self):
        res =  super(EmployeeChangeApprovalWizard,self).submit()
        obj = {'module':module,'id':f"{self.changes_request_id.id}"}
        if self.changes_request_id.employee_id.user_id.firebase_token: 
            if self.state == "approved":
                fireBaseNotification.sendPush("Approval of Employee Change Request","Your Employee Change Request has been Approved.",eval(self.changes_request_id.employee_id.user_id.firebase_token),obj) 
                                
            if self.state == "rejected":
                fireBaseNotification.sendPush("Rejection of Employee Change Request"," Your Employee Change Request has been Rejected.",eval(self.changes_request_id.employee_id.user_id.firebase_token),obj)
        return res