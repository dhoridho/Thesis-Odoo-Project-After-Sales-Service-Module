from odoo import _, api, fields, models


class SchoolHrPayslip(models.Model):
    _inherit = "hr.payslip"

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
    
    def get_teacher_employee_type(self, employee_id):
        employee = self.env['hr.employee'].browse([employee_id])
        if employee and employee.user_id and employee.user_id.has_group('school.group_school_teacher'):
            teacher = self.env['school.teacher'].search([('employee_id', '=', employee.id)], limit=1)
            if teacher:
                return teacher.employee_type
        return False


    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        res = super(SchoolHrPayslip, self).get_worked_day_lines(contracts, date_from, date_to)
        for contract in contracts.filtered(lambda contract: contract.resource_calendar_id):
            teacher_hours, teacher_classes = self._get_total_number_of_hours_and_classes(contract.employee_id, date_from, date_to)
            if contract.employee_id and contract.employee_id.user_id.has_group('school.group_school_teacher'):
                total_hours = {
                    "name": _("Total Hours of Teacher in Month"),
                    "code": "TCH_HRS",
                    "sequence": 99,
                    "number_of_days": 0,
                    "number_of_hours": teacher_hours,
                    "contract_id": contract.id,
                }
                total_classes = {
                    "name": _("Total Presence (Classes) Teacher in Month"),
                    "sequence": 100,
                    "code": "TCH_CLS",
                    "number_of_days": teacher_classes,
                    "number_of_hours": 0,
                    "contract_id": contract.id,
                }
                res.extend([total_hours, total_classes])
        return res

