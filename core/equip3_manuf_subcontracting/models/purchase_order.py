from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.osv import expression


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    subcon_picking_ids = fields.Many2many('stock.picking', relation='purchase_picking_subcon_ids', string='Subcontracting Delivery Orders')

    @api.depends('subcon_production_id', 'is_a_subcontracting')
    def _compute_production_name(self):
        for record in self:
            name = ''
            production_id = record.subcon_production_id
            if record.is_a_subcontracting and production_id:
                name = '%s - %s' % (production_id.name, production_id.product_id.name)
            record.subcon_production_name = name

    @api.depends('company_id', 'subcon_picking_ids')
    def _compute_subcon_transfer_count(self):
        for record in self:
            transfers = record.subcon_picking_ids
            record.subcon_delivery_count = len(transfers.filtered(lambda o: o.picking_type_code == 'internal'))
            record.subcon_receipt_count = len(transfers.filtered(lambda o: o.picking_type_code == 'incoming'))

    @api.depends('is_a_subcontracting', 'subcon_production_id', 'company_id')
    def _compute_allowed_partners(self):
        domain = self._domain_partner()
        partner_sudo = self.env['res.partner'].sudo()
        partner_ids = partner_sudo.search(domain)
        for record in self:
            allowed_partner_ids = partner_ids.ids
            if record.is_a_subcontracting:
                subcon_partner_ids = record.subcon_production_id.bom_id.subcontractor_ids.ids
                allowed_partner_ids = partner_ids.filtered(lambda p: p.id in subcon_partner_ids).ids
            record.allowed_partner_ids = [(6, 0, allowed_partner_ids)]

    partner_id = fields.Many2one('res.partner', domain="[('id', 'in', allowed_partner_ids)]")
    allowed_partner_ids = fields.Many2many('res.partner', compute=_compute_allowed_partners)

    is_a_subcontracting = fields.Boolean(string='Is a Subcontracting')
    subcon_production_id = fields.Many2one('mrp.production', string='Production Order')
    subcon_production_name = fields.Char(string='Production Order Name', compute=_compute_production_name, store=True)
    subcon_product_qty = fields.Float(string='Subcontract Quantity', digits='Product Unit of Measure')
    subcon_uom_id = fields.Many2one('uom.uom', string='Subcontracting Unit of Measure')

    subcon_delivery_count = fields.Integer(compute=_compute_subcon_transfer_count)
    subcon_receipt_count = fields.Integer(compute=_compute_subcon_transfer_count)

    @api.constrains('is_a_subcontracting')
    def is_a_subcontracting_constraints(self):
        for record in self:
            if not record.is_a_subcontracting:
                continue
            missing_field = False
            if not record.subcon_production_id:
                missing_field = 'Production Order (subcon_production_id)'
            if not record.subcon_uom_id:
                missing_field = 'Subcontracting UoM (subcon_uom_id)'
            if record.subcon_product_qty <= 0.0:
                missing_field = 'Subcontracting Quantity (subcon_product_qty)'
            if missing_field:
                raise ValidationError(_('%s is mandatory when Subcontracting is True!' % missing_field))

    def action_view_subcon_transfer(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('equip3_inventory_operation.action_from_interwarehouse_request')
        pickings = self.subcon_picking_ids
        company = self.company_id
        subcon_warehouse = company.subcontracting_warehouse_id
        if self.env.context.get('subcon_transfer', 'material') == 'material':
            pickings = pickings.filtered(lambda o: o.picking_type_code == 'internal')
        else:
            pickings = pickings.filtered(lambda o: o.picking_type_code == 'incoming')

        if not pickings:
            return
        
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        else:
            if 'domain' in action:
                del action['domain']
            action['views'] = [(False, 'form')]
            action['res_id'] = pickings.id

        action['context'] = str(dict(eval(action.get('context', '').strip() or '{}', self._context), active_model='stock.picking', active_ids=pickings.ids, active_id=pickings[0].id))
        return action

    def _prepare_subcon_vals(self):
        self.ensure_one()
        values = {
            'origin': self.name,
            'company_id': self.company_id.id,
            'branch_id': self.branch_id.id,
            'is_readonly_origin': True,
            'is_a_subcontracting': True,
            'subcon_production_id': self.subcon_production_id.id,
            'subcon_product_qty': self.subcon_product_qty,
            'subcon_uom_id': self.subcon_uom_id.id,
            'subcon_qty_producing': self.subcon_product_qty,
            'subcon_qty_produced': 0.0,
        }
        return values

    def _prepare_subcon_transfer_vals(self, moves, picking_type_id, location_id, location_dest_id):
        self.ensure_one()
        move_ids_without_package = []
        for sequence, move in enumerate(moves):
            move_ids_without_package += [(0, 0, {
                'move_line_sequence': sequence + 1,
                'name': move.product_id.display_name,
                'product_id': move.product_id.id,
                'product_uom_qty': move.product_uom_qty,
                'product_uom': move.product_uom,
                'initial_demand': move.product_uom_qty,
                'location_id': location_id.id,
                'location_dest_id': location_dest_id.id,
                'subcon_move_id': move.id,
                'allocated_cost': move.allocated_cost
            })]

        values = {
            'location_id': location_id.id,
            'location_dest_id': location_dest_id.id,
            'partner_id': self.partner_id.id,
            'scheduled_date': self.date_planned,
            'picking_type_id': picking_type_id.id,
            'move_ids_without_package': move_ids_without_package
        }
        values.update(self._prepare_subcon_vals())
        return values

    def _prepare_subcon_delivery_vals(self, workorders):
        self.ensure_one()
        production = self.subcon_production_id
        location_id = production.location_dest_id
        location_dest_id = self.company_id.subcontracting_warehouse_id.lot_stock_id
        picking_type_id = self.env['stock.picking.type'].search([
            ('company_id', '=', self.company_id.id),
            ('code', '=', 'internal'),
            ('default_location_dest_id', '=', location_dest_id.id),
        ], limit=1)

        values = self._prepare_subcon_transfer_vals(workorders.move_raw_ids, picking_type_id, location_id, location_dest_id)
        values.update({
            'move_type': 'direct',
            'subcon_material_workorder_ids': [(6, 0, workorders.ids)]
        })
        return values

    def _prepare_subcon_receipt_vals(self, workorders):
        self.ensure_one()
        production = self.subcon_production_id
        location_id = self.partner_id.property_stock_supplier
        location_dest_id = production.location_dest_id
        picking_type_id = self.env['stock.picking.type'].search([
            ('company_id', '=', self.company_id.id),
            ('code', '=', 'incoming'),
            ('default_location_dest_id', '=', location_dest_id.id),
        ], limit=1)

        values = self._prepare_subcon_transfer_vals(workorders.byproduct_ids | workorders.move_finished_ids, picking_type_id, location_id, location_dest_id)
        values.update({
            'subcon_requisition_id': self.requisition_id.id,
            'subcon_finished_workorder_ids': [(6, 0, workorders.ids)]
        })
        return values

    def button_confirm(self):
        res = super(PurchaseOrder, self).button_confirm()
        for record in self.filtered(lambda o: o.is_a_subcontracting):
            production_id = record.subcon_production_id
            requisition_id = record.requisition_id

            # TODO: should split move_raw_ids and move_finished_ids instead of workorders?
            workorder_ids = production_id.split_workorders(record)
            subcon_workorders = workorder_ids.filtered(lambda w: w.is_a_subcontracting)

            if not requisition_id:
                subcon_picking_values = [(0, 0, record._prepare_subcon_delivery_vals(subcon_workorders))]
            else:
                picking_ids = self.env['stock.picking'].search([('subcon_requisition_id', '=', requisition_id.id)])
                subcon_picking_values = [(4, picking.id) for picking in picking_ids]

            subcon_picking_values += [(0, 0, record._prepare_subcon_receipt_vals(subcon_workorders))]
            record.write({'subcon_picking_ids': subcon_picking_values})

            production_id.button_unplan()
            production_id.button_plan()

        return res
    
    def create_blanket_order(self):
        res = super(PurchaseOrder, self).create_blanket_order()
        requisition = self.env['purchase.requisition']
        for record in self:
            if record.is_a_subcontracting:
                requisition_id = requisition.search([('purchase_id', '=', record.id)])
                if requisition_id:
                    record.requisition_id = requisition_id.id
        return res

    def _create_picking(self):
        # ignore _create_picking for subcontracting orders
        return super(PurchaseOrder, self.filtered(lambda o: not o.is_a_subcontracting))._create_picking()
