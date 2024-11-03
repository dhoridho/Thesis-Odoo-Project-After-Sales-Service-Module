# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models, tools

from odoo.addons.izi_marketplace.objects.utils.tools import get_mp_asset


class MarketplaceReturn(models.Model):
    _name = 'mp.return'
    _inherit = 'mp.base'
    _rec_mp_return_statuses = {}
    _rec_name = 'mp_return_sn'
    _description = 'Marketplace Return'

    MP_RETURN_STATUSES = [
        ('new', 'New'),
        ('in_requested', 'In Request'),
        ('in_process', 'In Process'),
        ('completed', 'Completed'),
        ('closed', 'Closed'),
    ]

    MP_RETURN_TYPE = [
        ('refund', 'Refund Only'),
        ('return_refund', 'Return & Refund'),
    ]

    mp_return_sn = fields.Char(string='MP Return SN')
    sale_id = fields.Many2one(comodel_name='sale.order', string='Order Reference',
                              compute="_get_order_id", store=True, readonly=True)
    mp_return_status = fields.Selection(string="MP Return Status", selection=MP_RETURN_STATUSES, required=False,
                                        store=True, compute="_compute_mp_return_status", readonly=True)
    mp_order_exid = fields.Char(string='MP Order External ID', readonly=True)
    mp_return_reason = fields.Text(string='Text Reason', readonly=True)
    mp_return_ship_due_date = fields.Datetime(string='Return Ship Due Date', readonly=True)
    mp_return_create_time = fields.Datetime(string='Return Create Time', readonly=True)
    mp_return_update_time = fields.Datetime(string='Return Update Time', readonly=True)
    mp_return_amount = fields.Float(string='Return Amount Total', readonly=True)
    mp_return_line = fields.One2many(
        comodel_name='mp.return.line',
        inverse_name='mp_return_id',
        string='MP Return Line',
    )
    mp_return_image_ids = fields.One2many(
        comodel_name='mp.return.image',
        inverse_name='mp_return_id',
        string='MP Return Images',
    )
    type = fields.Selection(selection=MP_RETURN_TYPE, string='Type')
    mp_user_name = fields.Char(string='Buyer Name')

    @classmethod
    def _build_model_attributes(cls, pool):
        super(MarketplaceReturn, cls)._build_model_attributes(pool)
        cls._add_rec_mp_return_status()

    @classmethod
    def _add_rec_mp_return_status(cls, mp_return_statuses=None):
        if mp_return_statuses:
            cls._rec_mp_return_statuses = dict(cls._rec_mp_return_statuses, **dict(mp_return_statuses))

    @api.depends('sale_id', 'mp_order_exid')
    def _get_order_id(self):
        so_obj = self.env['sale.order']
        for rec in self:
            if rec.mp_order_exid:
                order_id = so_obj.search([('mp_external_id', '=', rec.mp_order_exid)], limit=1)
                if order_id:
                    rec.sale_id = order_id.id
                else:
                    rec.sale_id = None
            else:
                rec.sale_id = None

    def _compute_mp_return_status(self):
        for mp_return in self:
            if mp_return.marketplace not in mp_return._rec_mp_return_statuses.keys():
                mp_return.mp_return_status = None
            else:
                mp_return_status_field, mp_return_statuses = mp_return._rec_mp_return_statuses[mp_return.marketplace]
                mp_return_status_value = 'new'
                for mp_return_status, mp_return_status_codes in mp_return_statuses.items():
                    if getattr(mp_return, mp_return_status_field) in mp_return_status_codes:
                        mp_return_status_value = mp_return_status
                        break
                mp_return.mp_return_status = mp_return_status_value

    def fetch_order_return(self):
        if hasattr(self, '%s_fetch_order_return' % self.marketplace):
            getattr(self, '%s_fetch_order_return' % self.marketplace)()


class MarketplaceReturnLine(models.Model):
    _name = 'mp.return.line'
    _inherit = 'mp.base'
    _description = 'Marketplace Return Line'

    name = fields.Char(string='Product Name', compute='_get_item_sku_name', store=True)
    default_code = fields.Char(string='Product SKU', compute='_get_item_sku_name', store=True)
    product_id = fields.Many2one('product.product', string='Product ID')
    mp_item_price = fields.Float(string='MP Item Price')
    mp_item_qty = fields.Integer(string='MP Item Qty')
    mp_return_id = fields.Many2one('mp.return', string='Return ID')

    @api.depends('name', 'default_code', 'product_id')
    def _get_item_name(self):
        for rec in self:
            if rec.product_id:
                rec.name = rec.product_id.display_name
                rec.default_code = rec.product_id.default_code
            else:
                rec.name = ''
                rec.default_code = ''


class MarketplaceReturnImage(models.Model):
    _name = 'mp.return.image'
    _description = 'Marketplace Return Image'

    sequence = fields.Integer(string="Sequence", default=1)
    name = fields.Char(string="Image URL")
    image = fields.Binary('Image', attachment=True)
    mp_return_id = fields.Many2one(comodel_name="mp.return",
                                   string="Marketplace Return", readonly=True, ondelete="cascade")


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Return
    mp_return_ids = fields.One2many('mp.return', 'sale_id', string='Return/Refund')
    mp_return_count = fields.Integer(string='MP Returns', compute='_compute_return_ids')

    @api.depends('mp_return_ids')
    def _compute_return_ids(self):
        for order in self:
            order.mp_return_count = len(order.mp_return_ids)

    def action_view_mp_return(self):
        '''
        This function returns an action that display existing Marketplace Return Orders
        of given sales order ids. It can either be a in a list or in a form
        view, if there is only one return order to show.
        '''
        action = self.env["ir.actions.actions"]._for_xml_id("izi_marketplace.action_window_mp_return_per_marketplace")

        mp_returns = self.mapped('mp_return_ids')
        if len(mp_returns) > 1:
            action['domain'] = [('id', 'in', mp_returns.ids)]
        elif mp_returns:
            form_view = [(self.env.ref('izi_marketplace.form_mp_return').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = mp_returns.id
        # Prepare the context.
        mp_return_id = mp_returns[0]
        action['context'] = dict(self._context,
                                 default_marketplace=self.mp_account_id.marketplace,
                                 default_mp_account_id=self.mp_account_id.id,
                                 default_sale_id=self.id)
        return action
