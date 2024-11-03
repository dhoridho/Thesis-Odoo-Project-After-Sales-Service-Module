import json
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MRPProduction(models.Model):
    _inherit = 'mrp.production'

    def _compute_lot_ids(self):
        for production in self:
            consumption_ids = production.consumption_ids
            lot_ids = consumption_ids.finished_lot_ids | consumption_ids.rejected_lot_ids
            production.lot_ids = [(6, 0, lot_ids.ids)]

    has_clicked_mark_done = fields.Boolean()
    consumption_ids = fields.One2many('mrp.consumption', 'manufacturing_order_id', string='Production Records', readonly=True)
    
    lot_ids = fields.Many2many('stock.production.lot', string='Lot/Serial Numbers', compute=_compute_lot_ids)
    reservation_state = fields.Selection(tracking=False)

    rejected_product_id = fields.Many2one('product.product', string='Rejected Goods')

    finished_product_qty = fields.Float('Finished Quantity', digits='Product Unit of Measure', readonly=True)
    rejected_product_qty = fields.Float('Rejected Quantity', digits='Product Unit of Measure', readonly=True)

    """ Technical fields.
    To keep original BoM data when Production Order confirmed.
    Odoo doesn't allow editing confirmed moves which is the main problem for MPR, 
    since BoM may change when MO is confirmed but MPR is still in draft state.
    Rather than creating multiple duplicates of each BoM fields, 
    this one field will save the BoM data as soon as the MO is confirmed and loaded for MPR purposes."""
    bom_data = fields.Text(readonly=True)

    @api.onchange('bom_id')
    def _set_bom_fields(self):
        super(MRPProduction, self)._set_bom_fields()
        self.rejected_product_id = self.bom_id.rejected_product_id.id

    def _set_qty_producing(self):
        pass

    @api.depends('move_raw_ids.state', 'move_raw_ids.quantity_done', 'move_finished_ids.state',
    'workorder_ids', 'workorder_ids.state', 'product_qty', 'qty_producing', 'has_clicked_mark_done')
    def _compute_state(self):
        super(MRPProduction, self)._compute_state()
        for production in self:
            workorders = production.workorder_ids
            if production.has_clicked_mark_done:
                production.state = 'done'
            elif any(wo_state in ('progress', 'pause') for wo_state in workorders.mapped('state')):
                production.state = 'progress'
            elif any(wo_state in ('ready', 'block') for wo_state in workorders.mapped('state')) and any(
                    wo_duration > 0 for wo_duration in workorders.mapped('duration')):
                production.state = 'progress'
            elif any(wo_state != 'progress' and wo_state == 'block' for wo_state in workorders.mapped('state')):
                production.state = 'confirmed'
            elif workorders:
                if production.state == 'done' or all(wo_state == 'done' for wo_state in workorders.mapped('state')):
                    production.state = 'to_close'

            production.reservation_state = False
            if production.state not in ('draft', 'done', 'cancel'):
                relevant_move_state = production.move_raw_ids._get_relevant_state_among_moves()
                if relevant_move_state == 'partially_available':
                    if production.bom_id.operation_ids and production.bom_id.ready_to_produce == 'asap':
                        production.reservation_state = production._get_ready_to_produce_state()
                    else:
                        production.reservation_state = 'confirmed'
                elif relevant_move_state != 'draft':
                    production.reservation_state = relevant_move_state

    def button_mark_done(self):
        warning = self.env['button.mark.done.warning']
        skip_all_wo_done = self.env.context.get('skip_all_wo_done')

        for production_id in self:
            workorder_ids = production_id.workorder_ids

            if not skip_all_wo_done:
                all_workorder_done = all(wo.state in ('done', 'cancel') for wo in workorder_ids)
                if not all_workorder_done:
                    warning_id = warning.create({
                        'production_id': production_id.id,
                        'message': _('There are unfinished work order, are you sure want to force done?')
                    })
                    return warning_id.open_self()

            for workorder in workorder_ids:
                if workorder.state == 'progress':
                    if workorder.is_user_working:
                        raise UserError(_('Please finish work order %s first!' % workorder.workorder_id))
                    else:
                        workorder.with_context(bypass_consumption=True).button_finish()
                        move_to_cancel = (production_id.move_raw_ids | production_id.move_finished_ids).filtered(
                            lambda m: m.byproduct_id and workorder in (m.workorder_id, m.mrp_workorder_component_id, m.mrp_workorder_byproduct_id) and m.state != 'done')
                        move_to_cancel._action_cancel()

                elif workorder.state in ('pending', 'ready'):
                    workorder.action_cancel()
                    move_to_cancel = production_id.move_raw_ids | production_id.move_finished_ids.filtered(
                        lambda m: m.byproduct_id and workorder in (m.workorder_id, m.mrp_workorder_component_id, m.mrp_workorder_byproduct_id))
                    move_to_cancel._action_cancel()

            production_id.write({
                'has_clicked_mark_done': True,  # will trigger state to done (see compute_state)
                'date_finished': fields.Datetime.now(),
                'priority': '0',
                'is_locked': True,
            })
            production_id.move_raw_ids.filtered(lambda m: m.state not in ('done', 'cancel'))._action_cancel()

    def _read_bom_data(self, origin=False):
        """ Returns the .read() of the current BoM 
        (and updates it with the original BoM data if param origin is True). """

        def _get_fields(model_name):
            """ Reading all fields with .read() is too much, 
            therefore the fields to read (and save) are defined in each model 
            via `_fields_to_dump` method. See mrp_bom.py """

            model = self.env[model_name].sudo()
            field_list = ['id', 'display_name']
            try:
                field_list += model._fields_to_dump()
            except AttributeError:
                pass
            return {fname: model._fields[fname] for fname in field_list}

        def _read_records(records, level=0, max_level=1):
            records = records.sudo()
            fields_to_dump = _get_fields(records._name)
            relational_fields = {
                field_name: field
                for field_name, field in fields_to_dump.items()
                if field.type in ('many2one', 'one2many', 'many2many')}
    
            record_datas = records.read(fields_to_dump.keys())
            for record_data in record_datas:
                record = records.filtered(lambda r: r.id == record_data['id'])
                for field_name, field in relational_fields.items():
                    fields_to_dump = _get_fields(field.comodel_name)
                    if field.type == 'many2one':
                        field_data = record[field_name].read(fields_to_dump.keys())
                        if field_data:
                            field_data = field_data[0]
                        else:
                            field_data = {'id': False}
                    else:
                        if level < max_level:
                            field_data = _read_records(record[field_name], level=level+1)
                        else:
                            field_data = record[field_name].read(fields_to_dump.keys())
                    record_data[field_name] = field_data
            return record_datas

        """ Read BoM data and it's fields recursively """
        datas = _read_records(self.mapped('bom_id'))

        if origin:
            """ Update BoM data with it's origin data when MO is confirmed """
            for data in datas:
                production = self.filtered(lambda p: p.bom_id.id == data['id'])
                origin_data = json.loads(production.bom_data or '{}')
                data.update(origin_data)

        return {d['id']: d for d in datas}

    def _dump_bom_data(self):
        """ In case action_confirm called from Production Plan, `self` can be more than 1 record. """
        bom_datas = self._read_bom_data()

        for production in self:
            bom_data = bom_datas.get(production.bom_id.id, dict())
            production.write({'bom_data': json.dumps(bom_data, default=str)})

            for workorder in production.workorder_ids:
                workorder.write({'origin_operation_id': workorder.operation_id.id})

            for move in (production.move_raw_ids | production.move_finished_ids):
                if move.bom_line_id:
                    values = {
                        'origin_bom_line_id': move.bom_line_id.id,
                        'origin_operation_id': move.operation_id.id
                    }
                elif move.byproduct_id:
                    values = {
                        'origin_byproduct_id': move.byproduct_id.id,
                        'origin_operation_id': move.operation_id.id
                    }
                elif move.production_id:
                    values = {
                        'origin_finished_id': move.finished_id.id
                    }
                move.write(values)


    def action_confirm(self):
        result = super(MRPProduction, self).action_confirm()

        """ Dump BoM data to load later """
        self._dump_bom_data()

        return result
