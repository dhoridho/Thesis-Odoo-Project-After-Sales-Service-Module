from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ac_expiry_date = fields.Integer(string="Action Checklist Expiry Date")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        res.update({
            'ac_expiry_date': IrConfigParam.get_param('ac_expiry_date', '1'),
        })
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values() 
        self.env['ir.config_parameter'].sudo().set_param('ac_expiry_date', self.ac_expiry_date) 
        if self.is_hse_action_approval_matrix is True:
            self.env.ref('equip3_hse_operation.approval_matrix_action_checklist_configuration_menu').active = True
        else:
            self.env.ref('equip3_hse_operation.approval_matrix_action_checklist_configuration_menu').active = False


class ApprovalMatrixActionChecklist(models.Model):
    _name = 'approval.matrix.action.checklist'
    _description = 'Approval Matrix Action Checklist'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _order = 'create_date DESC'

    name = fields.Char(string="Name", required=True, tracking=True)
    company_id = fields.Many2one('res.company', string="Company", required=True, tracking=True, readonly=True, default=lambda self: self.env.company.id)
    branch_id = fields.Many2one('res.branch', string="Branch", tracking=True, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, 
                                domain=lambda self: [('id', 'in', self.env.branches.ids)])
    approval_matrix_ids = fields.One2many('approval.matrix.action.checklist.line', 'approval_matrix_id', string='Approving Matrix Action Checklist', tracking=True)
 
    @api.constrains('approval_matrix_ids')
    def _check_is_approver_matrix_line_ids_exist(self):
        for record in self:
            if not record.approval_matrix_ids:
                raise ValidationError("Can't save action checklist approval matrix because there's no approver in approver line!")

    @api.constrains('name')
    def _check_existing_record_name(self):
        for record in self:
            name_id = self.env['approval.matrix.action.checklist'].search(
                [('name', '=', record.name)])
            if len(name_id) > 1:
                raise ValidationError(
                    f'The Approval matrix name already exists, which is the same as the other approval matrix name.\nPlease change the approval name.')    
    
        
    @api.constrains('company_id', 'branch_id')
    def _check_existing_record(self):
        for record in self:
            approval_matrix_id = self.search([('company_id', '=', record.company_id.id),
                                            ('branch_id', '=', record.branch_id.id),
                                            ('id', '!=', record.id)], limit=1)

            if approval_matrix_id:
                raise ValidationError("The action checklist approval matrix is already exist in branch %s. Please change the branch.\nExisted approval : '%s'." %((approval_matrix_id.branch_id.name),(approval_matrix_id.name)))

                    
    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in rec.approval_matrix_ids:
                line.sequence = current_sequence
                current_sequence += 1

    def copy(self, default=None):
        res = super(ApprovalMatrixActionChecklist, self.with_context(keep_line_sequence=True)).copy(default)
        return res


class ApprovalMatrixActionChecklistLine(models.Model):
    _name = "approval.matrix.action.checklist.line"
    _description = "Approval Matrix Action Checklist Line"
    
    @api.model
    def default_get(self, fields):
        res = super(ApprovalMatrixActionChecklistLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'approval_matrix_ids' in context_keys:
                if len(self._context.get('approval_matrix_ids')) > 0:
                    next_sequence = len(self._context.get('approval_matrix_ids')) + 1
            res.update({'sequence': next_sequence})
        return res

    approval_matrix_id = fields.Many2one('approval.matrix.action.checklist', string='Approval Matrix')
    sequence = fields.Integer(required=True, index=True, help='Use to arrange calculation sequence', tracking=True)
    sequence2 = fields.Integer(
        string="No.",
        related="sequence",
        readonly=True,
        store=True,
        tracking=True
    )
    approvers = fields.Many2many('res.users')
    minimum_approver = fields.Integer(default=1)

    def unlink(self):
        approval = self.approval_matrix_id
        res = super(ApprovalMatrixActionChecklistLine, self).unlink()
        approval._reset_sequence()
        return res

    @api.model
    def create(self, vals):
        res = super(ApprovalMatrixActionChecklistLine, self).create(vals)
        if not self.env.context.get("keep-line_sequence", False):
            res.approval_matrix_id._reset_sequence()
        return res