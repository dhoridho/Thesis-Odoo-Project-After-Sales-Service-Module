from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MrpQaParentWizard(models.TransientModel):
    _name = 'mrp.qa.parent.wizard'
    _description = 'MRP Quality Alert Parent Wizard'

    @api.model
    def _get_default_team_id(self):
        team_ids = self.env['sh.qc.team'].search([])
        if team_ids:
            return team_ids[0].id
        return False

    team_id = fields.Many2one('sh.qc.team', string='Team', required=True, default=_get_default_team_id)
    user_id = fields.Many2one('res.users', string='Responsible', required=True, default=lambda self: self.env.user)
    tag_ids = fields.Many2many('sh.qc.alert.tags', string='Tags')
    line_ids = fields.One2many('mrp.qa.wizard', 'wizard_id', string='Alerts')

    @api.onchange('team_id', 'user_id', 'tag_ids')
    def onchange_header_fields(self):
        for line in self.line_ids:
            line.user_id = self.user_id.id
            line.team_id = self.team_id.id
            line.tag_ids = [(6, 0, self.tag_ids.ids)]


class MrpQaWizard(models.TransientModel):
    _name = 'mrp.qa.wizard'
    _description = 'MRP Quality Alert Wizard'

    def write(self, vals):
        res = super(MrpQaWizard, self).write(vals)
        for record in self:
            alert_id = record.alert_id
            if not alert_id:
                continue
            alert_id.write({
                'user_id': record.user_id.id,
                'team_id': record.team_id.id,
                'tag_ids': [(6, 0, record.tag_ids.ids)]
            })
        return res

    def _prepare_default_values(self, move, point, consumption):
        values = {
            'move_id': move.id,
            'point_id': point.id,
            'team_id': self.env['sh.qc.team'].search([], limit=1).id,
            'user_id': self.env.user.id,
        }
        if not move:
            values.update({'consumption_id': consumption.id})
        return values

    def create_from_move_point(self, move_point, consumption):
        if self:
            raise ValidationError(_('Self is not empty!'))

        sh_alert = self.env['sh.mrp.quality.alert']
        to_create = []
        for move, point in move_point:
            domain = [
                ('move_id', '=', move.id),
                ('control_point_id', '=', point.id)
            ]
            if not move:
                domain += [('consumption_id', '=', consumption.id)]
            alert = sh_alert.search(domain)
            values = self._prepare_default_values(move, point, consumption)
            if alert:
                values.update({
                    'alert_id': alert.id,
                    'team_id': alert.team_id.id,
                    'user_id': alert.user_id.id,
                    'tag_ids': [(6, 0, alert.tag_ids.ids)],
                    'sh_priority': alert.sh_priority,
                })
            to_create.append(values)
        line_ids = self.create(to_create)
        return self.env['mrp.qa.parent.wizard'].create({'line_ids': [(6, 0, line_ids.ids)]})

    @api.depends('move_id', 'consumption_id', 'move_id.product_id', 'consumption_id.product_id')
    def _compute_product_id(self):
        for record in self:
            move_id = record.move_id
            consumption_id = record.consumption_id
            product_id = (move_id or consumption_id).product_id
            record.product_id = product_id and product_id.id or False

    wizard_id = fields.Many2one('mrp.qa.parent.wizard', string='Wizard')

    move_id = fields.Many2one('stock.move', string='Move')
    consumption_id = fields.Many2one('mrp.consumption', string='Production Record')
    point_id = fields.Many2one('sh.qc.point', string='Control Point')
    alert_id = fields.Many2one('sh.mrp.quality.alert', string='Quality Alert')

    product_id = fields.Many2one('product.product', string='Product', compute=_compute_product_id, store=True)

    boolean_field = fields.Boolean(default=True)
    team_id = fields.Many2one('sh.qc.team', string='Team')
    user_id = fields.Many2one('res.users', string='Responsible')
    tag_ids = fields.Many2many('sh.qc.alert.tags', string='Tags')
    sh_priority = fields.Selection([
        ('0', 'Very Low'),
        ('1', 'Low'),
        ('2', 'Normal'),
        ('3', 'High')
    ], string='Priority')

    def action_open_alert(self):
        self.ensure_one()
        return {
            'name': _('Quality Alert'),
            'type': 'ir.actions.act_window',
            'res_model': 'sh.mrp.quality.alert',
            'view_mode': 'form',
            'res_id': self.alert_id.id,
            'target': 'current'
        }

    def action_create_alert(self):
        wizard_id = self.wizard_id
        new_stage = self.env['sh.qc.alert.stage'].search([
            ('name', '=', 'NEW')
        ], limit=1)

        self.alert_id = self.env['sh.mrp.quality.alert'].create({
            'move_id': self.move_id.id,
            'consumption_id': self.consumption_id.id,
            'product_id': self.product_id.id,
            'control_point_id': self.point_id.id,
            'user_id': wizard_id.user_id.id,
            'team_id': self.team_id.id,
            'sh_priority': self.sh_priority,
            'tag_ids': [(6, 0, wizard_id.tag_ids.ids)],
            'stage_id': new_stage and new_stage.id or False
        })
        return self.action_open_alert()
