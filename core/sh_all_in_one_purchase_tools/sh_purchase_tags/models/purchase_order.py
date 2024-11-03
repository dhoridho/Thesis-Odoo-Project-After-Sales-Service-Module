# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import api, models, fields
from lxml import etree


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    purchase_tag_ids = fields.Many2many("sh.purchase.tags",
                                        string="Purchase Tag")

    def insert_after(self, element, new_element):
        parent = element.getparent()
        parent.insert(parent.index(element) + 1, new_element)

    @api.model
    def fields_view_get(
        self,
        view_id=None,
        view_type="form",
        toolbar=False,
        submenu=False,
    ):
        res = super(PurchaseOrder, self).fields_view_get(
            view_id=view_id,
            view_type=view_type,
            toolbar=toolbar,
            submenu=submenu,
        )

        if view_type != "search":
            return res

        doc = etree.XML(res["arch"])

        purchase_tags = self.env["sh.purchase.tags"].search([]).sorted(
            "name",
            reverse=True,
        )

        if not purchase_tags:
            return res

        node = doc.find(".//filter[@name='order_date']")

        self.insert_after(node, etree.fromstring("<separator/>"))

        for purchase_tag in purchase_tags:
            purchase_tag_filter = """
            <filter string="{name}" domain="[('purchase_tag_ids', '=', {purchase_tag_id})]"/>
            """.format(**{
                "name": purchase_tag.name,
                "purchase_tag_id": purchase_tag.id,
            })
            self.insert_after(node, etree.fromstring(purchase_tag_filter))
        self.insert_after(node, etree.fromstring("<separator/>"))

        res["arch"] = etree.tostring(doc)

        return res

    def action_mass_tag_update(self):
        return {
            'name':
            'Mass Tag Update',
            'res_model':
            'sh.purchase.update.mass.tag.wizard',
            'view_mode':
            'form',
            'context': {
                'default_purchase_order_ids':
                [(6, 0, self.env.context.get('active_ids'))]
            },
            'view_id':
            self.env.ref(
                'sh_all_in_one_purchase_tools.sh_purchase_mass_tag_wizard_form_view').id,
            'target':
            'new',
            'type':
            'ir.actions.act_window'
        }
