from odoo import api , models, fields 
from datetime import datetime, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT


class ApprovalMatrixRejectProgress(models.TransientModel):
    _name = 'approval.matrix.progress.reject'
    _description = "Approval Matrix Reject Progress"

    reason = fields.Text(string="Reason")
    job_id = fields.Many2one('project.task', string='Job Order')

    def action_confirm(self):
        if self._context.get('is_reject_from_tree') == False:
            history_id = self.env['progress.history'].browse([self._context.get('active_id')])
            user = self.env.user
            approving_matrix_line = sorted(history_id.progress_history_user_ids.filtered(lambda r: r.is_approve == False))
            if approving_matrix_line:
                matrix_line = approving_matrix_line[0]
                matrix_line.write({'feedback': self.reason})
                history_id.action_reject_approval() 

            # progress = self.env['progress.history'].search([('progress_wiz', '=', history_id.progress_wiz.id),('id', '!=', history_id.id)])
            # if progress:
            #     for res in progress:
            #         approving_matrix_line_prog = sorted(res.progress_history_user_ids.filtered(lambda r: r.is_approve == False))
            #         if approving_matrix_line_prog:
            #             matrix_line = approving_matrix_line_prog[0]
            #             matrix_line.write({'feedback': self.reason})
            #             res.action_reject_approval()

            job_id = self.job_id.id
            action = self.env.ref('equip3_construction_operation.job_order_action_form').read()[0]
            action['res_id'] = job_id
            return action

        else:
            i = 0
            history = []
            for progress in self._context.get('rejectable_progress'):
                if i == 0:
                    history.append(self.env['progress.history'].search([('id', '=', progress)]))
                    i+=1
                else:
                    history[0] += (self.env['progress.history'].search([('id', '=', progress)]))

            if len(history) > 0:
                for req in history[0]:
                    user = self.env.user
                    approving_matrix_line = sorted(req.progress_history_user_ids.filtered(lambda r: r.is_approve == False))
                    if approving_matrix_line:
                        matrix_line = approving_matrix_line[0]
                        matrix_line.write({'feedback': self.reason})
                        req.action_reject_approval() 


                    progress = self.env['progress.history'].search([('progress_wiz', '=', req.progress_wiz.id), ('id', '!=', req.id)])
                    if progress:
                        for res in progress:
                            approving_matrix_line_prog = sorted(res.progress_history_user_ids.filtered(lambda r: r.is_approve == False))
                            if approving_matrix_line_prog:
                                matrix_line = approving_matrix_line_prog[0]
                                matrix_line.write({'feedback': self.reason})
                                res.action_reject_approval() 
                    

            return {'type': 'ir.actions.act_window_close'}
       