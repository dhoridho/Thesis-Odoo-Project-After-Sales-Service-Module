from odoo import fields, models, api


class HrAttendanceChangeWizard(models.TransientModel):
    _name = 'hr.attendance.change.wizard'

    feedback = fields.Text()
    state = fields.Char()

    def submit(self):
        """ Prepare the Attendance Change feedback and trigger Approve. """
        self.ensure_one()
        hr_attendance_change = self.env['hr.attendance.change'].browse(self._context.get('active_ids', []))
        hr_attendance_change.feedback_parent = self.feedback
        if self.env.context.get('is_approve'):
            hr_attendance_change.action_approve()
        else:
            hr_attendance_change.action_refuse()
