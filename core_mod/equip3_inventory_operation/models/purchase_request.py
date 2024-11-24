from odoo import models, fields, api, _


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    mr_id = fields.Many2many('material.request', 'pr_id',
                             'mr_id', 'pr_mr_id', string='Mr')

    def button_done_pr(self):
        res = super(PurchaseRequest, self).button_done_pr()
        if self.mr_id:
            mr_rec = self.env['material.request'].search(
                [('id', 'in', self.mr_id.ids)])
            for pr_line in self.line_ids:
                for mr_line in mr_rec.product_line:
                    if pr_line.product_id.id == mr_line.product.id:
                        for po in pr_line.purchase_lines:
                            mr_line.pr_in_progress_qty += po.product_qty
                            mr_line.pr_done_qty += po.qty_received
        return res


class PurchaseRequestLine(models.Model):
    _inherit = 'purchase.request.line'

    mr_line_id = fields.Many2one('material.request.line')
    cancelled_qty = fields.Float('Cancelled Quantity', readonly='1')
