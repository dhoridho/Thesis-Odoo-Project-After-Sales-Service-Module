from odoo import models, fields, api

class ClearCache(models.TransientModel):
    _name = 'clear.cache.wizard'
    _description = 'Clear Cache Wizard'


    def do_clear_caches(self):
        user = self.env.user
        user.clear_caches()
