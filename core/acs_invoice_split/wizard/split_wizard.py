# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
 
class SplitInvoiceLine(models.TransientModel):
    _name = 'split.invoice.line'
    _description = 'Split Record Line'

    wizard_id = fields.Many2one("split.invoice.wizard")
    line_id = fields.Many2one("account.move.line")
    product_id = fields.Many2one("product.product", "Product")
    name = fields.Text("Description")
    quantity = fields.Float("Quantity")
    price = fields.Float("Unit Price")
    qty_to_split = fields.Float(string='Split Qty')
    price_to_split = fields.Float(string='Split Price')
    percentage_to_split = fields.Float(string='Split Percentage')
    display_type = fields.Selection([
        ('line_section', 'Section'),
        ('line_note', 'Note'),
    ], default=False, help="Technical field for UX purpose.")


class SplitInvoiceWizard(models.TransientModel):
    _name = 'split.invoice.wizard'
    _description = 'Split Invoice Record'

    split_selection = fields.Selection([
            ('invoice','Full Invoice'),
            ('lines','Invoice Lines'),
        ], 'Split Type', default='invoice')
    percentage = fields.Float("Percentage to Split", default=50)
    line_split_selection = fields.Selection([
            ('qty','Quantity'),
            ('price','Unit Price'),
            ('percentage','Percentage'),
        ], 'Split Line by', default='qty')
    line_ids = fields.One2many('split.invoice.line', 'wizard_id', string='Invoice Lines')
    partner_id = fields.Many2one('res.partner', 'Customer/Supplier', required=True)

    @api.model
    def default_get(self, fields):
        res = super(SplitInvoiceWizard, self).default_get(fields)
        active_model = self._context.get('active_model')
        if active_model == 'account.move':
            active_record = self.env['account.move'].browse(self._context.get('active_id'))
            if active_record.state!='draft':
                raise ValidationError(_('Invoice must be in draft state.'))
            lines = []
            for line in active_record.invoice_line_ids:
                lines.append((0,0,{
                    'name': line.name,
                    'product_id': line.product_id and line.product_id.id or False,
                    'line_id': line.id,
                    'quantity': line.quantity,
                    'price': line.price_unit,
                    'qty_to_split': 1,
                    'price_to_split': line.price_unit * 0.5,
                    'percentage_to_split': 50,
                    'display_type': line.display_type,
                    'wizard_id': self.id
                }))
            res.update({'line_ids': lines, 'partner_id': active_record.partner_id.id })
        return res        

    def split_lines(self, active_record, split_field, update_field):
        lines_to_split = active_record.invoice_line_ids.filtered(lambda r: r[split_field])
        new_inv_id = False
        if len(lines_to_split) >= 1:
            new_inv_id = active_record.with_context(from_split_invoice=True).copy()
            new_inv_id.partner_id = self.partner_id.id
            for line in new_inv_id.invoice_line_ids:
                if not line[split_field]:
                    line.with_context(check_move_validity=False).unlink()
                else:
                    line.with_context(check_move_validity=False).write({
                        update_field: line[split_field],
                        split_field: 0
                    })

            for line in active_record.invoice_line_ids:
                if line[split_field]:
                    if line[update_field] == line[split_field]:
                        line.with_context(check_move_validity=False).unlink()
                    else:
                        line.with_context(check_move_validity=False).write({
                            update_field: line[update_field] - line[split_field],
                            split_field: 0
                        })

        else:
            raise ValidationError(_('Please Enter Proper Amount/Quantity/Percentage To Split.'))
        return new_inv_id

    def split_record(self):
        active_model = self._context.get('active_model')
        new_inv_id = False
        if active_model == 'account.move':
            active_record = self.env['account.move'].browse(self._context.get('active_id'))
            #Create Splited Record
            if self.split_selection == 'invoice':
                #Incase of 100% just unlink active record.
                if self.percentage==100:
                    active_record.write({'partner_id': self.partner_id.id})
                    active_record.with_context(check_move_validity=False)._onchange_partner_id()
                    return active_record

                if not self.percentage:
                    raise ValidationError(_('Please Enter Percentage To Split.'))
                new_inv_id = active_record.with_context(from_split_invoice=True).copy()
                new_inv_id.partner_id = self.partner_id.id
                for line in new_inv_id.invoice_line_ids:
                    new_price = line.price_unit * (self.percentage / 100)
                    line.with_context(check_move_validity=False).price_unit = new_price

                for active_line in active_record.invoice_line_ids:
                    new_price = active_line.price_unit - (active_line.price_unit * (self.percentage / 100))
                    active_line.with_context(check_move_validity=False).price_unit = new_price

            if self.split_selection == 'lines':
                for line in self.line_ids:
                    price_to_split = 0
                    if self.line_split_selection == 'price':
                        price_to_split = line.price_to_split
                    elif self.line_split_selection == 'percentage':
                        price_to_split = line.line_id.price_unit * (line.percentage_to_split / 100)

                    line.line_id.with_context(check_move_validity=False).write({
                        'qty_to_split': line.qty_to_split,
                        'price_to_split': price_to_split,
                    })

                if self.line_split_selection == 'qty':
                    new_inv_id = self.split_lines(active_record, 'qty_to_split', 'quantity')

                if self.line_split_selection in ['price', 'percentage']:
                    new_inv_id = self.split_lines(active_record, 'price_to_split', 'price_unit')

            new_inv_id.with_context(check_move_validity=False)._onchange_partner_id()

            new_inv_id.with_context(check_move_validity=False)._recompute_dynamic_lines(recompute_all_taxes=True, recompute_tax_base_amount=True)
            active_record.with_context(check_move_validity=False)._recompute_dynamic_lines(recompute_all_taxes=True, recompute_tax_base_amount=True)
        
            new_inv_id.message_post_with_view('mail.message_origin_link',
                values={'self': new_inv_id, 'origin': active_record},
                subtype_id=self.env.ref('mail.mt_note').id
            )
            active_record.message_post_with_view('mail.message_origin_link',
                values={'self': active_record, 'origin': new_inv_id, 'edit': True,},
                subtype_id=self.env.ref('mail.mt_note').id
            )

        return new_inv_id
