# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import ValidationError
from datetime import date, datetime
from dateutil import relativedelta as rd
from dateutil.relativedelta import relativedelta
import math
import logging
import tempfile
import binascii

_logger = logging.getLogger(__name__)

try:
    import xlrd
except ImportError:
    _logger.debug('Cannot `import xlrd`.')

class HrImportLeaveBalance(models.TransientModel):
    _name = "hr.import.leave.balance"
    _description = 'Import Leave Balance'

    import_file = fields.Binary(string="Import File", required=True)
    import_name = fields.Char('Import Name', size=64)

    def import_action(self):
        import_name_extension = self.import_name.split('.')[1]
        if import_name_extension not in ['xls', 'xlsx']:
            raise ValidationError('The upload file is using the wrong format. Please upload your file in xlsx or xls format.')
        
        fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        fp.write(binascii.a2b_base64(self.import_file))
        fp.seek(0)
        workbook = xlrd.open_workbook(fp.name)
        sheet = workbook.sheet_by_index(0)
        keys = sheet.row_values(0)
        xls_reader = [sheet.row_values(i) for i in range(1, sheet.nrows)]

        for row in xls_reader:
            line = dict(zip(keys, row))

            if line.get('Employee ID'):
                employee_id_type = type(line.get('Employee ID'))
                if employee_id_type == float:
                    employee_id = str(int(line.get('Employee ID')))
                else:
                    employee_id = str(line.get('Employee ID'))
                employee_obj = self.env['hr.employee'].search([('sequence_code','=',employee_id),('active','=',True)], limit=1)
                if not employee_obj:
                    raise ValidationError(('Employee ID %s not found') % (employee_id))
                else:
                    employee = employee_obj
            else:
                raise ValidationError(('Employee ID of %s cannot be empty') % (str(line.get('Employee'))))

            if line.get('Leave Type'):
                leave_type_obj = self.env['hr.leave.type'].search([('name','=',str(line.get('Leave Type')))], limit=1)
                if not leave_type_obj:
                    raise ValidationError(('Leave Type %s not found') % (str(line.get('Leave Type'))))
                else:
                    leave_type = leave_type_obj
            else:
                raise ValidationError(('Leave Type of %s cannot be empty') % (str(line.get('Employee'))))
            
            if leave_type.leave_method != 'anniversary':
                if line.get('Start Valid Date'):
                    start_valid_date_vals = xlrd.xldate_as_tuple(line.get('Start Valid Date'), workbook.datemode)
                    start_valid_date = str(start_valid_date_vals[0])+'-'+str(start_valid_date_vals[1])+'-'+str(start_valid_date_vals[2])
                else:
                    raise ValidationError(('Start Valid Date of %s cannot be empty') % (str(line.get('Employee'))))
            
            if line.get('Current Period'):
                current_period_vals = str(int(line.get('Current Period')))
                current_period = current_period_vals.strip()
            else:
                raise ValidationError(('Current Period of %s cannot be empty') % (str(line.get('Employee'))))
            
            hr_years_obj = self.env['hr.years'].sudo().search([('name','=',current_period),('status', '=', 'open')], limit=1)
            if hr_years_obj:
                hr_years = hr_years_obj
            else:
                raise ValidationError(('HR Years %s not found') % (str(current_period)))
            
            if line.get('Assigned'):
                assigned = float(line.get('Assigned'))
            else:
                assigned = 0.0
            
            carry_forward = False
            if leave_type.leave_method == 'annually':
                valid_to_date = date(hr_years.name, 12, 31)
                self.env.cr.execute(
                    """SELECT id, employee_id FROM hr_leave_balance where employee_id = %d and holiday_status_id 
                    = %d and hr_years = %d and active = 'true' ORDER BY id DESC LIMIT 1""" % (
                        employee.id, leave_type.id, hr_years.name))
                leave_balance_active = self.env.cr.dictfetchall()
                
                if leave_type.carry_forward in ['remaining_amount','specific_days']:
                    is_limit_period = leave_type.is_limit_period
                    limit_period = leave_type.limit_period
                    carry_forward = leave_type.carry_forward
                else:
                    is_limit_period = False
                    limit_period = int(0)
                
                leave_balance_id = False
                if not leave_balance_active:
                    if not leave_type.gender or leave_type.gender == employee.gender:
                        leave_balance_id = self.env['hr.leave.balance'].create({
                            'employee_id': employee.id,
                            'holiday_status_id': leave_type.id,
                            'leave_entitlement': leave_type.leave_entitlement,
                            'assigned': assigned,
                            'hr_years': hr_years.name,
                            'current_period': current_period,
                            'start_date': start_valid_date,
                            'is_limit_period': is_limit_period,
                            'limit_period': limit_period,
                            'hr_years_id': hr_years.id,
                            'carry_forward': carry_forward,
                        })
                elif leave_balance_active and leave_type.repeated_allocation == True:
                    leave_balance = self.env['hr.leave.balance'].browse(leave_balance_active[0].get('id'))
                    if not leave_type.gender or leave_type.gender == employee.gender:
                        assign = leave_balance.assigned + assigned
                        leave_balance.write({'assigned': assign,'limit_period': limit_period,'is_limit_period': is_limit_period})
                        leave_balance_id = leave_balance
                
                if leave_balance_id:
                    leave_balance_id = leave_balance_id.id
                else:
                    leave_balance_id = False
                    
                self.env.cr.execute(
                    """SELECT employee_id FROM hr_leave_count where employee_id = %d and holiday_status_id 
                    = %d and hr_years = %d and active = 'true'""" % (
                        employee.id, leave_type.id, hr_years.name))
                hr_leave_count = self.env.cr.fetchall()
                if not hr_leave_count:
                    if not leave_type.gender or leave_type.gender == employee.gender:
                        self.env['hr.leave.count'].create({
                            'employee_id': employee.id,
                            'holiday_status_id': leave_type.id,
                            'count': assigned,
                            'start_date': start_valid_date,
                            'expired_date': valid_to_date,
                            'hr_years': hr_years.name,
                            'leave_balance_id': leave_balance_id,
                            'description': 'Allocation',
                        })
                elif hr_leave_count and leave_type.repeated_allocation == True:
                    if not leave_type.gender or leave_type.gender == line.gender:
                        self.env['hr.leave.count'].create({
                            'employee_id': employee.id,
                            'holiday_status_id': leave_type.id,
                            'count': assigned,
                            'start_date': start_valid_date,
                            'expired_date': valid_to_date,
                            'hr_years': hr_years.name,
                            'leave_balance_id': leave_balance_id,
                            'description': 'Allocation',
                        })
            elif leave_type.leave_method == 'anniversary':
                start_date = employee.date_of_joining
                var = int(hr_years.name) - 1
                to_date = date(var, 12, 31)
                diff = rd.relativedelta(to_date, start_date)
                months = diff.months + (12 * diff.years) + 1
                valid_month = int(start_date.strftime("%m"))
                valid_date = int(start_date.strftime("%d"))
                valid_start_date = date(hr_years.name, valid_month, valid_date)
                valid_to_year = valid_start_date + relativedelta(years=1)
                valid_to_date = valid_to_year + relativedelta(days=-1)

                self.env.cr.execute(
                    """SELECT id, employee_id FROM hr_leave_balance where employee_id = %d and holiday_status_id 
                    = %d and hr_years = %d and active = 'true' ORDER BY id DESC LIMIT 1""" % (
                        employee.id, leave_type.id, hr_years.name))
                leave_balance_active = self.env.cr.dictfetchall()
                
                if leave_type.carry_forward in ['remaining_amount','specific_days']:
                    is_limit_period = leave_type.is_limit_period
                    limit_period = leave_type.limit_period
                    carry_forward = leave_type.carry_forward
                else:
                    is_limit_period = False
                    limit_period = int(0)
                
                leave_balance_id = False
                if not leave_balance_active:
                    if not leave_type.gender or leave_type.gender == employee.gender:
                        leave_balance_id = self.env['hr.leave.balance'].create({
                            'employee_id': employee.id,
                            'holiday_status_id': leave_type.id,
                            'leave_entitlement': leave_type.leave_entitlement,
                            'assigned': assigned,
                            'hr_years': hr_years.name,
                            'current_period': current_period,
                            'start_date': valid_start_date,
                            'is_limit_period': is_limit_period,
                            'limit_period': limit_period,
                            'hr_years_id': hr_years.id,
                            'carry_forward': carry_forward,
                        })
                elif leave_balance_active and leave_type.repeated_allocation == True:
                    leave_balance = self.env['hr.leave.balance'].browse(leave_balance_active[0].get('id'))
                    if not leave_type.gender or leave_type.gender == employee.gender:
                        assign = leave_balance.assigned + assigned
                        leave_balance.write({'assigned': assign,'limit_period': limit_period,'is_limit_period': is_limit_period})
                        leave_balance_id = leave_balance
                
                if leave_balance_id:
                    leave_balance_id = leave_balance_id.id
                else:
                    leave_balance_id = False

                self.env.cr.execute(
                    """SELECT employee_id FROM hr_leave_count where employee_id = %d and holiday_status_id 
                    = %d and hr_years = %d and active = 'true'""" % (
                        employee.id, leave_type.id, hr_years.name))
                hr_leave_count = self.env.cr.fetchall()
                if not hr_leave_count:
                    if not leave_type.gender or leave_type.gender == employee.gender:
                        self.env['hr.leave.count'].create({
                            'employee_id': employee.id,
                            'holiday_status_id': leave_type.id,
                            'count': assigned,
                            'start_date': valid_start_date,
                            'expired_date': valid_to_date,
                            'hr_years': hr_years.name,
                            'leave_balance_id': leave_balance_id,
                            'description': 'Allocation',
                        })
                elif hr_leave_count and leave_type.repeated_allocation == True:
                    if not leave_type.gender or leave_type.gender == line.gender:
                        self.env['hr.leave.count'].create({
                            'employee_id': employee.id,
                            'holiday_status_id': leave_type.id,
                            'count': assigned,
                            'start_date': valid_start_date,
                            'expired_date': valid_to_date,
                            'hr_years': hr_years.name,
                            'leave_balance_id': leave_balance_id,
                            'description': 'Allocation',
                        })
            elif leave_type.leave_method == 'monthly':
                start_date = datetime.strptime(start_valid_date, '%Y-%m-%d').date()
                current_year = hr_years.name
                current_day = date.today()
                valid_month = int(start_date.strftime("%m"))
                valid_date = int(start_date.strftime("%d"))
                valid_start_date = date(hr_years.name, valid_month, valid_date)
                valid_monthly_start_date = valid_start_date + relativedelta(months=1)
                
                monthly_assigned = 0
                while valid_monthly_start_date < current_day:
                    if monthly_assigned < leave_type.maximum_leave:
                        monthly_assigned += leave_type.leave_entitlement
                    valid_monthly_start_date += relativedelta(months=1)
                
                self.env.cr.execute(
                    """SELECT id, employee_id FROM hr_leave_balance where employee_id = %d and holiday_status_id 
                    = %d and hr_years_monthly = %d and active = 'true' ORDER BY id DESC LIMIT 1""" % (
                        employee.id, leave_type.id, current_year))
                leave_balance_active = self.env.cr.dictfetchall()
                if leave_type.carry_forward in ['remaining_amount','specific_days']:
                    is_limit_period = leave_type.is_limit_period
                    limit_period = leave_type.limit_period
                    carry_forward = leave_type.carry_forward
                else:
                    is_limit_period = False
                    limit_period = int(0)
                
                leave_balance_id = False
                if not leave_balance_active:
                    if not leave_type.gender or leave_type.gender == employee.gender:
                        leave_balance_id = self.env['hr.leave.balance'].create({
                            'employee_id': employee.id,
                            'holiday_status_id': leave_type.id,
                            'leave_entitlement': leave_type.leave_entitlement,
                            'assigned': monthly_assigned,
                            'hr_years': hr_years.name,
                            'hr_years_monthly': hr_years.name,
                            'current_period': hr_years.name,
                            'start_date': valid_start_date,
                            'is_limit_period': is_limit_period,
                            'limit_period': limit_period,
                            'hr_years_id': hr_years.id,
                            'carry_forward': carry_forward,
                        })
                elif leave_balance_active and leave_type.repeated_allocation == True:
                    leave_balance = self.env['hr.leave.balance'].browse(leave_balance_active[0].get('id'))
                    if not leave_type.gender or leave_type.gender == line.gender:
                        assign = leave_balance.assigned + leave_type.maximum_leave
                        leave_balance.write({'assigned': assign,'limit_period': limit_period,'is_limit_period': is_limit_period})
                        leave_balance_id = leave_balance
                
                if leave_balance_id:
                    leave_balance_id = leave_balance_id.id
                else:
                    leave_balance_id = False

                start_list = []
                to_count_date = 0
                if leave_type.maximum_leave and leave_type.leave_entitlement:
                    to_count_date = math.ceil(leave_type.maximum_leave / leave_type.leave_entitlement)
                if current_year == start_date.year:
                    monthly_start_date = start_date
                    monthly_to_date = monthly_start_date + relativedelta(months=to_count_date)
                    while monthly_start_date < monthly_to_date:
                        monthly_start_date += relativedelta(months=1)
                        if monthly_start_date < current_day:
                            start_list.append(monthly_start_date)
                else:
                    valid_date = int(start_date.strftime("%d"))
                    monthly_start_date = date(current_year, 1, valid_date)
                    monthly_to_date = monthly_start_date + relativedelta(months=to_count_date)
                    while monthly_start_date < monthly_to_date and monthly_start_date < current_day:
                        start_list.append(monthly_start_date)
                        monthly_start_date += relativedelta(months=1)
                
                to_date = ''
                value = 0
                final_value = leave_type.leave_entitlement
                for count_start_date in start_list:
                    if leave_type.valid_leave == 'one_year':
                        monthly_to_date = count_start_date + relativedelta(years=1)
                        to_date = monthly_to_date - relativedelta(days=1)
                    elif leave_type.valid_leave == 'end_year':
                        to_date = date(current_year, 12, 31)
                    current_count_month = count_start_date.month
                    self.env.cr.execute(
                        """SELECT employee_id FROM hr_leave_count where employee_id = %d and holiday_status_id 
                        = %d and hr_months = %d and hr_years_monthly = %d and active = 'true'""" % (
                            employee.id, leave_type.id, current_count_month, current_year))
                    hr_leave_count = self.env.cr.fetchall()
                    value += leave_type.leave_entitlement
                    if value > leave_type.maximum_leave:
                        last_before = value - leave_type.leave_entitlement
                        final_value = leave_type.maximum_leave - last_before
                    if not hr_leave_count:
                        if not leave_type.gender or leave_type.gender == employee.gender:
                            self.env['hr.leave.count'].create({
                                'employee_id': employee.id,
                                'holiday_status_id': leave_type.id,
                                'count': final_value,
                                'hr_years': hr_years.name,
                                'hr_months': current_count_month,
                                'hr_years_monthly': hr_years.name,
                                'start_date': count_start_date,
                                'expired_date': to_date,
                                'leave_balance_id': leave_balance_id,
                                'description': 'Allocation',
                            })
                    elif hr_leave_count and leave_type.repeated_allocation == True:
                        if not leave_type.gender or leave_type.gender == employee.gender:
                            self.env['hr.leave.count'].create({
                                'employee_id': employee.id,
                                'holiday_status_id': leave_type.id,
                                'count': final_value,
                                'hr_years': hr_years.name,
                                'hr_months': current_count_month,
                                'hr_years_monthly': hr_years.name,
                                'start_date': count_start_date,
                                'expired_date': to_date,
                                'leave_balance_id': leave_balance_id,
                                'description': 'Allocation',
                            })
                        
            elif leave_type.leave_method == 'none':
                current_date = fields.Date.today()
                start_valid_count = fields.Date.from_string(start_valid_date)
                if leave_type.allocation_valid_until == "number_of_days":
                    valid_to = start_valid_count + relativedelta(days=leave_type.expiry_days)
                    while valid_to < current_date:
                        start_valid_count = valid_to + relativedelta(days=1)
                        valid_to = start_valid_count + relativedelta(days=leave_type.expiry_days)
                    date_end_year = date(current_date.year, 12, 31)
                    if valid_to <= date_end_year:
                        valid_to_date = valid_to
                    else:
                        valid_to_date = date_end_year
                elif leave_type.allocation_valid_until == "spesific_days":
                    valid_specific_month = int(leave_type.allocation_months_expired)
                    valid_specific_date = int(leave_type.allocation_date_expired)
                    next_year = current_date.year + 1
                    valid_to_date = date(next_year, valid_specific_month, valid_specific_date)
                elif leave_type.allocation_valid_until == "end_of_year":
                    valid_to_date = date(current_date.year, 12, 31)
                self.env.cr.execute(
                    """SELECT id, employee_id FROM hr_leave_balance where employee_id = %d and holiday_status_id 
                    = %d and hr_years = %d and active = 'true' ORDER BY id DESC LIMIT 1""" % (
                        employee.id, leave_type.id, hr_years.name))
                leave_balance_active = self.env.cr.dictfetchall()
                
                if leave_type.carry_forward in ['remaining_amount','specific_days']:
                    is_limit_period = leave_type.is_limit_period
                    limit_period = leave_type.limit_period
                    carry_forward = leave_type.carry_forward
                else:
                    is_limit_period = False
                    limit_period = int(0)
                
                leave_balance_id = False
                if not leave_balance_active:
                    if not leave_type.gender or leave_type.gender == employee.gender:
                        leave_balance_id = self.env['hr.leave.balance'].create({
                            'employee_id': employee.id,
                            'holiday_status_id': leave_type.id,
                            'leave_entitlement': leave_type.leave_entitlement,
                            'assigned': assigned,
                            'hr_years': hr_years.name,
                            'current_period': current_period,
                            'start_date': start_valid_date,
                            'is_limit_period': is_limit_period,
                            'limit_period': limit_period,
                            'hr_years_id': hr_years.id,
                            'carry_forward': carry_forward,
                        })
                elif leave_balance_active and leave_type.repeated_allocation == True:
                    leave_balance = self.env['hr.leave.balance'].browse(leave_balance_active[0].get('id'))
                    if not leave_type.gender or leave_type.gender == employee.gender:
                        assign = leave_balance.assigned + assigned
                        leave_balance.write({'assigned': assign,'limit_period': limit_period,'is_limit_period': is_limit_period})
                        leave_balance_id = leave_balance
                
                if leave_balance_id:
                    leave_balance_id = leave_balance_id.id
                else:
                    leave_balance_id = False

                self.env.cr.execute(
                    """SELECT employee_id FROM hr_leave_count where employee_id = %d and holiday_status_id 
                    = %d and hr_years = %d and active = 'true'""" % (
                        employee.id, leave_type.id, hr_years.name))
                hr_leave_count = self.env.cr.fetchall()
                if not hr_leave_count:
                    if not leave_type.gender or leave_type.gender == employee.gender:
                        self.env['hr.leave.count'].create({
                            'employee_id': employee.id,
                            'holiday_status_id': leave_type.id,
                            'count': assigned,
                            'start_date': start_valid_count,
                            'expired_date': valid_to_date,
                            'hr_years': hr_years.name,
                            'leave_balance_id': leave_balance_id,
                            'description': 'Allocation',
                        })
                elif hr_leave_count and leave_type.repeated_allocation == True:
                    if not leave_type.gender or leave_type.gender == line.gender:
                        self.env['hr.leave.count'].create({
                            'employee_id': employee.id,
                            'holiday_status_id': leave_type.id,
                            'count': assigned,
                            'start_date': start_valid_count,
                            'expired_date': valid_to_date,
                            'hr_years': hr_years.name,
                            'leave_balance_id': leave_balance_id,
                            'description': 'Allocation',
                        })
        return {
                'name': _('Leave Balance'),
                'domain': [],
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'hr.leave.balance',
                'view_id': False,
                'views': [(self.env.ref('equip3_hr_holidays_extend.view_my_leave_balance_tree').id, 'tree'),(self.env.ref('equip3_hr_holidays_extend.view_my_leave_balance_form').id, 'form')],
                'type': 'ir.actions.act_window'
               }