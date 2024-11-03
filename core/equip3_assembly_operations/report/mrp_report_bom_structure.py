from odoo import models, api
from odoo.tools import float_round


class MrpReportBomStructure(models.AbstractModel):
    _inherit = 'report.mrp.report_bom_structure'

    def _get_bom_lines(self, bom, bom_quantity, product, line_id, level):
        if bom.equip_bom_type != 'assembly':
            return super(MrpReportBomStructure, self)._get_bom_lines(bom, bom_quantity, product, line_id, level)
        
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

        components = []
        total = 0
        for line in bom.bom_line_ids:
            line_quantity = (bom_quantity / (bom.product_qty or 1.0)) * line.product_qty
            if line._skip_bom_line(product):
                continue
            company = bom.company_id or self.env.company
            currency = company.currency_id
            product = line.product_id.with_company(company)

            if line.child_bom_id:
                report = self._get_report_data(line.child_bom_id.id, searchQty=line.product_uom_id._compute_quantity(line_quantity, line.child_bom_id.product_uom_id))
                report_lines = report.get('lines', {})
                price = report_lines.get('price', 0.0)
                sub_total = report_lines.get('total', 0.0)
            else:
                if is_cost_per_warehouse:
                    warehouse_prices = product.warehouse_price_ids
                    product_price = 0.0
                    if warehouse_prices:
                        product_price = sum(warehouse_prices.mapped('standard_price')) / len(warehouse_prices)
                else:
                    product_price = product.standard_price
                    
                price = product.uom_id._compute_price(product_price, line.product_uom_id)
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
