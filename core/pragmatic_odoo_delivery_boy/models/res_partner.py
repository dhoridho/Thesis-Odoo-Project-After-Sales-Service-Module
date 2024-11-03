from odoo import fields, models, api


class ResPartnerInherit(models.Model):
    _inherit = "res.partner"

    drive_rate = fields.Float("Driver Rate per KM")
    is_driver = fields.Boolean('Is a Driver', default=False)
    is_app_login = fields.Boolean(string='Is App Login', help="")
    device_imei_no = fields.Char(string='Device IMEI No.', help="")
    status = fields.Selection([('available', 'Available'), ('not_available', 'Not Available')],
                              string="Delivery Boy Status", default='available')
    driver_message = fields.Text(string='Driver Message')

    def set_unset_delivery_boy(self):
        if self.is_driver == True:
            self.is_driver = False
        else:
            self.is_driver = True

    def write(self, vals):
        res = super(ResPartnerInherit, self).write(vals)
        if 'street' in vals or 'country_id' in vals or 'state_id' in vals:
            self.geo_localize()
        return res


