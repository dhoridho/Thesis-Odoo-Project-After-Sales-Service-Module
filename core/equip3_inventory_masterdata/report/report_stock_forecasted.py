from odoo import models, api, fields


class ReplenishmentReport(models.AbstractModel):
    _name = 'report.equip3_inventory_masterdata.report_product_forecast'
    _description = "Equip Stock Replenishment Report"
    _inherit = 'report.stock.report_product_product_replenishment'

    def _get_report_data(self, product_template_ids=False, product_variant_ids=False):
        res = super(ReplenishmentReport, self)._get_report_data(product_template_ids=product_template_ids, product_variant_ids=product_variant_ids)
        if product_template_ids:
            product_templates = self.env['product.template'].browse(product_template_ids)
            set_uoms = product_templates.mapped('uom_id')
            if len(set_uoms) > 1:
                res['uom'] = ''
        elif product_variant_ids:
            product_variants = self.env['product.product'].browse(product_variant_ids)
            set_uoms = product_variants.mapped('uom_id')
            if len(set_uoms) > 1:
                res['uom'] = ''
        return res

    @api.model
    def get_report_values_public(self, docids, data=None):
        if not data:
            data = dict()
        context = self.env.context.copy()
        context.update(data.get('context', {}))
        self = self.with_context(context)
        result = self._get_report_values(docids, data=data)
        for line in result.get('docs', {}).get('lines', []):
            move_in = line['move_in']
            move_out = line['move_out']

            move_in_qty = False
            if move_in:
                move_in_qty = move_in.product_uom._compute_quantity(move_in.product_uom_qty, move_in.product_id.uom_id)

            move_out_qty = False
            if move_out:
                move_out_qty = move_out.product_uom._compute_quantity(move_out.product_uom_qty, move_out.product_id.uom_id)
            line['move_in_qty'] = move_in_qty
            line['move_out_qty'] = move_out_qty
        return result


class ReplenishmentTemplateReport(models.AbstractModel):
    _name = 'report.equip3_inventory_masterdata.report_product_tmpl_forecast'
    _description = "Equip Stock Replenishment Report"
    _inherit = 'report.equip3_inventory_masterdata.report_product_forecast'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'data': data,
            'doc_ids': docids,
            'doc_model': 'product.product',
            'docs': self._get_report_data(product_template_ids=docids),
        }
