# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class StockPickingInherit(models.Model):
    _inherit = "stock.picking"

    base_sync = fields.Boolean("Base Sync", default=False)

    def genreate_sequence(self):
        pickings = self.env["stock.picking"].search([
            ("base_sync", "=", True),
            ("id", "in", self.ids)
        ])
        for picking in pickings:
            if picking.base_sync:
                picking_type = self.env["stock.picking.type"].browse(
                    picking.picking_type_id.id
                )
                picking.name = picking_type.sequence_id.next_by_id()
                picking.base_sync = False

        result = {
            "name": "Delivery Order Resequence",
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "stock.picking",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", pickings.ids)],
            "target": "current",
        }

        return result

    def _remove_stock_picking_name_uniq_constraint(self):
        try:
            self._cr.execute(
                "ALTER TABLE stock_picking DROP CONSTRAINT stock_picking_name_uniq"
            )
            _logger.debug(
                "Remove constrint stock_picking_name_uniq",
            )
        except Exception as e:
            raise ValidationError("Error removing SQL constraint: %s" % str(e))

    def remove_stock_picking_unique_name(self):
        self._remove_stock_picking_name_uniq_constraint()


class StockMoveInherit(models.Model):
    _inherit = "stock.move"

    @api.depends("purchase_request_allocation_ids")
    def _compute_purchase_request_ids(self):
        for rec in self:
            if rec.purchase_request_allocation_ids:
                rec.purchase_request_ids = rec.purchase_request_allocation_ids.mapped(
                    "purchase_request_id"
                )
            else:
                rec.purchase_request_ids = False
