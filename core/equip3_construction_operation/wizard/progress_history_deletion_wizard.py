from odoo import api, fields, models


class ProgressHistoryDeletionWizard(models.TransientModel):
    _name = 'progress.history.deletion.wizard'
    _description = 'Progress History Deletion Wizard'

    current_progress = fields.Many2one(comodel_name='progress.history', string='Current Progress')
    txt = fields.Text(string="Confirmation", default="Are you sure you want to delete this progress?")

    def delete_progress_history(self):
        self.current_progress.unlink()

    
