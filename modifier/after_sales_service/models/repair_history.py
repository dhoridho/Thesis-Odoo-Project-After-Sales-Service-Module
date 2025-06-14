from odoo import api, fields, models
from odoo.exceptions import UserError


class RepairHistory(models.Model):
    _name = 'repair.history'
    _description = 'Repair History'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Repair Reference', required=True, copy=False, readonly=True, default='New')
    company_id = fields.Many2one('res.company', string="Company", readonly=True, default=lambda self: self.env.company)

    # Fields for linking to Service Request or Warranty Claim
    service_request_id = fields.Many2one('service.request', string='Service Request')
    warranty_claim_id = fields.Many2one('warranty.claim', string='Warranty Claim')
    origin = fields.Char('Source Document', compute='_compute_origin', store=True)

    # Common fields for tracking repairs
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    technician_id = fields.Many2one('hr.employee', string='Assigned Technician', readonly=True)
    repair_date = fields.Date('Repair Date', default=fields.Date.today)
    completion_date = fields.Date('Completion Date', readonly=True)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('waiting_approval', 'Waiting Approval'),
    ], string='State', default='pending', tracking=True)
    repair_type = fields.Selection([
        ('repair', 'Repair'),
        ('replace', 'Replace'),
        ('maintenance', 'Maintenance'),
    ], string='Repair Type')
    description = fields.Text('Repair Description')

    has_group = fields.Boolean(compute='_compute_has_group')

    # Rejection fields
    reject_reason = fields.Text('Rejection Reason', readonly=True)

    @api.model
    def _compute_has_group(self):
        for record in self:
            record.has_group = self.env.user.has_group('after_sale_service.group_technician')

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
            if not record.repair_type:
                raise UserError('Repair Type is required to be filled.')
            if record.state == 'pending':
                if record.is_warranty_repair:
                    record.warranty_claim_id.resolution_type = record.repair_type
                    record.warranty_claim_id.state = 'in_progress'
                else:
                    record.service_request_id.service_type = record.repair_type
                    record.service_request_id.state = 'in_progress'
                record.state = 'in_progress'

    def action_complete(self):
        for record in self:
            if record.state == 'in_progress':
                record.completion_date = fields.Date.today()
                record.state = 'completed'

                # Update related document
                if record.is_warranty_repair:
                    record.warranty_claim_id.state = 'completed'
                    record.warranty_claim_id.resolution_date = fields.Date.today()
                else:
                    record.service_request_id.state = 'completed'
                    record.service_request_id.actual_completion_date = fields.Date.today()

                # Send email
                template = self.env.ref('after_sales_service.email_template_repair_complete', raise_if_not_found=False)
                if template and record.partner_id.email:
                    template.send_mail(record.id, force_send=True)



    def by_domain_repair_history(self):
        user = self.env.user
        employee = self.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)

        # Manager group check (replace with your actual XML ID)
        is_manager = user.has_group('after_sales_service.group_technician_manager')

        domain = []
        if employee and employee.job_id and employee.job_id.name == 'Technician' and not is_manager:
            domain = [('technician_id.user_id', '=', user.id)]

        return {
            'type': 'ir.actions.act_window',
            'name': 'Repairs & Maintenance',
            'res_model': 'repair.history',
            'view_mode': 'tree,form',
            'domain': domain,
            'context': {},
        }

    def action_reject(self):
        """Open reject wizard"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reject Repair',
            'res_model': 'repair.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_repair_history_id': self.id,
            },
        }
    def action_reset_to_pending(self):
        """Reset rejected repair back to pending"""
        for record in self:
            if record.state in ['rejected', 'waiting_approval']:
                record.write({
                    'state': 'pending',
                })
                # Reset related documents
                if record.is_warranty_repair and record.warranty_claim_id:
                    record.warranty_claim_id.state = 'submitted'
                elif record.service_request_id:
                    record.service_request_id.state = 'submitted'

    def action_confirm_reject(self):
        for record in self:
            if record.state == 'waiting_approval':
                if record.is_warranty_repair and record.warranty_claim_id:
                    record.warranty_claim_id.resolution_type = False
                    record.warranty_claim_id.resolution_date = False
                    record.warranty_claim_id.technician_id = False
                    record.warranty_claim_id.state = 'assign_technician'
                elif record.service_request_id:
                    record.service_request_id.service_type = False
                    record.service_request_id.technician_id = False
                    record.service_request_id.state = 'assign_technician'
                record.state = 'rejected'

    @api.onchange('repair_type')
    def _onchange_repair_type(self):
        if self.service_request_id and self.repair_type == 'replace':
            raise UserError('Repair Type cannot be "Replace" for Service Requests.')




class RepairRejectWizard(models.TransientModel):
    _name = 'repair.reject.wizard'
    _description = 'Repair Reject Wizard'

    repair_history_id = fields.Many2one('repair.history', string='Repair History', required=True)
    reject_reason = fields.Text('Rejection Reason', required=True,
                                help="Please provide a reason for rejecting this repair request")

    # Additional fields for better tracking
    reject_date = fields.Date('Rejection Date', default=fields.Date.today, readonly=True)
    rejected_by = fields.Many2one('res.users', string='Rejected By',
                                  default=lambda self: self.env.user, readonly=True)

    def action_reject_repair(self):
        """Process the repair rejection"""
        self.ensure_one()

        repair = self.repair_history_id

        # Validate that repair can be rejected
        if repair.state not in ['pending', 'in_progress']:
            raise UserError("Only pending or in-progress repairs can be rejected.")

        # Update repair history
        repair.write({
            'state': 'waiting_approval',
            'reject_reason': self.reject_reason,
        })

        # Update related service request or warranty claim
        if repair.is_warranty_repair and repair.warranty_claim_id:
            repair.warranty_claim_id.write({
                'state': 'repair_rejected',
            })
            repair.warranty_claim_id.message_post(
                body=f"Reject Reason: {self.reject_reason}<br/>Waiting for Technician Manager to respond",
                subtype_xmlid='mail.mt_note'
            )
        elif repair.service_request_id:
            repair.service_request_id.write({
                'state': 'repair_rejected',
            })
            repair.service_request_id.message_post(
                body=f"Reject Reason: {self.reject_reason}<br/>Waiting for Technician Manager to respond",
                subtype_xmlid='mail.mt_note'
            )

        # Post message to chatter
        repair.message_post(
            body=f"Repair rejected by {self.rejected_by.name}.<br/>Reason: {self.reject_reason}",
            subtype_xmlid='mail.mt_note'
        )


        return {
            'type': 'ir.actions.act_window_close'
        }


