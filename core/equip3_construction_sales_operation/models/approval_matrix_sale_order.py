
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, Warning
from lxml import etree


class ApprovalMatrixSaleOrderConst(models.Model):
    _name = 'approval.matrix.sale.order.const'
    _description = "Approval Matrix Sale Order"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    name = fields.Char(string='Name', tracking=True, required=True)
    project_id = fields.Many2many('project.project', string='Project')
    company_id = fields.Many2one("res.company", string="Company", tracking=True, required=True, readonly=True, default=lambda self: self.env.company.id)
    branch_id = fields.Many2one("res.branch", string="Branch", tracking=True, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, 
                                domain=lambda self: [('id', 'in', self.env.branches.ids)])
    config = fields.Selection([
        ('contract_amt', 'Contract Amount'),
        ('adjustment_amt', 'Adjustment Amount'),
        ('discount_amt', 'Discount Amount'),
    ], 'Configuration', store=True, required=True, default="contract_amt", tracking=True)
    minimum_amt = fields.Float(string='Minimum Amount', required=True, tracking=True)
    maximum_amt = fields.Float(string='Maximum Amount', required=True, tracking=True)
    approval_matrix_ids = fields.One2many('approval.matrix.sale.order.lines.const', 'approval_matrix_id', string="Approver Name")
    type_contract = fields.Selection([('addendum', 'Addendum'),('dedendum', 'Dedendum')], string='Type of BOQ')
    department_type = fields.Selection([('department', 'Internal'),('project', 'External')], string='Type of Project')
    set_default = fields.Boolean(string='Set as Default', default=False)

    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(ApprovalMatrixSaleOrderConst, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        root = etree.fromstring(res['arch'])
        if self.env.user.has_group(
                'abs_construction_management.group_construction_user') and not self.env.user.has_group(
                'equip3_construction_accessright_setting.group_construction_engineer'):
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
        if self.env.user.has_group(
                'abs_construction_management.group_construction_user') and not self.env.user.has_group(
                'abs_construction_management.group_construction_manager'):
            domain.append(('project_id', 'in', self.env.user.project_ids.ids))
            domain.append(('create_uid', '=', self.env.user.id))
        elif self.env.user.has_group(
                'abs_construction_management.group_construction_manager') and not self.env.user.has_group(
                'equip3_construction_accessright_setting.group_construction_director'):
            domain.append(('project_id', 'in', self.env.user.project_ids.ids))

        return super(ApprovalMatrixSaleOrderConst, self).search_read(domain, fields, offset, limit, order)

    @api.onchange('set_default')
    def _onchange_set_default(self):
        for rec in self:
            if rec.set_default == True:
                rec.project_id = False
    
    @api.onchange('config')
    def _onchange_set_config(self):
        for rec in self:
            if rec.config != 'contract_amt':
                rec.type_contract = False

    @api.onchange('department_type')
    def _onchange_department_type(self):
        for rec in self:
            if self.env.user.has_group('sales_team.group_sale_salesman') and not self.env.user.has_group('sales_team.group_sale_manager'):
                if rec.department_type == 'project':
                    return {
                        'domain': {'project_id': [('department_type', '=', 'project'), ('primary_states', '!=', 'cancelled'), ('company_id', '=', rec.company_id.id),('id', 'in', self.env.user.project_ids.ids)]}
                    }
                elif rec.department_type == 'department':
                    return {
                        'domain': {'project_id': [('department_type', '=', 'department'), ('primary_states', '!=', 'cancelled'), ('company_id', '=', rec.company_id.id),('id', 'in', self.env.user.project_ids.ids)]}
                    }
            else:
                if rec.department_type == 'project':
                    return {
                        'domain': {'project_id': [('department_type', '=', 'project'), ('primary_states', '!=', 'cancelled'), ('company_id', '=', rec.company_id.id)]}
                    }
                elif rec.department_type == 'department':
                    return {
                        'domain': {'project_id': [('department_type', '=', 'department'), ('primary_states', '!=', 'cancelled'), ('company_id', '=', rec.company_id.id)]}
                    }

    @api.constrains('approval_matrix_ids')
    def _check_is_approver_matrix_line_ids_exist(self):
        for record in self:
            if not record.approval_matrix_ids:
                raise ValidationError("Can't save contract approval matrix because there's no approver in approver line!")
    
    @api.constrains('name')
    def _check_existing_record_name(self):
        for record in self:
            name_id = self.env['approval.matrix.sale.order.const'].search(
                [('name', '=', record.name)])
            if len(name_id) > 1:
                raise ValidationError(
                    f'The Approval matrix name already exists, which is the same as the other approval matrix name.\nPlease change the approval name.')    

    @api.model
    def default_get(self, fields):
        res = super(ApprovalMatrixSaleOrderConst, self).default_get(fields)
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        sale_matrix_config_const =  IrConfigParam.get_param('sale_matrix_config_const', 'contract_amt')
        res['config'] = sale_matrix_config_const
        return res

    @api.constrains('project_id', 'company_id', 'branch_id', 'config', 'minimum_amt', 'maximum_amt', 'set_default')
    def _check_existing_record(self):
        for record in self:
            if record.type_contract == 'addendum':
                approval_matrix_id = self.search([('company_id', '=', record.company_id.id),
                                                ('branch_id', '=', record.branch_id.id), 
                                                ('id', '!=', record.id), 
                                                ('config', '=', record.config),
                                                ('type_contract', '=', 'addendum'),
                                                ('set_default', '=', False),
                                                '|', '|',
                                                '&', ('minimum_amt', '<=', record.minimum_amt), ('maximum_amt', '>=', record.minimum_amt),
                                                '&', ('minimum_amt', '<=', record.maximum_amt), ('maximum_amt', '>=', record.maximum_amt),
                                                '&', ('minimum_amt', '>=', record.minimum_amt), ('maximum_amt', '<=', record.maximum_amt)], limit=1)
                
                approval_matrix_id_default = self.search([('company_id', '=', record.company_id.id),
                                                    ('branch_id', '=', record.branch_id.id),
                                                    ('id', '!=', record.id),
                                                    ('config', '=', record.config),
                                                    ('type_contract', '=', 'addendum'),
                                                    ('set_default', '=', True),
                                                    '|', '|',
                                                    '&', ('minimum_amt', '<=', record.minimum_amt), ('maximum_amt', '>=', record.minimum_amt),
                                                    '&', ('minimum_amt', '<=', record.maximum_amt), ('maximum_amt', '>=', record.maximum_amt),
                                                    '&', ('minimum_amt', '>=', record.minimum_amt), ('maximum_amt', '<=', record.maximum_amt)], limit=1)
                
            else:
                approval_matrix_id = self.search([('company_id', '=', record.company_id.id),
                                                ('branch_id', '=', record.branch_id.id), 
                                                ('id', '!=', record.id), 
                                                ('config', '=', record.config),
                                                ('type_contract', '=', 'dedendum'),
                                                ('set_default', '=', False),
                                                '|', '|',
                                                '&', ('minimum_amt', '<=', record.minimum_amt), ('maximum_amt', '>=', record.minimum_amt),
                                                '&', ('minimum_amt', '<=', record.maximum_amt), ('maximum_amt', '>=', record.maximum_amt),
                                                '&', ('minimum_amt', '>=', record.minimum_amt), ('maximum_amt', '<=', record.maximum_amt)], limit=1)
                
                approval_matrix_id_default = self.search([('company_id', '=', record.company_id.id),
                                                    ('branch_id', '=', record.branch_id.id),
                                                    ('id', '!=', record.id),
                                                    ('config', '=', record.config),
                                                    ('type_contract', '=', 'dedendum'),
                                                    ('set_default', '=', True),
                                                    '|', '|',
                                                    '&', ('minimum_amt', '<=', record.minimum_amt), ('maximum_amt', '>=', record.minimum_amt),
                                                    '&', ('minimum_amt', '<=', record.maximum_amt), ('maximum_amt', '>=', record.maximum_amt),
                                                    '&', ('minimum_amt', '>=', record.minimum_amt), ('maximum_amt', '<=', record.maximum_amt)], limit=1)
            
            if record.set_default == False:
                for matrix in approval_matrix_id:
                    for proj in matrix.project_id:
                        if proj in record.project_id:
                            raise ValidationError("The minimum and maximum range of this approval matrix is intersects with other approval matrix '%s' in same branch and project. Please change the minimum and maximum range" % (approval_matrix_id.name))
            else:
                if approval_matrix_id_default:
                    raise ValidationError("The minimum and maximum range of this approval matrix default is intersects with other approval matrix default '%s' in same branch. Please change the minimum and maximum range" % (approval_matrix_id_default.name))
    
    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in rec.approval_matrix_ids:
                line.sequence = current_sequence
                current_sequence += 1
    
    def copy(self, default=None):
        res = super(ApprovalMatrixSaleOrderConst, self.with_context(keep_line_sequence=True)).copy(default)
        return res


class ApprovalMatrixSaleOrderLinesConst(models.Model):
    _name = 'approval.matrix.sale.order.lines.const'
    _description = "Approval Matrix Sale Order Lines"

    @api.model
    def default_get(self, fields):
        res = super(ApprovalMatrixSaleOrderLinesConst, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'approval_matrix_ids' in context_keys:
                if len(self._context.get('approval_matrix_ids')) > 0:
                    next_sequence = len(self._context.get('approval_matrix_ids')) + 1
            res.update({'sequence': next_sequence})
        return res

    approval_matrix_id = fields.Many2one('approval.matrix.sale.order.const', string='Approval Matrix')
    order_id = fields.Many2one('sale.order.const', string="Sale Order")
    sequence = fields.Integer(required=True, index=True, help='Use to arrange calculation sequence')
    sequence2 = fields.Integer(
        string="No.",
        related="sequence",
        readonly=True,
        store=True
    )
    approvers = fields.Many2many('res.users')
    minimum_approver = fields.Integer(default=1)
    approval_type = fields.Selection([('contract_amt', 'Contract Amount'),
                                      ('adjustment_amt', 'Adjustment Amount'),
                                      ('discount_amt', 'Discount Amount')], string='Configuration')

    def unlink(self):
        approval = self.approval_matrix_id
        res = super(ApprovalMatrixSaleOrderLinesConst, self).unlink()
        approval._reset_sequence()
        return res

    @api.model
    def create(self, vals):
        res = super(ApprovalMatrixSaleOrderLinesConst, self).create(vals)
        if not self.env.context.get("keep-line_sequence", False):
            res.approval_matrix_id._reset_sequence()
        return res
