from odoo import models, fields, api


def safe_div(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        return a


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    @api.model
    def _product_tmpl_domain(self):
        if self.env.context.get('default_equip_bom_type', 'mrp') == 'kitchen':
            return """[
                ('type', 'in', ('product', 'consu')),
                '|', ('company_id', '=', False), ('company_id', '=', company_id),
                ('produceable_in_kitchen', '=', True)
            ]"""
        return super(MrpBom, self)._product_tmpl_domain()

    product_tmpl_id = fields.Many2one(domain=_product_tmpl_domain)

    kitchen_forecast_cost = fields.Float(compute='_kitchen_get_bom_cost', store=False)

    @api.depends('product_id', 'product_tmpl_id', 'bom_line_ids', 'bom_line_ids.product_id', 'bom_line_ids.product_qty', 'equip_bom_type')
    def _kitchen_get_bom_cost(self):
        kitchen_boms = self.filtered(lambda o: o.equip_bom_type == 'kitchen')

        for bom in kitchen_boms:
            company = bom.company_id or self.env.company
            bom_quantity = bom.product_qty
            product = bom.product_id or bom.product_tmpl_id.product_variant_id
            total = bom._kitchen_get_bom_lines(bom, bom_quantity, product, False, 1)
            byproduct_total = bom._kitchen_get_byproduct_lines(bom, bom_quantity, product, False, 1, total)
            total -= byproduct_total
            bom.kitchen_forecast_cost = total

        (self - kitchen_boms).kitchen_forecast_cost = 0.0

    def _kitchen_get_bom_lines(self, bom, bom_quantity, product, line_id, level):
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

        components = []
        total = 0
        for line in bom.bom_line_ids:
            line_quantity = safe_div(bom_quantity, bom.product_qty) * line.product_qty
            if line._skip_bom_line(product):
                continue
            company = bom.company_id or self.env.company
            currency = company.currency_id
            product = line.product_id.with_company(company)

            if is_cost_per_warehouse:
                warehouse_prices = product.warehouse_price_ids
                product_price = 0.0
                if warehouse_prices:
                    product_price = sum(warehouse_prices.mapped('standard_price')) / len(warehouse_prices)
            else:
                product_price = product.standard_price
            
            price = product.uom_id._compute_price(product_price, line.product_uom_id) * line_quantity
            if line.child_bom_id:
                factor = safe_div(
                    line.product_uom_id._compute_quantity(line_quantity, line.child_bom_id.product_uom_id),
                    line.child_bom_id.product_qty)
                sub_total = self._kitchen_get_price(line.child_bom_id, factor, product)
            else:
                sub_total = price
            sub_total = currency.round(sub_total)
            total += sub_total
        return total

    def _kitchen_get_byproduct_lines(self, bom, bom_quantity, product, line_id, level, total_material):
        currency = self.env.company.currency_id
        byproduct_total = 0
        for line in bom.byproduct_ids:
            sub_total = currency.round((line.kitchen_allocated_cost * total_material) / 100)
            byproduct_total += sub_total
        return byproduct_total

    def _kitchen_get_price(self, bom, factor, product):
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

        price = 0
        for line in bom.bom_line_ids:
            if line._skip_bom_line(product):
                continue
            company = bom.company_id or self.env.company
            currency = company.currency_id
            product = line.product_id.with_company(company)

            if line.child_bom_id:
                qty = safe_div(
                    line.product_uom_id._compute_quantity(line.product_qty * factor, line.child_bom_id.product_uom_id),
                    line.child_bom_id.product_qty)
                sub_price = self._kitchen_get_price(line.child_bom_id, qty, product)
                price += sub_price
            else:
                if is_cost_per_warehouse:
                    warehouse_prices = product.warehouse_price_ids
                    product_price = 0.0
                    if warehouse_prices:
                        product_price = sum(warehouse_prices.mapped('standard_price')) / len(warehouse_prices)
                else:
                    product_price = product.standard_price

                prod_qty = line.product_qty * factor
                not_rounded_price = product.uom_id._compute_price(product_price, line.product_uom_id) * prod_qty
                price += currency.round(not_rounded_price)
        return price


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    kitchen_cost = fields.Float(string='Kitchen Cost', compute='_compute_kitchen_cost', store=False)

    @api.depends('product_id', 'product_uom_id', 'product_qty', 'child_bom_id', 'bom_id', 'bom_id.equip_bom_type')
    def _compute_kitchen_cost(self):
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

        kitchen_bom_lines = self.filtered(lambda o: o.bom_id.equip_bom_type == 'kitchen')
        for bom_line in kitchen_bom_lines:
            company = bom_line.bom_id.company_id or self.env.company
            currency = company.currency_id
            product = bom_line.product_id.with_company(company)

            line_quantity = bom_line.product_qty
            if bom_line.child_bom_id:
                factor = safe_div(
                    bom_line.product_uom_id._compute_quantity(line_quantity, bom_line.child_bom_id.product_uom_id),
                    bom_line.child_bom_id.product_qty)
                sub_total = bom_line.bom_id._kitchen_get_price(bom_line.child_bom_id, factor, product)
            else:
                if is_cost_per_warehouse:
                    warehouse_prices = product.warehouse_price_ids
                    product_price = 0.0
                    if warehouse_prices:
                        product_price = sum(warehouse_prices.mapped('standard_price')) / len(warehouse_prices)
                else:
                    product_price = product.standard_price

                sub_total = product_price
                if bom_line.product_uom_id and product.uom_id:
                    sub_total = product.uom_id._compute_price(product_price, bom_line.product_uom_id) * line_quantity
            
            sub_total = currency.round(sub_total)
            bom_line.kitchen_cost = sub_total

        (self - kitchen_bom_lines).kitchen_cost = 0.0


class MRPBomByProduct(models.Model):
    _inherit = 'mrp.bom.byproduct'

    kitchen_allocated_cost = fields.Float(string='Kitchen Allocated Cost (%)')
    kitchen_cost = fields.Float(string='Kitchen Cost', compute='_compute_kitchen_cost', store=False)

    @api.depends('bom_id', 'bom_id.equip_bom_type', 'bom_id.bom_line_ids', 'bom_id.bom_line_ids.kitchen_cost', 'kitchen_allocated_cost')
    def _compute_kitchen_cost(self):
        kitchen_byproducts = self.filtered(lambda o: o.bom_id.equip_bom_type == 'kitchen')
        for byproduct in kitchen_byproducts:
            bom = byproduct.bom_id
            material_cost = sum(bom.bom_line_ids.mapped('kitchen_cost'))
            byproduct.kitchen_cost = (material_cost * byproduct.kitchen_allocated_cost) / 100

        (self - kitchen_byproducts).kitchen_cost = 0.0
