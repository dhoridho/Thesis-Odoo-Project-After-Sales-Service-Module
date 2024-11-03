# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class SaleServiceMatrixReject(models.TransientModel):
    _name = "sale.service.matrix.reject"
    _description = "Sale Service Matrix Reject"

    reason = fields.Text(string="Reason")

    def action_reject(self):
        sale_service_id = self.env["sale.service"].browse(
            [self._context.get("active_id")]
        )
        user = self.env.user
        approving_matrix_line = sorted(
            sale_service_id.approved_matrix_ids.filtered(lambda r: not r.approved),
            key=lambda r: r.sequence,
        )
        if approving_matrix_line:
            matrix_line = approving_matrix_line[0]
            name = matrix_line.state_char or ""
            if name != "":
                name += "\n • %s: Rejected - %s" % (
                    user.name,
                    datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                )
            else:
                name += "• %s: Rejected - %s" % (
                    user.name,
                    datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                )
            matrix_line.write(
                {
                    "state_char": name,
                    "time_stamp": datetime.now(),
                    "feedback": self.reason,
                    "last_approved": self.env.user,
                }
            )
            sale_service_id.state = "rejected"
