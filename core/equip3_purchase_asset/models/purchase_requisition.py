
from odoo import api, fields, models, _


class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'
    
    is_assets_orders = fields.Boolean(string="Assets Orders", default=False)
    
    @api.model
    def create(self, vals):
        context = dict(self.env.context) or {}
        res = super(PurchaseRequisition , self).create(vals)
        if context.get('assets_orders'):
            res.name = self.env['ir.sequence'].next_by_code('purchase.requisition.blanket.order.new.a')
        return res
    
    @api.depends('branch_id')
    def _get_approval_matrix(self):
        res = super(PurchaseRequisition, self)._get_approval_matrix()
        for record in self:
            if record.is_assets_orders:
                matrix_id = self.env['approval.matrix.blanket.order'].search([('branch_id', '=', record.branch_id.id), ('order_type', '=', 'assets_order')], limit=1, order='id desc')
                record.approval_matrix_id = matrix_id
        return res

class PurchaseRequisitionLine(models.Model):
    _inherit = 'purchase.requisition.line'
    
    # Jalan
    @api.model
    def _default_domain(self):
        context = dict(self.env.context) or {}
        res = super(PurchaseRequisitionLine , self)._default_domain()
        domain = [('company_id','=',self.env.company.id)]
        if context.get('assets_orders'):
            return domain+[('type', '=', 'asset')]
        return res
    
    is_assets_orders = fields.Boolean(string="Assets Orders", default=False, related='requisition_id.is_assets_orders')
    product_id = fields.Many2one(domain=_default_domain)
    