from odoo import models, fields, api


class ReportAssemblyProduction(models.AbstractModel):
    _name = 'report.equip3_assembly_reports.report_assembly_production'
    _description = 'Assembly Structure Report'

    @api.model
    def get_html(self, rec_id=False):
        res = self._get_report_data(rec_id=rec_id)
        res['lines']['report_type'] = 'html'
        res['lines']['report_structure'] = 'all'
        res['lines'] = self.env.ref('equip3_assembly_reports.report_equip3_assembly')._render({'data': res['lines']})
        return res

    @api.model
    def _get_report_data(self, rec_id):
        lines = {}
        lines = self._get_assembly_rec(rec_id)
        return {
            'lines': lines,
        }

    def _get_assembly_rec(self, rec_id=False):
        assembly_obj = self.env['assembly.production.record'].browse(rec_id)
        lines = {
            'assembly': assembly_obj,
            'record_type': assembly_obj.record_type,
            'assembly_prod_name': assembly_obj.product_tmpl_id.display_name,
            'product': assembly_obj.product_tmpl_id,
            'product_qty': assembly_obj.product_qty,
            'name': assembly_obj and assembly_obj.display_name or '',
        }
        components = self._get_assembly_lines(assembly_obj)
        finished_goods, total = self._get_assembly_finished_good_lines(assembly_obj)
        lines['components'] = components
        lines['finished_goods'] = finished_goods
        lines['total'] = total
        return lines

    def _get_assembly_lines(self, assembly):
        components = []
        stock_ids = self.env['stock.valuation.layer'].search(
            [('id', 'in', assembly.move_raw_ids.stock_valuation_layer_ids.ids)])
        for value in stock_ids:
            components.append({
                'product_id': value.product_id.id,
                'product_name': value.product_id.display_name,
                'product_consumed_qty': abs(value.quantity),
                'total_value': abs(value.value)
            })
        return components

    def _get_assembly_finished_good_lines(self, assembly):
        finished_good = []
        total = 0
        finished_stock_ids = self.env['stock.valuation.layer'].search(
            [('id', 'in', assembly.move_finished_ids.stock_valuation_layer_ids.ids)])
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
