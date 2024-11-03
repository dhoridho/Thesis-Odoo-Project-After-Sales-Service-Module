
from odoo import api , models, fields 
from datetime import datetime, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

class ApprovalMatrixCustomerReject(models.TransientModel):
    _name = 'approval.matrix.customer.reject'
    _description = "Approval Matrix Customer Reject"


    reason = fields.Text(string="Reason")

    def action_confirm(self):
        customer_request_id = self.env['res.partner'].browse([self._context.get('active_id')])
        user = self.env.user
        approving_matrix_line = sorted(customer_request_id.approved_matrix_ids_customer.filtered(lambda r:not r.approved), key=lambda r:r.sequence)
        print('approving_matrix_line', approving_matrix_line)
        if approving_matrix_line:
            matrix_line = approving_matrix_line[0]
            name = matrix_line.state_char or ''
            if name != '':
                name += "\n • %s: Rejected" % (user.name)
            else:
                name += "• %s: Rejected" % (user.name)
            matrix_line.write({'state_char': name, 'time_stamp': datetime.now(), 'approver_state': 'refuse', 'feedback': self.reason})
            customer_request_id.state_customer = 'rejected'
            customer_request_id.active = False
