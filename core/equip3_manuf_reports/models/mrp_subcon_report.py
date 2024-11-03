from odoo import models, fields, api, tools
from odoo.tools import float_is_zero


class MrpSubcontractingReport(models.Model):
    _name = 'mrp.subcontracting.report'
    _description = 'MRP Subcontracting Report'
    _auto = False

    @api.depends('company_id', 'location_id', 'owner_id', 'product_id', 'quantity')
    def _compute_value(self):
        for quant in self:
            if not quant.location_id:
                quant.value = 0
                return

            if not quant.location_id._should_be_valued() or\
                    (quant.owner_id and quant.owner_id != quant.company_id.partner_id):
                quant.value = 0
                continue
            if quant.product_id.cost_method == 'fifo':
                quantity = quant.product_id.quantity_svl
                if float_is_zero(quantity, precision_rounding=quant.product_id.uom_id.rounding):
                    quant.value = 0.0
                    continue
                average_cost = quant.product_id.with_company(quant.company_id).value_svl / quantity
                quant.value = quant.quantity * average_cost
            else:
                quant.value = quant.quantity * quant.product_id.with_company(quant.company_id).standard_price

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if 'value' not in fields:
            return super(MrpSubcontractingReport, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        res = super(MrpSubcontractingReport, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        for group in res:
            if group.get('__domain'):
                quants = self.search(group['__domain'])
                group['value'] = sum(quant.value for quant in quants)
        return res

    product_id = fields.Many2one('product.product', string='Product')
    location_id = fields.Many2one('stock.location', string='Location')
    partner_id = fields.Many2one('res.partner', string='Vendor')
    lot_id = fields.Many2one('stock.production.lot', string='Lot/Serial Number')
    package_id = fields.Many2one('stock.quant.package', string='Package')
    owner_id = fields.Many2one('res.partner', string='Owner')
    quantity = fields.Float(string='On Hand Quantity', digits='Product Unit of Measure')
    available_quantity = fields.Float(string='Available Quantity', digits='Product Unit of Measure')
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    value = fields.Monetary(string='Value', compute=_compute_value)
    company_id = fields.Many2one('res.company', string='Company')
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute('''
            CREATE or REPLACE VIEW %s AS (
                SELECT
                    sq.id as id,
                    sml.product_id as product_id,
                    sq.location_id as location_id,
                    po.partner_id as partner_id,
                    sml.lot_id as lot_id,
                    sml.package_id as package_id,
                    sml.owner_id as owner_id,
                    sml.product_uom_id as product_uom_id,
                    sml.company_id as company_id,
                    SUM(sq.quantity) as quantity,
                    SUM(sq.quantity) - SUM(sq.reserved_quantity) as available_quantity
                FROM
                    stock_move_line sml
                JOIN stock_move sm ON sm.id = sml.move_id
                JOIN purchase_order po ON po.subcon_production_id = sm.production_id or po.subcon_production_id = sm.raw_material_production_id
                LEFT JOIN stock_quant sq ON sq.product_id = sml.product_id
                GROUP BY
                    sq.id, 
                    sml.product_id, 
                    sq.location_id, 
                    po.partner_id, 
                    sml.lot_id, 
                    sml.package_id, 
                    sml.owner_id, 
                    sml.product_uom_id, 
                    sml.company_id
            )
        ''' % (self._table,)
        )
