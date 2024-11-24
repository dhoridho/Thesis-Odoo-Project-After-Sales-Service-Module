from odoo import models, fields, api


class ServiceRequest(models.Model):
    _name = 'service.request'
    _description = 'Service Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # General fields
    name = fields.Char('Request Reference', required=True, copy=False, readonly=True, default='New')
    customer_id = fields.Many2one('res.partner', string='Customer', required=True)
    # sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    request_date = fields.Date('Request Date', default=fields.Date.today, required=True)

    # Warranty details
    # warranty_status = fields.Selection([
    #     ('in_warranty', 'In Warranty'),
    #     ('out_warranty', 'Out of Warranty')
    # ], string='Warranty Status', compute='_compute_warranty_status', store=True)

    # Status and tracking
    description = fields.Text('Issue Description')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('done', 'Completed'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    technician_id = fields.Many2one('hr.employee', string='Assigned Technician')
    repair_history_ids = fields.One2many('repair.history', 'service_request_id', string='Repair History')

    @api.model
    def create(self, vals):
        # Auto-generate a unique request reference
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('service.request') or 'New'
        return super(ServiceRequest, self).create(vals)

    # @api.depends('sale_order_id')
    # def _compute_warranty_status(self):
    #     for record in self:
    #         if record.sale_order_id:
    #             # Assuming each sale order has warranty_end_date
    #             warranty_end_date = record.sale_order_id.warranty_end_date
    #             record.warranty_status = 'in_warranty' if warranty_end_date and warranty_end_date >= fields.Date.today() else 'out_warranty'
