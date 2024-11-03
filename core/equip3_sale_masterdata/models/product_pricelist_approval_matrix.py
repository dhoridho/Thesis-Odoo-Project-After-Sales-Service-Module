from odoo import models, fields, api, _


class ProductPricelistApprovalMatrix(models.Model):
    _name = 'product.pricelist.approval.matrix'
    _description = 'Product Pricelist Approval Matrix'
    _inherit = 'mail.thread'

    name = fields.Char(string='Name', required=True, copy=False, tracking=True)
    company_id = fields.Many2one(
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.company, 
        readonly=True,
        copy=False,
        string='Company'
    )
    
    branch_id = fields.Many2one(
        comodel_name='res.branch',
        default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, 
        domain=lambda self: [('id', 'in', self.env.branches.ids)],
        copy=False,
        string='Branch',
        required=True, 
        tracking=True)
    
    line_ids = fields.One2many('product.pricelist.approval.matrix.line', 'matrix_id',  string='Approval Lines')

    _sql_constraints = [
        ('unique_product_pricelist_approval_matrix', 'unique(company_id, branch_id)', 'The branch already used for another Approval Matrix. Please choose another branch.')
    ]


class ProductPricelistApprovalMatrixLine(models.Model):
    _name = 'product.pricelist.approval.matrix.line'
    _description = 'Product Pricelist Approval Matrix Line'

    @api.depends('matrix_id', 'matrix_id.line_ids', 'matrix_id.line_ids.approver_ids')
    def _compute_added_approvers(self):
        for record in self:
            added_approvers = record.matrix_id.line_ids.mapped('approver_ids')
            record.added_approver_ids = [(6, 0, added_approvers.ids)]

    @api.depends('matrix_id', 'matrix_id.line_ids')
    def _compute_sequence(self):
        for record in self:
            lines = record.matrix_id.line_ids
            for sequence, line in enumerate(lines):
                line.sequence = sequence + 1

    matrix_id = fields.Many2one('product.pricelist.approval.matrix', 'Approval Matrix')

    sequence = fields.Integer('Sequence', compute=_compute_sequence)
    sequence_handle = fields.Integer('Sequence Handle')
    
    # cannot add same approver on diffrent line 
    added_approver_ids = fields.Many2many('res.users', compute=_compute_added_approvers)
    approver_ids = fields.Many2many('res.users', string='Approver', domain="[('id', 'not in', added_approver_ids)]")
    
    minimum_approver = fields.Integer('Minimum Approver', default=1, required=True)


class ProductPricelistApprovalEntry(models.Model):
    _name = 'product.pricelist.approval.entry'
    _description = 'Product Pricelist Approval Entry'
    
    @api.depends('line_ids', 'line_ids.approver_id', 'line_ids.state', 'minimum_approver')
    def _compute_fields(self):
        for record in self:
            line_ids = record.line_ids
            approved_lines = line_ids.filtered(lambda l: l.state == 'approved')
            rejected_lines = line_ids.filtered(lambda l: l.state == 'rejected')

            approver_ids = line_ids.mapped('approver_id').ids
            approved_ids = approved_lines.mapped('approver_id').ids
            rejected_ids = rejected_lines.mapped('approver_id').ids

            need_action_ids = [
                approver for approver in approver_ids
                if approver not in approved_ids + rejected_ids
            ]

            state = 'draft'
            if line_ids:
                if rejected_lines:
                    state = 'rejected'
                elif approved_lines and len(approved_lines) >= record.minimum_approver:
                    state = 'approved'
                elif any(line.state == 'to_approve' for line in line_ids):
                    state = 'to_approve'

            record.write({
                'approved_ids': [(6, 0, approved_ids)],
                'rejected_ids': [(6, 0, rejected_ids)],
                'need_action_ids': [(6, 0, need_action_ids)],
                'state': state
            })

    @api.depends('line_ids', 'line_ids.note')
    def _compute_description(self):
        for record in self:
            line_ids = record.line_ids
            record.description = '\n'.join(['- %s' % line.note for line in line_ids if line.note])

    pricelist_request_id = fields.Many2one(comodel_name='product.pricelist.request', string='Priceist Request')

    line_id = fields.Many2one(comodel_name='product.pricelist.approval.matrix.line', required=False, string='Approval Matrix Line')

    sequence = fields.Integer(string='Sequence')
    minimum_approver = fields.Integer(string='Minimum Approver')
    approver_ids = fields.Many2many(comodel_name='res.users', string='Approver')
    requested_id = fields.Many2one(comodel_name='res.users', string='Requested User')
    requested_time = fields.Datetime(string='Requested Time')

    line_ids = fields.One2many(
        comodel_name='product.pricelist.approval.entry.line', 
        inverse_name='entry_id',
        string='Approver Lines')

    approved_ids = fields.Many2many(
        comodel_name='res.users',
        string='Approved By',
        compute=_compute_fields)
    rejected_ids = fields.Many2many(
        comodel_name='res.users',
        string='Rejected By',
        compute=_compute_fields)
    need_action_ids = fields.Many2many(
        comodel_name='res.users',
        string='Need Action',
        compute=_compute_fields
    )

    description = fields.Text(string='Approval Status', compute=_compute_description)

    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('to_approve', 'To Approve'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected')
        ], 
        compute=_compute_fields,
        string='Status')


class ProductPricelistApprovalEntryLine(models.Model):
    _name = 'product.pricelist.approval.entry.line'
    _description = 'Product Pricelist Approval Entry Line'

    entry_id = fields.Many2one(
        comodel_name='product.pricelist.approval.entry',
        required=True,
        ondelete='cascade',
        copy=False,
        string='Entry')

    approver_id = fields.Many2one(
        comodel_name='res.users', 
        string='Approver')

    action_time = fields.Datetime(string='Approved/Rejected Time')

    state = fields.Selection(
        selection=[
            ('to_approve', 'To Approve'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected')
        ],
        string='Status'
    )

    note = fields.Text(string='Notes')
    reason_id = fields.Many2one(comodel_name='product.pricelist.approval.entry.reason', string='Reason')


class ProductPricelistApprovalEntryReason(models.Model):
    _name = 'product.pricelist.approval.entry.reason'
    _description = 'Product Pricelist Approval Entry Reason'

    name = fields.Char(required=True, string='Reason')

    _sql_constraints = [('name_unique', 'unique(name)', _('Reason already Exist!'))]
