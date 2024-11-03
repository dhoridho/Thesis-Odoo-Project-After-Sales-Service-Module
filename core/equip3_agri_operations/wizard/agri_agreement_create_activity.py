from odoo import models, fields, api, _


class AgriAgreementCreateActivity(models.TransientModel):
    _name = 'agri.agreement.create.activity'
    _description = 'Agri Agreement Create Activity'

    agreement_id = fields.Many2one('agri.agreement', required=True)
    agreement_type = fields.Selection(related='agreement_id.agreement_type')
    agreement_activity_line_ids = fields.One2many('agriculture.daily.activity.line', related='agreement_id.activity_line_ids')
    agreement_block_ids = fields.Many2many('crop.block', related='agreement_id.block_ids')

    assign_type = fields.Selection(selection=[
        ('existing', 'Existing Activity'),
        ('new', 'New Activity')
    ], required=True, default='existing')
    schedule_date = fields.Date()
    activity_line_id = fields.Many2one('agriculture.daily.activity.line', domain="[('daily_activity_type', '=', agreement_type), ('activity_id', 'in', allowed_activity_ids), ('id', 'not in', agreement_activity_line_ids), ('block_id', 'in', agreement_block_ids)]")
    activity_id = fields.Many2one('crop.activity', string='Activity', domain="[('id', 'in', allowed_activity_ids)]")
    allowed_activity_ids = fields.Many2many('crop.activity', compute='_compute_allowed_activities')
    block_id = fields.Many2one('crop.block', domain="[('id', 'in', agreement_block_ids)]")
    sub_block_id = fields.Many2one('crop.block.sub', string='Sub-Block', domain="[('id', 'in', allowed_sub_block_ids)]")
    allowed_sub_block_ids = fields.Many2many('crop.block.sub', compute='_compute_allowed_sub_blocks')

    @api.depends('assign_type', 'block_id', 'activity_line_id')
    def _compute_allowed_sub_blocks(self):
        for record in self:
            if record.assign_type == 'existing':
                sub_block_ids = record.activity_line_id.sub_block_id.ids
            else:
                sub_block_ids = record.block_id.sub_ids.filtered(lambda o: o.state == 'active').ids
            record.allowed_sub_block_ids = [(6, 0, sub_block_ids)]

    @api.depends('agreement_id', 'agreement_id.contract_ids', 'agreement_id.contract_ids.activity_id')
    def _compute_allowed_activities(self):
        for record in self:
            activity_ids = record.agreement_id.contract_ids.mapped('activity_id')
            record.allowed_activity_ids = [(6, 0, activity_ids.ids)]

    @api.onchange('activity_line_id')
    def _onchange_activity_line_id(self):
        self.block_id = self.activity_line_id and self.activity_line_id.block_id.id or False
        self.sub_block_id = self.activity_line_id.sub_block_id.id

    @api.onchange('allowed_activity_ids')
    def _onchange_allowed_activity_ids(self):
        if self.allowed_activity_ids:
            self.activity_id = self.allowed_activity_ids[0].id or self.allowed_activity_ids[0]._origin.id

    def action_confirm(self):
        self.ensure_one()
        if self.assign_type == 'new':
            activity_line_id = self.env['agriculture.daily.activity.line'].create({
                'agreement_sequence': len(self.agreement_id.activity_line_ids) + 1,
                'daily_activity_type': self.agreement_type,
                'is_whole_day': True,
                'company_id': self.agreement_id.company_id.id,
                'branch_id': self.agreement_id.branch_id.id,
                'analytic_group_ids': [(6, 0, self.agreement_id.analytic_tag_ids.ids)],
                'date_scheduled': self.schedule_date,
                'block_id': self.block_id.id,
                'sub_block_id': self.sub_block_id.id,
                'activity_id': self.activity_id.id,
                'agreement_id': self.agreement_id.id,
                'size': (self.sub_block_id or self.block_id).size,
                'uom_id': (self.sub_block_id or self.block_id).uom_id.id,
            })

            activity_line_id._onchange_harvest()
            activity_line_id._onchange_nursery()
            activity_line_id._onchange_activity_id()
            activity_line_id._onchange_location_id()
            activity_line_id._onchange_block_id()
            activity_line_id._onchange_date_scheduled()
        else:
            if self.activity_line_id not in self.agreement_id.activity_line_ids:
                self.activity_line_id.write({
                    'agreement_sequence': len(self.agreement_id.activity_line_ids) + 1,
                    'agreement_id': self.agreement_id.id
                })