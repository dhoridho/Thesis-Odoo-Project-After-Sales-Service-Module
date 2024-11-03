# -*- encoding: utf-8 -*-

from odoo import models, fields
from odoo.tools.translate import _


class WebsiteMenu(models.Model):
    """Improve website.menu with adding booleans that drive
    if the menu is displayed when the user has an access to the Delivery Control App.
    """
    _inherit = 'website.menu'

    is_display_in_delivery_control_app = fields.Boolean(
        string="Delivery",
        default=True,
        help=_("If checked, "
               "the menu will be displayed when the user is logged and responsible for manage sale order delivery.")
    )

