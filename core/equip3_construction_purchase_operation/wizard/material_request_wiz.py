from datetime import datetime
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError, Warning


class MaterialRequestWiz(models.TransientModel):
    _name = 'material.request.wiz'
    _description = 'Create Material Request Wizard'

    cost_sheet = fields.Many2one('job.cost.sheet', string='Cost Sheet')
    destination_warehouse = fields.Many2one('stock.warehouse', required=True, string="Destination warehouse")
    analytic_group = fields.Many2many('account.analytic.tag', required=True, string="Analytic group")
    budgeting_period = fields.Selection([
        ('project', 'Project Length Budgeting'),
        ('monthly', 'Monthly Budgeting'),
        ('custom', 'Custom Time Budgeting'),], string='Budgeting Period')
    multiple_budget_ids = fields.Many2many('project.budget', string='Multiple Budget')
    is_multiple_budget = fields.Boolean('Multiple Budget', default=False)
    type_of_mr = fields.Selection([
        ('material', 'Material'), 
        ('labour', 'Labour'), 
        ('overhead', 'Overhead'),
        ('equipment', 'Equipment Lease'), 
        ('subcon', 'Subcon Agreement')],
        string="Type of Request")
    schedule_date = fields.Date('Scheduled Date', required='1')
    is_material = fields.Boolean(string='Subcon', default=False)
    is_subcon = fields.Boolean(string='Subcon', default=False)
    is_rental = fields.Boolean(string='Subcon', default=False)
    is_multiple_budget_procurement = fields.Boolean(string="Is Multiple Budget", compute='_is_multiple_budget_procurement')
    
    def _is_multiple_budget_procurement(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_multiple_budget_procurement = IrConfigParam.get_param('is_multiple_budget_procurement')
        for record in self:
            record.is_multiple_budget_procurement = is_multiple_budget_procurement
    
    def _get_project_budget(self):
        for rec in self:
            Job_cost_sheet = rec.cost_sheet
            if rec.schedule_date:
                schedule = datetime.strptime(str(self.schedule_date), "%Y-%m-%d")
                month_date = schedule.strftime("%B")
                if Job_cost_sheet.project_id.budgeting_period == 'monthly':
                    data = rec.env['budget.period.line'].search([('month', '=', month_date),
                                                                ('line_project_ids', '=', Job_cost_sheet.project_id.id),], limit=1)
                    budget = rec.env['project.budget'].search([('project_id', '=', Job_cost_sheet.project_id.id),
                                                                ('cost_sheet', '=', Job_cost_sheet.id),
                                                                ('month', '=', data.id)], limit=1)
                    return budget
                elif Job_cost_sheet.project_id.budgeting_period == 'custom':
                    budget = rec.env['project.budget'].search([('project_id', '=', Job_cost_sheet.project_id.id),
                                                                ('cost_sheet', '=', Job_cost_sheet.id),
                                                                ('bd_start_date', '<=', rec.schedule_date),
                                                                ('bd_end_date', '>=', rec.schedule_date)], limit=1)
                    return budget
                else:
                    pass

    @api.onchange('is_multiple_budget')
    def _onchange_multiple_budget(self):
        for rec in self:
            Job_cost_sheet = rec.cost_sheet
            return {
                'domain': {'multiple_budget_ids': [('project_id','=',Job_cost_sheet.project_id.id)]}
            }
        
    # Subcon Cost sheet to PR
    def prepare_purchase_request(self, record):
        return{
            'origin' : record.number,
            'company_id' : record.company_id.id,
            'project': record.project_id.id,
            'cost_sheet': record.id,
            'analytic_account_group_ids': [(6, 0, [v.id for v in record.account_tag_ids])],
            'branch_id': record.branch_id.id,
            'destination_warehouse': self.destination_warehouse.id,
            'is_subcontracting':True,
            'is_services_orders':True,
        } 

    # Equipment Lease Cost Sheet to PR
    def prepare_purchase_rental(self, record):
        return {
            'origin' : record.number,
            'company_id' : record.company_id.id,
            'project': record.project_id.id,
            'cost_sheet': record.id,
            'analytic_account_group_ids': [(6, 0, [v.id for v in record.account_tag_ids])],
            'branch_id': record.branch_id.id,
            'destination_warehouse': self.destination_warehouse.id,
            'branch_id': record.branch_id.id
        }
    
    # Material / Labour / Overhead Cost Sheet to MR
    def prepare_product_lines(self, record):
        return {
            'project': record.project_id.id,
            'job_cost_sheet': record.id,
            'destination_warehouse_id': self.destination_warehouse.id,
            'analytic_account_group_ids': [(6, 0, [v.id for v in record.account_tag_ids])],
            'schedule_date': self.schedule_date,
            'type_of_mr': self.type_of_mr,
            'source_document': record.number,
        }
    
    # Subcon Budget to PR
    def prepare_purchase_request_budget_subcon(self, budget):
        return{
            'branch_id': budget.branch_id.id,
            'origin' : budget.name,
            'company_id' : budget.company_id.id,
            'project': budget.project_id.id,
            'cost_sheet': budget.cost_sheet.id,
            'analytic_account_group_ids': [(6, 0, [v.id for v in budget.analytic_group_id])],
            'project_budget': budget.id,
            'is_multiple_budget': self.is_multiple_budget,
            'multiple_budget_ids': [(6, 0, [v.id for v in self.multiple_budget_ids])],
            'destination_warehouse': self.destination_warehouse.id,
        } 
    
    # Equipment Lease Budget to PR
    def prepare_purchase_request_budget_equipment(self, budget):
        return{
            'branch_id': budget.branch_id.id,
            'origin' : budget.name,
            'company_id' : budget.company_id.id,
            'project': budget.project_id.id,
            'cost_sheet': budget.cost_sheet.id,
            'analytic_account_group_ids': [(6, 0, [v.id for v in budget.analytic_group_id])],
            'project_budget': budget.id,
            'is_multiple_budget': self.is_multiple_budget,
            'multiple_budget_ids': [(6, 0, [v.id for v in self.multiple_budget_ids])],
            'destination_warehouse': self.destination_warehouse.id,
        } 
    
    # Material / Labour / Overhead Budget to MR
    def prepare_product_lines_budget(self, budget):
        return {
            'project': budget.project_id.id,
            'job_cost_sheet': budget.cost_sheet.id,
            'destination_warehouse_id': self.destination_warehouse.id,
            'analytic_account_group_ids': [(6, 0, [v.id for v in budget.analytic_group_id])],
            'project_budget': budget.id,
            'is_multiple_budget': self.is_multiple_budget,
            'multiple_budget_ids': [(6, 0, [v.id for v in self.multiple_budget_ids])],
            'schedule_date': self.schedule_date,
            'type_of_mr': self.type_of_mr,
            'source_document': budget.name,
        }

    def create_material_request_submit(self):
        Job_cost_sheet = self.cost_sheet
        budget = self._get_project_budget()
        if self.budgeting_period != 'project':
            if not budget:
                raise ValidationError(_("There is no periodical budget created for this date"))
            else:
                for bud in budget:
                    if bud.state != 'in_progress':
                        raise ValidationError(_("Please in progress the periodical budget '{}' first.".format(budget.name)))   
                    
        if self.type_of_mr == 'equipment':
            bud_qty_left = 0
            bud_amt_left = 0

            context = {
                'rentals_orders': 1, 
                'default_is_rental_orders':True,
                'default_is_single_request_date':True,
                'default_is_single_delivery_destination':True,
                'default_requested_by': self.env.uid,
                'default_request_date': self.schedule_date,
            }
            
            for record in Job_cost_sheet:
                if record.budgeting_method == 'product_budget':
                    if self.budgeting_period == 'project':
                        for line_id in record.material_equipment_ids:
                            bud_qty_left += line_id.budgeted_qty_left
                            bud_amt_left += line_id.budgeted_amt_left
                        if bud_qty_left < 1 or bud_amt_left < 1 :
                            raise ValidationError("There is no budget for equipment lease left")
                    else:
                        if self.is_multiple_budget == False:
                            for line_bud in budget.budget_equipment_ids:
                                bud_qty_left += line_bud.qty_left
                                bud_amt_left += line_bud.amt_left
                            if bud_qty_left < 1 or bud_amt_left < 1 :
                                raise ValidationError("There is no budget for equipment lease left")
                        else:
                            for budget_id in self.multiple_budget_ids:
                                for bud in budget_id.budget_equipment_ids:
                                    bud_qty_left += bud.qty_left
                                    bud_amt_left += bud.amt_left
                            if bud_qty_left < 1 or bud_amt_left < 1 :
                                raise ValidationError("There is no budget for equipment lease left")
                
                elif record.budgeting_method == 'gop_budget':
                    if self.budgeting_period == 'project':
                        for line_id in record.material_equipment_gop_ids:
                            bud_amt_left += line_id.budgeted_amt_left
                        if bud_amt_left < 1 :
                            raise ValidationError("There is no budget for subcon left")
                    else:
                        if self.is_multiple_budget == False:
                            for line_bud in budget.budget_equipment_gop_ids:
                                bud_amt_left += line_bud.amt_left
                            if bud_amt_left < 1 :
                                raise ValidationError("There is no budget for subcon left")
                        else:
                            for budget_id in self.multiple_budget_ids:
                                for bud in budget_id.budget_equipment_gop_ids:
                                    bud_amt_left += bud.amt_left
                            if bud_amt_left < 1 :
                                raise ValidationError("There is no budget for subcon left")
                
                elif record.budgeting_method == 'budget_type':
                    if self.budgeting_period == 'project':
                        if record.equipment_budget_left < 1 :
                            raise ValidationError("There is no budget for subcon left")
                    else:
                        if self.is_multiple_budget == False:
                            if budget.amount_left_equipment < 1 :
                                raise ValidationError("There is no budget for subcon left")
                        else:
                            for budget_id in self.multiple_budget_ids:
                                bud_amt_left += budget_id.amount_left_equipment
                            if bud_amt_left < 1 :
                                raise ValidationError("There is no budget for subcon left")

                elif record.budgeting_method == 'total_budget':
                    if self.budgeting_period == 'project':
                        if record.contract_budget_left < 1 :
                            raise ValidationError("There is no budget for subcon left")
                        for line_id in record.material_equipment_ids:
                            bud_qty_left += line_id.budgeted_qty_left
                            bud_amt_left += line_id.budgeted_amt_left
                        if bud_qty_left < 1 or bud_amt_left < 1 :
                            raise ValidationError("There is no budget for equipment lease left")
                    else:
                        for line_bud in budget.budget_equipment_ids:
                            bud_qty_left += line_bud.qty_left
                            bud_amt_left += line_bud.amt_left
                        if bud_qty_left < 1 or bud_amt_left < 1:
                            raise ValidationError("There is no budget for equipment lease left")
                
                if self.budgeting_period == 'project':
                    purchase_request = self.env['purchase.request'].with_context(context).create(self.prepare_purchase_rental(record))
                else:
                    if self.is_multiple_budget == False:
                        purchase_request = self.env['purchase.request'].with_context(context).create(self.prepare_purchase_request_budget_equipment(budget))
                    else:
                        raise ValidationError("Need Develop")
                    
                for res in purchase_request:
                    res.line_ids = [(5, 0, 0)] 
                    if self.budgeting_period == 'project':
                        res.get_equipment_table_form_cs(res)
                    else:
                        if self.is_multiple_budget == False:
                            res.get_equipment_table_form_bd(res)
                        else:
                            raise ValidationError("Need Develop")
                        
                    for line in res.line_ids:
                        line._onchange_product()
                
                return {
                        'type': 'ir.actions.act_window',
                        'name': 'Purchase Request',
                        'view_mode': 'form',
                        'res_model': 'purchase.request',
                        'res_id' : purchase_request.id,
                        'target': 'current'
                    }
    
        elif self.type_of_mr == 'subcon':
            bud_qty_left = 0
            bud_amt_left = 0
            
            context = {'services_good': 1,
                       'default_is_services_orders': True,
                       'default_is_subcontracting': True,
                       'default_is_single_request_date' : True,
                       'default_requested_by': self.env.uid,
                       'default_request_date' : self.schedule_date,
                      }
            
            for record in Job_cost_sheet:
                if record.budgeting_method == 'product_budget':
                    if self.budgeting_period == 'project':
                        for line_id in record.material_subcon_ids:
                            bud_qty_left += line_id.budgeted_qty_left
                            bud_amt_left += line_id.budgeted_amt_left
                        if bud_qty_left < 1 or bud_amt_left < 1 :
                            raise ValidationError("There is no budget for subcon left")
                    else:
                        if self.is_multiple_budget == False:
                            for line_bud in budget.budget_subcon_ids:
                                bud_qty_left += line_bud.qty_left
                                bud_amt_left += line_bud.amt_left
                            if bud_qty_left < 1 or bud_amt_left < 1 :
                                raise ValidationError("There is no budget for subcon left")
                        else:
                            for budget_id in self.multiple_budget_ids:
                                for bud in budget_id.budget_subcon_ids:
                                    bud_qty_left += bud.qty_left
                                    bud_amt_left += bud.amt_left
                            if bud_qty_left < 1 or bud_amt_left < 1 :
                                raise ValidationError("There is no budget for subcon left")
                
                elif record.budgeting_method == 'gop_budget':
                    if self.budgeting_period == 'project':
                        for subcon in record.material_subcon_ids:
                            bud_amt_left += subcon.budgeted_amt_left
                        if bud_amt_left < 1 :
                            raise ValidationError("There is no budget for subcon left")
                    else:
                        if self.is_multiple_budget == False:
                            for line_bud in budget.budget_subcon_ids:
                                bud_amt_left += line_bud.amt_left
                            if bud_amt_left < 1 :
                                raise ValidationError("There is no budget for subcon left")
                        else:
                            for budget_id in self.multiple_budget_ids:
                                for bud in budget_id.budget_subcon_ids:
                                    bud_amt_left += bud.amt_left
                            if bud_amt_left < 1 :
                                raise ValidationError("There is no budget for subcon left")
                
                elif record.budgeting_method == 'budget_type':
                    if self.budgeting_period == 'project':
                        if record.subcon_budget_left < 1 :
                            raise ValidationError("There is no budget for subcon left")
                    else:
                        if self.is_multiple_budget == False:
                            if budget.amount_left_subcon < 1 :
                                raise ValidationError("There is no budget for subcon left")
                        else:
                            for budget_id in self.multiple_budget_ids:
                                bud_amt_left += budget_id.amount_left_subcon
                            if bud_amt_left < 1 :
                                raise ValidationError("There is no budget for subcon left")

                elif record.budgeting_method == 'total_budget':
                    if self.budgeting_period == 'project':
                        if record.contract_budget_left < 1 :
                            raise ValidationError("There is no budget for subcon left")
                        for line_id in record.material_subcon_ids:
                            bud_qty_left += line_id.budgeted_qty_left
                            bud_amt_left += line_id.budgeted_amt_left
                        if bud_qty_left < 1 or bud_amt_left < 1 :
                            raise ValidationError("There is no budget for subcon left")
                    else:
                        for line_bud in budget.budget_subcon_ids:
                            bud_qty_left += line_bud.qty_left
                            bud_amt_left += line_bud.amt_left
                        if bud_qty_left < 1 or bud_amt_left < 1:
                            raise ValidationError("There is no budget for subcon left")
                
                if self.budgeting_period == 'project':
                    purchase_request = self.env['purchase.request'].with_context(context).create(self.prepare_purchase_request(record))
                else:
                    if self.is_multiple_budget == False:
                        purchase_request = self.env['purchase.request'].with_context(context).create(self.prepare_purchase_request_budget_subcon(budget))
                    else:
                        raise ValidationError("Need Develop")
                    
                for res in purchase_request:
                    res.variable_line_ids = False
                    if self.budgeting_period == 'project':
                        res.get_subcon_table_form_cs(res)
                    else:
                        if self.is_multiple_budget == False:
                            res.get_subcon_table_form_bd(res)
                        else:
                            raise ValidationError("Need Develop")
            
                    for line in res.variable_line_ids:
                        line._onchange_subcon()

                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Purchase Request',
                    'view_mode': 'form',
                    'res_model': 'purchase.request',
                    'res_id' : purchase_request.id,
                    'target': 'current'
                }
                
        else:
            bud_qty_left = 0
            bud_amt_left = 0

            for record in Job_cost_sheet:
                if self.type_of_mr == 'material':
                    if record.budgeting_method == 'product_budget':
                        if self.budgeting_period == 'project':
                            for line_id in record.material_ids:
                                bud_qty_left += line_id.budgeted_qty_left
                                bud_amt_left += line_id.budgeted_amt_left
                            if bud_qty_left < 1 or bud_amt_left < 1 :
                                raise ValidationError("There is no budget for material left")
                        else:
                            if self.is_multiple_budget == False:
                                for line_bud in budget.budget_material_ids:
                                    bud_qty_left += line_bud.qty_left
                                    bud_amt_left += line_bud.amt_left
                                if bud_qty_left < 1 or bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for material left")
                            else:
                                for budget_id in self.multiple_budget_ids:
                                    for bud in budget_id.budget_material_ids:
                                        bud_qty_left += bud.qty_left
                                        bud_amt_left += bud.amt_left
                                if bud_qty_left < 1 or bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for material left")
                    
                    elif record.budgeting_method == 'gop_budget':
                        if self.budgeting_period == 'project':
                            for line_id in record.material_gop_ids:
                                bud_amt_left += line_id.budgeted_amt_left
                            if bud_amt_left < 1 :
                                raise ValidationError("There is no budget for material left")
                        else:
                            if self.is_multiple_budget == False:
                                for line_bud in budget.budget_material_gop_ids:
                                    bud_amt_left += line_bud.amt_left
                                if bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for material left")
                            else:
                                for budget_id in self.multiple_budget_ids:
                                    for bud in budget_id.budget_material_gop_ids:
                                        bud_amt_left += bud.amt_left
                                if bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for material left")
                    
                    elif record.budgeting_method == 'budget_type':
                        if self.budgeting_period == 'project':
                            if record.material_budget_left < 1 :
                                raise ValidationError("There is no budget for material left")
                        else:
                            if self.is_multiple_budget == False:
                                if budget.amount_left_material < 1 :
                                    raise ValidationError("There is no budget for material left")
                            else:
                                for budget_id in self.multiple_budget_ids:
                                    bud_amt_left += budget_id.amount_left_material
                                if bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for material left")

                    elif record.budgeting_method == 'total_budget':
                        if self.budgeting_period == 'project':
                            if record.contract_budget_left < 1 :
                                raise ValidationError("There is no budget for material left")
                            for line_id in record.material_ids:
                                bud_qty_left += line_id.budgeted_qty_left
                                bud_amt_left += line_id.budgeted_amt_left
                            if bud_qty_left < 1 or bud_amt_left < 1 :
                                raise ValidationError("There is no budget for material left")
                        else:
                            for line_bud in budget.budget_material_ids:
                                bud_qty_left += line_bud.qty_left
                                bud_amt_left += line_bud.amt_left
                            if bud_qty_left < 1 or bud_amt_left < 1:
                                raise ValidationError("There is no budget for material left")

                elif self.type_of_mr == 'labour':
                    if record.budgeting_method == 'product_budget':
                        if self.budgeting_period == 'project':
                            for line_id in record.material_labour_ids:
                                bud_qty_left += line_id.budgeted_qty_left
                                bud_amt_left += line_id.budgeted_amt_left
                            if bud_qty_left < 1 or bud_amt_left < 1 :
                                raise ValidationError("There is no budget for labour left")
                        else:
                            if self.is_multiple_budget == False:
                                for line_bud in budget.budget_labour_ids:
                                    bud_qty_left += line_bud.qty_left
                                    bud_amt_left += line_bud.amt_left
                                if bud_qty_left < 1 or bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for labour left")
                            else:
                                for budget_id in self.multiple_budget_ids:
                                    for bud in budget_id.budget_labour_ids:
                                        bud_qty_left += bud.qty_left
                                        bud_amt_left += bud.amt_left
                                if bud_qty_left < 1 or bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for labour left")
                    
                    elif record.budgeting_method == 'gop_budget':
                        if self.budgeting_period == 'project':
                            for line_id in record.material_labour_gop_ids:
                                bud_amt_left += line_id.budgeted_amt_left
                            if bud_amt_left < 1 :
                                raise ValidationError("There is no budget for labour left")
                        else:
                            if self.is_multiple_budget == False:
                                for line_bud in budget.budget_labour_gop_ids:
                                    bud_amt_left += line_bud.amt_left
                                if bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for labour left")
                            else:
                                for budget_id in self.multiple_budget_ids:
                                    for bud in budget_id.budget_labour_gop_ids:
                                        bud_amt_left += bud.amt_left
                                if bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for labour left")
                    
                    elif record.budgeting_method == 'budget_type':
                        if self.budgeting_period == 'project':
                            if record.labour_budget_left < 1 :
                                raise ValidationError("There is no budget for labour left")
                        else:
                            if self.is_multiple_budget == False:
                                if budget.amount_left_labour < 1 :
                                    raise ValidationError("There is no budget for labour left")
                            else:
                                for budget_id in self.multiple_budget_ids:
                                    bud_amt_left += budget_id.amount_left_labour
                                if bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for labour left")

                    elif record.budgeting_method == 'total_budget':
                        if self.budgeting_period == 'project':
                            if record.contract_budget_left < 1 :
                                raise ValidationError("There is no budget for labour left")
                        else:
                            raise ValidationError("Need Develop")

                elif self.type_of_mr == 'overhead':
                    if record.budgeting_method == 'product_budget':
                        if self.budgeting_period == 'project':
                            for line_id in record.material_overhead_ids:
                                bud_qty_left += line_id.budgeted_qty_left
                                bud_amt_left += line_id.budgeted_amt_left
                            if bud_qty_left < 1 or bud_amt_left < 1 :
                                raise ValidationError("There is no budget for overhead left")
                        else:
                            if self.is_multiple_budget == False:
                                for line_bud in budget.budget_overhead_ids:
                                    bud_qty_left += line_bud.qty_left
                                    bud_amt_left += line_bud.amt_left
                                if bud_qty_left < 1 or bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for overhead left")
                            else:
                                for budget_id in self.multiple_budget_ids:
                                    for bud in budget_id.budget_overhead_ids:
                                        bud_qty_left += bud.qty_left
                                        bud_amt_left += bud.amt_left
                                if bud_qty_left < 1 or bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for overhead left")
                    
                    elif record.budgeting_method == 'gop_budget':
                        if self.budgeting_period == 'project':
                            for line_id in record.material_overhead_gop_ids:
                                bud_amt_left += line_id.budgeted_amt_left
                            if bud_amt_left < 1 :
                                raise ValidationError("There is no budget for overhead left")
                        else:
                            if self.is_multiple_budget == False:
                                for line_bud in budget.budget_overhead_gop_ids:
                                    bud_amt_left += line_bud.amt_left
                                if bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for overhead left")
                            else:
                                for budget_id in self.multiple_budget_ids:
                                    for bud in budget_id.budget_overhead_gop_ids:
                                        bud_amt_left += bud.amt_left
                                if bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for overhead left")
                    
                    elif record.budgeting_method == 'budget_type':
                        if self.budgeting_period == 'project':
                            if record.overhead_budget_left < 1 :
                                raise ValidationError("There is no budget for overhead left")
                        else:
                            if self.is_multiple_budget == False:
                                if budget.amount_left_overhead < 1 :
                                    raise ValidationError("There is no budget for overhead left")
                            else:
                                for budget_id in self.multiple_budget_ids:
                                    bud_amt_left += budget_id.amount_left_overhead
                                if bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for overhead left")

                    elif record.budgeting_method == 'total_budget':
                        if self.budgeting_period == 'project':
                            if record.contract_budget_left < 1 :
                                raise ValidationError("There is no budget for overhead left")
                            for line_id in record.material_overhead_ids:
                                bud_qty_left += line_id.budgeted_qty_left
                                bud_amt_left += line_id.budgeted_amt_left
                            if bud_qty_left < 1 or bud_amt_left < 1 :
                                raise ValidationError("There is no budget for overhead left")
                        else:
                            for line_bud in budget.budget_overhead_ids:
                                bud_qty_left += line_bud.qty_left
                                bud_amt_left += line_bud.amt_left
                            if bud_qty_left < 1 or bud_amt_left < 1:
                                raise ValidationError("There is no budget for overhead left")
            
            
                if self.budgeting_period == 'project':
                    material_request = self.env['material.request'].sudo().create(self.prepare_product_lines(record))
                else:
                    if self.is_multiple_budget == False:
                        material_request = self.env['material.request'].sudo().create(self.prepare_product_lines_budget(budget))
                    else:
                        raise ValidationError("Need Develop")
                    
                
                for res in material_request:
                    res.product_line = False
                    if self.budgeting_period == 'project':
                        if self.type_of_mr == 'material':
                            res.get_material_from_cost(res)
                        elif self.type_of_mr == 'labour':
                            res.get_labour_from_cost(res)
                        elif self.type_of_mr == 'overhead':
                            res.get_overhead_from_cost(res)
                    else:
                        if self.is_multiple_budget == False:
                            if self.type_of_mr == 'material':
                                res.get_material_from_budget(res)
                            elif self.type_of_mr == 'labour':
                                res.get_labour_from_budget(res)
                            elif self.type_of_mr == 'overhead':
                                res.get_overhead_from_budget(res)
                        else:
                            raise ValidationError("Need Develop")
            
                    for line in material_request.product_line:
                        line._onchange_product()

                return {
                        'type': 'ir.actions.act_window',
                        'name': 'Material Request',
                        'view_mode': 'form',
                        'res_model': 'material.request',
                        'res_id' : material_request.id,
                        'target': 'current'
                    }


# Workaround to remove 'labor' from type_of_mr selection by overriding it
class MaterialRequestWizInherit(models.TransientModel):
    _inherit = 'material.request.wiz'

    type_of_mr = fields.Selection([
        ('material', 'Material'),
        ('overhead', 'Overhead'),
        ('equipment', 'Equipment Lease'),
        ('subcon', 'Subcon Agreement')],
        string="Type of Request")
