
from odoo import api , models, fields 
from datetime import datetime, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT


class ApprovalMatrixsaleReject(models.TransientModel):
    _name = 'limit.approval.matrix.sale.reject.const'
    _description = 'Limit Approval Matrix Sale Construction Reject'

    reason = fields.Text(string="Reason")

    def action_confirm(self):
        sale_order_id = self.env['sale.order.const'].browse([self._context.get('active_id')])
        user = self.env.user
        approving_matrix_line = sorted(sale_order_id.approved_matrix_limit_ids.filtered(lambda r:not r.approved), key=lambda r:r.sequence)
        if approving_matrix_line:
            matrix_line = approving_matrix_line[0]
            name = matrix_line.state_char or ''
            if name != '':
                name += "\n • %s: Rejected" % (user.name)
            else:
                name += "• %s: Rejected" % (user.name)
            matrix_line.write({'state_char': name, 'time_stamp': datetime.now(), 'feedback': self.reason, 'last_approved': self.env.user})
            sale_order_id.state = 'over_limit_reject'
