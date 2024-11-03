# -*- coding: utf-8 -*-
import json
from odoo import fields, models, api
from odoo.tools import float_compare


class MrpProductionWizard(models.TransientModel):
    _name = 'mrp.production.wizard'
    _description = 'Add Production Order'

    plan_id = fields.Many2one('mrp.plan', string='Production Plan', required=True)
    line_ids = fields.One2many('mrp.production.wizard.line', 'wizard_id')
    display_line_ids = fields.One2many('mrp.production.wizard.line.display', 'wizard_id')
    is_auto_create_production_order = fields.Boolean(related='plan_id.is_auto_create_production_order')

    def _post_production_create(self):
        # inherited in manuf_account
        self.ensure_one()

    def confirm(self):
        self.ensure_one()
        plan = self.plan_id
        if self.env.context.get('skip_create_plan_line', False):
            order_ids = self.env['mrp.production']
            for line in self.line_ids:
                order_ids |= line._create_orders()
            self._post_production_create()
            return order_ids
        else:
            plan.line_ids = [(0, 0, {
                'line_id': line.line_id,
                'sequence': len(plan.line_ids) + sequence + 1,
                'product_id': line.product_id.id,
                'bom_id': line.bom_id.id,
                'to_produce_qty': line.product_qty * line.no_of_mrp,
                'uom_id': line.product_uom.id,
                'bom_line_id': line.bom_line_id.id,
                'operation_id': line.operation_id.id,
                'no_of_mrp': line.no_of_mrp,
                'bom_datas': line.bom_datas
            }) for sequence, line in enumerate(self.line_ids.filtered(lambda o: o.produce))]
            plan._generate_pseudo_materials()

    @api.onchange('display_line_ids')
    def _onchange_display_line_ids(self):
        line_ids = self.line_ids
        display_line_ids = self.display_line_ids
        parent_lines = display_line_ids.filtered(lambda o: o.parent_id == 0)

        display_lines_values = []
        line_values = []
        next_line_id = 1
        for display_line in parent_lines:
            line_id = next_line_id
            product_id = display_line.product_id
            bom_id = display_line.bom_id
            product_qty = display_line.product_qty
            product_uom = display_line.product_uom
            bom_line_id = display_line.bom_line_id
            operation_id = display_line.operation_id
            produce = display_line.produce
            no_of_mrp = display_line.no_of_mrp

            if not bom_id or not product_qty or not product_uom or not no_of_mrp:
                continue

            display_line_values = [(0, 0, {
                'line_id': next_line_id,
                'parent_id': 0,
                'level': 0,
                'product_id': product_id.id,
                'bom_id': bom_id.id,
                'product_qty': product_qty,
                'product_uom': product_uom.id,
                'bom_line_id': bom_line_id.id,
                'operation_id': operation_id.id,
                'produce': produce,
                'no_of_mrp': no_of_mrp,
                'case_field': 'A'
            })]
            next_line_id += 1

            real_line = line_ids.filtered(lambda o: o.line_id == line_id)
            if real_line:
                materials = json.loads(real_line.bom_datas)

                display_line_changes = display_line._has_changes(real_line)

                if display_line_changes:
                    bom_product_qty = product_uom._compute_quantity(product_qty, bom_id.product_uom_id) * no_of_mrp
                    materials = bom_id._boom(bom_product_qty, id=next_line_id, parent_id=line_id, data=materials)
                    
                    material_values = []
                    for material in materials:
                        material_values += [(0, 0, {
                            'line_id': next_line_id,
                            'parent_id': material['parent_id'],
                            'level': material['level'],
                            'product_id': material['product_id'],
                            'bom_id': material['bom_id'],
                            'product_qty': material['product_qty'],
                            'product_uom': material['product_uom'],
                            'bom_line_id': material['bom_line_id'],
                            'operation_id': material['operation_id'],
                            'produce': produce,
                            'no_of_mrp': 1,
                            'case_field': 'F'
                        })]
                        next_line_id += 1

                else:
                    to_skip = []
                    material_values = []
                    for material in materials:
                        material_line = display_line_ids.filtered(lambda o: o.line_id == material['line_id'])
                        if material_line:
                            if material['line_id'] in to_skip:
                                to_skip += [m['line_id'] for m in materials if m['parent_id'] == material['line_id']]
                                continue

                            material_line_changes = material_line._has_changes(material)
                            material_line_produce = material_line.produce if 'bom_id' not in material_line_changes else True
                            
                            material_values += [(0, 0, {
                                'line_id': next_line_id,
                                'parent_id': material_line.parent_id,
                                'level': material_line.level,
                                'product_id': material_line.product_id.id,
                                'bom_id': material_line.bom_id.id,
                                'product_qty': material_line.product_qty,
                                'product_uom': material_line.product_uom.id,
                                'bom_line_id': material_line.bom_line_id.id,
                                'operation_id': material_line.operation_id.id,
                                'produce': material_line_produce,
                                'no_of_mrp': material_line.no_of_mrp,
                                'case_field': 'B'
                            })]
                            next_line_id += 1

                            if material_line_changes:
                                to_skip += [m['line_id'] for m in materials if m['parent_id'] == material_line.line_id]

                                if material_line.bom_id:
                                    bom_product_qty = material_line.product_uom._compute_quantity(material_line.product_qty, material_line.bom_id.product_uom_id) * material_line.no_of_mrp
                                    child_materials = material_line.bom_id._boom(bom_product_qty, level=material_line.level + 1, id=next_line_id, parent_id=next_line_id - 1, data=materials)

                                    for child_material in child_materials:
                                        material_values += [(0, 0, {
                                            'line_id': next_line_id,
                                            'parent_id': child_material['parent_id'],
                                            'level': child_material['level'],
                                            'product_id': child_material['product_id'],
                                            'bom_id': child_material['bom_id'],
                                            'product_qty': child_material['product_qty'],
                                            'product_uom': child_material['product_uom'],
                                            'bom_line_id': child_material['bom_line_id'],
                                            'operation_id': child_material['operation_id'],
                                            'produce': material_line_produce,
                                            'no_of_mrp': 1,
                                            'case_field': 'C'
                                        })]
                                        next_line_id += 1
                            
                        else:
                            parent_line = display_line_ids.filtered(lambda o: o.line_id == material['parent_id'])
                            material_values += [(0, 0, {
                                'line_id': next_line_id,
                                'parent_id': material['parent_id'],
                                'level': material['level'],
                                'product_id': material['product_id'],
                                'bom_id': material['bom_id'],
                                'product_qty': material['product_qty'],
                                'product_uom': material['product_uom'],
                                'bom_line_id': material['bom_line_id'],
                                'operation_id': material['operation_id'],
                                'produce': parent_line.produce if parent_line else True,
                                'no_of_mrp': material['no_of_mrp'],
                                'case_field': 'D'
                            })]
                            next_line_id += 1

            else:
                bom_product_qty = product_uom._compute_quantity(product_qty, bom_id.product_uom_id) * no_of_mrp
                materials = bom_id._boom(bom_product_qty, id=next_line_id, parent_id=line_id)
                
                material_values = []
                for material in materials:
                    material_values += [(0, 0, {
                        'line_id': next_line_id,
                        'parent_id': material['parent_id'],
                        'level': material['level'],
                        'product_id': material['product_id'],
                        'bom_id': material['bom_id'],
                        'product_qty': material['product_qty'],
                        'product_uom': material['product_uom'],
                        'bom_line_id': material['bom_line_id'],
                        'operation_id': material['operation_id'],
                        'produce': produce,
                        'no_of_mrp': 1,
                        'case_field': 'E'
                    })]
                    next_line_id += 1

            line_values += [(0, 0, {
                'line_id': line_id,
                'product_id': product_id.id,
                'bom_id': bom_id.id,
                'product_qty': product_qty,
                'product_uom': product_uom.id,
                'produce': produce,
                'bom_line_id': bom_line_id.id,
                'operation_id': operation_id.id,
                'no_of_mrp': no_of_mrp,
                'bom_datas': json.dumps([values for a, b, values in material_values], default=str)
            })]

            display_line_values += material_values
            display_lines_values += display_line_values
        
        self.display_line_ids = [(5,)] + display_lines_values
        self.line_ids = [(5,)] + line_values


class MrpProductionWizardLine(models.TransientModel):
    _name = 'mrp.production.wizard.line'
    _description = 'MRP Plan Production Wizard Line'

    wizard_id = fields.Many2one('mrp.production.wizard')
    product_id = fields.Many2one('product.product', 'Product', domain="[('has_bom', '=', True)]")
    product_uom_category_id = fields.Many2one('uom.category', compute='_compute_product_uom_category')

    product_qty = fields.Float('Quantity', default=1, digits='Product Unit of Measure')
    product_uom = fields.Many2one('uom.uom', 'Unit of Measure')
    no_of_mrp = fields.Integer(string='No of Production Order', default=1)
    branch_id = fields.Many2one('res.branch', string='Branch')
    company = fields.Many2one('res.company', string='Company')
    bom_id = fields.Many2one(
        'mrp.bom', 'Bill of Material',
        domain="""[
        '&',
        '&',
            '|',
                ('company_id', '=', False),
                ('company_id', '=', company),
            '|',
                ('branch_id', '=', False),
                ('branch_id', '=', branch_id),
            '&',
                '|',
                    ('product_id','=',product_id),
                    '&',
                        ('product_tmpl_id.product_variant_ids','=',product_id),
                        ('product_id','=',False),
        ('type', '=', 'normal'),
        ('equip_bom_type', '=', 'mrp')]""",
        check_company=True)

    # technical fields
    bom_line_id = fields.Many2one('mrp.bom.line')
    operation_id = fields.Many2one('mrp.routing.workcenter')
    bom_datas = fields.Text()
    line_id = fields.Integer(default=-1)
    produce = fields.Boolean(default=True)

    @api.model
    def default_get(self, fields):
        defaults = super(MrpProductionWizardLine, self).default_get(fields)
        mrp_plan_id = False
        if self._context.get("active_model") == 'mrp.plan':
            mrp_plan_id = self._context.get("active_id")
              
        if self._context.get("mrp_plan_id") and self._context.get("is_from_confirm_so") == True:
            mrp_plan_id = self._context.get("mrp_plan_id")
                 
        mrp_plan = self.env["mrp.plan"].browse(mrp_plan_id)
        if mrp_plan:
            if mrp_plan.branch_id:
                defaults['branch_id'] = mrp_plan.branch_id.id
            if mrp_plan.company_id:
                defaults['company'] = mrp_plan.company_id.id
        return defaults

    @api.depends('product_id')
    def _compute_product_uom_category(self):
        for record in self:
            record.product_uom_category_id = record.product_id.uom_id.category_id.id

    @api.onchange('product_id', 'company', 'branch_id')
    def _onchange_product_id(self):
        if self.product_id and self.company:
            bom = self.env['mrp.bom'].with_context(branch_id=self.branch_id.id, equip_bom_type='mrp')._bom_find(product=self.product_id, company_id=self.company.id, bom_type='normal')
            self.bom_id = bom and bom.id or False

    @api.onchange('bom_id')
    def _onchange_bom_id(self):
        self.product_qty = self.bom_id.product_qty
        self.product_uom = self.bom_id.product_uom_id.id

    def _prepare_order_values(self, bom_id, product_id, product_qty, uom_id, parent_id):
        self.ensure_one()
        plan_id = self.wizard_id.plan_id
        values = {
            'mrp_plan_id': plan_id.id,
            'bom_id': bom_id,
            'product_id': product_id,
            'product_qty': product_qty,
            'product_uom_id': uom_id,
            'parent_id': parent_id.id,
            'company_id': plan_id.company_id.id,
            'branch_id': plan_id.branch_id.id,
            'user_id': self.env.user.id,
            'date_planned_start': plan_id.date_planned_start,
            'date_planned_finished': plan_id.date_planned_finished,
        }
        if plan_id.is_auto_create_production_order and plan_id.state in ('confirm', 'progress'):
            values.update({
                'additional_mo': True
            })
        return values

    def _create_order(self, bom_id, product_id, product_qty, uom_id, parent_id):
        self.ensure_one()
        values = self._prepare_order_values(bom_id, product_id, product_qty, uom_id, parent_id)
        order = self.env['mrp.production'].create(values).sudo()

        order.onchange_product_id()
        order.onchange_branch()
        order._onchange_workorder_ids()
        order._onchange_move_raw()
        order._onchange_move_finished()
        order.onchange_workorder_ids()
        order._onchange_location_dest()
        order._set_bom_fields()
        self._post_production_create(order)
        return order

    def _post_production_create(self, order):
        # inherited in manuf_account
        self.ensure_one()

    def _create_orders(self):
        self.ensure_one()
        material_values = json.loads(self.bom_datas or '{}')
        if not material_values:
            material_values = []
            for i in range(self.no_of_mrp):
                bom_product_qty = self.product_uom._compute_quantity(self.product_qty, self.bom_id.product_uom_id)
                for values in self.bom_id._boom(bom_product_qty, id=self.line_id+1, parent_id=self.line_id):
                    values.update({
                        'produce': values['bom_id'] is not False,
                        'line_id': values['id']
                    })
                    material_values += [values]

        order = self._create_order(self.bom_id.id, self.product_id.id, self.product_qty, self.product_uom.id, parent_id=self.env['mrp.production'])
        line_orders = {self.line_id: order}

        order_ids = [order.id]
        for values in material_values:
            if values['bom_id'] and values['produce']:
                parent_id = line_orders.get(values['parent_id'], self.env['mrp.production'])
                for i in range(values.get('no_of_mrp', 1)):
                    order = self._create_order(values['bom_id'], values['product_id'], values['product_qty'], values['product_uom'], parent_id)
                    line_orders[values['line_id']] = order
                    order_ids.append(order.id)
        return self.env['mrp.production'].browse(order_ids)


class MrpProductionWizardLineDisplay(models.TransientModel):
    _name = 'mrp.production.wizard.line.display'
    _inherit = 'mrp.production.wizard.line'
    _description = 'MRP Plan Production Wizard Line Display'

    # technical fields
    parent_id = fields.Integer()
    level = fields.Integer()
    case_field = fields.Char()

    @api.model
    def _get_editable_fields(self):
        return ['product_id', 'bom_id', 'product_qty', 'product_uom', 'produce', 'no_of_mrp']

    @api.model
    def _compare_float(self, val1, val2, rounding):
        return float_compare(val1, val2, precision_rounding=rounding) == 0

    @api.model
    def _compare_integer(self, val1, val2):
        return val1 == val2

    @api.model
    def _compare_boolean(self, val1, val2):
        return val1 is val2

    @api.model
    def _compare_many2one(self, val1, val2):
        if not isinstance(val1, int):
            val1 = val1.id
        if not isinstance(val2, int):
            val2 = val2.id
        return self._compare_integer(val1, val2)

    def _compare(self, field_name, value):
        field_type = self._fields[field_name].type
        if field_type == 'float':
            return self._compare_float(self[field_name], value, self.product_uom.rounding)
        return getattr(self, '_compare_%s' % field_type)(self[field_name], value)

    def _has_changes(self, line):
        changed_fields = []
        for field_name in self._get_editable_fields():
            if not self._compare(field_name, line[field_name]):
                changed_fields += [field_name]
        return changed_fields

    @api.onchange('bom_id')
    def _onchange_bom_id(self):
        if self.bom_id:
            self.product_qty = self.bom_id.product_qty
            self.product_uom = self.bom_id.product_uom_id.id
