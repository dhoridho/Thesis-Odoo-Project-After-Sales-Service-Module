from odoo import models, fields, _


class MrpQualityInspectWizard(models.TransientModel):
    _name = 'mrp.quality.inspect.wizard'
    _description = 'MRP Quality Inspect Wizard'

    check_id = fields.Many2one('sh.mrp.quality.check', string='Quality Check', required=True)
    point_id = fields.Many2one('sh.qc.point', string='Control Point', required=True)

    point_type = fields.Selection(related='point_id.type')
    product_id = fields.Many2one(related='check_id.product_id')

    message = fields.Html(string='Message')
    measure = fields.Float(string='Measure', digits='Product Unit of Measure')
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    text = fields.Text(string='Text')

    mode = fields.Selection(
        selection=[
            ('main', 'Main Wizard'),
            ('confirm', 'Confirm Wizard')
        ],
        string='Mode',
        required=True,
        default='main'
    )

    def action_validate(self, **kwargs):
        values = {
            'sh_norm': 0.0,
            'sh_date': fields.Datetime.now(),
            'state': self.env.context.get('state')
        }
        for key, value in kwargs.items():
            values[key] = value

        pop_wizard_ids = self.env.context.get('pop_wizard_ids')
        if pop_wizard_ids:
            self.check_id.write(values)
            action = self.env.ref('equip3_manuf_qc.action_view_mrp_qc_wizard').read()[0]
            action['domain'] = [('id', 'in', pop_wizard_ids)]
            action['context'] = {'active_wizard_ids': pop_wizard_ids, 'no_breadcrumbs': True}
            return action
        return self.check_id.write(values)

    def check_pass_fail(self):
        return self.action_validate()

    def check_measurement(self):
        if self.mode == 'confirm':
            if self.env.context.get('force_validate'):
                return self.action_validate(sh_norm=self.measure)
            return self.check_id.action_inspect(sh_norm=self.measure)

        if self.point_id.sh_unit_from <= self.measure <= self.point_id.sh_unit_to:
            return self.action_validate(sh_norm=self.measure)
        msg = _(
            'You measured <b>%s</b> mm and it should be between <b>%s</b> to <b>%s</b> mm.' %
            (self.measure, self.point_id.sh_unit_from, self.point_id.sh_unit_to)
        )
        return self.check_id.action_inspect(mode='confirm', message=msg, sh_norm=self.measure)

    def check_pics(self):
        self.action_validate(attachment_ids=[(6, 0, self.attachment_ids.ids)])
        for model in [
            self.check_id.sh_plan_id,
            self.check_id.sh_mrp,
            self.check_id.sh_workorder_id,
            self.check_id.sh_consumption_id
        ]:
            attachment_ids = model.attachment_ids | self.attachment_ids
            model.attachment_ids = [(6, 0, attachment_ids.ids)]
        return True

    def check_text(self):
        return self.action_validate(text_message=self.text)

    def action_check(self):
        self.ensure_one()
        if self.point_type == 'type1':
            return self.check_pass_fail()
        elif self.point_type == 'type2':
            return self.check_measurement()
        elif self.point_type == 'type3':
            return self.check_pics()
        elif self.point_type == 'type4':
            return self.check_text()
        return
