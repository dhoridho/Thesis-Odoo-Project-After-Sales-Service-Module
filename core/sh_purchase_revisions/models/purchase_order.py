# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, _


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    sh_po_number = fields.Integer('PO Number', copy=False, default=1)
    sh_purchase_order_id = fields.Many2one(
        'purchase.order', 'PurchaseOrder', copy=False)
    sh_revision_po_id = fields.Many2many("purchase.order",
                                         relation="purchase_order_revision_order_rel",
                                         column1="po_id",
                                         column2="revision_id",
                                         string="")

    po_count = fields.Integer(
        'Quality Checks', compute='_compute_get_po_count')
    sh_purchase_revision_config = fields.Boolean("Enable Purchase Revisions", related="company_id.sh_purchase_revision")

    def open_quality_check(self):
        po = self.env['purchase.order'].search(
            [('sh_purchase_order_id', '=', self.id)])
        action = self.env.ref(
            'sh_purchase_revisions.sh_action_purchase_order_quotation_revision').read()[0]
        action['context'] = {
            'domain': [('id', 'in', po.ids)]
        }
        action['domain'] = [('id', 'in', po.ids)]
        return action

    def _compute_get_po_count(self):
        if self:
            for rec in self:
                rec.po_count = 0
                # qc = self.env['purchase.order'].search(
                #     [('sh_purchase_order_id', '=', rec.id)])
                self.env.cr.execute("""
                    SELECT count(id)
                    FROM purchase_order
                    WHERE sh_purchase_order_id = %s
                """ % (rec.id))
                order_count = self.env.cr.fetchall()
                rec.po_count = order_count[0][0]

    def sh_quotation_revision(self, default=None):
        if self:
            self.ensure_one()
            if default is None:
                default = {}
            if 'name' not in default:
                
                default['name'] = _('%s/%s') % (self.name, self.sh_po_number)
                default['state'] = 'draft'
                default['origin'] = self.name
                default['sh_purchase_order_id'] = self.id
                self.sh_po_number += 1

            self.copy(default=default)
            sh_child_po = self.env['purchase.order'].search(
                [('sh_purchase_order_id', '=', self.id)])
            self.sh_revision_po_id = [(6, 0, sh_child_po.ids)]
