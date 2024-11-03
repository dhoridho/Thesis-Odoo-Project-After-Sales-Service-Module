from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError
from datetime import date, datetime, timedelta


class HrEmployeeHSE(models.Model):
    _inherit = "hr.employee"

    # These 2 fields is a workaround to make the compute work as intended
    compute_safe_hour = fields.Float(string='Compute Safe Man-Hours', compute='_compute_safe_hour', store=False)
    safe_hour = fields.Float(string='Safe Man-Hours', store=True)

    incident_report_ids = fields.One2many('incident.report.employee', 'employee_id')
    safe_hour_history_ids = fields.One2many('safe.hour.history', 'employee_id')

    @api.depends('incident_report_ids', 'safe_hour_history_ids')
    def _compute_safe_hour(self):
        for rec in self:
            # --------------------- Incident Resetting Time -----------------------------
            if len(rec.incident_report_ids) > 0:
                for incident in rec.incident_report_ids:
                    if incident.is_new and not incident.death_report:
                        date_of_incident = incident.date_of_accident.date()
                        datetime_of_incident = incident.date_of_accident
                        incident_attendance = rec.env['hr.attendance'].search(
                            [('employee_id', '=', rec.id), ('start_working_date', '<=', date_of_incident)])

                        duration = 0

                        start_date = False
                        end_date = datetime_of_incident
                        i = 1
                        for attendance in incident_attendance:
                            if i == 1:
                                if len(rec.safe_hour_history_ids) > 0:
                                    if rec.safe_hour_history_ids[0].end_date:
                                        start_date = rec.safe_hour_history_ids[0].end_date
                                    else:
                                        start_date = attendance.check_in
                                else:
                                    start_date = attendance.check_in
                                i += 1
                            if attendance.check_out:
                                duration += attendance.worked_hours
                            elif not attendance.check_out:
                                if attendance.start_working_date == date.today():
                                    if datetime.now() < datetime_of_incident:
                                        diff = datetime_of_incident - attendance.check_in
                                        duration += (diff.total_seconds() / 60) / 100
                                    else:
                                        diff = datetime.now() - attendance.check_in
                                        duration += (diff.total_seconds() / 60) / 100
                                elif attendance.start_working_date != date.today():
                                    if attendance.start_working_date == date_of_incident:
                                        diff = datetime_of_incident - attendance.check_in
                                        duration += (diff.total_seconds() / 60) / 100
                                    else:
                                        diff = attendance.check_in.replace(hour=23, minute=59,
                                                                           second=59) - attendance.check_in
                                        duration += (diff.total_seconds() / 60) / 100

                        rec.compute_safe_hour = 0
                        rec.update({'safe_hour': 0})
                        incident.update({'is_new': False})

                        if len(incident_attendance) > 0:
                            rec.write({
                                'safe_hour_history_ids': [(0, 0, {'employee_id': rec.id,
                                                                  'start_date': start_date,
                                                                  'end_date': end_date,
                                                                  'duration': duration})]
                            })

            # ------------------------- Calculate Duration On Going Safe Hour ---------------------------------------

            if len(rec.safe_hour_history_ids) > 0:
                start_date = rec.safe_hour_history_ids[0].end_date.date()
                start_datetime = rec.safe_hour_history_ids[0].end_date
            duration = 0

            employee_attendance = rec.env['hr.attendance'].search([('employee_id', '=', rec.id), ('check_in', '!=', False)])
            if len(employee_attendance) > 0:
                if len(rec.incident_report_ids) > 0:
                    temp_attendance = employee_attendance.filtered(lambda x: x.start_working_date >= start_date)
                    for attendance in temp_attendance:
                        if attendance.check_out:
                            if attendance.check_in.date() == start_date:
                                duration += attendance.check_out - start_datetime
                            else:
                                duration += attendance.worked_hours
                        # don't use else for not check out, might add new logic later
                        elif not attendance.check_out:
                            if attendance.start_working_date == date.today():
                                if attendance.check_in.date() == start_date:
                                    diff = datetime.now() - start_datetime
                                    duration += (diff.total_seconds() / 60) / 100
                                else:
                                    diff = datetime.now() - attendance.check_in
                                    duration += (diff.total_seconds() / 60) / 100
                            elif attendance.start_working_date != date.today():
                                if attendance.check_in.date() == start_date:
                                    diff = attendance.check_in.replace(hour=23, minute=59, second=59) - start_datetime
                                    duration += (diff.total_seconds() / 60) / 100
                                else:
                                    diff = attendance.check_in.replace(hour=23, minute=59, second=59) - attendance.check_in
                                    duration += (diff.total_seconds() / 60) / 100
                else:
                    temp_attendance = employee_attendance
                    for attendance in temp_attendance:
                        if attendance.check_out:
                            duration += attendance.worked_hours
                        # don't use else for not check out, might add new logic later
                        elif not attendance.check_out:
                            if attendance.start_working_date == date.today():
                                diff = datetime.now() - attendance.check_in
                                duration += (diff.total_seconds() / 60) / 100
                            elif attendance.start_working_date != date.today():
                                diff = attendance.check_in.replace(hour=23, minute=59, second=59) - attendance.check_in
                                duration += (diff.total_seconds() / 60) / 100

            rec.compute_safe_hour = duration
            rec.update({'safe_hour': duration})
            # current_safe_hour.update({'duration': duration})


class SafeHourHistory(models.Model):
    _name = "safe.hour.history"
    _description = "Safe Hour History"
    _order = "id desc"

    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    no = fields.Integer(string="No", compute="_sequence_ref", store=False)
    start_date = fields.Datetime(string='Start Date', required=True)
    end_date = fields.Datetime(string='End Date')
    duration = fields.Float(string="Duration", default=0)

    def _sequence_ref(self):
        for rec in self:
            no = 0
            for line in rec.employee_id.safe_hour_history_ids:
                no += 1
                line.no = no
