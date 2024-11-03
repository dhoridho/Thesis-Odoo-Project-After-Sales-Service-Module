from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    invoice_count = fields.Integer(
        string="Invoice Count",
        compute="_compute_invoice_count",
        store=False
    )

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for order in self:
            order.invoice_count = len(order.invoice_ids)

    def action_view_invoices(self):
        self.ensure_one()
        action = self.env.ref('account.action_invoice_tree').read()[0]
        action['domain'] = [('origin', '=', self.name)]
        action['context'] = {'default_origin': self.name}
        return action