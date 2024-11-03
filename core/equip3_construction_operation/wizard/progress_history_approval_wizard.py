from odoo import _, api, fields, models
from datetime import datetime
from odoo.exceptions import ValidationError


class ProgressHistoryApproval(models.TransientModel):
    _name = 'progress.history.approval.wizard'
    _description = 'Progress History Approval Wizard'

    project_id = fields.Many2one('project.project', string='Project')
    work_order = fields.Many2one('project.task', string='Job Order')
    warning = fields.Html(
        string='warning', 
            compute='_compute_field' )
    is_approve = fields.Boolean(string='Approve')
    is_rejectable = fields.Boolean(string='Rejectable', default=True)
        
    @api.depends('project_id')
    def _compute_field(self):
        for record in self:
            progress_history = []
            if record.is_approve:
                temp_progress_history = self._context.get('non_approvable_progress')
                
                for progress in temp_progress_history:
                    progress_history.append(self.env['progress.history'].search([('id', '=', progress)]))

                temp_warning ="""
                                    <br/>
                                    <h4>You are not allowed to approve these following documents: </h4>
                """
            else:
                temp_progress_history = self._context.get('non_rejectable_progress')

                for progress in temp_progress_history:
                    progress_history.append(self.env['progress.history'].search([('id', '=', progress)]))

                temp_warning ="""
                                    <br/>
                                    <h4>You are not allowed to reject these following documents: </h4>
                """

            temp_warning += """
                                <br/>
                                <table class="o_list_table table table-sm table-hover table-striped o_list_table_ungrouped">
            """
            temp_warning += """
                                <thead>
                                    <tr>
                                        <th>Project</th>
                                        <th>Contract</th>
                                        <th>Stage</th>
                                        <th>Job Order</th>
                                        <th>Progress Summary</th>
                                        <th>Status</th>
                                    </tr>
                                </thead>
            """
            temp_warning += """
                                <tbody>
            """

            for progress in progress_history:
                temp_warning += """
                                    <tr>
                                        <td>%s</td>
                                        <td>%s</td>
                                        <td>%s</td>
                                        <td>%s</td>
                                        <td>%s</td>
                                        <td>%s</td>
                                    </tr>
                """ % (progress.project_id.name, progress.sale_order.name, progress.stage_new.name.name, progress.work_order.name, progress.progress_summary, progress.state)


            temp_warning += """
            </tbody>
                                </table>
            """

            record.warning = temp_warning

    def action_confirm(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reject Reason',
            'res_model': 'approval.matrix.progress.reject',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            "context": {'default_job_id': self.work_order.id,
                        'rejectable_progress': self._context.get('rejectable_progress'),
                        'is_reject_from_tree': True
                        }
        }

            
        
        
    
    