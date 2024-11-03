from odoo import _, api, fields, models


class TimeTable(models.Model):
    _inherit = 'time.table'

    year_id = fields.Many2one('academic.year', 'Academic Year', required=True,
                              help="Select academic year")


class EMSClassSchedule(models.Model):
    _name = 'ems.class.schedule'
    _description = 'Class Schedule'

    name = fields.Char(string='Name', required=True)
    standard_id = fields.Many2one('standard.standard', string='Standard', required=True)
    teacher_id = fields.Many2one('school.teacher', string='Teacher', required=True)
    class_room_id = fields.Many2one('class.room', 'Classroom')
    study_day = fields.Selection(
        [('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday')],
         string='Study Day')