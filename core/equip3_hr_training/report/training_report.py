# -*- coding: utf-8 -*-
from odoo import models, fields, tools, api, _
import base64
from io import BytesIO
from odoo.exceptions import ValidationError
import xlsxwriter


class HrTrainingReport(models.TransientModel):
    _name = 'training.report'
    _description = "Training Report"

    def _domain_employee_ids(self):
        domain = []
        if self.based_on == 'by_employee':
            emp_rec = self.env['hr.employee'].sudo().search([('company_id','=', self.env.company.id)])
            if emp_rec:
                for emp in emp_rec:
                    domain.append(emp.id)
        if self.based_on == 'by_job_position':
            if self.job_ids:
                emp_job_rec = self.env['hr.employee'].sudo().search([('job_id', 'in', self.job_ids.ids)])
                if emp_job_rec:
                    for emp in emp_job_rec:
                        domain.append(emp.id)
            if self.all_job:
                emp_rec = self.env['hr.employee'].sudo().search([('company_id','=', self.env.company.id)])
                if emp_rec:
                    for emp in emp_rec:
                        domain.append(emp.id)
        if self.based_on == 'by_department':
            if self.department_ids:
                emp_dept_rec = self.env['hr.employee'].sudo().search([('department_id', 'in', self.department_ids.ids)])
                if emp_dept_rec:
                    for emp in emp_dept_rec:
                        domain.append(emp.id)
            if self.all_dept:
                emp_rec = self.env['hr.employee'].sudo().search([('company_id','=', self.env.company.id)])
                if emp_rec:
                    for emp in emp_rec:
                        domain.append(emp.id)
        return domain

    @api.onchange('based_on', 'job_ids', 'department_ids', 'all_job', 'all_dept')
    def _onchange_based_on(self):
        domain = self._domain_employee_ids()
        return {'domain': {'employee_ids': [('id', 'in', domain)]}}

    @api.onchange('all_training_category')
    def _onchange_all_training_category(self):
        if self.all_training_category:
            training_cat_ids = self.env['training.category'].search([])
            self.training_category_ids = [(6, 0, training_cat_ids.ids)]
        else:
            self.training_category_ids = False

    @api.model
    def _multi_company_domain(self):
        return [('company_id','=', self.env.company.id)]
    
    based_on = fields.Selection(
        [('by_employee', 'By Employee'), ('by_job_position', 'By Job Position'), ('by_department', 'By Department')],
        string='Based On')
    employee_ids = fields.Many2many('hr.employee', string='Employee', default=_domain_employee_ids)
    job_ids = fields.Many2many('hr.job', string='Job', domain=_multi_company_domain)
    all_job = fields.Boolean('All Job Position')
    department_ids = fields.Many2many('hr.department', string='Department', domain=_multi_company_domain)
    all_dept = fields.Boolean('All Department')
    all_training_category = fields.Boolean('All Training Category', default=False)
    training_category_ids = fields.Many2many('training.category', string='Training Category')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')

    # Convert column Number to Column Name
    def col_num2_col_name(self, col):  # col is 1 based
        excel_col = str()
        div = col
        while div:
            (div, mod) = divmod(div - 1, 26)  # will return (x, 0 .. 25)
            excel_col = chr(mod + 65) + excel_col
        return excel_col

    def training_print_xls(self):
        if self.employee_ids:
            file_name = 'Training Report '
            fp = BytesIO()
            workbook = xlsxwriter.Workbook(fp)
            format0 = workbook.add_format({'font_size': 15, 'bold': True, 'align': 'left'})
            format1 = workbook.add_format({'font_size': 12, 'align': 'left'})
            format2 = workbook.add_format({'font_size': 12, 'bold': True, 'align': 'center'})
            format3 = workbook.add_format({'font_size': 12, 'align': 'center'})
            format4 = workbook.add_format({'font_size': 12, 'align': 'center'})
            format_red_color = workbook.add_format({'font_size': 12, 'bg_color': '#fb1111','align': 'center'})
            format_green_color = workbook.add_format({'font_size': 12, 'bg_color': '#67d644','align': 'center'})
            sheet = workbook.add_worksheet(file_name)
            sheet.set_column(0, 1, 15)
            sheet.set_column(2, 2, 7)

            # static Heading
            sheet.merge_range(4, 0, 6, 0, 'Job Position', format2)
            sheet.merge_range(4, 1, 6, 1, 'Employee', format2)
            sheet.merge_range(4, 2, 6, 2, 'Score', format2)
            course_column = 3
            # Dynamic Heading
            training_course = self.env['training.courses'].search(
                [('training_category_id', 'in', self.training_category_ids.ids)])
            for tc in training_course:
                sheet.set_column(course_column, course_column, 27)
                sheet.write(6, course_column, tc.name or '', format2)
                sheet.write(5, course_column, tc.training_category_id.name or '', format2)
                sheet.write(4, course_column, tc.training_category_id.parent_category_id.name or '', format2)
                course_column += 1
            sheet.set_column(course_column, course_column, 7)
            sheet.merge_range(4, course_column, 6, course_column, 'Total', format2)
            sheet.merge_range(0, course_column, 1, 0, "Training Report Result", format0)
            if self.based_on == 'by_employee':
                emp_list = list()
                for emp in self.employee_ids:
                    emp_list.append(emp.name)
                sheet.write(2, 0, "Employee", format2)
                sheet.merge_range(2, course_column, 2, 1, ", ".join(emp_list), format1)
            if self.based_on == 'by_job_position':
                if self.all_job:
                    sheet.write(2, 0, "Job", format2)
                    sheet.merge_range(2, course_column, 2, 1, "All Job Position", format4)
                else:
                    job_list = list()
                    for job in self.job_ids:
                        job_list.append(job.name)
                    sheet.write(2, 0, "Job", format2)
                    sheet.merge_range(2, course_column, 2, 1, ", ".join(job_list), format1)
            if self.based_on == 'by_department':
                if self.all_dept:
                    sheet.write(2, 0, "Department", format2)
                    sheet.merge_range(2, course_column, 2, 1, "All Department", format4)
                else:
                    dept_list = list()
                    for dept in self.department_ids:
                        dept_list.append(dept.name)
                    sheet.write(2, 0, "Department", format2)
                    sheet.merge_range(2, course_column, 2, 1, ", ".join(dept_list), format1)
            if self.start_date and self.end_date:
                sheet.write(3, 0, "Period", format2)
                sheet.merge_range(3, course_column, 3, 1, str(self.start_date) + ' - ' + str(self.end_date), format1)
            if not self.start_date and not self.end_date:
                sheet.write(3, 0, "Period", format2)
                sheet.merge_range(3, course_column, 3, 1, ' - ', format1)
            # Datas
            row = 7
            for employee in self.employee_ids:
                course_col = 3
                max_tc = []
                trc_rec = self.env['training.courses'].search([('training_category_id', 'in', self.training_category_ids.ids)])
                if trc_rec:
                    for trc in trc_rec:
                        datas = []
                        if not self.start_date and not self.end_date:
                            for tcl_rec in self.env['training.conduct.line'].search(
                                    [('employee_id', '=', employee.id), ('status', '=', 'Success'),
                                     ('course_id.training_category_id', 'in', self.training_category_ids.ids),
                                     ('conduct_id.stage_course_id.stage_id.name', '=', 'Completed'),
                                     ('conduct_id.course_id', '=', trc.id)]):
                                datas.append(tcl_rec.id)
                        if self.start_date and self.end_date:
                            for tcl_rec in self.env['training.conduct.line'].search(
                                    [('employee_id', '=', employee.id), ('status', '=', 'Success'),
                                     ('course_id.training_category_id', 'in', self.training_category_ids.ids),
                                     ('conduct_id.stage_course_id.stage_id.name', '=', 'Completed'),
                                     ('conduct_id.course_id', '=', trc.id),
                                     ('start_date', '>=', self.start_date), ('end_date', '<=', self.end_date)]):
                                datas.append(tcl_rec.id)
                        tcl = self.env['training.conduct.line'].browse(datas)
                        if tcl:
                            tcl_count = len(tcl)
                            max_tc.append(tcl_count)
                            sheet.write(row, 0, employee.job_id.name, format3)
                            sheet.write(row, 1, employee.name, format3)
                            a_row = row
                            for tc_line in tcl:
                                sheet.write(a_row, 2, 'Target', format4)
                                # sheet.write(a_row + 1, 0, '', format4)  # empty cell
                                # sheet.write(a_row + 1, 1, '', format4)  # empty cell
                                sheet.write(a_row + 1, 2, 'Actual', format4)
                                # sheet.write(a_row + 2, 0, '', format4)  # empty cell
                                # sheet.write(a_row + 2, 1, '', format4)  # empty cell
                                sheet.write(a_row + 2, 2, 'Gap', format4)
                                col_name = self.col_num2_col_name(course_column)
                                sheet.write(a_row, course_column, f'=Sum(D{a_row + 1}:{col_name}{a_row + 1})', format4)
                                sheet.write(a_row + 1, course_column, f'=Sum(D{a_row + 2}:{col_name}{a_row + 2})', format4)
                                sheet.write(a_row + 2, course_column, f'=Sum(D{a_row + 3}:{col_name}{a_row + 3})', format4)

                                for level_id in tcl.conduct_id.training_level_id:
                                    training_levels = self.env['training.level'].search([
                                        ('id', '=', level_id.id)
                                    ], limit=1)

                                    if training_levels:
                                        sheet.write(a_row, course_col, training_levels.target, format4)
                                        sheet.write(a_row + 1, course_col, tc_line.final_score, format4)
                                        if training_levels.target > tc_line.final_score:
                                            sheet.write(a_row + 2, course_col, (tc_line.final_score - training_levels.target), format_red_color)
                                        else:
                                            sheet.write(a_row + 2, course_col, (tc_line.final_score - training_levels.target), format_green_color)
                                a_row += 3
                            course_col += 1
                        else:
                            max_tc.append(0)
                else:
                    max_tc.append(1)
                max_number = max(max_tc)
                row += (max_number * 3)
            workbook.close()
            file_name += '.xls'

            export_id = self.env['training.report.attachment'].create(
                {'attachment_file': base64.encodebytes(fp.getvalue()), 'file_name': file_name})
            return {
                'view_mode': 'form',
                'res_id': export_id.id,
                'name': 'Training Report',
                'res_model': 'training.report.attachment',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'target': 'new',
            }
        else:
            raise ValidationError('There is no Data.')


class TrainingReportAttachment(models.TransientModel):
    _name = "training.report.attachment"
    _description = "Training Report Attachment"

    attachment_file = fields.Binary('Attachment File')
    file_name = fields.Char('File Name')
