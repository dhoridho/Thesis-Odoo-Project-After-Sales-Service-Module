from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BatchPicking(models.Model):
    _inherit = 'stock.picking.batch'

    branch_id2 = fields.Many2one('res.branch',
                                 default=lambda self: self.env.branches if len(
                                     self.env.branches) == 1 else False,
                                 domain=lambda self: [
                                     ('id', 'in', self.env.branches.ids)],
                                 string='Branch',
                                 tracking=True,
                                 readonly=False)

    def action_serialize(self):
        filter_move_lot_line = self.move_ids.filtered(
            lambda r: r.product_id.tracking == 'lot' and r.product_id.is_in_autogenerate)
        if filter_move_lot_line:
            context = dict(self._context or {})
            context.update({
                'default_picking_batch_id': self.id,
                'default_is_picking_batch': True
            })
            return {
                'name': 'Lot Serializer',
                'view_mode': 'form',
                'res_model': 'stock.lot.serialize',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'context': context,
                'target': 'new',
            }
        else:
            for rec in self:
                for move in rec.move_ids:
                    if move.product_id.tracking == 'serial' and move.product_id.is_sn_autogenerate:
                        if move.fulfillment < 100:
                            move._generate_serial_numbers()
                # rec._reset_sequence()

    def batch_label_report(self):
        for rec in self.move_ids:
            variant_product = rec._get_combination_name_variant()
            lot_ids = self.move_line_ids.mapped('lot_id')
            if not lot_ids:
                raise UserError(
                    'Barcode/Lot(s) are empty, or probably has not been registered to the system! Ensure to validate the Receipt first before printing.')

            data_varian = []  # Initialize an empty list to store dictionaries
            for attribut in variant_product:
                varian_data = {
                    'name': attribut.attribute_id.name,
                    'value': attribut.name
                }
                # Append the dictionary to the list
                data_varian.append(varian_data)

            data = {'lot_ids': lot_ids.ids, 'attributes_name': data_varian}

            report_action = self.env.ref(
                'stock.action_report_lot_label').report_action(lot_ids, data=data)
        return report_action

    def _sanity_check(self):
        for batch in self:
            if not batch.allowed_picking_ids:
                batch.batch.allowed_picking_ids()
            if not batch.picking_ids <= batch.allowed_picking_ids:
                erroneous_pickings = batch.picking_ids - batch.allowed_picking_ids
                # raise UserError(_(
                #     "The following transfers cannot be added to batch transfer %s. "
                #     "Please check their states and operation types, if they aren't immediate "
                #     "transfers or if they're not already part of another batch transfer.\n\n"
                #     "Incompatibilities: %s", batch.name, ', '.join(erroneous_pickings.mapped('name'))))

    no_container = fields.Char(string='Nomor Container')
    total_dpl_roll = fields.Float(
        string='Total DPL Roll Qty', compute='_compute_total_roll_dpl')
    total_dpl_qty = fields.Float(
        string='Total DPL Qty', compute='_compute_total_qty_dpl')
    total_actual_roll = fields.Float(
        string='Total Actual Roll', compute='_compute_total_actual_roll')
    total_actual_qty = fields.Float(
        string='Total Actual Qty', compute='_compute_total_actual_qty')
    no_invoice = fields.Char(string='No. Invoice')
    doc_type = fields.Selection([("po", "Purchase Order"),
                                 ("so", "Sales Order"),
                                 ("rn", "Receiving Notes"),
                                 ("do", "Delivery Order"),
                                 ("it_in", "Internal Transfer In"),
                                 ("it_oot", "Internal Transfer Out"),
                                 ], string='Document Type')

    purchase_ids = fields.Many2many(
        comodel_name='purchase.order',
        string='Purchase Order'
    )
    sale_ids = fields.Many2many(
        comodel_name='sale.order',
        string='Sale Order'
    )

    def auto_dpl_quantity(self):
        for move in self.move_ids.filtered(lambda a: a.dpl_quantity != a.quantity_done):
            move.write({'dpl_quantity': move.quantity_done})
            move.write({'qty_to_generate': move.quantity_done})

    def auto_conf_quantity(self):
        for move in self.move_ids.filtered(lambda a: a.conf_qty != a.quantity_done):
            move.write({'conf_qty': move.quantity_done})

    @api.depends('move_ids.dpl_roll_qty')
    def _compute_total_roll_dpl(self):
        for rec in self:
            rec.total_dpl_roll = sum(rec.move_ids.mapped('dpl_roll_qty'))

    @api.depends('move_ids.dpl_quantity')
    def _compute_total_qty_dpl(self):
        for rec in self:
            rec.total_dpl_qty = sum(rec.move_ids.mapped('dpl_quantity'))

    @api.depends('move_ids.actual_roll')
    def _compute_total_actual_roll(self):
        for rec in self:
            rec.total_actual_roll = sum(rec.move_ids.mapped('actual_roll'))

    @api.depends('move_ids.quantity_done')
    def _compute_total_actual_qty(self):
        for rec in self:
            rec.total_actual_qty = sum(rec.move_ids.mapped('quantity_done'))

    def add_no_container_to_lot(self):
        print("\n \n \n jalanin ini")
        if self.no_container:
            move_lines = self.move_line_ids.ids

            sql = """
            UPDATE stock_production_lot AS lot
                SET no_container = %s
                FROM stock_move_line AS smv
                WHERE lot.id = smv.lot_id
                AND smv.id IN %s """

            self.env.cr.execute(
                sql, (str(self.no_container), tuple(move_lines)))
        else:
            return

    @api.depends('picking_ids', 'picking_ids.state')
    def _compute_state(self):
        batchs = self.filtered(
            lambda batch: batch.state not in ['cancel', 'done'])
        for batch in batchs:
            if not batch.picking_ids:
                return
            # Cancels automatically the batch picking if all its transfers are cancelled.
            if all(picking.state == 'cancel' for picking in batch.picking_ids):
                batch.state = 'cancel'
            # Batch picking is marked as done if all its not canceled transfers are done.
            elif all(picking.state in ['cancel', 'done'] for picking in batch.picking_ids):
                batch.state = 'done'
                batch.add_no_container_to_lot()

    def action_done(self):
        # search_qty_not_same = self.move_ids.filtered(
        #     lambda a: a.dpl_quantity != a.quantity_done)
        # if search_qty_not_same:
        #     context = dict(self.env.context or {})
        #     if 'Confirm_dpl_quantity' in context:
        #         Confirm_dpl_quantity = True

        #     else:
        #         return {
        #             'type': 'ir.actions.act_window',
        #             'name': 'Confirm DPL Quantity',
        #             'res_model': 'confirm.dpl.qty',
        #             'view_type': 'form',
        #             'view_mode': 'form',
        #             'target': 'new',
        #             'context': {'default_bacth_id': self.id, 'default_move_ids': search_qty_not_same.ids},
        #         }

        self.auto_conf_quantity()
        res = super(BatchPicking, self).action_done()
        self.add_no_container_to_lot()

        return res

    @api.depends('company_id', 'location_ids', 'state', 'doc_type', 'purchase_ids', 'sale_ids')
    def _compute_allowed_picking_ids(self):
        allowed_picking_states = ['waiting', 'confirmed', 'assigned']
        for batch in self:
            domain_states = list(allowed_picking_states)
            domain = [
                ('company_id', '=', batch.company_id.id),
                ('is_consignment', '=', False),
                ('state', 'in', domain_states),
            ]

            domain_warehouse = []

            # print("\n \n \n _compute_allowed_picking_ids")
            if batch.doc_type:
                if batch.doc_type == 'so':
                    if batch.sale_ids:
                        picking = batch.sale_ids.mapped('picking_ids')
                        domain += [('id', 'in', picking.ids)]

                        domain_warehouse += [('id', 'in',
                                              batch.sale_ids.mapped('warehouse_new_id').ids)]
                elif batch.doc_type == 'po':
                    if batch.purchase_ids:
                        picking = batch.purchase_ids.mapped('picking_ids').ids
                        domain += [('id', 'in', picking)]

                        domain_warehouse += [('id', 'in',
                                              batch.purchase_ids.mapped('destination_warehouse_id').ids)]

                elif batch.doc_type == 'do':
                    if batch.location_ids:
                        domain += [('location_id', 'in', batch.location_ids.ids),
                                   ('picking_type_code', 'in', ('outgoing', 'outgoing'))]
                elif batch.doc_type == 'rn':
                    if batch.location_ids:
                        domain += [('location_dest_id', 'in', batch.location_ids.ids),
                                   ('picking_type_code', 'in', ('incoming', 'incoming'))]
                elif batch.doc_type == 'it_in':
                    if batch.location_ids:
                        domain += [('location_id', 'in', batch.location_ids.ids), ('picking_type_code',
                                                                                   'in', ('internal', 'internal')), ('is_transfer_in', '=', True)]
                elif batch.doc_type == 'it_oot':
                    if batch.location_ids:
                        domain += [('location_dest_id', 'in', batch.location_ids.ids), ('picking_type_code',
                                                                                        'in', ('internal', 'internal')), ('is_transfer_in', '=', False)]
                else:
                    if batch.location_ids:
                        domain += [('location_id', 'in',
                                    batch.location_ids.ids)]

            print("domain", domain)
            print("domain_warehouse", domain_warehouse)
            batch.allowed_picking_ids = self.env['stock.picking'].search(
                domain)
            batch.allowed_warehouse_ids = self.env['stock.warehouse'].search(
                domain_warehouse)

    allowed_picking_ids = fields.One2many(
        'stock.picking', compute='_compute_allowed_picking_ids')
    allowed_warehouse_ids = fields.One2many(
        'stock.warehouse', compute='_compute_allowed_picking_ids')

    @api.onchange('purchase_ids', 'sale_ids')
    def onchange_purchase_sale(self):
        for doc in self:
            # company_id', 'location_ids', 'state', 'doc_type', 'purchase_ids', 'sale_ids

            if doc.purchase_ids:

                location_ids = doc.purchase_ids.mapped(
                    'picking_ids').mapped('location_dest_id')
                doc.location_ids = [(6, 0, location_ids.ids)]

            if doc.sale_ids:
                location_ids = doc.sale_ids.mapped(
                    'picking_ids').mapped('location_id')
                doc.location_ids = [(6, 0, location_ids.ids)]

    @api.onchange('doc_type')
    def onchange_doc_type(self):
        for doc in self:
            # company_id', 'location_ids', 'state', 'doc_type', 'purchase_ids', 'sale_ids

            doc.purchase_ids = [(5, 0, 0)]
            doc.sale_ids = [(5, 0, 0)]
            doc.location_ids = [(5, 0, 0)]
            doc.no_container = False

    @api.onchange('allowed_warehouse_ids')
    def onchange_warehouse(self):
        for doc in self:
            if doc.allowed_warehouse_ids and doc.doc_type in ('po', 'so'):
                doc.warehouse_id = doc.allowed_warehouse_ids[0]

    filter_location_ids = fields.Many2many(
        'stock.location', string='Location', compute='_get_filter_locations', store=False)

    @api.depends('warehouse_id')
    def _get_filter_locations(self):
        location_ids = []
        for record in self:
            if record.warehouse_id:
                location_obj = self.env['stock.location']
                store_location_id = record.warehouse_id.view_location_id.id
                addtional_ids = location_obj.search(
                    [('location_id', 'child_of', store_location_id), ('usage', '=', 'internal')])
                for location in addtional_ids:
                    if location.location_id.id not in addtional_ids.ids:
                        location_ids.append(location.id)
                child_location_ids = self.env['stock.location'].search(
                    [('id', 'child_of', location_ids), ('id', 'not in', location_ids)]).ids
                final_location = child_location_ids + location_ids
                record.filter_location_ids = [(6, 0, final_location)]
            else:
                record.filter_location_ids = [(6, 0, [])]

    def write(self, vals):
        res = super(BatchPicking, self).write(vals)
        if 'dpl_line_ids' in vals:
            for line in vals['dpl_line_ids']:
                action, id_or_false, values = line
                dpl_line = self.env['dpl.line'].browse(id_or_false) if action == 1 else False
                if dpl_line:
                    if not dpl_line.is_generate:
                        move_line = self.move_ids.filtered(lambda m: m.id == dpl_line.move_id.id)
                        if move_line:
                            move_line.write({
                                'dpl_roll_qty': values.get('dpl_roll_qty'),
                                'quantity_done': values.get('quantity_done'),
                                'note': values.get('keterangan'),
                                'dpl_quantity': values.get('dpl_qty'),
                            })
                        dpl_line.is_generate = True
                        dpl_line.write({'is_generate': True})
                else:
                    new_dpl_line = self.env['dpl.line'].create(values)
                    move_line = self.move_ids.filtered(lambda m: m.id == values.get('move_id'))
                    if move_line:
                        move_line.write({
                            'dpl_roll_qty': values.get('dpl_roll_qty'),
                            'quantity_done': values.get('quantity_done'),
                            'note': values.get('keterangan'),
                            'dpl_quantity': values.get('dpl_qty'),
                        })
                    new_dpl_line.is_generate = True
                    new_dpl_line.write({'is_generate': True})
        return res

class DplLine(models.Model):
    _name = 'dpl.line'
    
    picking_batch_id = fields.Many2one('stock.picking.batch', string="Picking Batch")
    move_id = fields.Many2one('stock.move', string="Move ID")
    quantity_done = fields.Float(string="Quantity Done")
    keterangan = fields.Text(string="Keterangan")
    dpl_qty = fields.Float(string="DPL Quantity")
    dpl_roll_qty = fields.Float(string="DPL Roll Quantity")
    is_generate = fields.Boolean(string="Is Generated", default=False)
    company_id = fields.Many2one('res.company')

class StockPickingBatch(models.Model):
    _inherit = 'stock.picking.batch'

    dpl_line_ids = fields.One2many('dpl.line', 'picking_batch_id', string="DPL Lines")

class ConfirmDplQty(models.TransientModel):
    _name = 'confirm.dpl.qty'
    _description = 'confirm_dpl_qty'

    name = fields.Char(string='Name')

    bacth_id = fields.Many2one('stock.picking.batch', string='Batch Picking')
    move_ids = fields.Many2many(
        comodel_name='stock.move',
        string='Operation'
    )

    def process(self):
        for doc in self:
            doc.bacth_id.with_context(Confirm_dpl_quantity=True).action_done()
