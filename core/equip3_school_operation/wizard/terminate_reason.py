# See LICENSE file for full copyright and licensing details.


from odoo import _, models


class TerminateReasonFees(models.TransientModel):
    _inherit = "terminate.reason"

    def save_terminate(self):
        student = self._context.get("active_id")
        student_rec = self.env["student.student"].browse(student)
        student_rec.history_ids.write({'status': 'unactive'})
        academic_tracking = self.env['academic.tracking'].search([('student_id', '=', student_rec.id)])
        academic_tracking.intake_ids.write({'status': 'unactive'})
        return super(TerminateReasonFees, self).save_terminate()
