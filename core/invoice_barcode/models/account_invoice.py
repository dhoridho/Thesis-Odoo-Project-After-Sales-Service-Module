# -*- encoding: utf-8 -*-

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'barcodes.barcode_events_mixin']

    def get_scan_line_data(self, product, lot=False):
        account_id = product.property_account_income_id or product.categ_id.property_account_income_categ_id
        return {
            'product_id': product.id,
            'name':product.name,
            'tax_ids': [(6, 0, product.taxes_id.ids)],
            'quantity' : 1,
            'price_unit': product.lst_price,
            'product_uom_id': product.uom_id.id,
            'account_id': account_id.id,
        }

    def on_barcode_scanned(self, barcode):
        if barcode and self.state=='draft':
            lot = False
            ProductObj = self.env['product.product']
            InvLine = self.env['account.move.line']
            Lot = self.env['stock.production.lot']
            product = ProductObj.search([('barcode','=',barcode)], limit=1)
            if not product:
                lot = ProductObj.search([('default_code','=',barcode)], limit=1)
            if not product:
                lot = Lot.search([('name','=',barcode)], limit=1)
                product = lot.product_id
            if not product and not lot:
                raise UserError(_('There is no product with Barcode or Reference or Lot: %s') % (barcode))

            flag = True
            order_line = []
            for o_line in self.invoice_line_ids:
                if o_line.product_id == product:
                    flag = False
                    o_line.quantity += 1

            if flag:
                line_data = self.get_scan_line_data(product, lot)
                self.invoice_line_ids += InvLine.new(line_data)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: