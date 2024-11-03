
from odoo import api, fields, models, _


class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'
    
    is_rental_orders = fields.Boolean(string="Rental Orders", default=False)
    
    @api.model
    def create(self, vals):
        context = dict(self.env.context) or {}
        res = super(PurchaseRequisition , self).create(vals)
        if context.get('rentals_orders') or (res.purchase_id and res.purchase_id.is_rental_orders):
            context.update({
                'rentals_orders': True,
            })
            self = self.with_context(context)
            name = self.env['ir.sequence'].next_by_code('purchase.requisition.blanket.order.new.r')
            res.write({
                'name': name,
                'is_rental_orders': True,
            })
        return res
    
    @api.depends('branch_id')
    def _get_approval_matrix(self):
        res = super(PurchaseRequisition, self)._get_approval_matrix()
        for record in self:
            if record.is_rental_orders:
                matrix_id = self.env['approval.matrix.blanket.order'].search(
                    [
                        ('branch_id', '=', record.branch_id.id), 
                        ('order_type', '=', 'rental_order')
                    ], 
                    limit=1, order='id desc')
                record.approval_matrix_id = matrix_id
        return res

    
class PurchaseRequisitionLine(models.Model):
    _inherit = 'purchase.requisition.line'
    
    @api.model
    def _default_domain(self):
        context = dict(self.env.context) or {}
        res = super(PurchaseRequisitionLine , self)._default_domain()
        domain = [('company_id','=',self.env.company.id)]
        if context.get('rentals_orders'):
            return domain+[('is_rented', '=', True)]
        return res
    
    is_rental_orders = fields.Boolean(string="Rental Orders", default=False, related='requisition_id.is_rental_orders')
    product_id = fields.Many2one(domain=_default_domain)