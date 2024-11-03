from odoo import api, fields, models
from odoo.exceptions import Warning

class ProductProduct(models.Model):
    _inherit = "product.product"

    backup_start_time = fields.Float(string="Backup Start Time")
    backup_end_time = fields.Float(string="Backup End Time")

    @api.constrains('backup_start_time', 'backup_end_time')
    def _check_backup_start_end_time(self):
        for record in self:
            backup_start_time = record.backup_start_time
            backup_end_time = record.backup_end_time

            if backup_start_time < 0:
                raise Warning("Backup start time can't be minus (-)")

            if backup_end_time < 0:
                raise Warning("Backup end time can't be minus (-)")
