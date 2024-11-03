from odoo import models,fields,api,_


class PortalWizardUserInherit(models.TransientModel):
    _inherit = 'portal.wizard.user'

    is_vendor = fields.Boolean(string='Is Vendor', compute='_compute_is_vendor')

    @api.depends('partner_id')
    def _compute_is_vendor(self):
        for wizard_user in self:
            wizard_user.is_vendor = wizard_user.partner_id.is_vendor
            if wizard_user.is_vendor:
                wizard_user.in_portal = True
    

    def action_apply(self):
        res = super(PortalWizardUserInherit, self).action_apply()
        for wizard_user in self.sudo().with_context(active_test=False):
            if wizard_user.is_vendor:
                group_vendor_portal = self.env.ref('equip3_purchase_vendor_portal.group_portal_vendor')
                #Checking if the partner has a linked user
                user = wizard_user.partner_id.user_ids[0] if wizard_user.partner_id.user_ids else None
                if user:
                    user.is_tendor_vendor = True
                    #Checking if the user is in the group_vendor_portal
                    if group_vendor_portal not in user.groups_id:
                        user.write({'groups_id': [(4, group_vendor_portal.id)]})
        return res

