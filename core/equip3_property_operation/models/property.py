from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    # approval matrix for property rent
    rent_branch_id = fields.Many2one('res.branch', string='Branch')
    approvalmatrix_rent = fields.Many2one('approval.matrix.property.rent', string='Approval Matrix', compute='_compute_approval_matrix_rent')
    approval_sequence = fields.Integer(string='Approval Sequence', default=0, readonly=True)
    approvers_id = fields.Many2many('res.users', string='Approvers')
        
    @api.depends('rent_branch_id', 'deposite')
    def _compute_approval_matrix_rent(self):
        self.approvalmatrix_rent = self.env['approval.matrix.property.rent'].search([('branch_id', '=', self.rent_branch_id.id), ('min_amount', '<=', self.deposite), ('max_amount', '>=', self.deposite)], limit=1)
    
    def _check_approval_matrix_continue_rent(self):
        approval_line_ids = self.approvalmatrix_rent.approval_matrix_property_rent_line_ids
        line = approval_line_ids.filtered(lambda x: x.sequence == self.approval_sequence)
        
        if self.env.user not in approval_line_ids.mapped('user_name_ids') or self.env.user not in line.mapped('user_name_ids'):
            raise ValidationError('You are not allowed to do this action. Please contact your system administrator for approval')
            
        total_approval_line = len(approval_line_ids)

        self.approvers_id = [(4, self.env.user.id)]
        self.activity_search(['mail.mail_activity_data_todo']).unlink()

        if len(self.approvers_id) >= line.min_approvers:
            self.approvers_id = [(5)]
            self.approval_sequence += 1

            if self.approval_sequence == total_approval_line:
                self.approval_sequence = 0
                return True

            for user in approval_line_ids.filtered(lambda x: x.sequence == self.approval_sequence).mapped('user_name_ids'):
                self.activity_schedule(act_type_xmlid='mail.mail_activity_data_todo', user_id=user.id)
        return False
    
    # approval matrix for property sale
    sale_branch_id = fields.Many2one('res.branch', string='Branch')
    approvalmatrix_sale = fields.Many2one('approval.matrix.property.sale', string='Approval Matrix', compute='_compute_approval_matrix_sale')
        
    @api.depends('sale_branch_id', 'discounted_price')
    def _compute_approval_matrix_sale(self):
        self.approvalmatrix_sale = self.env['approval.matrix.property.sale'].search([('branch_id', '=', self.sale_branch_id.id), ('min_amount', '<=', self.discounted_price), ('max_amount', '>=', self.discounted_price)], limit=1)
    
    def _check_approval_matrix_continue_sale(self):
        approval_line_ids = self.approvalmatrix_sale.approval_matrix_property_sale_line_ids
        line = approval_line_ids.filtered(lambda x: x.sequence == self.approval_sequence)
        
        if self.env.user not in approval_line_ids.mapped('user_name_ids') or self.env.user not in line.mapped('user_name_ids'):
            raise ValidationError('You are not allowed to do this action. Please contact your system administrator for approval')
            
        total_approval_line = len(approval_line_ids)

        self.approvers_id = [(4, self.env.user.id)]
        self.activity_search(['mail.mail_activity_data_todo']).unlink()

        if len(self.approvers_id) >= line.min_approvers:
            self.approvers_id = [(5)]
            self.approval_sequence += 1

            if self.approval_sequence == total_approval_line:
                self.approval_sequence = 0
                return True

            for user in approval_line_ids.filtered(lambda x: x.sequence == self.approval_sequence).mapped('user_name_ids'):
                self.activity_schedule(act_type_xmlid='mail.mail_activity_data_todo', user_id=user.id)
        return False
    
    def sale_property_with_approval(self):
        if self._check_approval_matrix_continue_sale():
            return self.buy_now_property()
        else:
            return False
    
    def rent_property_with_approval(self):
        if self._check_approval_matrix_continue_rent():
            return self.reserve_property()
        else:
            return False