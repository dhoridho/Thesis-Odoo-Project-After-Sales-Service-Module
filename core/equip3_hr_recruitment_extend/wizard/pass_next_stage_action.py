from email.policy import default
from odoo import fields, models, api


class passNextStageAction(models.TransientModel):
    _name = 'pass.next.stage.action'
    
    name = fields.Text(default="Pass To Next Stage?")
    
    
    def submit(self):
        active_ids = self._context.get('active_ids', []) or []
        for record in self.env['hr.applicant'].browse(active_ids):
            record.pass_to_next_stage()