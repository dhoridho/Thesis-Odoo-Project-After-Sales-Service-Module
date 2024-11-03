from odoo import models, fields, api, _
from odoo import tools


class NurseryYieldReport(models.Model):
    _name = 'nursery.yield.report'
    _description = 'Nursery Yield Report'
    _auto = False

    activity_record_id = fields.Many2one('agriculture.daily.activity.record', string='Plantation Record')
    block_id = fields.Many2one('crop.block', string='Nursery Area')
    product_id = fields.Many2one('product.product', string='Crop')
    lot_id = fields.Many2one('stock.production.lot', string='Lot/Serial Number') 
    initial_qty = fields.Float(digits='Product Unit of Measure', string='Initial Quantity')
    counted_qty = fields.Float(digits='Product Unit of Measure', string='Counted Quantity')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    gemination_rate = fields.Float(string='Gemination Rate', group_operator='avg')

    @api.model
    def _query(self):
        return """SELECT
            dan.id,
            dan.activity_record_id,
            dan.block_id,
            dan.product_id,
            dan.lot_id,
            dan.current_qty AS initial_qty,
            dan.count AS counted_qty,
            dan.uom_id,
            (dan.count / ((coalesce(icp_max.value, '100')::numeric * dan.current_qty) / 100)) * 100 AS gemination_rate
        FROM
            (SELECT
                *,
                'equip3_agri_reports.agri_yield_minimum_target' AS min_key,
                'equip3_agri_reports.agri_yield_maximum_target' AS max_key
            FROM 
                agriculture_daily_activity_nursery
            ) dan
        LEFT JOIN
            agriculture_daily_activity_record dar
            ON (dar.id = dan.activity_record_id)
        LEFT JOIN
            crop_activity ca
            ON (ca.id = dar.activity_id)
        LEFT JOIN
            crop_activity_type cat
            ON (cat.id = ca.type_id)
        LEFT JOIN
            ir_config_parameter icp_min
            ON (icp_min.key = dan.min_key)
        LEFT JOIN
            ir_config_parameter icp_max
            ON (icp_max.key = dan.max_key)
        WHERE
            cat.value = 'crop_adjustment'
        """

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))