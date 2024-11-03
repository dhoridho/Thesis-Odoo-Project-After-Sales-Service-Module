from odoo import api, fields, models
from odoo.exceptions import ValidationError

class ApprovalMatrixMp(models.Model):
    _name = 'approval.matrix.mp'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Maintenance Plan Approval Matrix'

    _sql_constraints = [ ('branch_id_unique', 'UNIQUE (branch_id)', 'There is already an Approval Matrix for this Branch, please select other branch'), ]

    name = fields.Char(string='Name', required=True)
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.user.company_id, readonly=True)
    branch_id = fields.Many2one('res.branch', string='Branch', required=True, default=lambda self: self.env.branches if len(self.env.branches) == 1 else False,
        domain=lambda self: [('id', 'in', self.env.branches.ids)])
    approval_matrix_mp_ids = fields.One2many('approval.matrix.mp.line', 'approval_matrix_mp_id', string='Approval')

    @api.model
    def create(self, vals):
        res = super(ApprovalMatrixMp, self).create(vals)
        res._check_approval_matrix_line()
        return res

    def write(self, vals):
        res = super(ApprovalMatrixMp, self).write(vals)
        self._check_approval_matrix_line()
        return res

    def _check_approval_matrix_line(self):
        for line in self.approval_matrix_mp_ids:
            if line.min_approvers > len(line.user_ids) or line.min_approvers <= 0:
                raise ValidationError('Please make sure the minimum approvers not more than the user on approval line or value less than 1.')

class ApprovalMatrixMpLine(models.Model):
    _name = 'approval.matrix.mp.line'
    _description = 'Approval Matrix Mp Line'
    _order = 'sequence,id'

    approval_matrix_mp_id = fields.Many2one('approval.matrix.mp', string='Approval Matrix Maitnenance Plan')
    sequence = fields.Integer(string='Sequence')
    name = fields.Char(string='No', compute='_compute_name')
    user_ids = fields.Many2many('res.users', string='Approver', required=True)
    min_approvers = fields.Integer(string='Minimum Approvers', default=1)

    @api.depends('sequence')
    def _compute_name(self):
        for rec in self:
            rec.name = str(rec.sequence+1)
