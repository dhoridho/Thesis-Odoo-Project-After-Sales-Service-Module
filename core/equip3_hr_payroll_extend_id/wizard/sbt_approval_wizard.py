from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
import pytz

class HrSplitBankTransferApprovalWizard(models.TransientModel):
    _name = 'hr.split.bank.transfer.approval.wizard'
    _description = "HR Split Bank Transfer Approval Wizard"

    feedback = fields.Text()
    split_id = fields.Many2one('hr.split.bank.transfer')
    state = fields.Char()

    def submit(self):
        for line_item in self.split_id.split_approval_line_ids:
            if line_item.approver_state == 'draft' or line_item.approver_state == 'pending':
                for user in line_item.approver_ids:
                    if self.env.user.id in user.ids:
                        sequence_matrix = [data.sequence for data in self.split_id.split_approval_line_ids]
                        sequence_approval = [data.sequence for data in self.split_id.split_approval_line_ids.filtered(
                            lambda line: len(line.approver_confirm_ids) != line.minimum_approver)]
                        max_seq = max(sequence_matrix)
                        min_seq = min(sequence_approval)
                        approval = line_item.filtered(
                            lambda line: self.env.user.id in line.approver_ids.ids and len(
                                line.approver_confirm_ids) != line.minimum_approver and line.sequence == min_seq)
                        if approval:
                            self.split_id.approved_user_ids = [(4, self.env.user.id)]
                            approval.approver_confirm_ids = [(4, self.env.user.id)]
                            user_tz = self.env.user.tz or pytz.utc
                            local = pytz.timezone(user_tz)
                            timestamp = datetime.strftime(datetime.now().astimezone(local), '%d/%m/%Y %H:%M:%S')
                            if len(approval.approver_confirm_ids) == approval.minimum_approver:
                                approval.is_approve = True
                                approval.approver_state = 'approved'
                            else:
                                if self.state == "rejected":
                                    approval.approver_state = 'refuse'
                                else:
                                    approval.approver_state = 'pending'

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
                                self.split_id.state = 'rejected'
                                for line in self.split_id.split_bank_transfer_ids:
                                    line.state = 'rejected'

                            if self.state == "approved" and len(approval.approver_confirm_ids) == approval.minimum_approver and approval.sequence == max_seq:
                                self.split_id.state = 'approved'
                                for line in self.split_id.split_bank_transfer_ids:
                                    line.state = 'approved'

                        if not approval:
                            raise ValidationError("You not approval for this Request")