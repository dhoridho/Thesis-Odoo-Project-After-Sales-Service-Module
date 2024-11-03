from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    def _compute_subcon_pickings(self):
        for record in self:
            picking_ids = record.subcon_picking_ids
            record.subcon_delivery_count = len(picking_ids.filtered(
                lambda p: p.picking_type_code == 'outgoing'))
            record.subcon_receipt_count = len(picking_ids.filtered(
                lambda p: p.picking_type_code == 'incoming'))

    def _compute_can_be_subcontracted(self):
        for record in self:
            can_be_subcontracted = False
            for line in record.line_ids:
                product_bom_ids = line.product_id.active_bom_ids
                if not product_bom_ids:
                    continue
                can_be_subcontracted = any(bom.can_be_subcontracted for bom in product_bom_ids)
                if can_be_subcontracted:
                    break
            record.can_be_subcontracted = can_be_subcontracted

    @api.depends('line_ids', 'line_ids.product_qty', 'line_ids.bom_id', 'can_be_subcontracted')
    def _compute_can_create_do(self):
        for record in self:
            line_ids = record.line_ids
            can_create_do = False
            if line_ids and record.can_be_subcontracted:
                line_bom = line_ids.filtered(
                    lambda l: any(bom.can_be_subcontracted for bom in l.product_id.active_bom_ids))
                if line_bom:
                    po_lines = self.env['purchase.order.line'].search([
                        ('requisition_line_id', 'in', line_bom.ids), 
                        ('order_id.state', '!=', 'cancel')
                    ])

                    qty_remainings = dict()
                    for line in line_bom:
                        qty_remainings[line.id] = line.product_qty - sum(po_lines.filtered(lambda pl: pl.requisition_line_id == line).mapped('product_qty'))

                    can_create_do = not all(qty_remainings[l.id] == 0.0 for l in line_bom)
            record.can_create_do = can_create_do

    can_be_subcontracted = fields.Boolean(compute=_compute_can_be_subcontracted)
    is_a_subcontracting = fields.Boolean(string='Is a Subcontracting')
    subcon_production_id = fields.Many2one('mrp.production', string='Production Order')
    subcon_product_qty = fields.Float(string='Subcontract Quantity', digits='Product Unit of Measure')
    subcon_uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    subcon_operation_ids = fields.One2many('mrp.requisition.subcon.operation', 'requisition_id', string='Operation History')
    subcon_picking_ids = fields.One2many('stock.picking', 'subcon_requisition_id', string='Subcontracting Pickings')

    subcon_delivery_count = fields.Integer(compute=_compute_subcon_pickings)
    subcon_receipt_count = fields.Integer(compute=_compute_subcon_pickings)
    can_create_do = fields.Boolean(compute=_compute_can_create_do)

    def _prepare_subcon_vals(self):
        self.ensure_one()
        is_subcon = self.is_a_subcontracting
        values = {
            'origin': self.name,
            'is_readonly_origin': True,
            'is_a_subcontracting': is_subcon,
            'subcon_production_id': is_subcon and self.subcon_production_id.id or False,
            'subcon_product_qty': is_subcon and self.subcon_product_qty or 0.0,
            'subcon_uom_id': is_subcon and self.subcon_uom_id.id or False,
            'subcon_qty_producing': is_subcon and self.subcon_product_qty or 0.0,
            'subcon_qty_produced': 0.0,
            'subcon_requisition_id': self.id
        }
        return values

    def _prepare_subcon_delivery_vals(self):
        self.ensure_one()
        picking_type_id = self.env['stock.picking.type'].search([
            ('company_id', '=', self.company_id.id),
            ('sequence_code', '=', 'OUT')], limit=1)
        picking_type_location = picking_type_id.default_location_src_id
        first_location = self.env['stock.location'].search([
            ('company_id', '=', self.company_id.id)], limit=1)

        subcon_location = self.env['stock.location'].search([
            ('company_id', '=', self.company_id.id),
            ('barcode', 'like', 'SWH')], limit=1)
        partner_subcon_location = self.vendor_id.property_stock_subcontractor

        location_id = picking_type_location or first_location
        location_dest_id = subcon_location or partner_subcon_location or first_location

        move_ids_without_package = []
        for line in self.line_ids.filtered(lambda l: l.bom_id):
            line_qty = line.wizard_qty
            for bom_line in line.bom_id.bom_line_ids:
                bom_line_qty = bom_line.product_qty
                bom_id = bom_line.bom_id
                bom_qty = bom_id.product_qty
                move_ids_without_package += [(0, 0, {
                    'name': self.name,
                    'product_id': bom_line.product_id.id,
                    'initial_demand': (line_qty * bom_line_qty) / bom_qty,
                    'product_uom_qty': (line_qty * bom_line_qty) / bom_qty,
                    'product_uom': line.product_uom_id.id
                })]

        values = {
            'is_a_delivery': True,
            'name': picking_type_id.sequence_id.next_by_id(),
            'picking_type_id': picking_type_id.id,
            'location_id': location_id.id,
            'location_dest_id': location_dest_id.id,
            'move_ids_without_package': move_ids_without_package
        }
        values.update(self._prepare_subcon_vals())
        return values

    def action_create_delivery_order(self):
        self.ensure_one()

        if not self.can_be_subcontracted:
            return

        if self.subcon_production_id and self.date_end < self.subcon_production_id.create_date:
            raise ValidationError(_('Cannot generate DO for Agreement Deadline set on a date prior to MO creation!'))

        skip_wizard = self.env.context.get('skip_wizard')
        if not self.is_a_subcontracting and not skip_wizard:
            for line in self.line_ids:
                line.wizard_qty = line.qty_remaining
            return {
                'name': 'Choose Bill of Materials',
                'type': 'ir.actions.act_window',
                'res_model': 'requisition.delivery.order',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_requisition_id': self.id}
            }

        values = self._prepare_subcon_delivery_vals()
        picking_id = self.env['stock.picking'].create(values)

        purchase_ids = self.env['purchase.order'].search([
            ('requisition_id', '=', self.id),
            ('is_a_subcontracting', '=', True)
        ])
        if purchase_ids:
            purchase_ids.write({'subcon_picking_ids': [(4, picking_id.id)]})

    def action_view_subcon_pickings(self):
        self.ensure_one()
        picking_type_code = self.env.context.get('picking_type_code', 'outgoing')

        action_id = 'equip3_inventory_operation.action_delivery_order'
        if picking_type_code == 'incoming':
            action_id = 'equip3_inventory_operation.stock_picking_receiving_note'

        action = self.env['ir.actions.actions']._for_xml_id(action_id)
        pickings = self.subcon_picking_ids.filtered(lambda p: p.picking_type_code == picking_type_code)
        if not pickings:
            return
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        else:
            views = [(self.env.ref('stock.view_picking_form').id, 'form')]
            if 'views' in action:
                views += [(state, view) for state, view in action['views'] if view != 'form']
            action['views'] = views
            action['res_id'] = pickings.id

        action['context'] = dict(
            active_model='stock.picking',
            active_ids=pickings.ids,
            active_id=pickings.ids[0]
        )
        return action


class PurchaseRequisitionLine(models.Model):
    _inherit = 'purchase.requisition.line'

    def _get_qty_received(self):
        super(PurchaseRequisitionLine, self)._get_qty_received()
        for record in self:
            requisition_id = record.requisition_id
            if not requisition_id:
                continue

            if requisition_id.is_a_subcontracting:
                picking_ids = requisition_id.subcon_picking_ids.filtered(
                    lambda p: p.picking_type_code == 'incoming' and p.state in ('done', 'cancel')
                )
                qty_received = sum(picking_ids.mapped('subcon_qty_producing'))
                record.qty_received = qty_received
                record.qty_remaining = record.product_qty - record.qty_received

    bom_id = fields.Many2one(
        'mrp.bom',
        string='Bill of Material',
        domain="""[
            ('can_be_subcontracted', '=', True),
            ('type', '=', 'normal'),
            '|', 
                ('product_id', '=', product_id),
                '&',
                    ('product_tmpl_id.product_variant_ids', '=', product_id),
                    ('product_id', '=', False),
        ]""")

    # technical field for wizard
    wizard_qty = fields.Float('Wizard Quantity', digits='Product Unit of Measure')


class MrpSubconOperation(models.Model):
    _name = 'mrp.requisition.subcon.operation'
    _description = 'MRP Requisition Subcontracting Operation'

    requisition_id = fields.Many2one('purchase.requisition', string='Blanket Order', required=True)
    purchase_id = fields.Many2one('purchase.order', string='Purchase Order')
    picking_id = fields.Many2one('stock.picking', string='Receipt')
    production_id = fields.Many2one('mrp.production', string='Production Order')
    consumption_id = fields.Many2one('mrp.consumption', string='Production Record')
    date_validated = fields.Datetime(string='Date Validated')
    amount_received = fields.Float(digits='Product Unit of Measure')
