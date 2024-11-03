from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ShMrpQualityAlert(models.Model):
    _inherit = 'sh.mrp.quality.alert'

    @api.model
    def create(self, values):
        records = super(ShMrpQualityAlert, self).create(values)
        records.set_fields()
        return records

    def write(self, values):
        result = super(ShMrpQualityAlert, self).write(values)
        if not self.env.context.get('bypass_set_fields'):
            self.set_fields()
        return result

    @api.depends('wizard_ids', 'control_point_id', 'move_id', 'consumption_id')
    def _compute_show_create_qc_button(self):
        for record in self:
            err_message = record.get_create_qc_wizard_issues()
            record.show_create_qc_button = err_message is False

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        return self.env['sh.qc.alert.stage'].search([])

    move_id = fields.Many2one('stock.move', string='Move')
    consumption_id = fields.Many2one('mrp.consumption', string='Production Record')
    workorder_id = fields.Many2one('mrp.workorder', string='Work Order')
    mrp_id = fields.Many2one('mrp.production', string='Production Order')
    plan_id = fields.Many2one('mrp.plan', string='Production Plan')

    control_point_id = fields.Many2one('sh.qc.point', string='Control Point')
    stage_name = fields.Char(related='stage_id.name', string='Stage Name')
    wizard_ids = fields.One2many('mrp.qc.wizard', 'alert_id', string='Quality Check Wizard')
    show_create_qc_button = fields.Boolean(compute=_compute_show_create_qc_button)
    int_record = fields.Integer(default=1)
    stage_id = fields.Many2one(group_expand='_read_group_stage_ids')

    def set_fields_from_move(self):
        self.ensure_one()
        move = self.move_id
        return self.with_context(bypass_set_fields=True).write({
            'consumption_id': (move.mrp_consumption_id or move.mrp_consumption_finished_id).id,
            'workorder_id': (move.mrp_workorder_component_id or move.workorder_id).id,
            'mrp_id': (move.raw_material_production_id or move.production_id).id,
            'plan_id': (move.raw_material_production_id or move.production_id).mrp_plan_id.id
        })

    def set_fields_from_consumption(self):
        self.ensure_one()
        cons = self.consumption_id
        return self.with_context(bypass_set_fields=True).write({
            'workorder_id': cons.workorder_id.id,
            'mrp_id': cons.manufacturing_order_id.id,
            'plan_id': cons.manufacturing_plan.id
        })

    def set_fields(self):
        for record in self:
            if record.move_id:
                record.set_fields_from_move()
            else:
                record.set_fields_from_consumption()

    def get_create_qc_wizard_issues(self):
        self.ensure_one()
        if self.wizard_ids:
            return _('Quality Check Wizard already created!')
        if not self.control_point_id:
            return _('Control Point cannot be empty!')
        if not self.move_id and not self.consumption_id:
            return _('Either Stock Move or Production Record cannot be empty!')
        return False

    def action_create_qc_wizards(self):
        self.ensure_one()

        err_message = self.get_create_qc_wizard_issues()
        if err_message is not False:
            return ValidationError(err_message)

        wizard_id = self.env['mrp.qc.wizard'].search([
            ('alert_id', '=', False),
            ('move_id', '=', self.move_id.id),
            ('consumption_id', '=', self.consumption_id.id),
            ('point_id', '=', self.control_point_id.id)
        ])

        if wizard_id:
            wizard_id.write({'alert_id': self.id})
        else:
            self.env['mrp.qc.wizard'].create({
                'alert_id': self.id,
                'move_id': self.move_id.id,
                'consumption_id': self.consumption_id.id,
                'point_id': self.control_point_id.id
            })

        waiting_stage = self.env['sh.qc.alert.stage'].search([
            ('name', '=', 'WAITING')
        ], limit=1)
        if waiting_stage:
            self.stage_id = waiting_stage.id

    def action_done(self):
        self.ensure_one()

        if not self.wizard_ids:
            raise ValidationError(_("Please create quality checks first!"))

        if any(wizard.pending_count > 0 for wizard in self.wizard_ids):
            raise ValidationError(_("Please finish inspecting quality check first!"))

        done_stage = self.env['sh.qc.alert.stage'].search([
            ('name', '=', 'DONE')
        ], limit=1)
        if done_stage:
            self.stage_id = done_stage.id
