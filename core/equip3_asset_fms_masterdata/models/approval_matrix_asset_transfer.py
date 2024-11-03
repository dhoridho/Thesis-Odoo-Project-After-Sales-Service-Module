from odoo import api, fields, models
from datetime import datetime
from odoo.exceptions import ValidationError

class ApprovalMatrixAssetTransfer(models.Model):
    _name = 'approval.matrix.asset.transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Internal Asset Transfer Approval Matrix'

    _sql_constraints = [ ('branch_id_unique', 'CHECK(1=1)', 'There is already an Approval Matrix for this Branch, please select other branch'),('fac_area_unique', 'CHECK(1=1)', 'There is already an Approval Matrix for this Facilities Area, please select other Facilities Area')]

    name = fields.Char(string="Name", required=True)
    company_id = fields.Many2one("res.company", "Company", default=lambda self: self.env.user.company_id, readonly=True)
    branch_id = fields.Many2one('res.branch', string='Branch', required=True,default=lambda self: self.env.branches if len(self.env.branches) == 1 else False,
        domain=lambda self: [('id', 'in', self.env.branches.ids)])
    created_date = fields.Date(string='Create On', default=datetime.today().date(), readonly=True)
    user_id = fields.Many2one('res.users', 'Created By', required=True, readonly=True, default=lambda self: self.env.user)
    min_amount = fields.Float(string='Minimum Amount', required=True)
    max_amount = fields.Float(string='Maximum Amount', required=True)
    fac_area = fields.Many2one('maintenance.facilities.area', string='Facilities Area', required=True)
    approval_matrix_asset_transfer_ids = fields.One2many('approval.matrix.asset.transfer.line', 'approval_matrix_asset_transfer_id', string='Approval')

    @api.model
    def create(self, vals):
        res = super(ApprovalMatrixAssetTransfer, self).create(vals)
        res._check_approval_matrix_line()
        return res

    def write(self, vals):
        res = super(ApprovalMatrixAssetTransfer, self).write(vals)
        self._check_approval_matrix_line()
        return res

    @api.constrains('branch_id', 'fac_area')
    def _check_existing_record(self):
        for record in self:
            if record.branch_id:
                approval_matrix_id = self.search([('branch_id', '=', record.branch_id.id), ('id', '!=', record.id), ('fac_area', '=', record.fac_area.id), '|', '|',
                                                '&', ('min_amount', '<=', record.min_amount), ('max_amount', '>=', record.min_amount),
                                                '&', ('min_amount', '<=', record.max_amount), ('max_amount', '>=', record.max_amount),
                                                '&', ('min_amount', '>=', record.min_amount), ('max_amount', '<=', record.max_amount)], limit=1)
                # approval_matrix_id = self.search([('branch_id', '=', record.branch_id.id), ('id', '!=', record.id), ('fac_area', '=', record.fac_area.id)], limit=1)
                if approval_matrix_id:
                    raise ValidationError("The minimum and maximum range of this approval matrix is intersects with other approval matrix [%s] in same branch and facilities area.\nPlease change the minimum and maximum range" % (approval_matrix_id.name))

    def _check_approval_matrix_line(self):
        set_of_valid_state = set(['waiting_approval', 'approved', 'in_progress', 'done', 'cancel'])
        mapped_state = self.approval_matrix_asset_transfer_ids.mapped('state_id')
        if 'draft' in mapped_state: mapped_state.remove('draft')

        if set_of_valid_state != set(mapped_state):
            raise ValidationError('Please fill all state for Approval Matrix')

        if 0 in self.approval_matrix_asset_transfer_ids.mapped('min_approvers'):
            raise ValidationError('Please make sure the minimum approvers not more than the user on approval line or value less than 1.')

        for line in self.approval_matrix_asset_transfer_ids:
            if line.min_approvers > len(line.user_id):
                raise ValidationError('Please make sure the minimum approvers not more than the user on approval line or value less than 1.')

class ApprovalMatrixAssetTransferLine(models.Model):
    _name = 'approval.matrix.asset.transfer.line'
    _description= 'Approval Matrix Asset Transfer Line'

    approval_matrix_asset_transfer_id = fields.Many2one('approval.matrix.asset.transfer')
    state_id = fields.Selection([('waiting_approval', 'Waiting For Approval'),
         ('approved', 'Approved'),
         ('in_progress', 'In Progress'),
         ('done', 'Done'),
         ('cancel', 'Cancelled')], string="Status", default='draft', required=True)
    user_id = fields.Many2many(comodel_name='res.users', string='User', required=True)
    min_approvers = fields.Integer(string='Minimum Approvers', required=True, default=1)
