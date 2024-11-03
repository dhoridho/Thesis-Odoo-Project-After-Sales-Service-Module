import json
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HarvestRecord(models.Model):
    _inherit = 'agriculture.daily.activity.record'

    daily_activity_type = fields.Selection(selection_add=[('harvest', 'Harvest')], ondelete={'harvest': 'cascade'})
    harvest_transfer_line_ids = fields.One2many('agriculture.harvest.transfer', 'activity_record_id', string='Harvest Transfer')

    harvest_transfer_ids = fields.One2many('internal.transfer', 'agri_harvest_record_id', string='Harvest Transfers')
    harvest_transfer_count = fields.Integer(compute='_compute_harvest_internal_transfer')

    crop_move_ids = fields.One2many('stock.move', 'agri_crop_move_record_id', string='Harvest Crop Moves')

    can_serialize_harvest = fields.Boolean(compute='_compute_can_serialize_harvest')

    @api.depends('harvest_ids')
    def _compute_can_serialize_harvest(self):
        for record in self:
            to_serialize_moves = record.harvest_ids.filtered(lambda o: o.agri_product_tracking in ('lot', 'serial') and not o.harvest_serialize_data)
            record.can_serialize_harvest = len(to_serialize_moves) > 0

    @api.depends('harvest_transfer_ids')
    def _compute_harvest_internal_transfer(self):
        for record in self:
            record.harvest_transfer_count = len(record.harvest_transfer_ids)
    
    def _process_transfer(self):
        res = super(HarvestRecord, self)._process_transfer()
        if self.category_type == 'harvest':
            for line in self.harvest_transfer_line_ids:
                line._create_internal_transfer()
        return res

    def _process_harvest_logging(self):
        self.ensure_one()
        self._process_harvest_fruit_harvesting()

        crop_move_values = []
        for move in self.harvest_ids:
            if move.crop_id.crop_count < move.product_uom_qty:
                raise ValidationError(_("There's not enough crop quantity!"))
            
            production_location = move.crop_id.crop.with_company(self.company_id).property_stock_production
            crop_move_values += [{
                'agri_crop_move_record_id': self.id,
                'agri_crop_move_line_id': self.activity_line_id.id,
                'agri_crop_move_plan_id': self.daily_activity_id and self.daily_activity_id.id or False,
                'name': self.name,
                'origin': self.name,
                'product_id': move.crop_id.crop.id,
                'product_uom': move.product_uom.id,
                'date': fields.Date.today(),
                'product_uom_qty': move.quantity_done,
                'quantity_done': move.product_uom_qty,
                'location_id': self.block_id.location_id.id,
                'location_dest_id': production_location.id
            }]

            move.crop_id.crop_count -= move.product_uom_qty
        
        self.crop_move_ids = self.env['stock.move'].create(crop_move_values)
        self.crop_move_ids._action_done()

        reference = self.daily_activity_id and self.daily_activity_id.name or self.activity_line_id.name
        self.crop_move_ids.write({'name': reference, 'origin': reference})
        self.crop_move_ids.stock_valuation_layer_ids.update({
            'daily_activity_id': self.daily_activity_id and self.daily_activity_id.id or False,
            'activity_line_id': self.activity_line_id.id,
            'activity_record_id': self.id
        })
        self.write({'stock_valuation_layer_ids': [(4, svl.id) for svl in self.crop_move_ids.stock_valuation_layer_ids]})


    def action_view_harvest_internal_transfer(self):
        self.ensure_one()
        result = self.env['ir.actions.actions']._for_xml_id('equip3_inventory_operation.action_internal_transfer_request')
        records = self.harvest_transfer_ids
        if not records:
            return
        if len(records) > 1:
            result['domain'] = [('id', 'in', records.ids)]
        else:
            form_view = [(self.env.ref('equip3_inventory_operation.view_form_internal_transfer').id, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(s, v) for s, v in result['views'] if v != 'form']
            else:
                result['views'] = form_view
            result['res_id'] = records.id
        result['context'] = str(dict(eval(result.get('context') or '{}', self._context), create=False))
        return result

    def action_view_stock_moves(self, records):
        if self.activity_harvest_type == 'logging':
            records |= self.crop_move_ids
        return super(HarvestRecord, self).action_view_stock_moves(records)

    def action_harvest_serializer(self):
        self.ensure_one()
        for move in self.harvest_ids.filtered(lambda m: m.agri_product_tracking in ('lot', 'serial') and not m.harvest_serialize_data):
            wizard = self.env['agri.move.serializer'].with_context(default_move_id=move.id).create({'move_id': move.id})
            wizard.action_assign()
            wizard.action_confirm()
        return self.activity_line_id.action_actualization()

    def _process_harvest(self):
        self.ensure_one()
        company_id = self.company_id

        for move in self.harvest_ids.filtered(lambda m: m.agri_product_tracking in ('lot', 'serial') and m.harvest_serialize_data):
            move._action_confirm()
            record_name = self.name

            data = json.loads(move.harvest_serialize_data)
            move_line_values = [(5,)]
            for line in data['line_ids']:
                values = move._prepare_move_line_vals(quantity=line['quantity'])
                lot_id = self.env['stock.production.lot'].create({
                    'name': line['lot_name'],
                    'product_id': line['product_id'],
                    'company_id': company_id.id,
                    'ref': record_name
                })
                values.update({
                    'lot_id': lot_id.id,
                    'qty_done': line['quantity']
                })
                move_line_values += [(0, 0, values)]
            move.move_line_ids = move_line_values
        return super(HarvestRecord, self)._process_harvest()


class AgricultureHarvestTransfer(models.Model):
    _name = 'agriculture.harvest.transfer'
    _description = 'Agriculture Harvest Transfer'

    activity_record_id = fields.Many2one('agriculture.daily.activity.record', string='Harvest Record', required=True, ondelete='cascade')
    crop_id = fields.Many2one('agriculture.crop', string='Crop', required=True)
    block_id = fields.Many2one('crop.block', string='Current Block', required=True)
    location_id = fields.Many2one('stock.location', related='block_id.location_id', string='Current Location')
    block_crop_ids = fields.One2many(related='block_id.crop_ids')
    location_dest_id = fields.Many2one('stock.location', string='Destination Location', required=True)
    quantity = fields.Float(default=1.0)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    transfer_id = fields.Many2one('internal.transfer', string='Internal Transfer')

    @api.onchange('crop_id')
    def _onchange_crop_id(self):
        self.uom_id = self.crop_id and self.crop_id.crop.uom_id.id or False

    @api.constrains('quantity')
    def _check_quantity(self):
        for record in self:
            if record.quantity <= 0.0:
                raise ValidationError(_('Quantity must be positive!'))

    def _prepare_internal_transfer_values(self):
        self.ensure_one()
        harvest_record = self.activity_record_id
        harvest_line = harvest_record.activity_line_id
        harvest_plan  = harvest_line.daily_activity_id or self.env['agriculture.daily.activity']

        now = fields.Datetime.now()
        warehouse_id = self.location_id.get_warehouse().id
        warehouse_dest_id = self.location_dest_id.get_warehouse().id

        return {
            'agri_harvest_record_id': harvest_record.id,
            'agri_harvest_line_id': harvest_line.id,
            'agri_harvest_plan_id': harvest_plan.id,
            'requested_by': self.env.user.id,
            'source_warehouse_id': warehouse_id,
            'source_location_id': self.location_id.id,
            'destination_warehouse_id': warehouse_dest_id,
            'destination_location_id': self.location_dest_id.id,
            'company_id': harvest_record.company_id.id,
            'branch_id': harvest_record.branch_id.id,
            'scheduled_date': now,
            'source_document': harvest_record.name,
            'product_line_ids': [(0, 0, {
                'sequence': 1,
                'source_location_id': self.location_id.id,
                'destination_location_id': self.location_dest_id.id,
                'product_id': self.crop_id.crop.id,
                'description': self.crop_id.crop.display_name,
                'qty': self.quantity,
                'uom': self.uom_id.id,
                'scheduled_date': now,
                'analytic_account_group_ids': [(6, 0, harvest_record.analytic_group_ids.ids)]
            })],
            'analytic_account_group_ids': [(6, 0, harvest_record.analytic_group_ids.ids)]
        }

    def _create_internal_transfer(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('equip3_inventory_operation.action_internal_transfer_request')
        context = dict(eval(action.get('context') or '{}', self.env.context))

        transfer_values = self._prepare_internal_transfer_values()
        transfer = self.env['internal.transfer'].with_context(context).create(transfer_values)
        transfer.onchange_source_loction_id()
        transfer.onchange_dest_loction_id()
