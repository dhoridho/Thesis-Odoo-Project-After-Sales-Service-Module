from odoo import _, api, fields, models
import json

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    procurement_planning_id = fields.Many2one(
        comodel_name='procurement.planning.model', string='Procurement Planning', ondelete='cascade')

    @api.model
    def create(self, vals):
        context = self.env.context
        if vals.get('procurement_planning_id'):
            procurement_planning = self.env['procurement.planning.model'].browse(
                vals['procurement_planning_id'])
            if procurement_planning.state == 'confirm':
                procurement_planning.state = 'in_progress'

        if context.get('default_pr_id'):
            purchase_requests = self.env['purchase.request'].browse(context.get('default_pr_id'))
            for purchase_request in purchase_requests:
                if purchase_request and purchase_request.procurement_planning_id:
                    vals['procurement_planning_id'] = purchase_request.procurement_planning_id.id
                    break

        return super(PurchaseOrder, self).create(vals)
    
    def button_confirm(self):
        res = super(PurchaseOrder, self).button_confirm()
        for order in self.filtered('procurement_planning_id'):
            procurement_planning = order.procurement_planning_id
            procurement_lines_by_product_id = {line.product_id.id: line for line in procurement_planning.procurement_line}
            for line in order.order_line:
                if line.product_id.id in procurement_lines_by_product_id:
                    procurement_lines_by_product_id[line.product_id.id].quantity_ordered += line.product_qty
        return res

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    product_id_domain = fields.Char(
        'Product Domain', compute="compute_product_id_domain")

    @api.depends('order_id.procurement_planning_id')
    def compute_product_id_domain(self):
        self.product_id_domain = False
        procurement_planning = self.order_id.procurement_planning_id
        if procurement_planning:
            product_tmpl_ids = procurement_planning.procurement_line.mapped('product_id').ids
            self.product_id_domain = json.dumps(
                [('id', 'in', product_tmpl_ids)]) if product_tmpl_ids else json.dumps([('id', 'in', [])])
