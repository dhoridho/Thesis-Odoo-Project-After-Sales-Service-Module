from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ast import literal_eval
from dateutil.relativedelta import relativedelta


class AgricultureCropPhase(models.Model):
    _name = 'crop.phase'
    _description = 'Crop Phase Management'

    PERIOD = [
        ('year', 'Year(s)'),
        ('month', 'Month(s)')
    ]

    name = fields.Char(string='Name', required=True)
    crop_age = fields.Integer(string='Crop Age', default=1)
    period = fields.Selection(PERIOD, string='Period')
    crop_age_str = fields.Char(string='Crop Age', compute='_get_crop_age_str')

    @api.depends('crop_age', 'period')
    def _get_crop_age_str(self):
        for crop_phase in self:
            if crop_phase.period and crop_phase.period == 'year':
                crop_phase.crop_age_str = str(crop_phase.crop_age) + " Year(s)"
            elif crop_phase.period and crop_phase.period == 'month':
                crop_phase.crop_age_str = str(crop_phase.crop_age) + " Month(s)"
            else:
                crop_phase.crop_age_str = str(crop_phase.crop_age)


class AgricultureCropEstate(models.Model):
    _name = 'crop.estate'
    _inherit = ['image.mixin']
    _description = 'Crop Estate Management'

    @api.depends('block_ids', 'block_ids.size')
    def _compute_area(self):
        for record in self:
            record.size = sum(record.block_ids.mapped('size'))

    name = fields.Char(string='Estate Name', required=True)
    location_id = fields.Many2one('stock.location', string='Location', required=True)
    size = fields.Float(string='Area', compute=_compute_area)
    uom_id = fields.Many2one('uom.uom', string='UOM', required=True)
    division_ids = fields.One2many('agriculture.division', 'estate_id', string='Divisions')
    block_ids = fields.One2many('crop.block', 'estate_id', string='Blocks')


class AgricultureDivision(models.Model):
    _name = 'agriculture.division'
    _inherit = ['image.mixin']
    _description = 'Agriculture Division'

    @api.depends('block_ids', 'block_ids.size')
    def _compute_area(self):
        for record in self:
            record.area = sum(record.block_ids.mapped('size'))

    name = fields.Char(required=True, copy=False, string='Division Name')
    estate_id = fields.Many2one('crop.estate', string='Estate', required=True)
    area = fields.Float(string='Area', digits='Product Unit of Measure', compute=_compute_area)
    area_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    block_ids = fields.One2many('crop.block', 'division_id', string='Blocks', readonly=True)


class AgricultureCrop(models.Model):
    _name = 'agriculture.crop'
    _inherit = ['image.mixin']
    _description = 'Crop Management'
    _rec_name = 'crop'
    
    def name_get(self):
        result = []
        for record in self:
            name = '%s - %s - %s' % (record.crop.display_name, record.crop_count, record.uom_id.display_name)
            result.append((record.id, name))
        return result

    crop = fields.Many2one('product.product', string='Crop', required=True, domain="[('is_agriculture_product', '=', True)]")
    block_id = fields.Many2one('crop.block', string='Block', readonly=True)
    crop_count = fields.Float(string='Crop Count', default=1.0)
    crop_date = fields.Date(string='Crop Date', required=1)
    crop_phase = fields.Many2one('crop.phase', string='Crop Phase')
    crop_age = fields.Char(string='Crop Age', related='crop_phase.crop_age_str')
    uom_id = fields.Many2one('uom.uom', string='UOM')

    origin = fields.Char(readonly=True)


class AgricultureCropBlock(models.Model):
    _name = 'crop.block'
    _inherit = ['image.mixin']
    _description = 'Crop Block Management'

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
            'name': _('Daily Activity Notification'),
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
            
    @api.depends('activity_line_ids', 'activity_line_ids.state')
    def _compute_activity_histories(self):
        for record in self:
            record.activity_history_ids = record.activity_line_ids.filtered(lambda a: a.state == 'done')

    name = fields.Char(string='Name', required=True)
    estate_id = fields.Many2one('crop.estate', string='Estate', required=True)
    size = fields.Float(string='Area', default=1.0)
    uom_id = fields.Many2one('uom.uom', string='UOM', required=True)
    crop_ids = fields.One2many('agriculture.crop', 'block_id', string='Crops', readonly=True)
    division_id = fields.Many2one('agriculture.division', string='Division', domain="[('estate_id', '=', estate_id)]", store=True)

    activity_line_ids = fields.One2many('agriculture.daily.activity.line', 'block_id', string='Activity Lines')
    activity_history_ids = fields.One2many('agriculture.daily.activity.line', compute=_compute_activity_histories, string='Activity History')

    activity_harvest_ids = fields.One2many('stock.move', 'block_id', string='Harvest Moves', readonly=True)
    
    count_available = fields.Integer(compute="_compute_count_available_draft_progress")
    count_draft = fields.Integer(compute="_compute_count_available_draft_progress")
    count_progress = fields.Integer(compute="_compute_count_available_draft_progress")

    scheduled_ids = fields.One2many('crop.block.cron', 'block_id', string='Scheduled Activities')
    daily_activity_id = fields.Many2one('agriculture.daily.activity', string='Scheduled Daily Activity')

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
            
    def _get_action(self, action_xmlid):
        action = self.env.ref(action_xmlid).read()[0]
        if self:
            action['division_id'] = self.division_id.id
        context = {
            'search_default_block_id': [self.id],
            'default_block_id': self.id,
            'default_division_id': self.division_id.id,
        }
        action_context = literal_eval(action['context'])
        context = {**action_context, **context}
        action['context'] = context
        return action
                
    def get_action_activity_available(self):
        for r in self:
            return r._get_action('equip3_agri_operations.agriculture_daily_activity_available_action')
    
    def get_action_activity_draft(self):
        for r in self:
            return r._get_action('equip3_agri_operations.agriculture_daily_activity_draft_action')
    
    def get_action_activity_progress(self):
        for r in self:
            return r._get_action('equip3_agri_operations.agriculture_daily_activity_progress_action')


class AgricultureCropBlockCron(models.Model):
    _name = 'crop.block.cron'
    _description = 'Block Scheduled Activities'

    @api.model
    def create(self, vals):
        vals['name'] = _('Auto Create Daily Activity')
        vals['model_id'] = self.env.ref('equip3_agri_operations.model_crop_block_cron').id
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
                'harvest': activity.group_id.type == 'harvesting',
                'nursery': activity.group_id.type == 'nursery',
                'notes': _('Scheduled action %s' % fields.Datetime.now()),
            })
        daily_activity._onchange_line_ids()
        daily_activity._set_line_ids()
        daily_activity._onchange_block_id()
        daily_activity._onchange_date_scheduled()
    

class AgricultureCropActivity(models.Model):
    _name = 'crop.activity'
    _description = 'Crop Activity Management'

    @api.depends('group_id', 'group_id.type')
    def _compute_activity_group_type(self):
        for record in self:
            group_type = False
            if record.group_id:
                group_type = record.group_id.type
            record.group_type = group_type

    name = fields.Char(string='Activity', required=True)
    account_id = fields.Many2one('account.account', string='Activity Account', required=True)
    material_ids = fields.One2many('crop.activity.material', 'activity_id', string='Materials')
    asset_ids = fields.One2many('crop.activity.asset', 'activity_id', string='Assets')
    crop_ids = fields.One2many('crop.activity.crop', 'activity_id', string='Crops')
    harvest_ids = fields.One2many('crop.activity.harvest', 'activity_id', string='Harvest')
    group_id = fields.Many2one('crop.activity.group', string='Activity Group', required=True)
    group_type = fields.Selection(
        selection=[
            ('land_clearing', 'Land Clearing'),
            ('nursery', 'Nursery'),
            ('maintenance', 'Maintenance'),
            ('harvesting', 'Harvesting')
        ],
        compute=_compute_activity_group_type,
        store=True,
        string='Activity Type'
    )
    is_planting = fields.Boolean(string='Planting')

    @api.onchange('group_type')
    def _onchange_group_type(self):
        # make sure to keep crop_ids is null when group type != 'nursery'
        if self.group_type != 'nursery':
            self.crop_ids = [(5,)]
            self.is_planting = False
            
        # make sure to keep harvest_ids null when group type != 'harvesting'
        if self.group_type != 'harvesting':
            self.harvest_ids = [(5,)]


class AgricultureCropActivityGroup(models.Model):
    _name = 'crop.activity.group'
    _description = 'Crop Activity Group'

    name = fields.Char(required=True, copy=False)
    type = fields.Selection(
        selection=[
            ('land_clearing', 'Land Clearing'),
            ('nursery', 'Nursery'),
            ('maintenance', 'Maintenance'),
            ('harvesting', 'Harvesting')
        ], string='Activity Type'
    )


class AgricultureCropActivityMaterial(models.Model):
    _name = 'crop.activity.material'
    _description = 'Crop Activity Material'
    _rec_name = 'product_id'

    activity_id = fields.Many2one('crop.activity', string='Activity', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Material', required=True)
    quantity = fields.Float(string='Quantity', digits='Product Unit of Measure', default=1.0)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', related='product_id.uom_id')

    standard_area = fields.Float(string='Standard Area', digits='Product Unit of Measure', default=1.0)
    area_uom_id = fields.Many2one('uom.uom', string='Area Unit of Measure', required=True, default=lambda self: self.env.company.crop_default_uom_id)


class AgricultureCropActivityAsset(models.Model):
    _name = 'crop.activity.asset'
    _description = 'Crop Activity Asset'
    _rec_name = 'asset_id'

    activity_id = fields.Many2one('crop.activity', string='Activity', required=True, ondelete='cascade')
    asset_id = fields.Many2one('maintenance.equipment', string='Asset', required=True)
    user_id = fields.Many2one('res.users', required=True, string='Responsible')


class AgricultureCropActivityCrop(models.Model):
    _name = 'crop.activity.crop'
    _description = 'Crop Activity Crop'
    _rec_name = 'product_id'

    activity_id = fields.Many2one('crop.activity', string='Activity', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Crop', required=True, domain="[('is_agriculture_product', '=', True)]")
    product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Meaure', default=1.0)
    product_uom_id = fields.Many2one('uom.uom', string='Product UoM', required=True)
    area = fields.Float(string='Standard Area', digits='Product Unit of Measure', default=1000.0)
    area_uom_id = fields.Many2one('uom.uom', string='Area UoM', required=True, default=lambda self: self.env.company.crop_default_uom_id)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id.id


class AgricultureCropActivityHarvest(models.Model):
    _name = 'crop.activity.harvest'
    _description = 'Crop Activity Harvest'
    _rec_name = 'product_id'

    activity_id = fields.Many2one('crop.activity', string='Activity', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Harvest', required=True, domain="[('is_agriculture_product', '=', True)]")
    product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Meaure', default=1.0)
    product_uom_id = fields.Many2one('uom.uom', string='Product UoM', required=True)
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id.id
