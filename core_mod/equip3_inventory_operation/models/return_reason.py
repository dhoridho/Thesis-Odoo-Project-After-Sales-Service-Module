from odoo import models, fields


class ReturnReason(models.Model):
    _name = "return.reason"
    _description = "Return Reason"

    name = fields.Char("Reason")
