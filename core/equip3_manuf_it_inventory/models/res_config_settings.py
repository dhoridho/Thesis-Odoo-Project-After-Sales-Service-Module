from odoo import _, api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    _description = 'Resource Config Settings'


    is_it_inventory = fields.Boolean(string="IT Inventory", default=True)
    # is_ceisa_it_inventory = fields.Boolean(string="Set Ceisa 4.0", default=False)
    is_ceisa_it_inventory = fields.Boolean(string="Set Ceisa 4.0",
                                           related='company_id.is_ceisa_it_inventory', readonly=False)


    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        company = self.env.company
        ICP = self.env['ir.config_parameter'].sudo()
        res.update({'is_it_inventory': ICP.get_param('is_it_inventory', False),
                    'is_ceisa_it_inventory': company.is_ceisa_it_inventory,
                    })
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ISP = self.env['ir.config_parameter'].sudo()
        ISP.set_param('is_it_inventory', self.is_it_inventory)
        # ISP.set_param('is_ceisa_it_inventory', self.is_ceisa_it_inventory)
        company_id = self.env.company.id
        # users = self.env['res.users'].search([('company_id', '=', company_id)])
        users=self.env['res.users'].search([('active', '=', True), ('share', '=', False)]).filtered(lambda u,current_company_id=company_id:current_company_id in u.company_ids.ids)
        # group_id = self.env['res.groups'].search([('name', '=', 'visible ceisa menu')])
        group_id = self.env.ref('equip3_manuf_it_inventory.group_ceisa_visibility_menu').id
        visgroup = False
        if group_id:
            visgroup = self.env['res.groups'].search([('id', '=', group_id)], limit=1)

        self.company_id.sudo().update({'is_ceisa_it_inventory': self.is_ceisa_it_inventory})
        if self.is_it_inventory == False:
            self.env.ref('equip3_manuf_it_inventory.it_inventory_menu_root').active = False
        else:
            self.env.ref('equip3_manuf_it_inventory.it_inventory_menu_root').active = True

        self.env.ref('equip3_manuf_it_inventory.menu_national_port_master_data').active = True
        self.env.ref('equip3_manuf_it_inventory.menu_overseas_port_master_data').active = True

        if self.is_ceisa_it_inventory == False:
            if visgroup:
                visgroup.write({'users': [(3, user.id) for user in users]})
            # self.env.ref('equip3_manuf_it_inventory.menu_national_port_master_data').active = False
            # self.env.ref('equip3_manuf_it_inventory.menu_overseas_port_master_data').active = False
        else:
            if visgroup:
                visgroup.write({'users': [(4, user.id) for user in users]})
            # self.env.ref('equip3_manuf_it_inventory.menu_national_port_master_data').active = True
            # self.env.ref('equip3_manuf_it_inventory.menu_overseas_port_master_data').active = True
