from odoo import api, fields, models


class WarrantyClaim(models.Model):
    _name = 'warranty.claim'
    _description = 'Warranty Claim'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Claim Number', required=True, copy=False, readonly=True, default='New')
    customer_id = fields.Many2one('res.partner', string='Customer', required=True, ondelete='cascade')
    sale_order_id = fields.Many2one('sale.order', string='Related Sale Order')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    claim_date = fields.Date(string='Claim Date', default=fields.Date.today)
    warranty_expiry_date = fields.Date(string='Warranty Expiry Date')
    description = fields.Text(string='Problem Description')

    status = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed')
    ], string='Status', default='draft', tracking=True)

    technician_id = fields.Many2one('hr.employee', string='Assigned Technician')
    repair_ids = fields.One2many('repair.history', 'warranty_claim_id', string='Repair History')
    replacement_product_id = fields.Many2one('product.product', string='Replacement Product')
    resolution_date = fields.Date(string='Resolution Date')

    # New field to indicate whether the resolution was a repair or replacement
    resolution_type = fields.Selection([
        ('repair', 'Repair'),
        ('replace', 'Replace')
    ], string='Resolution Type', tracking=True)

    is_in_warranty = fields.Boolean(string='In Warranty', compute='_compute_is_in_warranty')

    @api.depends('sale_order_id', 'warranty_expiry_date')
    def _compute_is_in_warranty(self):
        for record in self:
            record.is_in_warranty = record.warranty_expiry_date and record.warranty_expiry_date >= fields.Date.today()
