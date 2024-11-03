from odoo import models, fields, _
from odoo.exceptions import ValidationError


class ShMrpQualityControlReuse(models.AbstractModel):
    _name = 'sh.mrp.qc.reuse'
    _description = 'MRP Quality Control Reuse'

    def get_pair_move_point(self, need_alert=None, mandatory=None):

        def get_boolean_domain(value):
            if value in [True, False]:
                return [value]
            return [True, False]

        self.ensure_one()
        domain_need_alert = get_boolean_domain(need_alert)
        domain_mandatory = get_boolean_domain(mandatory)

        pairs = []
        moves = self.qc_moves_field_name()
        if moves:
            for move in moves:
                for point in move.qc_point_ids.filtered(
                        lambda p: p.need_alert in domain_need_alert and p.is_mandatory in domain_mandatory):
                    pairs.append((move, point))
        else:
            operation_ids = self.manufacturing_order_id.bom_id.operation_ids
            for point in operation_ids.mapped('quality_point_ids').filtered(
                    lambda p: p.need_alert in domain_need_alert and p.is_mandatory in domain_mandatory):
                pairs.append((self.env['stock.move'], point))
        return pairs

    def is_any_qc_to_process(self):
        self.ensure_one()
        any_qc_pending_left = False
        any_qc_mandatory_left = False

        if self.state != 'progress' and self._name != 'mrp.consumption':
            return any_qc_pending_left, any_qc_mandatory_left

        for move, point in self.get_pair_move_point():
            domain = [
                ('move_id', '=', move.id),
                ('control_point_id', '=', point.id)
            ]

            if not move:
                domain += [('sh_consumption_id', '=', self.id)]

            checks = self.env['sh.mrp.quality.check'].search(domain)

            # check if there's any quality check to create
            qc_pending_left = len(checks) < point.number_of_test
            if not qc_pending_left:

                # check if there's any quality check to inspect
                qc_pending_left = any(c.state not in ('pass', 'fail') for c in checks)

                if not qc_pending_left:
                    # check if there's any quality alert to be done
                    alert_checks = checks.filtered(lambda c: c.wizard_id.alert_id)
                    qc_pending_left = any(c.wizard_id.alert_id.stage_id.name != 'DONE' for c in alert_checks)

            if point.is_mandatory and not any_qc_mandatory_left:
                any_qc_mandatory_left = qc_pending_left

            if not any_qc_pending_left:
                any_qc_pending_left = qc_pending_left

            if any_qc_pending_left and any_qc_mandatory_left:
                break

        return any_qc_pending_left, any_qc_mandatory_left

    def check_mandatory_qc(self):
        self.ensure_one()
        if self.any_qc_mandatory_left:
            raise ValidationError(_("There's mandatory quality control you must check first!"))

    def qc_check_field_name(self):
        if self._name == 'mrp.plan':
            return 'sh_plan_id'
        elif self._name == 'mrp.production':
            return 'sh_mrp'
        elif self._name == 'mrp.workorder':
            return 'sh_workorder_id'
        elif self._name == 'mrp.consumption':
            return 'sh_consumption_id'
        raise ValidationError(_('Not implemented!'))

    def qc_alert_field_name(self):
        if self._name == 'mrp.plan':
            return 'plan_id'
        elif self._name == 'mrp.production':
            return 'mrp_id'
        elif self._name == 'mrp.workorder':
            return 'workorder_id'
        elif self._name == 'mrp.consumption':
            return 'consumption_id'
        raise ValidationError(_('Not implemented!'))

    def qc_move_point_field_name(self):
        if self._name == 'mrp.plan':
            return 'plan_id'
        elif self._name == 'mrp.production':
            return 'production_id'
        elif self._name == 'mrp.workorder':
            return 'workorder_id'
        elif self._name == 'mrp.consumption':
            return 'consumption_id'
        raise ValidationError(_('Not implemented!'))

    def qc_moves_field_name(self):
        if self._name == 'mrp.plan':
            return self.mo_stock_move_ids
        elif self._name == 'mrp.production':
            return self.move_raw_ids
        elif self._name == 'mrp.workorder':
            return self.move_raw_ids
        elif self._name == 'mrp.consumption':
            return self.move_raw_ids | self.move_finished_ids
        raise ValidationError(_('Not implemented!'))

    def qc_check_action(self):
        if self._name == 'mrp.plan':
            return 'equip3_manuf_qc.plan_quality_check_action'
        elif self._name == 'mrp.production':
            return 'sh_inventory_mrp_qc.mrp_quality_check_action'
        elif self._name == 'mrp.workorder':
            return 'sh_inventory_mrp_qc.wo_quality_check_action'
        elif self._name == 'mrp.consumption':
            return 'equip3_manuf_qc.consumption_quality_check_action'
        raise ValidationError(_('Not implemented!'))

    def qc_alert_action(self):
        if self._name == 'mrp.plan':
            return 'equip3_manuf_qc.plan_quality_alert_action'
        elif self._name == 'mrp.production':
            return 'sh_inventory_mrp_qc.mrp_quality_alert_action'
        elif self._name == 'mrp.workorder':
            return 'sh_inventory_mrp_qc.wo_quality_alert_action'
        elif self._name == 'mrp.consumption':
            return 'equip3_manuf_qc.consumption_quality_alert_action'
        raise ValidationError(_('Not implemented!'))

    def _compute_quality_control(self):
        sh_check = self.env['sh.mrp.quality.check']
        sh_alert = self.env['sh.mrp.quality.alert']
        qc_check_field_name = self.qc_check_field_name()
        qc_alert_field_name = self.qc_alert_field_name()

        for record in self:
            point_ids = record.qc_moves_field_name().mapped('qc_point_ids')
            need_qc = len(point_ids) > 0

            # default quality control fields when need_qc is False
            qc_pass = False
            qc_fail = False
            pending_qc = False
            check_ids = self.env['sh.mrp.quality.check']
            alert_ids = self.env['sh.mrp.quality.alert']

            need_alert = False
            any_qc_mandatory_left = False

            if need_qc:
                check_ids = sh_check.search([(qc_check_field_name, '=' , record.id)])
                alert_ids = sh_alert.search([(qc_alert_field_name, '=' , record.id)])

                qc_pass_count = len(check_ids.filtered(lambda c: c.state == 'pass'))
                qc_fail_count = len(check_ids.filtered(lambda c: c.state == 'fail'))

                need_alert = len(point_ids.filtered(lambda p: p.need_alert)) > 0
                pending_qc, any_qc_mandatory_left = record.is_any_qc_to_process()

                qc_pass = not pending_qc and qc_pass_count > qc_fail_count
                qc_fail = not pending_qc and qc_pass_count < qc_fail_count

            record.need_qc = need_qc
            record.qc_pass = qc_pass
            record.qc_fail = qc_fail
            record.pending_qc = pending_qc
            record.need_alert = need_alert
            record.qc_count = len(check_ids)
            record.qc_alert_count = len(alert_ids)
            record.any_qc_mandatory_left = any_qc_mandatory_left
            record.sh_mrp_quality_check_ids = [(6, 0, check_ids.ids)]
            record.sh_mrp_quality_alert_ids = [(6, 0, alert_ids.ids)]
            record.show_check_button = len(point_ids.filtered(lambda p: not p.need_alert)) > 0
            record.show_alert_button = len(point_ids.filtered(lambda p: p.need_alert)) > 0

    # OVERRIDE FROM SH_INVENTORY_MRP_QC
    need_qc = fields.Boolean(compute=_compute_quality_control)

    qc_fail = fields.Boolean('QC Fail', compute=_compute_quality_control, search='search_fail_qc')
    qc_pass = fields.Boolean('QC Pass', compute=_compute_quality_control, search='search_pass_qc')
    pending_qc = fields.Boolean('Pending QC', compute=_compute_quality_control, search='search_pending_qc')

    qc_count = fields.Integer(compute=_compute_quality_control, string='Quality Checks Count')
    qc_alert_count = fields.Integer(compute=_compute_quality_control, string='Quality Alerts Count')

    sh_mrp_quality_check_ids = fields.One2many(
        'sh.mrp.quality.check', string='Quality Checks', compute=_compute_quality_control)
    sh_mrp_quality_alert_ids = fields.One2many(
        'sh.mrp.quality.alert', string='Quality Alerts', compute=_compute_quality_control)
    attachment_ids = fields.Many2many('ir.attachment', string='QC Pictures', copy=False)

    # NEW ADDED
    need_alert = fields.Boolean(compute=_compute_quality_control)
    show_check_button = fields.Boolean(compute=_compute_quality_control)
    show_alert_button = fields.Boolean(compute=_compute_quality_control)
    any_qc_mandatory_left = fields.Boolean(compute=_compute_quality_control)
    parent_wizard_id = fields.Many2one('mrp.qc.wizard.parent')

    def _search_qc_fields(self, operator, value, field):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise ValidationError(_('Operator strict to "=" or "!=" and value must be boolean!'))
        rec_ids = self.search([]).filtered(lambda r: r[field]).ids
        if (operator == '=' and value is True) or (operator == '!=' and value is False):
            return [('id', 'in', rec_ids)]
        return [('id', 'not in', rec_ids)]

    def search_pending_qc(self, operator, value):
        return self._search_qc_fields(operator, value, 'pending_qc')

    def search_fail_qc(self, operator, value):
        return self._search_qc_fields(operator, value, 'qc_fail')

    def search_pass_qc(self, operator, value):
        return self._search_qc_fields(operator, value, 'qc_pass')

    # def button_quality_check(self):
    #     self.ensure_one()
    #     pairs = self.get_pair_move_point(need_alert=False)
    #     moves, consumption = self.get_qc_fields()[:2]
    #     wizard_ids = self.env['mrp.qc.wizard'].get_or_create(pairs, moves, consumption)

    #     action = self.env.ref('equip3_manuf_qc.action_view_mrp_qc_wizard').read()[0]
    #     action['domain'] = [('id', 'in', wizard_ids.ids)]
    #     action['context'] = {'active_wizard_ids': wizard_ids.ids, 'no_breadcrumbs': True}
    #     return action

    def _get_next_move_point(self):
        for pair in self.move_point_ids.filtered(
            lambda p: p.remaining_check > 0 and \
                (p.move_type != 'finished' or \
                    (p.move_type == 'finished' and self._name == 'mrp.consumption'))
        ):
            return pair
        return False

    def button_quality_check(self):
        self.ensure_one()
        pair = self._get_next_move_point()

        if not pair:
            return
        
        return {
            'name': 'Quality Check',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('equip3_manuf_qc.view_sh_mrp_qc_wizard_form').id,
            'res_model': 'sh.mrp.qc.wizard',
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
                'default_move_id': pair.move_id.id,
                'default_point_id': pair.point_id.id,
                'default_move_point_id': pair.id
            },
            'target': 'new',
        }

    def button_quality_alert(self):
        self.ensure_one()
        pairs = self.get_pair_move_point(need_alert=True)
        wizard_id = self.env['mrp.qa.wizard'].create_from_move_point(pairs, self)
        
        for line in wizard_id.line_ids:
            if not line.alert_id and line.point_id.need_alert and line.point_id.auto_create_alert:
                line.action_create_alert()
                if line.alert_id:
                    line.alert_id.action_create_qc_wizards()

        action = self.env.ref('equip3_manuf_qc.action_view_mrp_qa_parent_wizard').read()[0]
        action['res_id'] = wizard_id.id
        return action

    def action_view_quality_check(self):
        self.ensure_one()
        action = self.env.ref(self.qc_check_action()).read()[0]
        action['domain'] = [('id', 'in', self.sh_mrp_quality_check_ids.ids)]
        action['context'] = {'create': False, 'edit': False, 'delete': False}
        return action

    def action_view_quality_alert(self):
        self.ensure_one()
        action = self.env.ref(self.qc_alert_action()).read()[0]
        action['domain'] = [('id', 'in', self.sh_mrp_quality_alert_ids.ids)]
        action['context'] = {'create': False, 'edit': False, 'delete': False}
        return action
