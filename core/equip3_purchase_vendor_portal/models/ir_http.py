# -*- encoding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @api.model
    def get_frontend_session_info(self):
        session_info = super(IrHttp, self).get_frontend_session_info()
        partner_id = request.env.user.sudo().partner_id
        session_info['is_both'] = partner_id.is_customer and partner_id.is_vendor
        session_info['is_vendor'] = not partner_id.is_customer and partner_id.is_vendor
        session_info['is_customer'] = partner_id.is_customer and not partner_id.is_vendor
        return session_info
        
class WebsiteMenuInherit(models.Model):
    _inherit = "website.menu"

    user_not_logged = fields.Boolean(
        string="User Not Logged",
        default=True,
        help=_("If checked, "
               "the menu will be displayed when the user is not logged "
               "and give access.")
    )
