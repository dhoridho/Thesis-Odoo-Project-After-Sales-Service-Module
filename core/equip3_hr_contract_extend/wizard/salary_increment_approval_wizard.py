from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
import pytz

class SalaryIncrementApprovalWizard(models.TransientModel):
    _name = 'salary.increment.approval.wizard'

    feedback = fields.Text()
    salary_increment_id = fields.Many2one('hr.salary.increment')
    state = fields.Char('State')

    def submit(self):
        current_user = self.env.uid
        if self.env.user not in self.salary_increment_id.approved_user_ids:
            if self.salary_increment_id.is_approver:
                for user in self.salary_increment_id.approver_user_ids:
                    for approver in user.approver_id:
                        if current_user == approver.id:
                            self.salary_increment_id.approved_user_ids = [(4, current_user)]
                            user.approved_employee_ids = [(4, current_user)]
                            var = len(user.approved_employee_ids) + 1
                            user_tz = self.env.user.tz or 'UTC'
                            local = pytz.timezone(user_tz)
                            timestamp = datetime.strftime(datetime.now().astimezone(local), '%d/%m/%Y %H:%M:%S')
                            if len(user.approved_employee_ids) == user.minimum_approver:
                                user.is_approve = True
                            if not user.approval_status:
                                user.approval_status = f"{self.env.user.name}:Approved" if self.state == "approved" else f"{self.env.user.name}:Rejected"
                                if self.feedback:
                                    user.feedback = f"{self.env.user.name}:{self.feedback or ''}"
                                else:
                                    user.feedback = f"{''}"
                                user.timestamp = f"{self.env.user.name}:{timestamp}"
                            else:
                                string_approval = []
                                string_approval.append(user.approval_status)
                                if self.state == "approved":
                                    string_approval.append(f"{self.env.user.name}:Approved")
                                    user.approval_status = "\n".join(string_approval)
                                else:
                                    string_approval.append(f"{self.env.user.name}:Rejected")
                                    user.approval_status = "\n".join(string_approval)

                                if self.feedback:
                                    feedback = f"{self.env.user.name}:{self.feedback or ''}"
                                else:
                                    feedback = f"{''}"
                                feedback_list = [user.feedback, feedback]
                                final_feedback = "\n".join(feedback_list)
                                user.feedback = f"{final_feedback}"

                                string_timestamp = [user.timestamp, f"{self.env.user.name}:{timestamp}"]
                                final_timestamp = "\n".join(string_timestamp)
                                user.timestamp = f"{final_timestamp}"
                
                if self.state == "rejected":
                    self.salary_increment_id.state = "rejected"
                else:
                    matrix_line = sorted(self.salary_increment_id.approver_user_ids.filtered(lambda r: r.is_approve == False))
                    if len(matrix_line) == 0:
                        self.salary_increment_id.state = "approved"
        else:
            raise ValidationError("You not approval for this Request")