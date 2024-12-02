from odoo import models, fields, api
from odoo.exceptions import UserError

class ServiceRequest(models.Model):
    _name = 'service.request'
    _description = 'Service Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # General fields
    name = fields.Char('Request Reference', required=True, copy=False, readonly=True, default='New')
    customer_id = fields.Many2one('res.partner', string='Customer', required=True)
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    request_date = fields.Date('Request Date', default=fields.Date.today, required=True)

    # Status and tracking
    description = fields.Text('Issue Description')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('ready_assign', 'Ready to Assign'),
        ('in_progress', 'In Progress'),
        ('done', 'Completed'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    technician_id = fields.Many2one('hr.employee', string='Assigned Technician')
    repair_history_ids = fields.One2many('repair.history', 'service_request_id', string='Repair History')

    service_type = fields.Selection([
        ('repair', 'Repair'),
        ('maintenance', 'Maintenance'),
        ('inspection', 'Inspection'),
    ], string='Service Type', readonly=True)
    estimated_completion_date = fields.Date(string='Estimated Completion Date')
    actual_completion_date = fields.Date(string='Actual Completion Date')
    feedback = fields.Text(string='Customer Feedback')
    rating = fields.Selection([
        ('1', 'Very Bad'),
        ('2', 'Bad'),
        ('3', 'Neutral'),
        ('4', 'Good'),
        ('5', 'Excellent'),
    ], string='Rating')

    @api.model
    def create(self, vals):
        # Auto-generate a unique request reference
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('service.request') or 'New'
        record = super(ServiceRequest, self).create(vals)
        record._check_ready_to_assign()
        return record

    def write(self, vals):
        result = super(ServiceRequest, self).write(vals)
        self._check_ready_to_assign()
        return result

    def _check_ready_to_assign(self):
        """Automatically change the state to 'ready_assign' if technician_id is not set and the state is draft."""
        for record in self:
            if record.state == 'draft' and not record.technician_id:
                record.state = 'ready_assign'

    def action_submit_order(self):
        if not self.technician_id:
            raise UserError('Please assign a technician before submitting the order.')
        self.ensure_one()
        self.state = 'in_progress'
        self.env['repair.history'].create({
            'customer_id': self.customer_id.id,
            'product_id': self.product_id.id,
            'technician_id': self.technician_id.id,
            'service_request_id': self.id,
            'repair_date': fields.Date.today(),
            'state': 'pending',
        })
