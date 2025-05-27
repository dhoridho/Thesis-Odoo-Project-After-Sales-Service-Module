from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class WarrantyClaim(models.Model):
    _name = 'warranty.claim'
    _description = 'Warranty Claim'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Claim Number', required=True, copy=False, readonly=True, default='New')
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, ondelete='cascade')
    sale_order_id = fields.Many2one('sale.order', string='Related Sale Order', required=True)
    date_order = fields.Datetime(string='Order Date', related='sale_order_id.date_order', store=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    valid_product_ids = fields.Many2many('product.product', compute='_compute_valid_product_ids', store=False)
    claim_date = fields.Date(string='Claim Date', default=fields.Date.today)
    warranty_expiry_date = fields.Date(string='Warranty Expiry Date', compute='_compute_warranty_expiry_date', store=True, readonly=True)
    description = fields.Text(string='Problem Description')
    responsible_id = fields.Many2one(
        'res.users',
        string='Responsible',
        default=lambda self: self._default_responsible_id(),
        readonly=True,
        tracking=True
    )

    def _default_responsible_id(self):
        """Set default responsible only if current user is internal"""
        if self.env.user.has_group('base.group_user'):  # Checks if internal user
            return self.env.user
        return False

    is_by_portal = fields.Boolean('Is by Portal', default=False)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('assign_technician', 'Assign Technician'),
        ('submitted', 'Submitted'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected')
    ], string='Status', default='draft', tracking=True)

    technician_id = fields.Many2one('hr.employee', string='Assigned Technician')
    repair_ids = fields.One2many('repair.history', 'warranty_claim_id', string='Repair History')
    repair_count = fields.Integer(
        string='Repair History Count',
        compute='_compute_repair_count'
    )

    @api.depends('repair_ids')
    def _compute_repair_count(self):
        for record in self:
            record.repair_count = len(record.repair_ids)

    def action_view_repair_history(self):
        return {
            'name': 'Repair History',
            'type': 'ir.actions.act_window',
            'res_model': 'repair.history',  # Replace with actual model name
            'view_mode': 'tree,form',
            'domain': [('service_request_id', '=', self.id)],  # Adjust field name as needed
            'context': {'default_warranty_claim_id': self.id},
        }


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
            'partner_id': self.partner_id.id,
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

        if self.env.user.has_group('base.group_portal'):
            vals.update({
                'is_by_portal': True,
                'responsible_id': False
            })

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

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id and not self.product_id.has_warranty:
            warning = {
                'title': _('Invalid Product'),
                'message': _('The selected product does not have a warranty. Please choose another product.')
            }
            # Clear the product selection
            self.product_id = False
            return {'warning': warning}

    @api.depends('sale_order_id')
    def _compute_valid_product_ids(self):
        for record in self:
            if record.sale_order_id:
                product_ids = record.sale_order_id.order_line.mapped('product_id.id')
                record.valid_product_ids = [(6, 0, product_ids)]
            else:
                record.valid_product_ids = [(6, 0, [])]

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
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


    def by_domain_warranty_claim(self):
        user = self.env.user

        # Check if the user is an employee and has the job title "Technician"
        employee = self.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)

        is_manager = user.has_group('after_sales_service.group_customer_service_manager') or user.has_group(
            'after_sales_service.group_technician_manager')

        domain = []
        context = {}
        view_id = self.env.ref("after_sales_service.view_warranty_claim_tree").id
        name = "Warranty Claims"

        if employee and employee.job_id and employee.job_id.name in ['Technician', 'Technician Manager']:
            if employee.job_id.name != 'Technician Manager':
                domain = [('technician_id', '=', employee.id)]
            view_id = self.env.ref("after_sales_service.view_warranty_claim_tree_technician").id
            name = "Warranty Claims Technician"
        elif not is_manager:
            context = {'search_default_own_document': 1}

        return {
            'name': name,
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "tree,form",
            "views": [(view_id, 'tree'), (False, 'form')],  # Define views with IDs
            "domain": domain,
            'context': context,
        }

    def get_portal_url(self, suffix=None, report_type=None, download=None, **kwargs):
        """Generate portal access URL for warranty claims"""
        self.ensure_one()
        return '/my/warranty-claims/%s' % self.id

    def open_assign_technician_wizard(self):
        """Open the technician assignment wizard"""
        return {
            'name': 'Assign Technician',
            'type': 'ir.actions.act_window',
            'res_model': 'technician.assign.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': self._name,
                'active_id': self.id,
            }
        }