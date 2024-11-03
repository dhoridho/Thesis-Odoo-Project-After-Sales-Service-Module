
from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta

class ExtendRental(models.Model):
    _name = 'extend.rental'
    _description = "Extend Rental"

    po_id = fields.Many2one('purchase.order')
    old_date_planned = fields.Date("Expected Return Date")
    old_rent_duration = fields.Integer(string='Rent Duration')
    old_rent_duration_unit = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ('years', 'Years')
    ],string="Single Rent Duration")
    date_planned = fields.Datetime("Extended Rent Duration")
    rent_duration = fields.Integer(string='Rent Duration')
    rent_duration_unit = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ('years', 'Years')
    ],string="Single Rent Duration")
    line_ids = fields.One2many('extend.rental.line', 'rental_id')

    @api.onchange('rent_duration','rent_duration_unit')
    def onchange_extend_rent_duration(self):
        for rec in self:
            if rec.rent_duration_unit == 'days':
                rec.date_planned = rec.old_date_planned + relativedelta(days=rec.rent_duration)
            elif rec.rent_duration_unit == 'weeks':
                rec.date_planned = rec.old_date_planned + relativedelta(weeks=rec.rent_duration)
            elif rec.rent_duration_unit == 'months':
                rec.date_planned = rec.old_date_planned + relativedelta(months=rec.rent_duration)
            elif rec.rent_duration_unit == 'years':
                rec.date_planned = rec.old_date_planned + relativedelta(years=rec.rent_duration)

    def action_create_rfq(self):
        self.env.context = dict(self._context)
        self.env.context.update({'from_extend_rental': True})
        for rec in self:
            product_line_data = []
            history_line = []
            vals = {
                'partner_id' : rec.po_id.partner_id.id,
                'is_rental_orders' : True,
                'branch_id': rec.po_id.branch_id.id,
                # 'order_line' : product_line_data,
                # 'history_extend_ids' : history_line,
                'destination_warehouse_id': rec.po_id.destination_warehouse_id.id,
                'picking_type_id': rec.po_id.picking_type_id.id,
                'date_planned': rec.old_date_planned + relativedelta(days=1),
                'rent_duration': rec.rent_duration,
                'rent_duration_unit': rec.rent_duration_unit,
                'is_extend_id': rec.po_id.id,
                'origin': rec.po_id.name,
            }
            po_obj = self.env['purchase.order']
            po_id = po_obj.create(vals)
            for line in rec.line_ids:
                product_id = self.env['product.product'].search([('product_tmpl_id','=', line.product_id.id)])
                self.env['purchase.order.line'].create({
                    'order_id': po_id.id,
                    'product_id' : product_id.id,
                    'name' : line.description,
                    'price_unit': line.unit_price,
                    'display_type': False,
                    'analytic_tag_ids': rec.po_id.analytic_account_group_ids.ids,
                    'date_planned': rec.old_date_planned + relativedelta(days=1),
                    'product_qty' : line.extend_qty,
                    'product_uom' : product_id.uom_id.id,
                })
                # for history in rec.po_id.history_extend_ids:
                #     self.env['history.extend.rental'].create({
                #         'po_id': po_id.id,
                #         'po_reference': history.po_reference,
                #         'expected_date': history.expected_date,
                #         'expected_return_date': history.expected_return_date,
                #         'rent_duration': history.rent_duration,
                #         'total': history.total
                #     })
                duration_unit = dict(self.env['purchase.order'].fields_get(allfields=['rent_duration_unit'])['rent_duration_unit']['selection'])[po_id.rent_duration_unit]
                self.env['history.extend.rental'].create({
                    'po_id': rec.po_id.id,
                    'po_reference': po_id.name,
                    'expected_date': po_id.date_planned,
                    'expected_return_date': po_id.expected_return_date,
                    'rent_duration': str(po_id.rent_duration) + " " + duration_unit,
                    'total': po_id.amount_total
                })
            po_id._onchange_destination_warehouse()
            return {
                'name': 'Requests for Quotation',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'purchase.order',
                'type': 'ir.actions.act_window',
                'res_id': po_id.id,
                'target': 'current',
            }

class ExtendRentalLine(models.Model):
    _name = 'extend.rental.line'
    _description = "Extend Rental Line"

    rental_id = fields.Many2one('extend.rental', string="Rental")
    product_id = fields.Many2one('product.template', string='Product')
    description = fields.Char("Description")
    rented_qty = fields.Float("Rented Qty")
    extend_qty = fields.Float("Quantity to Extend")
    unit_price = fields.Float("Unit Price")

class HistoryExtendRental(models.Model):
    _name = 'history.extend.rental'
    _description = "History Extend Rental"

    rental_id = fields.Many2one('extend.rental', string="Rental")
    po_id = fields.Many2one('purchase.order')
    po_reference = fields.Char("PO Reference")
    expected_date = fields.Datetime("Expected Date")
    expected_return_date = fields.Datetime("Expected Return Date")
    rent_duration = fields.Char("Rent Duration")
    total = fields.Float("Total")
