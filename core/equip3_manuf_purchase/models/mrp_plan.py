from odoo import models, fields, api, _


class MrpPlan(models.Model):
    _inherit = 'mrp.plan'

    @api.model
    def _default_mrp_allow_submit_pr(self):
        return eval(self.env['ir.config_parameter'].sudo().get_param('equip3_manuf_purchase.mrp_allow_submit_pr_pp', 'False'))

    @api.model
    def _default_mrp_allow_submit_pr_partial(self):
        return eval(self.env['ir.config_parameter'].sudo().get_param('equip3_manuf_purchase.mrp_allow_submit_pr_partial_pp', 'False'))

    mrp_allow_submit_pr = fields.Boolean(string='Allow Submit Purchase Request', default=_default_mrp_allow_submit_pr)
    mrp_allow_submit_pr_partial = fields.Boolean(string='Allow Submit Partial Purchase Request', default=_default_mrp_allow_submit_pr_partial)

    def action_purchase_request(self):
        if not self.mrp_allow_submit_pr_partial or self.env.context.get('skip_wizard', False):
            res = super(MrpPlan, self).action_purchase_request()
            orders = self.env.context.get('order_ids', self.env['mrp.production'])
            if orders.exists():
                orders.write({'is_purchase_requested': True})
            return res
        return {
            'name': _('Purchase Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.material.request.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'context': {
                'default_plan_id': self.id,
                'default_action': 'action_purchase_request'
            }
        }
