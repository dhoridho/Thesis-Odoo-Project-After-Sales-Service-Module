from odoo import api, fields, models, _

class AttendanceConfigurationFlow(models.TransientModel):
    _name = 'attendance.configuration.flow'

    name = fields.Char('Name', default='Attendance Flow')

    def get_action_info(self):
        action = self.env.ref(self._context['act_ref'])
        result = action.read()[0]
        return result