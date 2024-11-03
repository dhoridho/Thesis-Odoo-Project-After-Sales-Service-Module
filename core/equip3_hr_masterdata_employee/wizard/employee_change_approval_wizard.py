from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
import pytz

class EmployeeChangeApprovalWizard(models.TransientModel):
    _name = 'employee.change.approval.wizard'

    feedback = fields.Text()
    changes_request_id = fields.Many2one('hr.employee.change.request')
    state = fields.Char('State')

    def submit(self):
        sequence_matrix = [data.sequence for data in self.changes_request_id.approval_line_ids]
        sequence_approval = [data.sequence for data in self.changes_request_id.approval_line_ids.filtered(
            lambda line: len(line.approved_employee_ids) != line.minimum_approver)]
        max_seq = max(sequence_matrix)
        min_seq = min(sequence_approval)
        approval = self.changes_request_id.approval_line_ids.filtered(
            lambda line: self.env.user.id in line.user_ids.ids and len(
                line.approved_employee_ids) != line.minimum_approver and line.sequence == min_seq)
        if approval:
            self.changes_request_id.approved_user_ids = [(4, self.env.user.id)]
            approval.approved_employee_ids = [(4, self.env.user.id)]
            user_tz = self.env.user.tz or 'UTC'
            local = pytz.timezone(user_tz)
            timestamp = datetime.strftime(datetime.now().astimezone(local), '%d/%m/%Y %H:%M:%S')
            if len(approval.approved_employee_ids) == approval.minimum_approver:
                approval.is_approve = True

            if not approval.approval_status:
                approval.approval_status = f"{self.env.user.name}:Approved" if self.state == "approved" else f"{self.env.user.name}:Rejected"
                if self.feedback:
                    approval.feedback = f"{self.env.user.name}:{self.feedback or ''}"
                else:
                    approval.feedback = f"{''}"
                approval.timestamp = f"{self.env.user.name}:{timestamp}"

            else:
                string_approval = []
                string_approval.append(approval.approval_status)
                if self.state == "approved":
                    string_approval.append(f"{self.env.user.name}:Approved")
                    approval.approval_status = "\n".join(string_approval)
                else:
                    string_approval.append(f"{self.env.user.name}:Rejected")
                    approval.approval_status = "\n".join(string_approval)

                if self.feedback:
                    feedback = f"{self.env.user.name}:{self.feedback or ''}"
                else:
                    feedback = f"{''}"
                feedback_list = [approval.feedback, feedback]
                final_feedback = "\n".join(feedback_list)
                approval.feedback = f"{final_feedback}"

                string_timestamp = [approval.timestamp, f"{self.env.user.name}:{timestamp}"]
                final_timestamp = "\n".join(string_timestamp)
                approval.timestamp = f"{final_timestamp}"

            if self.state == "rejected":
                self.changes_request_id.state = "rejected"

            if self.state == "approved" and len(approval.approved_employee_ids) == approval.minimum_approver and approval.sequence == max_seq:
                self.changes_request_id.state = "approved"
                self.changes_request_id.employee_id.write(self.changes_request_id.prepare_data_employee())
                self.changes_request_id.prepare_data_employee_lines()

        if not approval:
            raise ValidationError("You not approval for this Request")