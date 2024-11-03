from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError


class CompleteProjectWizard(models.TransientModel):
    _name = 'complete.project.wizard'
    _description = 'Confirmation wizard for completing a project'

    project_id = fields.Many2one('project.project', string='project')
    project_name = fields.Char(string='Project : ', related='project_id.name')
    progressive_claim_names = fields.Char(string='Progress Claim : ', compute='_compute_progressive_claim_names' )
    warning = fields.Html(string='Warning')
    
    
    @api.depends('project_id')
    def _compute_progressive_claim_names(self):
        progress_claim_ids = self.env['progressive.claim'].search([('project_id', '=', self.project_id.id)])
        temp_list = list()
        for record in progress_claim_ids:
            temp_list.append(record.name)
        self.progressive_claim_names = ', '.join(temp_list)

        temp_warning ="""
             You have unfinished progressive claim(s) : <br>
             <table class="table table-striped" cellspacing="1" cellpadding="4" border="0">
                        <tr>
                            <th>Progressive Claim</th>
                        </tr>"""
        
        for progressive in progress_claim_ids:
            temp_warning += """
                            <tr>
                                <td>""" + progressive.name + """</td>
                            </tr>
            """
        
        temp_warning += """</table>"""

        self.warning = temp_warning

class CompleteProjectWizardDate(models.TransientModel):
    _name = 'complete.project.wizard.date'
    _description = 'Confirmation Complete Project'

    act_end_date = fields.Date(string='Actual End Date')
    
    def action_confirm(self):
        project = self.env['project.project'].browse([self._context.get('active_id')])
        project.write({'act_end_date': self.act_end_date, 
                      'primary_states': 'completed'
                      })
