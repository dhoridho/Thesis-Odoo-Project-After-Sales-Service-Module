from odoo import api, models, fields, _

class ClassFlowWizard(models.TransientModel):
    _name = 'class.flow.wizard'

    name = fields.Char(string='Name', default='School Flow')

    def button_create_exam(self):
        action = self.env.ref('exam.action_exam_exam_form').read()[0]
        return action

    def button_generate_classes_exam(self):
        action = self.env.ref('equip3_school_operation.action_generate_classes').read()[0]
        return action

    def button_exam_classes(self):
        action = self.env.ref('equip3_school_operation.ems_exam_class_action').read()[0]
        return action

    def button_daily_attendance(self):
        action = self.env.ref('school_attendance.action_daily_attendance_form').read()[0]
        return action

    def button_regular_timetable(self):
        action = self.env.ref('timetable.action_timetable_regular').read()[0]
        return action

    def button_generate_classes_regular(self):
        action = self.env.ref('equip3_school_operation.action_generate_classes').read()[0]
        return action

    def button_regular_classes(self):
        action = self.env.ref('equip3_school_operation.ems_regular_class_action').read()[0]
        return action

    def button_exam_timetable(self):
        action = self.env.ref('exam.timetable_exam_action').read()[0]
