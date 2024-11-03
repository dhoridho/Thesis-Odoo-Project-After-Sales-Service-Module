from odoo import models,fields,api
from lxml import etree
import json as simplejson
import json


class ProductTemplateInherit(models.Model):
    _inherit = 'product.template'

    is_external_link = fields.Boolean('Is External Link', default=False)

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=True, submenu=True):
        res = super(ProductTemplateInherit, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                               submenu=submenu)
        is_external_link = self.env.context.get("default_is_external_link")
        doc = etree.XML(res['arch'])
        if is_external_link and view_type == 'form':
            for node in doc.xpath("//field"):
                modifiers = simplejson.loads(node.get("modifiers"))
                modifiers['readonly'] = True
                node.set('modifiers', simplejson.dumps(modifiers))
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

    def _get_combination_info(self, combination=False, product_id=False, add_qty=1, pricelist=False, warehouse_id=1, parent_combination=False, only_template=False):

        res = super(ProductTemplateInherit,self)._get_combination_info(combination, product_id, add_qty, pricelist, parent_combination, only_template)
        product = self.env['product.product'].browse(res['product_id'])
        if warehouse_id:
            qty_available = product.sudo().with_context(warehouse=warehouse_id).qty_available
        else:
            qty_available = product.sudo().qty_available
        res.update({
            'qty_available':qty_available
        })
        return res
