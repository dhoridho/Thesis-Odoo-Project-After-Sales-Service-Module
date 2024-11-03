from dataclasses import field
from email.policy import default
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError,UserError
from datetime import datetime

class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    project = fields.Many2one(comodel_name = 'project.project', string='Project', domain=lambda self:[('company_id','=',self.env.company.id),('primary_states','=','progress')])
    budgeting_period = fields.Selection(related='cost_sheet.budgeting_period', string='Budgeting Period')
    budgeting_method = fields.Selection(related='project.budgeting_method', string='Budgeting Method')
    cost_sheet = fields.Many2one('job.cost.sheet', string='Cost Sheet')
    project_budget = fields.Many2one('project.budget', string='Periodical Budget', domain="[('project_id','=', project), ('state','=', 'in_progress')]")
    multiple_budget_ids = fields.Many2many('project.budget', string='Multiple Budget', domain="[('project_id','=', project), ('state','=', 'in_progress')]")
    is_multiple_budget = fields.Boolean('Multiple Budget', default=False)
    material_request = fields.Many2one('material.request', 'Material Request')

    is_subcontracting = fields.Boolean('Is Subcontracting', default=False)
    is_material_orders = fields.Boolean('Is Material Orders', default=False)
    is_orders = fields.Boolean('Is Orders', default=False)
    is_asset_cons_order = fields.Boolean('Is Asset Cons Order', default=False)

    variable_line_ids = fields.One2many('pr.variable.line', 'variable_id', string='Variable Line')
    material_line_ids = fields.One2many('pr.material.line', 'material_id', string='Material Line')
    service_line_ids = fields.One2many('pr.service.line', 'service_id', string='Service Line')
    equipment_line_ids = fields.One2many('pr.equipment.line', 'equipment_id')
    labour_line_ids = fields.One2many('pr.labour.line', 'labour_id', string='Labour Line')
    overhead_line_ids = fields.One2many('pr.overhead.line', 'overhead_id', string='Overhead Line')
    is_single_request_date = fields.Boolean(string="Single Request Date", default=True)
    is_multiple_budget_procurement = fields.Boolean(string="Is Multiple Budget", compute='_is_multiple_budget_procurement')
    state = fields.Selection(selection_add=[('cancel', 'Cancelled')], ondelete={'cancel': 'cascade'})

    def _is_multiple_budget_procurement(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_multiple_budget_procurement = IrConfigParam.get_param('is_multiple_budget_procurement')
        for record in self:
            record.is_multiple_budget_procurement = is_multiple_budget_procurement

    @api.onchange('is_subcontracting')
    def _onchange_is_subcontracting(self):
        context = dict(self.env.context) or {}
        if context.get('services_good'):
            self.is_subcontracting = True

    @api.onchange('is_orders')
    def _onchange_is_orders(self):
        context = dict(self.env.context) or {}
        if context.get('orders'):
            self.is_orders = True

    @api.onchange('cost_sheet')
    def onchange_job_cost_sheet(self):
        for rec in self.cost_sheet:
            if rec.state != 'in_progress':
                raise ValidationError(_('Cost sheet status is not in progress. Please In Progress cost sheet first.'))

    @api.onchange('project')
    def _onchange_cost_sheet(self):
        self.analytic_account_group_ids = False
        for rec in self:
            for proj in rec.project:
                rec.cost_sheet = rec.env['job.cost.sheet'].search([('project_id', '=', proj.id), ('state', 'not in', ['cancelled','reject','revised'])])
                if rec.cost_sheet == 'freeze':
                    raise ValidationError("The budget for this project is being freeze")
                else:
                    self.write({'cost_sheet' : rec.cost_sheet})
                    self.analytic_account_group_ids = self.cost_sheet.account_tag_ids.ids
                    rec.branch_id = rec.project.branch_id.id
                    rec.destination_warehouse = rec.project.warehouse_address

    def _get_project_budget(self, res):
        Job_cost_sheet = res.cost_sheet
        if res.request_date:
            schedule = datetime.strptime(str(self.request_date), "%Y-%m-%d")
            month_date = schedule.strftime("%B")
            if res.project.budgeting_period == 'monthly':
                data = res.env['budget.period.line'].search([('month', '=', month_date),
                                                            ('line_project_ids', '=', Job_cost_sheet.project_id.id),], limit=1)
                budget = res.env['project.budget'].search([('project_id', '=', Job_cost_sheet.project_id.id),
                                                            ('cost_sheet', '=', Job_cost_sheet.id),
                                                            ('month', '=', data.id)], limit=1)
                return budget
            elif res.project.budgeting_period == 'custom':
                budget = res.env['project.budget'].search([('project_id', '=', Job_cost_sheet.project_id.id),
                                                            ('cost_sheet', '=', Job_cost_sheet.id),
                                                            ('bd_start_date', '<=', res.request_date),
                                                            ('bd_end_date', '>=', res.request_date)], limit=1)
                return budget
            else:
                pass


    def table_form_cs_subcon(self, res, cost, cos):
        res.variable_line_ids = [(0, 0, {
            'project_scope': cos.project_scope.id,
            'section': cos.section_name.id,
            'variable': cos.variable.id,
            'quantity': cos.budgeted_qty_left,
            'budget_quantity': cos.budgeted_qty_left,
            'uom': cos.uom_id.id,
            'analytic_group': [(6, 0, [v.id for v in cost.account_tag_ids])],
        })]

    def table_form_bd_subcon(self, res, budget, bud):
        res.variable_line_ids = [(0, 0, {
            'project_scope': bud.project_scope.id,
            'section': bud.section_name.id,
            'variable': bud.subcon_id.id,
            'quantity': bud.qty_left,
            'budget_quantity': bud.qty_left,
            'uom': bud.uom_id.id,
            'analytic_group': [(6, 0, [v.id for v in budget.analytic_group_id])],
        })]

    def table_form_cs_equipment(self, res, cost, cos):
        res.line_ids = [(0, 0, {
            'type' : 'equipment',
            'project_scope' : cos.project_scope.id,
            'section' : cos.section_name.id,
            'group_of_product' : cos.group_of_product.id,
            'product_id' : cos.product_id.id,
            'name' : cos.description,
            'product_uom_id' : cos.uom_id.id,
            'product_qty' : cos.budgeted_qty_left,
            'budget_quantity' : cos.budgeted_qty_left,
            'company_id' : cost.company_id.id,
            'dest_loc_id': cost.warehouse_id.id,
            'analytic_account_group_ids': [(6, 0, [v.id for v in cost.account_tag_ids])],
        })]

    def table_form_bd_equipment(self, res, budget, bud):
        res.line_ids = [(0, 0, {
            'type' : 'equipment',
            'project_scope' : bud.project_scope.id,
            'section' : bud.section_name.id,
            'group_of_product' : bud.group_of_product.id,
            'product_id' : bud.product_id.id,
            'name' : bud.description,
            'product_uom_id' : bud.uom_id.id,
            'product_qty' : bud.qty_left,
            'budget_quantity' : bud.qty_left,
            'company_id' : budget.cost_sheet.company_id.id,
            'dest_loc_id': budget.cost_sheet.warehouse_id.id,
            'analytic_account_group_ids': [(6, 0, [v.id for v in budget.analytic_group_id])],
        })]

    def get_subcon_table_form_cs(self, res):
        for cost in res.cost_sheet:
            for cos in cost.material_subcon_ids:
                if res.budgeting_method != 'product_budget':
                    if cos.budgeted_qty_left > 0:
                        res.table_form_cs_subcon(res, cost, cos)
                else:
                    if cos.budgeted_qty_left > 0:
                        res.table_form_cs_subcon(res, cost, cos)

    def get_subcon_table_form_bd(self, res):
        for budget in res.project_budget:
            for bud in budget.budget_subcon_ids:
                if res.budgeting_method != 'product_budget':
                    if bud.qty_left > 0:
                        res.table_form_bd_subcon(res, budget, bud)
                else:
                    if bud.qty_left > 0:
                        res.table_form_bd_subcon(res, budget, bud)

    def get_equipment_table_form_cs(self, res):
        for cost in res.cost_sheet:
            for cos in cost.material_equipment_ids:
                if res.budgeting_method != 'product_budget':
                    if cos.budgeted_qty_left > 0:
                        res.table_form_cs_equipment(res, cost, cos)
                else:
                    if cos.budgeted_qty_left > 0:
                        res.table_form_cs_equipment(res, cost, cos)

    def get_equipment_table_form_bd(self, res):
        for budget in res.project_budget:
            for bud in budget.budget_equipment_ids:
                if res.budgeting_method != 'product_budget':
                    if bud.qty_left > 0:
                        res.table_form_bd_equipment(res, budget, bud)
                else:
                    if bud.qty_left > 0:
                        res.table_form_bd_equipment(res, budget, bud)

    @api.onchange('line_ids')
    def _onchange_line_ids(self):
        for rec in self:
            if rec.is_goods_orders :
                if len(rec.material_request) > 0:
                    for line in rec.line_ids:
                        if line.project_scope and line.section and line.group_of_product and line.product_id:
                            line.budget_quantity = line.mr_line_id.budget_quantity
                            line._check_qty_budget()
                            if rec.material_request.type_of_mr == "material":
                                line.cs_material_id = line.mr_line_id.cs_material_id
                                line.bd_material_id = line.mr_line_id.bd_material_id
                            elif rec.material_request.type_of_mr == "equipment":
                                line.cs_equipment_id = line.mr_line_id.cs_equipment_id
                                line.bd_equipment_id = line.mr_line_id.bd_equipment_id
                            elif rec.material_request.type_of_mr == "overhead":
                                line.cs_overhead_id = line.mr_line_id.cs_overhead_id
                                line.bd_overhead_id = line.mr_line_id.bd_overhead_id
                else:
                    for line in rec.line_ids:
                        if line.project_scope and line.section and line.group_of_product and line.product_id:
                            if rec.budgeting_period == 'project':
                                cs_lines = rec.cost_sheet.material_ids.filtered(lambda x: (x.project_scope.id == line.project_scope.id) and (x.section_name.id == line.section.id) and \
                                                                                            (x.group_of_product.id == line.group_of_product.id) and (x.product_id.id == line.product_id.id) )
                                line.budget_quantity = cs_lines[0].budgeted_qty_left if len(cs_lines) > 0 else line.budget_quantity
                            else:
                                bd_lines = rec.project_budget.budget_material_ids.filtered(lambda x: (x.project_scope.id == line.project_scope.id) and (x.section_name.id == line.section.id) and \
                                                                                            (x.group_of_product.id == line.group_of_product.id) and (x.product_id.id == line.product_id.id) )
                                line.budget_quantity = bd_lines[0].qty_left if len(bd_lines) > 0 else line.budget_quantity

                            line._check_qty_budget()

    @api.onchange('project', 'is_multiple_budget', 'project_budget')
    def _onchange_get_line_pr(self):
        for res in self:
            if res.project:
                bud_qty_left = 0
                bud_amt_left = 0

                if res.is_subcontracting == True:
                    res.variable_line_ids = [(5, 0, 0)]
                    if res.budgeting_method == 'product_budget':
                        if res.budgeting_period == 'project':
                            for line_id in res.cost_sheet.material_subcon_ids:
                                bud_qty_left += line_id.budgeted_qty_left
                                bud_amt_left += line_id.budgeted_amt_left
                            if bud_qty_left < 1 or bud_amt_left < 1 :
                                raise ValidationError("There is no budget for subcon left")
                            else:
                                for cost in res.cost_sheet:
                                    for cos in cost.material_subcon_ids:
                                        if cos.budgeted_qty_left > 0:
                                            res.table_form_cs_subcon(res, cost, cos)
                        else:
                            if res.is_multiple_budget == False:
                                for line_bud in res.project_budget.budget_subcon_ids:
                                    bud_qty_left += line_bud.qty_left
                                    bud_amt_left += line_bud.amt_left
                                if bud_qty_left < 1 or bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for subcon left")
                                else:
                                    for budget in res.project_budget:
                                        for bud in budget.budget_subcon_ids:
                                            if bud.qty_left > 0:
                                                res.table_form_bd_subcon(res, budget, bud)
                            else:
                                for budget_id in res.multiple_budget_ids:
                                    for bud in budget_id.budget_subcon_ids:
                                        bud_qty_left += bud.qty_left
                                        bud_amt_left += bud.amt_left
                                if bud_qty_left < 1 or bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for subcon left")
                                else:
                                    for budget in res.multiple_budget_ids:
                                        for bud in budget.budget_subcon_ids:
                                            if bud.qty_left > 0:
                                                res.table_form_bd_subcon(res, budget, bud)

                    elif res.budgeting_method == 'gop_budget':
                        if res.budgeting_period == 'project':
                            for line_id in res.cost_sheet.material_subcon_ids:
                                bud_amt_left += line_id.budgeted_amt_left
                            if bud_amt_left < 1 :
                                raise ValidationError("There is no budget for subcon left")
                            else:
                                for cost in res.cost_sheet:
                                    for cos in cost.material_subcon_ids:
                                        res.table_form_cs_subcon(res, cost, cos)
                        else:
                            if res.is_multiple_budget == False:
                                for line_bud in res.project_budget.budget_subcon_ids:
                                    bud_amt_left += line_bud.amt_left
                                if bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for subcon left")
                                else:
                                    for budget in res.project_budget:
                                        for bud in budget.budget_subcon_ids:
                                            res.table_form_bd_subcon(res, budget, bud)
                            else:
                                for budget_id in res.multiple_budget_ids:
                                    for bud in budget_id.budget_subcon_ids:
                                        bud_amt_left += bud.amt_left
                                if bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for subcon left")
                                else:
                                    for budget in res.multiple_budget_ids:
                                        for bud in budget.budget_subcon_ids:
                                            res.table_form_bd_subcon(res, budget, bud)

                    elif res.budgeting_method == 'budget_type':
                        if res.budgeting_period == 'project':
                            if res.cost_sheet.subcon_budget_left < 1 :
                                raise ValidationError("There is no budget for subcon left")
                            else:
                                for cost in res.cost_sheet:
                                    for cos in cost.material_subcon_ids:
                                        res.table_form_cs_subcon(res, cost, cos)
                        else:
                            if res.is_multiple_budget == False:
                                if res.project_budget.amount_left_subcon < 1 :
                                    raise ValidationError("There is no budget for subcon left")
                                else:
                                    for budget in res.project_budget:
                                        for bud in budget.budget_subcon_ids:
                                            res.table_form_bd_subcon(res, budget, bud)
                            else:
                                for budget_id in res.multiple_budget_ids:
                                    bud_amt_left += budget_id.amount_left_subcon
                                if bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for subcon left")
                                else:
                                    for budget in res.multiple_budget_ids:
                                        for bud in budget.budget_subcon_ids:
                                            res.table_form_bd_subcon(res, budget, bud)

                    elif res.budgeting_method == 'total_budget':
                        if res.budgeting_period == 'project':
                            if res.cost_sheet.contract_budget_left < 1 :
                                raise ValidationError("There is no budget for subcon left")
                            else:
                                for cost in res.cost_sheet:
                                    for cos in cost.material_subcon_ids:
                                        res.table_form_cs_subcon(res, cost, cos)
                        else:
                            if res.is_multiple_budget == False:
                                if res.project_budget.budget_left < 1 :
                                    raise ValidationError("There is no budget for subcon left")
                                else:
                                    for budget in res.project_budget:
                                        for bud in budget.budget_subcon_ids:
                                            res.table_form_bd_subcon(res, budget, bud)
                            else:
                                for budget_id in res.multiple_budget_ids:
                                    bud_amt_left += budget_id.budget_left
                                if bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for subcon left")
                                else:
                                    for budget in res.multiple_budget_ids:
                                        for bud in budget.budget_subcon_ids:
                                            res.table_form_bd_subcon(res, budget, bud)

                    for line in res.variable_line_ids:
                        line._onchange_subcon()


                if res.is_rental_orders == True:
                    res.line_ids = [(5, 0, 0)]
                    if res.budgeting_method == 'product_budget':
                        if res.budgeting_period == 'project':
                            for line_id in res.cost_sheet.material_equipment_ids:
                                bud_qty_left += line_id.budgeted_qty_left
                                bud_amt_left += line_id.budgeted_amt_left
                            if bud_qty_left < 1 or bud_amt_left < 1 :
                                raise ValidationError("There is no budget for equipment lease left")
                            else:
                                for cost in res.cost_sheet:
                                    for cos in cost.material_equipment_ids:
                                        if cos.budgeted_qty_left > 0:
                                            res.table_form_cs_equipment(res, cost, cos)
                        else:
                            if res.is_multiple_budget == False:
                                for line_bud in res.project_budget.budget_equipment_ids:
                                    bud_qty_left += line_bud.qty_left
                                    bud_amt_left += line_bud.amt_left
                                if bud_qty_left < 1 or bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for equipment lease left")
                                else:
                                    for budget in res.project_budget:
                                        for bud in budget.budget_equipment_ids:
                                            if bud.qty_left > 0:
                                                res.table_form_bd_equipment(res, budget, bud)
                            else:
                                for budget_id in res.multiple_budget_ids:
                                    for bud in budget_id.budget_equipment_ids:
                                        bud_qty_left += bud.qty_left
                                        bud_amt_left += bud.amt_left
                                if bud_qty_left < 1 or bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for equipment lease left")
                                else:
                                    for budget in res.multiple_budget_ids:
                                        for bud in budget.budget_subcon_ids:
                                            if bud.qty_left > 0:
                                                res.table_form_bd_equipment(res, budget, bud)

                    elif res.budgeting_method == 'gop_budget':
                        if res.budgeting_period == 'project':
                            for line_id in res.cost_sheet.material_equipment_gop_ids:
                                bud_amt_left += line_id.budgeted_amt_left
                            if bud_amt_left < 1 :
                                raise ValidationError("There is no budget for subcon left")
                            else:
                                for cost in res.cost_sheet:
                                    for cos in cost.material_equipment_ids:
                                        res.table_form_cs_equipment(res, cost, cos)
                        else:
                            if res.is_multiple_budget == False:
                                for line_bud in res.project_budget.budget_equipment_gop_ids:
                                    bud_amt_left += line_bud.amt_left
                                if bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for subcon left")
                                else:
                                    for budget in res.project_budget:
                                        for bud in budget.budget_equipment_ids:
                                            res.table_form_bd_equipment(res, budget, bud)
                            else:
                                for budget_id in res.multiple_budget_ids:
                                    for bud in budget_id.budget_equipment_gop_ids:
                                        bud_amt_left += bud.amt_left
                                if bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for subcon left")
                                else:
                                    for budget in res.multiple_budget_ids:
                                        for bud in budget.budget_subcon_ids:
                                            res.table_form_bd_equipment(res, budget, bud)

                    elif res.budgeting_method == 'budget_type':
                        if res.budgeting_period == 'project':
                            if res.cost_sheet.equipment_budget_left < 1 :
                                raise ValidationError("There is no budget for subcon left")
                            else:
                                for cost in res.cost_sheet:
                                    for cos in cost.material_equipment_ids:
                                        res.table_form_cs_equipment(res, cost, cos)
                        else:
                            if res.is_multiple_budget == False:
                                if res.project_budget.amount_left_equipment < 1 :
                                    raise ValidationError("There is no budget for subcon left")
                                else:
                                    for budget in res.project_budget:
                                        for bud in budget.budget_equipment_ids:
                                            res.table_form_bd_equipment(res, budget, bud)
                            else:
                                for budget_id in res.multiple_budget_ids:
                                    bud_amt_left += budget_id.amount_left_equipment
                                if bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for subcon left")
                                else:
                                    for budget in res.multiple_budget_ids:
                                        for bud in budget.budget_subcon_ids:
                                            res.table_form_bd_equipment(res, budget, bud)

                    elif res.budgeting_method == 'total_budget':
                        if res.budgeting_period == 'project':
                            if res.cost_sheet.contract_budget_left < 1 :
                                raise ValidationError("There is no budget for subcon left")
                            else:
                                for cost in res.cost_sheet:
                                    for cos in cost.material_equipment_ids:
                                        res.table_form_cs_equipment(res, cost, cos)
                        else:
                            if res.is_multiple_budget == False:
                                if res.project_budget.budget_left < 1 :
                                    raise ValidationError("There is no budget for subcon left")
                                else:
                                    for budget in res.project_budget:
                                        for bud in budget.budget_equipment_ids:
                                            res.table_form_bd_equipment(res, budget, bud)
                            else:
                                for budget_id in res.multiple_budget_ids:
                                    bud_amt_left += budget_id.budget_left
                                if bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for subcon left")
                                else:
                                    for budget in res.multiple_budget_ids:
                                        for bud in budget.budget_subcon_ids:
                                            res.table_form_bd_equipment(res, budget, bud)

                    for line in res.line_ids:
                        line._onchange_product()


    @api.onchange('project', 'request_date')
    def _onchange_request_date(self):
        for res in self:
            if res.project:
                if res.budgeting_period != 'project':
                    budget = res._get_project_budget(res)
                    if budget:
                        res.project_budget = budget.id
                    else:
                        raise ValidationError(_("There is no periodical budget created for this date"))

    def send_bd_res_qty(self, reserved_bd):
        return{
            'qty_res': reserved_bd,
        }

    def send_cs_res_qty(self, reserved_cs):
        return{
            'reserved_qty': reserved_cs,
        }

    def reserved_pr_bd_subcon(self, res, line, reserved_bd):
        res.project_budget.budget_subcon_ids = [(1, line.bd_subcon_id.id, res.send_bd_res_qty(reserved_bd))]

    def reserved_pr_cs_subcon(self, res, line, reserved_cs):
        res.cost_sheet.material_subcon_ids = [(1, line.cs_subcon_id.id, res.send_cs_res_qty(reserved_cs))]

    def reserved_pr_bd_equipment(self, record, line, reserved_bd):
        record.project_budget.budget_equipment_ids = [(1, line.bd_equipment_id.id, record.send_bd_res_qty(reserved_bd))]

    def reserved_pr_cs_equipment(self, record, line, reserved_cs):
        record.cost_sheet.material_equipment_ids = [(1, line.cs_equipment_id.id, record.send_cs_res_qty(reserved_cs))]

    def button_done_pr(self):
        res = super(PurchaseRequest, self).button_done_pr()
        if self.project and self.mr_id:
            mr_rec = self.env['material.request'].search([('id','in', self.mr_id.ids)])
            for pr_line in self.line_ids:
                for mr_line in mr_rec.product_line:
                    if pr_line.project_scope.id == mr_line.project_scope.id and pr_line.section.id == mr_line.section.id and pr_line.group_of_product.id == mr_line.group_of_product.id and pr_line.product_id.id == mr_line.product.id:
                        # mr_line.done_qty = mr_line.done_qty + pr_line.product_qty
                        for po in pr_line.purchase_lines:
                            mr_line.pr_in_progress_qty += po.product_qty
                            mr_line.pr_done_qty += po.qty_received

        return res
            
    def action_confirm_purchase_request(self):
        if self.cost_sheet.state == 'freeze':
            raise ValidationError("The budget for this project is being freeze")
        else:
            if self.is_subcontracting is False:
                for record in self:
                    for line in record.line_ids:
                        if line.product_qty <= 0:
                            raise ValidationError("Quantity should be greater then 0!")
                        if line.type == 'equipment':
                            diff = 0
                            if self.cost_sheet.budgeting_period in ['project']:
                                diff = line.budget_quantity - line.cs_equipment_id.budgeted_qty_left
                            elif self.cost_sheet.budgeting_period in ['monthly', 'custom']:
                                diff = line.budget_quantity - line.bd_equipment_id.qty_left

                            if diff != 0:
                                raise ValidationError("There’s differences on this document budget quantity with Cost Sheet/ Periodical Budget. Please create new document.")
                                
                            reserved_bd = 0.00
                            reserved_cs = 0.00
                            if line.bd_equipment_id:
                                reserved_bd = (line.product_qty + line.bd_equipment_id.qty_res)
                                record.reserved_pr_bd_equipment(record, line, reserved_bd)
                                reserved_cs = (line.product_qty + line.cs_equipment_id.reserved_qty)
                                record.reserved_pr_cs_equipment(record, line, reserved_cs)
                            else:
                                reserved_cs = (line.product_qty + line.cs_equipment_id.reserved_qty)
                                record.reserved_pr_cs_equipment(record, line, reserved_cs)
                    if not record.line_ids:
                        raise ValidationError("Please Enter Lines Data!")
                    else:
                        record.write({'state': 'approved', 'purchase_req_state': 'pending'})
            else:
                for record in self:
                    for line in record.variable_line_ids:
                        diff = 0
                        if self.cost_sheet.budgeting_period in ['project']:
                            diff = line.budget_quantity - line.cs_subcon_id.budgeted_qty_left
                        elif self.cost_sheet.budgeting_period in ['monthly', 'custom']:
                            diff = line.budget_quantity - line.bd_subcon_id.qty_left

                        if diff != 0:
                            raise ValidationError("There’s differences on this document budget quantity with Cost Sheet/ Periodical Budget. Please create new document.")

                        if line.quantity <= 0:
                            raise ValidationError("Quantity should be greater then 0!")

                    record.write({'state': 'approved', 'purchase_req_state': 'pending'})

    def action_confirm_purchase_request_2(self):
        for res in self:
            reserved_bd = 0.00
            reserved_cs = 0.00
            if res.cost_sheet.state == 'freeze':
                raise ValidationError("The budget for this project is being freeze")
            else:
                if res.budgeting_method == 'product_budget':
                    if res.project_budget:
                        res.action_confirm_purchase_request()
                        for line in res.variable_line_ids:
                            if line.quantity > line.bd_subcon_id.qty_left and res.budgeting_method == 'product_budget':
                                raise ValidationError(_("The quantity is over the remaining budget"))
                            else:
                                reserved_bd = (line.quantity + line.bd_subcon_id.qty_res)
                                res.reserved_pr_bd_subcon(res, line, reserved_bd)
                                reserved_cs = (line.quantity + line.cs_subcon_id.reserved_qty)
                                res.reserved_pr_cs_subcon(res, line, reserved_cs)
                                line.write({'state': 'approved'})
                    else:
                        res.action_confirm_purchase_request()
                        for line in res.variable_line_ids:
                            if line.quantity > line.cs_subcon_id.budgeted_qty_left and res.budgeting_method == 'product_budget':
                                raise ValidationError(_("The quantity is over the remaining budget"))
                            else:
                                reserved_cs = (line.quantity + line.cs_subcon_id.reserved_qty)
                                res.reserved_pr_cs_subcon(res, line, reserved_cs)
                                line.write({'state': 'approved'})
                else:
                    if res.project_budget:
                        res.action_confirm_purchase_request()
                        for line in res.variable_line_ids:
                            reserved_bd = (line.quantity + line.bd_subcon_id.qty_res)
                            res.reserved_pr_bd_subcon(res, line, reserved_bd)
                            reserved_cs = (line.quantity + line.cs_subcon_id.reserved_qty)
                            res.reserved_pr_cs_subcon(res, line, reserved_cs)
                            line.write({'state': 'approved'})
                    else:
                        res.action_confirm_purchase_request()
                        for line in res.variable_line_ids:
                            reserved_cs = (line.quantity + line.cs_subcon_id.reserved_qty)
                            res.reserved_pr_cs_subcon(res, line, reserved_cs)
                            line.write({'state': 'approved'})

    def button_cancel_pr(self):
        res = super(PurchaseRequest, self).button_cancel_pr()
        if self.cost_sheet.state == 'freeze':
            raise ValidationError("The budget for this project is being freeze")
        else:
            if self.is_subcontracting:
                if self.project_budget:
                    for rec in self.variable_line_ids:
                        for bud in rec.bd_subcon_id:
                            reserved = 0.00
                            for sub in self.project_budget:
                                reserved = (bud.qty_res - rec.quantity)
                                sub.budget_subcon_ids = [(1, rec.bd_subcon_id.id, {
                                        'qty_res': reserved,
                                    })]
                            for cs in rec.cs_subcon_id:
                                reserved = (cs.reserved_qty - rec.quantity)
                                for cos in self.cost_sheet:
                                    cos.material_subcon_ids = [(1, rec.cs_subcon_id.id, {
                                            'reserved_qty': reserved,
                                        })]
                    return res
                else:
                    for rec in self.variable_line_ids:
                        reserved = 0.00
                        for cs in rec.cs_subcon_id:
                            reserved = (cs.reserved_qty - rec.quantity)
                            for sub in self.cost_sheet:
                                sub.material_subcon_ids = [(1, rec.cs_subcon_id.id, {
                                        'reserved_qty': reserved,
                                    })]
                    return res
            else:
                for product in self.line_ids:
                    # if product.type == 'equipment':
                    if self.project:
                        product.purchase_request_line_cancel()
                return res

    def button_draft(self):
        res = super(PurchaseRequest, self).button_draft()
        if self.is_subcontracting:
            if self.project_budget:
                for rec in self.variable_line_ids:
                    for bud in rec.bd_subcon_id:
                        reserved = 0.00
                        for sub in self.project_budget:
                            reserved = (bud.qty_res - rec.quantity)
                            sub.budget_subcon_ids = [(1, rec.bd_subcon_id.id, {
                                    'qty_res': reserved,
                                })]
                        for cs in rec.cs_subcon_id:
                            reserved = (cs.reserved_qty - rec.quantity)
                            for cos in self.cost_sheet:
                                cos.material_subcon_ids = [(1, rec.cs_subcon_id.id, {
                                        'reserved_qty': reserved,
                                    })]
                return res
            else:
                for rec in self.variable_line_ids:
                    reserved = 0.00
                    for cs in rec.cs_subcon_id:
                        reserved = (cs.reserved_qty - rec.quantity)
                        for sub in self.cost_sheet:
                            sub.material_subcon_ids = [(1, rec.cs_subcon_id.id, {
                                    'reserved_qty': reserved,
                                })]
                return res
        else:
            return res

    def button_draft_cancel(self):
        res = super(PurchaseRequest, self).button_draft()
        return res


    project_scope_computed = fields.Many2many('project.scope.line', string="computed scope lines",
                                              compute='get_scope_lines')

    @api.depends('project.project_scope_ids')
    def get_scope_lines(self):
        for rec in self:
            pro = rec.project
            scope_ids = []
            if pro.project_scope_ids:
                for line in pro.project_scope_ids:
                    if line.project_scope:
                        scope_ids.append(line.project_scope.id)
                rec.project_scope_computed = [(6, 0, scope_ids)]
            else:
                rec.project_scope_computed = [(6, 0, [])]


class PurchaseRequestLine(models.Model):
    _inherit = 'purchase.request.line'

    project_scope = fields.Many2one('project.scope.line', 'Project Scope')
    section = fields.Many2one('section.line', 'Section')
    variable = fields.Many2one('variable.template', 'Variable')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    product = fields.Many2one('product.product', 'Product')
    budget_quantity = fields.Float('Budget Quantity')
    is_orders = fields.Boolean('Is Orders', default=False)
    project = fields.Many2one(related='request_id.project', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                 compute='get_section_lines')
    type = fields.Selection([('material','Material'),
                            ('labour','Labour'),
                            ('overhead','Overhead'),
                            ('equipment','Equipment')],
                            string = "Type")


    # Material
    cs_material_id = fields.Many2one('material.material', string='CS Material ID')
    cs_material_gop_id = fields.Many2one('material.gop.material', string='CS Material GOP ID')
    bd_material_id = fields.Many2one('budget.material', string='BD Material ID')
    bd_material_ids = fields.Many2many('budget.material', string='BD Material IDS')
    bd_material_gop_id = fields.Many2one('budget.gop.material', string='BD Material GOP ID')
    bd_material_gop_ids = fields.Many2many('budget.gop.material', string='BD Material GOP IDS')

    # Labour
    cs_labour_id = fields.Many2one('material.labour', string='CS Labour ID')
    cs_labour_gop_id = fields.Many2one('material.gop.labour', string='CS Labour GOP ID')
    bd_labour_id = fields.Many2one('budget.labour', string='BD Labour ID')
    bd_labour_ids = fields.Many2many('budget.labour', string='BD Labour IDS')
    bd_labour_gop_id = fields.Many2one('budget.gop.labour', string='BD Labour GOP ID')
    bd_labour_gop_ids = fields.Many2many('budget.gop.labour', string='BD Labour GOP IDS')

    # Overhead
    cs_overhead_id = fields.Many2one('material.overhead', string='CS Overhead ID')
    cs_overhead_gop_id = fields.Many2one('material.gop.overhead', string='CS Overhead GOP ID')
    bd_overhead_id = fields.Many2one('budget.overhead', string='BD Overhead ID')
    bd_overhead_ids = fields.Many2many('budget.overhead', string='BD Overhead IDS')
    bd_overhead_gop_id = fields.Many2one('budget.gop.overhead', string='BD Overhead GOP ID')
    bd_overhead_gop_ids = fields.Many2many('budget.gop.overhead', string='BD Overhead GOP IDS')

    # Equipment
    cs_equipment_id = fields.Many2one('material.equipment', string='CS Equipment ID')
    cs_equipment_gop_id = fields.Many2one('material.gop.equipment', string='CS Equipment GOP ID')
    bd_equipment_id = fields.Many2one('budget.equipment', string='BD Equipment ID')
    bd_equipment_ids = fields.Many2many('budget.equipment', string='BD Equipment IDS')
    bd_equipment_gop_id = fields.Many2one('budget.gop.equipment', string='BD Equipment GOP ID')
    bd_equipment_gop_ids = fields.Many2many('budget.gop.equipment', string='BD Equipment GOP IDS')

    # Cancel boolean
    is_cancel = fields.Boolean('Is Cancel', default=False)

    @api.onchange('product_id', 'request_id.is_rental_orders')
    def _onchange_product_type(self):
        for res in self:
            if res.request_id.is_rental_orders == True:
                res.type = 'equipment'

    @api.onchange('type', 'request_id.is_multiple_budget', 'project_scope', 'section', 'product_id', 'group_of_product')
    def _onchange_product(self):
        for line in self:
            if line.request_id.budgeting_method == 'gop_budget':
                if line.project_scope and line.section and line.group_of_product:
                    if line.type == 'material':
                        line.cs_material_id = False
                        line.bd_material_id = False
                        line.bd_material_ids = False
                        line.cs_material_gop_id = False
                        line.bd_material_gop_id = False
                        line.bd_material_gop_ids = False
                        # line.cs_material_id = self.env['material.material'].search([('job_sheet_id', '=', line.request_id.cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
                        # convert above code to query
                        self.env.cr.execute("""SELECT id FROM material_material WHERE job_sheet_id = %s AND project_scope = %s AND section_name = %s AND group_of_product = %s AND product_id = %s""",
                        (line.request_id.cost_sheet.id, line.project_scope.id, line.section.id, line.group_of_product.id, line.product_id.id))
                        result = self.env.cr.fetchone()
                        if result:
                            line.cs_material_id = result[0]

                        # line.cs_material_gop_id = self.env['material.gop.material'].search([('job_sheet_id', '=', line.request_id.cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id)])
                        # convert above code to query
                        self.env.cr.execute("""SELECT id FROM material_gop_material WHERE job_sheet_id = %s AND project_scope = %s AND section_name = %s AND group_of_product = %s""",
                        (line.request_id.cost_sheet.id, line.project_scope.id, line.section.id, line.group_of_product.id))
                        result = self.env.cr.fetchone()
                        if result:
                            line.cs_material_gop_id = result[0]
                        if line.request_id.is_multiple_budget is False:
                            if line.request_id.project_budget:
                                # line.bd_material_id = self.env['budget.material'].search([('budget_id', '=', line.request_id.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
                                # convert above code to query
                                self.env.cr.execute("""SELECT id FROM budget_material WHERE budget_id = %s AND project_scope = %s AND section_name = %s AND group_of_product = %s AND product_id = %s""",
                                (line.request_id.project_budget.id, line.project_scope.id, line.section.id, line.group_of_product.id, line.product_id.id))
                                result = self.env.cr.fetchone()
                                if result:
                                    line.bd_material_id = result[0]

                                # line.bd_material_gop_id = self.env['budget.gop.material'].search([('budget_id', '=', line.request_id.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id)])
                                # convert above code to query
                                self.env.cr.execute("""SELECT id FROM budget_gop_material WHERE budget_id = %s AND project_scope = %s AND section_name = %s AND group_of_product = %s""",
                                (line.request_id.project_budget.id, line.project_scope.id, line.section.id, line.group_of_product.id))
                                result = self.env.cr.fetchone()
                                if result:
                                    line.bd_material_gop_id = result[0]
                        else:
                            budget_ids = []
                            budget_gop_ids = []
                            budget_mat_ids = []
                            budget = self.env['budget.gop.material'].search([('budget_id', 'in', line.request_id.multiple_budget_ids.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id)])
                            budget_mat = self.env['budget.material'].search([('budget_id', 'in', line.request_id.multiple_budget_ids.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])

                            if budget:
                                for bud in budget:
                                    budget_gop_ids.append((0,0, bud.id))

                            if budget_mat:
                                for buds in budget_mat:
                                    budget_mat_ids.append((0,0, buds.id))

                            line.bd_material_gop_ids = budget_gop_ids
                            line.bd_material_ids = budget_mat_ids

                    if line.type == 'labour':
                        line.cs_labour_id = False
                        line.bd_labour_id = False
                        line.bd_labour_ids = False
                        line.cs_labour_gop_id = False
                        line.bd_labour_gop_id = False
                        line.bd_labour_gop_ids = False
                        line.cs_labour_id = self.env['material.labour'].search([('job_sheet_id', '=', line.request_id.cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
                        line.cs_labour_gop_id = self.env['material.gop.labour'].search([('job_sheet_id', '=', line.request_id.cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id)])

                        if line.request_id.is_multiple_budget == False:
                            if line.request_id.project_budget:
                                line.bd_labour_id = self.env['budget.labour'].search([('budget_id', '=', line.request_id.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
                                line.bd_labour_gop_id = self.env['budget.gop.labour'].search([('budget_id', '=', line.request_id.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id)])

                        else:
                            budget_gop_ids = []
                            budget_lab_ids = []
                            budget = self.env['budget.gop.labour'].search([('budget_id', 'in', line.request_id.multiple_budget_ids.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id)])
                            budget_lab = self.env['budget.labour'].search([('budget_id', 'in', line.request_id.multiple_budget_ids.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])

                            if budget:
                                for bud in budget:
                                    budget_gop_ids.append((0,0, bud.id))

                            if budget_lab:
                                for buds in budget_lab:
                                    budget_lab_ids.append((0,0, buds.id))

                            line.bd_labour_gop_ids = budget_gop_ids
                            line.bd_labour_ids = budget_lab_ids

                    if line.type == 'overhead':
                        line.cs_overhead_id = False
                        line.bd_overhead_id = False
                        line.bd_overhead_ids = False
                        line.cs_overhead_gop_id = False
                        line.bd_overhead_gop_id = False
                        line.bd_overhead_gop_ids = False
                        # line.cs_overhead_id = self.env['material.overhead'].search([('job_sheet_id', '=', line.request_id.cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
                        # convert above code to query
                        self.env.cr.execute("""SELECT id FROM material_overhead WHERE job_sheet_id = %s AND project_scope = %s AND section_name = %s AND group_of_product = %s AND product_id = %s""",
                        (line.request_id.cost_sheet.id, line.project_scope.id, line.section.id, line.group_of_product.id, line.product_id.id))
                        result = self.env.cr.fetchone()
                        if result:
                            line.cs_overhead_id = result[0]

                        # line.cs_overhead_gop_id = self.env['material.gop.overhead'].search([('job_sheet_id', '=', line.request_id.cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id)])
                        # convert above code to query
                        self.env.cr.execute("""SELECT id FROM material_gop_overhead WHERE job_sheet_id = %s AND project_scope = %s AND section_name = %s AND group_of_product = %s""",
                        (line.request_id.cost_sheet.id, line.project_scope.id, line.section.id, line.group_of_product.id))
                        result = self.env.cr.fetchone()
                        if result:
                            line.cs_overhead_gop_id = result[0]

                        if line.request_id.is_multiple_budget is False:
                            if line.request_id.project_budget:
                                # line.bd_overhead_id = self.env['budget.overhead'].search([('budget_id', '=', line.request_id.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
                                # convert above code to query
                                self.env.cr.execute("""SELECT id FROM budget_overhead WHERE budget_id = %s AND project_scope = %s AND section_name = %s AND group_of_product = %s AND product_id = %s""",
                                (line.request_id.project_budget.id, line.project_scope.id, line.section.id, line.group_of_product.id, line.product_id.id))
                                result = self.env.cr.fetchone()
                                if result:
                                    line.bd_overhead_id = result[0]
                                # line.bd_overhead_gop_id = self.env['budget.gop.overhead'].search([('budget_id', '=', line.request_id.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id)])
                                # convert above code to query
                                self.env.cr.execute("""SELECT id FROM budget_gop_overhead WHERE budget_id = %s AND project_scope = %s AND section_name = %s AND group_of_product = %s""",
                                (line.request_id.project_budget.id, line.project_scope.id, line.section.id, line.group_of_product.id))
                                result = self.env.cr.fetchone()
                                if result:
                                    line.bd_overhead_gop_id = result[0]

                        else:
                            budget_gop_ids = []
                            budget_ove_ids = []
                            budget = self.env['budget.gop.overhead'].search([('budget_id', 'in', line.request_id.multiple_budget_ids.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id)])
                            budget_ove = self.env['budget.overhead'].search([('budget_id', 'in', line.request_id.multiple_budget_ids.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])

                            if budget:
                                for bud in budget:
                                    budget_gop_ids.append((0,0, bud.id))

                            if budget_ove:
                                for buds in budget:
                                    budget_ove_ids.append((0,0, buds.id))

                            line.bd_overhead_gop_ids = budget_gop_ids
                            line.bd_overhead_ids = budget_ove_ids

                    if line.type == 'equipment':
                        line.cs_equipment_id = False
                        line.bd_equipment_id = False
                        line.bd_equipment_ids = False
                        line.cs_equipment_gop_id = False
                        line.bd_equipment_gop_id = False
                        line.bd_equipment_gop_ids = False
                        # line.cs_equipment_id = self.env['material.equipment'].search([('job_sheet_id', '=', line.request_id.cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
                        # convert above code to query
                        self.env.cr.execute("""SELECT id FROM material_equipment WHERE job_sheet_id = %s AND project_scope = %s AND section_name = %s AND group_of_product = %s AND product_id = %s""",
                        (line.request_id.cost_sheet.id, line.project_scope.id, line.section.id, line.group_of_product.id, line.product_id.id))
                        result = self.env.cr.fetchone()
                        if result:
                            line.cs_equipment_id = result[0]
                        # line.cs_equipment_gop_id = self.env['material.gop.equipment'].search([('job_sheet_id', '=', line.request_id.cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id)])
                        # convert above code to query
                        self.env.cr.execute("""SELECT id FROM material_gop_equipment WHERE job_sheet_id = %s AND project_scope = %s AND section_name = %s AND group_of_product = %s""",
                        (line.request_id.cost_sheet.id, line.project_scope.id, line.section.id, line.group_of_product.id))
                        result = self.env.cr.fetchone()
                        if result:
                            line.cs_equipment_gop_id = result[0]

                        if line.request_id.is_multiple_budget is False:
                            if line.request_id.project_budget:
                                # line.bd_equipment_id = self.env['budget.equipment'].search([('budget_id', '=', line.request_id.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
                                # convert above code to query
                                self.env.cr.execute("""SELECT id FROM budget_equipment WHERE budget_id = %s AND project_scope = %s AND section_name = %s AND group_of_product = %s AND product_id = %s""",
                                (line.request_id.project_budget.id, line.project_scope.id, line.section.id, line.group_of_product.id, line.product_id.id))
                                result = self.env.cr.fetchone()
                                if result:
                                    line.bd_equipment_id = result[0]

                                # line.bd_equipment_gop_id = self.env['budget.gop.equipment'].search([('budget_id', '=', line.request_id.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id)])
                                # convert above code to query
                                self.env.cr.execute("""SELECT id FROM budget_gop_equipment WHERE budget_id = %s AND project_scope = %s AND section_name = %s AND group_of_product = %s""",
                                (line.request_id.project_budget.id, line.project_scope.id, line.section.id, line.group_of_product.id))
                                result = self.env.cr.fetchone()
                                if result:
                                    line.bd_equipment_gop_id = result[0]
                                line.budget_quantity = line.bd_equipment_id.qty_left
                            else:
                                line.budget_quantity = line.cs_equipment_id.budgeted_qty_left

                        else:
                            budget_gop_ids = []
                            budget_equ_ids = []
                            budget = self.env['budget.gop.equipment'].search([('budget_id', 'in', line.request_id.multiple_budget_ids.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id)])
                            budget_equ = self.env['budget.equipment'].search([('budget_id', 'in', line.request_id.multiple_budget_ids.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])

                            if budget:
                                for bud in budget:
                                    budget_gop_ids.append((0,0, bud.id))

                            if budget_equ:
                                for buds in budget_equ:
                                    budget_equ_ids.append((0,0, buds.id))
                                    line.budget_quantity += buds.qty_left
                            else:
                                line.budget_quantity = 0

                            line.bd_equipment_gop_ids = budget_gop_ids
                            line.bd_equipment_ids = budget_equ_ids

            elif line.request_id.budgeting_method in ('product_budget', 'budget_type', 'total_budget'):
                if line.project_scope and line.section and line.group_of_product and line.product_id:
                    if line.type == 'material':
                        line.cs_material_id = False
                        line.bd_material_id = False
                        line.bd_material_ids = False
                        # line.cs_material_id = self.env['material.material'].search([('job_sheet_id', '=', line.request_id.cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
                        # convert above code to query
                        self.env.cr.execute("""SELECT id FROM material_material WHERE job_sheet_id = %s AND project_scope = %s AND section_name = %s AND group_of_product = %s AND product_id = %s""", (line.request_id.cost_sheet.id, line.project_scope.id, line.section.id, line.group_of_product.id, line.product_id.id))
                        cs_material_id = self.env.cr.fetchone()
                        if cs_material_id:
                            line.cs_material_id = cs_material_id[0]
                        else:
                            line.cs_material_id = False

                        if line.request_id.is_multiple_budget is False:
                            if line.request_id.project_budget:
                                # line.bd_material_id = self.env['budget.material'].search([('budget_id', '=', line.request_id.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
                                # convert above code to query
                                self.env.cr.execute("""SELECT id FROM budget_material WHERE budget_id = %s AND project_scope = %s AND section_name = %s AND group_of_product = %s AND product_id = %s""", (line.request_id.project_budget.id, line.project_scope.id, line.section.id, line.group_of_product.id, line.product_id.id))
                                bd_material_id = self.env.cr.fetchone()
                                if bd_material_id:
                                    line.bd_material_id = bd_material_id[0]
                        else:
                            budget_ids = []
                            budget = self.env['budget.material'].search([('budget_id', 'in', line.request_id.multiple_budget_ids.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
                            if budget:
                                for bud in budget:
                                    budget_ids.append((0,0, bud.id))

                            line.bd_material_ids = budget_ids

                    if line.type == 'labour':
                        line.cs_labour_id = False
                        line.bd_labour_id = False
                        line.bd_labour_ids = False
                        line.cs_labour_id = self.env['material.labour'].search([('job_sheet_id', '=', line.request_id.cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])

                        if line.request_id.is_multiple_budget == False:
                            if line.request_id.project_budget:
                                line.bd_labour_id = self.env['budget.labour'].search([('budget_id', '=', line.request_id.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])

                        else:
                            budget_ids = []
                            budget = self.env['budget.labour'].search([('budget_id', 'in', line.request_id.multiple_budget_ids.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
                            if budget:
                                for bud in budget:
                                    budget_ids.append((0,0, bud.id))

                            line.bd_labour_ids = budget_ids

                    if line.type == 'overhead':
                        line.cs_overhead_id = False
                        line.bd_overhead_id = False
                        line.bd_overhead_ids = False
                        # line.cs_overhead_id = self.env['material.overhead'].search([('job_sheet_id', '=', line.request_id.cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
                        # convert above code to query
                        self.env.cr.execute("""SELECT id FROM material_overhead WHERE job_sheet_id = %s AND project_scope = %s AND section_name = %s AND group_of_product = %s AND product_id = %s""",
                        (line.request_id.cost_sheet.id, line.project_scope.id, line.section.id, line.group_of_product.id, line.product_id.id))
                        cs_overhead_id = self.env.cr.fetchone()
                        if cs_overhead_id:
                            line.cs_overhead_id = cs_overhead_id[0]

                        if line.request_id.is_multiple_budget is False:
                            if line.request_id.project_budget:
                                # line.bd_overhead_id = self.env['budget.overhead'].search([('budget_id', '=', line.request_id.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
                                # convert above code to query
                                self.env.cr.execute("""SELECT id FROM budget_overhead WHERE budget_id = %s AND project_scope = %s AND section_name = %s AND group_of_product = %s AND product_id = %s""",
                                (line.request_id.project_budget.id, line.project_scope.id, line.section.id, line.group_of_product.id, line.product_id.id))
                                bd_overhead_id = self.env.cr.fetchone()
                                if bd_overhead_id:
                                    line.bd_overhead_id = bd_overhead_id[0]
                        else:
                            budget_ids = []
                            budget = self.env['budget.overhead'].search([('budget_id', '=', line.request_id.multiple_budget_ids.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
                            if budget:
                                for bud in budget:
                                    budget_ids.append((0,0, bud.id))

                            line.bd_overhead_ids = budget_ids

                    if line.type == 'equipment':
                        line.cs_equipment_id = False
                        line.bd_equipment_id = False
                        line.bd_equipment_ids = False
                        # line.cs_equipment_id = self.env['material.equipment'].search([('job_sheet_id', '=', line.request_id.cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
                        # convert above code to query
                        self.env.cr.execute("""SELECT id FROM material_equipment WHERE job_sheet_id = %s AND project_scope = %s AND section_name = %s AND group_of_product = %s AND product_id = %s""",
                        (line.request_id.cost_sheet.id, line.project_scope.id, line.section.id, line.group_of_product.id, line.product_id.id))
                        cs_equipment_id = self.env.cr.fetchone()
                        if cs_equipment_id:
                            line.cs_equipment_id = cs_equipment_id[0]

                        if line.request_id.is_multiple_budget is False:
                            if line.request_id.project_budget:
                                # line.bd_equipment_id = self.env['budget.equipment'].search([('budget_id', '=', line.request_id.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
                                # convert above code to query
                                self.env.cr.execute("""SELECT id FROM budget_equipment WHERE budget_id = %s AND project_scope = %s AND section_name = %s AND group_of_product = %s AND product_id = %s""",
                                (line.request_id.project_budget.id, line.project_scope.id, line.section.id, line.group_of_product.id, line.product_id.id))
                                bd_equipment_id = self.env.cr.fetchone()
                                if bd_equipment_id:
                                    line.bd_equipment_id = bd_equipment_id[0]
                                line.budget_quantity = line.bd_equipment_id.qty_left
                            else:
                                line.budget_quantity = line.cs_equipment_id.budgeted_qty_left
                        else:
                            budget_ids = []
                            budget = self.env['budget.equipment'].search([('budget_id', '=', line.request_id.multiple_budget_ids.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
                            if budget:
                                for bud in budget:
                                    budget_ids.append((0,0, bud.id))
                                    line.budget_quantity += bud.qty_left
                            else:
                                line.budget_quantity = 0

                            line.bd_equipment_ids = budget_ids

    @api.depends('project.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.project.project_section_ids:
                    for line in rec.project.project_section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.onchange('group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            if rec.group_of_product:
                group_of_product = rec.group_of_product.id if rec.group_of_product else False
                return {
                    'domain': {'product_id': [('group_of_product', '=', group_of_product)]}
                }
            else:
                return {
                    'domain': {'product_id': []}
                }
    
    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self.product_id and self.group_of_product:
            if self.group_of_product.id not in self.product_id.group_of_product.ids:
                self.update({
                    'product_id': False,
                })

    def purchase_request_line_cancel(self):
        for rec in self:
            if rec.agreement_id and rec.agreement_id.state2 != "cancel":
                raise UserError(_("please cancel the purchase tender first!"))

            if not (all(element == 'cancel' for element in rec.purchase_lines.mapped('state'))):
                raise UserError(_("please cancel the purchase order first!"))
            else:
                rec.purchase_state = 'cancel'
                rec.is_cancel = True

                if rec.type == 'equipment':
                    if rec.bd_equipment_id:
                        rec.bd_equipment_id.qty_res = (rec.bd_equipment_id.qty_res - rec.product_qty)
                        rec.cs_equipment_id.reserved_qty = (rec.cs_equipment_id.reserved_qty - rec.product_qty)
                    else:
                        rec.cs_equipment_id.reserved_qty = (rec.cs_equipment_id.reserved_qty - rec.product_qty)

                all_count = len(rec.request_id.line_ids.ids)
                current_cancal_count = 0
                for line in rec.request_id.line_ids:
                    if line.purchase_state == 'cancel':
                        current_cancal_count += 1
                if all_count == current_cancal_count:
                    rec.request_id.purchase_req_state = 'cancel'
                    rec.request_id.state = 'cancel'

        return True

    @api.onchange('is_orders')
    def _onchange_is_orders(self):
        context = dict(self.env.context) or {}
        if context.get('orders'):
            self.is_orders = True

    @api.onchange('product_qty')
    def _check_qty_budget(self):
        for res in self:
            if res.request_id.budgeting_method == 'product_budget':
                if res.product_qty > res.budget_quantity:
                    raise ValidationError(_("The quantity is over the budget quantity"))
            else:
                pass

    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self.product and self.group_of_product:
            if self.group_of_product.id not in self.product.group_of_product.ids:
                self.update({
                    'product': False,
                })


class VariableLine(models.Model):
    _name = 'pr.variable.line'
    _description = "Variable Line Purchase Request"
    _order = "sequence"

    sequence = fields.Integer('Sequence', default=1)
    cs_subcon_id = fields.Many2one('material.subcon', string='CS Subcon ID')
    bd_subcon_id = fields.Many2one('budget.subcon', string='BD Subcon ID')
    bd_subcon_ids = fields.Many2many('budget.gop.overhead', string='BD Subcon IDS')
    sr_no = fields.Char('No.', compute="_sequence_ref")
    variable_id = fields.Many2one('purchase.request', string='Variable ID')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    variable = fields.Many2one('variable.template', string='Job Subcon')
    budget_quantity = fields.Float(string='Budget Quantity')
    quantity = fields.Float(string='Quantity')
    subcon_uom_category_id = fields.Many2one(related='variable.variable_uom.category_id')
    uom = fields.Many2one('uom.uom', string='Unit of Measure')
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section = fields.Many2one('section.line', string='Section')
    analytic_group = fields.Many2many('account.analytic.tag', string='Analytic Group')
    rfq_variable_id = fields.Many2one('rfq.variable.line')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'Waiting For Approval'),
        ('approved', 'Approved'),
        ('purchase_request', 'Purchase Request'),
        ('rfq', 'Request for Quotation'),
        ('purchase_order', 'Purchase Order'),
        ('purchase_agreement', 'Purchase Agreement'),
        ('rejected', 'Rejected'),
        ('done', 'done'),
        ('canceled', 'Canceled'),
        ], string='Purchase Status', default='draft')
    project = fields.Many2one(related='variable_id.project', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                 compute='get_section_lines')

    @api.onchange('variable_id.is_multiple_budget',  'project_scope', 'section', 'variable')
    def _onchange_subcon(self):
        for line in self:
            if line.project_scope and line.section and line.variable:
                line.cs_subcon_id = False
                line.bd_subcon_id = False
                line.bd_subcon_ids = False
                line.cs_subcon_id = self.env['material.subcon'].search([('job_sheet_id', '=', line.variable_id.cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('variable', '=', line.variable.id)])

                if line.variable_id.is_multiple_budget == False:
                    if line.variable_id.project_budget:
                        line.bd_subcon_id = self.env['budget.subcon'].search([('budget_id', '=', line.variable_id.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('subcon_id', '=', line.variable.id)])

                else:
                    budget_ids = []
                    budget = self.env['budget.subcon'].search([('budget_id', 'in', line.variable_id.multiple_budget_ids.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('subcon_id', '=', line.variable.id)])
                    if budget:
                        for bud in budget:
                            budget_ids.append((0,0, bud.id))

                    line.bd_subcon_ids = budget_ids

    @api.depends('project.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.project.project_section_ids:
                    for line in rec.project.project_section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    def send_bd_res_qty(self, res_qty_bd):
        return{
            'qty_res': res_qty_bd,
        }

    def send_cs_res_qty(self, res_qty_cs):
        return{
            'reserved_qty': res_qty_cs,
        }

    def update_res_bd(self, res, res_qty_bd):
        res.variable_id.project_budget.budget_subcon_ids = [(1, res.bd_subcon_id.id, res.send_bd_res_qty(res_qty_bd))]

    def update_res_cs(self, res, res_qty_cs):
        res.variable_id.cost_sheet.material_subcon_ids = [(1, res.cs_subcon_id.id, res.send_cs_res_qty(res_qty_cs))]

    def cancel_variable(self):
        for res in self:
            res_qty_bd = 0.00
            res_qty_cs = 0.00
            if res.rfq_variable_id:
                if res.rfq_variable_id.state == 'draft' or res.rfq_variable_id.state == 'canceled':
                    if res.bd_subcon_id:
                        res_qty_bd = res.bd_subcon_id.qty_res - res.quantity
                        res.update_res_bd(res, res_qty_bd)
                        res_qty_cs = res.cs_subcon_id.reserved_qty - res.quantity
                        res.update_res_cs(res, res_qty_cs)
                        res.write({'state' : 'canceled'})
                    else:
                        res_qty_cs = res.cs_subcon_id.reserved_qty - res.quantity
                        res.update_res_cs(res, res_qty_cs)
                        res.write({'state' : 'canceled'})
                else:
                    raise ValidationError(_("Please cancel the purchase order first"))
            else:
                res.write({'state' : 'canceled'})

    @api.onchange('variable')
    def onchange_variable(self):
        res = {}
        if not self.variable:
            return res
        self.uom = self.variable.variable_uom.id

    @api.onchange('quantity')
    def budget_quantity_validation(self):
        for res in self:
            if res.variable_id.budgeting_method == 'product_budget':
                if res.quantity > res.budget_quantity:
                    raise ValidationError(_("The quantity is over the remaining budget"))
            else:
                pass

    @api.depends('variable_id.variable_line_ids', 'variable_id.variable_line_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.variable_id.variable_line_ids:
                no += 1
                l.sr_no = no

    @api.model
    def create(self, vals):
        vals['sr_no'] = self.env['ir.sequence'].next_by_code('variable_purchase_request') or ('New')
        res = super(VariableLine, self).create(vals)
        return res


class PRMaterialLine(models.Model):
    _name = 'pr.material.line'
    _description = "Purchase Request Material Line"

    var_material_id = fields.Many2one('material.variable', string='VAR Material ID')
    bd_subcon_id = fields.Many2one('budget.subcon', string='BD Subcon ID')
    cs_subcon_id = fields.Many2one('material.subcon', string='CS Subcon ID')
    material_id = fields.Many2one('purchase.request', string='Material ID')
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section = fields.Many2one('section.line', string='Section')
    variable = fields.Many2one('variable.template', string='Variable')
    subcon = fields.Many2one('variable.template', string='Job Subcon')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    product = fields.Many2one('product.product', string='Product')
    description = fields.Char(string='Description')
    quantity = fields.Float(string='Quantity')
    budget_quantity = fields.Float(string='Budget Quantity')
    analytic_group = fields.Many2many('account.analytic.tag', string='Analytic Group')
    uom = fields.Many2one('uom.uom', string='Unit of Measure')
    request_date = fields.Date('Request Date', default=datetime.now())
    estimated_cost = fields.Monetary(
        string="Estimated Cost",
        currency_field="currency_id",
        default=0.0,
        help="Estimated cost of Purchase Request Line, not propagated to PO.")
    currency_id = fields.Many2one(related="company_id.currency_id", readonly=True)
    company_id = fields.Many2one('res.company', related='material_id.company_id',
                                 string='Company', store=True, readonly=True, default=lambda self: self.env.company)
    destination_warehouse = fields.Many2one('stock.warehouse', 'Destination Warehouse')
    purchased_qty = fields.Float('RFQ/PO Qty', readonly=True)
    purchase_status = fields.Selection(
        [('request_for_amendment', 'Request for Amendemnt'), ('draft', 'RFQ'), ('sent', 'RFQ Sent'),
         ('to_approve', 'To Approve'), ('waiting_for_approve', 'Waiting for Approval'),
         ('rfq_approved', 'RFQ Approved'),
         ('purchase', 'Purchase Order'), ('reject', 'Rejected'), ('done', 'Locked'),
         ('on_hold', 'On Hold'), ('cancel', 'Cancelled')],
        string="Purchase Status", readonly=True)
    project = fields.Many2one(related='material_id.project', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                 compute='get_section_lines')

    @api.depends('project.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.project.project_section_ids:
                    for line in rec.project.project_section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.onchange('product')
    def onchange_product(self):
        res = {}
        if not self.product:
            return res
        self.quantity = 1.0
        self.uom = self.product.uom_id.id

    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self.product and self.group_of_product:
            if self.group_of_product.id not in self.product.group_of_product.ids:
                self.update({
                    'product': False,
                })


class PRServiceLine(models.Model):
    _name = 'pr.service.line'
    _description = "Purchase Request Service Line"

    service_id = fields.Many2one('purchase.request', string='Service ID')
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section = fields.Many2one('section.line', string='Section')
    variable = fields.Many2one('variable.template', string='Variable')
    subcon = fields.Many2one('variable.template', string='Job Subcon')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    product = fields.Many2one('product.product', string='Product')
    description = fields.Char(string='Description')
    quantity = fields.Float(string='Quantity')
    budget_quantity = fields.Float(string='Budget Quantity')
    analytic_group = fields.Many2many('account.analytic.tag', string='Analytic Group')
    uom = fields.Many2one('uom.uom', string='Unit of Measure')
    request_date = fields.Date('Request Date', default=datetime.now())
    estimated_cost = fields.Monetary(
        string="Estimated Cost",
        currency_field="currency_id",
        default=0.0,
        help="Estimated cost of Purchase Request Line, not propagated to PO.")
    currency_id = fields.Many2one(related="company_id.currency_id", readonly=True)
    company_id = fields.Many2one('res.company', related='service_id.company_id',
                                 string='Company', store=True, readonly=True, default=lambda self: self.env.company)
    destination_warehouse = fields.Many2one('stock.warehouse', 'Destination Warehouse')
    purchased_qty = fields.Float('RFQ/PO Qty', readonly=True)
    purchase_status = fields.Selection(
        [('request_for_amendment', 'Request for Amendemnt'), ('draft', 'RFQ'), ('sent', 'RFQ Sent'),
         ('to_approve', 'To Approve'), ('waiting_for_approve', 'Waiting for Approval'),
         ('rfq_approved', 'RFQ Approved'),
         ('purchase', 'Purchase Order'), ('reject', 'Rejected'), ('done', 'Locked'),
         ('on_hold', 'On Hold'), ('cancel', 'Cancelled')],
        string="Purchase Status", readonly=True)

    project = fields.Many2one(related='service_id.project', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                 compute='get_section_lines')

    @api.depends('project.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.project.project_section_ids:
                    for line in rec.project.project_section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.onchange('product')
    def onchange_product(self):
        res = {}
        if not self.product:
            return res
        self.quantity = 1.0
        self.uom = self.product.uom_id.id

    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self.product and self.group_of_product:
            if self.group_of_product.id not in self.product.group_of_product.ids:
                self.update({
                    'product': False,
                })


class PREquipmentLine(models.Model):
    _name = 'pr.equipment.line'
    _description = "Purchase Request Equipment Line"

    equipment_id = fields.Many2one('purchase.request', string='Equipment ID')
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section = fields.Many2one('section.line', string='Section')
    variable = fields.Many2one('variable.template', string='Variable')
    subcon = fields.Many2one('variable.template', string='Job Subcon')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    product = fields.Many2one('product.product', string='Product')
    description = fields.Char(string='Description')
    quantity = fields.Float(string='Quantity')
    budget_quantity = fields.Float(string='Budget Quantity')
    analytic_group = fields.Many2many('account.analytic.tag', string='Analytic Group')
    uom = fields.Many2one('uom.uom', 'UoM')
    request_date = fields.Date('Request Date', default=datetime.now())
    estimated_cost = fields.Monetary(
        string="Estimated Cost",
        currency_field="currency_id",
        default=0.0,
        help="Estimated cost of Purchase Request Line, not propagated to PO.",)
    currency_id = fields.Many2one(related="company_id.currency_id", readonly=True)
    company_id = fields.Many2one('res.company', related='equipment_id.company_id',
                                 string='Company', store=True, readonly=True, default=lambda self: self.env.company)
    destination_warehouse = fields.Many2one('stock.warehouse', 'Destination Warehouse')
    purchased_qty = fields.Float('RFQ/PO Qty', readonly=True)
    purchase_status = fields.Selection(
        [('request_for_amendment', 'Request for Amendemnt'), ('draft', 'RFQ'), ('sent', 'RFQ Sent'),
         ('to_approve', 'To Approve'), ('waiting_for_approve', 'Waiting for Approval'),
         ('rfq_approved', 'RFQ Approved'),
         ('purchase', 'Purchase Order'), ('reject', 'Rejected'), ('done', 'Locked'),
         ('on_hold', 'On Hold'), ('cancel', 'Cancelled')],
        string="Purchase Status", readonly=True)

    project = fields.Many2one(related='equipment_id.project', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                 compute='get_section_lines')

    @api.depends('project.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.project.project_section_ids:
                    for line in rec.project.project_section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.onchange('product')
    def onchange_product(self):
        res = {}
        if not self.product:
            return res
        self.quantity = 1.0
        self.uom = self.product.uom_id.id

    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self.product and self.group_of_product:
            if self.group_of_product.id not in self.product.group_of_product.ids:
                self.update({
                    'product': False,
                })


class PRLabourLine(models.Model):
    _name = 'pr.labour.line'
    _description = "Purchase Request Labour Line"

    labour_id = fields.Many2one('purchase.request', string='Labour ID')
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section = fields.Many2one('section.line', string='Section')
    variable = fields.Many2one('variable.template', string='Variable')
    subcon = fields.Many2one('variable.template', string='Job Subcon')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    product = fields.Many2one('product.product', string='Product')
    description = fields.Char(string='Description')
    quantity = fields.Float(string='Quantity')
    budget_quantity = fields.Float(string='Budget Quantity')
    analytic_group = fields.Many2many('account.analytic.tag', string='Analytic Group')
    uom = fields.Many2one('uom.uom', string='Unit of Measure')
    request_date = fields.Date('Request Date', default=datetime.now())
    estimated_cost = fields.Monetary(
        string="Estimated Cost",
        currency_field="currency_id",
        default=0.0,
        help="Estimated cost of Purchase Request Line, not propagated to PO.")
    currency_id = fields.Many2one(related="company_id.currency_id", readonly=True)
    company_id = fields.Many2one('res.company', related='labour_id.company_id',
                                 string='Company', store=True, readonly=True, default=lambda self: self.env.company)
    destination_warehouse = fields.Many2one('stock.warehouse', 'Destination Warehouse')
    purchased_qty = fields.Float('RFQ/PO Qty', readonly=True)
    purchase_status = fields.Selection(
        [('request_for_amendment', 'Request for Amendemnt'), ('draft', 'RFQ'), ('sent', 'RFQ Sent'),
         ('to_approve', 'To Approve'), ('waiting_for_approve', 'Waiting for Approval'),
         ('rfq_approved', 'RFQ Approved'),
         ('purchase', 'Purchase Order'), ('reject', 'Rejected'), ('done', 'Locked'),
         ('on_hold', 'On Hold'), ('cancel', 'Cancelled')],
        string="Purchase Status", readonly=True)

    project = fields.Many2one(related='labour_id.project', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                 compute='get_section_lines')

    @api.depends('project.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.project.project_section_ids:
                    for line in rec.project.project_section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.onchange('product')
    def onchange_product(self):
        res = {}
        if not self.product:
            return res
        self.quantity = 1.0
        self.uom = self.product.uom_id.id

    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self.product and self.group_of_product:
            if self.group_of_product.id not in self.product.group_of_product.ids:
                self.update({
                    'product': False,
                })


class PROverheadLine(models.Model):
    _name = 'pr.overhead.line'
    _description = "Purchase Request Overhead Line"

    overhead_id = fields.Many2one('purchase.request', string='Overhead ID')
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section = fields.Many2one('section.line', string='Section')
    variable = fields.Many2one('variable.template', string='Variable')
    subcon = fields.Many2one('variable.template', string='Job Subcon')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    product = fields.Many2one('product.product', string='Product')
    description = fields.Char(string='Description')
    quantity = fields.Float(string='Quantity')
    budget_quantity = fields.Float(string='Budget Quantity')
    analytic_group = fields.Many2many('account.analytic.tag', string='Analytic Group')
    uom = fields.Many2one('uom.uom', string='Unit of Measure')
    request_date = fields.Date('Request Date', default=datetime.now())
    estimated_cost = fields.Monetary(
        string="Estimated Cost",
        currency_field="currency_id",
        default=0.0,
        help="Estimated cost of Purchase Request Line, not propagated to PO.")
    currency_id = fields.Many2one(related="company_id.currency_id", readonly=True)
    company_id = fields.Many2one('res.company', related='overhead_id.company_id',
                                 string='Company', store=True, readonly=True, default=lambda self: self.env.company)
    destination_warehouse = fields.Many2one('stock.warehouse', 'Destination Warehouse')
    purchased_qty = fields.Float('RFQ/PO Qty', readonly=True)
    purchase_status = fields.Selection(
        [('request_for_amendment', 'Request for Amendemnt'), ('draft', 'RFQ'), ('sent', 'RFQ Sent'),
         ('to_approve', 'To Approve'), ('waiting_for_approve', 'Waiting for Approval'),
         ('rfq_approved', 'RFQ Approved'),
         ('purchase', 'Purchase Order'), ('reject', 'Rejected'), ('done', 'Locked'),
         ('on_hold', 'On Hold'), ('cancel', 'Cancelled')],
        string="Purchase Status", readonly=True)

    project = fields.Many2one(related='overhead_id.project', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                 compute='get_section_lines')

    @api.depends('project.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.project.project_section_ids:
                    for line in rec.project.project_section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.onchange('product')
    def onchange_product(self):
        res = {}
        if not self.product:
            return res
        self.quantity = 1.0
        self.uom = self.product.uom_id.id

    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self.product and self.group_of_product:
            if self.group_of_product.id not in self.product.group_of_product.ids:
                self.update({
                    'product': False,
                })
