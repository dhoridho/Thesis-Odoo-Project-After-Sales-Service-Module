from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning
from lxml import etree

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    bc_expiry_date = fields.Integer(string="Budget Change Request Expiry Date")
    bt_expiry_date = fields.Integer(string="Project Budget Transfer Expiry Date")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        res.update({
            'bc_expiry_date': IrConfigParam.get_param('bc_expiry_date', '1'),
            'bt_expiry_date': IrConfigParam.get_param('bt_expiry_date', '1')
        })
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values() 
        self.env['ir.config_parameter'].sudo().set_param('bc_expiry_date', self.bc_expiry_date) 
        self.env['ir.config_parameter'].sudo().set_param('bt_expiry_date', self.bt_expiry_date) 
        if self.budget_change_request_approval_matrix == True:
            self.env.ref('equip3_construction_operation.approval_matrix_internal_transfer_budget_configuration_menu').active = True
            self.env.ref('equip3_construction_operation.approval_matrix_internal_transfer_budget_configuration_menu_internal').active = True
        else:
            self.env.ref('equip3_construction_operation.approval_matrix_internal_transfer_budget_configuration_menu').active = False
            self.env.ref('equip3_construction_operation.approval_matrix_internal_transfer_budget_configuration_menu_internal').active = False

        if self.project_budget_transfer_approval_matrix == True:
            self.env.ref('equip3_construction_operation.approval_matrix_project_budget_transfer_configuration_menu').active = True
            self.env.ref('equip3_construction_operation.approval_matrix_project_budget_transfer_configuration_menu_internal').active = True
        else:
            self.env.ref('equip3_construction_operation.approval_matrix_project_budget_transfer_configuration_menu').active = False
            self.env.ref('equip3_construction_operation.approval_matrix_project_budget_transfer_configuration_menu_internal').active = False

        if self.is_change_allocation_approval_matrix == True:
            self.env.ref('equip3_construction_operation.approval_matrix_change_allocation_configuration_menu').active = True
            self.env.ref('equip3_construction_operation.approval_matrix_internal_change_allocation_configuration_menu_internal').active = True
        else:
            self.env.ref('equip3_construction_operation.approval_matrix_change_allocation_configuration_menu').active = False
            self.env.ref('equip3_construction_operation.approval_matrix_internal_change_allocation_configuration_menu_internal').active = False


class ApprovalMatrixInternalTransferBudget(models.Model):
    _name = 'approval.matrix.internal.transfer.budget'
    _description = 'Approval Matrix Internal Transfer Budget'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    
    name = fields.Char(string="Name", required=True, tracking=True)
    company_id = fields.Many2one('res.company', string="Company", required=True, tracking=True, readonly=True, default=lambda self: self.env.company.id)
    branch_id = fields.Many2one('res.branch', string="Branch", tracking=True, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, 
                                domain=lambda self: [('id', 'in', self.env.branches.ids),('company_id','=', self.env.company.id)])
    project = fields.Many2many('project.project', string='Project')
    minimum_amt = fields.Float(string="Minimum Amount", tracking=True)
    maximum_amt = fields.Float(string="Maximum Amount", tracking=True)
    approval_matrix_ids = fields.One2many('approval.matrix.internal.transfer.budget.line', 'approval_matrix_id', string='Approving Matrix Internal Transfer Budget', tracking=True)
    is_project_transfer = fields.Boolean("Is Project Budget Transfer", default=False)
    department_type = fields.Selection([('department', 'Internal'),('project', 'External')], string='Type of Department')
    set_default = fields.Boolean(string='Set as Default', default=False)
    is_change_allocation = fields.Boolean(string='Is Change Allocation', default=False)
 
 
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(ApprovalMatrixInternalTransferBudget, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        root = etree.fromstring(res['arch'])
        if self.env.user.has_group('abs_construction_management.group_construction_user') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_engineer'):
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)

        else:
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        return res
    
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        if  self.env.user.has_group('equip3_construction_accessright_setting.group_construction_engineer') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_director'):
            domain.append(('project.id','in',self.env.user.project_ids.ids))
        
        return super(ApprovalMatrixInternalTransferBudget, self).search_read(domain, fields, offset, limit, order)
    
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        if  self.env.user.has_group('equip3_construction_accessright_setting.group_construction_engineer') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_director'):
            domain.append(('project.id','in',self.env.user.project_ids.ids))
        return super(ApprovalMatrixInternalTransferBudget, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    


    @api.onchange('set_default')
    def _onchange_set_default(self):
        for rec in self:
            if rec.set_default == True:
                rec.project = False

    @api.constrains('approval_matrix_ids')
    def _check_is_approver_matrix_line_ids_exist(self):
        for record in self:
            if not record.approval_matrix_ids:
                if record.is_project_transfer == False and record.is_change_allocation == False:
                    raise ValidationError("Can't save budget change request approval matrix because there's no approver in approver line!")
                elif record.is_project_transfer == False and record.is_change_allocation == True:
                    raise ValidationError("Can't save change allocation approval matrix because there's no approver in approver line!")
                elif record.is_project_transfer == True and record.is_change_allocation == False:
                    raise ValidationError("Can't save project budget transfer approval matrix because there's no approver in approver line!")

    @api.constrains('name', 'department_type', 'is_project_transfer', 'is_change_allocation')
    def _check_existing_record_name(self):
        for record in self:
            name_id = self.env['approval.matrix.internal.transfer.budget'].search(
                [('name', '=', record.name), ('is_project_transfer', '=', record.is_project_transfer), ('is_change_allocation', '=', record.is_change_allocation), ('department_type', '=', record.department_type)])
            if len(name_id) > 1:
                raise ValidationError(
                    f'The Approval matrix name already exists, which is the same as the other approval matrix name.\nPlease change the approval name.')    

    @api.onchange('department_type')
    def _onchange_department_type(self):
        for rec in self:
            if self.env.user.has_group('abs_construction_management.group_construction_user') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_director'):
                if rec.department_type == 'project':
                    return {
                        'domain': {'project': [('department_type', '=', 'project'), ('primary_states', '!=', 'cancelled'), ('company_id', '=', rec.company_id.id),('id','in',self.env.user.project_ids.ids)]}
                    }
                elif rec.department_type == 'department':
                    return {
                        'domain': {'project': [('department_type', '=', 'department'), ('primary_states', '!=', 'cancelled'), ('company_id', '=', rec.company_id.id),('id','in',self.env.user.project_ids.ids)]}
                    }
                
            else:
                if rec.department_type == 'project':
                    return {
                        'domain': {'project': [('department_type', '=', 'project'), ('primary_states', '!=', 'cancelled'), ('company_id', '=', rec.company_id.id),('id','in',self.env.user.project_ids.ids)]}
                    }
                elif rec.department_type == 'department':
                    return {
                        'domain': {'project': [('department_type', '=', 'department'), ('primary_states', '!=', 'cancelled'), ('company_id', '=', rec.company_id.id),('id','in',self.env.user.project_ids.ids)]}
                    }

    @api.constrains('project', 'company_id', 'branch_id', 'minimum_amt', 'maximum_amt', 'set_default', 'department_type', 'is_project_transfer')
    def _check_existing_record(self):
        for record in self:
            domain = [('company_id', '=', record.company_id.id),
                    ('branch_id', '=', record.branch_id.id),
                    ('id', '!=', record.id),
                    ('department_type', '=', record.department_type),
                    ('is_project_transfer', '=', record.is_project_transfer),
                    ('is_change_allocation', '=', record.is_change_allocation)]
            
            domain_default = domain.copy()
            domain_default += [('set_default', '=', True)]

            domain += [('set_default', '=', False)]

            if not record.is_change_allocation:
                domain_default += ['|', '|',
                                    '&', ('minimum_amt', '<=', record.minimum_amt), ('maximum_amt', '>=', record.minimum_amt),
                                    '&', ('minimum_amt', '<=', record.maximum_amt), ('maximum_amt', '>=', record.maximum_amt),
                                    '&', ('minimum_amt', '>=', record.minimum_amt), ('maximum_amt', '<=', record.maximum_amt)]
                
                domain += ['|', '|',
                                    '&', ('minimum_amt', '<=', record.minimum_amt), ('maximum_amt', '>=', record.minimum_amt),
                                    '&', ('minimum_amt', '<=', record.maximum_amt), ('maximum_amt', '>=', record.maximum_amt),
                                    '&', ('minimum_amt', '>=', record.minimum_amt), ('maximum_amt', '<=', record.maximum_amt)]

            

            find_duplicate = self.search(domain, limit=1)
            find_default = self.search(domain_default, limit=1)

            if record.set_default == False:
                for matrix in find_duplicate:
                    for proj in matrix.project:
                        if proj in record.project:
                            if record.is_change_allocation:
                                raise ValidationError("The change allocation approval matrix for this project is already exist in branch %s. Please change the project or the branch.\nExisted approval : '%s'." %((find_duplicate.branch_id.name),(find_duplicate.name)))

                            raise ValidationError("The minimum and maximum range of this approval matrix is intersects with other approval matrix '%s' in same branch and project. Please change the minimum and maximum range" % (find_duplicate.name))
            else:
                if find_default:
                    raise ValidationError("You have set the approval matrix default and only can set one approval matrix default for all projects in branch {}.\nCurrent Default: '{}'.".format(find_default.branch_id.name, find_default.name))

                    
    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in rec.approval_matrix_ids:
                line.sequence = current_sequence
                current_sequence += 1

    def copy(self, default=None):
        res = super(ApprovalMatrixInternalTransferBudget, self.with_context(keep_line_sequence=True)).copy(default)
        return res


class ApprovalMatrixInternalTransferBudgetLine(models.Model):
    _name = "approval.matrix.internal.transfer.budget.line"
    _description = "Approval Matrix Internal Transfer Budget Line"
    
    @api.model
    def default_get(self, fields):
        res = super(ApprovalMatrixInternalTransferBudgetLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'approval_matrix_ids' in context_keys:
                if len(self._context.get('approval_matrix_ids')) > 0:
                    next_sequence = len(self._context.get('approval_matrix_ids')) + 1
            res.update({'sequence': next_sequence})
        return res

    approval_matrix_id = fields.Many2one('approval.matrix.internal.transfer.budget', string='Approval Matrix')
    internal_transfer_budget_id = fields.Many2one('internal.transfer.budget', string="Budget Transfer")
    sequence = fields.Integer(required=True, index=True, help='Use to arrange calculation sequence')
    sequence2 = fields.Integer(
        string="No.",
        related="sequence",
        readonly=True,
        store=True
    )
    approvers = fields.Many2many('res.users')
    minimum_approver = fields.Integer(default=1)

    def unlink(self):
        approval = self.approval_matrix_id
        res = super(ApprovalMatrixInternalTransferBudgetLine, self).unlink()
        approval._reset_sequence()
        return res

    @api.model
    def create(self, vals):
        res = super(ApprovalMatrixInternalTransferBudgetLine, self).create(vals)
        if not self.env.context.get("keep-line_sequence", False):
            res.approval_matrix_id._reset_sequence()
        return res