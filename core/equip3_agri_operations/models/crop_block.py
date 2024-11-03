from odoo import models, fields, api


class AgricultureCropBlock(models.Model):
    _inherit = 'crop.block'

    scheduled_ids = fields.One2many('crop.block.cron', 'block_id', string='Scheduled Activities')
    daily_activity_id = fields.Many2one('agriculture.daily.activity', string='Scheduled Plantation Plan')

    activity_line_ids = fields.One2many('agriculture.daily.activity.line', 'block_id', string='Plantation Lines')
    activity_history_ids = fields.One2many('agriculture.daily.activity.line', compute='_compute_activity_histories', string='Activity History')

    activity_harvest_ids = fields.One2many('stock.move', 'block_id', string='Harvest Moves', readonly=True)
    
    count_available = fields.Integer(compute="_compute_count_available_draft_progress")
    count_draft = fields.Integer(compute="_compute_count_available_draft_progress")
    count_progress = fields.Integer(compute="_compute_count_available_draft_progress")

    @api.depends('activity_line_ids', 'activity_line_ids.state')
    def _compute_activity_histories(self):
        for record in self:
            record.activity_history_ids = record.activity_line_ids.filtered(lambda a: a.state == 'done')

    def _compute_count_available_draft_progress(self):
        domains = {
            'count_draft': [('state', '=', 'draft')],
            'count_progress': [('state', '=', 'progress')],
            'count_available': [('state', 'in', ('draft', 'progress'))],
        }
        for field in domains:
            data = self.env['agriculture.daily.activity'].read_group(domains[field] +
                [('state', 'not in', ('to_be_approved', 'approved', 'rejected', 'confirm', 'done', 'cancel')), ('block_id', 'in', self.ids)],
                ['block_id'], ['block_id'])
            count = {
                x['block_id'][0]: x['block_id_count']
                for x in data if x['block_id']
            }
            for record in self:
                record[field] = count.get(record.id, 0)

    @api.model
    def create(self, vals):
        records = super(AgricultureCropBlock, self).create(vals)
        for record in records:
            record.check_daily_activity()
        return records

    def write(self, vals):
        res = super(AgricultureCropBlock, self).write(vals)
        if not vals.get('scheduled_ids'):
            return res
        for record in self:
            record.check_daily_activity()
        return res

    def check_daily_activity(self):
        self.ensure_one()
        if not self.scheduled_ids:
            self.daily_activity_id = False
            return
        if self.daily_activity_id:
            return
        daily_activity = self.env['agriculture.daily.activity'].create({'block_id': self.id})
        cron_values = {
            'name': _('Plantation Plan Notification'),
            'model_id': self.env.ref('equip3_agri_operations.model_agriculture_daily_activity').id,
            'state': 'code',
            'code': 'model._check_notification(%s)' % daily_activity.id,
            'user_id': self.env.ref('base.user_admin').id,
            'numbercall': 1,
            'nextcall': daily_activity.create_date + relativedelta(days=1),
            'interval_type': 'days',
            'interval_number': 1
        }
        self.env['ir.cron'].create(cron_values)
        self.daily_activity_id = daily_activity.id


class AgricultureCropBlockCron(models.Model):
    _name = 'crop.block.cron'
    _description = 'Block Scheduled Activities'

    @api.model
    def create(self, vals):
        vals['name'] = _('Auto Create Plantation Plan')
        vals['model_id'] = self.env.ref('equip3_agri_masterdata.model_crop_block_cron').id
        vals['state'] = 'code'
        vals['user_id'] = self.env.ref('base.user_admin').id
        vals['numbercall'] = -1
        records = super(AgricultureCropBlockCron, self).create(vals)
        for record in records:
            record.code = 'model.run_scheduler(%s)' % record.id
        return records

    def unlink(self):
        for record in self:
            if record.cron_id:
                record.cron_id.unlink()
        return super(AgricultureCropBlockCron, self).unlink()

    block_id = fields.Many2one('crop.block', string='Block', required=True, ondelete='cascade')
    activity_ids = fields.Many2many('crop.activity', string='Activities')

    cron_id = fields.Many2one('ir.cron', delegate=True, required=True, ondelete='cascade')

    def run_scheduler(self, schedule_id):
        schedule = self.browse(schedule_id)
        block = schedule.block_id
        daily_activity = block.daily_activity_id
        for activity in schedule.activity_ids:
            self.env['agriculture.daily.activity.line'].create({
                'daily_activity_id': daily_activity.id,
                'activity_id': activity.id, 
                'block_id': block.id,
                'crop_ids': [(6, 0, block.crop_ids.ids)],
                'harvest': activity.group_id.category_id.value == 'harvest',
                'nursery': activity.group_id.category_id.value == 'nursery',
                'notes': _('Scheduled action %s' % fields.Datetime.now()),
            })
        daily_activity._onchange_line_ids()
        daily_activity._set_line_ids()
        daily_activity._onchange_block_id()
        daily_activity._onchange_date_scheduled()
