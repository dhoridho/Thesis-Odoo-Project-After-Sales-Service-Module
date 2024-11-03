from typing import Sequence
from odoo import fields,models,api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from pytz import timezone

class Equp3CareerTransitionPopupWizard(models.TransientModel):
    _name = 'career.transition.wizard'
    feedback = fields.Text()
    transition_id = fields.Many2one('hr.career.transition')
    state = fields.Char(related='transition_id.transition_wizard_state')
    
    
    def submit(self):
        if not self.feedback:
            self.feedback = ""
        for line_item in self.transition_id.approval_matrix_ids:
            if line_item.approver_state == 'draft' or line_item.approver_state == 'pending':
                for user in line_item.approver_id:
                    if self.env.user.id in user.ids:
                        sequence = [data.sequence for data in self.transition_id.approval_matrix_ids]
                        sequence_app = [data.sequence for data in self.transition_id.approval_matrix_ids.filtered(lambda  line:len(line.approver_confirm) != line.minimum_approver )]
                        max_seq =  max(sequence)
                        min_seq =  min(sequence_app)
                        now = datetime.now(timezone(self.env.user.tz))
                        dateformat = f"{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"
                        approval = line_item.filtered(lambda  line:self.env.user.id in line.approver_id.ids and len(line.approver_confirm) != line.minimum_approver and  line.sequence == min_seq)
                        if approval:
                            self.transition_id.approved_user_ids = [(4, self.env.user.id)]
                            approval.approver_confirm = [(4,self.env.user.id)]
                            if len(approval.approver_confirm) == approval.minimum_approver:
                                approval.is_approve = True
                            if len(approval.approver_confirm) == approval.minimum_approver and not approval.sequence == max_seq and self.state != "rejected":
                                self.transition_id.approver_mail()
                                self.transition_id.approver_wa_template()
                            if not approval.approval_status:
                                approval.approval_status = f"{self.env.user.name}:Approved" if  self.state == "approve" else f"{self.env.user.name}:Rejected"
                                if self.feedback:
                                    approval.feedback = f"{self.env.user.name}:{self.feedback}"
                                else:
                                    approval.feedback = ""
                            else:
                                string_approval = []
                                string_approval.append(approval.approval_status)
                                if  self.state == "approve":
                                    string_approval.append(f"{self.env.user.name}:Approved")
                                    approval.approval_status = "\n".join(string_approval)
                                else:
                                    string_approval.append(f"{self.env.user.name}:Rejected")
                                    approval.approval_status = "\n".join(string_approval)

                                if self.feedback:
                                    feedback_list = [approval.feedback,
                                                     f"{self.env.user.name}:{self.feedback}"]
                                    final_feedback = "\n".join(feedback_list)
                                    approval.feedback = f"{final_feedback}"
                                elif approval.feedback and not self.feedback:
                                    approval.feedback = approval.feedback
                                else:
                                    approval.feedback = ""
                            timestamp = f"{self.env.user.name}:{dateformat}"
                            if approval.timestamp:
                                string_timestammp = [approval.timestamp]
                                string_timestammp.append(timestamp)
                                approval.timestamp= "\n".join(string_timestammp)
                            if not approval.timestamp:
                                approval.timestamp =  timestamp

                            if self.state == "rejected":
                                self.transition_id.status = self.state
                                self.transition_id.reject_mail()
                                self.transition_id.rejected_wa_template()


                            # approval.timestamp = datetime.now()
                            if len(approval.approver_confirm) == approval.minimum_approver and approval.sequence == max_seq and self.state == "approve":
                                self.transition_id.status = self.state
                                self.transition_id.approved_mail()
                                self.transition_id.approved_wa_template()
                                self.transition_id.update_career_transition_letter()
                                if self.transition_id.career_transition != 'termination' and self.state == "approve":
                                    self.transition_id.is_hide_renew = False
                                if self.transition_id.contract_id:
                                    transition_date = datetime.strptime(str(self.transition_id.transition_date), "%Y-%m-%d") + timedelta(days=-1)
                                    self.transition_id.contract_id.date_end = transition_date
                                    self.transition_id.contract_id.career_transition_id = self.transition_id.id
                            # elif self.state == "rejected":
                            #     self.transition_id.status = self.state
                            #     self.transition_id.reject_mail()
                            #     self.transition_id.rejected_wa_template()

                        if not approval:
                            raise ValidationError("You not approval for this Request")
            
            
            
    