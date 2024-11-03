from odoo import api , models, fields 
from datetime import datetime, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

class ClaimRequestReject(models.TransientModel):
    _name = 'claim.request.reject'

    reason = fields.Text(string="Reason")
    claim_id = fields.Many2one('progressive.claim', string='Claim ID')

    def action_confirm(self):
        job_id = self.env['claim.request.line'].browse([self._context.get('active_id')])
        job_id.write({'rejected_reason': self.reason, 
                      'rejected_date': datetime.now(), 
                      'state': 'rejected',
                      'state2': 'rejected',
                      'requested_progress_2': 0
                      })
                      
        if job_id.request_ids:
            for res in job_id.request_ids:
                res.write({'wo_prog_temp': 0})
                # if job_id.progressive_bill == False:
                #     res.work_order.write({
                #         'last_progress': res.last_progress
                #     })
                # elif job_id.progressive_bill == True:
                #     res.work_order_sub.write({
                #         'last_progress': res.last_progress
                #     })
            

        claim_id = self.claim_id.id
        action = self.env.ref('equip3_construction_accounting_operation.progressive_claim_action_form').read()[0]
        action['res_id'] = claim_id
        return action
            

class ApprovalMatrixRejectRequest(models.TransientModel):
    _name = 'approval.matrix.claim.request.reject'

    reason = fields.Text(string="Reason")
    claim_id = fields.Many2one('progressive.claim', string='Claim ID')

    def action_confirm(self):
        claim = self.env['claim.request.line'].browse([self._context.get('active_id')])
        approving_matrix_line = sorted(claim.claim_request_user_ids.filtered(lambda r: r.is_approve == False))
        if approving_matrix_line:
            matrix_line = approving_matrix_line[0]
            matrix_line.write({'feedback': self.reason})
            claim.action_reject_approval()

        claim_id = self.claim_id.id
        action = self.env.ref('equip3_construction_accounting_operation.progressive_claim_action_form').read()[0]
        action['res_id'] = claim_id
        return action
    
    # def action_confirm(self):
    #     req = self.env['claim.request.line'].browse([self._context.get('active_id')])
    #     user = self.env.user
    #     approving_matrix_line = sorted(req.approved_matrix_ids.filtered(lambda r:not r.approved), key=lambda r:r.sequence)
    #     if approving_matrix_line:
    #         matrix_line = approving_matrix_line[0]
    #         name = matrix_line.state_char or ''
    #         if name != '':
    #             name += "\n • %s: Rejected" % (user.name)
    #         else:
    #             name += "• %s: Rejected" % (user.name)
    #         matrix_line.write({'state_char': name, 'time_stamp': datetime.now(), 'feedback': self.reason, 'last_approved': self.env.user})
    #         req.write({'state': 'rejected',
    #                   'requested_progress_2': 0
    #                   })

    #     if req.request_ids:
    #         for res in req.request_ids:
    #             res.write({'wo_prog_temp': 0})
                # if req.progressive_bill == False:
                #     res.work_order.write({
                #         'last_progress': res.last_progress
                #     })
                # elif req.progressive_bill == True:
                #     res.work_order_sub.write({
                #         'last_progress': res.last_progress
                #     })
            
