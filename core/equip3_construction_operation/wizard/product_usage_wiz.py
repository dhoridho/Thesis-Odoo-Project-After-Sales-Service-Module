from odoo import _, api, fields, models
from datetime import datetime
from odoo.exceptions import ValidationError


class ProductUsageWiz(models.TransientModel):
    _name = 'product.usage.wiz'
    _description = 'Create Product Usage'

    def product_usage(self):
        for record in self:
            context = {
                'default_scrap_request_name': record.name,
                'default_project': record.project_id.id,
                'default_schedule_date': record.schedule_date,
                'default_material_type': record.material_type,
                'default_work_orders': record.job_order.id,
                'default_progress_id': record.progress_id.id,
                'default_warehouse_id': record.warehouse.id,
                'default_responsible_id': record.responsible.id,
                'default_analytic_tag_ids': record.analytic_groups.ids,
                'default_scrap_type': record.usage_type.id,
                'default_is_product_usage': True,
            }
            return {
                'type': 'ir.actions.act_window',
                'name': 'Product Usage',
                'view_mode': 'form',
                'res_model': 'stock.scrap.request',
                'target': 'current',
                'context': context,
            }

    name = fields.Char('Name')
    project_id = fields.Many2one('project.project', string='Project', required=True)
    job_order = fields.Many2one('project.task', string='Job Order', domain="[('project_id','=', project_id),('state','=', 'inprogress')]")
    schedule_date = fields.Date('schedule Date', default=datetime.now(), required=True)
    material_type = fields.Selection([('material','Material'), ('equipment','Equipment'),('overhead','Overhead')], string = "Material Type")
    warehouse = fields.Many2one('stock.warehouse','Warehouse',context="{'default_active_id': active_id}")
    responsible = fields.Many2one('res.users','Responsible')
    usage_type = fields.Many2one('usage.type','Usage Type',invisible="1",)
    analytic_groups = fields.Many2one('account.analytic.tag','Analytic Groups')
    progress_id = fields.Many2one('progress.history', string="Progress", domain="[('work_order','=', job_order)]")


# Workaround to immediately remove labour from material type to existing database
class ProductUsageWiz(models.TransientModel):
    _inherit = 'product.usage.wiz'

    material_type = fields.Selection(
        [('material', 'Material'), ('overhead', 'Overhead')], string="Material Type")


