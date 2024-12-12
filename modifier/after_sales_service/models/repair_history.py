from odoo import api, fields, models


class RepairHistory(models.Model):
    _name = 'repair.history'
    _description = 'Repair History'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Repair Reference', required=True, copy=False, readonly=True, default='New')

    # Fields for linking to Service Request or Warranty Claim
    service_request_id = fields.Many2one('service.request', string='Service Request')
    warranty_claim_id = fields.Many2one('warranty.claim', string='Warranty Claim')
    origin = fields.Char('Source Document', compute='_compute_origin', store=True)

    # Common fields for tracking repairs
    customer_id = fields.Many2one('res.partner', string='Customer', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    technician_id = fields.Many2one('hr.employee', string='Assigned Technician', readonly=True)
    repair_date = fields.Date('Repair Date', default=fields.Date.today)
    completion_date = fields.Date('Completion Date', readonly=True)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed')
    ], string='State', default='pending', tracking=True)
    repair_type = fields.Selection([
        ('repair', 'Repair'),
        ('replace', 'Replace'),
        ('maintenance', 'Maintenance'),
    ], string='Repair Type')
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

    @api.depends('service_request_id', 'warranty_claim_id')
    def _compute_origin(self):
        for record in self:
            if record.service_request_id:
                record.origin = record.service_request_id.name
            elif record.warranty_claim_id:
                record.origin = record.warranty_claim_id.name
            else:
                record.origin = False

    def action_confirm(self):
        for record in self:
            if record.state == 'pending':
                if record.is_warranty_repair:
                    record.warranty_claim_id.resolution_type = record.repair_type
                else:
                    record.service_request_id.service_type = record.repair_type
                record.state = 'in_progress'

    def action_complete(self):
        for record in self:
            if record.state == 'in_progress':
                record.completion_date = fields.Date.today()
                record.state = 'completed'
                if record.is_warranty_repair:
                    record.warranty_claim_id.state = 'completed'
                    record.warranty_claim_id.resolution_date = fields.Date.today()
                else:
                    record.service_request_id.state = 'completed'
                    record.service_request_id.actual_completion_date = fields.Date.today()
