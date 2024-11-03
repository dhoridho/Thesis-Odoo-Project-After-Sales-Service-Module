from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta, date

ESTIMATES_DICT = {
    'material_line_ids' : 'material_id',
    'labour_line_ids' : 'labour_id',
    'subcon_line_ids' : 'subcon_id',
    'overhead_line_ids' : 'overhead_id',
    'equipment_line_ids' : 'equipment_id',
    'internal_asset_line_ids' : 'asset_id'
}

COST_SHEET_DICT = {
    'material_line_ids' : 'material_ids',
    'labour_line_ids' : 'material_labour_ids',
    'subcon_line_ids' : 'material_subcon_ids',
    'overhead_line_ids' : 'material_overhead_ids',
    'equipment_line_ids' : 'material_equipment_ids',
    'internal_asset_line_ids' : 'internal_asset_ids'
}


class SaleOrderConstInherit(models.Model):
    _inherit = 'sale.order.const'

    is_set_projects_type = fields.Boolean(string='Set Projects Type', store=True)
    project_template_id = fields.Many2one('templates.project', 'Project Template')
    is_empty_cost_sheet = fields.Boolean(string="Start with empty cost sheet")
    project_budget_id = fields.Many2one('project.budget', 'Project Budget')
    project_budget_ids = fields.Many2many('project.budget', 'sale_order_project_budget_rel', 'sale_order_id', 'project_budget_id', string='Project Budgets')
    
    @api.onchange('project_id')
    def onchange_project_id_3(self):
        for res in self:
            job_cost_sheet = res.project_id.cost_sheet
            if res.project_id:
                stock_warehouse = self.env['stock.warehouse'].search([('name', '=', res.project_id.name)], limit=1)
                res.write({'warehouse_address': stock_warehouse})
                res_partner = self.env['res.partner'].search([('id', '=', res.project_id.partner_id.id)], limit=1)
                res.write({'partner_id': res_partner})

    @api.onchange('job_references')
    def _onchange_job_reference_23(self):
        if self.job_references:
            job = self.job_references[0]
            self.cost_sheet_ref = job.cost_sheet_ref
    
    def _onchange_cost_sheet(self):
        line = self.env['job.cost.sheet'].create({
                'cost_sheet_name': self.project_id.name + ' - ' + self.partner_id.name,
                'project_id': self.project_id.id,
                'branch_id': self.branch_id.id,
                'is_empty_cost_sheet': self.is_empty_cost_sheet,
                'sale_order_ref':  [(4, self.id)],
                'is_over_budget_ratio': self.is_over_budget_ratio,
                'ratio_value': self.ratio_value
            })
        
        line.sudo().onchange_approving_matrix_lines()
        
        if self.is_empty_cost_sheet:
            if line:
                line.sudo()._onchange_sale_order_ref_empty_cost_sheet()
                line.sudo()._get_customer()
        else:
            if line:
                line.sudo()._onchange_sale_order_ref()
                line.sudo()._get_customer()
    
    def _onchange_cost_sheet_var(self):
        self.cost_sheet_ref.write({
            'sale_order_ref':  [(4, self.id)]
        })
        sale_id = self
        self.cost_sheet_ref.sudo()._variation_order_send(sale_id)

    def create_contract_completion_from_template(self, project_template_id):
        created_completion = False
        for rec in self:
            if len(project_template_id.project_template_line) > 0:
                stages = []
                for template in rec.project_template_id.project_template_line:
                    stage = rec.env['project.task.type'].create({
                        'name': template.name,
                    })
                    stages.append((0, 0, {
                        'name': stage.id,
                        'stage_weightage': template.stage_weightage,
                    }))
                completion = rec.env['project.completion.const'].create({
                    'name': rec.id,
                    'completion_id': rec.project_id.id,
                    'stage_details_ids': stages,
                    'contract_percentage': 100,
                })
                created_completion = completion
            else:
                raise ValidationError(_("No Template Line found, please add template line in Project Template menu first."))
        return created_completion

    def create_job_order_from_template(self, project_template_id, completion):
        for rec in self:
            if len(project_template_id.project_template_line) > 0:
                created_job_order = []
                for template in project_template_id.project_template_line:
                    total_weightage = sum([x.task_weightage for x in template.job_order_template_id])
                    if total_weightage > 100:
                        raise ValidationError(
                            _("Total weightage of job order template can't be more than 100. Please re-set job order weightage in Job Order Template menu first."))
                    for task_template in template.job_order_template_id:
                        for stage in completion.stage_details_ids:
                            if stage.name.name == template.name:
                                job_order = rec.env['project.task'].create({
                                    'name': task_template.name,
                                    'project_id': rec.project_id.id,
                                    'cost_sheet': rec.project_id.cost_sheet.id,
                                    'sale_order': rec.id,
                                    'stage_new': stage.id,
                                    'stage_weightage': template.stage_weightage,
                                    'work_weightage': task_template.task_weightage,
                                    'planned_start_date': rec.start_date,
                                    'planned_end_date': rec.end_date,
                                })
                                created_job_order.append(job_order)
                if len(created_job_order) > 0 and len(project_template_id.predecessor_template_line) > 0:
                    for line in project_template_id.predecessor_template_line:
                        predecessor_task = False
                        successor_task = False
                        for job_order in created_job_order:
                            if job_order.name == line.predecessor_task_id.name:
                                predecessor_task = job_order
                            if job_order.name == line.successor_task_id.name:
                                successor_task = job_order
                        if predecessor_task and successor_task:
                            successor_task.write({
                                'predecessor_ids': [(0, 0, {
                                    'parent_task_id': predecessor_task.id,
                                    'type': line.type,
                                    'lag_qty': line.lag,
                                    'lag_type': line.lag_type,
                                    })]
                            })
                            # predecessor_task.write({
                            #     'successor_ids': [(0, 0, {
                            #         'parent_task_id': successor_task.id,
                            #         'type': line.type,
                            #         'lag_qty': line.lag,
                            #         'lag_type': line.lag_type,
                            #         })]
                            # })
            else:
                raise ValidationError(_("No Template Line found, please add template line in Project Template menu first."))

    def _button_confirm_contd(self):

        self.write(self._onchange_so())
        self.job_references.write(self._onchange_job_ref())
        
        if self.contract_category == 'main':   
            
            self.project_id.write({'project_scope_ids': False,
                                   'project_section_ids': False,
                                  })
            
            scope_list = []
            section_list = []
            for scope in self.project_scope_ids:
                scope_list.append((0, 0, {
                    'project_scope': scope.project_scope.id,
                    'description': scope.description,
                    })
                )

            for section in self.section_ids:
                section_list.append((0, 0, {
                    'project_scope': section.project_scope.id,
                    'section': section.section.id,
                    'description': section.description,
                    'quantity': section.quantity,
                    'uom_id': section.uom_id.id,
                    })
                )
            
            if self.opportunity_id:
                self.opportunity_id.stage_id = 4
            self.project_id.write(self._onchange_project_false())
            self.write(self._send_contract())
            self.project_id.write(self._send_project(scope_list, section_list))
            self.project_id.sudo()._onchange_sale_order_main()
            self.project_id.sudo()._inprogress_project_warehouse()
            self._method_budget_period()
            self._onchange_cost_sheet()
            
            for sale in self:
                except_main = self.env['sale.order.const'].search([('project_id', '=', sale.project_id.id), 
                                                                ('contract_category', '=', 'main'), 
                                                                ('id', '!=', sale.id)])
                if except_main:
                    for res in except_main:
                        res.write({'state' : 'block'})
                else:
                    pass

            if self.is_set_projects_type is True:
                completion = self.create_contract_completion_from_template(self.project_template_id)
                self.create_job_order_from_template(self.project_template_id, completion)

        elif self.contract_category == 'var':
            
            exist_scope = []
            scope_list = []
            for sco_pro in self.project_id.project_scope_ids:
                exist_scope.append(sco_pro.project_scope.id)

            for sco_con in self.project_scope_ids:
                if sco_con.project_scope.id not in exist_scope:
                    scope_list.append((0, 0, {
                        'project_scope': sco_con.project_scope.id,
                        'description': sco_con.description,
                        })
                    )
                else:
                    pass
            
            exist_section = []
            section_list = []
            for sec_pro in self.project_id.project_section_ids:
                same_pro = str(sec_pro.project_scope.id) + ' - ' + str(sec_pro.section.id)
                exist_section.append(same_pro)
            
            for sec_con in self.section_ids:
                same_con = str(sec_con.project_scope.id) + ' - ' + str(sec_con.section.id)
                if same_con not in exist_section:
                    section_list.append((0, 0, {
                        'project_scope': sec_con.project_scope.id,
                        'section': sec_con.section.id,
                        'description': sec_con.description,
                        'quantity': sec_con.quantity,
                        'uom_id': sec_con.uom_id.id,
                        })
                    )
                else:
                    pass
            
            contract_list = self._send_contract_var()
            self._onchange_cost_sheet_var()
            self.project_id.write({
                    'project_scope_ids': scope_list,
                    'project_section_ids': section_list,
                })

            if self.vo_payment_type == 'split':   
                self._split_payment_type(contract_list)

                # if self.is_set_projects_type == True:
                #     return {
                #         'type': 'ir.actions.act_window',
                #         'name': 'Project Template Selection',
                #         'res_model': 'project.template.confirmation.wizard',
                #         'view_mode': 'form',
                #         'target': 'new',
                #         'context': {'default_project_id': self.project_id.id,
                #                     'default_sale_order_id': self.id,}
                #     }

            if self.vo_payment_type == 'join': 
                self._join_payment_type(contract_list)

                                
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        for record in self:
            record.write({'sale_state': 'progress'})
            keep_name_so = IrConfigParam.get_param('keep_name_so', False)
            if not keep_name_so:
                if record.origin:
                    record.origin += "," + record.name
                else:
                    record.origin = record.name
                record.name = self.env['ir.sequence'].next_by_code('sale.order.quotation.order.const')
        return

    def action_cost_sheet(self):
        job_sheet = self.env['job.cost.sheet'].search([('sale_order_ref', '=', self.id)], limit=1)
        action = job_sheet.get_formview_action()
        return action

    cost_sheet_ref = fields.Many2one('job.cost.sheet', 'Cost Sheet',
                     domain="[('state', '=', 'approved'), ('company_id', '=', company_id)]")

    def report_data2array(self, data_dict):
        def traverse(data_dict, depth = 0):
            data_arr = []
            blank_data = {}
            for k, v in data_dict.items():
                blank_data = { x : '' for x, _ in v.items()}
                v['style'] = depth
                data_arr += [v]
                data_arr += traverse(v['children'],  depth + 1)
                if v.get('_subtotal', False):
                    v['_subtotal']['style'] = 3
                    data_arr += [v['_subtotal']]
                    
                if depth == 0 and len(data_arr) > 0:
                    blank_data['style'] = 1
                    data_arr += [blank_data]

            return data_arr
                
        return traverse(data_dict)

    def get_report_data(self, print_level_option):
        scope_sect_prod_dict = {}
        sale_order_id = self
        cost_sheet_id = self.cost_sheet_ref
        contract_category = sale_order_id.contract_category

        char_inc = 'A'
        for i, item in enumerate(sale_order_id.project_scope_ids):
            scope_sect_prod_dict[item.project_scope.name] = {
                'field'             : 'scope',
                'no'                : chr(ord(char_inc) + i),
                'name'              : item.project_scope.name,
                'qty_before'        : '',
                'qty'               : '',
                'contractor_before' : '',
                'contractor'        : '',
                'time_before'       : '',
                'time'              : '',
                'uom_before'        : '',
                'uom'               : '',
                'unit_price_before' : '',
                'unit_price'        : '',
                'total_before'      : '',
                'total'             : '',
                'children'          : {},
                'counter'           : 1,
                '_subtotal' : {
                    'field'             : 'scope',
                    'no'                : '',
                    'name'              : 'Subtotal ' + sale_order_id.getRoman(i + 1),
                    'qty_before'        : '',
                    'qty'               : '',
                    'contractor_before' : '',
                    'contractor'        : '',
                    'time_before'       : '',
                    'time'              : '',
                    'uom_before'        : '',
                    'uom'               : '',
                    'unit_price_before' : '',
                    'unit_price'        : '',
                    'total_before'      : item.amount_line,
                    'total'             : item.amount_line,
                    'children'          : {},
                    'counter'           : 1,
                },
            }

        for i, item in enumerate(sale_order_id.section_ids):
            if scope_sect_prod_dict.get(item.project_scope.name, False):
                scope_sect_prod_dict[item.project_scope.name]['children'][item.section.name] = {
                    'field'             : 'section',
                    'no'                : scope_sect_prod_dict[item.project_scope.name]['counter'],
                    'name'              : item.section.name,
                    'qty_before'        : item.quantity,
                    'qty'               : item.quantity,
                    'contractor_before' : '',
                    'contractor'        : '',
                    'time_before'       : '',
                    'time'              : '',
                    'uom_before'        : '',
                    'uom'               : item.uom_id.name,
                    'unit_price_before' : '',
                    'unit_price'        : '',
                    'total_before'      : item.amount_line,
                    'total'             : item.amount_line,
                    'children'          : {},
                    'counter'           : 'a',
                }
                scope_sect_prod_dict[item.project_scope.name]['counter'] += 1

        if print_level_option == '3_level':
            for field, key in ESTIMATES_DICT.items():
                item_dict = {}
                    
                for x in sale_order_id[field]:
                    item_key = str(x.project_scope.name) + '_' + str(x.section_name.name) + '_' + str(x[key].name)
                    if item_dict.get(item_key, False):
                        item_dict[item_key]['qty'] = item_dict[item_key]['qty_before'] + x.quantity
                        item_dict[item_key]['uom'] = x.uom_id.name
                        item_dict[item_key]['unit_price'] = x.amount_line / x.quantity if x.quantity else x.unit_price,
                        item_dict[item_key]['total'] = x.subtotal
                    else :
                        temp = {
                            'field'             : field,
                            'name'              : x[key].name,
                            'qty_before'        : x.budget_quantity if field != 'labour_line_ids' else 0,
                            'qty'               : x[{'main' : 'quantity', 'var' : 'quantity_after'}[contract_category]] if field != 'labour_line_ids' else 0,
                            'contractor_before' : x.budget_contractors if field == 'labour_line_ids' else 0,
                            'contractor'        : x[{'main' : 'contractors', 'var' : 'contractors_after'}[contract_category]] if field == 'labour_line_ids' else 0,
                            'time_before'       : x.budget_time if field == 'labour_line_ids' else 0,
                            'time'              : x[{'main' : 'time', 'var' : 'time_after'}[contract_category]] if field == 'labour_line_ids' else 0,
                            'uom_before'        : '',
                            'uom'               : x.uom_id.name,
                            'unit_price_before' : x.budget_unit_price,
                            'unit_price'        : x.unit_price ,
                            'total_before'      : 0,
                            'total'             : x.amount_line,
                            'children'          : {},
                        }

                        markup = sale_order_id.adjustment_sub / sale_order_id.amount_untaxed
                        if field == 'labour_line_ids':
                            if temp['contractor_before'] != 0 and temp['time_before'] != 0 :
                                temp['unit_price_before'] = temp['unit_price_before'] + ( temp['unit_price_before'] * markup)
                            else:
                                temp['unit_price_before'] = 0

                            if temp['contractor'] != 0 and temp['time'] != 0 :
                                temp['unit_price'] = temp['unit_price'] + ( temp['unit_price'] * markup)
                            else:
                                temp['unit_price'] = 0

                        else:
                            if temp['qty_before'] != 0:
                                temp['unit_price_before'] = temp['unit_price_before'] + ( temp['unit_price_before'] * markup)
                            else:
                                temp['unit_price_before'] = 0

                            if temp['qty'] != 0:
                                temp['unit_price'] = temp['unit_price'] + ( temp['unit_price'] * markup)
                            else:
                                temp['unit_price'] = 0

                        item_dict[item_key] = temp

                for key, item in item_dict.items():
                    key_arr = key.split('_')
                    scope = key_arr[0]
                    section = key_arr[1]
                    product = key_arr[2]
                    
                    if contract_category == 'var':
                        if item['field'] != 'labour_line_ids':
                            if item['qty_before'] == 0 and item['qty'] == 0: continue
                        else:
                            if item['contractor_before'] == 0 and item['contractor'] == 0 and item['time_before'] == 0 and item['time'] == 0: continue

                    try:
                        char_inc = scope_sect_prod_dict[scope]['children'][section]['counter'] 
                        scope_sect_prod_dict[scope]['children'][section]['children'][product] = {
                            'field'             : item['field'],
                            'no'                : char_inc,
                            'name'              : product,
                            'qty_before'        : item['qty_before'],
                            'qty'               : item['qty'],
                            'contractor_before' : item['contractor_before'],
                            'contractor'        : item['contractor'],
                            'time_before'       : item['time_before'],
                            'time'              : item['time'],
                            'uom_before'        : item['uom_before'],
                            'uom'               : item['uom'],
                            'unit_price_before' : item['unit_price_before'],
                            'unit_price'        : item['unit_price'],
                            'total_before'      : item['total_before'],
                            'total'             : item['total'],
                            'children'          : {},
                        }
                        scope_sect_prod_dict[scope]['children'][section]['counter'] = chr(ord(char_inc) + 1)

                    except Exception as e:
                        continue

        return scope_sect_prod_dict


class JobEstimateToVariationInherit(models.TransientModel):
    _inherit = 'job.estimate.variation.const'

    def _prepare_value(self, main_contract):
        res = super(JobEstimateToVariationInherit, self)._prepare_value(main_contract)
        job_id = self.env['job.estimate'].browse([self._context.get('active_id')])
        job_cost_sheet = self.env['job.cost.sheet'].search([('project_id', '=', job_id.project_id.id), ('state', '!=', 'cancelled')], limit=1)
        res['cost_sheet_ref'] = job_cost_sheet or False

        return res


class SaleOrderMaterialLine(models.Model):
    _inherit = 'sale.order.material.line'

    budget_unit_price = fields.Float('Budget Unit Price')
    quantity_after = fields.Float('Quantity After')
    cs_material_id = fields.Many2one('material.material', string='Cost Sheet Material')
    bd_material_id = fields.Many2one('budget.material', string='Budget Material')
    material_boq_ids = fields.Many2many('material.estimate', 'material_sale_order_boq_rel', string='Material BOQ')


class SaleOrderlabourLine(models.Model):
    _inherit = 'sale.order.labour.line'
    
    budget_unit_price = fields.Float('Budget Unit Price')
    contractors_after = fields.Float('Contractors After')
    time_after = fields.Float('Time After')
    cs_labour_id = fields.Many2one('material.labour', string='Cost Sheet Labour')
    bd_labour_id = fields.Many2one('budget.labour', string='Budget Labour')
    labour_boq_ids = fields.Many2many('labour.estimate', 'labour_sale_order_boq_rel', string='Labour BOQ')


class SaleOrderoverheadLine(models.Model):
    _inherit = 'sale.order.overhead.line'

    budget_unit_price = fields.Float('Budget Unit Price')
    quantity_after = fields.Float('Quantity After')
    cs_overhead_id = fields.Many2one('material.overhead', string='Cost Sheet Overhead')
    bd_overhead_id = fields.Many2one('budget.overhead', string='Budget Overhead')
    overhead_boq_ids = fields.Many2many('overhead.estimate', 'overhead_sale_order_boq_rel', string='Overhead BOQ')


class SaleOrdersubconLine(models.Model):
    _inherit = 'sale.order.subcon.line'

    budget_unit_price = fields.Float('Budget Unit Price')
    quantity_after = fields.Float('Quantity After')
    cs_subcon_id = fields.Many2one('material.subcon', string='Cost Sheet Subcon')
    bd_subcon_id = fields.Many2one('budget.subcon', string='Budget Subcon')
    subcon_boq_ids = fields.Many2many('subcon.estimate', 'subcon_sale_order_boq_rel', string='Subcon BOQ')


class SaleOrderEquipmentLine(models.Model):
    _inherit = 'sale.order.equipment.line'

    budget_unit_price = fields.Float('Budget Unit Price')
    quantity_after = fields.Float('Quantity After')
    cs_equipment_id = fields.Many2one('material.equipment', string='Cost Sheet Equipment')
    bd_equipment_id = fields.Many2one('budget.equipment', string='Budget Equipment')
    equipment_boq_ids = fields.Many2many('equipment.estimate', 'equipment_sale_order_boq_rel', string='Equipment BOQ')


class SaleOrderInternalAsset(models.Model):
    _inherit = 'sale.internal.asset.line'

    budget_unit_price = fields.Float('Budget Unit Price')
    quantity_after = fields.Float('Quantity After')
    cs_internal_asset_id = fields.Many2one('internal.asset', string='Cost Sheet Internal Assets')
    bd_internal_asset_id = fields.Many2one('budget.internal.asset', string='Budget Internal Assets')
    internal_asset_boq_ids = fields.Many2many('internal.assets', 'internal_asset_sale_order_boq_rel', string='Internal Assets BOQ')
