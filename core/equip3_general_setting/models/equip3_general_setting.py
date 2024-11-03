# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    implementor_setting = fields.Boolean('Implementor Settings')
    general = fields.Boolean(string="General")
    purchase = fields.Boolean(string="Purchase")
    sales = fields.Boolean(string="Sales")
    inventory = fields.Boolean(string="Inventory")
    accounting = fields.Boolean(string="Accounting")
    manufacturing = fields.Boolean(string="Manufacturing")
    central_kitchen = fields.Boolean(string="Central Kitchen")
    human_resource = fields.Boolean(string="Human Resource")
    pos = fields.Boolean(string="POS")
    simple_manufacturing = fields.Boolean(string="Simple Manufacturing")
    assembly = fields.Boolean(string="Assembly")
    cutting = fields.Boolean(string='Cutting')
    mining = fields.Boolean(string='Mining')
    agriculture = fields.Boolean(string='Agriculture')
    company_code = fields.Char(string='Company Code', size=4)

    show_branch = fields.Boolean(string='Branch Required')

    _sql_constraints = [
        ('company_code_uniq', 'unique (company_code)', 'Company code cannot be same with the other companies !'),
    ]

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    implementor_setting = fields.Boolean(string='Implementor Settings', related='company_id.implementor_setting', readonly=False)
    general = fields.Boolean(string="General", related='company_id.general', readonly=False)
    purchase = fields.Boolean(string="Purchase", related='company_id.purchase', readonly=False)
    sales = fields.Boolean(string="Sales", related='company_id.sales', readonly=False)
    inventory = fields.Boolean(string="Inventory", related='company_id.inventory', readonly=False)
    accounting = fields.Boolean(string="Acccounting", related='company_id.accounting', readonly=False)
    manufacturing = fields.Boolean(string="Manufacturing", related='company_id.manufacturing', readonly=False)
    central_kitchen = fields.Boolean(string="Central Kitchen", related='company_id.central_kitchen', readonly=False)
    human_resource = fields.Boolean(string="Human Resource", related='company_id.human_resource', readonly=False)
    pos = fields.Boolean(string="POS", related='company_id.pos', readonly=False)
    simple_manufacturing = fields.Boolean(string="Simple Manufacturing", related='company_id.simple_manufacturing', readonly=False)
    assembly = fields.Boolean(string="Assembly", related="company_id.assembly", readonly=False)
    cutting = fields.Boolean(string="Cutting", related="company_id.cutting", readonly=False)
    mining = fields.Boolean(string="Mining", related="company_id.mining", readonly=False)
    agriculture = fields.Boolean(string="Agriculture", related="company_id.agriculture", readonly=False)

    show_branch = fields.Boolean(related='company_id.show_branch', readonly=False)

    @api.model
    def create(self, vals):
        res = super(ResConfigSettings, self).create(vals)
        self.env['res.groups'].sudo()._update_user_groups_view()
        return res

