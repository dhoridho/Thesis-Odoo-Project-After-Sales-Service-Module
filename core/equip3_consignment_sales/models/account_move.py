from odoo import _, api, fields, models
from lxml import etree


class AccountMove(models.Model):
    _inherit = 'account.move'

    sale_consignment_id = fields.Many2one(
        comodel_name='sale.consignment.agreement', string='Sale Consignment', readonly=True)


    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=True, submenu=True):
        res = super(AccountMove, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        context = self._context or {}
        if context.get('active_model') == 'sale.order':
            sale_id = self.env['sale.order'].browse(context.get('active_id'))
            if sale_id and sale_id.sale_consignment_id:
                if view_type == 'form':
                    doc = etree.XML(
                        res['fields']['invoice_line_ids']['views']['tree']['arch'])
                    tree_element = doc.xpath("//tree")[0]
                    tree_element.set('create', '0')
                    updated_arch = etree.tostring(
                        doc, pretty_print=True, encoding='unicode')
                    res['fields']['invoice_line_ids']['views']['tree']['arch'] = updated_arch
        return res