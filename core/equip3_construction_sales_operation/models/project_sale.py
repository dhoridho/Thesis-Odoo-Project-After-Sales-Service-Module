from odoo import _, api , fields , models
from odoo.exceptions import UserError, ValidationError, Warning, _logger
from lxml import etree 


class ProjectSale(models.Model):
    _inherit = 'project.project'

    total_sale_order = fields.Integer(string="Sales Order",compute='_comute_sales_orders')
    total_quotation = fields.Integer(string="Quotation",compute='_comute_quotation')

    # main contract
    sale_order_main = fields.Many2one('sale.order.const', string="Contract", domain="{('contract_category', '=', 'main')}")
    main_order_date = fields.Datetime(string="Order Date")
    main_approved_date = fields.Datetime(string="Approved Date")
    main_job_estimate = fields.Many2one('job.estimate', string="BOQ")
    is_set_adjustment_sale = fields.Boolean(string='Advance Adjustment Calculation', default=False, store=True)
    # count_job_estimate = fields.Integer(string="BOQ",compute='_comute_job_estimate')
    sale_order_ids = fields.One2many(comodel_name='sale.order.const', inverse_name='project_id', string='Contract', domain="{('state', '=', 'sale')}")
    lead_id = fields.Many2one('crm.lead', string='Opportunity')
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        if self.env.context.get('is_sale_project'):
            if  self.env.user.has_group('sales_team.group_sale_salesman') and not self.env.user.has_group('sales_team.group_sale_salesman_all_leads'):
                domain.append(('id','in',self.env.user.project_ids.ids))
                domain.append(('create_uid','=',self.env.user.id))
            elif self.env.user.has_group('sales_team.group_sale_salesman_all_leads') and not self.env.user.has_group('sales_team.group_sale_manager'):
                domain.append(('id','in',self.env.user.project_ids.ids))
            
        return super(ProjectSale, self).search_read(domain, fields, offset, limit, order)
    
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        if self.env.context.get('is_sale_project'):
            print("self.env.context.get('is_sale_project')")
            print(self.env.context.get('is_sale_project'))
            if  self.env.user.has_group('sales_team.group_sale_salesman') and not self.env.user.has_group('sales_team.group_sale_salesman_all_leads'):
                domain.append(('id','in',self.env.user.project_ids.ids))
                domain.append(('create_uid','=',self.env.user.id))
            elif self.env.user.has_group('sales_team.group_sale_salesman_all_leads') and not self.env.user.has_group('sales_team.group_sale_manager'):
                domain.append(('id','in',self.env.user.project_ids.ids))
        return super(ProjectSale, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)


    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(ProjectSale, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if self.env.user.has_group('sales_team.group_sale_salesman') and not self.env.user.has_group('sales_team.group_sale_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
            
        return res   

    @api.onchange('main_job_estimate')
    def _onchannge_main_job_estimate(self):
        if self.main_job_estimate and self.department_type == 'department':
            job = self.main_job_estimate
            self.write({
                'main_contract_amount' : job.total_job_estimate
            })

    @api.onchange('sale_order_main') 
    def _onchange_sale_order_main(self):
        self.main_order_date = False
        self.main_contract_amount = False
        self.main_down_payment = False
        self.main_retention1 = False
        self.main_retention1_date = False
        self.main_retention_term_1 = False
        self.main_retention2 = False
        self.main_retention2_date = False
        self.main_retention_term_2 = False
        self.main_tax_id = False
        self.main_payment_term = False

        if self.sale_order_main:
            order = self.sale_order_main
            self.main_order_date = order.date_order
            self.main_contract_amount = order.contract_amount
            self.main_dp_method = order.dp_method
            self.main_down_payment = order.down_payment
            self.main_retention1 = order.retention1
            self.main_retention1_date = order.retention1_date
            self.main_retention_term_1 = order.retention_term_1
            self.main_retention2 = order.retention2
            self.main_retention2_date = order.retention2_date 
            self.main_retention_term_2 = order.retention_term_2
            self.main_tax_id = [(6, 0, [v.id for v in order.tax_id])]
            self.main_payment_term = order.payment_term_id

    def get_contract_customer_values(self):
        for rec in self:
            return {
                'dp_method': rec.main_dp_method,
                'down_payment': rec.main_down_payment,
                'retention1': rec.main_retention1,
                'retention_term_1': rec.main_retention_term_1,
                'retention2': rec.main_retention2,
                'retention_term_2': rec.main_retention_term_2,
                'tax_id': [(6, 0, [v.id for v in rec.main_tax_id])],
                'payment_term_id': rec.main_payment_term.id,
                'diff_penalty': rec.diff_penalty,
                'method': rec.method,
                'amount': rec.amount,
                'method_client': rec.method_client,
                'amount_client': rec.amount_client,
            }

    def _comute_job_estimate(self):
        for job in self:
            job_count = self.env['job.estimate'].search_count([('project_id', '=', self.id), ('state_new', 'not in', ('rejected','cancel'))])
            job.total_job_estimate = job_count
    
    def _comute_quotation(self):
        for order in self:
            quo_count = self.env['sale.order.const'].search_count([('project_id', '=', self.id), ('state', 'not in', ('sale','done'))])
            order.total_quotation = quo_count
    
    def _comute_sales_orders(self):
        for order in self:
            order_count = self.env['sale.order.const'].search_count([('project_id', '=', self.id), ('state', 'in', ('sale','done'))])
            order.total_sale_order = order_count

    # def action_job_estimate(self):
    #     return {
    #         'name': ("BOQ"),
    #         'view_mode': 'tree,form',
    #         'res_model': 'job.estimate',
    #         'type': 'ir.actions.act_window',
    #         'target': 'current',
    #         'domain': [('project_id', '=', self.id), ('state_new', 'not in', ('rejected','cancel'))],
    #     }

    def action_sale_order(self):
        return {
            'name': ("Contracts"),
            'view_mode': 'tree,form',
            'res_model': 'sale.order.const',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('project_id', '=', self.id), ('state', 'in', ('sale','done'))],
        }

    def add_contract_completion(self):
        return {
            'name': ("Contract Completion Stage"),
            'view_mode': 'form',
            'view_id': self.env.ref('equip3_construction_sales_operation.project_completion_const_view_form').id,
            'res_model': 'project.completion.const',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'default_completion_id': self.id,}
        }

    def create_bill(self):
        pass

    def create_invoice(self):
        pass


    def action_create_boq(self):
        list_scope = []
        list_section = []

        for record in self:
            project = record.id
            customer = record.partner_id.id or False
            if record.project_scope_ids:
                for line in record.project_scope_ids:
                    list_scope.append(
                        (0, 0, {'project_scope': line.project_scope.id, 
                                'description': line.description}
                        )
                    )
            
            if record.project_section_ids:
                for line_1 in record.project_section_ids:
                    list_section.append(
                        (0, 0, {'project_scope': line_1.project_scope.id, 
                                'section_name': line_1.section.id,
                                'description': line_1.description, 
                                'quantity': line_1.quantity,
                                'uom_id': line_1.uom_id.id}
                        )
                    )

        context = {'default_project_id': project,
                   'default_partner_id': customer,
                   'project_scope_ids': list_scope,
                   'section_ids': list_section,
                  }
        

        return {
            "name": "BOQ",
            "type": "ir.actions.act_window",
            "res_model": "job.estimate",
            "context": context,
            "view_mode": 'form',
            "target": "current",
        }

    def action_boq(self):
        return {
            'name': ("BOQ"),
            'view_mode': 'tree,form',
            'res_model': 'job.estimate',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('project_id', '=', self.id)],
        }
    
    def action_quotations(self):
        return {
            'name': ("Quotation"),
            'view_mode': 'tree,form',
            'res_model': 'sale.order.const',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('project_id', '=', self.id), ('state', 'not in', ('sale','done'))],
        }
    
    all_project_progress = fields.Float(string="Project Progress", compute="compute_all_project_progress")

    @api.depends('project_completion_ids') 
    def compute_all_project_progress(self):
        total = 0
        for rec in self:
            total = sum(rec.project_completion_ids.mapped('completion_line'))
            rec.all_project_progress = total
        return total


class VariationOrderLineInherit(models.Model):
    _inherit = "variation.order.line"
        
    name = fields.Many2one('sale.order.const', string="Sales Order Reference", ondelete='cascade')
    order_date = fields.Datetime(string="Order Date")
        
    diff_penalty = fields.Boolean(string='Different Penalty', related='name.diff_penalty')
    method = fields.Selection([('fix', 'Fixed'), ('percentage', 'Percentage')], string='Method',
                                    default='percentage', related='name.method')
    amount = fields.Float(string='Amount', related='name.amount')
    method_client = fields.Selection([('fix', 'Fixed'), ('percentage', 'Percentage')], string='Method',
                            default='percentage', related='name.method_client')
    amount_client = fields.Float(string='Amount', related='name.amount_client')


class VariationOrderInternalLine(models.Model):
    _inherit = 'variation.order.internal.line'

    name = fields.Many2one(
        string='Variation Order',
        comodel_name='job.estimate',
        ondelete='cascade',
    )


class ProjectCompletionInherit(models.Model):
    _inherit = "project.completion.const"

    name = fields.Many2one('sale.order.const', string="Contract", ondelete='restrict', domain="[('project_id.name','=',project_id), ('vo_payment_type','=','split'), ('state','=','sale')]")
    job_estimate = fields.Many2one('job.estimate' ,string="BOQ", ondelete='restrict', domain="[('project_id.name','=', project_id), ('state_new','in',('approved', 'confirmed'))]")
    completion_id = fields.Many2one('project.project', string="Project")
    completion_line = fields.Float(string="Completion Line",  compute="_compute_completion_line")

    @api.depends('project_completion', 'contract_percentage')
    def _compute_completion_line(self):
        total = 0
        for line in self:
            total = (line.project_completion * line.contract_percentage) / 100
            line.completion_line = total

    # department_type = fields.Selection(related='completion_id.department_type', string='Type of Project')
# =======
    department_type = fields.Selection([
        ('department', 'Internal'),
        ('project', 'External'),
    ], string='Type of Project', compute="_check_department_type")

    @api.depends('completion_id') 
    def _check_department_type(self):
        for res in self:
            if res.completion_id._origin.id and res.completion_id._origin.name:
                check = self.env['project.project'].search([('id', '=', res.completion_id._origin.id), ('name', '=', res.completion_id._origin.name)], limit=1)
            else:
                check = self.env['project.project'].search([('id', '=', res.completion_id.id), ('name', '=', res.completion_id.name)], limit=1)
            if check.department_type == 'department':
                res.write({'department_type' : 'department'})
            elif check.department_type == 'project':
                res.write({'department_type' : 'project'})
                
    @api.constrains('name')
    def _check_existing_record(self):
        for record in self:
            if record.department_type == 'project':
                check = self.env['project.completion.const'].search([('completion_id', '=', record.completion_id.id), ('name', '=', record.name.id)])
                if len(check) > 1:
                    raise ValidationError(
                        f'The contract in this contract completion stage is the same as another contract completion stage. Please change the contract')
    
    @api.constrains('job_estimate')
    def _check_existing_record_job(self):
        for record in self:
            if record.department_type == 'department':
                check = self.env['project.completion.const'].search([('completion_id', '=', record.completion_id.id), ('job_estimate', '=', record.job_estimate.id)])
                if len(check) > 1:
                    raise ValidationError(
                        f'The BOQ in this contract completion stage is the same as another contract completion stage. Please change the BOQ')

    def save_contract_completion(self):
        total_percentage_line = 0
        contract_stage = self.env['project.completion.const'].search([('completion_id', '=', self.completion_id.id), ('id', '!=', self.id)])
        if contract_stage:
            for con in contract_stage:
                total_percentage_line += con.contract_percentage
        
        if self.contract_percentage + total_percentage_line > 100:
            raise ValidationError(_("Contract Percentage of The Project exceeds 100%.\nPlease, re-set again."))
        
        total_weightage = 0
        for line in self.stage_details_ids:
            total_weightage += line.stage_weightage
        
        if total_weightage <= 0:
            raise ValidationError(
                f'The total of stage weightage is %s' % (total_weightage) + '%. \nPlease, re-set the weightage of each stage.' )
        elif total_weightage > 100:
            raise ValidationError(
                f'The total of stage weightage is more than 100%.\nPlease, re-set the weightage of each stage.')
        elif total_weightage < 100:
            return{
                'name': ("Confirmation"),
                'type': 'ir.actions.act_window',
                'res_model': 'contract.completion.validation.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_contract_completion_id': self.id,}
            }
        else:
            return {
                'type': 'ir.actions.act_window_close',
            }

    @api.onchange('stage_details_ids')
    def _onchange_stage_details_ids(self):
        for rec in self:
            # Check if data already in DB
            if rec._origin.id:
                previous_stage_detail_ids = rec._origin.stage_details_ids._origin
                current_stage_detail_ids = rec.stage_details_ids._origin

                if len(current_stage_detail_ids) < len(previous_stage_detail_ids):
                    not_allowed_stage_to_delete = previous_stage_detail_ids.filtered(
                        lambda x: x.id not in current_stage_detail_ids.ids
                        and x.stage_completion > 0
                    )
                    if len(not_allowed_stage_to_delete) > 0:
                        raise ValidationError(
                            f"You're not allowed to delete stage that already has completion.")

    def edit_contract_completion(self):
        return {
            'name': ("Contract Completion Stage"),
            'view_mode': 'form',
            'view_id': self.env.ref('equip3_construction_sales_operation.project_completion_const_view_form').id,
            'res_model': 'project.completion.const',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'default_completion_id': self.completion_id.id,}
        }

    def delete_contract_completion(self):
        for rec in self:
            job_orders = self.env["project.task"].search([('completion_ref', '=', rec.id)])
            if len(job_orders) > 0:
                raise ValidationError(_("Can't delete contract completion that already used in the job order"))

        return {
            'type': 'ir.actions.act_window',
            'name': 'Confirmation',
            'res_model': 'project.completion.delete.confirmation',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    def scope_as_stage(self):
        if self.department_type == 'project':
            for stage in self.stage_details_ids:
                job_order = self.env['project.task'].search([('stage_new', '=', stage.id)])
                if len(job_order) > 0:
                    raise ValidationError(_("Stage already used in the job order"))

            self.stage_details_ids = False
            for scope in self.name.project_scope_ids:
                name = scope.project_scope.name 
                stages = self.env['project.task.type'].search([('name', '=', name)])
                if len(stages) == 0:
                    self.env['project.task.type'].create({'name': scope.project_scope.name})
                
            for scope in self.name.project_scope_ids:
                name = scope.project_scope.name 
                stages = self.env['project.task.type'].search([('name', '=', name)])
                if len(stages) > 0:
                    for scope_stage in stages:
                        self.stage_details_ids = [(0, 0, {
                            'name': scope_stage.id
                        })]
            
        elif self.department_type == 'department':
            for stage in self.stage_details_ids:
                job_order = self.env['project.task'].search([('stage_new', '=', stage.id)])
                if len(job_order) > 0:
                    raise ValidationError(_("Stage already used in the job order"))

            self.stage_details_ids = False
            for scope in self.job_estimate.project_scope_ids:
                name = scope.project_scope.name 
                stages = self.env['project.task.type'].search([('name', '=', name)])
                if len(stages) == 0:
                    self.env['project.task.type'].create({'name': scope.project_scope.name})
            
            for scope in self.job_estimate.project_scope_ids:
                name = scope.project_scope.name 
                stages = self.env['project.task.type'].search([('name', '=', name)])
                if len(stages) > 0:
                    for scope_stage in stages:
                        self.stage_details_ids = [(0, 0, {
                            'name': scope_stage.id
                        })]

        # Prevent wizard from closing after button click
        return {
            'name': ("Contract Completion Stage"),
            'view_mode': 'form',
            'view_id': self.env.ref('equip3_construction_sales_operation.project_completion_const_view_form').id,
            'res_model': 'project.completion.const',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def section_as_stage(self):
        if self.department_type == 'project':
            for stage in self.stage_details_ids:
                job_order = self.env['project.task'].search([('stage_new', '=', stage.id)])
                if len(job_order) > 0:
                    raise ValidationError(_("Stage already used in the job order"))
        
            self.stage_details_ids = False
            for section in self.name.section_ids:
                name = section.section.name 
                stages = self.env['project.task.type'].search([('name', '=', name)])
                if len(stages) == 0:
                    self.env['project.task.type'].create({'name': section.section.name})
                
            for section in self.name.section_ids:
                name = section.section.name 
                stages = self.env['project.task.type'].search([('name', '=', name)])
                if len(stages) > 0:
                    for section_stage in stages:
                        self.stage_details_ids = [(0, 0, {
                            'name': section_stage.id
                        })]

        elif self.department_type == 'department':
            for stage in self.stage_details_ids:
                job_order = self.env['project.task'].search([('stage_new', '=', stage.id)])
                if len(job_order) > 0:
                    raise ValidationError(_("Stage already used in the job order"))
        
            self.stage_details_ids = False
            for section in self.job_estimate.section_ids:
                name = section.section_name.name 
                stages = self.env['project.task.type'].search([('name', '=', name)])
                if len(stages) == 0:
                    self.env['project.task.type'].create({'name': section.section_name.name})
            
            for section in self.job_estimate.section_ids:
                name = section.section_name.name 
                stages = self.env['project.task.type'].search([('name', '=', name)])
                if len(stages) > 0:
                    for section_stage in stages:
                        self.stage_details_ids = [(0, 0, {
                            'name': section_stage.id
                        })]

        # Prevent wizard from closing after button click
        return {
            'name': ("Contract Completion Stage"),
            'view_mode': 'form',
            'view_id': self.env.ref('equip3_construction_sales_operation.project_completion_const_view_form').id,
            'res_model': 'project.completion.const',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
    
    def variable_as_stage(self):
        if self.department_type == 'project':
            for stage in self.stage_details_ids:
                job_order = self.env['project.task'].search([('stage_new', '=', stage.id)])
                if len(job_order) > 0:
                    raise ValidationError(_("Stage already used in the job order"))

            self.stage_details_ids = False
            for variable in self.name.variable_ids:
                name = variable.variable.name 
                stages = self.env['project.task.type'].search([('name', '=', name)])
                if len(stages) == 0:
                    self.env['project.task.type'].create({'name': variable.variable.name})
                
            for variable in self.name.variable_ids:
                name = variable.variable.name 
                stages = self.env['project.task.type'].search([('name', '=', name)])
                if len(stages) > 0:
                    for variable_stage in stages:
                        self.stage_details_ids = [(0, 0, {
                            'name': variable_stage.id
                        })]

        elif self.department_type == 'department':
            for stage in self.stage_details_ids:
                job_order = self.env['project.task'].search([('stage_new', '=', stage.id)])
                if len(job_order) > 0:
                    raise ValidationError(_("Stage already used in the job order"))

            self.stage_details_ids = False
            for variable in self.job_estimate.variable_ids:
                name = variable.variable_name.name 
                stages = self.env['project.task.type'].search([('name', '=', name)])
                if len(stages) == 0:
                    self.env['project.task.type'].create({'name': variable.variable_name.name})
            
            for variable in self.job_estimate.variable_ids:
                name = variable.variable_name.name 
                stages = self.env['project.task.type'].search([('name', '=', name)])
                if len(stages) > 0:
                    for variable_stage in stages:
                        self.stage_details_ids = [(0, 0, {
                            'name': variable_stage.id
                        })]

        # Prevent wizard from closing after button click
        return {
            'name': ("Contract Completion Stage"),
            'view_mode': 'form',
            'view_id': self.env.ref('equip3_construction_sales_operation.project_completion_const_view_form').id,
            'res_model': 'project.completion.const',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
        
class ProjectStageNewInherit(models.Model):
    _inherit = "project.stage.const"

    sale_order = fields.Many2one(related='stage_id.name', string="Contract")
    job_estimate = fields.Many2one(related='stage_id.job_estimate', string="BOQ")

    # def write(self, vals):
    #     for rec in self:
    #         job_order = self.env['project.task'].search([('stage_new', '=', rec.id)])
    #         if len(job_order) > 0:
    #             raise ValidationError(_("Can't edit stage that already used in the job order"))
    #     res = super().write(vals)
    #     return res

    def unlink(self):
        for rec in self:
            job_order = self.env['project.task'].search([('stage_new', '=', rec.id)])
            if len(job_order) > 0:
                raise ValidationError(_("Can't delete stage that already used in the job order"))
        res = super().unlink()
        return res
