from odoo import api, fields, models
from odoo.exceptions import ValidationError
from datetime import datetime

class ApprovalMatrixPropertySale(models.Model):
    _name = 'approval.matrix.property.sale'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Property Sale Approval Matrix'
    

    name = fields.Char(string="Name", required=True)
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.user.company_id, readonly=True)
    branch_id = fields.Many2one('res.branch', string='Branch', required=True)
    created_date = fields.Date(string='Create On', default=datetime.today().date(), readonly=True)
    user_id = fields.Many2one('res.users', 'Created By', required=True, readonly=True, default=lambda self: self.env.user)
    min_amount = fields.Float(string='Minimum Amount', required=True)
    max_amount = fields.Float(string='Maximum Amount', required=True)
    approval_matrix_property_sale_line_ids = fields.One2many('approval.matrix.property.sale.line', 'approval_matrix_property_sale_id', string='Approval')
    
    @api.model
    def create(self, vals):
        res = super(ApprovalMatrixPropertySale, self).create(vals)
        res._check_approval_matrix_line()
        return res

    def write(self, vals):
        res = super(ApprovalMatrixPropertySale, self).write(vals)
        self._check_approval_matrix_line()
        return res
    
    @api.constrains('branch_id', 'min_amount', 'max_amount')
    def _check_existing_record(self):
        for record in self:
            if record.branch_id:
                approval_matrix_id = self.search([('branch_id', '=', record.branch_id.id), ('id', '!=', record.id), '|', '|',
                                                '&', ('min_amount', '<=', record.min_amount), ('max_amount', '>=', record.min_amount),
                                                '&', ('min_amount', '<=', record.max_amount), ('max_amount', '>=', record.max_amount),
                                                '&', ('min_amount', '>=', record.min_amount), ('max_amount', '<=', record.max_amount)], limit=1)
                if approval_matrix_id:
                    raise ValidationError("The minimum and maximum range of this approval matrix is intersects with other approval matrix [%s] in same branch. Please change the minimum and maximum range" % (approval_matrix_id.name))

    def _check_approval_matrix_line(self):
        for line in self.approval_matrix_property_sale_line_ids:
            if line.min_approvers > len(line.user_name_ids) or line.min_approvers <= 0:
                raise ValidationError('Please make sure the minimum approvers not more than the user on approval line or value less than 1.')

class ApprovalMatrixPropertySaleLines(models.Model):
    _name = 'approval.matrix.property.sale.line'
    _description = "Approval Matrix Property Sale"

    @api.model
    def default_get(self, fields):
        res = super(ApprovalMatrixPropertySaleLines, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 0
            if 'approval_matrix_property_sale_line_ids' in context_keys:
                if len(self._context.get('approval_matrix_property_sale_line_ids')) > 0:
                    next_sequence = len(self._context.get('approval_matrix_property_sale_line_ids')) + 1
            res.update({'sequence': next_sequence})
        return res

    approval_matrix_property_sale_id = fields.Many2one('approval.matrix.property.sale')
    user_name_ids = fields.Many2many('res.users', string="Users", required=True)
    min_approvers = fields.Integer(string='Minimum Approvers', required=True, default=1)
    sequence = fields.Integer(required=True, index=True, help='Use to arrange calculation sequence', tracking=True)
    sequence2 = fields.Integer(string="No.", readonly=True, store=True, tracking=True, compute='_compute_sequence2')
    
    @api.depends('sequence')
    def _compute_sequence2(self):
        for record in self:
            record.sequence2 = record.sequence + 1
