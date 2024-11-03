# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError, UserError, RedirectWarning, Warning

class AccountMove(models.Model):
    _inherit = "account.move"

    patient_id = fields.Many2one('hms.patient',string="Patient")
    hospital_invoice_type = fields.Selection(selection_add=[('pharmacy', 'Pharmacy')])

    @api.model
    def assign_invoice_lots(self, picking):
        MoveLine = self.env['stock.move.line']
        for line in self.invoice_line_ids:
            quantity = line.product_uom_id._compute_quantity(line.quantity, line.product_id.uom_id)
            if line.batch_no:
                move_line_id = MoveLine.search([('product_id', '=', line.product_id.id),('picking_id','=',picking.id),('product_uom_qty','=',quantity),('lot_id','=',False),('qty_done','=',0)],limit=1)
                if move_line_id:
                    move_line_id.lot_id = line.batch_no.id
                    move_line_id.qty_done = quantity

    def get_scan_line_data(self, product, lot=False):
        res = super(AccountMove, self).get_scan_line_data(product, lot)
        res['batch_no'] = lot and lot.id or False
        return res


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    product_id = fields.Many2one(domain=[('sale_ok', '=', True),('hospital_product_type', '=', 'medicament')])
    batch_no = fields.Many2one("stock.production.lot", domain=[('locked', '=', False)], string="Batch Number")
    exp_date = fields.Datetime(string="Expiry Date")
    
    @api.onchange('quantity', 'batch_no')
    def onchange_batch(self):
        if self.batch_no and self.move_id.move_type=='out_invoice':
            if self.batch_no.product_qty < self.quantity:
                batch_product_qty = self.batch_no.product_qty
                self.batch_no = False
                warning = {
                    'title': "Warning",
                    'message': _("Selected Lot do not have enough qty. %s qty needed and lot have only %s" %(self.quantity,batch_product_qty)),
                }
                return {'warning': warning}

            self.exp_date = self.batch_no.use_date
            if self.batch_no.mrp:
                self.price_unit = self.batch_no.mrp

    #ACS: Check requirement and remove if not needed as it causing in default odoo test cases
    # @api.onchange('product_id')
    # def _onchange_product_id(self):
    #     res = super(AccountMoveLine, self)._onchange_product_id()
    #     for line in self:
    #         if line.move_id and line.product_id and line.move_id.move_type =='in_invoice':
    #             line.product_uom_id = line.product_id.uom_po_id.id

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: