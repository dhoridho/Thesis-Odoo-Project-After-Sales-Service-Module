from odoo import models, fields, api, _
from lxml import etree


class ResCompany(models.Model):
    _inherit = 'res.company'

    overburden = fields.Boolean(string='Overburden')
    coal_getting = fields.Boolean(string='Coal Getting')
    hauling = fields.Boolean(string='Hauling')
    crushing = fields.Boolean(string='Crushing')
    barging = fields.Boolean(string='Barging')

    overburden_uom = fields.Many2one('uom.uom', string="Unit of Measure")
    coal_getting_uom = fields.Many2one('uom.uom', string="Unit of Measure")
    hauling_uom = fields.Many2one('uom.uom', string="Unit of Measure")
    crushing_uom = fields.Many2one('uom.uom', string="Unit of Measure")
    barging_uom = fields.Many2one('uom.uom', string="Unit of Measure")

    mining_site = fields.Boolean(string='Mining Site', default=False)
    mining_project = fields.Boolean(string='Mining Pit', default=False)
    daily_production = fields.Boolean(string='Daily Production', default=False)
    mining_site_wa_notif = fields.Boolean(string='Mining Site Whatsapp Notification')
    mining_project_wa_notif = fields.Boolean(string='Mining Pit Whatsapp Notification')
    daily_production_wa_notif = fields.Boolean(string='Daily Production Whatsapp Notification')
    
    mining_production_plan = fields.Boolean(string='Mining Production Plan', default=False)
    mining_production_line = fields.Boolean(string='Mining Production Line', default=False)
    mining_production_act = fields.Boolean(string='Mining Production Actualization', default=False)
    mining_production_plan_wa_notif = fields.Boolean(string='Mining Production Plan Whatsapp Notification')
    mining_production_line_wa_notif = fields.Boolean(string='Mining Production Line Whatsapp Notification')
    mining_production_act_wa_notif = fields.Boolean(string='Mining Production Actualiation Whatsapp Notification')

    def write(self, vals):
        res = super(ResCompany, self).write(vals)
        menu_mining_site = self.env.ref("equip3_mining_operations.mining_menu_configuration_approval_matrix_mining_site")
        menu_mining_project = self.env.ref("equip3_mining_operations.mining_menu_configuration_approval_matrix_mining_project")

        menu_production_plan = self.env.ref("equip3_mining_operations.mining_menu_configuration_approval_matrix_production_plan")
        menu_production_line = self.env.ref("equip3_mining_operations.mining_menu_configuration_approval_matrix_production_line")
        menu_production_act = self.env.ref("equip3_mining_operations.mining_menu_configuration_approval_matrix_production_act")
        for company in self:

            for field_name, model_name in zip(
                ('mining_production_plan', 'mining_production_line', 'mining_production_act'),
                ('mining.production.plan', 'mining.production.line', 'mining.production.actualization')
            ):
                if field_name in vals:
                    is_on = company[field_name]
                    records = self.env[model_name].sudo().search([
                        ('company_id', '=', company.id),
                        ('state', '=', is_on and 'draft' or 'to_be_approved')
                    ])
                    records.action_toggle_matrix(is_on)

            if not company == self.env.company:
                continue
            
            menu_mining_site.active = company.mining_site
            menu_mining_project.active = company.mining_project
            menu_production_plan.active = company.mining_production_plan
            menu_production_line.active = company.mining_production_line
            menu_production_act.active = company.mining_production_act
        return res


class MaintenanceEquipment(models.Model):
    _inherit = "maintenance.equipment"

    capacity_asset = fields.Float(string="Capacity")
    capacity_asset_uom = fields.Many2one('uom.uom', string="UoM")
    is_asset_warehouse = fields.Boolean(string='Is a Warehouse')
    asset_warehouse_short_code = fields.Char(string='Short Name', size=5)
    warehouse_id = fields.Many2one('stock.warehouse', string="Short Name", context={'active_test': False})
    is_warehouse_create = fields.Boolean(string='Is Warehouse Created')

    @api.model
    def create(self, vals):
        res = super().create(vals)
        res._create_warehouse()
        return res

    def _create_warehouse(self):
        for record in self:
            if record.is_asset_warehouse and not record.warehouse_id:
                warehouse_id = self.env['stock.warehouse'].sudo().create({
                    'name': record.name,
                    'code': record.asset_warehouse_short_code,
                })
                record.warehouse_id = warehouse_id.id
                record.is_warehouse_create = True
            elif record.is_asset_warehouse and record.warehouse_id:
                record.warehouse_id.sudo().write({
                    'active': True,
                    'name': record.name,
                    'code': record.asset_warehouse_short_code,
                })
            elif not record.is_asset_warehouse and record.warehouse_id:
                record.warehouse_id.sudo().write({
                    'active': False
                })

    def write(self, vals):
        res = super(MaintenanceEquipment, self).write(vals)
        if 'is_asset_warehouse' in vals:
            self._create_warehouse()
        return res

class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    def name_get(self):
        result = []
        context = dict(self.env.context) or {}
        for record in self:
            name = record.name
            if context.get('default_vehicle_checkbox') and record.code:
                name = record.code
            result.append((record.id, name))
        return result

class InheritProductTmpl(models.Model):
    _inherit = 'product.template'

    mining_product_type = fields.Selection(
        selection=[
            ('product', 'Mining Product'),
            ('fuel', 'Fuel')
        ]
    )
    
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(InheritProductTmpl, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        
        if view_type != 'form':
            return result
            
        doc = etree.XML(result['arch'])
        mining_tab = doc.xpath("//page[@name='mining']")
        if not self.env.company.mining and mining_tab:
            mining_tab[0].set('invisible', '1')
            mining_tab[0].set('modifiers', '{"invisible": true}')
            
        result['arch'] = etree.tostring(doc, encoding='unicode')
        return result


class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(ProductProduct, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        
        if view_type != 'form':
            return result
            
        doc = etree.XML(result['arch'])
        mining_tab = doc.xpath("//page[@name='mining']")
        if not self.env.company.mining and mining_tab:
            mining_tab[0].set('invisible', '1')
            mining_tab[0].set('modifiers', '{"invisible": true}')
            
        result['arch'] = etree.tostring(doc, encoding='unicode')
        return result
