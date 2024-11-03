from odoo import api, fields, models, _

class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    number_of_hours = fields.Float(compute='_compute_number_of_hours', inverse='_set_number_of_hours', store=True)

    @api.depends(
        'payslip_id', 'payslip_id.employee_id', 'payslip_id.teacher_attendance_ids', 
        'payslip_id.ttlnbrofhrs_hours', 'payslip_id.ttlnbrofclss_hours', 'code',
    )
    def _compute_number_of_hours(self):
        for rec in self:
            if rec.payslip_id.teacher_attendance_ids:
                user = rec.payslip_id.employee_id.user_id
                is_teacher = user.has_group('school.group_school_teacher')
                if is_teacher and rec.code == 'TTLNBROFHRS':
                    rec.number_of_hours = rec.payslip_id.ttlnbrofhrs_hours
                elif is_teacher and rec.code == 'TTLNBROFCLSS':
                    rec.number_of_hours = rec.payslip_id.ttlnbrofclss_hours

    def _set_number_of_hours(self):
        pass

class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    teacher_attendance_ids = fields.Many2many('teacher.attendance', compute='_compute_teacher_attendance_ids')
    ttlnbrofhrs_hours = fields.Float()
    ttlnbrofclss_hours = fields.Float()

    def _compute_teacher_attendance_ids(self):
        for rec in self:
            rec.teacher_attendance_ids = [(5, 0, 0)]
            if rec.employee_id and rec.employee_id.user_id.has_group('school.group_school_teacher'):
                rec.teacher_attendance_ids = [(6, 0, self.env['teacher.attendance'].search([('teacher_id.user_id', '=', rec.employee_id.user_id.id)]).ids)]
                teacher_hours = 0
                teacher_classes = 0
                for teacher_attendance in rec.teacher_attendance_ids:
                    daily_attendances = teacher_attendance.daily_attendance_ids.filtered(lambda x: x.date >= rec.date_from and x.date <= rec.date_to)
                    teacher_hours += sum(daily_attendances.mapped('hours'))
                    teacher_classes += len(daily_attendances)
                rec.ttlnbrofhrs_hours = teacher_hours
                rec.ttlnbrofclss_hours = teacher_classes

    def _get_total_number_of_hours_and_classes(self, employee, date_from, date_to):
        teacher_hours = 0
        teacher_classes = 0
        teacher_attendance_ids = self.env['teacher.attendance'].search([('teacher_id.user_id', '=', employee.user_id.id)])
        if teacher_attendance_ids:
            date_from = fields.Date.from_string(date_from)
            date_to = fields.Date.from_string(date_to)
            for teacher_attendance in teacher_attendance_ids:
                daily_attendances = teacher_attendance.daily_attendance_ids.filtered(lambda x: x.date >= date_from and x.date <= date_to)
                teacher_hours += sum(daily_attendances.mapped('hours'))
                teacher_classes += len(daily_attendances)
        return teacher_hours, teacher_classes
