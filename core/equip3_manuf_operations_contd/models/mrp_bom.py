from odoo import models, fields, api
from lxml import etree


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    is_locked = fields.Boolean(default='_is_locked', compute='_compute_is_locked')

    def _compute_is_locked(self):
        self.is_locked = self._is_locked()

    @api.model
    def _is_locked(self):
        return self.env.user.has_group('mrp.group_locked_by_default')

    @api.model
    def _fields_to_dump(self):
        return [
            'product_tmpl_id',
            'product_id',
            'product_qty',
            'product_uom_id',
            'bom_line_ids',
            'byproduct_ids',
            'operation_ids',
            'finished_ids'
        ]


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    @api.model
    def _fields_to_dump(self):
        return [
            'product_id',
            'product_qty',
            'product_uom_id',
            'operation_id'
        ]


class MrpBomByproduct(models.Model):
    _inherit = 'mrp.bom.byproduct'

    @api.model
    def _fields_to_dump(self):
        return [
            'product_id',
            'product_qty',
            'product_uom_id',
            'operation_id'
        ]


class MrpBomFinished(models.Model):
    _inherit = 'mrp.bom.finished'

    @api.model
    def _fields_to_dump(self):
        return [
            'product_id',
            'product_qty',
            'product_uom_id',
            'is_mandatory'
        ]
