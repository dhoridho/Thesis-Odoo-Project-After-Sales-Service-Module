from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from lxml import etree


class View(models.Model):
    _inherit = 'ir.ui.view'

    def _compute_xml_id(self):
        # fixing issue external id
        res = super()._compute_xml_id()
        try:
            view_id = self.env.ref('equip3_discount_with_tax.view_order_invoice_discount_form_inherit')
        except:
            view_id = False
        if view_id:
            for rec in self:
                if rec.id == view_id.id:
                    rec.xml_id = 'equip3_discount_with_tax.view_order_invoice_discount_form_inherits'
        return res