from odoo import models, fields, api


class ReportKitchenProduction(models.AbstractModel):
    _name = 'report.equip3_kitchen_reports.report_kitchen_production'
    _description = 'Kitchen Structure Report'

    @api.model
    def get_html(self, rec_id=False):
        res = self._get_report_data(rec_id=rec_id)
        res['lines']['report_type'] = 'html'
        res['lines']['report_structure'] = 'all'
        res['lines'] = self.env.ref('equip3_kitchen_reports.report_equip3_kitchen')._render({'data': res['lines']})
        return res

    @api.model
    def _get_report_data(self, rec_id):
        lines = {}
        lines = self._get_kitchen_rec(rec_id)
        return {
            'lines': lines,
        }

    def _get_kitchen_rec(self, rec_id=False):
        kitchen_obj = self.env['kitchen.production.record'].browse(rec_id)
        lines = {
            'kitchen': kitchen_obj,
            'kitchen_prod_name': kitchen_obj.product_tmpl_id.display_name,
            'product': kitchen_obj.product_tmpl_id,
            'product_qty': kitchen_obj.product_qty,
            'name': kitchen_obj and kitchen_obj.display_name or '',
        }
        components = self._get_kitchen_lines(kitchen_obj)
        finished_goods, total = self._get_kitchen_finished_good_lines(kitchen_obj)
        lines['components'] = components
        lines['finished_goods'] = finished_goods
        lines['total'] = total
        return lines

    def _get_kitchen_lines(self, kitchen):
        components = []
        stock_ids = self.env['stock.valuation.layer'].search(
            [('id', 'in', kitchen.move_raw_ids.stock_valuation_layer_ids.ids)])
        for value in stock_ids:
            components.append({
                'product_id': value.product_id.id,
                'product_name': value.product_id.display_name,
                'product_consumed_qty': abs(value.quantity),
                'total_value': abs(value.value)
            })
        return components

    def _get_kitchen_finished_good_lines(self, kitchen):
        finished_good = []
        total = 0
        finished_stock_ids = self.env['stock.valuation.layer'].search(
            [('id', 'in', kitchen.move_finished_ids.stock_valuation_layer_ids.ids)])
        for value in finished_stock_ids:
            finished_good.append({
                'finished_product': value.product_id,
                'finished_product_id': value.product_id.id,
                'finished_product_name': value.product_id.display_name,
                'finished_product_qty': abs(value.quantity),
                'finished_total_value': abs(value.value),
            })
            total += abs(value.value)
        return finished_good, total
