from odoo import models, fields, api


class ShMrpQualityCheck(models.Model):
    _inherit = 'sh.mrp.quality.check'

    @api.model
    def create(self, values):
        records = super(ShMrpQualityCheck, self).create(values)
        records.set_fields()
        return records

    def write(self, values):
        result = super(ShMrpQualityCheck, self).write(values)
        if not self.env.context.get('bypass_set_fields'):
            self.set_fields()
        return result

    move_id = fields.Many2one('stock.move', string='Move')
    sh_consumption_id = fields.Many2one('mrp.consumption', string='Production Record')
    sh_workorder_id = fields.Many2one('mrp.workorder', string='Work Order')
    sh_mrp = fields.Many2one('mrp.production', string='Production Order')
    sh_plan_id = fields.Many2one('mrp.plan', string='Production Plan')

    product_type = fields.Selection(
        selection=[
            ('material', 'Material'),
            ('finished', 'Finished Good'),
            ('wip', 'WIP')
        ],
        string='Product Type',
        default='material'
    )
    description = fields.Char()
    wizard_id = fields.Many2one('mrp.qc.wizard', string='Wizard')

    type_of_qc = fields.Selection(related='control_point_id.type_of_qc', string='QC Type')
    product_image = fields.Image(related='product_id.image_1920')

    quantitative_ids = fields.One2many('qc.quantitative.lines', 'check_id', string="Quantitative Lines")
    qualitative_ids = fields.One2many('qc.qualitative.lines', 'check_id', string="Qualitative Lines")
    state = fields.Selection(
        selection_add=[
            ('fail',),
            ('repair', 'Under Repair'),
            ('scrap','Under Scrap'),
            ('transfer','Under ITR')
        ]
    )

    def set_fields_from_move(self):
        self.ensure_one()
        move = self.move_id
        return self.with_context(bypass_set_fields=True).write({
            'sh_consumption_id': (move.mrp_consumption_id or move.mrp_consumption_finished_id).id,
            'sh_workorder_id': (move.mrp_workorder_component_id or move.workorder_id).id,
            'sh_mrp': (move.raw_material_production_id or move.production_id).id,
            'sh_plan_id': (move.raw_material_production_id or move.production_id).mrp_plan_id.id
        })

    def set_fields_from_consumption(self):
        self.ensure_one()
        cons = self.sh_consumption_id
        return self.with_context(bypass_set_fields=True).write({
            'sh_workorder_id': cons.workorder_id.id,
            'sh_mrp': cons.manufacturing_order_id.id,
            'sh_plan_id': cons.manufacturing_plan.id
        })

    def set_fields(self):
        for record in self:
            if record.move_id:
                record.set_fields_from_move()
            else:
                record.set_fields_from_consumption()

    def action_inspect(self, mode='main', message=False, sh_norm=0.0):
        self.ensure_one()
        if not message:
            message = self.control_point_id.sh_instruction

        context = self.env.context.copy()
        context.update({
            'default_mode': mode,
            'default_check_id': self.id,
            'default_point_id': self.control_point_id.id,
            'default_message': message,
            'default_measure': sh_norm
        })

        action = self.env.ref('equip3_manuf_qc.action_view_mrp_quality_inspect_wizard').read()[0]
        action['context'] = context
        return action


    def recheck(self):
        wizard_id = self.env['sh.mrp.qc.wizard'].sudo().search([
            ('move_id', '=', self.move_id.id),
            ('res_id', '=', self.sh_consumption_id.id),
            ], limit=1, order='id desc')
        ctx = {
            'default_id': wizard_id.id,
            'default_res_model': wizard_id.res_model,
            'default_res_id': wizard_id.res_id,
            'default_move_point_id': wizard_id.move_point_id.id,
            'default_move_id': wizard_id.move_id.id,
            'default_point_id': wizard_id.point_id.id,
            'default_check_id': wizard_id.check_id.id,

        }
        return {
            'name': 'Self Check',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('equip3_manuf_qc.view_sh_mrp_qc_wizard_form_confirmed').id,
            'res_model': 'sh.mrp.qc.wizard',
            'res_id': wizard_id.id,
            'context': ctx,
            'target': 'new',
        }


class QuantitativeLines(models.Model):
    _inherit = 'qc.quantitative.lines'

    check_id = fields.Many2one('sh.mrp.quality.check', string="Quality Check")


class QuantitativeLines(models.Model):
    _inherit = 'qc.qualitative.lines'

    check_id = fields.Many2one('sh.mrp.quality.check', string="Quality Check")
    