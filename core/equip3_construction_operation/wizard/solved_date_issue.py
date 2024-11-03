from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError
from datetime import datetime, date
from datetime import timedelta

class Solvedissue(models.TransientModel):
    _name = 'solve.issue.date'

    solved_date = fields.Datetime(string='Issue Solved Date', required=True, default=fields.Datetime.now)
    issue_id = fields.Many2one('project.issue', string='Issue')

    def confirm(self):
        stage = self.env['issue.stage'].search([('name', '=', 'Solved')], limit=1).id
        self.issue_id.update({'issue_stage_id': stage})
        self.issue_id.write({'issue_solved_date': self.solved_date})