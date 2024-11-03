# -*- coding: utf-8 -*-
from odoo import fields, models, tools, api, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class WizardChangeComponents(models.TransientModel):
    _name = 'mrp.change.component.wizard'
    _description = 'Change Components Wizard'

    production_id = fields.Many2one('mrp.production', string='Production')
    line_ids = fields.One2many('mrp.change.component.wizard.line', 'add_id')
    production_ids = fields.Many2many('mrp.production', string='Productions')
    hide_mo_field = fields.Boolean()

    def confirm(self):
        self.ensure_one()
        for line in self.line_ids:
            production = line.production_id
            workorder = line.workorder_id
            move_id = line.move_id
            if move_id:
                line_product_qty = line.product_uom._compute_quantity(line.product_uom_qty, line.product_id.uom_id)
                is_material_qty_changed = float_compare(line_product_qty, move_id.product_qty, precision_rounding=line.product_id.uom_id.rounding) != 0
                move_values = {
                    'product_uom_qty': line.product_uom_qty,
                    'product_uom': line.product_uom.id,
                    'is_material_qty_changed': is_material_qty_changed
                }
                move_id.write(move_values)
                if not move_id.product_uom_qty:
                    move_id._action_cancel()
            else:
                move_raw_values = production._get_move_raw_values(
                    product_id=line.product_id,
                    product_uom_qty=line.product_uom_qty,
                    product_uom=line.product_uom,
                    operation_id=line.operation_id.id
                )
                move_raw_values.update({
                    'mrp_workorder_component_id': workorder.id,
                    'workorder_id': workorder.id,
                    'mrp_plan_id': production.mrp_plan_id and production.mrp_plan_id.id or False
                })
                new_move = self.env['stock.move'].create(move_raw_values)
                new_move._action_confirm()
                new_move._action_assign()

            production.button_unplan()
            production.button_plan()

    @api.constrains('line_ids')
    def _constrains_line_ids(self):
        for record in self:
            if not record.line_ids:
                raise ValidationError(_('There is no material to consume!'))


class WizardChangeComponentLine(models.TransientModel):
    _name = 'mrp.change.component.wizard.line'
    _description = 'Change Components Wizard Line'

    add_id = fields.Many2one('mrp.change.component.wizard')

    move_id = fields.Many2one('stock.move', string='Stock Move')
    bom_line_id = fields.Many2one('mrp.bom.line', string='BoM Line', related='move_id.bom_line_id')

    product_id = fields.Many2one('product.product', string='Product', domain="[('id', 'in', allowed_product_ids)]")
    product_uom_category_id = fields.Many2one('uom.category', related='product_id.uom_id.category_id')
    product_uom_qty = fields.Float('To Consume', digits='Product Unit of Measure')
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure', domain="[('category_id', '=', product_uom_category_id)]")

    alternative_component_ids = fields.Many2many('product.product', related='bom_line_id.alternative_component_ids')
    allowed_product_ids = fields.Many2many('product.product', compute='_compute_allowed_products')
    
    operation_id = fields.Many2one('mrp.routing.workcenter', string='Operation To Consume', domain="[('id', 'in', allowed_operation_ids)]")
    allowed_operation_ids = fields.One2many('mrp.routing.workcenter', related='bom_id.operation_ids')
    
    production_id = fields.Many2one('mrp.production', string='Production Order')
    workorder_id = fields.Many2one('mrp.workorder', string='Production Work Order')
    bom_id = fields.Many2one('mrp.bom', 'BoM', related='production_id.bom_id')

    @api.depends('bom_id')
    def _compute_allowed_products(self):
        for record in self:
            bom_id = record.bom_id
            product_ids = []
            if bom_id:
                bom_line_ids = bom_id.bom_line_ids
                product_ids = (bom_line_ids.mapped('product_id') | bom_line_ids.mapped('alternative_component_ids')).ids
            record.allowed_product_ids = [(6, 0, product_ids)]

    @api.onchange('product_id', 'bom_line_id')
    def _onchange_product_bom_lines(self):
        if not self.bom_line_id and self.product_id:
            self.product_uom = self.product_id.uom_id.id

    @api.onchange('production_id', 'operation_id')
    def _onchange_operation_id(self):
        if not self.production_id:
            return
        workorder_ids = self.production_id.workorder_ids.filtered(lambda w: w.operation_id == self.operation_id)
        if workorder_ids:
            self.workorder_id = workorder_ids[0].id
