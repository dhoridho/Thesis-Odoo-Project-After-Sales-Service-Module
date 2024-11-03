from datetime import datetime
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _


class StockScrapRequestInherit(models.Model):
    _inherit = 'stock.scrap.request'
    _description = "Product Usage"

    project = fields.Many2one ('project.project', string="Project", domain="[('primary_states','=', 'progress')]")
    contract = fields.Many2one('sale.order.const', string="Contract", domain="[('project_id','=', project)]")
    cost_sheet = fields.Many2one('job.cost.sheet', string='Cost Sheet', force_save="1")
    project_budget = fields.Many2one('project.budget', string='Periodical Budget', domain="[('project_id','=', project),('state','=', 'in_progress')]")
    budgeting_method = fields.Selection(related='project.budgeting_method', string='Budgeting Method')
    budgeting_period = fields.Selection(related='project.budgeting_period', string='Budgeting Period')
    actualization_project_budget = fields.Many2one('project.budget', string='Actualization Periodical Budget', domain="[('project_id','=', project)]")
    work_orders = fields.Many2one('project.task', string='Job Order', domain="[('project_id','=', project),('state','=', 'inprogress')]")
    material_type = fields.Selection([('material','Material'), ('overhead','Overhead'),('equipment','Equipment')],string = "Material Type")
    department_type = fields.Selection(related='project.department_type', string='Type of Project')
    job_estimate = fields.Many2one('job.estimate', string="BOQ", domain="[('project_id','=', project)]")
    project_scope_computed = fields.Many2many('project.scope.line', string="computed scope lines",
                                              compute='get_scope_lines')
    progress_id = fields.Many2one('progress.history', string="Progress", domain="[('work_order','=', work_orders)]")

    @api.onchange('project')
    def _onchange_project(self):
        if self.project:
            cost_sheet = self.env['job.cost.sheet'].search([('project_id', '=', self.project.id), ('state', '=', 'in_progress')],limit=1)
            if cost_sheet:
                for proj in self.project:
                    self.cost_sheet = cost_sheet.id
                    self.analytic_tag_ids = [(6, 0, [v.id for v in proj.analytic_idz])]
                    self.warehouse_id = proj.warehouse_address.id
            else:
                raise ValidationError(_("Please set the the cost sheet of this project to 'In Progress' first before input the product usage"))

    def _get_project_budget(self, date):
        for rec in self:
            Job_cost_sheet = rec.cost_sheet
            if date:
                schedule = datetime.strptime(str(date.date()), "%Y-%m-%d")
                month_date = schedule.strftime("%B")
                if rec.project.budgeting_period == 'monthly':
                    data = rec.env['budget.period.line'].search([('month', '=', month_date),
                                                                ('line_project_ids', '=', Job_cost_sheet.project_id.id)], limit=1)
                    budget = rec.env['project.budget'].search([('project_id', '=', Job_cost_sheet.project_id.id),
                                                                ('cost_sheet', '=', Job_cost_sheet.id),
                                                                ('month', '=', data.id)], limit=1)
                    return budget
                elif rec.project.budgeting_period == 'custom':
                    budget = rec.env['project.budget'].search([('project_id', '=', Job_cost_sheet.project_id.id),
                                                                ('cost_sheet', '=', Job_cost_sheet.id),
                                                                ('bd_start_date', '<=', date),
                                                                ('bd_end_date', '>=', date)], limit=1)
                    return budget
                else:
                    pass

    # get from project budget
    def get_bd_material(self, line):
        standard_price = line.product_id.standard_price
        self.env.cr.execute(
            """SELECT standard_price FROM product_warehouse_price WHERE warehouse_id = %s and product_id = %s""" % (
                self.warehouse_id.id, line.product_id.id))
        if self.env.cr.rowcount > 0:
            standard_price = self.env.cr.fetchone()[0]

        return {
            'project_scope': line.project_scope.id,
            'section': line.section_name.id,
            'variable': line.variable.id,
            'group_of_product': line.group_of_product.id,
            'product_id': line.product_id.id,
            'budget_qty': line.unused_qty,
            'product_uom_id': line.uom_id.id,
            'on_hand_qty_converted': line.on_hand_qty_converted,
            'sale_price': standard_price,
        }

    def get_bd_labour(self, line):
        return {
            'project_scope': line.project_scope.id,
            'section': line.section_name.id,
            'variable': line.variable.id,
            'group_of_product': line.group_of_product.id,
            'product_id': line.product_id.id,
            'budget_qty': line.unused_qty,
            'product_uom_id': line.uom_id.id,
            'on_hand_qty_converted': line.on_hand_qty_converted,
        }

    def get_bd_overhead(self, line):
        standard_price = line.product_id.standard_price
        self.env.cr.execute(
            """SELECT standard_price FROM product_warehouse_price WHERE warehouse_id = %s and product_id = %s""" % (
                self.warehouse_id.id, line.product_id.id))
        if self.env.cr.rowcount > 0:
            standard_price = self.env.cr.fetchone()[0]

        return {
            'project_scope': line.project_scope.id,
            'section': line.section_name.id,
            'variable': line.variable.id,
            'group_of_product': line.group_of_product.id,
            'product_id': line.product_id.id,
            'budget_qty': line.unused_qty,
            'product_uom_id': line.uom_id.id,
            'on_hand_qty_converted': line.on_hand_qty_converted,
            'sale_price': standard_price,
        }

    def get_bd_equipment(self, line):
        standard_price = line.product_id.standard_price
        self.env.cr.execute(
            """SELECT standard_price FROM product_warehouse_price WHERE warehouse_id = %s and product_id = %s""" % (
                self.warehouse_id.id, line.product_id.id))
        if self.env.cr.rowcount > 0:
            standard_price = self.env.cr.fetchone()[0]

        return {
            'project_scope': line.project_scope.id,
            'section': line.section_name.id,
            'variable': line.variable.id,
            'group_of_product': line.group_of_product.id,
            'product_id': line.product_id.id,
            'budget_qty': line.unused_qty,
            'product_uom_id': line.uom_id.id,
            'sale_price': standard_price,
        }

    # get from cost sheet
    def get_cs_material(self, line):
        standard_price = line.product_id.standard_price
        self.env.cr.execute(
            """SELECT standard_price FROM product_warehouse_price WHERE warehouse_id = %s and product_id = %s""" % (
                self.warehouse_id.id, line.product_id.id))
        if self.env.cr.rowcount > 0:
            standard_price = self.env.cr.fetchone()[0]

        return {
            'project_scope': line.project_scope.id,
            'section': line.section_name.id,
            'variable': line.variable_ref.id,
            'group_of_product': line.group_of_product.id,
            'product_id': line.product_id.id,
            'budget_qty': line.unused_qty,
            'product_uom_id': line.uom_id.id,
            'on_hand_qty_converted': line.on_hand_qty_converted,
            'sale_price': standard_price,
        }

    def get_cs_labour(self, line):
        return {
            'project_scope': line.project_scope.id,
            'section': line.section_name.id,
            'variable': line.variable_ref.id,
            'group_of_product': line.group_of_product.id,
            'product_id': line.product_id.id,
            'budget_qty': line.unused_qty,
            'product_uom_id': line.uom_id.id,
            'on_hand_qty_converted': line.on_hand_qty_converted,
        }

    def get_cs_overhead(self, line):
        standard_price = line.product_id.standard_price
        self.env.cr.execute(
            """SELECT standard_price FROM product_warehouse_price WHERE warehouse_id = %s and product_id = %s""" % (
                self.warehouse_id.id, line.product_id.id))
        if self.env.cr.rowcount > 0:
            standard_price = self.env.cr.fetchone()[0]

        return {
            'project_scope': line.project_scope.id,
            'section': line.section_name.id,
            'variable': line.variable_ref.id,
            'group_of_product': line.group_of_product.id,
            'product_id': line.product_id.id,
            'budget_qty': line.unused_qty,
            'product_uom_id': line.uom_id.id,
            'on_hand_qty_converted': line.on_hand_qty_converted,
            'sale_price': standard_price,
        }

    def get_cs_equipment(self, line):
        standard_price = line.product_id.standard_price
        self.env.cr.execute(
            """SELECT standard_price FROM product_warehouse_price WHERE warehouse_id = %s and product_id = %s""" % (
                self.warehouse_id.id, line.product_id.id))
        if self.env.cr.rowcount > 0:
            standard_price = self.env.cr.fetchone()[0]
        return {
            'project_scope': line.project_scope.id,
            'section': line.section_name.id,
            'variable': line.variable_ref.id,
            'group_of_product': line.group_of_product.id,
            'product_id': line.product_id.id,
            'budget_qty': line.unused_qty,
            'product_uom_id': line.uom_id.id,
            'sale_price': standard_price,
        }

    @api.onchange('budgeting_method', 'cost_sheet', 'project_budget', 'material_type')
    def _get_product_line(self):
        self.scrap_ids = [(5, 0, 0)]
        for rec in self:
            if rec.material_type == 'material':
                if rec.project_budget:
                    for line in rec.project_budget.budget_material_ids.filtered(lambda b: b.on_hand_qty_converted > 0):
                        rec.scrap_ids = [(0, 0, rec.get_bd_material(line))]
                else:
                    for line in rec.cost_sheet.material_ids.filtered(lambda b: b.on_hand_qty_converted > 0):
                        rec.scrap_ids = [(0, 0, rec.get_cs_material(line))]
            # if rec.material_type == 'labour':
            #     if rec.project_budget:
            #         for line in rec.project_budget.budget_labour_ids.filtered(lambda b: b.on_hand_qty_converted > 0):
            #             rec.scrap_ids = [(0, 0, rec.get_bd_labour(line))]
            #     else:
            #         for line in rec.cost_sheet.material_labour_ids.filtered(lambda b: b.on_hand_qty_converted > 0):
            #             rec.scrap_ids = [(0, 0, rec.get_cs_labour(line))]
            if rec.material_type == 'overhead':
                if rec.project_budget:
                    for line in rec.project_budget.budget_overhead_ids.filtered(lambda b: b.overhead_catagory in ('product') and b.on_hand_qty_converted > 0):
                        rec.scrap_ids = [(0, 0, rec.get_bd_overhead(line))]
                else:
                    for line in rec.cost_sheet.material_overhead_ids.filtered(lambda b: b.overhead_catagory in ('product') and b.on_hand_qty_converted > 0):
                        rec.scrap_ids = [(0, 0, rec.get_cs_overhead(line))]
            if rec.material_type == 'equipment':
                if rec.project_budget:
                    for line in rec.project_budget.budget_equipment_ids:
                        rec.scrap_ids = [(0, 0, rec.get_bd_equipment(line))]
                else:
                    for line in rec.cost_sheet.material_equipment_ids:
                        rec.scrap_ids = [(0, 0, rec.get_cs_equipment(line))]

            for line in self.scrap_ids:
                line._onchange_product_reference()
                line.update({'location_id': self.warehouse_id.lot_stock_id.id})
                line._onchange_location_and_product_id()

    def update_budget_gop_value(self, value_bud):
        return {
            'amt_used': value_bud,
        }

    def update_cost_gop_value(self, value_cs):
        return {
            'actual_used_amt': value_cs,
        }

    def update_dif_budget_gop_value(self, dif_value_bud):
        return {
            'dif_amt_used': dif_value_bud,
        }

    def create_material_budget_gop_value(self, line, amount):
        return {
            'cs_material_gop_id': line.cs_material_gop_id.id,
            'project_scope': line.project_scope.id,
            'section_name': line.section.id,
            'variable': line.variable.id,
            'group_of_product': line.group_of_product.id,
            'amt_used': amount,
        }

    def send_line_gop_budget(self, budget):
        return {'budget_material_gop_ids' : budget}

    def update_material_gop_bd(self, budget, line, amount):
        if self.project_budget == self.actualization_project_budget:
            value_bud = line.bd_material_gop_id.amt_used + amount
            for sub in self.project_budget:
                sub.budget_material_gop_ids = [(1, line.bd_material_gop_id.id, self.update_budget_gop_value(value_bud))]
        else:
            same_material = self.env['budget.gop.material'].search([('budget_id', '=', line.scrap_id.actualization_project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id)])
            value_bud = same_material.amt_used + amount
            dif_value_bud = line.bd_material_gop_id.amt_used + amount
            if same_material:
                for sub in self.actualization_project_budget:
                    sub.budget_material_gop_ids = [(1, same_material.id, self.update_budget_gop_value(value_bud))]
            else:
                for sub in self.actualization_project_budget:
                    budget.append((0, 0, self.create_material_budget_gop_value(line, amount)))
                    sub.write(self.send_line_budget(budget))
                for bd in self.project_budget:
                    bd.budget_material_gop_ids = [(1, line.bd_material_gop_id.id, self.update_dif_budget_gop_value(dif_value_bud))]

    def update_labour_gop_bd(self, budget, line, amount):
        if self.project_budget == self.actualization_project_budget:
            value_bud = line.bd_labour_gop_id.amt_used + amount
            for sub in self.project_budget:
                sub.budget_labour_gop_ids = [(1, line.bd_labour_gop_id.id, self.update_budget_gop_value(value_bud))]
        else:
            same_material = self.env['budget.gop.labour'].search([('budget_id', '=', line.scrap_id.actualization_project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id)])
            value_bud = same_material.amt_used + amount
            dif_value_bud = line.bd_labour_gop_id.amt_used + amount
            if same_material:
                for sub in self.actualization_project_budget:
                    sub.budget_labour_gop_ids = [(1, same_material.id, self.update_budget_gop_value(value_bud))]
            else:
                for sub in self.actualization_project_budget:
                    budget.append((0, 0, self.create_material_budget_gop_value(line, amount)))
                    sub.write(self.send_line_budget(budget))
                for bd in self.project_budget:
                    bd.budget_labour_gop_ids = [(1, line.bd_labour_gop_id.id, self.update_dif_budget_gop_value(dif_value_bud))]

    def update_overhead_gop_bd(self, budget, line, amount):
        if self.project_budget == self.actualization_project_budget:
            value_bud = line.bd_overhead_gop_id.amt_used + amount
            for sub in self.project_budget:
                sub.budget_overhead_gop_ids = [(1, line.bd_overhead_gop_id.id, self.update_budget_gop_value(value_bud))]
        else:
            same_material = self.env['budget.gop.labour'].search([('budget_id', '=', line.scrap_id.actualization_project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id)])
            value_bud = same_material.amt_used + amount
            dif_value_bud = line.bd_overhead_gop_id.amt_used + amount
            if same_material:
                for sub in self.actualization_project_budget:
                    sub.budget_overhead_gop_ids = [(1, same_material.id, self.update_budget_gop_value(value_bud))]
            else:
                for sub in self.actualization_project_budget:
                    budget.append((0, 0, self.create_material_budget_gop_value(line, amount)))
                    sub.write(self.send_line_budget(budget))
                for bd in self.project_budget:
                    bd.budget_overhead_gop_ids = [(1, line.bd_overhead_gop_id.id, self.update_dif_budget_gop_value(dif_value_bud))]

    def update_material_gop_cs(self, line, amount):
        value_cs = line.cs_material_gop_id.actual_used_amt + amount
        for cs in self.cost_sheet:
            cs.material_gop_ids = [(1, line.cs_material_gop_id.id, self.update_cost_gop_value(value_cs))]

    def update_labour_gop_cs(self, line, amount):
        value_cs = line.cs_labour_gop_id.actual_used_amt + amount
        for cs in self.cost_sheet:
            cs.labour_gop_ids = [(1, line.cs_labour_gop_id.id, self.update_cost_gop_value(value_cs))]

    def update_overhead_gop_cs(self, line, amount):
        value_cs = line.cs_overhead_gop_id.actual_used_amt + amount
        for cs in self.cost_sheet:
            cs.overhead_gop_ids = [(1, line.cs_overhead_gop_id.id, self.update_cost_gop_value(value_cs))]

    def update_budget_value(self, reserved_bud, value_bud):
        return {
            'qty_used': reserved_bud,
            'amt_used': value_bud,
        }

    def update_cost_value(self, reserved_cs, value_cs):
        return {
            'actual_used_qty': reserved_cs,
            'actual_used_amt': value_cs,
        }

    def update_dif_budget_value(self, dif_reserved_bud, dif_value_bud):
        return {
            'dif_qty_used': dif_reserved_bud,
            'dif_amt_used': dif_value_bud,
        }

    def create_material_budget_value(self, line, amount):
        scrap_qty = line.product_uom_id._compute_quantity(line.scrap_qty, line.product_id.uom_id)
        return {
            'cs_material_id': line.cs_material_id.id,
            'project_scope': line.project_scope.id,
            'section_name': line.section.id,
            'variable': line.variable.id,
            'group_of_product': line.group_of_product.id,
            'product_id': line.product_id.id,
            'quantity': 0,
            'qty_used': scrap_qty,
            'amt_used': amount,
        }

    def create_labour_budget_value(self, line, amount):
        scrap_qty = line.product_uom_id._compute_quantity(line.scrap_qty, line.product_id.uom_id)
        return {
            'cs_labour_id': line.cs_labour_id.id,
            'project_scope': line.project_scope.id,
            'section_name': line.section.id,
            'variable': line.variable.id,
            'group_of_product': line.group_of_product.id,
            'product_id': line.product_id.id,
            'quantity': 0,
            'qty_used': scrap_qty,
            'amt_used': amount,
        }

    def create_overhead_budget_value(self, line, amount):
        scrap_qty = line.product_uom_id._compute_quantity(line.scrap_qty, line.product_id.uom_id)
        return {
            'cs_overhead_id': line.cs_overhead_id.id,
            'project_scope': line.project_scope.id,
            'section_name': line.section.id,
            'variable': line.variable.id,
            'group_of_product': line.group_of_product.id,
            'product_id': line.product_id.id,
            'quantity': 0,
            'qty_used': scrap_qty,
            'amt_used': amount,
        }

    def send_line_budget(self, budget):
        return {'budget_material_ids' : budget}

    def update_material_bd(self, budget, line, amount):
        scrap_qty = line.product_uom_id._compute_quantity(line.scrap_qty, line.product_id.uom_id)
        if self.project_budget == self.actualization_project_budget:
            reserved_bud = line.bd_material_id.qty_used + scrap_qty
            value_bud = line.bd_material_id.amt_used + amount
            for sub in self.project_budget:
                sub.budget_material_ids = [(1, line.bd_material_id.id, self.update_budget_value(reserved_bud, value_bud))]
        else:
            same_material = self.env['budget.material'].search([('budget_id', '=', line.scrap_id.actualization_project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id),('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
            reserved_bud = same_material.qty_used + scrap_qty
            value_bud = same_material.amt_used + amount
            dif_reserved_bud = line.bd_material_id.qty_used + scrap_qty
            dif_value_bud = line.bd_material_id.amt_used + amount
            if same_material:
                for sub in self.actualization_project_budget:
                    sub.budget_material_ids = [(1, same_material.id, self.update_budget_value(reserved_bud, value_bud))]
            else:
                for sub in self.actualization_project_budget:
                    budget.append((0, 0, self.create_material_budget_value(line, amount)))
                    sub.write(self.send_line_budget(budget))
                for bd in self.project_budget:
                    bd.budget_material_ids = [(1, line.bd_material_id.id, self.update_dif_budget_value(dif_reserved_bud, dif_value_bud))]


    def update_material_cs(self, line, amount):
        scrap_qty = line.product_uom_id._compute_quantity(line.scrap_qty, line.product_id.uom_id)
        reserved_cs = line.cs_material_id.actual_used_qty + scrap_qty
        value_cs = line.cs_material_id.actual_used_amt + amount
        for cs in self.cost_sheet:
            cs.material_ids = [(1, line.cs_material_id.id, self.update_cost_value(reserved_cs, value_cs))]

    def update_labour_bd(self, budget, line, amount):
        scrap_qty = line.product_uom_id._compute_quantity(line.scrap_qty, line.product_id.uom_id)
        if self.project_budget == self.actualization_project_budget:
            reserved_bud = line.bd_labour_id.qty_used + scrap_qty
            value_bud = line.bd_labour_id.amt_used + amount
            for sub in self.project_budget:
                sub.budget_labour_ids = [(1, line.bd_labour_id.id, self.update_budget_value(reserved_bud, value_bud))]
        else:
            same_labour = self.env['budget.labour'].search([('budget_id', '=', line.scrap_id.actualization_project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
            reserved_bud = same_labour.qty_used + scrap_qty
            value_bud = same_labour.amt_used + amount
            dif_reserved_bud = line.bd_labour_id.qty_used + scrap_qty
            dif_value_bud = line.bd_labour_id.amt_used + amount
            if same_labour:
                for sub in self.actualization_project_budget:
                    sub.budget_labour_ids = [(1, same_labour.id, self.update_budget_value(reserved_bud, value_bud))]
            else:
                for sub in self.actualization_project_budget:
                    budget.append((0, 0, self.create_labour_budget_value(line, amount)))
                    sub.budget_labour_ids.write(self.send_line_budget(budget))
                for bd in self.project_budget:
                    bd.budget_labour_ids = [(1, line.bd_labour_id.id, self.update_dif_budget_value(dif_reserved_bud, dif_value_bud))]

    def update_labour_cs(self, line, amount):
        scrap_qty = line.product_uom_id._compute_quantity(line.scrap_qty, line.product_id.uom_id)
        reserved_cs = line.cs_labour_id.actual_used_qty + scrap_qty
        value_cs = line.cs_labour_id.actual_used_amt + amount
        for cs in self.cost_sheet:
            cs.material_labour_ids = [(1, line.cs_labour_id.id, self.update_cost_value(reserved_cs, value_cs))]

    def update_overhead_bd(self, budget, line, amount):
        scrap_qty = line.product_uom_id._compute_quantity(line.scrap_qty, line.product_id.uom_id)
        if self.project_budget == self.actualization_project_budget:
            reserved_bud = line.bd_overhead_id.qty_used + scrap_qty
            value_bud = line.bd_overhead_id.amt_used + amount
            for sub in self.project_budget:
                sub.budget_overhead_ids = [(1, line.bd_overhead_id.id, self.update_budget_value(reserved_bud, value_bud))]
        else:
            same_overhead = self.env['budget.overhead'].search([('budget_id', '=', line.scrap_id.actualization_project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
            reserved_bud = same_overhead.qty_used + scrap_qty
            value_bud = same_overhead.amt_used + amount
            dif_reserved_bud = line.bd_overhead_id.qty_used + scrap_qty
            dif_value_bud = line.bd_overhead_id.amt_used + amount
            if same_overhead:
                for sub in self.actualization_project_budget:
                    sub.budget_overhead_ids = [(1, same_overhead.id, self.update_budget_value(reserved_bud, value_bud))]
            else:
                for sub in self.actualization_project_budget:
                    budget.append((0, 0, self.create_overhead_budget_value(line, amount)))
                    sub.budget_overhead_ids.write(self.send_line_budget(budget))
                for bd in self.project_budget:
                    bd.budget_overhead_ids = [(1, line.bd_overhead_id.id, self.update_dif_budget_value(dif_reserved_bud, dif_value_bud))]

    def update_overhead_cs(self, line, amount):
        scrap_qty = line.product_uom_id._compute_quantity(line.scrap_qty, line.product_id.uom_id)
        reserved_cs = line.cs_overhead_id.actual_used_qty + scrap_qty
        value_cs = line.cs_overhead_id.actual_used_amt + amount
        for cs in self.cost_sheet:
            cs.material_overhead_ids = [(1, line.cs_overhead_id.id, self.update_cost_value(reserved_cs, value_cs))]

    def send_consumed_data(self, line):
        scrap_qty = line.product_uom_id._compute_quantity(line.scrap_qty, line.product_id.uom_id)
        return {'usage_id': self.id,
                'date_used': self.schedule_date,
                'group_of_product': line.group_of_product.id,
                'product_id': line.product_id.id,
                'quantity': scrap_qty,
                'state': 'validated',
                }

    def send_product_data(self, line):
        scrap_qty = line.product_uom_id._compute_quantity(line.scrap_qty, line.product_id.uom_id)
        return {'project_scope': line.project_scope.id,
                'section_name': line.section.id,
                'group_of_product': line.group_of_product.id,
                'product_id': line.product_id.id,
                'quantity': scrap_qty,
                'uom_id': line.product_uom_id.id,
                }

    def send_material_consumed_history(self, consumed):
        return {'consumed_material_history_ids' : consumed,
                }

    def send_material_consumed_line_history(self, consumed, product):
        return {'consumed_material_ids': product,
                'consumed_material_history_ids' : consumed,
                }

    def send_labour_consumed_history(self, consumed):
        return {'consumed_labour_history_ids' : consumed,
                }

    def send_labour_consumed_line_history(self, consumed, product):
        return {'consumed_labour_ids': product,
                'consumed_labour_history_ids' : consumed,
                }

    def send_overhead_consumed_history(self, consumed):
        return {'consumed_overhead_history_ids' : consumed,
                }

    def send_overhead_consumed_line_history(self, consumed, product):
        return {'consumed_overhead_ids': product,
                'consumed_overhead_history_ids' : consumed,
                }

    def update_consumed_qty(self, cal_qty):
        return {
            'quantity': cal_qty,
        }

    def update_consumed_material(self, line):
        consumed = [(0, 0, self.send_consumed_data(line))]
        if line.con_material_id:
            cal_qty = 0.00
            scrap_qty = line.product_uom_id._compute_quantity(line.scrap_qty, line.product_id.uom_id)
            cal_qty = (line.con_material_id.quantity + scrap_qty)
            self.work_orders.consumed_material_ids = [(1, line.con_material_id.id, self.update_consumed_qty(cal_qty))]
            self.work_orders.write(self.send_material_consumed_history(consumed))
        else:
            product = [(0, 0, self.send_product_data(line))]
            self.work_orders.write(self.send_material_consumed_line_history(consumed, product))

    def update_consumed_labour(self, line):
        consumed = [(0, 0, self.send_consumed_data(line))]
        if line.con_labour_id:
            cal_qty = 0.00
            scrap_qty = line.product_uom_id._compute_quantity(line.scrap_qty, line.product_id.uom_id)
            cal_qty = (line.con_labour_id.quantity + scrap_qty)
            self.work_orders.consumed_labour_ids = [(1, line.con_labour_id.id, self.update_consumed_qty(cal_qty))]
            self.work_orders.write(self.send_labour_consumed_history(consumed))
        else:
            product = [(0, 0, self.send_product_data(line))]
            self.work_orders.write(self.send_labour_consumed_line_history(consumed, product))

    def update_consumed_overhead(self, line):
        consumed = [(0, 0, self.send_consumed_data(line))]
        if line.con_overhead_id:
            cal_qty = 0.00
            scrap_qty = line.product_uom_id._compute_quantity(line.scrap_qty, line.product_id.uom_id)
            cal_qty = (line.con_overhead_id.quantity + scrap_qty)
            self.work_orders.consumed_overhead_ids = [(1, line.con_overhead_id.id, self.update_consumed_qty(cal_qty))]
            self.work_orders.write(self.send_overhead_consumed_history(consumed))
        else:
            product = [(0, 0, self.send_product_data(line))]
            self.work_orders.write(self.send_overhead_consumed_line_history(consumed, product))

    # def _check_on_hand(self, line):
    #     on_hand = 0 
    #     if line.product_id and line.location_id:
    #         location = self.env['stock.quant'].search([('location_id', '=', line.location_id.id), ('product_id', '=', line.product_id.id)])
    #         for loc in location:
    #             on_hand += loc.available_quantity

    #     if line.scrap_qty > on_hand:
    #         raise ValidationError(_("There is not enough stock for '{}' in the location '{}'.\n(Available quantity = {})".format(line.product_id.name , line.location_id.display_name, on_hand)))

    def update_gop_values(self, type):
        for rec in self:
            if type == 'material':
                rec.cost_sheet.get_gop_material_table()
                if rec.project_budget:
                    rec.project_budget.get_gop_material_table()
            if type == 'overhead':
                rec.cost_sheet.get_gop_overhead_table()
                if rec.project_budget:
                    rec.project_budget.get_gop_overhead_table()

    def action_request_validated(self):
        res = super(StockScrapRequestInherit, self).action_request_validated()
        # consumed = []
        # product = []
        budget = []
        on_hand = 0
        amount = 0
        scrap_qty = 0
        for line in self.scrap_ids:
            location = self.env['stock.quant'].search([('location_id', '=', line.location_id.id), ('product_id', '=', line.product_id.id)])
            for loc in location:
                on_hand += loc.available_quantity

            scrap_qty = line.product_uom_id._compute_quantity(line.scrap_qty, line.product_id.uom_id)
            standard_price = line.product_id.standard_price
            self.env.cr.execute("""SELECT standard_price FROM product_warehouse_price WHERE warehouse_id = %s and product_id = %s""" % (line.warehouse_id.id, line.product_id.id))
            if self.env.cr.rowcount > 0:
                standard_price = self.env.cr.fetchone()[0]

            if scrap_qty > on_hand:
                raise ValidationError(_("There is not enough stock for '{}' in the location '{}'.\n(Available quantity = {})".format(line.product_id.name , line.location_id.display_name, on_hand)))

            if self.project:
                if self.cost_sheet.state == 'freeze':
                    raise ValidationError("The budget for this project is being freeze")
                else:
                    if self.material_type == 'material':
                        # if self.project_budget:
                        #     if line.bd_material_id.purchased_qty > 0:
                        #         unit_price = line.bd_material_id.purchased_amt / line.bd_material_id.purchased_qty
                        #     else:
                        #         unit_price = line.cs_material_id.price_unit
                        # else:
                        #     if line.cs_material_id.purchased_qty > 0:
                        #         unit_price = line.cs_material_id.purchased_amt / line.cs_material_id.purchased_qty
                        #     else:
                        #         unit_price = line.cs_material_id.price_unit
                        amount = standard_price * scrap_qty

                        if self.project_budget:
                            self.update_material_bd(budget, line, amount)

                        self.update_material_cs(line, amount)
                        self.update_consumed_material(line)
                        line.ch_material_id = self.env['consumed.material.history'].search([('consumed_id', '=', line.scrap_id.work_orders.id), ('usage_id', '=', self.id)])
                        if self.cost_sheet.budgeting_method == 'gop_budget':
                            self.update_gop_values('material')

                # if self.material_type == 'labour':
                #     unit_price = line.cs_labour_id.purchased_amt / line.cs_labour_id.purchased_qty
                #     amount = standard_price * scrap_qty
                #
                #     if self.project_budget:
                #         self.update_labour_bd(budget, line, amount)
                #
                #     self.update_labour_cs(line, amount)
                #     self.update_consumed_labour(line)
                #     line.ch_labour_id = self.env['consumed.labour.history'].search([('consumed_id', '=', line.scrap_id.work_orders.id), ('usage_id', '=', self.id)])

                if self.material_type == 'overhead':
                    amount = standard_price * scrap_qty

                    if self.project_budget:
                        self.update_overhead_bd(budget, line, amount)

                    self.update_overhead_cs(line, amount)
                    self.update_consumed_overhead(line)
                    line.ch_overhead_id = self.env['consumed.overhead.history'].search([('consumed_id', '=', line.scrap_id.work_orders.id), ('usage_id', '=', self.id)])

                    if self.cost_sheet.budgeting_method == 'gop_budget':
                        self.update_gop_values('overhead')

        return res

    def action_cancel(self):
        res = super(StockScrapRequestInherit, self).action_cancel()
        if self.cost_sheet.state == 'freeze':
            raise ValidationError("The budget for this project is being freeze")
        else:
            if self.state == 'validated':
                if self.material_type == 'material':
                    if self.project_budget:
                        for rec in self.scrap_ids:
                            reserved = 0.00
                            for bud in rec.bd_material_id:
                                reserved = (bud.qty_used - rec.scrap_qty)
                                for sub in self.project_budget:
                                    sub.budget_material_ids = [(1, rec.bd_material_id.id, {
                                            'qty_used': reserved,
                                        })]
                            for cs in rec.cs_material_id:
                                reserved = (cs.actual_used_qty - rec.scrap_qty)
                                for sheet in self.cost_sheet:
                                    sheet.material_ids = [(1, rec.cs_material_id.id, {
                                            'actual_used_qty': reserved,
                                        })]
                            cal_qty = 0.00
                            for con in rec.con_material_id:
                                cal_qty = (con.quantity - rec.scrap_qty)
                                if cal_qty == 0:
                                    self.work_orders.consumed_material_ids = [(2, rec.con_material_id.id, 0)]
                                else:
                                    self.work_orders.consumed_material_ids = [(1, rec.con_material_id.id, {
                                            'quantity': cal_qty,
                                        })]
                            self.work_orders.consumed_material_history_ids = [(1, rec.ch_material_id.id, {
                                'state': 'cancel',
                            })]

                    else:
                        for rec in self.scrap_ids:
                            reserved = 0.00
                            for cs in rec.cs_material_id:
                                    reserved = (cs.actual_used_qty - rec.scrap_qty)
                                    for sheet in self.cost_sheet:
                                        sheet.material_ids = [(1, rec.cs_material_id.id, {
                                                'actual_used_qty': reserved,
                                            })]
                            cal_qty = 0.00
                            for con in rec.con_material_id:
                                cal_qty = (con.quantity - rec.scrap_qty)
                                if cal_qty == 0:
                                    self.work_orders.consumed_material_ids = [(2, rec.con_material_id.id, 0)]
                                else:
                                    self.work_orders.consumed_material_ids = [(1, rec.con_material_id.id, {
                                            'quantity': cal_qty,
                                        })]
                            self.work_orders.consumed_material_history_ids = [(1, rec.ch_material_id.id, {
                                'state': 'cancel',
                            })]


                # if self.material_type == 'labour':
                #     if self.project_budget:
                #         for rec in self.scrap_ids:
                #             reserved = 0.00
                #             for bud in rec.bd_labour_id:
                #                 reserved = (bud.qty_used - rec.scrap_qty)
                #                 for sub in self.project_budget:
                #                     sub.budget_labour_ids = [(1, rec.bd_labour_id.id, {
                #                             'qty_used': reserved,
                #                         })]
                #             for cs in rec.cs_labour_id:
                #                 reserved = (cs.actual_used_qty - rec.scrap_qty)
                #                 for sheet in self.cost_sheet:
                #                     sheet.material_labour_ids = [(1, rec.cs_labour_id.id, {
                #                             'actual_used_qty': reserved,
                #                         })]
                #             cal_qty = 0.00
                #             for con in rec.con_labour_id:
                #                 cal_qty = (con.quantity - rec.scrap_qty)
                #                 if cal_qty == 0:
                #                     self.work_orders.consumed_labour_ids = [(2, rec.con_labour_id.id, 0)]
                #                 else:
                #                     self.work_orders.consumed_labour_ids = [(1, rec.con_labour_id.id, {
                #                             'quantity': cal_qty,
                #                         })]
                #             self.work_orders.consumed_labour_history_ids = [(1, rec.ch_labour_id.id, {
                #                 'state': 'cancel',
                #             })]
                #     else:
                #         for rec in self.scrap_ids:
                #             reserved = 0.00
                #             for cs in rec.cs_labour_id:
                #                 reserved = (cs.actual_used_qty - rec.scrap_qty)
                #                 for sheet in self.cost_sheet:
                #                     sheet.material_labour_ids = [(1, rec.cs_labour_id.id, {
                #                             'actual_used_qty': reserved,
                #                         })]
                #             cal_qty = 0.00
                #             for con in rec.con_labour_id:
                #                 cal_qty = (con.quantity - rec.scrap_qty)
                #                 if cal_qty == 0:
                #                     self.work_orders.consumed_labour_ids = [(2, rec.con_labour_id.id, 0)]
                #                 else:
                #                     self.work_orders.consumed_labour_ids = [(1, rec.con_labour_id.id, {
                #                             'quantity': cal_qty,
                #                         })]
                #             self.work_orders.consumed_labour_history_ids = [(1, rec.ch_labour_id.id, {
                #                 'state': 'cancel',
                #             })]


                if self.material_type == 'overhead':
                    if self.project_budget:
                        for rec in self.scrap_ids:
                            reserved = 0.00
                            for bud in rec.bd_overhead_id:
                                reserved = (bud.qty_used - rec.scrap_qty)
                                for sub in self.project_budget:
                                    sub.budget_overhead_ids = [(1, rec.bd_overhead_id.id, {
                                            'qty_used': reserved,
                                        })]
                            for cs in rec.cs_overhead_id:
                                reserved = (cs.actual_used_qty - rec.scrap_qty)
                                for sheet in self.cost_sheet:
                                    sheet.material_overhead_ids = [(1, rec.cs_overhead_id.id, {
                                            'actual_used_qty': reserved,
                                        })]
                            cal_qty = 0.00
                            for con in rec.con_overhead_id:
                                cal_qty = (con.quantity - rec.scrap_qty)
                                if cal_qty == 0:
                                    self.work_orders.consumed_overhead_ids = [(2, rec.con_overhead_id.id, 0)]
                                else:
                                    self.work_orders.consumed_overhead_ids = [(1, rec.con_overhead_id.id, {
                                            'quantity': cal_qty,
                                        })]
                            self.work_orders.consumed_overhead_history_ids = [(1, rec.ch_overhead_id.id, {
                                'state': 'cancel',
                            })]
                    else:
                        for rec in self.scrap_ids:
                            reserved = 0.00
                            for cs in rec.cs_overhead_id:
                                reserved = (cs.actual_used_qty - rec.scrap_qty)
                                for sheet in self.cost_sheet:
                                    sheet.material_overhead_ids = [(1, rec.cs_overhead_id.id, {
                                            'actual_used_qty': reserved,
                                        })]
                            cal_qty = 0.00
                            for con in rec.con_overhead_id:
                                cal_qty = (con.quantity - rec.scrap_qty)
                                if cal_qty == 0:
                                    self.work_orders.consumed_overhead_ids = [(2, rec.con_overhead_id.id, 0)]
                                else:
                                    self.work_orders.consumed_overhead_ids = [(1, rec.con_overhead_id.id, {
                                            'quantity': cal_qty,
                                        })]
                            self.work_orders.consumed_overhead_history_ids = [(1, rec.ch_overhead_id.id, {
                                'state': 'cancel',
                            })]


                if self.material_type == 'equipment':
                    if self.project_budget:
                        for rec in self.scrap_ids:
                            reserved = 0.00
                            for bud in rec.bd_equipment_id:
                                reserved = (bud.qty_used - rec.scrap_qty)
                                for sub in self.project_budget:
                                    sub.budget_equipment_ids = [(1, rec.bd_equipment_id.id, {
                                            'qty_used': reserved,
                                        })]
                            for cs in rec.cs_equipment_id:
                                reserved = (cs.actual_used_qty - rec.scrap_qty)
                                for sheet in self.cost_sheet:
                                    sheet.material_equipment_ids = [(1, rec.cs_equipment_id.id, {
                                            'actual_used_qty': reserved,
                                        })]
                            cal_qty = 0.00
                            for con in rec.con_equipment_id:
                                cal_qty = (con.quantity - rec.scrap_qty)
                                if cal_qty == 0:
                                    self.work_orders.consumed_equipment_ids = [(2, rec.con_equipment_id.id, 0)]
                                else:
                                    self.work_orders.consumed_equipment_ids = [(1, rec.con_equipment_id.id, {
                                            'quantity': cal_qty,
                                        })]
                            self.work_orders.consumed_equipment_history_ids = [(1, rec.ch_equipment_id.id, {
                                'state': 'cancel',
                            })]
                    else:
                        for rec in self.scrap_ids:
                            reserved = 0.00
                            for cs in rec.cs_equipment_id:
                                reserved = (cs.actual_used_qty - rec.scrap_qty)
                                for sheet in self.cost_sheet:
                                    sheet.material_equipment_ids = [(1, rec.cs_equipment_id.id, {
                                            'actual_used_qty': reserved,
                                        })]
                            cal_qty = 0.00
                            for con in rec.con_equipment_id:
                                cal_qty = (con.quantity - rec.scrap_qty)
                                if cal_qty == 0:
                                    self.work_orders.consumed_equipment_ids = [(2, rec.con_equipment_id.id, 0)]
                                else:
                                    self.work_orders.consumed_equipment_ids = [(1, rec.con_equipment_id.id, {
                                            'quantity': cal_qty,
                                        })]
                            self.work_orders.consumed_equipment_history_ids = [(1, rec.ch_equipment_id.id, {
                                'state': 'cancel',
                            })]

        return res

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

    def action_request_confirm(self):
        for record in self:
            zero_qty_scrap_ids = record.scrap_ids.filtered(lambda x: x.scrap_qty <= 0)
            if zero_qty_scrap_ids:
                zero_qty_scrap_ids.unlink()
        return super(StockScrapRequestInherit, self).action_request_confirm()


# Workaround to immediately remove labour from material type to existing database
class StockScrapRequestInherit2(models.Model):
    _inherit = 'stock.scrap.request'

    material_type = fields.Selection([('material','Material'), ('overhead','Overhead')], string="Material Type")


class StockScrapInherit(models.Model):
    _inherit = 'stock.scrap'
    _order = 'id'

    con_material_id = fields.Many2one('consumed.material', 'Consume Material ID')
    con_labour_id = fields.Many2one('consumed.labour', 'Consume labour ID')
    con_overhead_id = fields.Many2one('consumed.overhead', 'Consume overhead ID')
    con_equipment_id = fields.Many2one('consumed.equipment', 'Consume equipment ID')

    ch_material_id = fields.Many2many(comodel_name='consumed.material.history', string='Consumed Material History ID')
    ch_labour_id = fields.Many2many(comodel_name='consumed.labour.history', string='Consumed Labour History ID')
    ch_overhead_id = fields.Many2many(comodel_name='consumed.overhead.history', string='Consumed Overhead History ID')
    ch_equipment_id = fields.Many2many(comodel_name='consumed.equipment.history', string='Consumed Equipment History ID')

    cs_material_id = fields.Many2one('material.material', 'CS Material ID')
    cs_labour_id = fields.Many2one('material.labour', 'CS Labour ID')
    cs_overhead_id = fields.Many2one('material.overhead', 'CS Overhead ID')
    cs_equipment_id = fields.Many2one('material.equipment', 'CS Equipment ID')

    bd_material_id = fields.Many2one('budget.material', 'CS Material ID')
    bd_labour_id = fields.Many2one('budget.labour', 'CS Labour ID')
    bd_overhead_id = fields.Many2one('budget.overhead', 'CS Overhead ID')
    bd_equipment_id = fields.Many2one('budget.equipment', 'CS Equipment ID')

    cs_material_gop_id = fields.Many2one('material.gop.material', 'CS Material gop ID')
    cs_labour_gop_id = fields.Many2one('material.gop.labour', 'CS Labour gop ID')
    cs_overhead_gop_id = fields.Many2one('material.gop.overhead', 'CS Overhead gop ID')
    cs_equipment_gop_id = fields.Many2one('material.gop.equipment', 'CS Equipment gop ID')

    bd_material_gop_id = fields.Many2one('budget.gop.material', 'BD Material gop ID')
    bd_labour_gop_id = fields.Many2one('budget.gop.labour', 'BD Labour gop ID')
    bd_overhead_gop_id = fields.Many2one('budget.gop.overhead', 'BD Overhead gop ID')
    bd_equipment_gop_id = fields.Many2one('budget.gop.equipment', 'BD Equipment gop ID')

    project_scope = fields.Many2one('project.scope.line', string="Project Scope")
    section = fields.Many2one('section.line', string="Section")
    variable = fields.Many2one('variable.template', string="Variable")
    budget_qty = fields.Float('Budget Quantity', default=0.00)
    group_of_product = fields.Many2one('group.of.product', string="Group of Product")
    subcon = fields.Many2one('variable.template', string='Subcon', domain="[('variable_subcon', '=', True)]")
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                 compute='get_section_lines')
    on_hand_qty_converted = fields.Float('On Hand Quantity Converted', readonly=True)
    base_product_uom_id = fields.Many2one('uom.uom', 'Base Uom', related='product_id.uom_id')
    prev_product_uom_id = fields.Many2one('uom.uom', 'Prev Uom')
    project = fields.Many2one (related='scrap_id.project', string="Project")
    budgeting_method = fields.Selection(related='scrap_id.budgeting_method', string='Budgeting Method')
    budgeting_period = fields.Selection(related='scrap_id.budgeting_period', string='Budgeting Period')
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    material_type = fields.Selection(related='scrap_id.material_type' ,string = "Material Type")

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

    @api.onchange('project_scope', 'section', 'group_of_product', 'product_id')
    def _onchange_product_reference(self):
        for line in self:
            if line.project_scope and line.section and line.group_of_product and line.product_id:
                if line.scrap_id.budgeting_method != 'gop_budget':
                    if line.scrap_id.material_type == 'material':
                        line.cs_material_id = self.env['material.material'].search([('job_sheet_id', '=', line.scrap_id.cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
                        if line.scrap_id.project_budget:
                            line.bd_material_id = self.env['budget.material'].search([('budget_id', '=', line.scrap_id.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
                    # elif line.scrap_id.material_type == 'labour':
                    #     line.cs_labour_id = self.env['material.labour'].search([('job_sheet_id', '=', line.scrap_id.cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
                    #     if line.scrap_id.project_budget:
                    #         line.bd_labour_id = self.env['budget.labour'].search([('budget_id', '=', line.scrap_id.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
                    elif line.scrap_id.material_type == 'overhead':
                        line.cs_overhead_id = self.env['material.overhead'].search([('job_sheet_id', '=', line.scrap_id.cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
                        if line.scrap_id.project_budget:
                            line.bd_overhead_id = self.env['budget.overhead'].search([('budget_id', '=', line.scrap_id.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
                else:
                    if line.scrap_id.material_type == 'material':
                        line.cs_material_id = self.env['material.material'].search([('job_sheet_id', '=', line.scrap_id.cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
                        line.cs_material_gop_id = self.env['material.gop.material'].search([('job_sheet_id', '=', line.scrap_id.cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id)])
                        if line.scrap_id.project_budget:
                            line.bd_material_id = self.env['budget.material'].search([('budget_id', '=', line.scrap_id.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
                            line.bd_material_gop_id = self.env['budget.gop.material'].search([('budget_id', '=', line.scrap_id.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id)])
                    # elif line.scrap_id.material_type == 'labour':
                    #     line.cs_labour_id = self.env['material.labour'].search([('job_sheet_id', '=', line.scrap_id.cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
                    #     line.cs_labour_gop_id = self.env['material.gop.labour'].search([('job_sheet_id', '=', line.scrap_id.cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id)])
                    #     if line.scrap_id.project_budget:
                    #         line.bd_labour_id = self.env['budget.labour'].search([('budget_id', '=', line.scrap_id.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
                    #         line.bd_labour_gop_id = self.env['budget.gop.labour'].search([('budget_id', '=', line.scrap_id.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id)])
                    elif line.scrap_id.material_type == 'overhead':
                        line.cs_overhead_id = self.env['material.overhead'].search([('job_sheet_id', '=', line.scrap_id.cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
                        line.cs_overhead_gop_id = self.env['material.gop.overhead'].search([('job_sheet_id', '=', line.scrap_id.cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id)])
                        if line.scrap_id.project_budget:
                            line.bd_overhead_id = self.env['budget.overhead'].search([('budget_id', '=', line.scrap_id.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product_id.id)])
                            line.bd_overhead_gop_id = self.env['budget.gop.overhead'].search([('budget_id', '=', line.scrap_id.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id)])

    @api.onchange('scrap_qty')
    def _onchange_scrap_qty_validation(self):
        for rec in self:
            if rec.scrap_id.project:
                scrap_qty = rec.product_uom_id._compute_quantity(rec.scrap_qty, rec.product_id.uom_id)
                if scrap_qty > rec.on_hand_qty_converted:
                    raise ValidationError(_("There is not enough stock for '{}' in the location '{}'."
                                            "\n(Available quantity = {})".format(rec.product_id.name ,
                                                                                 rec.location_id.display_name,
                                                                                 rec.on_hand_qty_converted)))

                # total_scrap_qty = 0
                # for scrap in rec.scrap_id.scrap_ids:
                #     if rec.product_id == scrap.product_id:
                #         # To prevent double counting of current scrap in newly added product usage request
                #         # Changing quantity will create a virtual line that will lead to double counting,
                #         # This code will ignore that virtual line
                #         if not scrap._origin:
                #             if scrap.id.ref:
                #                 total_scrap_qty += scrap.scrap_qty
                #         else:
                #             total_scrap_qty += scrap.scrap_qty
                # if total_scrap_qty > rec.available_quantity:
                #     raise ValidationError(_("Usage Quantity is over available quantity for product {}. The available quantity for {} is {}".format(rec.product_id.name, rec.product_id.name, rec.available_quantity)))

    @api.onchange('product_uom_id')
    def _onchange_product_uom_id(self):
        for line in self:
            if line.product_id:
                if line.prev_product_uom_id:
                    line.scrap_qty = line.prev_product_uom_id._compute_quantity(line.scrap_qty, line.product_uom_id)
                else:
                    line.scrap_qty = line.product_id.uom_id._compute_quantity(line.scrap_qty, line.product_uom_id)
                line.prev_product_uom_id = line.product_uom_id

            converted_budget = 0
            if line.scrap_id.material_type == 'material':
                if line.cs_material_id and line.bd_material_id:
                    if line.product_uom_id == line.bd_material_id.uom_id:
                        converted_budget = line.bd_material_id.unused_qty
                    else:
                        line_factor = line.product_uom_id.factor
                        line_factor_inv = line.product_uom_id.factor_inv
                        dest_bd_factor = line.bd_material_id.uom_id.factor
                        dest_bd_factor_inv = line.bd_material_id.uom_id.factor_inv
                        if line.product_uom_id.uom_type == 'reference':
                            if line.bd_material_id.uom_id.uom_type == 'bigger':
                                converted_budget = (line.bd_material_id.unused_qty * dest_bd_factor_inv)
                            elif line.bd_material_id.uom_id.uom_type == 'smaller':
                                converted_budget = (line.bd_material_id.unused_qty / dest_bd_factor)
                            elif line.bd_material_id.uom_id.uom_type == 'reference':
                                converted_budget = (line.bd_material_id.unused_qty)
                        elif line.product_uom_id.uom_type == 'bigger':
                            if line.bd_material_id.uom_id.uom_type == 'bigger':
                                converted_budget = ((line.bd_material_id.unused_qty * line_factor_inv) / dest_bd_factor_inv)
                            elif line.bd_material_id.uom_id.uom_type == 'smaller':
                                converted_budget = ((line.bd_material_id.unused_qty / dest_bd_factor) / line_factor_inv)
                            elif line.bd_material_id.uom_id.uom_type == 'reference':
                                converted_budget = (line.bd_material_id.unused_qty / line_factor_inv)
                        elif line.product_uom_id.uom_type == 'smaller':
                            if line.bd_material_id.uom_id.uom_type == 'bigger':
                                converted_budget = ((line.bd_material_id.unused_qty * dest_bd_factor_inv) * line_factor)
                            elif line.bd_material_id.uom_id.uom_type == 'smaller':
                                converted_budget = ((line.bd_material_id.unused_qty / dest_bd_factor) * line_factor)
                            elif line.bd_material_id.uom_id.uom_type == 'reference':
                                converted_budget = (line.bd_material_id.unused_qty * line_factor)
                    line.budget_qty = converted_budget

                elif line.cs_material_id and not line.bd_material_id:
                    if line.product_uom_id == line.cs_material_id.uom_id:
                        converted_budget = line.cs_material_id.unused_qty
                    else:
                        line_factor = line.product_uom_id.factor
                        line_factor_inv = line.product_uom_id.factor_inv
                        dest_cs_factor = line.cs_material_id.uom_id.factor
                        dest_cs_factor_inv = line.cs_material_id.uom_id.factor_inv
                        if line.product_uom_id.uom_type == 'reference':
                            if line.cs_material_id.uom_id.uom_type == 'bigger':
                                converted_budget = (line.cs_material_id.unused_qty * dest_cs_factor_inv)
                            elif line.cs_material_id.uom_id.uom_type == 'smaller':
                                converted_budget = (line.cs_material_id.unused_qty / dest_cs_factor)
                            elif line.cs_material_id.uom_id.uom_type == 'reference':
                                converted_budget = (line.cs_material_id.unused_qty)
                        elif line.product_uom_id.uom_type == 'bigger':
                            if line.cs_material_id.uom_id.uom_type == 'bigger':
                                converted_budget = ((line.cs_material_id.unused_qty * line_factor_inv) / dest_cs_factor_inv)
                            elif line.cs_material_id.uom_id.uom_type == 'smaller':
                                converted_budget = ((line.cs_material_id.unused_qty / dest_cs_factor) / line_factor_inv)
                            elif line.cs_material_id.uom_id.uom_type == 'reference':
                                converted_budget = (line.cs_material_id.unused_qty / line_factor_inv)
                        elif line.product_uom_id.uom_type == 'smaller':
                            if line.cs_material_id.uom_id.uom_type == 'bigger':
                                converted_budget = ((line.cs_material_id.unused_qty * dest_cs_factor_inv) * line_factor)
                            elif line.cs_material_id.uom_id.uom_type == 'smaller':
                                converted_budget = ((line.cs_material_id.unused_qty / dest_cs_factor) * line_factor)
                            elif line.cs_material_id.uom_id.uom_type == 'reference':
                                converted_budget = (line.cs_material_id.unused_qty * line_factor)
                    line.budget_qty = converted_budget

            # if line.scrap_id.material_type == 'labour':
            #     if line.cs_labour_id and line.bd_labour_id:
            #         if line.product_uom_id == line.bd_labour_id.uom_id:
            #             converted_budget = line.bd_labour_id.unused_qty
            #         else:
            #             line_factor = line.product_uom_id.factor
            #             line_factor_inv = line.product_uom_id.factor_inv
            #             dest_bd_factor = line.bd_labour_id.uom_id.factor
            #             dest_bd_factor_inv = line.bd_labour_id.uom_id.factor_inv
            #             if line.product_uom_id.uom_type == 'reference':
            #                 if line.bd_labour_id.uom_id.uom_type == 'bigger':
            #                     converted_budget = (line.bd_labour_id.unused_qty * dest_bd_factor_inv)
            #                 elif line.bd_labour_id.uom_id.uom_type == 'smaller':
            #                     converted_budget = (line.bd_labour_id.unused_qty / dest_bd_factor)
            #                 elif line.bd_labour_id.uom_id.uom_type == 'reference':
            #                     converted_budget = (line.bd_labour_id.unused_qty)
            #             elif line.product_uom_id.uom_type == 'bigger':
            #                 if line.bd_labour_id.uom_id.uom_type == 'bigger':
            #                     converted_budget = ((line.bd_labour_id.unused_qty * line_factor_inv) / dest_bd_factor_inv)
            #                 elif line.bd_labour_id.uom_id.uom_type == 'smaller':
            #                     converted_budget = ((line.bd_labour_id.unused_qty / dest_bd_factor) / line_factor_inv)
            #                 elif line.bd_labour_id.uom_id.uom_type == 'reference':
            #                     converted_budget = (line.bd_labour_id.unused_qty / line_factor_inv)
            #             elif line.product_uom_id.uom_type == 'smaller':
            #                 if line.bd_labour_id.uom_id.uom_type == 'bigger':
            #                     converted_budget = ((line.bd_labour_id.unused_qty * dest_bd_factor_inv) * line_factor)
            #                 elif line.bd_labour_id.uom_id.uom_type == 'smaller':
            #                     converted_budget = ((line.bd_labour_id.unused_qty / dest_bd_factor) * line_factor)
            #                 elif line.bd_labour_id.uom_id.uom_type == 'reference':
            #                     converted_budget = (line.bd_labour_id.unused_qty * line_factor)
            #         line.budget_qty = converted_budget
            #
            #     elif line.cs_labour_id and not line.bd_labour_id:
            #         if line.product_uom_id == line.cs_labour_id.uom_id:
            #             converted_budget = line.cs_labour_id.unused_qty
            #         else:
            #             line_factor = line.product_uom_id.factor
            #             line_factor_inv = line.product_uom_id.factor_inv
            #             dest_cs_factor = line.cs_labour_id.uom_id.factor
            #             dest_cs_factor_inv = line.cs_labour_id.uom_id.factor_inv
            #             if line.product_uom_id.uom_type == 'reference':
            #                 if line.cs_labour_id.uom_id.uom_type == 'bigger':
            #                     converted_budget = (line.cs_labour_id.unused_qty * dest_cs_factor_inv)
            #                 elif line.cs_labour_id.uom_id.uom_type == 'smaller':
            #                     converted_budget = (line.cs_labour_id.unused_qty / dest_cs_factor)
            #                 elif line.cs_labour_id.uom_id.uom_type == 'reference':
            #                     converted_budget = (line.cs_labour_id.unused_qty)
            #             elif line.product_uom_id.uom_type == 'bigger':
            #                 if line.cs_labour_id.uom_id.uom_type == 'bigger':
            #                     converted_budget = ((line.cs_labour_id.unused_qty * line_factor_inv) / dest_cs_factor_inv)
            #                 elif line.cs_labour_id.uom_id.uom_type == 'smaller':
            #                     converted_budget = ((line.cs_labour_id.unused_qty / dest_cs_factor) / line_factor_inv)
            #                 elif line.cs_labour_id.uom_id.uom_type == 'reference':
            #                     converted_budget = (line.cs_labour_id.unused_qty / line_factor_inv)
            #             elif line.product_uom_id.uom_type == 'smaller':
            #                 if line.cs_labour_id.uom_id.uom_type == 'bigger':
            #                     converted_budget = ((line.cs_labour_id.unused_qty * dest_cs_factor_inv) * line_factor)
            #                 elif line.cs_labour_id.uom_id.uom_type == 'smaller':
            #                     converted_budget = ((line.cs_labour_id.unused_qty / dest_cs_factor) * line_factor)
            #                 elif line.cs_labour_id.uom_id.uom_type == 'reference':
            #                     converted_budget = (line.cs_labour_id.unused_qty * line_factor)
            #         line.budget_qty = converted_budget

            if line.scrap_id.material_type == 'overhead':
                if line.cs_overhead_id and line.bd_overhead_id:
                    if line.product_uom_id == line.bd_overhead_id.uom_id:
                        converted_budget = line.bd_overhead_id.unused_qty
                    else:
                        line_factor = line.product_uom_id.factor
                        line_factor_inv = line.product_uom_id.factor_inv
                        dest_bd_factor = line.bd_overhead_id.uom_id.factor
                        dest_bd_factor_inv = line.bd_overhead_id.uom_id.factor_inv
                        if line.product_uom_id.uom_type == 'reference':
                            if line.bd_overhead_id.uom_id.uom_type == 'bigger':
                                converted_budget = (line.bd_overhead_id.unused_qty * dest_bd_factor_inv)
                            elif line.bd_overhead_id.uom_id.uom_type == 'smaller':
                                converted_budget = (line.bd_overhead_id.unused_qty / dest_bd_factor)
                            elif line.bd_overhead_id.uom_id.uom_type == 'reference':
                                converted_budget = (line.bd_overhead_id.unused_qty)
                        elif line.product_uom_id.uom_type == 'bigger':
                            if line.bd_overhead_id.uom_id.uom_type == 'bigger':
                                converted_budget = ((line.bd_overhead_id.unused_qty * line_factor_inv) / dest_bd_factor_inv)
                            elif line.bd_overhead_id.uom_id.uom_type == 'smaller':
                                converted_budget = ((line.bd_overhead_id.unused_qty / dest_bd_factor) / line_factor_inv)
                            elif line.bd_overhead_id.uom_id.uom_type == 'reference':
                                converted_budget = (line.bd_overhead_id.unused_qty / line_factor_inv)
                        elif line.product_uom_id.uom_type == 'smaller':
                            if line.bd_overhead_id.uom_id.uom_type == 'bigger':
                                converted_budget = ((line.bd_overhead_id.unused_qty * dest_bd_factor_inv) * line_factor)
                            elif line.bd_overhead_id.uom_id.uom_type == 'smaller':
                                converted_budget = ((line.bd_overhead_id.unused_qty / dest_bd_factor) * line_factor)
                            elif line.bd_overhead_id.uom_id.uom_type == 'reference':
                                converted_budget = (line.bd_overhead_id.unused_qty * line_factor)
                    line.budget_qty = converted_budget

                elif line.cs_overhead_id and not line.bd_overhead_id:
                    if line.product_uom_id == line.cs_overhead_id.uom_id:
                        converted_budget = line.cs_overhead_id.unused_qty
                    else:
                        line_factor = line.product_uom_id.factor
                        line_factor_inv = line.product_uom_id.factor_inv
                        dest_cs_factor = line.cs_overhead_id.uom_id.factor
                        dest_cs_factor_inv = line.cs_overhead_id.uom_id.factor_inv
                        if line.product_uom_id.uom_type == 'reference':
                            if line.cs_overhead_id.uom_id.uom_type == 'bigger':
                                converted_budget = (line.cs_overhead_id.unused_qty * dest_cs_factor_inv)
                            elif line.cs_overhead_id.uom_id.uom_type == 'smaller':
                                converted_budget = (line.cs_overhead_id.unused_qty / dest_cs_factor)
                            elif line.cs_overhead_id.uom_id.uom_type == 'reference':
                                converted_budget = (line.cs_overhead_id.unused_qty)
                        elif line.product_uom_id.uom_type == 'bigger':
                            if line.cs_overhead_id.uom_id.uom_type == 'bigger':
                                converted_budget = ((line.cs_overhead_id.unused_qty * line_factor_inv) / dest_cs_factor_inv)
                            elif line.cs_overhead_id.uom_id.uom_type == 'smaller':
                                converted_budget = ((line.cs_overhead_id.unused_qty / dest_cs_factor) / line_factor_inv)
                            elif line.cs_overhead_id.uom_id.uom_type == 'reference':
                                converted_budget = (line.cs_overhead_id.unused_qty / line_factor_inv)
                        elif line.product_uom_id.uom_type == 'smaller':
                            if line.cs_overhead_id.uom_id.uom_type == 'bigger':
                                converted_budget = ((line.cs_overhead_id.unused_qty * dest_cs_factor_inv) * line_factor)
                            elif line.cs_overhead_id.uom_id.uom_type == 'smaller':
                                converted_budget = ((line.cs_overhead_id.unused_qty / dest_cs_factor) * line_factor)
                            elif line.cs_overhead_id.uom_id.uom_type == 'reference':
                                converted_budget = (line.cs_overhead_id.unused_qty * line_factor)
                    line.budget_qty = converted_budget

    @api.onchange('scrap_qty')
    def _onchange_consumed(self):
        if self.budgeting_method == 'product_budget':
            if self.scrap_id.material_type == 'material':
                if self.scrap_qty > self.budget_qty:
                    raise ValidationError(_( "Material quantity is over the budget quantity."))

            # if self.scrap_id.material_type == 'labour':
            #     if self.scrap_qty > self.budget_qty:
            #         raise ValidationError(_( "Labour quantity is over the budget quantity."))

            if self.scrap_id.material_type == 'overhead':
                if self.scrap_qty > self.budget_qty:
                    raise ValidationError(_( "Overhead quantity is over the budget quantity."))

            if self.scrap_id.material_type == 'equipment':
                if self.scrap_qty > self.budget_qty:
                    raise ValidationError(_( "Equipment quantity is over the budget quantity."))
