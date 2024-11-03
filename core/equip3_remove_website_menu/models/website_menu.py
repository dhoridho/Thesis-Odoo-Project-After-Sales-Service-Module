
from odoo import models,api

class WebsiteMenu(models.Model):
    _inherit = 'website.menu'

    @api.model
    def delete_from_website_menu(self):
        query = """
            DELETE from website_menu where name = 'Delivery Route'
        """
        self.env.cr.execute(query)
