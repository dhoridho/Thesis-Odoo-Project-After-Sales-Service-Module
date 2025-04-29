from odoo import models, fields, api
from odoo.exceptions import UserError

class ServiceRequest(models.Model):
    _name = 'service.request'
    _description = 'Service Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # General fields
    name = fields.Char('Request Reference', required=True, copy=False, readonly=True, default='New')
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    request_date = fields.Date('Request Date', default=fields.Date.today, required=True)
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

    # Status and tracking
    description = fields.Text('Issue Description')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('assign_technician', 'Assign Technician'),
        ('submitted', 'Submitted'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    technician_id = fields.Many2one('hr.employee', string='Assigned Technician')
    repair_history_ids = fields.One2many('repair.history', 'service_request_id', string='Repair History')

    service_type = fields.Selection([
        ('repair', 'Repair'),
        ('maintenance', 'Maintenance'),
        ('replace', 'Replace'),
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

    request_month = fields.Char(
        string="Request Month",
        compute="_compute_request_month",
        store=True,
        index=True
    )

    @api.depends('request_date')
    def _compute_request_month(self):
        for record in self:
            if record.request_date:
                record.request_month = record.request_date.strftime('%Y-%m')
            else:
                record.request_month = False

    @api.model
    def create(self, vals):
        # Auto-generate a unique request reference
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('service.request') or 'New'

        if self.env.user.has_group('base.group_portal'):
            vals.update({
                'is_by_portal': True,
                'responsible_id': False
            })

        record = super(ServiceRequest, self).create(vals)
        record._check_ready_to_assign()
        return record

    def write(self, vals):
        result = super(ServiceRequest, self).write(vals)
        self._check_ready_to_assign()
        return result

    def _check_ready_to_assign(self):
        for record in self:
            if record.state == 'draft' and not record.technician_id:
                record.state = 'assign_technician'

    def action_submit_order(self):
        if not self.technician_id:
            raise UserError('Please assign a technician before submitting the order.')
        self.ensure_one()
        self.state = 'submitted'
        self.env['repair.history'].create({
            'partner_id': self.partner_id.id,
            'product_id': self.product_id.id,
            'technician_id': self.technician_id.id,
            'service_request_id': self.id,
            'repair_date': fields.Date.today(),
            'state': 'pending',
        })

    def by_domain_service_request(self):
        user = self.env.user

        # Check if the user is an employee and has the job title "Technician"
        employee = self.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)

        if employee and employee.job_id and employee.job_id.name == 'Technician':
            domain = [('technician_id', '=', employee.id)]  # Match technician_id with the employee's ID
            view_id = self.env.ref("after_sales_service.view_service_request_tree_technician").id
        else:
            domain = []
            view_id = self.env.ref("after_sales_service.view_service_request_tree").id

        return {
            'name': 'Service Request Technician' if employee.job_id.name == 'Technician' else 'Service Request',
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "tree,form",
            "views": [(view_id, 'tree'), (False, 'form')],  # Define views with IDs
            "domain": domain
        }

    # In service_request.py, add:

    def get_portal_url(self, suffix=None, report_type=None, download=None, **kwargs):
        """Generate portal access URL for service requests"""
        self.ensure_one()
        return '/my/service-requests/%s' % self.id