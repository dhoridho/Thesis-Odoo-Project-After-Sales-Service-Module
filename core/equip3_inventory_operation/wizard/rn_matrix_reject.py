# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class ReceivingNotesMatrixReject(models.TransientModel):
    _name = "rn.matrix.reject"
    _description = 'Receiving NOtes Approval Matrix'

    reason = fields.Text(string="Reason")

    def action_reject(self):
        picking_id = self.env['stock.picking'].browse([self._context.get('active_id')])
        user = self.env.user
        approving_matrix_line = sorted(picking_id.approved_matrix_ids.filtered(lambda r:not r.approved), key=lambda r:r.sequence)
        if approving_matrix_line:
            matrix_line = approving_matrix_line[0]
            name = matrix_line.approval_status or ''
            if name != '':
                name += "\n • %s: Rejected - %s" % (user.name, datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT))
            else:
                name += "• %s: Rejected - %s" % (user.name, datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT))
            matrix_line.write({'approval_status': name, 'time_stamp': datetime.now(), 'feedback': self.reason, 'last_approved': self.env.user})
            picking_id.state = 'rejected'
        return True

class DeliveryOrderMatrixReject(models.TransientModel):
    _name = "do.matrix.reject"
    _description = 'DO Matrix Reject'

    reason = fields.Text(string="Reason")

    def action_reject(self):
        picking_id = self.env['stock.picking'].browse([self._context.get('active_id')])
        user = self.env.user
        do_approving_matrix_line = sorted(picking_id.do_approved_matrix_ids.filtered(lambda r:not r.approved), key=lambda r:r.sequence)
        if do_approving_matrix_line:
            matrix_line = do_approving_matrix_line[0]
            name = matrix_line.approval_status or ''
            if name != '':
                name += "\n • %s: Rejected - %s" % (user.name, datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT))
            else:
                name += "• %s: Rejected - %s" % (user.name, datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT))
            matrix_line.write({'approval_status': name, 'time_stamp': datetime.now(), 'feedback': self.reason, 'last_approved': self.env.user})
            picking_id.state = 'rejected'
        return True
