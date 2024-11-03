
from odoo import api, fields, models, _
import logging
_logger = logging.getLogger(__name__)

class ApprovalReject(models.TransientModel):
    _name='account.approval.reject'
    _description = 'Reject Approval'
    
    move_id = fields.Many2one('account.move','Move')
    feedback = fields.Text('Reason')
    @api.model
    def default_get(self, fields_list):
        # OVERRIDE
        res = super().default_get(fields_list)
        if self._context.get('active_model') == 'account.move' and self._context.get('active_id'):
                move_id = self.env['account.move'].browse(self._context.get('active_id'))
                res['move_id'] = [(4,move_id.id)]
        return res
    def action_post_reject(self):
        self.move_id.write_matrix_line({'state_char':'Rejected','time_stamp':fields.Datetime.now(),'feedback':self.feedback})
        self.move_id.state = 'rejected'
        return True