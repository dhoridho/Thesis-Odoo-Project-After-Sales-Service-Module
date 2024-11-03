# -*- coding: utf-8 -*-

from odoo import fields, models, tools

class HrAttendanceChangeAnalysis(models.Model):
    _name = "hr.attendance.change.analysis"
    _description = 'HR Attendance Change Analysis'
    _auto = False

    employee_id = fields.Many2one('hr.employee', string='Employee')
    date = fields.Date('Date')
    request_count = fields.Integer('Request Count')

    def init(self):
        tools.drop_view_if_exists(self._cr, 'hr_attendance_change_analysis')

        self._cr.execute("""
            CREATE or REPLACE view hr_attendance_change_analysis as (
                SELECT
                    ROW_NUMBER() over() as id, change.employee_id as employee_id,
                    change_line.date as date,
                    count(1) filter (where change.state='to_approve' OR change.state='approved') AS request_count
                    FROM hr_attendance_change_line change_line
                    LEFT JOIN hr_attendance_change change ON change_line.hr_attendance_change_id=change.id
                    WHERE change.state='to_approve' OR change.state='approved'
                    GROUP BY change.employee_id, change_line.date
            )
        """)