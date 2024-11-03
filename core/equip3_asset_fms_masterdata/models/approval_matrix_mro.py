from odoo import api, fields, models
from datetime import datetime
from odoo.exceptions import ValidationError

class ApprovalMatrixMro(models.Model):
    _name = 'approval.matrix.mro'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Maintenance Repair Order Approval Matrix'

    _sql_constraints = [ ('branch_id_unique','UNIQUE (branch_id, state)', 'here is already an Approval Matrix for this Stages, please select other stages '), ]

    name = fields.Char(string="Name", required=True)
    company_id = fields.Many2one("res.company", "Company", default=lambda self: self.env.user.company_id, readonly=True)
    branch_id = fields.Many2one('res.branch', string='Branch', required=True,default=lambda self: self.env.branches if len(self.env.branches) == 1 else False,
        domain=lambda self: [('id', 'in', self.env.branches.ids)])
    created_date = fields.Date(string='Create On', default=datetime.today().date(), readonly=True)
    user_id = fields.Many2one('res.users', 'Created By', required=True, readonly=True, default=lambda self: self.env.user)
    min_amount = fields.Float(string='Minimum Amount', required=True)
    max_amount = fields.Float(string='Maximum Amount', required=True)
    approval_matrix_mro_ids = fields.One2many('approval.matrix.mro.line', 'approval_matrix_mro_id', string='Approval')
    state = fields.Selection([('in_progress', 'In Progress'),
        ('pending', 'Post'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], string="Stages", default='in_progress', required=True)

    @api.model
    def create(self, vals):
        res = super(ApprovalMatrixMro, self).create(vals)
        res._check_approval_matrix_line()
        return res

    def write(self, vals):
        res = super(ApprovalMatrixMro, self).write(vals)
        self._check_approval_matrix_line()
        return res

    # @api.constrains('branch_id', 'min_amount', 'max_amount')
    # def _check_existing_record(self):
    #     for record in self:
    #         if record.branch_id:
    #             approval_matrix_id = self.search([('branch_id', '=', record.branch_id.id), ('id', '!=', record.id), '|', '|',
    #                                             '&', ('min_amount', '<=', record.min_amount), ('max_amount', '>=', record.min_amount),
    #                                             '&', ('min_amount', '<=', record.max_amount), ('max_amount', '>=', record.max_amount),
    #                                             '&', ('min_amount', '>=', record.min_amount), ('max_amount', '<=', record.max_amount)], limit=1)
    #             if approval_matrix_id:
    #                 raise ValidationError("The minimum and maximum range of this approval matrix is intersects with other approval matrix [%s] in same branch. Please change the minimum and maximum range" % (approval_matrix_id.name))


    def _check_approval_matrix_line(self):
        set_of_valid_state = set(['in_progress', 'pending', 'done', 'cancel'])
        # mapped_state = self.approval_matrix_mro_ids.mapped('state_id')
        # if 'draft' in mapped_state: mapped_state.remove('draft')

        # if set_of_valid_state != set(mapped_state):
        #     raise ValidationError('Please fill all state for Approval Matrix')
        if len(self.approval_matrix_mro_ids) < 1:
            raise ValidationError('You Have to Fill User and Minimum Approver in Line')

        if 0 in self.approval_matrix_mro_ids.mapped('min_approvers'):
            raise ValidationError('Please make sure the minimum approvers not more than the user on approval line or value less than 1.')

        for line in self.approval_matrix_mro_ids:
            if line.min_approvers > len(line.user_id):
                raise ValidationError('Please make sure the minimum approvers not more than the user on approval line or value less than 1.')

class ApprovalMatrixMroLine(models.Model):
    _name = 'approval.matrix.mro.line'
    _description = 'Approval Matrix Mro Line'

    approval_matrix_mro_id = fields.Many2one('approval.matrix.mro')
    user_id = fields.Many2many(comodel_name='res.users', string='User', required=True)
    min_approvers = fields.Integer(string='Minimum Approvers', required=True, default=1)
