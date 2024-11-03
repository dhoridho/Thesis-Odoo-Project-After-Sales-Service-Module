from odoo import api, fields, models, _
from datetime import datetime, date
from odoo.exceptions import UserError, ValidationError


class JobCostSheet(models.Model):
    _inherit = 'job.cost.sheet'

    is_engineering = fields.Boolean('Engineering', readonly=True, compute='onchange_project_enginerring')
    manufacture_line = fields.One2many('cost.manufacture.line', 'job_sheet_id')
    # amount material
    manuf_budget_created = fields.Monetary(string='Manufacture Budget Created', readonly=True, Store=True,
                                           force_save="1")
    manuf_budget_left = fields.Monetary(string='Manufacture Budget Left', readonly=True, Store=True, force_save="1")
    amount_manuf = fields.Monetary(string='Manufacture Cost', readonly=True, compute='_amount_manuf')
    # manuf used/unused
    manuf_budget_unused = fields.Monetary(string='Manufacture Budget Unused', readonly=True, Store=True, force_save="1")
    manuf_budget_used = fields.Monetary(string='Manufacture Budget Used', readonly=True, Store=True, force_save="1")
    # manuf_actual_cost = fields.Monetary(string='Manufacture Actual Cost', readonly=True, Store= True, force_save="1")
    count_mrp_cons = fields.Integer(compute="_compute_count_mrp_cons")

    type = fields.Selection([('construction', 'Construction'), ('engineering', 'Engineering')],
                            string="Type", related='project_id.construction_type')
    hide_cascade = fields.Boolean('Hide cascade button', default=True, compute='_compute_hide_cascade')
    hide_undo = fields.Boolean('Hide undo button', default=True, compute='_compute_hide_undo')

    def _compute_count_mrp_cons(self):
        for res in self:
            mrp = self.env['mrp.plan'].search_count(
                [('cost_sheet', '=', res.id), ('project_id', '=', res.project_id.id),
                 ('contract', 'in', res.sale_order_ref.ids)])
            res.count_mrp_cons = mrp

    def action_mrp_cons(self):
        return {
            'name': ("Production Plan"),
            'view_mode': 'tree,form',
            'res_model': 'mrp.plan',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('cost_sheet', '=', self.id), ('project_id', '=', self.project_id.id),
                       ('contract', 'in', self.sale_order_ref.ids)],
        }

    def get_so_line_condition(self, scope_new_data, section_new_data, data, scope_data, section_data, line=False,
                              line_product_id=False):
        return [
            scope_new_data.name == scope_data.name,
            section_new_data.name == section_data.name,
            data[2].get('finish_good_id') == line.finish_good_id.id,
            data[2].get('group_of_product') == line.group_of_product.id,
            data[2].get('product_id') == line_product_id.id,
            data[2].get('description') == line.description,
            data[2].get('uom_id') == line.uom_id.id,
        ]

    def prepare_material_so(self, item):
        res = super(JobCostSheet, self).prepare_material_so(item)
        res['finish_good_id'] = item.finish_good_id.id
        res['bom_id'] = item.bom_id.id
        return res

    def prepare_labour_so(self, item):
        res = super(JobCostSheet, self).prepare_labour_so(item)
        res['finish_good_id'] = item.finish_good_id.id
        res['bom_id'] = item.bom_id.id
        return res

    def prepare_subcon_so(self, item):
        res = super(JobCostSheet, self).prepare_subcon_so(item)
        res['finish_good_id'] = item.finish_good_id.id
        res['bom_id'] = item.bom_id.id
        return res

    def prepare_overhead_so(self, item):
        res = super(JobCostSheet, self).prepare_overhead_so(item)
        res['finish_good_id'] = item.finish_good_id.id
        res['bom_id'] = item.bom_id.id
        return res

    def prepare_asset_so(self, item):
        res = super(JobCostSheet, self).prepare_asset_so(item)
        res['finish_good_id'] = item.finish_good_id.id
        res['bom_id'] = item.bom_id.id
        return res

    def prepare_equipment_so(self, item):
        res = super(JobCostSheet, self).prepare_equipment_so(item)
        res['finish_good_id'] = item.finish_good_id.id
        res['bom_id'] = item.bom_id.id
        return res

    def _sales_order_onchange(self):
        res = super(JobCostSheet, self)._sales_order_onchange()
        self.manufacture_line = [(5, 0, 0)]
        if self.is_empty_cost_sheet == False:
            if self.sale_order_ref:
                sale = self.sale_order_ref
                data_added = []
                for manuf in sale.manufacture_line:
                    append = True
                    section_data = self.env['section.line'].search([('id', '=', manuf.section.id)])
                    scope_data = self.env['project.scope.line'].search([('id', '=', manuf.project_scope.id)])
                    for data in data_added:
                        scope_new_data = self.env['project.scope.line'].search(
                            [('id', '=', data[2].get('project_scope'))])
                        section_new_data = self.env['section.line'].search([('id', '=', data[2].get('section_name'))])
                        condition = [
                            scope_new_data.id == scope_data.id,
                            section_new_data.id == section_data.id,
                            data[2].get('finish_good_id') == manuf.finish_good_id.id,
                            data[2].get('bom_id') == manuf.bom_id.id,
                            data[2].get('uom_id') == manuf.uom_id.id,
                            data[2].get('final_finish_good_id') == manuf.final_finish_good_id.id,
                        ]
                        if all(condition):
                            append = False
                            data[2]['product_qty'] += manuf.quantity
                            data[2]['manuf_amount_total'] += manuf.subtotal_manuf

                    if append:
                        data_added.append((0, 0, {
                            'project_scope': manuf.project_scope.id,
                            'section_name': manuf.section.id,
                            'variable_ref': manuf.variable_ref.id,
                            'final_finish_good_id': manuf.final_finish_good_id.id or False,
                            'finish_good_id': manuf.finish_good_id.id,
                            'bom_id': manuf.bom_id.id,
                            'product_qty': manuf.quantity,
                            'uom_id': manuf.uom_id.id,
                            'price_unit': manuf.bom_id.forecast_cost,
                            'manuf_amount_total': manuf.subtotal_manuf,
                        }))
                self.manufacture_line = data_added
        return res

    def send_vo_material(self, material):
        res = super(JobCostSheet, self).send_vo_material(material)
        res['finish_good_id'] = material.finish_good_id.id
        res['bom_id'] = material.bom_id.id
        return res

    def send_vo_labour(self, labour):
        res = super(JobCostSheet, self).send_vo_labour(labour)
        res['finish_good_id'] = labour.finish_good_id.id
        res['bom_id'] = labour.bom_id.id
        return res

    def send_vo_subcon(self, subcon):
        res = super(JobCostSheet, self).send_vo_subcon(subcon)
        res['finish_good_id'] = subcon.finish_good_id.id
        res['bom_id'] = subcon.bom_id.id
        return res

    def send_vo_overhead(self, overhead):
        res = super(JobCostSheet, self).send_vo_overhead(overhead)
        res['finish_good_id'] = overhead.finish_good_id.id
        res['bom_id'] = overhead.bom_id.id
        return res

    def send_vo_asset(self, asset):
        res = super(JobCostSheet, self).send_vo_asset(asset)
        res['finish_good_id'] = asset.finish_good_id.id
        res['bom_id'] = asset.bom_id.id
        return res

    def send_vo_equipment(self, equipment):
        res = super(JobCostSheet, self).send_vo_equipment(equipment)
        res['finish_good_id'] = equipment.finish_good_id.id
        res['bom_id'] = equipment.bom_id.id
        return res

    def filter_ids(self, exist_ids, line=False, line_product_id=False):
        filtered_ids = exist_ids.filtered(lambda p: p.project_scope.name == line.project_scope.name and
                                                    p.section_name.name == line.section_name.name and
                                                    p.finish_good_id == line.finish_good_id and
                                                    p.bom_id == line.bom_id and
                                                    p.group_of_product == line.group_of_product and
                                                    p.product_id == line_product_id and
                                                    p.description == line.description)
        return filtered_ids

    def filter_asset_ids(self, exist_ids, line=False, line_product_id=False):
        filtered_ids = exist_ids.filtered(lambda p: p.project_scope.name == line.project_scope.name and
                                                    p.section_name.name == line.section_name.name and
                                                    p.finish_good_id == line.finish_good_id and
                                                    p.bom_id == line.bom_id and
                                                    p.asset_category_id == line.asset_category_id and
                                                    p.asset_id == line_product_id)
        return filtered_ids

    @api.onchange('project_id')
    def onchange_project_enginerring(self):
        if self.project_id:
            self.is_engineering = False
            if self.project_id.construction_type == 'engineering':
                self.is_engineering = True

    # amount manuf ---------------------
    @api.depends('manufacture_line.manuf_amount_total')
    def _amount_manuf(self):
        for sheet in self:
            amount_manuf = 0.0
            amount_cre_manuf = 0.0
            amount_left_manuf = 0.0
            amount_used_manuf = 0.0
            amount_unused_manuf = 0.0
            for line in sheet.manufacture_line:
                amount_manuf += line.manuf_amount_total
                amount_cre_manuf += line.manuf_create_amt
                amount_left_manuf += line.budgeted_amt_left
                amount_used_manuf += line.actual_used_amt
                amount_unused_manuf += line.unused_amt
            sheet.update({
                'manuf_budget_created': amount_cre_manuf,
                'manuf_budget_left': amount_left_manuf,
                'manuf_budget_used': amount_used_manuf,
                'manuf_budget_unused': amount_unused_manuf,
                'amount_manuf': amount_manuf,
            })

    def _compute_hide_cascade(self):
        for res in self:
            if res.manufacture_line:
                for line in res.manufacture_line:
                    if line.cascaded == False:
                        res.hide_cascade = False
                        return
                res.hide_cascade = True
            else:
                res.hide_cascade = True

    def _compute_hide_undo(self):
        for res in self:
            if res.manufacture_line:
                for line in res.manufacture_line:
                    if line.cascaded != False:
                        res.hide_undo = False
                        return
                res.hide_undo = True
                return
            else:
                res.hide_undo = True
                return
            
    def cascade_bom_button(self):
        def _get_manuf_line_cascade(line):
            return {
                'cost_manuf_line_id': line.id,
                'project_scope': line.project_scope.id,
                'section_name': line.section_name.id,
                'finish_good_id': line.finish_good_id.id,
                'finish_good_id_template': line.finish_good_id_template.id,
                'bom_id': line.bom_id.id,
                'product_qty': line.product_qty,
            }
        manuf_line = []
        for line in self.manufacture_line.filtered(lambda l: l.cascaded == False):
            manuf_line.append((0, 0, _get_manuf_line_cascade(line)))
        if len(manuf_line) > 0:
            context = {
                'default_company_id': self.company_id.id,
                'default_project_id': self.project_id.id,
                'default_cost_sheet': self.id,
                'default_hide_job_estimate': True,
                'default_undo_cascade': False,
                'default_job_cascade_line_ids': manuf_line,
                }
            return {
                    'type': 'ir.actions.act_window',
                    'name': 'Create Quotation',
                    'res_model': 'job.cascade.wizard',
                    'context': context,
                    'view_type': 'form',
                    'view_mode': 'form',
                    'target': 'new',
                }
        else:
            raise ValidationError("The to manufacture table is empty, please input at least one line!")

    def undo_cascade_bom(self):
        def _get_manuf_line_undo(line):
            return {
                'cost_manuf_line_id': line.id,
                'project_scope': line.project_scope.id,
                'section_name': line.section_name.id,
                'finish_good_id': line.finish_good_id.id,
                'finish_good_id_template': line.finish_good_id_template.id,
                'bom_id': line.bom_id.id,
                'product_qty': line.product_qty,
            }
        manuf_line = []
        for line in self.manufacture_line.filtered(lambda l: l.cascaded == True and not l.parent_manuf_line):
            manuf_line.append((0, 0, _get_manuf_line_undo(line)))
        if len(manuf_line) > 0:
            context = {
                'default_company_id': self.company_id.id,
                'default_project_id': self.project_id.id,
                'default_cost_sheet': self.id,
                'default_hide_job_estimate': True,
                'default_undo_cascade': True,
                'default_job_cascade_line_ids': manuf_line,
                }
            return {
                    'type': 'ir.actions.act_window',
                    'name': 'Undo Cascade to Child BOM',
                    'view_mode': 'form',
                    'res_model': 'job.cascade.wizard',
                    'target': 'new',
                    'context': context
                }
        else:
            raise ValidationError("The to manufacture table is empty, please input at least one line!")


    def action_cost_sheet_revision(self, default=None):
        self.state = 'revised'
        if self:
            self.ensure_one()
            self.is_revision_created = True
            if default is None:
                default = {}

            # Change number
            if self.is_revision_cs:
                cs_count = self.search([("main_revision_cs_id", '=', self.main_revision_cs_id.id), ('is_revision_cs', '=', True)])
                split_number = self.number.split('/')
                if split_number[-1].startswith('R'):
                    split_number[-1] = 'R%d' % (len(cs_count) + 1)
                else:
                    split_number.append('R%d' % (len(cs_count) + 1))
                number = '/'.join(split_number)
            else:
                cs_count = self.search([("main_revision_cs_id", '=', self.id), ('is_revision_cs', '=', True)])
                number = _('%s/R%d') % (self.number, len(cs_count) + 1)

            # Setting the default values for the new record.
            if 'number' not in default:
                default['state'] = 'draft'
                default['revision_cs_id'] = self.id 
                default['is_revision_cs'] = True
                if self.is_revision_cs:
                    default['main_revision_cs_id'] = self.main_revision_cs_id.id
                else:
                    default['main_revision_cs_id'] = self.id
                default['is_revision_created'] = False
                default['revision_count'] = 0
                
            new_project_id = self.copy(default=default)
            # Contract History
            for contract_line in self.contract_history_ids:
                contract_line.copy({
                    'job_sheet_id': new_project_id.id,
                })
            # Manuf
            for manuf_line in self.manufacture_line:
                manuf_line.copy({
                    'job_sheet_id': new_project_id.id,
                })
            # Material
            for material_line in self.material_ids:
                material_line.copy({
                    'job_sheet_id': new_project_id.id,
                })
            for material_gop in self.material_gop_ids:
                material_gop.copy({
                    'job_sheet_id': new_project_id.id,
                })
            # Labour
            for labour_line in self.material_labour_ids:
                labour_line.copy({
                    'job_sheet_id': new_project_id.id,
                })
            for labour_gop in self.material_labour_gop_ids:
                labour_gop.copy({
                    'job_sheet_id': new_project_id.id,
                })
            # Overhead
            for overhead_line in self.material_overhead_ids:
                overhead_line.copy({
                    'job_sheet_id': new_project_id.id,
                })
            for overhead_gop in self.material_overhead_gop_ids:
                overhead_gop.copy({
                    'job_sheet_id': new_project_id.id,
                })
            # Internal Asset
            for asset_line in self.internal_asset_ids:
                asset_line.copy({
                    'job_sheet_id': new_project_id.id,
                })
            # Equipment
            for equipment_line in self.material_equipment_ids:
                equipment_line.copy({
                    'job_sheet_id': new_project_id.id,
                })
            for equipment_gop in self.material_equipment_gop_ids:
                equipment_gop.copy({
                    'job_sheet_id': new_project_id.id,
                })
            # Subcon
            for subcon_line in self.material_subcon_ids:
                subcon_line.copy({
                    'job_sheet_id': new_project_id.id,
                })
            for subcon_gop in self.material_subcon_gop_ids:
                subcon_gop.copy({
                    'job_sheet_id': new_project_id.id,
                })
            # Approval Matrix Line
            for approval_line in self.cost_sheet_user_ids:
                approval_line.copy({
                    'cost_sheet_approver_id': new_project_id.id,
                })

            new_project_id.cost_sheet_user_ids = [(5, 0, 0)]
            new_project_id.write({'state': 'draft',
                          'approved_user_ids': False,
                          'approved_user': False,
                          })
            new_project_id.onchange_approving_matrix_lines()

            if number.startswith('JCS'):
                new_project_id.number = number

            if self.is_revision_cs:
                new_project_id.revision_history_id = [(6, 0, self.main_revision_cs_id.ids + cs_count.ids)]
            else:
                new_project_id.revision_history_id = [(6, 0, self.ids)]
            
        return {
                'type': 'ir.actions.act_window',
                'name': 'Cost Sheet',
                'view_mode': 'form',
                'res_model': 'job.cost.sheet',
                'res_id' : new_project_id.id,
                'target': 'current'
            }


    project_scope_computed = fields.Many2many('project.scope.line', string="computed scope lines",
                                              compute='get_scope_lines')

    @api.depends('project_id.project_scope_ids')
    def get_scope_lines(self):
        for rec in self:
            pro = rec.project_id
            scope_ids = []
            if pro.project_scope_ids:
                for line in pro.project_scope_ids:
                    if line.project_scope:
                        scope_ids.append(line.project_scope.id)
                rec.project_scope_computed = [(6, 0, scope_ids)]
            else:
                rec.project_scope_computed = [(6, 0, [])]

class CostManufactureLine(models.Model):
    _name = 'cost.manufacture.line'
    _description = 'Cost Manufacture Line'

    job_sheet_id = fields.Many2one('job.cost.sheet', string='Job Sheet', ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date", default=date.today())
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')
    cascaded = fields.Boolean(string="Cascaded", default=False)
    is_child = fields.Boolean(string="Is child", default=False)
    finish_good_id = fields.Many2one('product.product', 'Finished Goods', required=True)
    finish_good_id_template = fields.Many2one(related='finish_good_id.product_tmpl_id', string='Finish Goods Template',
											  readonly=True)
    parent_manuf_line = fields.Many2one('mrp.bom', string='Parent BOM')
    bom_id = fields.Many2one('mrp.bom', 'BOM', required=True)
    product_qty = fields.Float('Quantity', default=1)
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    price_unit = fields.Float(string='Unit Price', default='0.00')
    manuf_amount_total = fields.Float(string='Budgeted Amount')
    budgeted_qty_left = fields.Float('Budgeted Quantity Left', compute="_budget_quntity_left")
    budgeted_amt_left = fields.Float('Budgeted Amount Left', compute="_budget_amount_left")
    rejected_qty = fields.Float('Rejected Quantity', default=0.00)
    actual_used_qty = fields.Float('Actual Used Quantity', default=0.00)
    actual_used_amt = fields.Float('Actual Used Amount', default=0.00)
    manuf_create_qty = fields.Float('Finished Quantity', default=0.00)
    manuf_create_amt = fields.Float('Manufactured Amount', default=0.00)
    allocated_budget_qty = fields.Float('Allocated Budget Quantity', default=0.00)
    allocated_budget_amt = fields.Float('Allocated Budget Amount', default=0.00)
    product_qty_na = fields.Float('Unallocated Quantity', default=0.00, compute="_product_qty_na")
    product_amt_na = fields.Float('Unallocated Amount', default=0.00, compute="_product_amt_na")
    unused_qty = fields.Float('Unused Quantity', default=0.00, compute="_unused_qty")
    unused_amt = fields.Float('Unused Amount', default=0.00, compute="_unused_amt")
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    company_id = fields.Many2one(related='job_sheet_id.company_id', string='Company', store=True, readonly=True,
                                 index=True)
    project_id = fields.Many2one(related='job_sheet_id.project_id', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                 compute='get_section_lines')

    @api.depends('project_id.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:        
                if rec.project_id.project_section_ids:
                    for line in rec.project_id.project_section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.depends('job_sheet_id.manufacture_line', 'job_sheet_id.manufacture_line.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.job_sheet_id.manufacture_line:
                no += 1
                l.sr_no = no

    @api.onchange('product_qty', 'price_unit')
    def onchange_quantity(self):
        price = 0.00
        for line in self:
            price = (line.product_qty * line.price_unit)
            line.manuf_amount_total = price

    @api.onchange('product_qty', 'rejected_qty', 'actual_used_qty')
    def _budget_quntity_left(self):
        for line in self:
            line.budgeted_qty_left = (line.product_qty - line.rejected_qty - line.manuf_create_qty)

    @api.onchange('manuf_amount_total', 'actual_used_amt')
    def _budget_amount_left(self):
        for line in self:
            line.budgeted_amt_left = (line.manuf_amount_total - line.manuf_create_amt)

    def _product_qty_na(self):
        for line in self:
            line.product_qty_na = line.product_qty - line.allocated_budget_qty

    def _product_amt_na(self):
        for line in self:
            line.product_amt_na = line.manuf_amount_total - (line.allocated_budget_qty * line.price_unit)

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    def _unused_qty(self):
        for line in self:
            line.unused_qty = line.product_qty - line.actual_used_qty

    def _unused_amt(self):
        for line in self:
            line.unused_amt = line.manuf_amount_total - line.actual_used_amt


class MaterialGopMaterial(models.Model):
    _inherit = 'material.gop.material'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods')
    bom_id = fields.Many2one('mrp.bom', 'BOM')
    final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')

class MaterialMaterial(models.Model):
    _inherit = 'material.material'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods')
    bom_id = fields.Many2one('mrp.bom', 'BOM')
    final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')

class MaterialGopLabour(models.Model):
    _inherit = 'material.gop.labour'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods')
    bom_id = fields.Many2one('mrp.bom', 'BOM')
    final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')

class MaterialLabour(models.Model):
    _inherit = 'material.labour'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods')
    bom_id = fields.Many2one('mrp.bom', 'BOM')
    final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')

class MaterialGopOverhead(models.Model):
    _inherit = 'material.gop.overhead'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods')
    bom_id = fields.Many2one('mrp.bom', 'BOM')
    final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')

class MaterialOverhead(models.Model):
    _inherit = 'material.overhead'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods')
    bom_id = fields.Many2one('mrp.bom', 'BOM')
    final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')

class MaterialSubcon(models.Model):
    _inherit = 'material.subcon'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods')
    bom_id = fields.Many2one('mrp.bom', 'BOM')
    final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')

class InternalAsset(models.Model):
    _inherit = 'internal.asset'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods')
    bom_id = fields.Many2one('mrp.bom', 'BOM')
    final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')

class MaterialGopEquipment(models.Model):
    _inherit = 'material.gop.equipment'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods')
    bom_id = fields.Many2one('mrp.bom', 'BOM')
    final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')

class MaterialEquipment(models.Model):
    _inherit = 'material.equipment'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods')
    bom_id = fields.Many2one('mrp.bom', 'BOM')
    final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')
