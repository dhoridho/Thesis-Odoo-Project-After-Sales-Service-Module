# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from datetime import date
from odoo import tools


class StockPickingBatch(models.Model):
    _inherit = 'stock.picking.batch'

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else False




    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    @api.model
    def _domain_branch_warehouse(self):
        return [('branch_id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    @api.model
    def _domain_company(self):
        return [('id','=', self.env.company.id)]
        

    location_ids = fields.Many2many('stock.location', 'stock_location_picking_batch_rel', 'location_id',
                                    'batch_id', string='Locations', required=True, tracking=True, states={'draft': [('readonly', False)]})
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse", domain=_domain_branch_warehouse)
    company_id = fields.Many2one(related='warehouse_id.company_id',domain=_domain_company, store=True)
    branch_id = fields.Many2one('res.branch',
                                related="warehouse_id.branch_id",
                                domain=_domain_branch,
                                default = _default_branch,
                                string='Branch',
                                tracking=True,
                                readonly=True)
    filter_location_ids = fields.Many2many(
        'stock.location', string='Location', store=False)
    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation Type', check_company=True, copy=False,
        readonly=True, states={'draft': [('readonly', False)]}, tracking=True,
        domain="['|', '|', ('default_location_src_id', 'in', location_ids), \
                ('default_location_dest_id', 'in', location_ids), \
                '&', ('default_location_src_id', 'in', location_ids), \
                ('default_location_dest_id', 'in', location_ids)]")
    scheduled_date = fields.Datetime(
        'Scheduled Date', tracking=True, copy=False, store=True, readonly=False, compute="_compute_scheduled_date",
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help="""Scheduled date for the transfers to be processed.
              - If manually set then scheduled date for all transfers in batch will automatically update to this date.
              - If not manually changed and transfers are added/removed/updated then this will be their earliest scheduled date
                but this scheduled date will not be set for all transfers in batch.""")
    partner_id = fields.Many2one(
        related="user_id.partner_id", string='Partner')
    stock_picking_batch_ids = fields.One2many(
        'stock.picking.batch.line', 'picking_batch_id', string="Stock Picking Batch Line")

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('picking.batch')
        return super().create(vals)

    @api.onchange('warehouse_id')
    def _get_filter_locations(self):
        for record in self:
            warehouse = record.warehouse_id
            context = dict(self.env.context or {})
            location_ids = []

            if warehouse:
                domain = [('warehouse_id', '=', warehouse.id),
                          ('usage', '=', 'internal')]

                if context.get('batch_picking'):
                    domain.extend([
                        ('name', 'not ilike', 'Output'),
                        ('name', 'not ilike', 'Packing'),
                    ])
                elif context.get('batch_packing'):
                    domain.extend([
                        ('name', 'ilike', 'Packing'),
                    ])
                elif context.get('batch_delivery'):
                    domain.extend([
                        ('name', 'ilike', 'Output'),
                    ])

                locations = self.env['stock.location'].search(domain)

                if locations:
                    location_ids = locations.ids

            record.filter_location_ids = [(6, 0, location_ids)]

    @api.depends('move_ids', 'move_ids.product_uom_qty', 'move_ids.reserved_availability', 'move_ids.quantity_done', 'move_line_ids', 'move_line_ids.product_uom_qty', 'move_line_ids.qty_done')
    def product_by_same_locations(self):
        for record in self:
            product_line_data = [(5, 0, 0)]
            temp_list = []
            line_list_vals = []
            # sorted_move_ids = sorted(record.move_ids, key=lambda move: (move.location_id.id, move.product_id.id))

            for line in record.move_ids:
                if {'product_id': line.product_id.id, 'location_id': line.location_id.id} in temp_list:
                    filter_list = list(filter(lambda r: r.get('product_id') == line.product_id.id and r.get('location_id') == line.location_id.id,  line_list_vals))
                    if filter_list:
                        filter_list[0]['demand_qty'].append(line.product_uom_qty)
                        filter_list[0]['reserved_qty'].append(line.reserved_availability if [line.reserved_availability] else [line.product_uom_qty])
                        filter_list[0]['done_qty'].append(line.quantity_done)
                else:
                    temp_list.append({'product_id': line.product_id.id, 'location_id': line.location_id.id})
                    line_list_vals.append({
                        'sequence': line.location_id.removal_priority,
                        'product_id': line.product_id.id,
                        'transfer_id': line.picking_id.id,
                        'name': line.product_id.name,
                        'origin': line.origin,
                        'location_id': line.location_id.id,
                        'demand_qty': [line.product_uom_qty],
                        'reserved_qty': [line.reserved_availability] if [line.reserved_availability] else [line.product_uom_qty],
                        'done_qty': [line.quantity_done],
                        'uom_id': line.product_id.uom_id.id,
                    })

            for final_line in line_list_vals:
                final_line['demand_qty'] = sum(final_line['demand_qty'])
                final_line['reserved_qty'] = sum(final_line['reserved_qty'])
                final_line['done_qty'] = sum(final_line['done_qty'])
                product_line_data.append((0, 0, final_line))
            record.stock_picking_batch_ids = product_line_data

    @api.depends('company_id', 'location_ids', 'state')
    def _compute_allowed_picking_ids(self):
        allowed_picking_states = ['waiting', 'confirmed', 'assigned']

        for batch in self:
            domain_states = list(allowed_picking_states)

            domain = [
                ('company_id', '=', batch.company_id.id),
                ('is_consignment', '=', False),
                ('state', 'in', domain_states),

            ]
            if batch.location_ids:
                domain += [('location_id', 'in', batch.location_ids.ids),
                           ('picking_type_code', 'in', ('outgoing', 'internal'))]
            batch.allowed_picking_ids = self.env['stock.picking'].search(
                domain)

    def _get_street(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_address_details(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.city:
            address = "%s" % (partner.city)
        if partner.state_id.name:
            address += ", %s" % (partner.state_id.name)
        if partner.zip:
            address += ", %s" % (partner.zip)
        if partner.country_id.name:
            address += ", %s" % (partner.country_id.name)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def action_confirm(self):
        res = super(StockPickingBatch, self).action_confirm()
        for record in self:
            for move in record.move_line_ids:
                if move.picking_id.state == 'assigned':
                    move.picking_id.picking_batch_id = record.id
                    record.product_by_same_locations()
        return res

    def action_force_validate(self):
        for record in self:
            for line in record.move_ids:
                if not line.reserved_availability:
                    line.quantity_done = line.product_uom_qty
                else:
                    line.quantity_done = line.reserved_availability
            record.product_by_same_locations()
            for line in record.stock_picking_batch_ids:
                if line.reserved_qty:
                    line.done_qty = line.reserved_qty
                else:
                    line.done_qty = line.demand_qty
            return record.action_done()

    @api.onchange('warehouse_id')
    def onchange_warehouse(self):
        self.location_ids = [(6, 0, [])]
        self.picking_ids = [(6, 0, [])]

    @api.onchange('location_ids')
    def _onchange_location_ids(self):
        for rec in self:
            if rec.location_ids:
                pickings = rec.picking_ids.filtered(
                    lambda r: r.location_id.id in rec.location_ids.ids)
                rec.picking_ids = [(6, 0, pickings.ids)]
            else:
                rec.picking_ids = [(6, 0, [])]

    def action_assign(self):
        data = []
        for record in self:
            move_ids = record.move_ids.filtered(lambda r: r.state in (
                'waiting', 'confirmed', 'partially_available'))
            if record.state == 'in_progress' and move_ids:
                for move_id in move_ids:
                    data.append((0, 0, {
                        'product_id': move_id.product_id.id,
                        'transfer_id': move_id.picking_id.id,
                        'location_id': move_id.location_id.id,
                        'product_uom_qty': move_id.product_uom_qty,
                        'reserved_availability': move_id.reserved_availability,
                    }))
                record.picking_ids.filtered(lambda r: r.state in (
                    'waiting', 'confirmed', 'partially_available')).action_assign()
                record.product_by_same_locations()
            else:
                for move_id in move_ids:
                    if move_id.reserved_availability < move_id.product_uom_qty:
                        return {
                            'name': "Insufficient Quantity To Validate",
                            'type': 'ir.actions.act_window',
                            'res_model': 'stock.picking.batch.validate',
                            'view_type': 'form',
                            'view_mode': 'form',
                            'target': 'new',
                            'context': {
                                'default_name': self.name,
                                'default_warehouse_id': self.warehouse_id.id,
                                'default_scheduled_date': self.scheduled_date,
                                'default_user_id': self.user_id.id,
                                'default_stock_line': data
                            }
                        }
        return super(StockPickingBatch, self).action_assign()

    # override function action_done
    def action_done(self):
        self.ensure_one()
        self._check_company()
        pickings = self.mapped('picking_ids').filtered(
            lambda picking: picking.state not in ('cancel', 'done'))

        for picking in pickings:
            picking.message_post(
                body="<b>%s:</b> %s <a href=#id=%s&view_type=form&model=stock.picking.batch>%s</a>" % (
                    _("Transferred by"),
                    _("Batch Transfer"),
                    picking.batch_id.id,
                    picking.batch_id.name))
        for record in self:
            record.product_by_same_locations()
        return pickings.button_validate()

    def action_draft(self):
        for rec in self:
            if rec.state == 'cancel':
                rec.write({'state': 'draft'})
        return True


class StockMove(models.Model):
    _name = 'stock.picking.batch.line'
    _description = 'Stock Picking Batch Line'

    sequence = fields.Integer(string='Sequence')
    transfer_id = fields.Many2one('stock.picking', string="Picking")
    product_id = fields.Many2one('product.product', string="Product")
    name = fields.Char(string="Description")
    location_id = fields.Many2one('stock.location', string="Source Location")
    demand_qty = fields.Float(string="Demand")
    reserved_qty = fields.Float(string="Reserved")
    done_qty = fields.Float(string="Done")
    uom_id = fields.Many2one('uom.uom', string="Unit of Measure")
    picking_batch_id = fields.Many2one(
        'stock.picking.batch', string="Stock Picking Batch")
    origin = fields.Char('Source Document')
