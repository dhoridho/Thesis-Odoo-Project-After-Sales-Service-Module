from odoo import models, fields, api
from odoo.exceptions import UserError

class ServiceRequest(models.Model):
    _name = 'service.request'
    _description = 'Service Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # General fields
    name = fields.Char('Request Reference', required=True, copy=False, readonly=True, default='New')
    company_id = fields.Many2one('res.company', string="Company", readonly=True, default=lambda self: self.env.company)
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
    portal_type = fields.Selection([
        ('portal', 'Portal Submissions'),
        ('internal', 'Internal Submissions')
    ], string='Submission Type', compute='_compute_portal_type', store=True)

    @api.depends('is_by_portal')
    def _compute_portal_type(self):
        for record in self:
            record.portal_type = 'portal' if record.is_by_portal else 'internal'

            # Status and tracking
    description = fields.Text('Issue Description')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('assign_technician', 'Assign Technician'),
        ('submitted', 'Submitted'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('repair_rejected', 'Repair Rejected'),
    ], string='Status', default='draft', tracking=True)

    technician_id = fields.Many2one('hr.employee', string='Assigned Technician')
    repair_ids = fields.One2many('repair.history', 'service_request_id', string='Repair History')
    repair_count = fields.Integer(
        string='Repair History Count',
        compute='_compute_repair_count'
    )

    # Cancellation fields
    cancel_reason = fields.Selection([
        ('customer_request', 'Customer Request'),
        ('technical_issue', 'Technical Issue'),
        ('parts_unavailable', 'Parts Unavailable'),
        ('cost_concern', 'Cost Concern'),
        ('duplicate_request', 'Duplicate Request'),
        ('out_of_warranty', 'Out of Warranty'),
        ('other', 'Other'),
    ], string='Cancel Reason', readonly=True)

    cancel_notes = fields.Text(string='Cancel Notes', readonly=True)
    cancelled_by = fields.Many2one('res.users', string='Cancelled By', readonly=True)
    cancelled_date = fields.Datetime(string='Cancelled Date', readonly=True)




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
            'context': {'default_service_request_id': self.id},
        }

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
        self.env['repair.history'].sudo().create({
            'partner_id': self.partner_id.id,
            'product_id': self.product_id.id,
            'technician_id': self.technician_id.id,
            'service_request_id': self.id,
            'repair_date': fields.Date.today(),
            'state': 'pending',
        })

    def action_cancel(self):
        """Open cancel wizard instead of direct cancellation"""
        self.ensure_one()

        if self.state in ['completed', 'cancelled']:
            raise UserError('You cannot cancel a request that is already completed or cancelled.')

        return {
            'name': 'Cancel Service Request',
            'type': 'ir.actions.act_window',
            'res_model': 'service.request.cancel.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_service_request_id': self.id,
            }
        }

    def action_force_cancel(self):
        """Direct cancel method (for system use or specific cases)"""
        for record in self:
            if record.state in ['completed', 'cancelled']:
                raise UserError('You cannot cancel a claim that is already completed or cancelled.')

            record.state = 'cancelled'

            # Send email to partner
            template = self.env.ref('after_sales_service.email_template_service_cancel', raise_if_not_found=False)
            if template and record.partner_id.email:
                template.send_mail(record.id, force_send=True)

    def action_reset_to_draft(self):
        for record in self:
            if record.state not in ['cancelled']:
                raise UserError('You can only reset records that are Cancelled.')

            record.state = 'draft'

            # Send reset email
            template = self.env.ref('after_sales_service.email_template_service_reset', raise_if_not_found=False)
            if template and record.partner_id.email:
                template.send_mail(record.id, force_send=True)

    def by_domain_service_request(self):
        user = self.env.user

        # Check if the user is an employee and has the job title "Technician"
        employee = self.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)

        is_manager = user.has_group('after_sales_service.group_customer_service_manager') or user.has_group('after_sales_service.group_technician_manager')

        context = {}
        domain = []
        view_id = self.env.ref("after_sales_service.view_service_request_tree").id
        name = "Service Request"

        if employee and employee.job_id and employee.job_id.name in ['Technician', 'Technician Manager']:
            if employee.job_id.name != 'Technician Manager':
                domain = [('technician_id', '=', employee.id)]
            view_id = self.env.ref("after_sales_service.view_service_request_tree_technician").id
            name = "Service Request Technician"

        elif not is_manager:
            context = {'search_default_own_document': 1}

        return {
            'name': name,
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "tree,form",
            "views": [(view_id, 'tree'), (False, 'form')],  # Define views with IDs
            "domain": domain,
            "context": context,
        }

    # In service_request.py, add:

    def get_portal_url(self, suffix=None, report_type=None, download=None, **kwargs):
        """Generate portal access URL for service requests"""
        self.ensure_one()
        return '/my/service-requests/%s' % self.id

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

