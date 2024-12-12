from odoo import api, fields, models
from odoo.exceptions import UserError

class WarrantyClaim(models.Model):
    _name = 'warranty.claim'
    _description = 'Warranty Claim'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Claim Number', required=True, copy=False, readonly=True, default='New')
    customer_id = fields.Many2one('res.partner', string='Customer', required=True, ondelete='cascade')
    sale_order_id = fields.Many2one('sale.order', string='Related Sale Order', required=True)
    date_order = fields.Datetime(string='Order Date', related='sale_order_id.date_order', store=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    valid_product_ids = fields.Many2many('product.product', compute='_compute_valid_product_ids', store=False)
    claim_date = fields.Date(string='Claim Date', default=fields.Date.today)
    warranty_expiry_date = fields.Date(string='Warranty Expiry Date', compute='_compute_warranty_expiry_date', store=True, readonly=True)
    description = fields.Text(string='Problem Description')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('assign_technician', 'Assign Technician'),
        ('submitted', 'Submitted'),
        ('rejected', 'Rejected'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed')
    ], string='Status', default='draft', tracking=True)

    technician_id = fields.Many2one('hr.employee', string='Assigned Technician')
    repair_ids = fields.One2many('repair.history', 'warranty_claim_id', string='Repair History')
    replacement_product_id = fields.Many2one('product.product', string='Replacement Product')
    resolution_date = fields.Date(string='Resolution Date')
    resolution_type = fields.Selection([
        ('repair', 'Repair'),
        ('maintenance', 'Maintenance'),
        ('replace', 'Replace')
    ], string='Resolution Type', tracking=True)
    is_in_warranty = fields.Boolean(string='In Warranty', compute='_compute_is_in_warranty', readonly=True, store=True)

    def action_submit_order(self):
        self.ensure_one()
        if not self.technician_id:
            raise UserError('Please assign a technician before submitting the order.')
        self.state = 'submitted'
        self.env['repair.history'].create({
            'customer_id': self.customer_id.id,
            'product_id': self.product_id.id,
            'technician_id': self.technician_id.id,
            'warranty_claim_id': self.id,
            'repair_date': fields.Date.today(),
            'state': 'pending',
        })

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('warranty.claim') or 'New'
            record = super(WarrantyClaim, self).create(vals)
            record._check_ready_to_assign()
        return record

    def write(self, vals):
        result = super(WarrantyClaim, self).write(vals)
        self._check_ready_to_assign()
        return result

    @api.depends('sale_order_id', 'warranty_expiry_date')
    def _compute_is_in_warranty(self):
        for record in self:
            record.is_in_warranty = record.warranty_expiry_date and record.warranty_expiry_date >= fields.Date.today()

    @api.depends('sale_order_id', 'product_id')
    def _compute_warranty_expiry_date(self):
        for record in self:
            if record.sale_order_id:
                sale_order_line = self.env['sale.order.line'].search(
                    [('order_id', '=', record.sale_order_id.id), ('product_id', '=', record.product_id.id)], limit=1)
                record.warranty_expiry_date = sale_order_line.warranty_expire_date if sale_order_line else False
            else:
                record.warranty_expiry_date = False

    @api.depends('sale_order_id')
    def _compute_valid_product_ids(self):
        for record in self:
            if record.sale_order_id:
                product_ids = record.sale_order_id.order_line.mapped('product_id.id')
                record.valid_product_ids = [(6, 0, product_ids)]
            else:
                record.valid_product_ids = [(6, 0, [])]

    @api.onchange('customer_id')
    def _onchange_customer_id(self):
        self.sale_order_id = False
        self.product_id = False
        self.warranty_expiry_date = False

    @api.onchange('sale_order_id')
    def _onchange_sale_order_id(self):
        self.product_id = False
        self.warranty_expiry_date = False

    def _check_ready_to_assign(self):
        """Automatically change the state to 'ready_assign' if technician_id is not set and the state is draft."""
        for record in self:
            if record.state == 'draft' and not record.technician_id:
                record.state = 'assign_technician'
