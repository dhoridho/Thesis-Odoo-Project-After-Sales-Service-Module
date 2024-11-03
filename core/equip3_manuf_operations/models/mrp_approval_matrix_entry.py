from odoo import api, fields, models, _


class MrpApprovalMatrixEntry(models.Model):
    _name = 'mrp.approval.matrix.entry'
    _description = 'MRP Approval Matrix Entry'
    
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

    mp_id = fields.Many2one(comodel_name='mrp.plan', string='Production Plan')
    mo_id = fields.Many2one(comodel_name='mrp.production', string='Production Order')

    line_id = fields.Many2one(comodel_name='mrp.approval.matrix.line', required=True, string='Approval Matrix Line')
    matrix_type = fields.Selection(related='line_id.matrix_type')

    sequence = fields.Integer(string='Sequence')
    minimum_approver = fields.Integer(string='Minimum Approver')
    approver_ids = fields.Many2many(comodel_name='res.users', string='Approver')
    requested_id = fields.Many2one(comodel_name='res.users', string='Requested User')
    requested_time = fields.Datetime(string='Requested Time')

    line_ids = fields.One2many(
        comodel_name='mrp.approval.matrix.entry.line', 
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


class MrpApprovalMatrixEntry(models.Model):
    _name = 'mrp.approval.matrix.entry.line'
    _description = 'MRP Approval Matrix Entry Line'

    entry_id = fields.Many2one(
        comodel_name='mrp.approval.matrix.entry',
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
    reason_id = fields.Many2one(comodel_name='mrp.approval.matrix.entry.reason', string='Reason')


class MrpApprovalMatrixReason(models.Model):
    _name = 'mrp.approval.matrix.entry.reason'
    _description = 'MRP Approval Matrix Entry Reason'

    name = fields.Char(required=True, string='Reason')

    _sql_constraints = [('name_unique', 'unique(name)', _('Reason already Exist!'))]
