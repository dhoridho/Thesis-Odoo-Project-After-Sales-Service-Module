from odoo import api, fields, models
from odoo.exceptions import Warning

class ProductTemplate(models.Model):
    _inherit = "product.template"

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


    @api.model
    def create(self, vals_list):
        res = super(ProductTemplate, self).create(vals_list)
        for template in self:
            product_ids = self.env['product.product'].search([('product_tmpl_id', '=', res.id)])
            for product in product_ids:
                product.update({
                    'backup_start_time': template.backup_start_time,
                    'backup_end_time': template.backup_end_time,
                })
        return res

    def write(self, values):
        res = super(ProductTemplate, self).write(values)
        for template in self:
            product_ids = self.env['product.product'].search([('product_tmpl_id', '=', template.id)])
            for product in product_ids:
                product.update({
                    'backup_start_time': template.backup_start_time,
                    'backup_end_time': template.backup_end_time,
                })

        return res
