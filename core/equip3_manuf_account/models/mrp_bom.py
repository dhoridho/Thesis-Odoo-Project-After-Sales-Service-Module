from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import float_round


def safe_div(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        return a


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    forecast_cost = fields.Float(string='Forecast Cost', compute='_get_bom_cost', store=False)

    def _get_bom_cost(self):
        mrp_boms = self.filtered(lambda o: o.equip_bom_type == 'mrp')

        for bom in mrp_boms:
            forecast_cost = 0.0
            if bom.product_uom_id:
                report_data = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=bom.id, searchQty=bom.product_qty, searchVariant=False)
                forecast_cost = report_data.get('lines', {}).get('total', 0.0)
            
            bom.forecast_cost = forecast_cost
        (self - mrp_boms).forecast_cost = 0.0

    def _get_operation_line(self, bom, qty, level):
        operations = []
        total = 0.0
        for operation in bom.operation_ids:
            workcenter_id = operation._get_workcenter()
            operation_cycle = float_round(safe_div(qty, workcenter_id.capacity), precision_rounding=1, rounding_method='UP')
            duration_expected = operation_cycle * operation.time_cycle + workcenter_id.time_stop + workcenter_id.time_start
            total = ((duration_expected / 60.0) * workcenter_id.costs_hour)
            total = self.env.company.currency_id.round(total)

            labors = []
            for labor in workcenter_id.labor_ids:
                labor_total = ((duration_expected / 60.0) * labor.cost_per_hour)
                labors += [{
                    'level': level or 0,
                    'labor': labor,
                    'name': 'Labor - %s: %s' % (labor.user_id.display_name, operation.name),
                    'labor_name': labor.user_id.display_name,
                    'duration_expected': duration_expected,
                    'total': self.env.company.currency_id.round(labor_total),
                }]

            operations.append({
                'level': level or 0,
                'operation': operation,
                'name': '%s - %s' % (operation.name, operation.workcenter_id.name),
                'duration_expected': duration_expected,
                'total': self.env.company.currency_id.round(total),
                'labors': labors
            })
        return operations

    def _get_bom_lines(self, bom, bom_quantity, product, line_id, level):
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

        components = []
        total = 0
        for line in bom.bom_line_ids:
            line_quantity = safe_div(bom_quantity, bom.product_qty) * line.product_qty
            if line._skip_bom_line(product):
                continue
            company = bom.company_id or self.env.company
            product = line.product_id.with_company(company)
            if is_cost_per_warehouse and line.operation_id:
                product = product.with_context(price_for_warehouse=line.operation_id._get_workcenter().location_id.get_warehouse().id)
            price = product.uom_id._compute_price(product.standard_price, line.product_uom_id) * line_quantity
            if line.child_bom_id:
                factor = safe_div(
                    line.product_uom_id._compute_quantity(line_quantity, line.child_bom_id.product_uom_id),
                    line.child_bom_id.product_qty)
                sub_total = self._get_price(line.child_bom_id, factor, product)
            else:
                sub_total = price
            sub_total = self.env.company.currency_id.round(sub_total)
            total += sub_total
        return total

    def _get_byproduct_lines(self, bom, bom_quantity, product, line_id, level, total_material):
        byproduct_total = 0
        for line in bom.byproduct_ids:
            sub_total = self.env.company.currency_id.round((line.allocated_cost * total_material) / 100)
            byproduct_total += sub_total
        return byproduct_total

    def _get_price(self, bom, factor, product):
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

        price = 0
        if bom.operation_ids:
            # routing are defined on a BoM and don't have a concept of quantity.
            # It means that the operation time are defined for the quantity on
            # the BoM (the user produces a batch of products). E.g the user
            # product a batch of 10 units with a 5 minutes operation, the time
            # will be the 5 for a quantity between 1-10, then doubled for
            # 11-20,...
            operation_cycle = float_round(factor, precision_rounding=1, rounding_method='UP')
            operations = self._get_operation_line(bom, operation_cycle, 0)
            operation_total = sum(op.get('total', 0.0) for op in operations)
            price += operation_total

        for line in bom.bom_line_ids:
            if line._skip_bom_line(product):
                continue
            company = bom.company_id or self.env.company
            product = line.product_id.with_company(company)
            if is_cost_per_warehouse and line.operation_id:
                product = product.with_context(price_for_warehouse=line.operation_id._get_workcenter().location_id.get_warehouse().id)
            if line.child_bom_id:
                qty = safe_div(
                    line.product_uom_id._compute_quantity(line.product_qty * factor, line.child_bom_id.product_uom_id),
                    line.child_bom_id.product_qty)
                sub_price = self._get_price(line.child_bom_id, qty, product)
                price += sub_price
            else:
                prod_qty = line.product_qty * factor
                not_rounded_price = product.uom_id._compute_price(product.standard_price, line.product_uom_id) * prod_qty
                price += company.currency_id.round(not_rounded_price)
        return price

    @api.constrains('finished_ids')
    def _check_finished_ids(self):
        for record in self:
            finished_ids = record.finished_ids
            total_cost_allocation = sum(finished_ids.mapped('allocated_cost'))
            if total_cost_allocation != 100:
                raise ValidationError(_('Total Cost Allocation must be 100%!'))

    def _prepare_finished_values(self):
        values = super(MrpBom, self)._prepare_finished_values()
        values['allocated_cost'] = 100.0
        return values

    def _get_estimated_cost(self, product_id, product_qty, product_uom, parent, parent_field, level=0, skip=False):
        self.ensure_one()

        product_uom_qty = product_uom._compute_quantity(product_qty, self.product_uom_id)
        report = self.env['report.mrp.report_bom_structure']._get_report_data(self.id, searchQty=product_uom_qty)
        report_lines = report.get('lines', {})

        cost_values = []
        if not skip:
            for finished in self.finished_ids:
                qty = product_uom._compute_quantity(product_qty, finished.product_uom_id)
                product_qty = finished.product_uom_id._compute_quantity(qty, finished.product_id.uom_id)
                cost_values += [(0, 0, {
                    parent_field: parent.id,
                    'name': finished.product_id.display_name,
                    'qty': qty,
                    'product_qty': product_qty,
                    'uom_name': finished.product_uom_id.display_name,
                    'total_cost': (report_lines.get('total', 0.0) * finished.allocated_cost) / 100,
                    'type': 'finished',
                    'level': level,
                    'product_id': finished.product_id.id,
                })]
        
        for line_type in ('byproducts', 'components'):
            for line in report_lines.get(line_type, []):
                line_product = self.env['product.product'].browse(line.get('prod_id', False))
                line_product_uom_qty = line.get('prod_qty', 0.0)
                line_product_uom = self.env['uom.uom'].browse(line.get('prod_uom_id', False))
                product_qty = line_product_uom._compute_quantity(line_product_uom_qty, line_product.uom_id)

                total_cost = line.get('total', 0.0)

                if not line.get('child_bom'):
                    cost_values += [(0, 0, {
                        parent_field: parent.id,
                        'name': line_product.display_name,
                        'qty': line_product_uom_qty,
                        'product_qty': product_qty,
                        'uom_name': line_product_uom.display_name,
                        'total_cost': total_cost,
                        'type': line_type == 'byproducts' and 'byproduct' or 'component',
                        'level': level + 1,
                        'product_id': line.get('prod_id', False),
                    })]
                else:
                    cost_values += self.browse(line['child_bom'])._get_estimated_cost(
                        line_product, line_product_uom_qty, line_product_uom, parent, parent_field, level=level+1, skip=parent._name == 'mrp.plan')
        
        labors = []
        for line in report_lines.get('operations', []):
            cost_values += [(0, 0, {
                parent_field: parent.id,
                'name': line.get('name', ''),
                'qty': line.get('duration_expected', 0.0),
                'product_qty': line.get('duration_expected', 0.0),
                'uom_name': 'Minutes',
                'total_cost': line.get('total', 0.0),
                'type': 'overhead',
                'level': level + 1,
                'operation_id': line.get('operation_id', False)
            })]
            labors += line.get('labors', [])

        for labor in labors:
            cost_values += [(0, 0, {
                parent_field: parent.id,
                'name': labor.get('name', ''),
                'qty': labor.get('duration_expected', 0.0),
                'product_qty': labor.get('duration_expected', 0.0),
                'uom_name': 'Minutes',
                'total_cost': labor.get('total', 0.0),
                'type': 'labor',
                'level': level + 1,
                'operation_id': labor.get('operation_id', False),
                'user_id': labor.get('user_id', False)
            })]
        
        return cost_values

    def _get_material_cost(self, **kwargs):
        self.ensure_one()
        if kwargs.get('bom_qty') is None:
            kwargs['bom_qty'] = self.product_qty
        if kwargs.get('bom_uom') is None:
            kwargs['bom_uom'] = self.product_uom_id

        material_moves = kwargs.get('material_moves', self.env['stock.move'])

        lines = {}
        for bom_line in self.bom_line_ids:
            values = bom_line._get_cost(bom_qty=kwargs['bom_qty'], bom_uom=kwargs['bom_uom'])
            values['moves'] = material_moves.filtered(lambda o: o.bom_line_id == bom_line)
            lines[str(bom_line.id)] = values
        return dict(kwargs, total=sum(o['cost'] for o in lines.values()), lines=lines)

    def _get_byproduct_cost(self, **kwargs):
        if kwargs.get('bom_qty') is None:
            kwargs['bom_qty'] = self.product_qty
        if kwargs.get('bom_uom') is None:
            kwargs['bom_uom'] = self.product_uom_id

        material_moves = kwargs.get('material_moves', self.env['stock.move'])
        byproduct_moves = kwargs.get('byproduct_moves', self.env['stock.move'])

        if kwargs.get('material_cost') is None:
            kwargs['material_cost'] = self._get_material_cost(bom_qty=kwargs['bom_qty'], bom_uom=kwargs['bom_uom'], material_moves=material_moves)
        lines = {}
        for byproduct in self.byproduct_ids:
            values = byproduct._get_cost(bom_qty=kwargs['bom_qty'], bom_uom=kwargs['bom_uom'], material_cost=kwargs['material_cost'])
            values['moves'] = byproduct_moves.filtered(lambda o: o.byproduct_id == byproduct).ids
            lines[str(byproduct.id)] = values
        return dict(kwargs, total=sum(o['cost'] for o in lines.values()), lines=lines)

    def _get_finished_cost(self, **kwargs):
        if kwargs.get('bom_qty') is None:
            kwargs['bom_qty'] = self.product_qty
        if kwargs.get('bom_uom') is None:
            kwargs['bom_uom'] = self.product_uom_id

        material_moves = kwargs.get('material_moves', self.env['stock.move'])
        byproduct_moves = kwargs.get('byproduct_moves', self.env['stock.move'])
        finished_moves = kwargs.get('finished_moves', self.env['stock.move'])

        if kwargs.get('material_cost') is None:
            kwargs['material_cost'] = self._get_material_cost(bom_qty=kwargs['bom_qty'], bom_uom=kwargs['bom_uom'], material_moves=material_moves)
        if kwargs.get('byproduct_cost') is None:
            kwargs['byproduct_cost'] = self._get_byproduct_cost(bom_qty=kwargs['bom_qty'], bom_uom=kwargs['bom_uom'], material_cost=kwargs['material_cost'], byproduct_moves=byproduct_moves)
        
        lines = {}
        for finished in self.finished_ids:
            values = finished._get_cost(bom_qty=kwargs['bom_qty'], bom_uom=kwargs['bom_uom'], material_cost=kwargs['material_cost'], byproduct_cost=kwargs['byproduct_cost'])
            values['moves'] = finished_moves.filtered(lambda o: o.finished_id == finished).ids
            lines[str(finished.id)] = values
        return dict(kwargs, total=sum(o['cost'] for o in lines.values()), lines=lines)


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    cost = fields.Float(string='Cost', compute='_compute_cost', store=False)

    @api.depends('product_id', 'product_uom_id', 'product_qty', 'child_bom_id', 'operation_id', 'bom_id', 'bom_id.equip_bom_type')
    def _compute_cost(self):
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

        mrp_bom_lines = self.filtered(lambda o: o.bom_id.equip_bom_type == 'mrp')
        for bom_line in mrp_bom_lines:
            company = bom_line.bom_id.company_id or self.env.company
            currency = company.currency_id
            product = bom_line.product_id.with_company(company)

            line_quantity = bom_line.product_qty
            if bom_line.child_bom_id:
                factor = safe_div(
                    bom_line.product_uom_id._compute_quantity(line_quantity, bom_line.child_bom_id.product_uom_id),
                    bom_line.child_bom_id.product_qty)
                sub_total = bom_line.bom_id._get_price(bom_line.child_bom_id, factor, product)
            else:
                if is_cost_per_warehouse:
                    product_price = 0.0
                    if bom_line.operation_id:
                        product_price = product.with_context(price_for_warehouse=bom_line.operation_id._get_workcenter().location_id.get_warehouse().id).standard_price
                else:
                    product_price = product.standard_price
                
                sub_total = 0.0
                if bom_line.product_uom_id and product.uom_id:
                    sub_total = product.uom_id._compute_price(product_price, bom_line.product_uom_id) * line_quantity
            
            sub_total = currency.round(sub_total)
            bom_line.cost = sub_total

        (self - mrp_bom_lines).cost = 0.0

    def _get_cost(self, bom_qty=None, bom_uom=None, qty=None, uom=None, move=None):
        self.ensure_one()
        bom = self.bom_id
        company_id = bom.company_id

        if bom_qty is None:
            bom_qty = bom.product_qty
        if bom_uom is None:
            bom_uom = bom.product_uom_id
        
        if qty is None:
            qty = self.product_qty
        if uom is None:
            uom = self.product_uom_id

        product_id = self.product_id
        factor = bom_uom._compute_quantity(bom_qty, bom.product_uom_id) / bom.product_qty
        product_qty = self.product_uom_id._compute_quantity(uom._compute_quantity(qty, self.product_uom_id) * factor, product_id.uom_id)
        
        if move and move.state == 'done':
            unit_cost = abs(sum(move.stock_valuation_layer_ids.mapped('value')) / sum(move.stock_valuation_layer_ids.mapped('quantity')))
            cost = unit_cost * sum(move.stock_valuation_layer_ids.mapped('quantity'))
        elif move and move.state == 'cancel':
            unit_cost = 0.0
            cost = 0.0
        else:
            is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))
            product = product_id.with_company(company_id)
            if is_cost_per_warehouse and self.operation_id:
                product = product.with_context(price_for_warehouse=self.operation_id._get_workcenter().location_id.get_warehouse().id)
            
            unit_cost = product.standard_price
            cost = unit_cost * product_qty
        
        return {'unit_cost': unit_cost, 'cost': cost, 'quantity': product_qty}


class MrpBomByproduct(models.Model):
    _inherit = 'mrp.bom.byproduct'

    allocated_cost = fields.Float(string='Allocated Cost (%)', digits=0)
    cost = fields.Float(string='Cost', compute='_compute_cost', store=False)

    @api.depends('bom_id', 'bom_id.equip_bom_type', 'bom_id.bom_line_ids', 'bom_id.bom_line_ids.cost', 'allocated_cost')
    def _compute_cost(self):
        mrp_byproducts = self.filtered(lambda o: o.bom_id.equip_bom_type == 'mrp')
        for byproduct in mrp_byproducts:
            bom = byproduct.bom_id
            material_cost = sum(bom.bom_line_ids.mapped('cost'))
            byproduct.cost = (material_cost * byproduct.allocated_cost) / 100

        (self - mrp_byproducts).cost = 0.0

    @api.model
    def _fields_to_dump(self):
        return super(MrpBomByproduct, self)._fields_to_dump() + ['allocated_cost']

    def _get_cost(self, bom_qty=None, bom_uom=None, material_cost=None, qty=None, uom=None, allocated=None):
        self.ensure_one()
        bom = self.bom_id

        if bom_qty is None:
            bom_qty = bom.product_qty
        if bom_uom is None:
            bom_uom = bom.product_uom_id
        if material_cost is None:
            material_cost = bom._get_material_cost(bom_qty=bom_qty, bom_uom=bom_uom)

        if qty is None:
            qty = self.product_qty
        if uom is None:
            uom = self.product_uom_id
        if allocated is None:
            allocated = self.allocated_cost

        cost = (allocated * material_cost['total']) / 100
        factor = bom_uom._compute_quantity(bom_qty, bom.product_uom_id) / bom.product_qty
        product_qty = uom._compute_quantity(qty, self.product_uom_id) * factor
        unit_cost = cost / product_qty
        return {'unit_cost': unit_cost, 'cost': cost, 'quantity': product_qty}


class MrpBomFinished(models.Model):
    _inherit = 'mrp.bom.finished'

    allocated_cost = fields.Float(string='Cost Allocation (%)', digits=0)

    @api.constrains('allocated_cost')
    def _check_allocated_cost(self):
        for record in self:
            if not 0.0 < record.allocated_cost <= 100:
                raise ValidationError(_('Cost allocation must be positive and <= 100.0!'))

    @api.model
    def _fields_to_dump(self):
        return super(MrpBomFinished, self)._fields_to_dump() + ['allocated_cost']

    def _get_cost(self, bom_qty=None, bom_uom=None, material_cost=None, byproduct_cost=None, qty=None, uom=None, allocated=None):
        self.ensure_one()
        bom = self.bom_id

        if bom_qty is None:
            bom_qty = bom.product_qty
        if bom_uom is None:
            bom_uom = bom.product_uom_id
        if material_cost is None:
            material_cost = bom._get_material_cost(bom_qty=bom_qty, bom_uom=bom_uom)
        if byproduct_cost is None:
            byproduct_cost = bom._get_byproduct_cost(bom_qty=bom_qty, bom_uom=bom_uom, material_cost=material_cost['total'])

        if qty is None:
            qty = self.product_qty
        if uom is None:
            uom = self.product_uom_id
        if allocated is None:
            allocated = self.allocated_cost

        cost = (allocated * (material_cost['total'] - byproduct_cost['total'])) / 100
        factor = bom_uom._compute_quantity(bom_qty, bom.product_uom_id) / bom.product_qty
        product_qty = uom._compute_quantity(qty, self.product_uom_id) * factor
        unit_cost = cost / product_qty
        return {'unit_cost': unit_cost, 'cost': cost, 'quantity': product_qty}
