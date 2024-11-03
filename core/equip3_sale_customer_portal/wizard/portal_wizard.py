from odoo import models,fields,api,_


class PortalWizardUserInherit(models.TransientModel):
    _inherit = 'portal.wizard.user'

    is_customer = fields.Boolean(string='Is Customer', compute='_compute_is_customer')

    @api.depends('partner_id')
    def _compute_is_customer(self):
        for wizard_user in self:
            wizard_user.is_customer = wizard_user.partner_id.is_customer
    

    def action_apply(self):
        res = super(PortalWizardUserInherit, self).action_apply()
        for wizard_user in self.sudo().with_context(active_test=False):
            if wizard_user.is_customer:
                group_customer_portal = self.env.ref('equip3_sale_customer_portal.group_portal_customer')
                #Checking if the partner has a linked user
                user = wizard_user.partner_id.user_ids[0] if wizard_user.partner_id.user_ids else None
                if user:
                    #Checking if the user is in the group_customer_portal
                    if group_customer_portal not in user.groups_id:
                        user.write({'groups_id': [(4, group_customer_portal.id)]})
        return res

