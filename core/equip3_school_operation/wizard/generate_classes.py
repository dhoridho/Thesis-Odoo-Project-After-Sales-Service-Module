
from odoo import _, models, fields, api
from datetime import timedelta, datetime, date
from odoo.exceptions import ValidationError

class GenerateClasses(models.TransientModel):
    _name = "generate.classes"

    timetable_type = fields.Selection([("regular","Regular Timetable"),("exam","Exam Timetable")], string='Timetable Type', default="regular", required=True)
    timetable_name = fields.Many2many('time.table', string='Timetable Name', domain="[('timetable_type', '=', timetable_type)]", required=True)

    def create_classes(self, start_date, end_date, record, time):
        count = 0
        data = {}
        classes = self.env["ems.classes"]
        if time.timetable_type == "regular":
            classes_type = "regular"
            while start_date <= end_date:
                holiday = self.env["ems.public.holiday"].search([('date', '=', start_date)], limit=1)
                if holiday:
                    start_date += timedelta(days=1)
                    continue
                if str(start_date.strftime('%A')).lower() == record.week_day:
                    count += 1
                    data.update({count: start_date})
                start_date += timedelta(days=1)
        else:
            classes_type = "exam"
            data.update({count: start_date})
        for key, value in data.items():
            ems_classes = classes.search([('year_id', '=', time.year_id.id),('term_id', '=', time.term_id.id),
                        ('program_id', '=', time.program_id.id),('intake_id', '=', time.standard_id.id),('start_time', '=', record.start_time),
                        ('end_time', '=', record.end_time),('timetable_id', '=', time.id),('classroom_id', '=', record.class_room_id.id),
                        ('study_day', '=', record.week_day),('subject_id', '=', record.subject_id.id),('class_date', '=', value),
                        ('start_am_pm', '=', record.start_am_pm), ('end_am_pm', '=', record.end_am_pm)
                        ], limit=1)
            if ems_classes:
                continue
            if record.class_room_id:
                same_date_classes = self.env['ems.classes'].search([('classroom_id', '=', record.class_room_id.id), ('class_date', '=', value)])
                for x in same_date_classes:
                    if record.start_time >= x.start_time and record.start_time <= x.end_time:
                        raise ValidationError('Classroom is not available. Please select other class.')
                    if record.end_time >= x.start_time:
                        raise ValidationError('Classroom is not available. Please select other class.')
            classes_dict = {
                'name': time.name,
                'school_id': time.school_id.id,
                'year_id': time.year_id.id,
                'term_id': time.term_id.id,
                'program_id': time.program_id.id,
                'intake_id': time.standard_id.id,
                'group_class': time.group_class.ids,
                'start_time': record.start_time,
                'end_time': record.end_time,
                'timetable_id': time.id,
                'teacher_id': record.teacher_id.id,
                'classroom_id': record.class_room_id.id,
                'study_day': record.week_day,
                'subject_id': record.subject_id.id,
                'start_am_pm': record.start_am_pm,
                'end_am_pm': record.end_am_pm,
                'class_date': value,
                'classes_type': classes_type,
                'ems_classes_line': [(0, 0, {'student_id' : id, 'is_present': True}) for id in time.group_class.student_ids.ids]
            }
            classes.create(classes_dict)

    def generate_classes(self):
        for rec in self:
            domain = [('id', '=', rec.timetable_name.ids)]
            if rec.timetable_type == 'regular':
                domain += [('timetable_type','=','regular')]
            else:
                domain += [('timetable_type','=','exam')]
            timetable = self.env["time.table"].search(domain)
            for time in timetable:
                start_date = time.term_id.date_start
                end_date = time.term_id.date_stop
                for record in time.timetable_line_ids:
                    if time.timetable_type == "exam":
                        start_date = record.exm_date
                        end_date = record.exm_date + timedelta(days=1)
                    rec.create_classes(start_date, end_date, record, time)
