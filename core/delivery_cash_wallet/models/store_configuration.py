from odoo import api, models, fields, _


class StoreConfiguration(models.Model):
    _name = "store.configuration"
    _description = 'Store Configuration'
    _rec_name = "location_id"

    def _get_sales_managers(self):
        domain = [('groups_id', '=',self.env.ref('stock.group_stock_user').id),('groups_id', '=',self.env.ref('sales_team.group_sale_salesman').id)]
        return domain

    location_id = fields.Many2one("stock.location",string="Store/Location")
    sales_manager_ids = fields.Many2many("res.users","sales_manager_users_rel","manager_id","user_id",string="Sales Managers",domain=_get_sales_managers)
    delivery_boy_ids = fields.Many2many("res.users","delivery_boy_users_rel","delivery_boy_id","user_id",string="Delivery Boys",domain=lambda self: [('partner_id.is_driver', '=', True)])
    store_account_id = fields.Many2one("account.account",string="Store Cash Account",domain=lambda self: [('user_type_id.id', '=', self.env.ref('account.data_account_type_liquidity').id)])
    delivery_boy_account_id = fields.Many2one("account.account",string="Deliveryboys Cash A/c",domain=lambda self: [('user_type_id.id', '=', self.env.ref('account.data_account_type_liquidity').id)])
    delivery_boy_journal_id = fields.Many2one('account.journal',string="Delivery Boy Journal", domain=[('type','=','cash')])
    store_journal_id = fields.Many2one('account.journal',string="Store Journal", domain=[('type','=','cash')])

    @api.model
    def create(self,vals):
        res = super(StoreConfiguration, self).create(vals)
        for user in res.sales_manager_ids:
            user.location_ids = [(4,res.location_id.id)]
        return res

    def write(self,vals):
        for rec in self:
            for user in rec.sales_manager_ids:
                user.location_ids = [(3,rec.location_id.id)]
            res = super(StoreConfiguration, rec).write(vals)
            for user in rec.sales_manager_ids:
                user.location_ids = [(4,rec.location_id.id)]
            return res
    
    def unlink(self):
        for rec in self:
            for user in rec.sales_manager_ids:
                user.location_ids = [(3,rec.location_id.id)]
        return super(StoreConfiguration, self).unlink()
