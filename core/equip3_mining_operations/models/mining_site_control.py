from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MiningSiteControl(models.Model):
    _name = 'mining.site.control'
    _description = 'Mining Site Control'
    _inherit = 'mail.thread'
    _rec_name = 'mining_site'

    @api.model
    def _default_approval_matrix(self, company=None, branch=None):
        if not company:
            company = self.env.company
        if not company.mining_site:
            return False

        default = self.env.context.get('default_approval_matrix_id', False)
        if default:
            return default

        if not branch:
            branch = self.env.user.branch_id
        return self.env['mining.approval.matrix'].search([
            ('company_id', '=', company.id),
            ('branch_id', '=', branch.id),
            ('matrix_type', '=', 'msc')
        ], limit=1).id

    @api.model
    def _default_analytic_tag_ids(self):
        user = self.env.user
        analytic_priority = self.env['analytic.priority'].sudo().search([], limit=1, order='priority')
        analytic_tag_ids = []
        if analytic_priority.object_id == 'user' and user.analytic_tag_ids:
            analytic_tag_ids = user.analytic_tag_ids.ids
        elif analytic_priority.object_id == 'branch' and user.branch_id and user.branch_id.analytic_tag_ids:
            analytic_tag_ids = user.branch_id.analytic_tag_ids.ids
        elif analytic_priority.object_id == 'product_category':
            product_category = self.env['product.category'].sudo().search([('analytic_tag_ids', '!=', False)], limit=1)
            analytic_tag_ids = product_category.analytic_tag_ids.ids
        return [(6, 0, analytic_tag_ids)]

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id', False)
        if default_branch_id:
            return default_branch_id
        return self.env.branch.id if len(self.env.branches) == 1 else False

    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids)]

    @api.depends('approval_matrix_id', 'is_matrix_on')
    def _compute_approval_matrix_lines(self):
        for record in self:
            lines = []
            if record.is_matrix_on:
                for line in record.approval_matrix_id.line_ids:
                    lines += [(0, 0, {
                        'msc_id': record.id,
                        'line_id': line.id,
                        'sequence': line.sequence,
                        'minimum_approver': line.minimum_approver,
                        'approver_ids': [(6, 0, line.approver_ids.ids)]
                    })]
            record.approval_matrix_line_ids = lines

    @api.depends('approval_matrix_line_ids', 'approval_matrix_line_ids.need_action_ids', 'is_matrix_on')
    def _compute_user_is_approver(self):
        user = self.env.user
        for record in self:
            need_action_ids = record.approval_matrix_line_ids.mapped('need_action_ids')
            record.user_is_approver = user in need_action_ids and record.is_matrix_on

    mining_site = fields.Char('Mining Site Name', tracking=True)

    # to delete
    site_location = fields.Many2one('stock.location','Site Location', tracking=True)
    
    ppic = fields.Many2one('res.users', 'PPIC', tracking=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company,tracking=True)
    is_branch_required = fields.Boolean(related='company_id.show_branch')
    branch_id = fields.Many2one('res.branch', string='Branch', default=_default_branch, domain=_domain_branch, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_be_approved', 'To be Approved'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('confirmed', 'Confirmed'),
        ('progress', 'In Progress'),
        ('to_close', 'To Close'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='State', default='draft', tracking=True)

    state_reject = fields.Selection([
        ('draft', 'Draft'),
        ('rejected', 'Rejected'),
        ('progress', 'In Progress'),
        ('done', 'Done'),
    ])

    site_code = fields.Char(string='Site Code')
    
    analytic_group_ids = fields.Many2many(
        comodel_name='account.analytic.tag', 
        domain="[('company_id', '=', company_id)]", 
        string="Analytic Group", 
        readonly=True, 
        states={'draft': [('readonly', False)]}, 
        default=_default_analytic_tag_ids,
        tracking=True)
    
    approval_matrix_id = fields.Many2one(
        comodel_name='mining.approval.matrix', 
        domain="[('matrix_type', '=', 'msc')]",
        string='Approval Matrix', 
        default=_default_approval_matrix)

    approval_matrix_line_ids = fields.One2many(
        comodel_name='mining.approval.matrix.entry',
        inverse_name='msc_id',
        string='Approval Matrix Lines',
        compute=_compute_approval_matrix_lines,
        store=True)
    
    operation_ids = fields.One2many('mining.operations.two', 'site_id', string='Operations', readonly=True)

    product_mining_site_control_ids = fields.One2many(
        comodel_name='product.mining.site', 
        inverse_name='mining_site_control_id', 
        string='Product Mining Site Control')

    is_matrix_on = fields.Boolean(related='company_id.mining_site')
    user_is_approver = fields.Boolean(compute=_compute_user_is_approver)

    @api.constrains('mining_site')
    def _constrains_mining_site(self):
        for record in self:
            if self.search([('mining_site', '=', record.mining_site), ('id', '!=', record.id)]):
                raise ValidationError(_('There cannot be 2 mining site with the same name!'))

    @api.onchange('company_id', 'branch_id')
    def onchange_company_branch(self):
        if not self.company_id or not self.branch_id:
            self.approval_matrix_id = False
            return
        self.approval_matrix_id = self._default_approval_matrix(company=self.company_id, branch=self.branch_id)

    def action_approval(self):
        for record in self:
            if not record.is_matrix_on:
                continue
            options = {
                'post_log': True,
                'send_system': True,
                'send_email': True,
                'send_whatsapp': record.company_id.mining_site_wa_notif
            }
            record.approval_matrix_id.action_approval(record, options=options)
            record.write({'state': 'to_be_approved'})

    def action_approve(self):
        for record in self:
            if not record.is_matrix_on:
                continue
            record.approval_matrix_id.action_approve(record)
            if all(l.state == 'approved' for l in record.approval_matrix_line_ids):
                record.write({'state': 'approved'})

    def action_reject(self, reason=False):
        for record in self:
            if not record.is_matrix_on:
                continue
            result = record.approval_matrix_id.action_reject(record, reason=reason)
            if result is not True:
                return result
            if any(l.state == 'rejected' for l in record.approval_matrix_line_ids):
                record.write({'state': 'rejected'})

    def action_confirm(self):
        self.state = 'confirmed'

    def action_cancel(self):
        self.state = 'cancel'
