from odoo import models, fields
from lxml import etree


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    manuf_auto_create = fields.Selection(
        selection=[
            ('auto_mp', 'Auto Create Manufacturing Plan'),
            ('auto_mo', 'Auto Create Manufacturing Order'),
            ('none', 'None')
        ],
        required=False,
        default='none',
        string='Sales to Manufacturing'
    )

    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(ProductTemplate, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            doc = etree.XML(result['arch'])
            manufacturing_tab = doc.xpath("//field[@name='manuf_auto_create']")
            if manufacturing_tab and not self.env.company.sales_to_manufacturing:
                manufacturing_tab[0].getparent().remove(manufacturing_tab[0])
                result['arch'] = etree.tostring(doc, encoding='unicode')
        return result
