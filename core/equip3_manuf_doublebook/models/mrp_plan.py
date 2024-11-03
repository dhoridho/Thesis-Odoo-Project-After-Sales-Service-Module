from odoo import models, fields, api, _


class MrpPlan(models.Model):
    _name = 'mrp.plan'
    _inherit = ['mrp.plan', 'base.synchro.abstract']

    def sync_resequence(self):
        plans = self.filtered(lambda o: o.base_sync)
        for plan in plans:
            plan.plan_id = self.env['ir.sequence'].next_by_code('mrp.plan')
            plan.mrp_order_ids.sync_resequence()

    def sync_confirm(self):
        plans = self.filtered(lambda o: o.base_sync)
        for plan in plans:
            plan.mrp_order_ids.sync_confirm()
        plans.state = 'done'

    def sync_unlink(self):
        plans = self.filtered(lambda o: o.base_sync)
        plans.mrp_order_ids.sync_unlink()
        plans.unlink()


class MrpPlanLine(models.Model):
    _name = 'mrp.plan.line'
    _inherit = ['mrp.plan.line', 'base.synchro.abstract']


class MrpPlanMaterial(models.Model):
    _name = 'mrp.plan.material'
    _inherit = ['mrp.plan.material', 'base.synchro.abstract']
