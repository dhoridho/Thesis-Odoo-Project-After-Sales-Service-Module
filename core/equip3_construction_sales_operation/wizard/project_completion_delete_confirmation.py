from odoo import api , models, fields 


class ProjectCompletionDeleteConfirmation(models.TransientModel):
    _name = 'project.completion.delete.confirmation'
    _description = 'Confirmation Delete Contract Completion'

    txt = fields.Text(string="Confirmation",default="Are you sure you want to delete this contract completion?")

    def action_confirm(self):
        proj_completion = self.env['project.completion.const'].browse([self._context.get('active_id')])
        proj_completion.unlink()
