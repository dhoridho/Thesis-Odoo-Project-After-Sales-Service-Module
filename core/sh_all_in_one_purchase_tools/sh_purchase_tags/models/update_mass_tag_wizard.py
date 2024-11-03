# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import fields, models


class Updatemasstag(models.TransientModel):

    _name = "sh.purchase.update.mass.tag.wizard"
    _description = "Mass Tag Update Wizard"

    purchase_order_ids = fields.Many2many('purchase.order')
    wiz_tag_ids = fields.Many2many("sh.purchase.tags",
                                   string="Invoice Tags",
                                   required=True)
    update_method = fields.Selection([
        ("add", "Add"),
        ("replace", "Replace"),
    ],
        default="add")

    def update_tags(self):
        if self.update_method == 'add':
            for i in self.wiz_tag_ids:
                self.purchase_order_ids.write(
                    {'purchase_tag_ids': [(4, i.id)]})

        if self.update_method == 'replace':
            self.purchase_order_ids.write(
                {'purchase_tag_ids': [(6, 0, self.wiz_tag_ids.ids)]})
