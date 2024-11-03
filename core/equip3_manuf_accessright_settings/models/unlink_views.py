import json
from odoo import models, api
from psycopg2.errors import UndefinedColumn, UndefinedTable


views_to_delete = [
    ('view.order.form.mrp.view', 'sale.order', "sales_to_manufacturing"),
    ('res.config.settings.view.form.inherit.sales.to.manuf', 'res.config.settings', "sales_to_manufacturing"),
    ('res.config.settings.sales.to.manufacturing', 'res.config.settings', "sales_to_manufacturing"),
    ('view.order.form.mrp.view', 'sale.order', "manuf_auto_create"),
    ('product.template.sales.to.manufacturing.view', 'product.template', "manuf_auto_create"),
    ('view.purchase.request.form.inherited', 'purchase.request', "is_purchase_order"),
    ('view.mrp.plan.form', 'mrp.plan', "//field[@name='stock_valuation_layer_ids']/tree"),
    ('view.mrp.production.form', 'mrp.production', "//field[@name='stock_valuation_layer_ids']/tree"),
    ('mrp.consumption.form.subcontracting', 'mrp.consumption', "//field[@name='stock_valuation_layer_ids']/tree"),
    ('mrp.production.workorder.form.view.inherit.oop', 'mrp.workorder', "//field[@name='stock_valuation_layer_ids']/tree"),
    ('view.purchase.requisition.form', 'purchase.requisition', "is_a_subcontracting"),
    ('purchase.request.form.inherit', 'purchase.request', "is_a_subcontracting"),
    ('mrp.production.workorder.form.view.inherit', 'mrp.workorder', "is_a_subcontracting"),
    ('stock.picking.form.inherit.subcon', 'stock.picking', "is_a_subcontracting"),
    ('mrp.workorder.tree.editable.view.inherit.oop', 'mrp.workorder', "is_a_subcontracting"),
    ('mrp.consumption.form.subcontracting', 'mrp.consumption', "is_a_subcontracting"),
    ('sh.po.form.for.pmps.adv', 'purchase.order', "is_a_subcontracting"),
    ('mrp.production pivot', 'mrp.production', "total_subcontracting"),
    ('view.mining.cost.actualization.form', 'mining.cost.actualization', "total_subcontracting"),
    ('stock.valuation.layer.form.inherit', 'stock.valuation.layer', "total_subcontracting"),
    ('view.mrp.cost.actualization.form', 'mrp.cost.actualization', "total_subcontracting"),
    ('reuse.mrp.production.tree', 'mrp.production', "total_subcontracting"),
    ('product.template.only.form.view', 'product.template', "secret_name"),
    ('res.config.settings.view.form.purchase.inherit.exp.date', 'res.config.settings', "is_good_services_order"),
    ('res.config.settings.form', 'res.config.settings', "is_good_services_order"),
    ('res.config.settings.view.form.purchase.inherit.exp.date.po', 'res.config.settings', "is_good_services_order"),
    ('res.config.settings.implementor.form.inherit.base.setup', 'res.config.settings', "is_good_services_order"),
    ('view.stock.quant.tree.editable.manuf', 'stock.quant', "production_ref"),
    ('view.stock.quant.tree.manuf', 'stock.quant', "production_ref"),
    ('mrp_bom_form_view', 'mrp.bom', "subcontracting_product_id"),
    ('view.form.internal.transfer', 'internal.transfer', "is_mrp_transfer_request"),
    ('view.form.internal.transfer', 'internal.transfer', "is_mrp_transfer_back")
]


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    @api.model
    def _delete_mrp_views(self):
        View = self.env['ir.ui.view'].sudo()

        def _unlink(view_id):
            for child in View.search([('inherit_id', '=', view_id.id)]):
                _unlink(child)
            view_id.unlink()
            
        for name, model, substr in views_to_delete:
            view_id = View.search([
                ('name', '=', name),
                ('model', '=', model),
                ('arch_db', 'like', substr)
            ])
            if view_id:
                _unlink(view_id)

    @api.model
    def _get_branch_fields(self):
        self = self.sudo()
        to_change = {}
        for model in ['mrp.bom', 'mrp.routing.workcenter', 'mrp.workcenter', 'mrp.plan', 'mrp.production']:
            table = model.replace('.', '_')
            try:
                with self.env.cr.savepoint():
                    self.env.cr.execute('SELECT id, branch FROM %s WHERE branch IS NOT NULL' % table)
                    to_change[table] = self.env.cr.dictfetchall()
            except (UndefinedColumn, UndefinedTable):
                continue

        ir_config = self.env['ir.config_parameter'].sudo()
        ir_config.set_param('mrp_records_to_map', json.dumps(to_change, default=str))

    @api.model
    def _map_branch_fields(self):
        self = self.sudo()
        ir_config = self.env['ir.config_parameter'].sudo()
        table_records = json.loads(ir_config.get_param('mrp_records_to_map', '{}'))

        if not table_records:
            return
        
        for table, records in table_records.items():

            branch_records = {}
            for record in records:
                if record['branch'] not in branch_records:
                    branch_records[record['branch']] = [record['id']]
                else:
                    branch_records[record['branch']] += [record['id']]

            if not branch_records:
                continue

            case_clause = ['CASE']
            all_record_ids = []
            for branch_id, record_ids in branch_records.items():
                record_ids_str = ','.join([str(rid) for rid in record_ids])
                case_clause += ['WHEN id IN (%s) THEN %s' % (record_ids_str, branch_id)]
                all_record_ids += record_ids
            case_clause += ['END']
            case_clause = ' '.join(case_clause)

            all_record_ids_str = ','.join([str(rid) for rid in all_record_ids])
            where_clause = 'WHERE id IN (%s)' % all_record_ids_str

            query = 'UPDATE %s SET branch_id = %s %s' % (table, case_clause, where_clause)
            try:
                with self.env.cr.savepoint():
                    self.env.cr.execute(query)
            except (UndefinedColumn, UndefinedTable):
                continue

        ir_config.set_param('mrp_records_to_map', '{}')

    def _register_hook(self):
        result = super(MrpProduction, self)._register_hook()
        self._map_branch_fields()
        return result
