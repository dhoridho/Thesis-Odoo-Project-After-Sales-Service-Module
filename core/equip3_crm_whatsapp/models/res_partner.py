from odoo import models
from lxml import etree


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(ResPartner, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type != 'form' or not view_id:
            return res

        acrux_view_id = self.env.ref('equip3_crm_whatsapp.view_partner_form_acrux_chat', raise_if_not_found=False)
        if acrux_view_id and view_id == acrux_view_id.id:
            doc = etree.XML(res['arch'])
            for page in doc.findall('.//page'):
                attrib = page.attrib or dict()
                if attrib.get('name') not in ['contact_addresses', 'sales_purchases']:
                    page.set("modifiers", '{"invisible": [[1, "=", 1]]}')
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res
