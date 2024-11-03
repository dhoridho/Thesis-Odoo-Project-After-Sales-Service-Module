# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError
import logging
import tempfile
import binascii
from datetime import datetime, date, timedelta
import pytz

_logger = logging.getLogger(__name__)

try:
    import xlrd
except ImportError:
    _logger.debug('Cannot `import xlrd`.')

class HrWorkingScheduleCalendarImport(models.TransientModel):
    _name = "hr.working.schedule.calendar.import"
    _description = 'HR Working Schedule Calendar Import'

    import_file = fields.Binary(string="Import File")
    import_name = fields.Char('Import Name', size=64)

    def action_import(self):
        import_name_extension = self.import_name.split('.')[1]
        if import_name_extension not in ['xls', 'xlsx']:
            raise Warning('The upload file is using the wrong format. Please upload your file in xlsx or xls format.')

        fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        fp.write(binascii.a2b_base64(self.import_file))
        fp.seek(0)
        workbook = xlrd.open_workbook(fp.name)
        sheet = workbook.sheet_by_index(0)
        keys = sheet.row_values(0)
        xls_reader = [sheet.row_values(i) for i in range(1, sheet.nrows)]

        vals = []
        row_no = 0
        for row in xls_reader:
            line = dict(zip(keys, row))

            row_no += 1
            if line.get('Employee ID'):
                employee_obj = self.env['hr.employee'].search([('sequence_code','=',str(line.get('Employee ID')).strip()),('active','=',True)], limit=1)
                if not employee_obj:
                    raise Warning(('Employee ID "%s" at row %s not found') % (str(line.get('Employee ID')),str(row_no)))
                else:
                    employee = employee_obj
            else:
                raise Warning(('Employee ID of row %s cannot be empty') % (str(row_no)))
            
            if not employee.contract_id:
                raise Warning(('Contract of Employee ID "%s" not found') % (str(line.get('Employee ID'))))
            
            if not employee.department_id:
                raise Warning(('Department of Employee ID "%s" is empty') % (str(line.get('Employee ID'))))
            
            if line.get('Working Schedule'):
                working_schedule_obj = self.env['resource.calendar'].search([('name','=',str(line.get('Working Schedule')).strip())], limit=1)
                if not working_schedule_obj:
                    raise Warning(('Working Schedule "%s" at row %s not found') % (str(line.get('Working Schedule')),str(row_no)))
                else:
                    working_schedule = working_schedule_obj
            else:
                raise Warning(('Working Schedule of Employee ID "%s" at row %s cannot be empty') % (str(line.get('Employee ID')),str(row_no)))
            
            if line.get('Working Date'):
                res = True
                try:
                    res = bool(datetime.strptime(line.get('Working Date'), '%Y-%m-%d'))
                except ValueError:
                    res = False
                if not res:
                    raise Warning(('Working Date at row %s with Value %s does not match to any format "Y-m-d"') % (str(row_no),str(line.get('Working Date'))))
                working_date = datetime.strptime(line.get('Working Date'), '%Y-%m-%d').date()
                end_date = date(working_date.year, 12, 31)
            else:
                raise Warning(('Working Date of Employee ID "%s" at row %s cannot be empty') % (str(line.get('Employee ID')),str(row_no)))
            
            if line.get('Shift Variations Code'):
                shift_variations_obj = self.env['hr.shift.variation'].search([('shift_code','=',str(line.get('Shift Variations Code')).strip())], limit=1)
                if not shift_variations_obj:
                    raise Warning(('Shift Variations Code "%s" at row %s not found') % (str(line.get('Shift Variations Code')),str(row_no)))
                else:
                    shift_variations = shift_variations_obj
                    if shift_variations.attendance_formula_id:
                        attendance_formula = shift_variations.attendance_formula_id.id
                    else:
                        attendance_formula = False
                    hour_from = shift_variations.work_from
                    hour_to = shift_variations.work_to
                    tolerance_late = shift_variations.tolerance_for_late
                    break_from = shift_variations.break_from
                    break_to = shift_variations.break_to
                    minimum_hours = shift_variations.minimum_hours
                    day_type = shift_variations.day_type

                    start_date = working_date
                    start_time = timedelta(hours=shift_variations.work_from)
                    start_date_time = str(start_date) + ' ' + str(start_time)
                    start_tz = datetime.strptime(start_date_time, '%Y-%m-%d %H:%M:%S')
                    checkin = fields.Datetime.to_string(pytz.timezone(self.env.context.get('tz', 'utc') or 'utc').localize(fields.Datetime.from_string(start_tz),is_dst=None).astimezone(pytz.utc))

                    start_checkin_time = timedelta(hours=shift_variations.start_checkin)
                    start_date_checkin_time = str(start_date) + ' ' + str(start_checkin_time)
                    start_checkin_tz = datetime.strptime(start_date_checkin_time, '%Y-%m-%d %H:%M:%S')
                    start_checkin = fields.Datetime.to_string(pytz.timezone(self.env.context.get('tz', 'utc') or 'utc').localize(fields.Datetime.from_string(start_checkin_tz),is_dst=None).astimezone(pytz.utc))

                    if shift_variations.work_to < shift_variations.work_from:
                        date_end = start_date + timedelta(days=1)
                    else:
                        date_end = start_date

                    end_time = timedelta(hours=shift_variations.work_to)
                    end_date_time = str(date_end) + ' ' + str(end_time)
                    end_tz = datetime.strptime(end_date_time, '%Y-%m-%d %H:%M:%S')
                    checkout = fields.Datetime.to_string(pytz.timezone(self.env.context.get('tz', 'utc') or 'utc').localize(fields.Datetime.from_string(end_tz),is_dst=None).astimezone(pytz.utc))

                    end_checkout_time = timedelta(hours=shift_variations.end_checkout)
                    end_date_checkout_time = str(date_end) + ' ' + str(end_checkout_time)
                    end_checkout_tz = datetime.strptime(end_date_checkout_time, '%Y-%m-%d %H:%M:%S')
                    end_checkout = fields.Datetime.to_string(pytz.timezone(self.env.context.get('tz', 'utc') or 'utc').localize(fields.Datetime.from_string(end_checkout_tz),is_dst=None).astimezone(pytz.utc))
            else:
                raise Warning(('Shift Variations Code of Employee ID "%s" at row %s cannot be empty') % (str(line.get('Employee ID')),str(row_no)))
            
            data = {
                'employee_id': employee.id,
                'contract_id': employee.contract_id.id,
                'department_id': employee.department_id.id,
                'working_hours': working_schedule.id,
                'dayofweek': str(working_date.weekday()),
                'date_start': working_date,
                'date_end': end_date,
                'hour_from': hour_from,
                'hour_to': hour_to,
                'tolerance_late': tolerance_late,
                'break_from': break_from,
                'break_to': break_to,
                'minimum_hours': minimum_hours,
                'day_type': day_type,
                'checkin': checkin,
                'checkout': checkout,
                'start_checkin': start_checkin,
                'end_checkout': end_checkout,
                'attendance_formula_id': attendance_formula,
                'active': True,
                'is_import': True,
            }
            vals += [data]
        
        for rec in vals:
            check_employee_calendar = self.env['employee.working.schedule.calendar'].sudo().search([('employee_id','=',rec['employee_id']),('date_start','=',rec['date_start']),('active','=',True)])
            if check_employee_calendar:
                for cal in check_employee_calendar:
                    self.env.cr.execute("""DELETE FROM employee_working_schedule_calendar WHERE id = %s""" % (cal.id))
                self.env['employee.working.schedule.calendar'].sudo().create(rec)
            else:
                self.env['employee.working.schedule.calendar'].sudo().create(rec)
        return {
            'name': 'Import Employee Working Calendar',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.working.schedule.calendar.import.success',
            'view_mode': 'form',
            'view_type': 'form',
            'context': {'default_row_count': row_no},
            'target': 'new'
        }

class HrWorkingScheduleCalendarImportSuccess(models.TransientModel):
    _name = 'hr.working.schedule.calendar.import.success'
    _description = 'HR Working Schedule Calendar Import Success'

    row_count = fields.Integer("Row Count", readonly=True)
    message = fields.Text(string="Message", compute="_compute_message", readonly=True, store=True)

    @api.depends('row_count')
    def _compute_message(self):
        for rec in self:
            if rec.row_count:
                message = str(rec.row_count) + " records has been imported successfully!"
                rec.message = message