from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
import pytz

class HrAttendanceOfflineApprovalWizard(models.TransientModel):
    _name = 'hr.attendance.offline.approval.wizard'

    feedback = fields.Text()
    attendance_offline_id = fields.Many2one('hr.attendance.offline')
    state = fields.Char()

    def submit(self):
        for line_item in self.attendance_offline_id.approver_user_ids:
            if line_item.approver_state == 'draft' or line_item.approver_state == 'pending':
                for user in line_item.approver_ids:
                    if self.env.user.id in user.ids:
                        sequence_matrix = [data.sequence for data in self.attendance_offline_id.approver_user_ids]
                        sequence_approval = [data.sequence for data in self.attendance_offline_id.approver_user_ids.filtered(
                            lambda line: len(line.approved_user_ids) != line.minimum_approver)]
                        max_seq = max(sequence_matrix)
                        min_seq = min(sequence_approval)
                        approval = line_item.filtered(
                            lambda line: self.env.user.id in line.approver_ids.ids and len(
                                line.approved_user_ids) != line.minimum_approver and line.sequence == min_seq)
                        if approval:
                            self.attendance_offline_id.approved_user_ids = [(4, self.env.user.id)]
                            approval.approved_user_ids = [(4, self.env.user.id)]
                            user_tz = self.env.user.tz or pytz.utc
                            local = pytz.timezone(user_tz)
                            timestamp = datetime.strftime(datetime.now().astimezone(local), '%d/%m/%Y %H:%M:%S')
                            if len(approval.approved_user_ids) == approval.minimum_approver:
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
                                self.attendance_offline_id.state = self.state
                                line_item.approver_state = 'refuse'

                            if self.state == "approved" and len(approval.approved_user_ids) == approval.minimum_approver and approval.sequence == max_seq:
                                self.attendance_offline_id.state = self.state
                                line_item.approver_state = 'approved'
                                self.attendance_offline_id.action_update_attendance()

                        if not approval:
                            raise ValidationError("You not approval for this Request")