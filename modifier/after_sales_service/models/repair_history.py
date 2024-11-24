from odoo import api, fields, models


class RepairHistory(models.Model):
    _name = 'repair.history'
    _description = 'Repair History'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Repair Reference', required=True, copy=False, readonly=True, default='New')

    # Fields for linking to Service Request or Warranty Claim
    service_request_id = fields.Many2one('service.request', string='Service Request')
    warranty_claim_id = fields.Many2one('warranty.claim', string='Warranty Claim')

    # Common fields for tracking repairs
    customer_id = fields.Many2one('res.partner', string='Customer', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    technician_id = fields.Many2one('hr.employee', string='Assigned Technician', required=True)
    repair_date = fields.Date('Repair Date', default=fields.Date.today)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed')
    ], string='Status', default='pending', tracking=True)
    description = fields.Text('Repair Description')

    # Field to indicate if this is a warranty repair
    is_warranty_repair = fields.Boolean(string='Warranty Repair', compute='_compute_is_warranty_repair', store=True)

    @api.depends('warranty_claim_id')
    def _compute_is_warranty_repair(self):
        for record in self:
            record.is_warranty_repair = bool(record.warranty_claim_id)

    @api.model
    def create(self, vals):
        # Generate a unique Repair Reference
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('repair.history') or 'New'
        return super(RepairHistory, self).create(vals)
