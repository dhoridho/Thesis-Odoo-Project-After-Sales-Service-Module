from odoo import api, models, fields


class StudentLeaveFeedbackWizard(models.TransientModel):
    _name = "student.leave.feedback.wizard"
    _description = "Student Leave Feedback Wizard"

    name = fields.Text("Reasons")
    student_leave_request_id = fields.Many2one('studentleave.request', string='Student Leave Request')

    def submit(self):
        self.ensure_one()
        leave_request = self.env["studentleave.request"].browse([self.student_leave_request_id.id])
        if leave_request:
            leave_request.action_reject(self.name)
