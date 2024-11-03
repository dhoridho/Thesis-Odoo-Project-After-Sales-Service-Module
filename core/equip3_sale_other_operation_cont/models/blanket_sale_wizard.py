from odoo import models, fields, api, _
from datetime import datetime, date
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
import xlsxwriter
import xlrd
import xlwt
import base64
from io import BytesIO
from odoo.exceptions import UserError, ValidationError

class BlanketWizard(models.TransientModel):

    _inherit='blanketwiz.blanketwiz'

    @api.model
    def default_get(self, fields):
        res=super(BlanketWizard, self).default_get(fields)
        res.update({
            'wiz_line_ids': []
        })
        active_ids=self._context.get('active_ids')
        invoice_order_ids=self.env['saleblanket.saleblanket'].browse(active_ids)
        split_order_lines=[]
        for order in invoice_order_ids:
            for line in order.order_line_ids:
                split_order_lines.append((0,0, {
                    'partner_id': order.partner_id.id,
                    'product_id':line.product_id.id,
                    'remaining_quantity':line.remaining_quantity,
                    'new_quatation_quantity':0.00,
                    'blanket_order_line_id':line.id,
                    'unit_of_measure_id':line.product_uom.id,
                    'unit_price':line.price_unit,
                    'taxes_id':[(6,0,line.tax_id.ids)],
                    'subtotal':line.price_subtotal,
                }))
        res.update({
            'wiz_line_ids': split_order_lines
        })

        return res

    def create_quatation(self):
        line_order_id = self.env['saleblanket.saleblanket'].browse(self.env.context.get('active_ids'))
        env_id = self.env['orderwizline.orderwizline'].browse(self.env.context.get('active_ids'))
        quatation_quantity = all(line.new_quatation_quantity == 0 for line in self.wiz_line_ids)
        if quatation_quantity:
            raise ValidationError("New Quotation Quantity Is Required!")

        sale_order_id=self.env['sale.order'].create({
            'partner_id':line_order_id.partner_id.id,
            'validity_date' : line_order_id.expiry_date,
            'payment_term_id': line_order_id.payment_term_id.id,
            'pricelist_id': line_order_id.pricelist_id.id,
            'origin': line_order_id.name,
            "warehouse_id": self.env['stock.warehouse'].search([], limit=1, order="id").id,
            'warehouse_new_id': self.env['stock.warehouse'].search([], limit=1, order="id").id,
            'branch_id': line_order_id.branch_id.id,
            'account_tag_ids': [(6,0,line_order_id.analytic_tag_ids.ids)],
        })
        for rec in self.wiz_line_ids:
            if rec.new_quatation_quantity > rec.remaining_quantity:
                raise ValidationError("Quotation quantity is more than remaining quantity. ")
            if rec.new_quatation_quantity == 0:
                continue
            sale_order_id.order_line.create({'product_id': rec.product_id.id,
                'product_uom_qty':rec.new_quatation_quantity,
                'product_uom':rec.unit_of_measure_id.id,
                'price_unit':rec.unit_price,
                'line_warehouse_id': sale_order_id.warehouse_id.id,
                'multiple_do_date': date.today(),
                'tax_id':[(6,0,rec.taxes_id.ids)],
                'price_subtotal':rec.subtotal,
                'order_id':sale_order_id.id,
                'bo_id': rec.blanket_order_line_id.id,
                'account_tag_ids': [(6,0,rec.blanket_order_line_id.analytic_tag_ids.ids)],
            })
            remaining_quantity = rec.blanket_order_line_id.remaining_quantity - rec.new_quatation_quantity
            ordered_quantity = rec.blanket_order_line_id.ordered_qty + rec.new_quatation_quantity
            rec.blanket_order_line_id.write({'remaining_quantity': remaining_quantity, 'ordered_qty': ordered_quantity})
        sale_order_id.set_del_add_line()
        sale_order_id._compute_approving_matrix_lines()