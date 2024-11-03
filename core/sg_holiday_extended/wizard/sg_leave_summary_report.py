import base64
import io
import xlwt
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT,\
    DEFAULT_SERVER_DATE_FORMAT


class SgLeaveExportSummary(models.TransientModel):
    _name = "excel.sg.leave.summary.report"
    _description = "Sg Leave Export Summary"

    file = fields.Binary("Click On Download Link To Download Xls File",
                         readonly=True)
    name = fields.Char("Name", default='generic summary.xls')


class SgLeaveSummaryWizard(models.TransientModel):
    _name = 'sg.leave.summary.report.wizard'
    _description = "Sg Leave Summary Wizard"

    def _curr_employee(self):
        uid = self.env.uid
        context = self.env.context
        emp_id = context.get('default_employee_id', False)
        if emp_id:
            return emp_id
        ids = self.env['hr.employee'].search([('user_id', '=', uid)])
        if ids:
            return ids[0]
        return False

    to_date = fields.Date('Date To')
    from_date = fields.Date('Date From')
    leave_type_id = fields.Many2one('hr.leave.type', 'Leave Type')
    employee_id = fields.Many2one('hr.employee', 'Name of Employee',
                                  default=_curr_employee)
    all_employee = fields.Boolean("All Employee")
    all_leave = fields.Boolean("All Leave")

    @api.onchange('all_employee')
    def onchange_all_employee(self):
        """Onchange Employee."""
        vals = {}
        if self.all_employee is True:
            vals.update({'employee_id': False})
        return {'value': vals}

    @api.onchange('employee_id')
    def onchange_sg_employee(self):
        """Onchange sg employee.

        When you change employee, this method will change
        value of leave types accordingly.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user ID for security checks,
        @param ids: List of IDs
        @param context: A standard dictionary for contextual values
        @return: Dictionary of values.
        """
        result = {}
        result.update({'value': {'leave_type_id': False}})
        employee = self.employee_id
        if employee:
            if employee.leave_config_id and \
                employee.leave_config_id.holiday_group_config_line_ids:
                emp_leave_ids = [leave_type.leave_type_id.id for leave_type in employee.leave_config_id.holiday_group_config_line_ids if leave_type.leave_type_id]
                result.update({'domain': {'leave_type_id': [('id', 'in', emp_leave_ids)]}})
        else:
            all_leave_ids = self.env['hr.leave.type'].search([])
            result.update({'domain': {'leave_type_id':
                                      [('id', 'in', all_leave_ids.ids)]}})
        return result

    def _get_employee_header(self, worksheet, row, table_border):
        """Get employee header.

        this method display employee info header
        """
        worksheet.write(row + 2, 0, 'Department', table_border)
        worksheet.write(row + 2, 1, 'Employee ID', table_border)
        worksheet.write(row + 2, 2, 'Employee Name', table_border)
        worksheet.write(row + 2, 3, 'Date Joined', table_border)
        worksheet.write(row + 2, 4, 'Service Year', table_border)
        worksheet.write(row + 2, 5, 'Leave Structure', table_border)
        worksheet.write(row + 2, 6, 'Carry Forward Leave', table_border)
        worksheet.write(row + 2, 7, 'Current Year Entitlement', table_border)
        worksheet.write(row + 2, 8, 'Pending', table_border)
        worksheet.write(row + 2, 9, 'Taken', table_border)
        worksheet.write(row + 2, 10, 'Balance YTD', table_border)
        worksheet.write(row + 2, 11, 'Balance MTD', table_border)

    def _get_company_info(self, worksheet, row, header2):
        """Get company information.

        This method display company info
        """
        uid = self._uid
        ids = self.env['hr.employee'].search([('user_id', '=', uid)])
        today = datetime.now()
        today_date = str(today.strftime('%d')) + '-' + \
            str(today.strftime('%m')) + '-' + str(today.strftime('%Y'))
        worksheet.write(row + 0, 0, 'Title', header2)
        worksheet.write(row + 0, 1, 'Leave Balance Report', header2)
        worksheet.write(row + 1, 0, 'Company Name', header2)
        worksheet.write_merge(3, 3, 1, 3, ids.company_id.name, header2)
        worksheet.write(row + 2, 0, 'Date', header2)
        worksheet.write(row + 2, 1, today_date, header2)

    def _get_pending_leave(self, emp_id, leave_id, from_date_str, from_to_str):
        cr = self._cr
        cr.execute("""
            SELECT sum(number_of_days) FROM hr_leave where
            employee_id=%d and holiday_status_id = %d
            and state='confirm' and date_from >= '%s'
            and date_to <= '%s' """ % (emp_id, leave_id, from_date_str,
                                       from_to_str))
        pending_leave = cr.fetchone()
        return pending_leave

    def _get_taken_leave(self, emp_id, leave_id, from_date_str, from_to_str):
        cr = self._cr
        cr.execute("""
            SELECT sum(number_of_days) FROM hr_leave where
            employee_id=%d and holiday_status_id = %d
            and state='validate' and date_from >= '%s' and
            date_to <= '%s' """ % (emp_id, leave_id, from_date_str,
                                   from_to_str))
        taken_leave = cr.fetchone()
        return taken_leave

    def _get_total_leave(self, emp_id, leave_id, fiscalyear_id):
        cr = self._cr
        cr.execute("""
            SELECT sum(number_of_days) FROM hr_leave_allocation where
            employee_id=%d and holiday_status_id = %d and state='validate'
            and hr_year_id =%d""" % (emp_id, leave_id, fiscalyear_id))
        total_leave = cr.fetchone()
        if total_leave:
            total_leave = total_leave[0] if total_leave[0] is not None else 0
        else:
            total_leave = 0
        return total_leave

    def _get_carry_leave(self, emp_id, leave_id, fiscalyear_id):
        cr = self._cr
        cr.execute("""
                SELECT sum(number_of_days) FROM hr_leave_allocation where
                employee_id=%d and holiday_status_id = %d
                and state='validate' and hr_year_id =%d""" % (emp_id, leave_id,
                                                              fiscalyear_id))
        carry_leave = cr.fetchone()
        return carry_leave

    def _get_earn_leave(self, emp_id, leave_id, from_date_str, from_to_str,
                        fiscalyear_id):
        earn_leaves = 0
        holiday_obj = self.env['holiday.group.config.line']
        for holiday_earn_record in holiday_obj.search([
                    ('leave_type_id', '=', leave_id),
                    ('holiday_group_config_id', '=', emp_id.leave_config_id.id)
                                    ]):
            # commented the line as there is no code to check the boolean earned_leave
            # if holiday_earn_record.earned_leave is True:
            date_from1 = from_date_str
            date_to1 = from_to_str
            default_allocation = (
                holiday_earn_record.default_leave_allocation)
            working_months = relativedelta(date_to1, date_from1)
            total_month = 1
            if working_months and working_months.months:
                total_month = working_months.months
            if default_allocation:
                default_leave = (
                    float(default_allocation) / 12) * total_month
                earn_leaves = round(default_leave)
        return earn_leaves

    def print_sg_leave_summary_report_wizard(self):
        context = dict(self._context) or {}
        data = self.read()[0]
        if 'all_employee' or 'all_leave'in data:
            context.update({'all_employee': data['all_employee'],
                            'all_leave': data['all_leave']})
        context.update({
            'from_date': data['from_date'],
            'to_date': data['to_date'],
            'leave_type_id': data['leave_type_id'],
            'employee_id': data['employee_id']
        })
        if context.get('from_date') >= context.get('to_date'):
            raise ValidationError(_(
                "You must enter Date from less than Date To !"))
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Sheet 1')
        borders = xlwt.Borders()
        font = xlwt.Font()
        font.bold = True
        table_border = xlwt.easyxf('font: bold 1, height 200; align: wrap on;')
        table_border1 = xlwt.easyxf('font: height 200; align: wrap on;')
        table_border_center = xlwt.easyxf("font: bold 0; align: wrap on, \
        horiz centre;")
        table_border1_center = xlwt.easyxf("align: wrap on, horiz centre;")
        borders.top = xlwt.Borders.MEDIUM
        borders.bottom = xlwt.Borders.MEDIUM
        borders.left = xlwt.Borders.MEDIUM
        borders.right = xlwt.Borders.MEDIUM
        table_border.borders = borders
        table_border1.borders = borders
        table_border_center.borders = borders
        table_border1_center.borders = borders
        header2 = xlwt.easyxf('font: bold 1, height 200', 'align: left')
        header3 = xlwt.easyxf('font: bold 1 , height 250', 'align: left')
        header1 = xlwt.easyxf("align: wrap on;")
        borders.top = xlwt.Borders.MEDIUM
        borders.bottom = xlwt.Borders.MEDIUM
        borders.left = xlwt.Borders.MEDIUM
        borders.right = xlwt.Borders.MEDIUM
        header1.borders = borders

        worksheet.col(0).width = 7000
        worksheet.col(1).width = 7000
        worksheet.col(2).width = 7000
        worksheet.col(3).width = 7000
        worksheet.col(4).width = 7000
        worksheet.col(5).width = 6000
        worksheet.col(6).width = 6000
        worksheet.col(7).width = 6000
        worksheet.col(8).width = 6000
        worksheet.col(9).width = 7000
        worksheet.row(0).height = 600
        worksheet.row(1).height = 300
        worksheet.row(2).height = 400
        worksheet.row(3).height = 300
        worksheet.row(4).height = 300
        worksheet.row(5).height = 400
        worksheet.row(6).height = 300
        worksheet.row(7).height = 300
        worksheet.row(8).height = 400
        worksheet.row(9).height = 300

        if not context["employee_id"]:
            employee_res = self.env['hr.employee'].search([])
        leave_obj = self.env['hr.leave.type']
        if context['all_leave'] is True:
            leave_ids = leave_obj.search([])

        args = [('date_start', '<=', context.get('from_date')),
                ('date_stop', '>=', context.get('to_date'))]
        fiscalyear_id = self.env['hr.year'].search(args)
        if fiscalyear_id:
            fiscalyear_id = fiscalyear_id[0]
        else:
            raise ValidationError(_('You can search only single year records'))

        from_date_date = datetime.strptime(context["from_date"].strftime(
            DEFAULT_SERVER_DATETIME_FORMAT),
            DEFAULT_SERVER_DATETIME_FORMAT)
        from_date_str = from_date_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        from_to_date = (datetime.strptime(context["to_date"].strftime(
            DEFAULT_SERVER_DATETIME_FORMAT), DEFAULT_SERVER_DATETIME_FORMAT
        ) - relativedelta(hours=8))
        from_to_str = from_to_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

#       WHEN BOTH CHECKBOX IS TRUE
        if context['all_employee'] is True and context['all_leave'] is True:
            row = 2
            col = 0
            self._get_company_info(worksheet, row, header2)
            row = row + 4
            worksheet.row(row + 4).height = 300
            leave_name = ''
            leave_ids = leave_obj.search([])
            for leave in leave_ids:
                row = row + 1
                worksheet.row(row).height = 300
                worksheet.row(row + 2).height = 600
                leave_name = leave.name2 if leave.name2 else leave.name
                worksheet.write_merge(row, row, col, 2, leave_name, header3)
                self._get_employee_header(worksheet, row, table_border)
                row = row + 3
                col = 0
                for emp_record in employee_res:
                    emp_record = emp_record
                    emp_id = emp_record.id
                    leave_id = leave.id
#                   DEPARTMENT
                    if emp_record.department_id and \
                            emp_record.department_id.name:
                        worksheet.write(row, col + 0,
                                        emp_record.department_id.name,
                                        table_border1)
                    else:
                        worksheet.write(row, col + 0, '', table_border1)
#                   IDENTIFICATION NUMBER
                    if emp_record.identification_id:
                        worksheet.write(row, col + 1,
                                        emp_record.identification_id,
                                        table_border1)
                    else:
                        worksheet.write(row, col + 1, '', table_border1)
#                   EMPLOYEE NAME
                    if emp_record.name:
                        worksheet.write(row, col + 2, emp_record.name,
                                        table_border1)
                    else:
                        worksheet.write(row, col + 2, '', table_border1)
#                   DATE JOINED
                    if emp_record.join_date:
                        emp_join_dt = emp_record.join_date.strftime('%d') +\
                            '-' + emp_record.join_date.strftime('%m') + '-' + \
                            emp_record.join_date.strftime('%Y')
                        worksheet.write(row, col + 3, emp_join_dt,
                                        table_border1)
                    else:
                        worksheet.write(row, col + 3, '', table_border1)
#                   SERVICE YEARS
                    if emp_record.joined_year:
                        worksheet.write(row, col + 4, emp_record.joined_year,
                                        table_border1)
                    else:
                        worksheet.write(row, col + 4, '', table_border1)
#                   LEAVE STRUCTURE
                    if emp_record.leave_config_id and \
                            emp_record.leave_config_id.name:
                        worksheet.write(row, col + 5,
                                        emp_record.leave_config_id.name,
                                        table_border1)
                    else:
                        worksheet.write(row, col + 5, '', table_border1)
#                   CARRY FORWARD
                    carry_leave = self._get_carry_leave(emp_id, leave_id,
                                                        fiscalyear_id)
                    if carry_leave and carry_leave[0] and\
                            carry_leave[0] is not None:
                        worksheet.write(row, col + 6, int(carry_leave[0]),
                                        table_border1_center)
                    else:
                        worksheet.write(row, col + 6, 0, table_border1_center)
#                   CURRENT YEAR
                    total_leave = self._get_total_leave(emp_id, leave_id,
                                                        fiscalyear_id)
                    if total_leave != 0:
                        worksheet.write(row, col + 7, int(total_leave),
                                        table_border1_center)
                    else:
                        worksheet.write(row, col + 7, 0, table_border1_center)
#                   PENDING
                    pending_leave = self._get_pending_leave(emp_id, leave_id,
                                                            from_date_str,
                                                            from_to_str)
                    if pending_leave and pending_leave[0] and \
                            pending_leave[0] is not None:
                        worksheet.write(row, col + 8, pending_leave[0],
                                        table_border1_center)
                    else:
                        worksheet.write(row, col + 8, 0, table_border1_center)
#                   TAKEN
                    taken_leave = self._get_taken_leave(
                        emp_id, leave_id, from_date_str, from_to_str)
                    if taken_leave and taken_leave[0] and \
                            taken_leave[0] is not None:
                        worksheet.write(row, col + 9, taken_leave[0],
                                        table_border1_center)
                    else:
                        worksheet.write(row, col + 9, 0, table_border1_center)
#                   BALANCE YTD
                    if total_leave != 0:
                        if taken_leave and taken_leave[0] and \
                                taken_leave[0] is not None:
                            after_blc = int(total_leave) - taken_leave[0]
                            worksheet.write(row, col + 10, after_blc or 0,
                                            table_border1_center)
                        else:
                            worksheet.write(row, col + 10, total_leave,
                                            table_border1_center)
                    else:
                        worksheet.write(row, col + 10, 0, table_border1_center)
#                   BALANCE MTD
                    earn_leaves = self._get_earn_leave(emp_record, leave_id,
                        context["from_date"], context["to_date"], fiscalyear_id)
                    if earn_leaves != 0:
                        if taken_leave and taken_leave[0] and \
                                taken_leave[0] is not None:
                            earn_leaves = earn_leaves - taken_leave[0]
                            worksheet.write(row, col + 11, earn_leaves,
                                            table_border1_center)
                        else:
                            worksheet.write(row, col + 11, earn_leaves,
                                            table_border1_center)
                    else:
                        worksheet.write(row, col + 11, 0, table_border1_center)
                    row = row + 1
            row = row + 1

#       WHEN EMPLOYEE CHECKBOX TRUE
        elif context['all_employee'] is True and context['all_leave'] is False:
            row = 2
            col = 0
            self._get_company_info(worksheet, row, header2)
            row = row + 4
            leave_type = str(context["leave_type_id"][1]).upper() + \
                ' LEAVE RECORD'
            worksheet.row(row).height = 400
            worksheet.write_merge(row, row, col, 2, leave_type, header3)
            worksheet.row(row + 2).height = 500
            self._get_employee_header(worksheet, row, table_border)
            row = row + 3
            col = 0
            for emp_record in employee_res:
                emp_id = emp_record.id
                leave_id = context["leave_type_id"][0]
                pending_leave = self._get_pending_leave(
                    emp_id, leave_id, from_date_str, from_to_str)
                taken_leave = self._get_taken_leave(
                    emp_id, leave_id, from_date_str, from_to_str)
                total_leave = self._get_total_leave(
                    emp_id, leave_id, fiscalyear_id)
                carry_leave = self._get_carry_leave(
                    emp_id, leave_id, fiscalyear_id)
                earn_leaves = self._get_earn_leave(emp_record, leave_id,
                    context["from_date"], context["to_date"], fiscalyear_id)
#               DEPARTMENT
                if emp_record.department_id and emp_record.department_id.name:
                    worksheet.write(row, col + 0,
                                    emp_record.department_id.name,
                                    table_border1)
                else:
                    worksheet.write(row, col + 0, '', table_border1)
#               IDENTIFICATION NUMBER
                if emp_record.identification_id:
                    worksheet.write(row, col + 1, emp_record.identification_id,
                                    table_border1)
                else:
                    worksheet.write(row, col + 1, '', table_border1)
#               EMPLOYEE NAME
                if emp_record.name:
                    worksheet.write(row, col + 2, emp_record.name,
                                    table_border1)
                else:
                    worksheet.write(row, col + 2, emp_record.name,
                                    table_border1)
#               JOIN DATE
                if emp_record.join_date:
                    emp_j_date = emp_record.join_date
                    emp_join_dt = str(emp_j_date.strftime('%d')) + '-' + \
                        str(emp_j_date.strftime('%m')) + '-' + \
                        str(emp_j_date.strftime('%Y'))
                    worksheet.write(row, col + 3, emp_join_dt, table_border1)
                else:
                    worksheet.write(row, col + 3, '', table_border1)
#               SERVICE YEARS
                if emp_record.joined_year:
                    worksheet.write(row, col + 4, emp_record.joined_year,
                                    table_border1)
                else:
                    worksheet.write(row, col + 4, '', table_border1)
#               LEAVE STRUCTURE
                if emp_record.leave_config_id and \
                        emp_record.leave_config_id.name:
                    worksheet.write(row, col + 5,
                                    emp_record.leave_config_id.name,
                                    table_border1)
                else:
                    worksheet.write(row, col + 5, '', table_border1)
#               CARRY FORWARD
                if carry_leave and carry_leave[0] and carry_leave[0] is not\
                        None:
                    worksheet.write(row, col + 6, int(carry_leave[0]),
                                    table_border1_center)
                else:
                    worksheet.write(row, col + 6, 0, table_border1_center)
#               CURRENT YEAR TOTAL LEAVE
                if total_leave != 0:
                    worksheet.write(row, col + 7, int(total_leave),
                                    table_border1_center)
                else:
                    worksheet.write(row, col + 7, 0, table_border1_center)
#               PENDING
                if pending_leave and pending_leave[0] and \
                        pending_leave[0] is not None:
                    worksheet.write(row, col + 8, pending_leave[0],
                                    table_border1_center)
                else:
                    worksheet.write(row, col + 8, 0, table_border1_center)
#               TAKEN
                if taken_leave and taken_leave[0] and taken_leave[0] is not\
                        None:
                    worksheet.write(row, col + 9, taken_leave[0],
                                    table_border1_center)
                else:
                    worksheet.write(row, col + 9, 0, table_border1_center)
#               BALANCE YTD
                if total_leave != 0:
                    if taken_leave and taken_leave[0] and \
                            taken_leave[0] is not None:
                        after_blc = int(total_leave) - taken_leave[0]
                        worksheet.write(row, col + 10, after_blc or 0,
                                        table_border1_center)
                    else:
                        worksheet.write(row, col + 10, total_leave,
                                        table_border1_center)
                else:
                    worksheet.write(row, col + 10, 0, table_border1_center)
#               BALANCE MTD
                if earn_leaves != 0:
                    if taken_leave and taken_leave[0] and \
                            taken_leave[0] is not None:
                        earn_leaves = earn_leaves - taken_leave[0]
                        worksheet.write(row, col + 11, earn_leaves,
                                        table_border1_center)
                    else:
                        worksheet.write(row, col + 11, earn_leaves,
                                        table_border1_center)
                else:
                    worksheet.write(row, col + 11, 0, table_border1_center)
                row += 1
            row = row + 1

#         WHEN LEAVE CHECK BOX IS TRUE
        elif context['all_leave'] is True and context['all_employee'] is False:
            row = 2
            col = 0
            self._get_company_info(worksheet, row, header2)
            row = row + 4
            leave_name = ''
            emp_record = self.employee_id
            if emp_record.leave_config_id and\
                    emp_record.leave_config_id. holiday_group_config_line_ids:
                leave_ids = [leave_config_type.leave_type_id.id for leave_config_type in emp_record.leave_config_id.holiday_group_config_line_ids if leave_config_type.leave_type_id]
                for leave in leave_obj.browse(leave_ids):
                    row = row + 1
                    worksheet.row(row).height = 300
                    worksheet.row(row + 2).height = 500
                    leave_name = leave.name2 if leave.name2 else leave.name
                    worksheet.write_merge(row, row, col, 2,
                                          leave_name, header3)
                    self._get_employee_header(worksheet, row, table_border)
                    row = row + 3
                    col = 0
                    emp_id = emp_record.id
                    leave_id = leave.id
                    pending_leave = self._get_pending_leave(
                        emp_id, leave_id, from_date_str, from_to_str)
                    taken_leave = self._get_taken_leave(
                        emp_id, leave_id, from_date_str, from_to_str)
                    total_leave = self._get_total_leave(
                        emp_id, leave_id, fiscalyear_id)
                    carry_leave = self._get_carry_leave(
                        emp_id, leave_id, fiscalyear_id)
                    earn_leaves = self._get_earn_leave(emp_record, leave_id,
                        context["from_date"], context["to_date"], fiscalyear_id)
                    # DEPARTMENT
                    if emp_record.department_id and \
                            emp_record.department_id.name:
                        worksheet.write(row, col + 0,
                                        emp_record.department_id.name,
                                        table_border1)
                    else:
                        worksheet.write(row, col + 0, '', table_border1)
                    # IDENTIFICATION NUMBER
                    if emp_record.identification_id:
                        worksheet.write(row, col + 1,
                                        emp_record.identification_id,
                                        table_border1)
                    else:
                        worksheet.write(row, col + 1, '', table_border1)

                    if emp_record.name:
                        worksheet.write(row, col + 2, emp_record.name,
                                        table_border1)
                    else:
                        worksheet.write(row, col + 2, emp_record.name,
                                        table_border1)

                    if emp_record.join_date:
                        emp_j_date = emp_record.join_date
                        emp_join_dt = str(emp_j_date.strftime('%d')) + '-' + \
                            str(emp_j_date.strftime('%m')) + '-' + \
                            str(emp_j_date.strftime('%Y'))
                        worksheet.write(row, col + 3, emp_join_dt,
                                        table_border1)
                    else:
                        worksheet.write(row, col + 3, '', table_border1)

                    if emp_record.joined_year:
                        worksheet.write(row, col + 4, emp_record.joined_year,
                                        table_border1)
                    else:
                        worksheet.write(row, col + 4, '', table_border1)

                    if emp_record.leave_config_id and \
                            emp_record.leave_config_id.name:
                        worksheet.write(row, col + 5,
                                        emp_record.leave_config_id.name,
                                        table_border1)
                    else:
                        worksheet.write(row, col + 5, '', table_border1)

                    # CARRY FORWARD
                    if carry_leave and carry_leave[0] and \
                            carry_leave[0] is not None:
                        worksheet.write(row, col + 6, int(carry_leave[0]),
                                        table_border1_center)
                    else:
                        worksheet.write(row, col + 6, 0, table_border1_center)
                    # CURRENT YEAR TOTAL LEAVE
                    if total_leave != 0:
                        worksheet.write(row, col + 7, int(total_leave),
                                        table_border1_center)
                    else:
                        worksheet.write(row, col + 7, 0, table_border1_center)
                    # PENDING
                    if pending_leave and pending_leave[0] and \
                            pending_leave[0] is not None:
                        worksheet.write(row, col + 8, pending_leave[0],
                                        table_border1_center)
                    else:
                        worksheet.write(row, col + 8, 0, table_border1_center)
                    # TAKEN
                    if taken_leave and taken_leave[0] and \
                            taken_leave[0] is not None:
                        worksheet.write(row, col + 9, taken_leave[0],
                                        table_border1_center)
                    else:
                        worksheet.write(row, col + 9, 0, table_border1_center)
                    # BALANCE YTD
                    if total_leave != 0:
                        if taken_leave and taken_leave[0] and \
                                taken_leave[0] is not None:
                            after_blc = int(total_leave) - taken_leave[0]
                            worksheet.write(row, col + 10, after_blc or 0,
                                            table_border1_center)
                        else:
                            worksheet.write(row, col + 10, total_leave,
                                            table_border1_center)
                    else:
                        worksheet.write(row, col + 10, 0, table_border1_center)
                    # BALANCE MTD
                    if earn_leaves != 0:
                        if taken_leave and taken_leave[0] and \
                                taken_leave[0] is not None:
                            earn_leaves = earn_leaves - taken_leave[0]
                            worksheet.write(row, col + 11, earn_leaves,
                                            table_border1_center)
                        else:
                            worksheet.write(row, col + 11, earn_leaves,
                                            table_border1_center)
                    else:
                        worksheet.write(row, col + 11, 0, table_border1_center)
                    row += 1
                row = row + 1
        else:
            row = 2
            col = 0
            self._get_company_info(worksheet, row, header2)
            row = row + 5
            worksheet.row(row).height = 340
            worksheet.write_merge(row, row, col, 2,
                                  context["leave_type_id"][1], header3)
            worksheet.row(row + 2).height = 500
            self._get_employee_header(worksheet, row, table_border)
            row = row + 3
            col = 0
            emp_record = self.employee_id
            for emp_record in emp_record:
                emp_id = emp_record.id
                leave_id = context["leave_type_id"][0]
                pending_leave = self._get_pending_leave(
                    emp_id, leave_id, from_date_str, from_to_str)
                taken_leave = self._get_taken_leave(
                    emp_id, leave_id, from_date_str, from_to_str)
                total_leave = self._get_total_leave(
                    emp_id, leave_id, fiscalyear_id)
                carry_leave = self._get_carry_leave(
                    emp_id, leave_id, fiscalyear_id)
                earn_leaves = self._get_earn_leave(
                    emp_record, leave_id, context["from_date"],
                    context["to_date"], fiscalyear_id)
            if emp_record.department_id and \
                    emp_record.department_id.name:
                worksheet.write(row, col + 0, emp_record.department_id.name,
                                table_border1)
            else:
                worksheet.write(row, col + 0, '', table_border1)
#           IDENTIFICATION NUMBER
            if emp_record.identification_id:
                worksheet.write(row, col + 1, emp_record.identification_id,
                                table_border1)
            else:
                worksheet.write(row, col + 1, '', table_border1)
#           EMPLOYEE NAME
            if emp_record.name:
                worksheet.write(row, col + 2, emp_record.name, table_border1)
            else:
                worksheet.write(row, col + 2, emp_record.name, table_border1)
#           DATE JOINED
            if emp_record.join_date:
                emp_j_date = emp_record.join_date
                emp_join_dt = str(emp_j_date.strftime('%d')) + '-' + \
                    str(emp_j_date.strftime('%m')) + '-' + \
                    str(emp_j_date.strftime('%Y'))
                worksheet.write(row, col + 3, emp_join_dt, table_border1)
            else:
                worksheet.write(row, col + 3, '', table_border1)
#           SERVICE YEARS
            if emp_record.joined_year:
                worksheet.write(row, col + 4, emp_record.joined_year,
                                table_border1)
            else:
                worksheet.write(row, col + 4, '', table_border1)
#           LEAVE STRUCTURE
            if emp_record.leave_config_id and emp_record.leave_config_id.name:
                worksheet.write(row, col + 5, emp_record.leave_config_id.name,
                                table_border1)
            else:
                worksheet.write(row, col + 5, '', table_border1)
#           CARRY FORWARD
            if carry_leave and carry_leave[0] and carry_leave[0] is not None:
                worksheet.write(row, col + 6, int(carry_leave[0]),
                                table_border1_center)
            else:
                worksheet.write(row, col + 6, 0, table_border1_center)
#           CURRENT YEAR
            if total_leave != 0:
                worksheet.write(row, col + 7, int(total_leave),
                                table_border1_center)
            else:
                worksheet.write(row, col + 7, 0, table_border1_center)
#           PENDING
            if pending_leave and pending_leave[0] and pending_leave[0] is not\
                    None:
                worksheet.write(row, col + 8, pending_leave[0],
                                table_border1_center)
            else:
                worksheet.write(row, col + 8, 0, table_border1_center)
#           TAKEN
            if taken_leave and taken_leave[0] and taken_leave[0] is not None:
                worksheet.write(row, col + 9, taken_leave[0],
                                table_border1_center)
            else:
                worksheet.write(row, col + 9, 0, table_border1_center)
#           BALANCE YTD
            if total_leave != 0:
                if taken_leave and taken_leave[0] and taken_leave[0] is not\
                        None:
                    after_blc = int(total_leave) - taken_leave[0]
                    worksheet.write(row, col + 10, after_blc or 0,
                                    table_border1_center)
                else:
                    worksheet.write(row, col + 10, total_leave,
                                    table_border1_center)
            else:
                worksheet.write(row, col + 10, 0, table_border1_center)
#           BALANCE MTD
            if earn_leaves != 0:
                if taken_leave and taken_leave[0] and taken_leave[0] is not\
                        None:
                    earn_leaves = earn_leaves - taken_leave[0]
                    worksheet.write(row, col + 11, earn_leaves,
                                    table_border1_center)
                else:
                    worksheet.write(row, col + 11, earn_leaves,
                                    table_border1_center)
            else:
                worksheet.write(row, col + 11, 0, table_border1_center)
            row += 1
        row = row + 1
        fp = io.BytesIO()
        workbook.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()
        res = base64.b64encode(data)
#        res = base64.encodestring(data)
        vals = {'name': 'Leave summary.xls', 'file': res}
        module_rec = self.env['excel.sg.leave.summary.report'].create(vals)
        return {
            'name': _('Leave Summary Report'),
            'res_id': module_rec.id,
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'excel.sg.leave.summary.report',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
        }
