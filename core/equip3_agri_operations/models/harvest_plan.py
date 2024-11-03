from odoo import models, fields, api, _


class HarvestPlan(models.Model):
    _inherit = 'agriculture.daily.activity'

    daily_activity_type = fields.Selection(selection_add=[('harvest', 'Harvest')], ondelete={'harvest': 'cascade'})
    harvest_transfer_ids = fields.One2many('internal.transfer', 'agri_harvest_plan_id', string='Harvest Transfers')
    harvest_transfer_count = fields.Integer(compute='_compute_harvest_internal_transfer')

    any_harvest_logging = fields.Boolean(compute='_compute_activity_types')
    crop_move_ids = fields.One2many('stock.move', 'agri_crop_move_plan_id', string='Harvest Crop Moves')

    @api.depends('crop_activity_ids')
    def _compute_activity_types(self):
        super(HarvestPlan, self)._compute_activity_types()
        for record in self:
            record.any_harvest_logging = any(act.activity_type == 'harvest' and act.harvest_type == 'logging' for act in record.crop_activity_ids)

    @api.depends('harvest_transfer_ids')
    def _compute_harvest_internal_transfer(self):
        for record in self:
            record.harvest_transfer_count = len(record.harvest_transfer_ids)

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
        if self.any_harvest_logging:
            records |= self.crop_move_ids
        return super(HarvestPlan, self).action_view_stock_moves(records)
