from ast import Store
from dataclasses import field
from odoo import models, fields, api, _
from datetime import datetime, timedelta, date
from odoo.exceptions import ValidationError, UserError
from datetime import datetime


class PurchaseTender(models.Model):
    _inherit = 'purchase.agreement'

    project = fields.Many2one('project.project', 'Project',domain=lambda self:[('company_id','=',self.env.company.id),('primary_states','=','progress')])
    budgeting_method = fields.Selection(related='project.budgeting_method', string='Budgeting Method')
    budgeting_period = fields.Selection(related='project.budgeting_period', string='Budgeting Period')
    cost_sheet = fields.Many2one('job.cost.sheet', 'Cost Sheet')
    project_budget = fields.Many2one('project.budget', string='Periodical Budget', domain="[('project_id','=',project), ('state','=','in_progress')]")
    multiple_budget_ids = fields.Many2many('project.budget', string='Multiple Budget', domain="[('project_id','=',project), ('state','=','in_progress')]")
    is_multiple_budget = fields.Boolean('Multiple Budget', default=False)
    material_request = fields.Many2one('material.request', 'Material Request')
    sub_contracting = fields.Selection([('main_contract', 'Main Contract'), ('addendum', 'Addendum')],
                                       string="Contract Category", default='main_contract')
    po_tender_count = fields.Integer("Purchase Tender Count",compute="_compute_purchase_tender_count")
    total_split_tender = fields.Integer("Split Purchase Tender Count",compute="_comute_split_tender_count")
    is_subcontracting = fields.Boolean('Is Subcontracting', default=False, Store="1")
    is_material_orders = fields.Boolean('Is Material Orders', default=False, Store="1")
    is_orders = fields.Boolean('Is Orders', default=False, Store="1")
    is_asset_cons_order = fields.Boolean('Is Asset Cons Order', default=False, Store="1")
    material_order = fields.Boolean('Material Order')

    variable_line_ids = fields.One2many('pt.variable.line', 'variable_id', string='Variable Line')
    material_line_ids = fields.One2many('material.line', 'material_id', string='Material Line')
    service_line_ids = fields.One2many('service.line', 'service_id', string='Service Line')
    equipment_line_ids = fields.One2many('pa.equipment.line', 'equipment_id', string='Equipment Line')
    labour_line_ids = fields.One2many('labour.line', 'labour_id', string='Labour Line')
    overhead_line_ids = fields.One2many('overhead.line', 'overhead_id', string='Overhead Line')
    is_multiple_budget_procurement = fields.Boolean(string="Is Multiple Budget", compute='_is_multiple_budget_procurement')

    @api.depends('sh_purchase_agreement_line_ids.sh_qty', 'sh_purchase_agreement_line_ids.sh_price_unit')
    def _amount_total(self):
        res = super(PurchaseTender, self)._amount_total()
        for rec in self:
            total = 0
            if rec.project and (rec.project_budget or rec.cost_sheet):
                for subcon in rec.variable_line_ids:
                    total += (subcon.reference_price * subcon.quantity)
                rec.amount_total = total
        return res
    
    def _is_multiple_budget_procurement(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_multiple_budget_procurement = IrConfigParam.get_param('is_multiple_budget_procurement')
        for record in self:
            record.is_multiple_budget_procurement = is_multiple_budget_procurement

    def _get_project_budget(self):
        for rec in self:
            Job_cost_sheet = rec.cost_sheet
            if rec.project.budgeting_period == 'monthly':
                data = rec.env['budget.period.line'].search([('start_date', '<', rec.sh_delivery_date),
                                                            ('end_date', '>', rec.sh_delivery_date),
                                                            ('line_project_ids', '=', Job_cost_sheet.project_id.id),], limit=1)
                budget = rec.env['project.budget'].search([('project_id', '=', Job_cost_sheet.project_id.id),
                                                            ('cost_sheet', '=', Job_cost_sheet.id),
                                                            ('month', '=', data.id)], limit=1)
                return budget
            elif rec.project.budgeting_period == 'custom':
                budget = rec.env['project.budget'].search([('project_id', '=', Job_cost_sheet.project_id.id),
                                                            ('cost_sheet', '=', Job_cost_sheet.id),
                                                            ('bd_start_date', '<=', rec.sh_delivery_date),
                                                            ('bd_end_date', '>=', rec.sh_delivery_date)], limit=1)
                return budget
            else:
                pass

    def _send_line_PR(self):
        for res in self:
            for line in res.variable_line_ids:
                line.purchase_request_id.pt_variable_id = line.id

    def action_new_quotation2(self):
        if self.cost_sheet.state == 'freeze':
            raise ValidationError("The budget for this project is being freeze")
        else:
            context = dict(self._context or {})
            context.update({'default_agreement_id': self.id, 'default_partner_ids': self.partner_ids.ids})
            if self.project:
                context.update({'default_project':self.project.id})
            if self.project_budget:
                context.update({'default_project_budget': self.project_budget.id})
            if self.cost_sheet:
                context.update({'default_cost_sheet': self.cost_sheet.id})
            if self.is_material_orders == True:
                context.update({
                    'goods_order': 1, 
                    'default_is_goods_orders': True,
                    'default_is_material_orders': True,
                    'material_order': True,
                    })
            return {
                'name': ('New Quotation'),
                'type': 'ir.actions.act_window',
                'res_model': 'wizard.quotation.agreement',
                'view_id': self.env.ref('equip3_purchase_other_operation.wizard_quotation_agreement_form').id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                'context': context,
            }

    def tender_lines(self, rec, current_date, rec_line):
        return{
            'cs_material_id': rec_line.cs_material_id.id,
            'cs_labour_id': rec_line.cs_labour_id.id,
            'cs_overhead_id': rec_line.cs_overhead_id.id,
            'cs_equipment_id': rec_line.cs_equipment_id.id,
            'cs_subcon_id': rec_line.cs_subcon_id.id,
            'bd_material_id': rec_line.bd_material_id.id,
            'bd_labour_id': rec_line.bd_labour_id.id,
            'bd_overhead_id': rec_line.bd_overhead_id.id,
            'bd_equipment_id': rec_line.bd_equipment_id.id,
            'bd_subcon_id': rec_line.bd_subcon_id.id,
            'type': rec_line.type,
            'project_scope': rec_line.project_scope.id,
            'section': rec_line.section.id,
            'group_of_product': rec_line.group_of_product.id,
            'product_id': rec_line.sh_product_id.id,
            'name': rec_line.sh_product_id.name,
            'date_planned': current_date,
            'product_qty': rec_line.sh_qty,
            'budget_quantity': rec_line.budget_quantity,
            'analytic_tag_ids': rec_line.analytic_tag_ids.ids,
            'status': 'draft',
            'agreement_line_id': rec_line.id,
            'sh_product_description': rec_line.sh_product_description,
            'agreement_id': rec.id,
            'product_uom': rec_line.sh_product_uom_id.id,
            'destination_warehouse_id': rec_line.dest_warehouse_id.id,
            'picking_type_id':rec_line.picking_type_id.id,
        }

    def vendor_prepare(self, rec, line_ids, picking, vendor):
        return{
            'partner_id': vendor.id,
            'agreement_id': rec.id,
            'project': rec.project.id,
            'cost_sheet': rec.cost_sheet.id,
            'project_budget': rec.project_budget.id,
            'is_orders': rec.is_orders,
            'is_goods_orders': rec.is_goods_orders,
            'origin': rec.name, 
            'analytic_account_group_ids': rec.account_tag_ids.ids,
            'branch_id': rec.branch_id.id,
            'user_id': rec.sh_purchase_user_id.id,
            'picking_type_id': picking or False,
            'order_line': line_ids
        }

    def create_new_rfq(self, vendors):
        if self.cost_sheet.state == 'freeze':
            raise ValidationError("The budget for this project is being freeze")
        else:
            context = dict(self._context or {})
            for rec in self:
                po_obj = self.env['purchase.order']
                line_ids = []
                current_date = None
                # is_goods_orders = False
                if rec.sh_delivery_date:
                    current_date = rec.sh_delivery_date
                else:
                    current_date = fields.Datetime.now()
                # if rec.is_goods_orders:
                #     is_goods_orders = True
                for rec_line in rec.sh_purchase_agreement_line_ids:
                    picking = rec_line.picking_type_id.id
                    budget_price = 0
                    line_vals = rec.tender_lines(rec, current_date, rec_line)
                    if rec_line.type == 'material':
                        if rec_line.bd_material_id:
                            budget_price = rec_line.bd_material_id.amount
                            budget_amount = budget_price * rec_line.sh_qty
                        else:
                            budget_price = rec_line.cs_material_id.price_unit
                            budget_amount = budget_price * rec_line.sh_qty
                    elif rec_line.type == 'labour':
                        if rec_line.bd_labour_id:
                            budget_price = rec_line.bd_labour_id.amount
                            budget_amount = budget_price * rec_line.sh_qty
                        else:
                            budget_price = rec_line.cs_labour_id.price_unit
                            budget_amount = budget_price * rec_line.sh_qty
                    elif rec_line.type == 'overhead':
                        if rec_line.bd_overhead_id:
                            budget_price = rec_line.bd_overhead_id.amount
                            budget_amount = budget_price * rec_line.sh_qty
                        else:
                            budget_price = rec_line.cs_overhead_id.price_unit
                            budget_amount = budget_price * rec_line.sh_qty
                    elif rec_line.type == 'equipment':
                        if rec_line.bd_equipment_id:
                            budget_price = rec_line.bd_equipment_id.amount
                            budget_amount = budget_price * rec_line.sh_qty
                        else:
                            budget_price = rec_line.cs_equipment_id.price_unit
                            budget_amount = budget_price * rec_line.sh_qty
                    elif rec.is_material_orders:
                        budget_price = rec_line.var_material_id.unit_price
                        budget_amount = budget_price * rec_line.sh_qty
                    line_vals.update({'price_unit': budget_price})
                    line_vals.update({'budget_unit_price': budget_price})
                    line_vals.update({'remining_budget_amount': budget_amount})
                    if context.get('services_good'):
                        line_vals.update({'is_services_orders': True})
                    elif context.get('goods_order'):
                        line_vals.update({'is_goods_orders': True})
                    elif context.get('assets_orders'):
                        line_vals.update({'is_assets_orders': True})
                    elif context.get('rentals_orders'):
                        line_vals.update({'is_rental_orders': True})
                    line_ids.append((0, 0, line_vals))
                i = 0
                for vendor in vendors:
                    vals = rec.vendor_prepare(rec, line_ids, picking, vendor)
                    if context.get('services_good'):
                        vals.update({'is_services_orders': True})
                    elif context.get('goods_order'):
                        vals.update({'is_goods_orders': True})
                    elif context.get('assets_orders'):
                        line_vals.update({'is_assets_orders': True})
                    elif context.get('rentals_orders'):
                        line_vals.update({'is_rental_orders': True})
                    if rec.is_assets_orders:
                        vals['date_order'] = datetime.now()
                    elif rec.is_services_orders:
                        rfq_exp_date_services = self.env['ir.config_parameter'].get_param('equip3_purchase_operation.rfq_exp_date_services')
                        vals['date_order'] = datetime.now() + timedelta(days=int(rfq_exp_date_services))
                    else:
                        rfq_exp_date_goods = self.env['ir.config_parameter'].get_param('equip3_purchase_operation.rfq_exp_date_goods')
                        vals['date_order'] = datetime.now() + timedelta(days=int(rfq_exp_date_goods))
                    purchase_id = po_obj.with_context(context).create(vals)
                    purchase_id._onchange_partner_invoice_id()
                    i += 1
                if i and rec.state2 == 'pending':
                    rec.state = 'bid_submission'

    @api.onchange('project')
    def _onchange_cost_sheet(self, is_from_request=False):
        if not is_from_request:
            self.variable_line_ids = [(5, 0, 0)]
        self.project_budget = False
        data = False
        for rec in self:
            branch = rec.project.branch_id
            if rec.cost_sheet.state == 'freeze':
                raise ValidationError("The budget for this project is being freeze")
            else:
                for proj in rec.project:
                    if not is_from_request:
                        self.account_tag_ids = False
                        cost = rec.env['job.cost.sheet'].search([('project_id', '=', proj.id), ('state', 'in', ['in_progress', 'done'])])
                        rec.write({'cost_sheet' : cost})
                        rec.account_tag_ids = rec.cost_sheet.account_tag_ids.ids
                        rec.project_budget = rec._get_project_budget()
                    
                        if rec.project_budget:
                            rec.variable_line_ids = rec._get_budget_variable_line_ids(rec.project_budget)
                        elif not rec.project_budget and rec.cost_sheet:
                            rec.variable_line_ids = rec._get_cost_variable_line_ids(rec.cost_sheet)
            rec.update({'branch_id': branch.id})

    def _get_cost_variable_line_ids(self, line_id):
        vals = []
        for rec in self:
            for line in line_id.material_subcon_ids:
                vals.append((0, 0, {
                    'cs_subcon_id': line.id,
                    'purchase_request_id': line.id,
                    'project_scope': line.project_scope.id,
                    'section': line.section_name.id,
                    'variable_ref': line.variable_ref.id,
                    'variable': line.variable.id,
                    'quantity': line.product_qty,
                    'budget_qty': line.product_qty,
                    'uom': line.uom_id.id,
                    'budget_amount': line.price_unit,
                    'reference_price': line.price_unit
                }))
        return vals

    def _get_budget_variable_line_ids(self, line_id):
        vals = []
        for rec in self:
            for line in line_id.budget_subcon_ids:
                vals.append((0, 0, {
                    'cs_subcon_id': line.cs_subcon_id.id,
                    'bd_subcon_id': line.id,
                    'purchase_request_id': line.id,
                    'project_scope': line.project_scope.id,
                    'section': line.section_name.id,
                    'variable_ref': line.variable_ref.id,
                    'variable': line.subcon_id.id,
                    'quantity': line.quantity,
                    'budget_qty': line.quantity,
                    'uom': line.uom_id.id,
                    'budget_amount': line.cs_subcon_id.price_unit,
                    'reference_price': line.cs_subcon_id.price_unit

                }))
        return vals

    @api.onchange('variable_line_ids')
    def _get_material_line(self):
        material = [(5, 0, 0)]
        services = [(5, 0, 0)]
        equipment = [(5, 0, 0)]
        labour = [(5, 0, 0)]
        overhead = [(5, 0, 0)]
        for rec in self.variable_line_ids:
            for mat in rec.variable.material_variable_ids:
                res = (0, 0, {
                    'project_scope': rec.project_scope.id,
                    'section': rec.section.id,
                    'subcon': rec.variable.id,
                    'group_of_product': mat.group_of_product.id,
                    'product': mat.product_id.id,
                    'description': mat.description,
                    'quantity': rec.quantity * mat.quantity,
                    'analytic_tag_ids': [(6, 0, [v.id for v in rec.analytic_tag_ids])],
                    'uom': mat.uom_id.id,
                    'reference_price': mat.unit_price,
                })
                material.append(res)

            for serv in rec.variable.service_variable_ids:
                res = (0, 0, {
                    'project_scope': rec.project_scope.id,
                    'section': rec.section.id,
                    'subcon': rec.variable.id,
                    'group_of_product': serv.group_of_product.id,
                    'product': serv.product_id.id,
                    'description': serv.description,
                    'quantity': rec.quantity * serv.quantity,
                    'analytic_tag_ids': [(6, 0, [v.id for v in rec.analytic_tag_ids])],
                    'uom': serv.uom_id.id,
                    'reference_price': serv.unit_price,
                })
                services.append(res)

            for equi in rec.variable.equipment_variable_ids:
                res = (0, 0, {
                    'project_scope': rec.project_scope.id,
                    'section': rec.section.id,
                    'subcon': rec.variable.id,
                    'group_of_product': equi.group_of_product.id,
                    'product': equi.product_id.id,
                    'description': equi.description,
                    'quantity': rec.quantity * equi.quantity,
                    'analytic_tag_ids': [(6, 0, [v.id for v in rec.analytic_tag_ids])],
                    'uom': equi.uom_id.id,
                    'reference_price': equi.unit_price,
                })
                equipment.append(res)

            for lab in rec.variable.labour_variable_ids:
                res = (0, 0, {
                    'project_scope': rec.project_scope.id,
                    'section': rec.section.id,
                    'subcon': rec.variable.id,
                    'group_of_product': lab.group_of_product.id,
                    'product': lab.product_id.id,
                    'description': lab.description,
                    'quantity': rec.quantity * lab.quantity,
                    'analytic_tag_ids': [(6, 0, [v.id for v in rec.analytic_tag_ids])],
                    'uom': lab.uom_id.id,
                    'reference_price': lab.unit_price,
                })
                labour.append(res)

            for over in rec.variable.overhead_variable_ids:
                res = (0, 0, {
                    'project_scope': rec.project_scope.id,
                    'section': rec.section.id,
                    'subcon': rec.variable.id,
                    'group_of_product': over.group_of_product.id,
                    'product': over.product_id.id,
                    'description': over.description,
                    'quantity': rec.quantity * over.quantity,
                    'analytic_tag_ids': [(6, 0, [v.id for v in rec.analytic_tag_ids])],
                    'uom': over.uom_id.id,
                    'reference_price': over.unit_price,
                })
                overhead.append(res)

        self.material_line_ids = material
        self.service_line_ids = services
        self.equipment_line_ids = equipment
        self.labour_line_ids = labour
        self.overhead_line_ids = overhead

    def check_main_contract(self, main_contract, vendor):
        for rec in self:
            for main in main_contract:
                main_contract_subcon_line = []
                for contract in main:
                    main_contract_subcon_line.append({
                        'project_scope': contract.variable_line_ids.project_scope.id,
                        'section': contract.variable_line_ids.section.id,
                        'variable': contract.variable_line_ids.variable.id,
                        'cs_subcon_id': contract.variable_line_ids.cs_subcon_id.id,
                        'bd_subcon_id': contract.variable_line_ids.bd_subcon_id.id,
                    })
                for line in rec.variable_line_ids:
                    for main_subcon in main_contract_subcon_line:
                        if line.project_scope.id == main_subcon['project_scope'] and line.section.id == main_subcon['section'] and line.variable.id == main_subcon['variable'] and line.cs_subcon_id.id == main_subcon['cs_subcon_id'] and line.bd_subcon_id.id == main_subcon['bd_subcon_id']:
                            if rec.project.id == main.project.id and vendor.id == main.partner_id.id and rec.cost_sheet.id == main.cost_sheet.id and rec.project_budget.id == main.project_budget.id:
                                return False
                            else:
                                return True
        return True

    def action_new_quotation3(self):
        for rec in self:
            if rec.cost_sheet.state == 'freeze':
                raise ValidationError("The budget for this project is being freeze")
            else:
                po_obj = self.env['purchase.order']
                line_ids = []
                material = []
                service = []
                equipment = []
                labour = []
                overhead = []
                line_vals = []
                for rec_line in rec.variable_line_ids:
                    qty = 0.00
                    if self.project_budget:
                        # for ref in rec_line.bd_subcon_id:
                            line_vals = {
                                'purchase_agreement': rec.id,
                                'project_scope': rec_line.project_scope.id,
                                'section': rec_line.section.id,
                                # 'variable_ref': rec_line.variable_ref.id,
                                'variable': rec_line.variable.id,
                                'quantity': rec_line.quantity,
                                'budget_quantity': rec_line.quantity,
                                'uom': rec_line.uom.id,
                                'sub_total': rec_line.reference_price,
                                'total': rec_line.reference_price * rec_line.quantity,
                                'budget_amount': rec_line.bd_subcon_id.amount,
                                'budget_amount_total': rec_line.bd_subcon_id.amt_left,
                                'is_subtotal_readonly': True,
                            }
                    else:
                        # for ref in rec_line.cs_subcon_id:
                            line_vals = {
                                'purchase_agreement': rec.id,
                                'project_scope': rec_line.project_scope.id,
                                'section': rec_line.section.id,
                                # 'variable_ref': rec_line.variable_ref.id,
                                'variable': rec_line.variable.id,
                                'quantity': rec_line.quantity,
                                'budget_quantity': rec_line.quantity,
                                'uom': rec_line.uom.id,
                                'sub_total': rec_line.reference_price,
                                'total': rec_line.reference_price * rec_line.quantity,
                                'budget_amount': rec_line.cs_subcon_id.price_unit,
                                'budget_amount_total': rec_line.cs_subcon_id.budgeted_amt_left,
                                'is_subtotal_readonly': True,
                            }
                    line_ids.append((0, 0, line_vals))
                    for mat in rec_line.variable.material_variable_ids:
                            qty = rec_line.quantity * mat.quantity
                            material.append((0, 0, {
                                'project_scope': rec_line.project_scope.id,
                                'section': rec_line.section.id,
                                'variable': rec_line.variable.id,
                                'product': mat.product_id.id,
                                'description': mat.description,
                                'purchase_tender': rec.id,
                                'destination_warehouse': rec.destination_warehouse_id.id,
                                'quantity': qty,
                                'budget_quantity': qty,
                                'uom': mat.uom_id.id,
                                'unit_price': mat.unit_price,
                                'budget_unit_price': mat.unit_price,
                            }))
                    for ser in rec_line.variable.service_variable_ids:
                        qty = rec_line.quantity * ser.quantity
                        service.append((0, 0, {
                            'project_scope': rec_line.project_scope.id,
                            'section': rec_line.section.id,
                            'variable': rec_line.variable.id,
                            'product': ser.product_id.id,
                            'description': ser.description,
                            'purchase_tender': rec.id,
                            'destination_warehouse': rec.destination_warehouse_id.id,
                            'quantity': qty,
                            'budget_quantity': qty,
                            'uom': ser.uom_id.id,
                            'unit_price': ser.unit_price,
                            'budget_unit_price': ser.unit_price,
                        }))
                    for equ in rec_line.variable.equipment_variable_ids:
                        qty = rec_line.quantity * equ.quantity
                        equipment.append((0, 0, {
                            'project_scope': rec_line.project_scope.id,
                            'section': rec_line.section.id,
                            'variable': rec_line.variable.id,
                            'product': equ.product_id.id,
                            'description': equ.description,
                            'purchase_tender': rec.id,
                            'destination_warehouse': rec.destination_warehouse_id.id,
                            'quantity': qty,
                            'budget_quantity': qty,
                            'uom': equ.uom_id.id,
                            'unit_price': equ.unit_price,
                            'budget_unit_price': equ.unit_price,
                        }))
                    for lab in rec_line.variable.labour_variable_ids:
                        qty = rec_line.quantity * lab.quantity
                        labour.append((0, 0, {
                            'project_scope': rec_line.project_scope.id,
                            'section': rec_line.section.id,
                            'variable': rec_line.variable.id,
                            'product': lab.product_id.id,
                            'description': lab.description,
                            'purchase_tender': rec.id,
                            'destination_warehouse': rec.destination_warehouse_id.id,
                            'quantity': qty,
                            'budget_quantity': qty,
                            'uom': lab.uom_id.id,
                            'unit_price': lab.unit_price,
                            'budget_unit_price': lab.unit_price,
                        }))
                    for ove in rec_line.variable.overhead_variable_ids:
                        qty = rec_line.quantity * ove.quantity
                        overhead.append((0, 0, {
                            'project_scope': rec_line.project_scope.id,
                            'section': rec_line.section.id,
                            'variable': rec_line.variable.id,
                            'product': ove.product_id.id,
                            'description': ove.description,
                            'purchase_tender': rec.id,
                            'destination_warehouse': rec.destination_warehouse_id.id,
                            'quantity': qty,
                            'budget_quantity': qty,
                            'uom': ove.uom_id.id,
                            'unit_price': ove.unit_price,
                            'budget_unit_price': ove.unit_price,
                        }))
                i = 0
                contract = False
                main = False
                payment = False
                for vendor in self.partner_ids:
                    # TO DO : Fix Issue addendum categorization
                    main_contract = self.env['purchase.order'].search([('is_subcontracting','=',True),('project', '=', rec.project.id), ('partner_id', '=', vendor.id),('sub_contracting', '=', 'main_contract'), ('state', 'in',('purchase','done'))])
                    if rec.is_subcontracting is True:
                        is_main_contract = rec.check_main_contract(main_contract, vendor)
                        if is_main_contract is False:
                            contract = 'addendum'
                            main = main_contract.id
                            payment = 'join_payment'
                        else:
                            contract = 'main_contract'
                            main = False
                            payment = 'split_payment'
                    date = rec._set_expiry_date()
                    context = {
                        'services_good': 1,
                        'default_is_service': True,
                        'default_is_services_orders': True,
                        'default_is_subcontracting': True,
                        'search_default_project' : 1
                        }
                    vals = {
                        'partner_id': vendor.id,
                        'project': rec.project.id,
                        'cost_sheet': rec.cost_sheet.id,
                        'project_budget': rec.project_budget.id,
                        'date_order': date,
                        'agreement_id': rec.id,
                        'origin': rec.name,
                        'is_subcontracting': True,
                        'analytic_account_group_ids': rec.account_tag_ids.ids,
                        'branch_id': rec.branch_id.id,
                        'user_id': rec.sh_purchase_user_id.id,
                        'sub_contracting' : contract,
                        'addendum_payment_method' : payment,
                        'main_po_reference': main,
                        'contract_parent_po': main,
                        'variable_line_ids': line_ids,
                        'material_line_ids': material,
                        'service_line_ids': service,
                        'equipment_line_ids': equipment,
                        'labour_line_ids': labour,
                        'overhead_line_ids': overhead,
                        'picking_type_id': self.destination_warehouse_id.pick_type_id.id,
                    }
                    po_subcon = po_obj.with_context(context).create(vals)
                    for line in po_subcon.variable_line_ids:
                        line._onchange_subcon()
                    i += 1
                if i and rec.state2 == 'pending':
                    rec.state = 'bid_submission'
                
                tree_view_ref = self.env.ref('equip3_construction_purchase_operation.purchase_order_kpis_tree_cons_inherit', False)
                form_view_ref = self.env.ref('equip3_construction_purchase_operation.direct_purchase_form_view_equip3_purchase_other_operation_const_rfq_1', False)
                return {
                    'name': _('Received Quotations'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'purchase.order',
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_id': self.id,
                    'domain': [('agreement_id', '=', self.id), ('selected_order', '=', False), ('state', 'in', ['draft'])],
                    'target': 'current',
                    'views': [(tree_view_ref.id, 'tree'), (form_view_ref.id, 'form')],
                }

    @api.onchange('is_subcontracting')
    def _onchange_is_subcontracting(self):
        context = dict(self.env.context) or {}
        if context.get('services_good'):
            self.is_subcontracting = True

    @api.onchange('is_material_orders')
    def _onchange_is_material_orders(self):
        context = dict(self.env.context) or {}
        if context.get('goods_order'):
            self.is_material_orders = True

    @api.onchange('is_orders')
    def _onchange_is_orders(self):
        context = dict(self.env.context) or {}
        if context.get('orders'):
            self.is_orders = True

    @api.onchange('material_order')
    def _onchange_material_order(self):
        context = dict(self.env.context) or {}
        if context.get('goods_order'):
            self.material_order = True

    def _compute_purchase_tender_count(self):
        purchase_agreement_obj = self.env['purchase.agreement']
        for task in self:
            if task.name != False:
                po_count = purchase_agreement_obj.search_count([('sh_source','=',task.name), ('is_subcontracting','=',True)])
                if po_count:
                    task.po_tender_count = po_count
                else:
                    task.po_tender_count = 0
            else:
                task.po_tender_count = 0

    def _comute_split_tender_count(self):
        for rec in self:
            split_tender = self.env['purchase.agreement'].search_count([('sh_source','=',rec.name), ('is_material_orders','=',True), ('project','=',rec.project.id)])
            rec.total_split_tender = split_tender

    def action_material_tender(self):
        return {
            'name': ("Material Tender"),
            'view_mode': 'tree,form',
            'res_model': 'purchase.agreement',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('sh_source','=',self.name), ('is_material_orders','=',True), ('project','=',self.project.id)],
        }

    def split_purchase_agreement(self):
        """
        showing Split Purchase Agreement wizard and
        raise error if Received Quotation=0
        """
        for rec in self:
            if rec.rfq_count >= 0:
                return {    # Return Wizard Action calls if condition is True
                    'name': _('Split Purchase Agreement'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'wizard.purchase.agreement',
                    'context': {'default_agreement_id': rec.id},
                    'view_id': self.env.ref(
                        'equip3_construction_purchase_other_operation.wizard_split_purchase_agreement_form').id,
                    'view_type': 'form',
                    'view_mode': 'form',
                    'target': 'new',
                }


        # vals = self.agreement_id
        # res = self.env['purchase.agreement'].browse(vals.id)
        # if self.split_table == "material":
        #     for rec in self:
        #         rec.material_line_ids = [(5, 0, 0)]

    def action_confirm(self):
        if self:
            for rec in self:
                seq = self.env['ir.sequence'].next_by_code(
                    'purchase.agreement')
                rec.name = seq
                rec.state = 'confirm'
                if rec.is_subcontracting == False:
                    if not rec.sh_purchase_agreement_line_ids:
                        raise UserError(_("You cannot confirm Purchase Tender '%s' because there is no product line.", rec.name))

                    for vals in rec.sh_purchase_agreement_line_ids:
                        if vals.sh_qty <= 0 :
                            raise UserError("You cannot confirm purchase tender without quantity.")
                if self.cost_sheet.state == 'freeze':
                    raise ValidationError("The budget for this project is being freeze")
                else:
                    for rec in self.variable_line_ids:
                        if rec.quantity > rec.budget_qty:
                            raise ValidationError(_("The quantity is over the budget quantity"))
                        elif rec.reference_price > rec.budget_amount:
                            raise ValidationError(_("The reference price is over the unit price budget"))
                        rec.state = 'pending'


    # def action_confirm(self):
    #     res = super(PurchaseTender, self).action_confirm()
    #     if self.cost_sheet.state == 'freeze':
    #         raise ValidationError("The budget for this project is being freeze")
    #     else:
    #         for rec in self.variable_line_ids:
    #             if rec.quantity > rec.budget_qty:
    #                 raise ValidationError(_("The quantity is over the budget quantity"))
    #             elif rec.reference_price > rec.budget_amount:
    #                 raise ValidationError(_("The reference price is over the unit price budget"))
    #             rec.state = 'pending'
    #         return res

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


class VariableLine(models.Model):
    _name = 'pt.variable.line'
    _description = "Variable Line"
    _order = "sequence"

    sequence = fields.Integer('Sequence', default=1)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    cs_subcon_id = fields.Many2one('material.subcon', string='CS Subcon ID')
    bd_subcon_id = fields.Many2one('budget.subcon', string='BD Subcon ID')
    bd_subcon_ids = fields.Many2many('budget.gop.overhead', string='BD Subcon IDS')
    variable_id = fields.Many2one('purchase.agreement', string='Variable ID')
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section = fields.Many2one('section.line', string='Section')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    variable = fields.Many2one('variable.template', string='Job Subcon')
    quantity = fields.Float(string='Quantity')
    budget_qty = fields.Float(string='Budget Quantity')
    budget_amount = fields.Float(string='Budget Unit Price')
    uom = fields.Many2one('uom.uom', string='Unit of Measure')
    reference_price = fields.Float(string='Reference Price')
    purchase_request_id = fields.Many2one('pr.variable.line', 'PR Subcon Line')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Group')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'Waiting For Approval'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rfq', 'Request for Quotation'),
        ('purchase_order', 'Purchase Order'),
        ('rejected', 'Rejected'),
        ('done', 'done'),
        ('canceled', 'Canceled'),
        ], string='Purchase Status', default='draft')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                 compute='get_section_lines')
    project = fields.Many2one(related='variable_id.project', string='Project')
    schedule_date = fields.Date(related='variable_id.sh_delivery_date', string='Scheduled Date')

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
    

    @api.onchange('variable')
    def onchange_variable(self):
        res = {}
        if not self.variable:
            return res
        self.uom = self.variable.variable_uom.id
        self.quantity = 1.0

    @api.onchange('quantity')
    def quantity_validation(self):
        if self.quantity > self.budget_qty:
            raise ValidationError(_("The quantity is over the budget quantity"))

    @api.onchange('reference_price')
    def reference_price_validation(self):
        if self.reference_price > self.budget_amount:
            raise ValidationError(_("The reference price is over the unit price budget"))

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
        vals['sr_no'] = self.env['ir.sequence'].next_by_code('variable_product') or ('New')
        res = super(VariableLine, self).create(vals)
        return res


class MaterialLine(models.Model):
    _name = 'material.line'
    _description = "Material Line"
    _order = "sequence"

    sequence = fields.Integer('Sequence', default=1)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    cs_subcon_id = fields.Many2one('material.subcon', string='CS Subcon ID', compute="_compute_cs_subcon_id")
    bd_subcon_id = fields.Many2one('budget.subcon', string='BD Subcon ID', compute="_compute_bd_subcon_id")
    variable_material_id = fields.Many2one('pr.variable.line', 'Variable Material ID', compute="_compute_variable_material_id")
    material_id = fields.Many2one('purchase.agreement', 'Material ID')
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section = fields.Many2one('section.line', string='Section')
    variable = fields.Many2one('variable.template', string='Variable')
    subcon = fields.Many2one('variable.template', string='Job Subcon')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    product = fields.Many2one('product.product', string='Product')
    description = fields.Char(string='Description')
    quantity = fields.Float(string='Quantity')
    budget_quantity = fields.Float(string='Budget Quantity')
    uom = fields.Many2one('uom.uom', string='Unit of Measure')
    destination_warehouse = fields.Many2one(related='material_id.destination_warehouse_id', string='Destination')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Group')
    schedule_date = fields.Date(related='material_id.sh_delivery_date', string='Scheduled Date')
    reference_price = fields.Float(string= 'Reference Price')
    subtotal = fields.Float('Subtotal', readonly=True, compute='_compute_subtotal')
    company_id = fields.Many2one(related='material_id.company_id', string='Company')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                 compute='get_section_lines')
    project = fields.Many2one(related='material_id.project', string='Project')

    def _compute_cs_subcon_id(self):
        for rec in self:
            cs_subcon_id = rec.material_id.cost_sheet.material_subcon_ids.filtered(lambda x: x.project_scope.id == rec.project_scope.id and x.section_name.id == rec.section.id and x.variable.id == rec.subcon.id)
            rec.cs_subcon_id = cs_subcon_id.id or False

    def _compute_bd_subcon_id(self):
        for rec in self:
            bd_subcon_id = rec.material_id.project_budget.budget_subcon_ids.filtered(lambda x: x.project_scope.id == rec.project_scope.id and x.section_name.id == rec.section.id and x.subcon_id.id == rec.subcon.id)
            rec.bd_subcon_id = bd_subcon_id.id or False

    def _compute_variable_material_id(self):
        for rec in self:
            variable_material_id = rec.subcon.material_variable_ids.filtered(lambda x: x.group_of_product.id == rec.group_of_product.id and x.product_id.id == rec.product.id)
            rec.variable_material_id = variable_material_id.id or False
    @api.depends('quantity', 'reference_price')
    def _compute_subtotal(self):
        price = 0.0
        for line in self:
            if line.quantity <= 0:
                raise ValidationError('Quantity should be greater than 0.')
            else:
                price = (line.quantity * line.reference_price)
                line.subtotal = price

    @api.onchange('group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            group_of_product = rec.group_of_product.id if rec.group_of_product else False
            return {
                'domain': {'product': [('group_of_product', '=', group_of_product)]}
            }

    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self.product and self.group_of_product:
            if self.group_of_product.id not in self.product.group_of_product.ids:
                self.update({
                    'product': False,
                })
    
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
        self.ordered_quantity = 0
        self.quantity = 1.0
        self.uom = self.product.uom_id.id

    @api.onchange('product')
    def compute_groupofproduct(self):
        if self.product:
            self.group_of_product = self.product.group_of_product.id

    @api.depends('material_id.material_line_ids', 'material_id.material_line_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.material_id.material_line_ids:
                no += 1
                l.sr_no = no

    @api.model
    def create(self, vals):
        vals['sr_no'] = self.env['ir.sequence'].next_by_code('material_request') or ('New')
        res = super(MaterialLine, self).create(vals)
        return res


class ServiceLine(models.Model):
    _name = 'service.line'
    _description = "Service Line"
    _order = "sequence"

    sequence = fields.Integer('Sequence', default=1)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    service_id = fields.Many2one('purchase.agreement', 'Service ID')
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section = fields.Many2one('section.line', string='Section')
    variable = fields.Many2one('variable.template', string='Variable')
    subcon = fields.Many2one('variable.template', string='Job Subcon')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    product = fields.Many2one('product.product', string='Product')
    description = fields.Char(string='Description')
    quantity = fields.Float(string='Quantity')
    uom = fields.Many2one('uom.uom', string='Unit of Measure')
    destination_warehouse = fields.Many2one(related='service_id.destination_warehouse_id', string='Destination')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Group')
    schedule_date = fields.Date(related='service_id.sh_delivery_date', string='Scheduled Date')
    reference_price = fields.Float(string= 'Reference Price')
    subtotal = fields.Float('Subtotal', readonly=True, compute='_compute_subtotal')
    company_id = fields.Many2one(related='service_id.company_id', string='Company')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                 compute='get_section_lines')
    project = fields.Many2one(related='service_id.project', string='Project')

    @api.depends('quantity', 'reference_price')
    def _compute_subtotal(self):
        price = 0.0
        for line in self:
            if line.quantity <= 0:
                raise ValidationError('Quantity should be greater than 0.')
            else:
                price = (line.quantity * line.reference_price)
                line.subtotal = price

    @api.onchange('group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            group_of_product = rec.group_of_product.id if rec.group_of_product else False
            return {
                'domain': {'product': [('group_of_product', '=', group_of_product)]}
            }

    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self.product and self.group_of_product:
            if self.group_of_product.id not in self.product.group_of_product.ids:
                self.update({
                    'product': False,
                })
    
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
        self.ordered_quantity = 0
        self.quantity = 1.0
        self.uom = self.product.uom_id.id

    @api.onchange('product')
    def compute_groupofproduct(self):
        for res in self:
            if res.product:
                res.group_of_product = res.product.group_of_product.id

    @api.depends('service_id.service_line_ids', 'service_id.service_line_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.service_id.service_line_ids:
                no += 1
                l.sr_no = no

    @api.model
    def create(self, vals):
        vals['sr_no'] = self.env['ir.sequence'].next_by_code('service_request') or ('New')
        res = super(ServiceLine, self).create(vals)
        return res


class PAEquipmentLine(models.Model):
    _name = 'pa.equipment.line'
    _description = "Equipment Line"
    _order = "sequence"

    sequence = fields.Integer('Sequence', default=1)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    equipment_id = fields.Many2one('purchase.agreement', 'Equipment ID')
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section = fields.Many2one('section.line', string='Section')
    variable = fields.Many2one('variable.template', string='Variable')
    subcon = fields.Many2one('variable.template', string='Job Subcon')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    product = fields.Many2one('product.product', string='Product')
    description = fields.Char(string='Description')
    quantity = fields.Float(string='Quantity')
    uom = fields.Many2one('uom.uom', string='Unit of Measure')
    destination_warehouse = fields.Many2one(related='equipment_id.destination_warehouse_id', string='Destination')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Group')
    schedule_date = fields.Date(related='equipment_id.sh_delivery_date', string='Scheduled Date')
    reference_price = fields.Float(string= 'Reference Price')
    subtotal = fields.Float('Subtotal', readonly=True, compute='_compute_subtotal')
    company_id = fields.Many2one(related='equipment_id.company_id', string='Company')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                 compute='get_section_lines')
    project = fields.Many2one(related='equipment_id.project', string='Project')

    @api.depends('quantity', 'reference_price')
    def _compute_subtotal(self):
        price = 0.0
        for line in self:
            if line.quantity <= 0:
                raise ValidationError('Quantity should be greater than 0.')
            else:
                price = (line.quantity * line.reference_price)
                line.subtotal = price

    @api.onchange('group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            group_of_product = rec.group_of_product.id if rec.group_of_product else False
            return {
                'domain': {'product': [('group_of_product', '=', group_of_product)]}
            }

    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self.product and self.group_of_product:
            if self.group_of_product.id not in self.product.group_of_product.ids:
                self.update({
                    'product': False,
                })
    
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
        self.ordered_quantity = 0
        self.quantity = 1.0
        self.uom = self.product.uom_id.id
    
    @api.onchange('product')
    def compute_groupofproduct(self):
        if self.product:
            self.group_of_product = self.product.group_of_product.id

    @api.depends('equipment_id.equipment_line_ids', 'equipment_id.equipment_line_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.equipment_id.equipment_line_ids:
                no += 1
                l.sr_no = no

    @api.model
    def create(self, vals):
        vals['sr_no'] = self.env['ir.sequence'].next_by_code('pa_equipment_request') or ('New')
        res = super(PAEquipmentLine, self).create(vals)
        return res


class LabourLine(models.Model):
    _name = 'labour.line'
    _description = "Labour Line"
    _order = "sequence"

    sequence = fields.Integer('Sequence', default=1)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    labour_id = fields.Many2one('purchase.agreement', 'Labour ID')
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section = fields.Many2one('section.line', string='Section')
    variable = fields.Many2one('variable.template', string='Variable')
    subcon = fields.Many2one('variable.template', string='Job Subcon')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    product = fields.Many2one('product.product', string='Product')
    description = fields.Char(string='Description')
    quantity = fields.Float(string='Quantity')
    uom = fields.Many2one('uom.uom', string='Unit of Measure')
    destination_warehouse = fields.Many2one(related='labour_id.destination_warehouse_id', string='Destination')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Group')
    schedule_date = fields.Date(related='labour_id.sh_delivery_date', string='Scheduled Date')
    reference_price = fields.Float(string= 'Reference Price')
    subtotal = fields.Float('Subtotal', readonly=True, compute='_compute_subtotal')
    company_id = fields.Many2one(related='labour_id.company_id', string='Company')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                 compute='get_section_lines')
    project = fields.Many2one(related='labour_id.project', string='Project')

    @api.depends('quantity', 'reference_price')
    def _compute_subtotal(self):
        price = 0.0
        for line in self:
            if line.quantity <= 0:
                raise ValidationError('Quantity should be greater than 0.')
            else:
                price = (line.quantity * line.reference_price)
                line.subtotal = price

    @api.onchange('group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            group_of_product = rec.group_of_product.id if rec.group_of_product else False
            return {
                'domain': {'product': [('group_of_product', '=', group_of_product)]}
            }

    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self.product and self.group_of_product:
            if self.group_of_product.id not in self.product.group_of_product.ids:
                self.update({
                    'product': False,
                })
    
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

    @api.depends('labour_id.labour_line_ids', 'labour_id.labour_line_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.labour_id.labour_line_ids:
                no += 1
                l.sr_no = no

    @api.model
    def create(self, vals):
        vals['sr_no'] = self.env['ir.sequence'].next_by_code('labour_request') or ('New')
        res = super(LabourLine, self).create(vals)
        return res


class OverheadLine(models.Model):
    _name = 'overhead.line'
    _description = "Overhead Line"
    _order = "sequence"

    sequence = fields.Integer('Sequence', default=1)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    overhead_id = fields.Many2one('purchase.agreement', 'Overhead ID')
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section = fields.Many2one('section.line', string='Section')
    variable = fields.Many2one('variable.template', string='Variable')
    subcon = fields.Many2one('variable.template', string='Job Subcon')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    product = fields.Many2one('product.product', string='Product')
    description = fields.Char(string='Description')
    quantity = fields.Float(string='Quantity')
    uom = fields.Many2one('uom.uom', string='Unit of Measure')
    destination_warehouse = fields.Many2one(related='overhead_id.destination_warehouse_id', string='Destination')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Group')
    schedule_date = fields.Date(related='overhead_id.sh_delivery_date', string='Scheduled Date')
    reference_price = fields.Float(string= 'Reference Price')
    subtotal = fields.Float('Subtotal', readonly=True, compute='_compute_subtotal')
    company_id = fields.Many2one(related='overhead_id.company_id', string='Company')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                 compute='get_section_lines')
    project = fields.Many2one(related='overhead_id.project', string='Project')

    @api.depends('quantity', 'reference_price')
    def _compute_subtotal(self):
        price = 0.0
        for line in self:
            if line.quantity <= 0:
                raise ValidationError('Quantity should be greater than 0.')
            else:
                price = (line.quantity * line.reference_price)
                line.subtotal = price

    @api.onchange('group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            group_of_product = rec.group_of_product.id if rec.group_of_product else False
            return {
                'domain': {'product': [('group_of_product', '=', group_of_product)]}
            }

    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self.product and self.group_of_product:
            if self.group_of_product.id not in self.product.group_of_product.ids:
                self.update({
                    'product': False,
                })
    
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
        self.ordered_quantity = 0
        self.quantity = 1.0
        self.uom = self.product.uom_id.id

    @api.onchange('product')
    def compute_groupofproduct(self):
        if self.product:
            self.group_of_product = self.product.group_of_product.id

    @api.depends('overhead_id.overhead_line_ids', 'overhead_id.overhead_line_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.overhead_id.overhead_line_ids:
                no += 1
                l.sr_no = no

    @api.model
    def create(self, vals):
        vals['sr_no'] = self.env['ir.sequence'].next_by_code('overhead_request') or ('New')
        res = super(OverheadLine, self).create(vals)
        return res


class PurchaseTenderLine(models.Model):
    _inherit = 'purchase.agreement.line'

    var_material_id = fields.Many2one('material.variable', 'VAR Material ID', Store="1")
    cs_material_id = fields.Many2one('material.material', 'CS Material ID', Store="1")
    cs_labour_id = fields.Many2one('material.labour', 'CS Labour ID', Store="1")
    cs_overhead_id = fields.Many2one('material.overhead', 'CS Overhead ID', Store="1")
    cs_equipment_id = fields.Many2one('material.equipment', 'CS Equipment ID', Store="1")
    cs_subcon_id = fields.Many2one('material.subcon', 'CS Subcon ID', Store="1")
    bd_material_id = fields.Many2one('budget.material', 'BD Material ID', Store="1")
    bd_labour_id = fields.Many2one('budget.labour', 'BD Labour ID', Store="1")
    bd_overhead_id = fields.Many2one('budget.overhead', 'BD Overhead ID', Store="1")
    bd_equipment_id = fields.Many2one('budget.equipment', 'BD equipment ID', Store="1")
    bd_subcon_id = fields.Many2one('budget.subcon', 'BD Subcon ID', Store="1")
    type = fields.Selection([('material','Material'),
                            ('labour','Labour'),
                            ('overhead','Overhead'),
                            ('equipment','Equipment'),
                            ('split','Split')],
                            string = "Type")
    project_scope = fields.Many2one('project.scope.line', 'Project Scope')
    section = fields.Many2one('section.line', 'Section')
    variable = fields.Many2one('variable.template', 'Variable')
    subcon = fields.Many2one('variable.template', 'Subcon')
    group_of_product = fields.Many2one('group.of.product', 'Group of Product')
    budget_quantity = fields.Float('Budget Quantity')

    @api.onchange('group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            if rec.group_of_product:
                group_of_product = rec.group_of_product.id if rec.group_of_product else False
                return {
                    'domain': {'sh_product_id': [('group_of_product', '=', group_of_product)]}
                }
            else:
                return {
                    'domain': {'sh_product_id': []}
                }

    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self.sh_product_id and self.group_of_product:
            if self.group_of_product.id not in self.sh_product_id.group_of_product.ids:
                self.update({
                    'sh_product_id': False,
                })
