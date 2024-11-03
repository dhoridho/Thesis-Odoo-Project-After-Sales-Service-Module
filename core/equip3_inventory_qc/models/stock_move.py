from odoo import models, fields, api
from odoo.exceptions import ValidationError

class StockMove(models.Model):
    _inherit = 'stock.move'

    remaining_checked_qty = fields.Float(string="Remaining Checked Qty", copy=False)
    recheck_max_number = fields.Integer(string="Maximum Number Of Test")

    @api.onchange('product_id')
    def onchange_product_id(self):
        res = super(StockMove, self).onchange_product_id()
        if self.sh_quality_point_id:
            self.recheck_max_number = self.sh_quality_point_id.number_of_test
        return res

    @api.onchange('product_uom_qty')
    def _onchange_remaining_checked_qty(self):
        for record in self.filtered(lambda r: r.picking_id):
            quality_point_id = self.env['sh.qc.point'].sudo().search([
                ('product_ids', 'in', [record.product_id.id]),
                ('operation_ids', 'in', [record.picking_id.picking_type_id.id]),
                '|',
                ('team.user_ids.id', 'in', [self.env.uid]),
                ('team', '=', False)], limit=1, order='create_date desc')
            record.remaining_checked_qty = record.product_uom_qty if quality_point_id else 0

    def _get_last_check_result(self):

        for rec in self:
            rec.sh_last_qc_date = False
            rec.sh_last_qc_state = ''

            # Filter checks related to the specific product and picking
            check_count = rec.picking_id.sh_quality_check_ids.filtered(
                lambda x: x.product_id.id == rec.product_id.id
            )

            # Fetch the relevant quality point
            quality_point = self.env['sh.qc.point'].sudo().search([
                ('product_ids', 'in', [rec.product_id.id]),
                ('operation_ids', 'in', [rec.picking_id.picking_type_id.id]),
                '|',
                ('team.user_ids.id', 'in', [self.env.uid]),
                ('team', '=', False)
            ], limit=1, order='create_date desc')

            # Determine the number of tests needed
            number_of_test = quality_point.number_of_test if quality_point and quality_point.number_of_test > 0 else 100
            rec.number_of_test = number_of_test - len(check_count)

            # Fetch the last quality check
            last_quality_check = self.env['sh.quality.check'].search([
                ('product_id', '=', rec.product_id.id),
                ('sh_picking', '=', rec.picking_id.id)
            ], limit=1, order='create_date desc')

            if last_quality_check:
                rec.sh_last_qc_date = last_quality_check.create_date
                rec.sh_last_qc_state = last_quality_check.state
