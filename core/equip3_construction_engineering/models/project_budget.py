from odoo import api, fields, models, _
from datetime import datetime, date
from odoo.exceptions import ValidationError


class ProjectBudget(models.Model):
    _inherit = 'project.budget'

    is_engineering = fields.Boolean('Engineering', readonly=True, compute='onchange_project_enginerring')
    manufacture_line = fields.One2many('budget.manufacture.line','budget_id')

    amount_created_manuf = fields.Monetary(compute='_compute_amount_created_manuf',
                                                  string='Manuf Budget Created', readonly=True)
    amount_used_manuf = fields.Monetary(compute='_compute_amount_used_manuf', string='Manuf Budget Used',
                                           readonly=True)
    amount_left_manuf = fields.Monetary(compute='_compute_amount_left_manuf', string='Manuf Budget Left',
                                           readonly=True)
    amount_manuf = fields.Monetary(compute='_compute_amount_manuf', string='Manuf Cost', readonly=True)
    amount_unused_manuf = fields.Monetary(compute='_compute_unused_manuf', string='Manuf Unused',
                                             readonly=True)

    @api.onchange('project_id')
    def onchange_project_enginerring(self):
        if self.project_id:
            self.is_engineering = False
            if self.project_id.construction_type == 'engineering':
                self.is_engineering = True

    # Manuf method
    @api.depends('manufacture_line.amt_created')
    def _compute_amount_created_manuf(self):
        for sheet in self:
            amount_manuf_created = 0.0
            for line in sheet.manufacture_line:
                amount_manuf_created += line.amt_created
            sheet.update({'amount_created_manuf': amount_manuf_created})

    @api.depends('manufacture_line.amt_left')
    def _compute_amount_left_manuf(self):
        for sheet in self:
            amount_manuf_left = 0.0
            for line in sheet.manufacture_line:
                amount_manuf_left += line.amt_left
            sheet.update({'amount_left_manuf': amount_manuf_left})

    @api.depends('manufacture_line.amount_total')
    def _compute_amount_manuf(self):
        for sheet in self:
            amount_manuf = 0.0
            for line in sheet.manufacture_line:
                amount_manuf += line.amount_total
            sheet.update({'amount_manuf': amount_manuf})

    @api.depends('manufacture_line.amt_used')
    def _compute_amount_used_manuf(self):
        for sheet in self:
            amount_manuf_used = 0.0
            for line in sheet.manufacture_line:
                amount_manuf_used += line.amt_used
            sheet.update({'amount_used_manuf': amount_manuf_used})

    @api.depends('manufacture_line.unused_amt')
    def _compute_unused_manuf(self):
        for sheet in self:
            amount_unused_manuf = 0.0
            for line in sheet.manufacture_line:
                amount_unused_manuf += line.unused_amt
            sheet.update({'amount_unused_manuf': amount_unused_manuf})

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


class BudgetManufactureLine(models.Model):
    _name = 'budget.manufacture.line'
    _description = 'Budget Manufacture Line'

    budget_id = fields.Many2one('project.budget', string='Budget')
    cs_manuf_id = fields.Many2one('cost.manufacture.line', 'Manuf ID')
    budget_carry_over_id = fields.Many2one('project.budget.carry', string="Budget Carry Over")
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date", default=date.today())
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable = fields.Many2one('variable.template', string='Variable')
    finish_good_id = fields.Many2one('product.product', 'Finished Goods', required=True)
    bom_id = fields.Many2one('mrp.bom', 'BOM', required=True)
    quantity = fields.Float(string="Budget Quantity", default=1)
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    amount = fields.Float(string="Unit Price", default=0.00)
    amount_total = fields.Float(string="Budget Amount", compute="_amount_total_comute")
    amt_left = fields.Float(string='Budget Amount Left', compute="_budget_amount_left")
    amt_created = fields.Float(string='Manufactured Amount')
    amt_used = fields.Float('Actual Used Amount', default=0.00)
    qty_left = fields.Float(string='Budget Quantity Left', compute="_budget_quantity_left")
    qty_created = fields.Float(string='Finished Quantity')
    qty_used = fields.Float('Actual Used Quantity', default=0.00)
    budget_quantity = fields.Float(string="Sheet Budget Quantity")
    unallocated_quantity = fields.Float(string="Unallocated Budget Quantity")
    unused_qty = fields.Float('Unused Quantity', default=0.00, compute="_unused_qty")
    unused_amt = fields.Float('Unused Amount', default=0.00, compute="_unused_amt")
    dif_qty_used = fields.Float('Actual Used Quantity on different budget', default=0.00)
    dif_amt_used = fields.Float('Actual Used Amount on different budget', default=0.00)
    budget_amount = fields.Float(string="Sheet Budget Amount")
    unallocated_amount = fields.Float(string="Unallocated Budget Amount")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    rejected_qty = fields.Float(string='Rejected Quantity', default=0.00)
    manuf_create_qty = fields.Float(string='Manufactured Quantity', default=0.00)

    # on_hand_qty = fields.Float(string='On Hand Quantity', related='product_id.qty_available')
    # Carry Over
    status = fields.Selection([('carry_to', ' Carried to'),
                               ('carry_from', 'Carried From'),
                               ('carried_over', 'Carried Over')],
                              string="Status")
    carried_to = fields.Many2one('project.budget', string='Carried To')
    carried_from = fields.Many2one('project.budget', string='Carried From')
    carried_over = fields.Boolean(string='Carried Over')
    project_id = fields.Many2one(related='budget_id.project_id', string='Project')
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

    @api.depends('budget_id.manufacture_line', 'budget_id.manufacture_line.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.budget_id.manufacture_line:
                no += 1
                l.sr_no = no

    @api.onchange('quantity')
    def _amount_total_comute(self):
        for line in self:
            line.amount_total = line.quantity * line.amount

    @api.onchange('quantity', 'qty_created')
    def _budget_quantity_left(self):
        for line in self:
            line.qty_left = line.quantity - (line.qty_created)

    @api.onchange('amount_total', 'amt_created')
    def _budget_amount_left(self):
        for line in self:
            line.amt_left = line.amount_total - (line.amt_created)

    def _unused_qty(self):
        for line in self:
            line.unused_qty = line.quantity - line.qty_used - line.dif_qty_used

    def _unused_amt(self):
        for line in self:
            line.unused_amt = line.amount_total - line.amt_used - line.dif_amt_used


class BudgetMaterials(models.Model):
    _inherit = 'budget.material'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods')

class BudgetLabour(models.Model):
    _inherit = 'budget.labour'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods')

# class BudgetSubcon(models.Model):
#     _inherit = 'budget.subcon'

class BudgetOverhead(models.Model):
    _inherit = 'budget.overhead'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods')

class BudgetInternalAsset(models.Model):
    _inherit = 'budget.internal.asset'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods')

class BudgetEquipment(models.Model):
    _inherit = 'budget.equipment'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods')

class BudgetGopMaterial(models.Model):
    _inherit = 'budget.gop.material'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods')

class BudgetGopLabour(models.Model):
    _inherit = 'budget.gop.labour'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods')

class BudgetGopOverhead(models.Model):
    _inherit = 'budget.gop.overhead'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods')

class BudgetGopequipment(models.Model):
    _inherit = 'budget.gop.equipment'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods')
