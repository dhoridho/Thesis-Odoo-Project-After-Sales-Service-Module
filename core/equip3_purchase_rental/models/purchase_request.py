
from odoo import api, fields, models, _


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'
    
    is_rental_orders = fields.Boolean(string="Rental Orders", default=False)
    rent_duration = fields.Integer(string='Rent Duration')
    rent_duration_unit = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ('years', 'Years')
    ],string="Single Rent Duration")
        
    @api.model
    def create(self, vals):
        context = dict(self.env.context) or {}
        res = super(PurchaseRequest , self).create(vals)
        if context.get('default_is_rental_orders') or res.is_rental_orders:
            res.name = self.env['ir.sequence'].next_by_code('purchase.request.seqs.r')
        return res
    
    @api.depends('branch_id', 'company_id', 'department_id')
    def _compute_approval_matrix_request(self):
        is_pr_department = self.env['ir.config_parameter'].sudo().get_param('is_pr_department', False)
        res = super(PurchaseRequest, self)._compute_approval_matrix_request()
        for record in self:
            if record.is_rental_orders and record.is_approval_matrix_request and is_pr_department:
                approval_matrix_id = self.env['approval.matrix.purchase.request'].search([
                        ('branch_id', '=', record.branch_id.id), 
                        ('company_id', '=', record.company_id.id),
                        ('department_id', '=', record.department_id.id),
                        ('order_type', '=', "rental_order")], limit=1)
                record.approval_matrix_id = approval_matrix_id and approval_matrix_id.id or False
            elif record.is_rental_orders and record.is_approval_matrix_request:
                approval_matrix_id = self.env['approval.matrix.purchase.request'].search([
                        ('branch_id', '=', record.branch_id.id), 
                        ('company_id', '=', record.company_id.id),
                        ('order_type', '=', "rental_order")], limit=1)
                record.approval_matrix_id = approval_matrix_id and approval_matrix_id.id or False
        return res
    
class PurchaseRequestLine(models.Model):
    _inherit ='purchase.request.line'
    
    @api.model
    def _default_domain(self):
        context = dict(self.env.context) or {}
        res = super(PurchaseRequestLine, self)._default_domain()
        domain = [('company_id','=',self.env.company.id)]
        if context.get('rentals_orders'):
            return domain+[('is_rented', '=', True)]
        return res

    is_rental_orders = fields.Boolean(string="Rental Orders", default=False, related='request_id.is_rental_orders')
    product_id = fields.Many2one(domain=_default_domain, required=True)