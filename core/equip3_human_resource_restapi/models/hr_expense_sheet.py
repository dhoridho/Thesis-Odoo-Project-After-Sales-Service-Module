from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from ...restapi.models.firebase_notification import fireBaseNotification

module = "hr.expense.sheet"
class HRExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    def approve_expense_sheets(self):
        res =  super(HRExpenseSheet,self).approve_expense_sheets()
        obj = {'module':module,'id':f"{self.id}"}
        if self.employee_id.user_id.firebase_token:
            fireBaseNotification.sendPush("Approval of Expense Request","Your expense request has been approved.",eval(self.employee_id.user_id.firebase_token),obj) 
        return res
    
    def expense_refuse_sheet(self):
        res =  super(HRExpenseSheet,self).expense_refuse_sheet()
        obj = {'module':module,'id':f"{self.id}"}
        if self.employee_id.user_id.firebase_token:
            fireBaseNotification.sendPush("Rejection of Expense Request","Your expense request has been rejected.",eval(self.employee_id.user_id.firebase_token),obj) 
        return res
        