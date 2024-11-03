from odoo import api , fields , models
from odoo.exceptions import UserError, ValidationError, Warning
from lxml import etree


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ph_expiry_date = fields.Integer(string="Progress History Expiry Date")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        res.update({
            'ph_expiry_date': IrConfigParam.get_param('ph_expiry_date', '1'),
        })
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values() 
        self.env['ir.config_parameter'].sudo().set_param('ph_expiry_date', self.ph_expiry_date) 
        if self.is_progress_history_approval_matrix == True:
            self.env.ref('equip3_construction_operation.approval_matrix_progress_history_configuration_menu').active = True
            self.env.ref('equip3_construction_operation.progress_history_menu_approval').active = True
            self.env.ref('equip3_construction_operation.progress_history_menu').active = False
            self.env.ref('equip3_construction_operation.menu_sub_progress_history_internal_approval').active = True
            self.env.ref('equip3_construction_operation.menu_sub_progress_history_internal').active = False
        else:
            self.env.ref('equip3_construction_operation.approval_matrix_progress_history_configuration_menu').active = False
            self.env.ref('equip3_construction_operation.progress_history_menu_approval').active = False
            self.env.ref('equip3_construction_operation.progress_history_menu').active = True
            self.env.ref('equip3_construction_operation.menu_sub_progress_history_internal_approval').active = False
            self.env.ref('equip3_construction_operation.menu_sub_progress_history_internal').active = True


class ApprovalMatrixProgressHistory(models.Model):
    _name = 'approval.matrix.progress.history'
    _description = "Approval Matrix Progress History"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    name = fields.Char(string="Name", required=True, tracking=True)
    company_id = fields.Many2one('res.company', string="Company", required=True, tracking=True, readonly=True, default=lambda self: self.env.company.id)
    branch_id = fields.Many2one('res.branch', string="Branch", tracking=True, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, 
                                domain=lambda self: [('id', 'in', self.env.branches.ids),('company_id','=', self.env.company.id)])
    project_id = fields.Many2many('project.project', string='Project')
    project_director = fields.Many2one('res.users', string='Project Director')
    approval_matrix_ids = fields.One2many('approval.matrix.progress.history.line', 'approval_matrix_id', string="Approver Name")
    department_type = fields.Selection([('department', 'Internal'),('project', 'External')], string='Type of Project')
    set_default = fields.Boolean(string='Set as Default', default=False)
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(ApprovalMatrixProgressHistory, self).fields_view_get(
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
        if  self.env.user.has_group('abs_construction_management.group_construction_user') and not self.env.user.has_group('abs_construction_management.group_construction_manager'):
            domain.append(('project_id.id','in',self.env.user.project_ids.ids))
            domain.append(('create_uid','=',self.env.user.id))
        elif  self.env.user.has_group('abs_construction_management.group_construction_manager') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_director'):
            domain.append(('project_id.id','in',self.env.user.project_ids.ids))
        
        return super(ApprovalMatrixProgressHistory, self).search_read(domain, fields, offset, limit, order)

    @api.onchange('set_default')
    def _onchange_set_default(self):
        for rec in self:
            if rec.set_default == True:
                rec.project_id = False
    
    @api.constrains('approval_matrix_ids')
    def _check_is_approval_matrix_ids_exist(self):
        for record in self:
            if not record.approval_matrix_ids:
                raise ValidationError("Can't save progress history approval matrix because there's no approver in approver line!")
    
    @api.onchange('department_type')
    def _onchange_department_type(self):
        for rec in self:
            if self.env.user.has_group('abs_construction_management.group_construction_user') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_director'):
                if rec.department_type == 'project':
                    return {
                        'domain': {'project_id': [('department_type', '=', 'project'), ('primary_states', '!=', 'cancelled'), ('company_id', '=', rec.company_id.id),('id','in',self.env.user.project_ids.ids)]}
                    }
                elif rec.department_type == 'department':
                    return {
                        'domain': {'project_id': [('department_type', '=', 'department'), ('primary_states', '!=', 'cancelled'), ('company_id', '=', rec.company_id.id),('id','in',self.env.user.project_ids.ids)]}
                    }
                
            else:
                if rec.department_type == 'project':
                    return {
                        'domain': {'project_id': [('department_type', '=', 'project'), ('primary_states', '!=', 'cancelled'), ('company_id', '=', rec.company_id.id),('id','in',self.env.user.project_ids.ids)]}
                    }
                elif rec.department_type == 'department':
                    return {
                        'domain': {'project_id': [('department_type', '=', 'department'), ('primary_states', '!=', 'cancelled'), ('company_id', '=', rec.company_id.id),('id','in',self.env.user.project_ids.ids)]}
                    }

    @api.constrains('name', 'department_type')
    def _check_existing_record_name(self):
        for record in self:
            name_id = self.env['approval.matrix.progress.history'].search(
                [('name', '=', record.name),('department_type', '=', record.department_type)])
            if len(name_id) > 1:
                raise ValidationError(
                    f'The Approval matrix name already exists, which is the same as the other approval matrix name.\nPlease change the approval name.')    
    
    @api.constrains('project_id', 'company_id', 'branch_id', 'department_type', 'set_default')
    def _check_existing_record(self):
        for record in self:
            if record.department_type == 'project':
                approval_matrix_id = self.search([('company_id', '=', record.company_id.id),
                                              ('branch_id', '=', record.branch_id.id),
                                              ('id', '!=', record.id),
                                              ('set_default', '=', False),
                                              ('department_type', '=', 'project')], limit=1)
            
                approval_matrix_id_default = self.search([('company_id', '=', record.company_id.id),
                                                ('branch_id', '=', record.branch_id.id),
                                                ('id', '!=', record.id),
                                                ('set_default', '=', True),
                                                ('department_type', '=', 'project')], limit=1)
            
            else:
                approval_matrix_id = self.search([('company_id', '=', record.company_id.id),
                                              ('branch_id', '=', record.branch_id.id),
                                              ('id', '!=', record.id),
                                              ('set_default', '=', False),
                                              ('department_type', '=', 'department')], limit=1)
            
                approval_matrix_id_default = self.search([('company_id', '=', record.company_id.id),
                                                ('branch_id', '=', record.branch_id.id),
                                                ('id', '!=', record.id),
                                                ('set_default', '=', True),
                                                ('department_type', '=', 'department')], limit=1)
                
            if record.set_default == False:
                for matrix in approval_matrix_id:
                    for proj in matrix.project_id:
                        if proj in record.project_id:
                            raise ValidationError("The progress history approval matrix for this project is already exist in branch %s. Please change the project or the branch.\nExisted approval : '%s'." %((approval_matrix_id.branch_id.name),(approval_matrix_id.name)))
            else:
                if approval_matrix_id_default:
                    raise ValidationError("You have set the approval matrix default and only can set one approval matrix default for all projects in branch {}.\nCurrent Default: '{}'.".format(approval_matrix_id_default.branch_id.name, approval_matrix_id_default.name))
                       
    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in rec.approval_matrix_ids:
                line.sequence = current_sequence
                current_sequence += 1

    def copy(self, default=None):
        res = super(ApprovalMatrixProgressHistory, self.with_context(keep_line_sequence=True)).copy(default)
        return res


class ApprovalMatrixProgressHistoryLines(models.Model):
    _name = 'approval.matrix.progress.history.line'
    _description = "Approval Matrix Progress History Lines"

    @api.model
    def default_get(self, fields):
        res = super(ApprovalMatrixProgressHistoryLines, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'approval_matrix_ids' in context_keys:
                if len(self._context.get('approval_matrix_ids')) > 0:
                    next_sequence = len(self._context.get('approval_matrix_ids')) + 1
            res.update({'sequence': next_sequence})
        return res

    approval_matrix_id = fields.Many2one('approval.matrix.progress.history', string='Approval Matrix')
    progress_id = fields.Many2one('progress.history', string="Progress History")
    progress_id_wiz = fields.Many2one('progress.history.wiz', string="Progress History")
    sequence = fields.Integer(required=True, index=True, help='Use to arrange calculation sequence')
    sequence2 = fields.Integer(
        string="No.",
        related="sequence",
        readonly=True,
        store=True
    )
    approvers = fields.Many2many('res.users')
    minimum_approver = fields.Integer(default=1)
    approval_status = fields.Text()
    approved_time = fields.Text(string="Timestamp")
    feedback = fields.Text()

    def unlink(self):
        approval = self.approval_matrix_id
        res = super(ApprovalMatrixProgressHistoryLines, self).unlink()
        approval._reset_sequence()
        return res

    @api.model
    def create(self, vals):
        res = super(ApprovalMatrixProgressHistoryLines, self).create(vals)
        if not self.env.context.get("keep-line_sequence", False):
            res.approval_matrix_id._reset_sequence()
        return res