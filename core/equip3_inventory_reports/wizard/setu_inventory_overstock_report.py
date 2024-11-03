from odoo import _, api, fields, models


class SetuInventoryOverstockReport(models.TransientModel):
    _inherit = 'setu.inventory.overstock.report'

    def get_overstock_report_data(self):
        res_list = super(SetuInventoryOverstockReport, self).get_overstock_report_data()
        
        if isinstance(res_list, list):
            is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param(
                'equip3_inventory_base.is_cost_per_warehouse', 'False'))

            if is_cost_per_warehouse:
                warehouse_prices = self.env['product.warehouse.price'].sudo()
                
                for res in res_list:
                    warehouse_id = res.get('warehouse_id')
                    if warehouse_id:
                        price = warehouse_prices.search([
                            ('company_id', '=', self.env.company.id),
                            ('warehouse_id', '=', warehouse_id),
                            ('product_id', '=', res.get('product_id'))
                        ], limit=1).standard_price

                        if price:
                            overstock_value = price * res.get('overstock_qty', 0)
                            res['overstock_value'] = overstock_value
        return res_list

