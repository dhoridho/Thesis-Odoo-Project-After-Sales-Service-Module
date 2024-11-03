from odoo import models, api
from odoo.tools import float_round


def safe_div(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        return a


class MrpReportBomStructure(models.AbstractModel):
    _inherit = 'report.mrp.report_bom_structure'

    @api.model
    def _get_bom(self, bom_id=False, product_id=False, line_qty=False, line_id=False, level=False):
        bom = self.env['mrp.bom'].browse(bom_id)
        bom_quantity = line_qty
        if product_id:
            product = self.env['product.product'].browse(int(product_id))
        else:
            product = bom.product_id or bom.product_tmpl_id.product_variant_id
        data = super(MrpReportBomStructure, self)._get_bom(bom_id=bom_id, product_id=product_id, line_qty=line_qty, line_id=line_id, level=level)
        byproducts, byproduct_total = self._get_byproduct_lines(bom, bom_quantity, product, line_id, level, data['total'])

        labors = []
        for operation in data.get('operations', []):
            labors += operation.get('labors', [])
        labors_total = sum([labor['total'] for labor in labors])
        labors_time = sum([labor['duration_expected'] for labor in labors])

        data.update({
            'byproducts': byproducts,
            'labors': labors,
            'labors_cost': labors_total,
            'labors_time': labors_time,
            'total': data['total'] - byproduct_total + labors_total,

        })
        return data

    def _get_byproduct_lines(self, bom, bom_quantity, product, line_id, level, total_material):
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

        last_operation = bom.operation_ids and bom.operation_ids[-1] or self.env['mrp.routing.workcenter']

        byproducts = []
        byproduct_total = 0
        for line in bom.byproduct_ids:
            line_quantity = safe_div(bom_quantity, bom.product_qty) * line.product_qty
            company = bom.company_id or self.env.company
            product = line.product_id.with_company(company)
            if is_cost_per_warehouse:
                product = product.with_context(price_for_warehouse=last_operation._get_workcenter().location_byproduct_id.get_warehouse().id)

            sub_total = self.env.company.currency_id.round((line.allocated_cost * total_material) / 100)
            byproducts.append({
                'prod_id': product.id,
                'prod_name': product.display_name,
                'prod_qty': line_quantity,
                'prod_uom_id': line.product_uom_id.id,
                'prod_uom': line.product_uom_id.name,
                'prod_cost': company.currency_id.round(product.standard_price),
                'parent_id': bom.id,
                'line_id': line.id,
                'level': level or 0,
                'total': sub_total,
            })
            byproduct_total += sub_total
        return byproducts, byproduct_total

    def _get_labor_lines(self, bom, qty):
        labors = []
        for operation in bom.operation_ids:
            workcenter_id = operation._get_workcenter()
            operation_cycle = float_round(safe_div(qty, workcenter_id.capacity), precision_rounding=1, rounding_method='UP')
            duration_expected = operation_cycle * operation.time_cycle + workcenter_id.time_stop + workcenter_id.time_start
            for labor in workcenter_id.labor_ids:
                total = ((duration_expected / 60.0) * labor.costs_per_hour)
                labors.append({
                    'name': labor.user_id.display_name,
                    'duration_expected': duration_expected,
                    'total': self.env.company.currency_id.round(total),
                })
        return labors

    def _get_operation_line(self, bom, qty, level):
        operations = []
        total = 0.0
        for operation in bom.operation_ids:
            workcenter_id = operation._get_workcenter()
            operation_cycle = float_round(safe_div(qty, workcenter_id.capacity), precision_rounding=1, rounding_method='UP')
            duration_expected = operation_cycle * operation.time_cycle + workcenter_id.time_stop + workcenter_id.time_start
            total = ((duration_expected / 60.0) * workcenter_id.costs_hour)
            
            labors = []
            for labor in workcenter_id.labor_ids:
                labor_total = ((duration_expected / 60.0) * labor.cost_per_hour)
                labors += [{
                    'level': level or 0,
                    'operation_id': operation.id,
                    'user_id': labor.user_id.id,
                    'labor': labor,
                    'name': 'Labor - %s: %s' % (labor.user_id.display_name, operation.name),
                    'labor_name': labor.user_id.display_name,
                    'duration_expected': duration_expected,
                    'total': self.env.company.currency_id.round(labor_total),
                }]
            
            operations.append({
                'level': level or 0,
                'operation': operation,
                'operation_id': operation.id,
                'operation_name': operation.display_name,
                'name': '%s - %s' % (operation.name, workcenter_id.name),
                'duration_expected': duration_expected,
                'total': self.env.company.currency_id.round(total),
                'labors': labors
            })
        return operations

    def _get_bom_lines(self, bom, bom_quantity, product, line_id, level):
        if bom.equip_bom_type != 'mrp':
            return super(MrpReportBomStructure, self)._get_bom_lines(bom, bom_quantity, product, line_id, level)
        
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

        components = []
        total = 0
        for line in bom.bom_line_ids:
            line_quantity = (bom_quantity / (bom.product_qty or 1.0)) * line.product_qty
            if line._skip_bom_line(product):
                continue
            company = bom.company_id or self.env.company
            product = line.product_id.with_company(company)
            if is_cost_per_warehouse and line.operation_id:
                product = product.with_context(price_for_warehouse=line.operation_id._get_workcenter().location_id.get_warehouse().id)
            if line.child_bom_id:
                report = self._get_report_data(line.child_bom_id.id, searchQty=line.product_uom_id._compute_quantity(line_quantity, line.child_bom_id.product_uom_id))
                report_lines = report.get('lines', {})
                price = report_lines.get('price', 0.0)
                sub_total = report_lines.get('total', 0.0)
            else:
                price = product.uom_id._compute_price(product.standard_price, line.product_uom_id)
                sub_total = price * line_quantity
            
            sub_total = self.env.company.currency_id.round(sub_total)
            components.append({
                'prod_id': product.id,
                'prod_name': product.display_name,
                'code': line.child_bom_id and line.child_bom_id.display_name or '',
                'prod_qty': line_quantity,
                'prod_uom': line.product_uom_id.name,
                'prod_uom_id': line.product_uom_id.id,
                'prod_cost': company.currency_id.round(price),
                'parent_id': bom.id,
                'line_id': line.id,
                'level': level or 0,
                'total': sub_total,
                'child_bom': line.child_bom_id.id,
                'phantom_bom': line.child_bom_id and line.child_bom_id.type == 'phantom' or False,
                'attachments': self.env['mrp.document'].search(['|', '&',
                    ('res_model', '=', 'product.product'), ('res_id', '=', product.id), '&', ('res_model', '=', 'product.template'), ('res_id', '=', product.product_tmpl_id.id)]),

            })
            total += sub_total
        return components, total

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
            price += sum([op['total'] for op in operations])

        for line in bom.bom_line_ids:
            if line._skip_bom_line(product):
                continue
            company = bom.company_id or self.env.company
            product = line.product_id.with_company(company)
            if is_cost_per_warehouse and line.operation_id:
                product = product.with_context(price_for_warehouse=line.operation_id._get_workcenter().location_id.get_warehouse().id)
            if line.child_bom_id:
                qty = line.product_uom_id._compute_quantity(line.product_qty * factor, line.child_bom_id.product_uom_id) / line.child_bom_id.product_qty
                sub_price = self._get_price(line.child_bom_id, qty, product)
                price += sub_price
            else:
                prod_qty = line.product_qty * factor
                
                not_rounded_price = product.uom_id._compute_price(product.with_context(force_comany=company.id).standard_price, line.product_uom_id) * prod_qty
                price += company.currency_id.round(not_rounded_price)
        return price

    @api.model
    def get_labors(self, bom_id=False, qty=0, level=0):
        bom = self.env['mrp.bom'].browse(bom_id)
        lines = self._get_operation_line(bom, float_round(qty / bom.product_qty, precision_rounding=1, rounding_method='UP'), level)
        labors = []
        for line in lines:
            labors += line.get('labors', [])
        values = {
            'bom_id': bom_id,
            'currency': self.env.company.currency_id,
            'labors': labors,
        }
        return self.env.ref('equip3_manuf_account.report_mrp_labor_line')._render({'data': values})
