from odoo import fields, models, api
from odoo.exceptions import Warning
import datetime
from datetime import datetime, timedelta, date


class ResPartnerInherit(models.Model):
    _inherit = "res.partner"

    @api.model
    def create(self, vals):
        if self._context.get('is_driver'):
            if not vals.get('email'):
                raise Warning("Please enter an email address.")
            group_portal_user = self.env.ref('base.group_portal')
            group_driver = self.env.ref('pragmatic_odoo_delivery_boy.group_pragtech_driver')
            user_vals = {
                'name': vals.get('name'),
                'login': vals.get('email'),
                'groups_id': [(6, 0, [group_portal_user.id,group_driver.id])],
                'company_id': self.env.user.company_id.id,
            }
        res = super(ResPartnerInherit, self).create(vals)
        if self._context.get('is_driver'):
            user_vals.update({'partner_id': res.id})
            user = self.env['res.users'].create(user_vals)
            location = self.env['stock.location'].create({
                'name':res.name,
                'usage':'internal',
            })
            delivery_boy_location = self.env['delivery.boy.store'].create({
                'delivery_boy_id':user.id,
                'location_id':location.id
            })
            delivery_boy_status = self.env['delivery.boy.status'].create({
                'driver_id':user.id,
                'state':'offline',
            })
            delivery_boy_log = self.env['delivery.boy.log'].create({
                'driver_id':user.id,
                'date':datetime.now()
            })
            driver_wallet = self.env['driver.wallet'].create({
             'delivery_boy_id':res.id,
            })
        return res


class ChangePasswordWizard(models.TransientModel):
    _inherit = "change.password.wizard"

    def _default_user_ids(self):
        user_ids = self._context.get('active_model') == 'res.users' and self._context.get('active_ids') or []
        if self._context.get('active_model') == 'res.partner':
            id=self._context.get('active_id')
            user = self.env['res.users'].search([('partner_id','=',id)])
            user_ids = user.id
        return [
            (0, 0, {'user_id': user.id, 'user_login': user.login})
            for user in self.env['res.users'].browse(user_ids)
        ]

    user_ids = fields.One2many('change.password.user', 'wizard_id', string='Users', default=_default_user_ids)
