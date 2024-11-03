# -*- coding: utf-8 -*-

from odoo import fields, models

class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    pos_branch_id = fields.Many2one('res.branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])

    def _select(self):
        return super(AccountInvoiceReport, self)._select() + ", line.pos_branch_id as pos_branch_id"