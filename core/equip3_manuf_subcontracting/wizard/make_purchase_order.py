from odoo import models, fields, api, _


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = 'purchase.request.line.make.purchase.order'

    @api.model
    def default_get(self, fields):
        res = super(PurchaseRequestLineMakePurchaseOrder, self).default_get(fields)
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        if active_model != 'purchase.request' or not active_id:
            return res
        pr_id = self.env['purchase.request'].browse(active_id)
        if pr_id and pr_id.is_a_subcontracting and pr_id.subcon_production_id and pr_id.subcon_production_id.bom_id:
            res['supplier_id'] = pr_id.subcon_production_id.bom_id.subcontractor_ids and pr_id.subcon_production_id.bom_id.subcontractor_ids[0].id or False
        res['purchase_request_id'] = pr_id.id
        return res

    @api.depends('purchase_request_id')
    def _compute_allowed_suppliers(self):
        original_partner_ids = self.env['res.partner'].search([('is_company', '=', True)])
        for record in self:
            allowed_partner_ids = original_partner_ids.ids
            pr_id = record.purchase_request_id
            if pr_id and pr_id.is_a_subcontracting and pr_id.subcon_production_id:
                allowed_partner_ids = pr_id.subcon_production_id.bom_id.subcontractor_ids.ids
            record.allowed_supplier_ids = [(6, 0, allowed_partner_ids)]

    supplier_id = fields.Many2one('res.partner', domain="[('id', 'in', allowed_supplier_ids)]")
    allowed_supplier_ids = fields.Many2many('res.partner', compute=_compute_allowed_suppliers)
    purchase_request_id = fields.Many2one('purchase.request', string='Purchase Request')

    @api.model
    def _prepare_purchase_order(self, picking_type, group_id, company, origin):
        vals = super(PurchaseRequestLineMakePurchaseOrder, self)._prepare_purchase_order(picking_type, group_id, company, origin)
        purchase_request_id = self.purchase_request_id
        if not self.purchase_request_id or not purchase_request_id.is_a_subcontracting:
            return vals

        vals.update({
            'is_a_subcontracting': purchase_request_id.is_a_subcontracting,
            'subcon_production_id': purchase_request_id.subcon_production_id.id,
            'subcon_product_qty': purchase_request_id.subcon_product_qty,
            'subcon_uom_id': purchase_request_id.subcon_uom_id.id,
            'requisition_id': purchase_request_id.subcon_requisition_id.id
        })
        return vals
