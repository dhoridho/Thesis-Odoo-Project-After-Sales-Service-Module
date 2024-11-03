from odoo import _, api, fields, models
from datetime import datetime
from odoo.exceptions import ValidationError


class CompleteConfirmation(models.TransientModel):
    _name = 'complete.confirm.wiz'
    _description = 'Complete Confirmation Wizard'

    txt = fields.Text(string="Confirmation",default="Looks like the job order has not been completed.\nDo you want to finish it now?")
    reason = fields.Text(string="Reason")

    def yes_button(self):
        res = self._context.get('default_project_task_id', False)
        if res:
            res_id = self.env['project.task'].browse(res)
            if res_id:
                context = {'default_actual_end_date': self._context.get('default_actual_end_date', False),
                            'default_project_task_id': res_id.id,
                            'default_reason': self.reason}
                return{
                    'type': 'ir.actions.act_window',
                    'res_model': 'project.task.completion.wizard',
                    'name': _("Completion Confirmation"),
                    'target': 'new',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'context': context,
                }
        

