# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields


class Purchase(models.Model):
    _inherit = 'purchase.order'

    def _compute_access_url(self):
        super(Purchase, self)._compute_access_url()
        for order in self:
            if order.state in ['draft', 'sent']:
                order.access_url = '/my/rfq/%s' % (order.id)
            else:
                order.access_url = '/my/purchase/%s' % (order.id)

    def _get_report_base_filename(self):
        self.ensure_one()
        return '%s %s' % ('Purchase', self.name)

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    sh_tender_note = fields.Char('Note/Comment')
