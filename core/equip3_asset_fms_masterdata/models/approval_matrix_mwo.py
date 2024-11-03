from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import ValidationError

class ApprovalMatrixMwo(models.Model):
    _name = 'approval.matrix.mwo'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Maintenance Work Order Approval Matrix'

    _sql_constraints = [ ('branch_id_unique', 'UNIQUE (branch_id, state)', 'There is already an Approval Matrix for this Stages, please select other stages'), ]

    name = fields.Char(string="Name", required=True)
    company_id = fields.Many2one("res.company", "Company", default=lambda self: self.env.user.company_id, readonly=True)
    branch_id = fields.Many2one('res.branch', string='Branch', required=True,default=lambda self: self.env.branches if len(self.env.branches) == 1 else False,
        domain=lambda self: [('id', 'in', self.env.branches.ids)])
    created_date = fields.Date(string='Create On', default=datetime.today().date(), readonly=True)
    user_id = fields.Many2one('res.users', 'Created By', required=True, readonly=True, default=lambda self: self.env.user)
    approval_matrix_mwo_ids = fields.One2many('approval.matrix.mwo.line', 'approval_matrix_mwo_id', string='Approval')
    state = fields.Selection([('in_progress', 'In Progress'),
        ('pending', 'Post'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], string="Stages", default='in_progress', required=True)

    # @api.onchange('approval_matrix_mwo_ids')
    # def _check_double_state(self):
    #     mapped_state = self.approval_matrix_mwo_ids.mapped('state_id')
    #     newlist = []
    #     for x in mapped_state:
    #         if x not in newlist:
    #             newlist.append(x)
    #         else:
    #             raise ValidationError('You cannot select double Status')

    @api.model
    def create(self, vals):
        res = super(ApprovalMatrixMwo, self).create(vals)
        #print (res, '00000')
        res._check_approval_matrix_line()
        return res

    def write(self, vals):
        res = super(ApprovalMatrixMwo, self).write(vals)
        #print(res, '00000')
        self._check_approval_matrix_line()
        return res

    def _check_approval_matrix_line(self):
        set_of_valid_state = set(['in_progress', 'pending', 'done', 'cancel'])
        # mapped_state = self.approval_matrix_mwo_ids.mapped('state_id')
        # if 'draft' in mapped_state: mapped_state.remove('draft')

        if len(self.approval_matrix_mwo_ids) < 1:
            raise ValidationError('You Have to Fill User and Minimum Approver in Line')


        if 0 in self.approval_matrix_mwo_ids.mapped('min_approvers'):
            raise ValidationError('Please make sure the minimum approvers not more than the user on approval line or value less than 1.')

        for line in self.approval_matrix_mwo_ids:
            if line.min_approvers > len(line.user_ids):
                raise ValidationError('Please make sure the minimum approvers not more than the user on approval line or value less than 1.')

class ApprovalMatrixMwoLine(models.Model):
    _name = 'approval.matrix.mwo.line'
    _description = 'Approval Matrix Mwo Line'

    @api.model
    def default_get(self, fields):
        res = super(ApprovalMatrixMwoLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'approval_matrix_mwo_ids' in context_keys:
                if len(self._context.get('approval_matrix_mwo_ids')) > 0:
                    next_sequence = len(self._context.get('approval_matrix_mwo_ids')) + 1
            res.update({'sequence': next_sequence})
        return res

    sequence = fields.Integer(string="Sequence")
    approval_matrix_mwo_id = fields.Many2one('approval.matrix.mwo')
    user_ids = fields.Many2many(comodel_name='res.users', string='User', required=True)
    min_approvers = fields.Integer(string='Minimum Approvers', required=True, default=1)
    approved = fields.Boolean(string="approved")
    last_approved = fields.Many2one('res.users', string='Users')
