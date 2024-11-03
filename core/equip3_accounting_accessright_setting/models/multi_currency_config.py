from odoo import fields, models
 
class ResCompany(models.Model):
    _inherit = "res.company"

    


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'


    

    