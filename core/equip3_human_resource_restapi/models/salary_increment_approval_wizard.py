from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from ...restapi.models.firebase_notification import fireBaseNotification

module = "hr.salary.increment"
class SalaryIncrementWizard(models.TransientModel):
    _inherit = 'salary.increment.approval.wizard'

    def submit(self):
        res =  super(SalaryIncrementWizard,self).submit()
        obj = {'module':module,'id':f"{self.salary_increment_id.id}"}
        if self.salary_increment_id.employee_ids:
            for data in self.salary_increment_id.employee_ids:
                if data.user_id.firebase_token:
                    if self.state == "approved":
                        fireBaseNotification.sendPush("Approval of Salary Increment","Your Salary Increment has been Approved",eval(data.user_id.firebase_token),obj) 
                                        
                    if self.state == "rejected":
                        fireBaseNotification.sendPush("Rejection of Salary Increment","Your Salary Increment has been Rejected.",eval(data.user_id.firebase_token),obj)
        return res