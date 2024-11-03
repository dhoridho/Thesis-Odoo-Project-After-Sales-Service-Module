# import xlwt
import base64
import xlsxwriter

from dataclasses import asdict
from datetime import datetime
from io import BytesIO
from odoo import api, fields, models, tools, _
from xlsxwriter.utility import xl_range

class ClassSchedule(models.TransientModel):
    _name = "class.schedule"
    _description = "Class Schedule"

    teacher_id = fields.Many2one('school.teacher', string='Teacher')
    year_id = fields.Many2one('academic.year', string='Academic Year', domain="[('current', '=', True)]", required=True)
    term_id = fields.Many2one('academic.month', string="Term", domain="[('year_id', '=', year_id)]", required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    partner_id = fields.Many2one(comodel_name='res.partner', string="Partner")
    xls_file = fields.Binary('Class Schedule Excel File')
    print_all_teacher_class_schedule = fields.Boolean('Print All Teacher Class Schedule', default=True)

    def _get_street(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_address_details(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.city:
            address = "%s" % (partner.city)
        if partner.state_id.name:
            address += ", %s" % (partner.state_id.name)
        if partner.zip:
            address += ", %s" % (partner.zip)
        if partner.country_id.name:
            address += ", %s" % (partner.country_id.name)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False
    
    def action_print_report(self):     
        file_data = BytesIO()
        workbook = xlsxwriter.Workbook(file_data, {})
        
        if not self.print_all_teacher_class_schedule and self.teacher_id:
            teachers = self.teacher_id
            file_name = f'Class Schedule - {self.teacher_id.name}.xlsx'
        else:
            teachers = self.env['school.teacher'].search([])
            file_name = f'Teacher Class Schedule - {self.year_id.name} - {self.term_id.name}.xlsx'
        
        for teacher in teachers:
            # Create a new sheet for each teacher
            # Since sheet name can't exceed 31 characters, it will be truncated
            sheet_name = teacher.name[:31]
            sheet = workbook.add_worksheet(sheet_name)

            # Define cell formats
            format_info = workbook.add_format({'font_size': 12, 'align': 'left', 'valign': 'vcenter', 'bold': True})
            format_table_cell = workbook.add_format({'font_size': 12, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True})

            # Write report header
            sheet.write(0, 0, 'Teacher', format_info)
            sheet.write(0, 1, '{}'.format(teacher.name if teacher else ''), format_info)

            sheet.write(1, 0, 'Academic Year', format_info)
            sheet.write(1, 1, '{}'.format(self.year_id.name if self.year_id else ''), format_info)

            sheet.write(2, 0, 'Term', format_info)
            sheet.write(2, 1, '{}'.format(self.term_id.name if self.term_id else ''), format_info)

            # Fetch and organize schedule data for the current teacher
            ems_classes = teacher.ems_classes_ids.filtered(
                lambda x: x.year_id == self.year_id and x.term_id == self.term_id
                ).sorted(key=lambda x: (x.class_date, x.start_time)
            )

            schedule = {}
            for ems_class in ems_classes:
                if not ems_class.class_date or not ems_class.program_id or not ems_class.intake_id:
                    continue

                date = ems_class.class_date.strftime('%-d %b %Y')
                schedule.setdefault(date, {}).setdefault(ems_class.program_id.name, {}).setdefault(
                    ems_class.intake_id.name, []
                ).append('{}\n{}\n{} - {}'.format(
                    '; '.join([gc.name for gc in ems_class.group_class]),
                    ems_class.subject_id.name if ems_class.subject_id else '',
                    '{:02.0f}:{:02.0f}'.format(*divmod(ems_class.start_time * 60, 60)),
                    '{:02.0f}:{:02.0f}'.format(*divmod(ems_class.end_time * 60, 60))
                ))

            # Calculate the maximum number of classes for each program and intake
            max_class = {program.name: {} for program in ems_classes.mapped('program_id')}
            for programs in schedule.values():
                for program, intakes in programs.items():
                    for intake, classes in intakes.items():
                        max_class[program].setdefault(intake, 0)
                        max_class[program][intake] = max(max_class[program][intake], len(classes))
            
            # Write table headers
            sheet.merge_range(3, 0, 4, 0, 'Date', format_table_cell)
            program_start_col = 1
            program_col = {}
            intake_col = {}

            for program, intakes in max_class.items():
                program_col[program] = program_start_col
                col_length = sum(max_class[program].values())
                sheet.merge_range(3, program_start_col, 3, program_start_col + col_length - 1, program, format_table_cell)

                intake_start_col = program_start_col
                for intake, class_count in intakes.items():
                    intake_col[f'{program} - {intake}'] = (intake_start_col, class_count)
                    if class_count != 1:
                        sheet.merge_range(4, intake_start_col, 4, intake_start_col + class_count - 1, intake, format_table_cell)
                    else:
                        sheet.write(4, intake_start_col, intake, format_table_cell)
                    intake_start_col += class_count
                program_start_col += col_length
                
            # Write schedule data
            start_row = 5
            for date, programs in schedule.items():
                sheet.write(start_row, 0, date, format_table_cell)
                for program, intakes in programs.items():
                    for intake, classes in intakes.items():
                        class_start_col = intake_col[f'{program} - {intake}'][0]
                        len_intake_col = intake_col[f'{program} - {intake}'][1]
                        if len_intake_col % len(classes) == 0:
                            len_class_col = len_intake_col // len(classes)
                            for gc in classes:
                                if len_class_col != 1:
                                    sheet.merge_range(start_row, class_start_col, start_row, class_start_col + len_class_col - 1, gc, format_table_cell)
                                else:
                                    sheet.write(start_row, class_start_col, gc, format_table_cell)
                                class_start_col += len_class_col
                        else:
                            for gc in classes:
                                sheet.write(start_row, class_start_col, gc, format_table_cell)
                                class_start_col += 1
                start_row += 1
                
            # Apply formatting
            total_class_count = sum(class_count for intakes in max_class.values() for class_count in intakes.values())
            cell_range = xl_range(3, 0, 4 + len(schedule), total_class_count)
            format_border = workbook.add_format({'border': 1})
            sheet.conditional_format(cell_range, {'type': 'blanks', 'format': format_border})
            sheet.conditional_format(cell_range, {'type': 'no_blanks', 'format': format_border})
            sheet.autofit()

        workbook.close()
        file_data.seek(0)
        self.xls_file = base64.encodestring(file_data.getvalue())

        return{
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=class.schedule&field=xls_file&download=true&id=%s&filename=%s' % (self.id, file_name),
            'target': 'new',
        }

    def _get_timetable(self):
        for record in self:
            timetable_id = self.env["time.table"].search([('year_id', '=', record.year_id.id), ('term_id','=', record.term_id.id)], limit=1)
            return timetable_id

    def _get_timetable_lines(self):
        for record in self:
            timetable_id = self.env["time.table"].search([('year_id', '=', record.year_id.id), ('term_id','=', record.term_id.id)], limit=1)
            class_ids = self.env['ems.classes'].search([('timetable_id', '=', timetable_id.id), ('teacher_id', '=', record.teacher_id.id)], order='id')
            return class_ids
