from odoo import _, models,fields,SUPERUSER_ID, api
from odoo.exceptions import ValidationError

class WizardQtyConsignmentAgreement(models.TransientModel):
    _name = 'wizard.qty.consignment.agreement'
    _description = 'Wizard Qty Consignment Agreement'

    def _default_active_ids(self):
        active_model = self.env['consignment.agreement'].browse(self._context.get('active_ids'))
        order_line = []
        for line in active_model.line_ids:
            order_line.append((0, 0, {
                'consignment_agreement_line_id': line.id,
                'consignment_id' : line.consignment_id.id,
                'no' : line.sequence2,
                'product_id': line.product_id.id,
                # 'quantity_ordered': line.product_qty,
                'destination_id' : line.destination_warehouse_id.id,
                'receiving_quantities' : 0,
                # 'remaining' : line.remaining_quantities,
                'company_id': line.company_id.id,
                'product_uom_id': line.product_uom_id.id
            }))
        return order_line

    def _default_active_ids_consignment_agreement(self):
        active_model = self.env['consignment.agreement'].browse(self._context.get('active_ids'))
        return active_model.id

    consignment_agreement_line_wizard_ids = fields.One2many('wizard.qty.consignment.agreement.line', 'consignment_agreement_wizard_id', default=_default_active_ids)
    consignment_id = fields.Many2one('consignment.agreement',default=_default_active_ids_consignment_agreement)

    def confirm(self):
        picking_obj = self.env['stock.picking']
        move_obj = self.env['stock.move']
        location = self.env['stock.location'].search([('usage' ,'=', 'customer')])
        active_model = self.env['consignment.agreement'].browse(self._context.get('active_ids'))

        location_dest = ''
        for line in self.consignment_agreement_line_wizard_ids.sorted(lambda x: x.destination_id.id):
            receiving = 0
            count = 0
            if line.receiving_quantities >= 1:
                if location_dest == line.destination_id.lot_stock_id.id:
                    move_value = line._prepare_stock_move()
                    move = move_obj.with_user(SUPERUSER_ID).create(move_value)
                    move.write({'picking_id' : picking.id})
                    move.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm()

                if location_dest != line.destination_id.lot_stock_id.id:
                    value_create = line._prepare_picking()
                    picking = picking_obj.with_user(SUPERUSER_ID).create(value_create)
                    move_value = line._prepare_stock_move()
                    move = move_obj.with_user(SUPERUSER_ID).create(move_value)
                    move.write({'picking_id' : picking.id})
                    move.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm()
                location_dest = line.destination_id.lot_stock_id.id
        return True


class WizardQtyConsignmentAgreementLine(models.TransientModel):
    _name = 'wizard.qty.consignment.agreement.line'
    _description = 'Wizard Qty Consignment Agreement Line'

    consignment_agreement_wizard_id = fields.Many2one('wizard.qty.consignment.agreement')
    no = fields.Integer('No')
    product_id = fields.Many2one('product.product', 'Products')
    # quantity_ordered = fields.Integer('Quantity Ordered')
    destination_id = fields.Many2one('stock.warehouse', 'Destination')
    # remaining = fields.Integer('Remaining')
    receiving_quantities = fields.Integer('Receiving Quantities')
    consignment_id = fields.Many2one('consignment.agreement')
    consignment_agreement_line_id = fields.Many2one('consignment.agreement.line')
    company_id = fields.Many2one('res.company')
    product_uom_id = fields.Many2one('uom.uom')

    def _prepare_picking(self):
        vals = {}
        location = self.env['stock.location'].search([('usage' ,'=', 'supplier')],order='id asc', limit=1)
        for order in self:
            vals = {'branch_id' : order.consignment_id.branch_id.id,
                    'consignment_id' : order.consignment_id.id,
                    'location_dest_id' : order.destination_id.lot_stock_id.id,
                    'location_id' : location.id,
                    'picking_type_id' : order.destination_id.in_type_id.id,
                    'is_consignment' : True,
                    'move_type' : 'direct',
                    'origin' : order.consignment_id.name}
        return vals

    def _prepare_stock_move(self):
        vals = {}
        location = self.env['stock.location'].search([('usage' ,'=', 'supplier')],order='id asc', limit=1)
        now = fields.datetime.now().date()
        for order in self:

            vals = {
                'company_id' : order.company_id.id,
                'date': now,
                'company_id': order.company_id.id,
                'location_dest_id' : order.destination_id.lot_stock_id.id,
                'location_id': location.id,
                'name': order.product_id.product_tmpl_id.name,
                'procure_method': 'make_to_stock',
                'product_id' : order.product_id.id,
                'product_uom' : order.product_uom_id.id,
                'product_uom_qty' : order.receiving_quantities,
                'picking_type_id' : order.destination_id.in_type_id.id
                }
        return vals

    # @api.onchange('receiving_quantities')
    # def _onchange_receiving_quantities(self):
    #     for line in self:
    #         if line.receiving_quantities > line.remaining:
    #             raise ValidationError('receiving is more than remaining')
