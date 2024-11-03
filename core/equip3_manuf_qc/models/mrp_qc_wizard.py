from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MrpQualityCheckWizard(models.Model):
    _name = 'mrp.qc.wizard'
    _description = 'MRP Quality Check Wizard'

    def get_or_create(self, move_point, moves, consumption):
        if self:
            raise ValidationError(_('Self is not empty!'))

        to_append, to_create = self, []
        for move, point in move_point:
            domain = [
                ('move_id', '=', move.id),
                ('point_id', '=', point.id)
            ]
            if not move:
                domain += [('consumption_id', '=', consumption.id)]
            wizard = self.search(domain)
            if wizard:
                to_append |= wizard
            else:
                values = {'move_id': move.id, 'point_id': point.id}
                if not move:
                    values.update({'consumption_id': consumption.id})
                to_create.append(values)

        wizard_ids = to_append | self.create(to_create)
        if moves:
            linked_by_model = self.search([('move_id', 'in', moves.ids)])
            wizard_ids |= linked_by_model
        return wizard_ids

    @api.depends('point_id', 'point_id.number_of_test')
    def _compute_point_number_of_test(self):
        for record in self:
            point_id = record.point_id
            record.point_number_of_test = point_id and point_id.number_of_test or 1

    @api.depends('point_id', 'point_id.name', 'point_id.type')
    def _compute_points(self):
        for record in self:
            point_id = record.point_id
            record.point_name = point_id and point_id.name or False
            record.point_type = point_id and point_id.type or False

    @api.depends('check_ids', 'check_ids.state')
    def _compute_pass_fail_count(self):
        for record in self:
            check_ids = record.check_ids
            record.pass_count = len(check_ids.filtered(lambda c: c.state == 'pass'))
            record.fail_count = len(check_ids.filtered(lambda c: c.state == 'fail'))

    @api.depends('pass_count', 'fail_count')
    def _compute_state(self):
        for record in self:
            state = 'draft'
            pass_count = record.pass_count
            fail_count = record.fail_count

            if pass_count > fail_count:
                state = 'pass'
            elif pass_count < fail_count:
                state = 'fail'
            
            record.state = state

    @api.depends('move_id', 'consumption_id', 'move_id.product_id', 'consumption_id.product_id',
                 'move_id.mrp_consumption_finished_id')
    def _compute_product_id(self):
        for record in self:
            move_id = record.move_id
            consumption_id = record.consumption_id

            product_id = (consumption_id or move_id).product_id
            product_type = 'wip'
            if move_id:
                product_type = 'material'
                if move_id.mrp_consumption_finished_id:
                    product_type = 'finished'

            record.product_id = product_id and product_id.id or False
            record.product_type = product_type

    @api.depends('point_number_of_test', 'pass_count', 'fail_count')
    def _compute_pending_count(self):
        for record in self:
            record.pending_count = record.point_number_of_test - (record.pass_count + record.fail_count)

    move_id = fields.Many2one('stock.move', string='Stock Move')
    consumption_id = fields.Many2one('mrp.consumption', string='Production Record')
    point_id = fields.Many2one('sh.qc.point', string='Name')
    check_ids = fields.One2many('sh.mrp.quality.check', 'wizard_id', string='Quality Checks')
    alert_id = fields.Many2one('sh.mrp.quality.alert', string='Quality Alert')

    point_number_of_test = fields.Integer(string='Max. Test', compute=_compute_point_number_of_test)
    point_name = fields.Char(string='Reference', compute=_compute_points, store=True)

    point_type = fields.Selection(
        selection=[
            ('type1', 'Pass Fail'),
            ('type2', 'Measurement'),
            ('type3', 'Take a Picture'),
            ('type4', 'Text')
        ],
        string='QC Type',
        compute=_compute_points,
        store=True)

    product_id = fields.Many2one('product.product', string='Product', compute=_compute_product_id, store=True)
    product_type = fields.Selection(
        selection=[
            ('material', 'Material'),
            ('wip', 'WIP'),
            ('finished', 'Finished Good')
        ],
        default='material',
        compute=_compute_product_id,
        store=True
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('pass', 'Pass'),
            ('fail', 'Fail')
        ],
        compute=_compute_state,
        store=True
    )
    pass_count = fields.Integer(string='Pass', compute=_compute_pass_fail_count)
    fail_count = fields.Integer(string='Fail', compute=_compute_pass_fail_count)
    pending_count = fields.Integer(string='Pending', compute=_compute_pending_count)

    @api.constrains('move_id', 'point_id')
    def _unique_move_point(self):
        for record in self:
            move_id = record.move_id
            point_id = record.point_id

            if move_id and self.search([
                ('move_id', '=', move_id.id),
                ('point_id', '=', point_id.id),
                ('id', '!=', record.id)
            ]):
                raise ValidationError(_(
                    'Wizard for move: %s with point: %s already created!' %
                    (move_id.name, point_id.name))
                )

    def action_inspect(self):
        self.ensure_one()

        inspected_check_ids = self.check_ids.filtered(lambda c: c.state != 'draft')
        if len(inspected_check_ids) == self.point_number_of_test:
            raise ValidationError(_('Your maximum number of test has been reached!'))

        checks_to_inspect = self.check_ids - inspected_check_ids
        if checks_to_inspect:
            check_id = checks_to_inspect[0]
        else:
            check_id = self.env['sh.mrp.quality.check'].create({
                'wizard_id': self.id,
                'move_id': self.move_id.id,
                'sh_consumption_id': self.consumption_id.id,
                'control_point_id': self.point_id.id,
                'sh_control_point': self.point_name,
                'company_id': self.point_id.company_id.id,
                'description': self.point_id.description,
                'qc_type': self.point_type,
                'product_id': self.product_id.id,
                'product_type': self.product_type,
            })
        wizard_ids = self.env.context.get('active_wizard_ids', [])
        return check_id.with_context(pop_wizard_ids=wizard_ids).action_inspect()
