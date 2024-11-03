import json
from odoo import models, fields, api, _
from collections import defaultdict


class FinishedGoodSimulation(models.Model):
    _name = 'finished.good.simulation'
    _description = 'Finished Good Simulation'

    @api.model
    def create(self, values):
        if values.get('name', _('New')) == _('New'):
            values['name'] = self.env['ir.sequence'].next_by_code(
                'finished.good.simulation', sequence_date=None
            ) or _('New')
        return super(FinishedGoodSimulation, self).create(values)

    def _compute_generated_mrp(self):
        for record in self:
            record.mrp_plan_count = self.env['mrp.plan'].search_count([('origin', '=', record.name)])
            record.mrp_production_count = self.env['mrp.production'].search_count([('origin', '=', record.name)])

    @api.depends('finished_line_ids', 'finished_line_ids.active_for_create')
    def _compute_active_all(self):
        for record in self:
            active_all = False
            line_ids = record.finished_line_ids
            if line_ids:
                active_all = all(line.active_for_create for line in line_ids)
            record.active_all = active_all

    @api.depends('finished_line_ids', 'finished_line_ids.active_for_create')
    def _compute_active_any(self):
        for record in self:
            active_any = False
            line_ids = record.finished_line_ids
            if line_ids:
                active_any = any(line.active_for_create for line in line_ids)
            record.active_any = active_any

    name = fields.Char(default=lambda self: _('New'), required=True, readonly=True, copy=False, string='Reference')
    description = fields.Char(string='Name')
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
    branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
    create_uid = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user, readonly=True)
    finished_line_ids = fields.One2many('finished.good.simulation.line', 'simulation_id', string='Finished Goods')
    material_line_ids = fields.One2many('finished.good.simulation.material', 'simulation_id')

    based_on = fields.Selection(selection=[
        ('free_qty', 'Available'),
        ('qty_available', 'On Hand'),
        ('virtual_available', 'Forecasted')
    ], default='free_qty', required=True, string='Calculated Based On')

    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True)
    location_ids = fields.Many2many('stock.location', string='Locations', required=True, domain="[('warehouse_id', '=', warehouse_id), ('usage', '=', 'internal')]")

    mrp_plan_count = fields.Integer(compute=_compute_generated_mrp)
    mrp_production_count = fields.Integer(compute=_compute_generated_mrp)

    active_all = fields.Boolean(compute=_compute_active_all, store=True, readonly=False)
    active_any = fields.Boolean(compute=_compute_active_any)
    is_branch_required = fields.Boolean(related='company_id.show_branch')
    is_simulated = fields.Boolean()

    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('simulated', 'Simulated')
    ], default='draft', string='Status', required=True)

    @api.onchange('active_all')
    def _onchange_active_all(self):
        self.finished_line_ids.update({'active_for_create': self.active_all})

    @api.onchange('finished_line_ids')
    def _onchange_finished_line_ids(self):
        product_ids = []
        for line in self.finished_line_ids:
            for material in json.loads(line.bom_data):
                if material['bom_id']:
                    continue
                product_id = material['product_id']
                if product_id not in product_ids:
                    product_ids += [product_id]

        material_values = [(5,)]
        for product_id in product_ids:
            material_values += [(0, 0, {'product_id': product_id})]

        self.material_line_ids = material_values

        if self.is_simulated:
            self.action_simulate()

    @api.onchange('warehouse_id', 'based_on', 'finished_line_ids')
    def _onchange_set_locations(self):
        warehouse = self.warehouse_id
        qty_field = self.based_on
        products = self.finished_line_ids.mapped('bom_id').mapped('bom_line_ids').mapped('product_id')
        
        location_ids = []
        if qty_field:
            for location in self.env['stock.location'].search([
                ('warehouse_id', '=', warehouse.id),
                ('usage', '=', 'internal')
            ]):
                qty_values = products.with_context(location=location.id)._compute_quantities_dict(None, None, None)
                qty_location = 0.0
                for product in products:
                    qty_location += qty_values.get(product.id, {}).get(qty_field, 0.0)
                    if qty_location:
                        break
                if qty_location:
                    location_ids += [location.id]
        self.location_ids = [(6, 0, location_ids)]

    def action_simulate(self):
        self.ensure_one()
        
        leftover = {o.product_id: o[self.based_on] for o in self.material_line_ids}
        
        lines = [o for o in self.finished_line_ids]
        producible = {line: 0.0 for line in self.finished_line_ids}

        while lines:
            lines_to_remove = []
            for line in lines:
                bom = line.bom_id
                consumed = defaultdict(lambda: 0.0)

                is_enough_qty = True
                for material in json.loads(line.bom_data):
                    if material['bom_id']:
                        continue
                    materials = [(material['product_id'], material['product_qty'], material['product_uom'])]
                    bom_line_uom = self.env['uom.uom'].browse(material['product_uom'])
                    product = self.env['product.product'].browse(material['product_id'])
                    product_qty = bom_line_uom._compute_quantity(material['product_qty'], product.uom_id)
                    if product_qty > leftover[product]:
                        is_enough_qty = False
                        break
                    consumed[product] += product_qty
                    leftover[product] -= product_qty

                if is_enough_qty:
                    producible[line] += bom.product_uom_id._compute_quantity(bom.product_qty, line.uom_id)
                else:
                    for product, qty in consumed.items():
                        leftover[product] += qty
                    lines_to_remove += [line]

            for line in lines_to_remove:
                lines.remove(line)

        self.write({
            'state': 'simulated',
            'is_simulated': True,
            'finished_line_ids': [(1, line.id, {
                'estimated_qty': producible[line]
            }) for line in self.finished_line_ids],
            'material_line_ids': [(1, line.id, {
                'leftover_qty': leftover[line.product_id]
            }) for line in self.material_line_ids]
        })

    def _prepare_mrp_plan_values(self):
        self.ensure_one()
        description = self.name
        if self.description:
            description += ' (%s)' % self.description
        return {
            'name': description,
            'origin': self.name,
            'company_id': self.company_id.id,
            'branch_id': self.branch_id.id
        }

    def action_create_mrp_plan(self):
        self.ensure_one()
        plan_id = self.env['mrp.plan'].create(self._prepare_mrp_plan_values())
        plan_id.onchange_company_branch()
        
        wizard_id = self.env['mrp.production.wizard'].create({
            'plan_id': plan_id.id,
            'line_ids': [(0, 0, {
                'product_id': line.product_id.id,
                'bom_id': line.bom_id.id,
                'product_qty': line.uom_id._compute_quantity(line.estimated_qty, line.bom_id.product_uom_id),
                'product_uom': line.bom_id.product_uom_id.id,
                'branch_id': plan_id.branch_id.id,
                'company': plan_id.company_id.id
            }) for line in self.finished_line_ids.filtered(lambda l: l.active_for_create)]
        })
        wizard_id.confirm()
        return self.with_context(model='mrp.plan').action_view_mrp()

    def action_create_mrp_production(self):
        self.ensure_one()
        for line in self.finished_line_ids.filtered(lambda l: l.active_for_create):
            production_id = self.env['mrp.production'].create(line._prepare_mrp_order_values())
            production_id.sudo().onchange_product_id()
            production_id.sudo().onchange_branch()
            production_id.sudo()._onchange_workorder_ids()
            production_id.sudo()._onchange_move_raw()
            production_id.sudo()._onchange_move_finished()
            production_id.sudo().onchange_workorder_ids()
        return self.with_context(model='mrp.production').action_view_mrp()

    def action_view_mrp(self):
        self.ensure_one()
        model = self.env.context.get('model', False)
        if model not in ('mrp.plan', 'mrp.production'):
            return
        record_ids = self.env[model].search([('origin', '=', self.name)])
        if not record_ids:
            return
        action = {
            'name': model == 'mrp.plan' and _('Production Plan') or _('Production Order'),
            'type': 'ir.actions.act_window',
            'res_model': model,
            'target': 'current'
        }
        if len(record_ids) == 1:
            values = {
                'view_mode': 'form',
                'res_id': record_ids[0].id
            }
        else:
            values = {
                'view_mode': 'tree,form',
                'domain': [('id', 'in', record_ids.ids)]
            }
        action.update(values)
        return action


class FinishedGoodSimulationLine(models.Model):
    _name = 'finished.good.simulation.line'
    _description = 'Finished Good Simulation Line'

    def _bom_search(self):
        bom_domain = self.env['mrp.bom'].with_context(
            equip_bom_type='mrp',
            branch_id=branch.id
        )._bom_find_domain(product=self.product_id, company_id=self.company_id.id, bom_type='normal')
        boms = self.env['mrp.bom'].search(bom_domain, order='sequence, product_id')
        other_lines = self.simulation_id.finished_line_ids - self
        other_boms = other_lines.mapped('bom_id')
        return boms - other_boms

    @api.depends('simulation_id.company_id', 'simulation_id.finished_line_ids.bom_id', 'product_id')
    def _compute_allowed_bom_ids(self):
        for record in self:
            bom_ids = record._bom_search()
            record.allowed_bom_ids = [(6, 0, bom_ids.ids)]

    sequence = fields.Integer()
    simulation_id = fields.Many2one('finished.good.simulation', string='Simulation')
    company_id = fields.Many2one('res.company', related='simulation_id.company_id')
    branch_id = fields.Many2one('res.branch', related='simulation_id.branch_id')
    product_id = fields.Many2one('product.product', required=True, domain="[('has_bom', '=', True)]", string='Finished Good')
    allowed_bom_ids = fields.One2many('mrp.bom', compute=_compute_allowed_bom_ids)
    bom_id = fields.Many2one('mrp.bom', domain="[('id', 'in', allowed_bom_ids)]", required=True, string='BoM')
    estimated_qty = fields.Float(string='Estimated Producible Quantity', digits='Product Unit of Measure')
    active_for_create = fields.Boolean()
    uom_id = fields.Many2one('uom.uom', related='product_id.uom_id')
    bom_data = fields.Text(compute='_compute_bom_data', store=True)

    @api.onchange('product_id', 'company_id', 'branch_id')
    def _onchange_set_bom(self):
        bom_id = False
        if self.company_id and self.product_id and self.branch_id:
            bom_id = self.env['mrp.bom'].with_context(
                equip_bom_type='mrp',
                branch_id=self.branch_id.id
            )._bom_find(product=self.product_id, company_id=self.company_id.id, bom_type='normal').id
        self.bom_id = bom_id

    @api.depends('bom_id')
    def _compute_bom_data(self):
        for record in self:
            bom = record.bom_id
            bom_data = []
            if bom:
                bom_data = bom._boom(bom.product_qty)
            record.bom_data = json.dumps(bom_data)

    def _prepare_mrp_order_values(self):
        self.ensure_one()
        simulation = self.simulation_id
        return {
            'product_id': self.product_id.id,
            'product_qty': self.uom_id._compute_quantity(self.estimated_qty, self.bom_id.product_uom_id),
            'bom_id': self.bom_id.id,
            'user_id': self.env.user.id,
            'product_uom_id': self.bom_id.product_uom_id.id,
            'company_id': simulation.company_id.id,
            'branch_id': simulation.branch_id.id,
            'origin': simulation.name
        }


class FinishedGOodSimulationMaterial(models.Model):
    _name = 'finished.good.simulation.material'
    _description = 'Finished Good Simulation Material'

    @api.depends('product_id', 'warehouse_id', 'location_ids')
    def _compute_quantities(self):
        values = {}
        for record in self:
            qty_available = 0.0
            free_qty = 0.0
            virtual_available = 0.0

            product_id = record.product_id
            
            if product_id:

                if values.get(product_id):
                    qty_available = values[product_id]['qty_available']
                    free_qty = values[product_id]['free_qty']
                    virtual_available = values[product_id]['virtual_available']
                else:
                    warehouse = record.warehouse_id
                    for location in record.location_ids:
                        product_contexed = product_id.with_context(location=location.id or location._origin.id)
                        qty_values = product_contexed._compute_quantities_dict(None, None, None).get(product_id.id, {})

                        qty_available += qty_values.get('qty_available', 0.0)
                        free_qty += qty_values.get('free_qty', 0.0)
                        virtual_available += qty_values.get('virtual_available', 0.0)

                    values[product_id] = {
                        'qty_available': qty_available, 
                        'free_qty': free_qty,
                        'virtual_available': virtual_available
                    }
            
            record.qty_available = qty_available
            record.free_qty = free_qty
            record.virtual_available = virtual_available


    simulation_id = fields.Many2one('finished.good.simulation', string='Simulation')
    product_id = fields.Many2one('product.product', string='Product')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', related='simulation_id.warehouse_id')
    location_ids = fields.Many2many('stock.location', string='Locations', related='simulation_id.location_ids')
    uom_id = fields.Many2one('uom.uom', related='product_id.uom_id')

    qty_available = fields.Float(string='On Hand', digits='Product Unit of Measure', compute=_compute_quantities)
    free_qty = fields.Float(string='Available', digits='Product Unit of Measure', compute=_compute_quantities)
    virtual_available = fields.Float(string='Forecast', digits='Product Unit of Measure', compute=_compute_quantities)

    leftover_qty = fields.Float(string='Leftover', digits='Product Unit of Measure')
