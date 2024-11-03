# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from datetime import datetime

_marketplace_selection = [
    ('tokopedia', 'Tokopedia'),
    ('shopee', 'Shopee'),
    ('lazada', 'Lazada'),
    ('tiktok', 'TikTok Shop'),
    # ('blibli', 'Blibli'),
    # ('shopify', 'Shopify'),
    # ('zalora', 'Zalora'),
    # ('bukalapak', 'Bukalapak'),
]

HOSTS_SELLER = {
    'sp_id': 'https://seller.shopee.co.id',
    'lz_id': 'https://sellercenter.lazada.co.id',
    'tts_id': 'https://seller-id.tokopedia.com',
    'sp_sg': 'https://seller.shopee.sg',
    'lz_sg': 'https://sellercenter.lazada.sg',
    'tts_sg': 'https://seller-sg.tiktok.com',
    'sp_ph': 'https://seller.shopee.ph',
    'lz_ph': 'https://sellercenter.lazada.com.ph',
    'tts_ph': 'https://seller-ph.tiktok.com/',
    'sp_my': 'https://seller.shopee.com.my',
    'lz_my': 'https://sellercenter.lazada.com.my',
    'tts_my': 'https://seller-my.tiktok.com',
    'sp_th': 'https://seller.shopee.co.th',
    'lz_th': 'https://sellercenter.lazada.co.th',
    'tts_th': 'https://seller-th.tiktok.com',
    'sp_vn': 'https://banhang.shopee.vn',
    'lz_vn': 'https://sellercenter.lazada.vn',
    'tts_vn': 'https://seller-vn.tiktok.com',
    'sp_br': 'https://seller.shopee.com.br',
    'tts-uk': 'https://seller-uk.tiktok.com',
    'tts_us': 'https://seller-us.tiktok.com',
    'tp': 'https://seller.tokopedia.com'
}


class MarketplaceAccount(models.Model):
    _name = 'mp.account'
    _description = 'Marketplace Account'

    # @api.multi
    @api.constrains()
    def _check_required_if_marketplace(self):
        """ If the field has 'required_if_marketplace="<marketplace>"' attribute, then it
        required if record.marketplace is <marketplace>. """
        empty_field = []
        for record in self:
            for k, f in record._fields.items():
                if getattr(f, 'required_if_marketplace', None) == record.marketplace and not record[k]:
                    empty_field.append('Field %(field)s at ID %(id)s is empty.' % {
                        'field': self.env['ir.model.fields'].search([
                            ('name', '=', k),
                            ('model', '=', record._name)
                        ]).field_description,
                        'id': record.id,
                    })
        if empty_field:
            raise ValidationError(', '.join(empty_field))
        return True

#     _constraints = [
#         (_check_required_if_marketplace, 'Required fields not filled', []),
#     ]

    MP_ACCOUNT_STATES = [
        ('new', 'New'),
        ('authenticating', 'Authenticating'),
        ('authenticated', 'Authenticated'),
    ]

    MP_WEBHOOK_STATES = [
        ('registered', 'Registered'),
        ('no_register', 'No Register')
    ]

    READONLY_STATES = {
        'authenticated': [('readonly', True)],
        'authenticating': [('readonly', True)],
    }

    _AWB_ACTION_TYPE = [
        ('open', 'Open AWB in new Tab'),
        ('download', 'Auto Downloadable AWB'),
        ('print', 'Direct Print AWB')
    ]

    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    name = fields.Char(string="Name", required=True)
    marketplace = fields.Selection(string="Marketplace", selection=_marketplace_selection,
                                   required=True, states=READONLY_STATES)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(comodel_name="res.company", string="Company", index=1, readonly=False, required=True,
                                 default=lambda self: self.env['res.company']._company_default_get(),
                                 states=READONLY_STATES)
    currency_id = fields.Many2one(comodel_name="res.currency", string="Currency", required=True,
                                  default=lambda s: s.env.ref('base.IDR'))
    state = fields.Selection(string="Status", selection=MP_ACCOUNT_STATES, required=True, default="new",
                             states=READONLY_STATES)
    mp_token_ids = fields.One2many(comodel_name="mp.token", inverse_name="mp_account_id", string="Marketplace Tokens",
                                   required=False, states=READONLY_STATES)
    mp_token_id = fields.Many2one(comodel_name="mp.token", string="Marketplace Token", compute="_compute_mp_token")
    access_token = fields.Char(string="Access Token", related="mp_token_id.name", readonly=True)
    access_token_expired_date = fields.Datetime(string="Expired Date", related="mp_token_id.expired_date",
                                                readonly=True)
    auth_message = fields.Char(string="Authentication Message", readonly=True)
    mp_product_ids = fields.One2many(comodel_name="mp.product", inverse_name="mp_account_id",
                                     string="Marketplace Product(s)")
    branch_id = fields.Many2one('res.branch', string='Branch', required=True, default=lambda self: self.env.branches if len(self.env.branches) == 1 else False,
        readonly=False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
    warehouse_id = fields.Many2one('stock.warehouse', string='Default Warehouse Marketplace', domain=lambda self: [('id', 'in', self.env.user.warehouse_ids.ids)])
    insurance_product_id = fields.Many2one(comodel_name="product.product", string="Default Insurance Product",
                                           default=lambda self: self._get_default_insurance_product_id())
    sale_channel_id = fields.Many2one(comodel_name='sale.channel', string='Default Sales Channel')
    team_id = fields.Many2one(comodel_name='crm.team', string='Default Sales Channel')
    user_id = fields.Many2one(comodel_name='res.users', string='Default Salesperson')
    payment_term_id = fields.Many2one('account.payment.term', string='Default Payment Terms')
    pricelist_id = fields.Many2one('product.pricelist', string='Default Pricelist')
    wallet_journal_id = fields.Many2one('account.journal', string='Wallet Journal Account')
    global_discount_product_id = fields.Many2one(comodel_name="product.product",
                                                 string="Default Global Discount Product",
                                                 default=lambda self: self._get_default_global_discount_product_id())
    adjustment_product_id = fields.Many2one(comodel_name="product.product",
                                            string="Default Adjustment Product",
                                            default=lambda self: self._get_default_adjustment_product_id())
    services_product_id = fields.Many2one(comodel_name="product.product",
                                            string="Default Services Product",
                                            default=lambda self: self._get_default_services_product_id())
    create_invoice = fields.Boolean(string="Auto Create Invoice", default=False,
                                    help="Auto creating invoices after confirm sale order")
    auto_confirm = fields.Boolean(string="Auto Confirm Sale Order", default=True,
                                  help="Auto Confirm Sale Order if order status has processed")
    create_invoice_after_delivery = fields.Boolean(string="Auto Create Invoice After Delivery", default=False,
                                    help="Auto creating invoices after validate delivery order")
    keep_order_date = fields.Boolean(string="Keep Order Date", default=True,
                                     help="Keep Order date when Confirm Sales Order")
    get_unpaid_orders = fields.Boolean(string="Get Unpaid Order", default=False,
                                       help="Get order with status UNPAID from Shopee")
    get_cancelled_orders = fields.Boolean(string="Get Cancelled Order", default=False,
                                          help="Get order CANCELLED from marketplace if the order is not exists before")
    auto_print_label = fields.Boolean(string="Auto Print Shipping Label", default=False,
                                      help="Auto Print Shipping Label after Validating Stock Transfer")
    default_awb_action = fields.Selection(selection=_AWB_ACTION_TYPE, string='AWB Action Type', default='open')
    auto_process_orders = fields.Boolean(
        string="Auto Ship MP Order", help='If you are activate this feature, the system will be automatic processing order to marketplace')
    debug_force_update = fields.Boolean(string="Force Update", default=False,
                                        help="Force update even there is no changes from marketplace")
    debug_force_update_raw = fields.Boolean(string="Force Update Raw Only", default=False,
                                            help="Force update raw field only")
    debug_store_product_img = fields.Boolean(string="Store Product Image",
                                             default=False, help="Store product image as binary into the database")
    debug_product_limit = fields.Integer(string="Product Import Limit", required=True, default=0,
                                         help="Maximum number to import product, set 0 for unlimited!")
    debug_order_limit = fields.Integer(string="Order Import Limit", required=True, default=0,
                                       help="Maximum number to import order, set 0 for unlimited!")
    debug_skip_error = fields.Boolean(string="Skip Error", default=False,
                                      help="Skip error when processing records from marketplace")

    cron_id = fields.Many2one(comodel_name='ir.cron', string='Order Scheduler', readonly=True)
    cron_user_id = fields.Many2one('res.users', string='Scheduler User', related='cron_id.user_id')
    cron_interval_number = fields.Integer(string="Sync Every", default=1,
                                          help="Repeat every x.", related='cron_id.interval_number')
    cron_nextcall = fields.Datetime(string='Next Execution Date', related='cron_id.nextcall')
    cron_interval_type = fields.Selection(string='Interval Unit',
                                          default='minutes', related='cron_id.interval_type')
    cron_active = fields.Boolean(string='Active Scheduler', related='cron_id.active', readonly=False)
    mp_log_error_ids = fields.One2many(comodel_name='mp.log.error',
                                       inverse_name='mp_account_id', string='Marketplace Log Error')
    mp_webhook_state = fields.Selection(string="Webhook Status", selection=MP_WEBHOOK_STATES,
                                        default="no_register", readonly=True)


    @api.model
    def create(self, vals):
        vals.update({'create_invoice': True})
        res = super(MarketplaceAccount, self).create(vals)
        if not res.cron_id:
            if str(res.marketplace.capitalize()) == 'Shopee':
                attribute_cron = self.env['ir.cron'].sudo().create({
                    'name': 'IZI Shopee Attribute Scheduler %s' % (str(res.id)),
                    'model_id': self.env.ref('%s.model_%s' % (self._module, '_'.join(self._name.split('.')))).id,
                    'state': 'code',
                    'code': "model.shopee_get_category_attribute(id=%d);" %
                            ((res.id)),
                    'interval_number': 5,
                    'interval_type': 'minutes',
                    'numbercall': -1,
                    'active': False,
                })
            if str(res.marketplace.capitalize()) == 'Tokopedia':
                attribute_cron = self.env['ir.cron'].sudo().create({
                    'name': 'IZI Tokopedia Attribute Scheduler %s' % (str(res.id)),
                    'model_id': self.env.ref('%s.model_%s' % (self._module, '_'.join(self._name.split('.')))).id,
                    'state': 'code',
                    'code': "model.tokopedia_get_attribute(id=%d);" %
                            ((res.id)),
                    'interval_number': 1,
                    'interval_type': 'minutes',
                    'numbercall': -1,
                    'active': False,
                })
            if str(res.marketplace.capitalize()) == 'Lazada':
                lz_attribute_cron = self.env['ir.cron'].sudo().create({
                    'name': 'IZI Lazada Attribute Scheduler %s' % (str(res.id)),
                    'model_id': self.env.ref('%s.model_%s' % (self._module, '_'.join(self._name.split('.')))).id,
                    'state': 'code',
                    'code': "model.lazada_get_attribute(id=%d);" % ((res.id)),
                    'interval_number': 1,
                    'interval_type': 'minutes',
                    'numbercall': -1,
                    'active': False,
                })
                # variant_cron = self.env['ir.cron'].sudo().create({
                #     'name': 'IZI Tokopedia Variant Scheduler %s' % (str(res.id)),
                #     'model_id': self.env.ref('%s.model_%s' % (self._module, '_'.join(self._name.split('.')))).id,
                #     'state': 'code',
                #     'code': "model.tokopedia_get_variant(id=%d);" %
                #             ((res.id)),
                #     'interval_number': 1,
                #     'interval_type': 'minutes',
                #     'numbercall': -1,
                #     'active': False,
                # })
            order_cron = self.env['ir.cron'].sudo().create({
                'name': 'IZI %s Order Scheduler %s' % (str(res.marketplace.capitalize()), str(res.id)),
                'model_id': self.env.ref('%s.model_%s' % (self._module, '_'.join(self._name.split('.')))).id,
                'state': 'code',
                'code': "model.%s_get_orders(id=%d,time_range='last_hour',params='by_date_range');" %
                ((res.marketplace), (res.id)),
                'interval_number': 5,
                'interval_type': 'minutes',
                'numbercall': -1,
                'active': False,
            })
            return_cron = self.env['ir.cron'].sudo().create({
                'name': 'IZI %s Return Scheduler %s' % (str(res.marketplace.capitalize()), str(res.id)),
                'model_id': self.env.ref('%s.model_%s' % (self._module, '_'.join(self._name.split('.')))).id,
                'state': 'code',
                'code': "model.get_return(id=%d,time_range='last_hour',params='by_date_range');" % ((res.id)),
                'interval_number': 30,
                'interval_type': 'minutes',
                'numbercall': -1,
                'active': False,
            })
            webhook_process_cron = self.env['ir.cron'].sudo().create({
                'name': 'IZI %s Process Webhook Order %s' % (str(res.marketplace.capitalize()), str(res.id)),
                'model_id': self.env.ref('%s.model_%s' % (self._module, '_'.join(self._name.split('.')))).id,
                'state': 'code',
                'code': "model.process_webhook_orders(id=%d);" % ((res.id)),
                'interval_number': 1,
                'interval_type': 'minutes',
                'numbercall': -1,
                'active': True,
            })
            auto_ship_order = self.env['ir.cron'].sudo().create({
                'name': 'IZI %s Auto Ship Order %s' % (str(res.marketplace.capitalize()), str(res.id)),
                'model_id': self.env.ref('%s.model_%s' % (self._module, '_'.join(self._name.split('.')))).id,
                'state': 'code',
                'code': "model.auto_ship_orders(id=%d, tz=timezone(%s));" % ((res.id), self._context.get('tz', 'Asia/Jakarta')),
                'interval_number': 2,
                'interval_type': 'minutes',
                'numbercall': -1,
                'active': False,
            })
            wallet_cron = self.env['ir.cron'].sudo().create({
                'name': 'IZI %s Wallet Scheduler %s' % (str(res.marketplace.capitalize()), str(res.id)),
                'model_id': self.env.ref('%s.model_%s' % (self._module, '_'.join(self._name.split('.')))).id,
                'state': 'code',
                'code': "model.get_orders_wallet(id=%d,time_range='last_hours',params='by_date_range',mode='data_only');" %
                        ((res.id)),
                'interval_number': 30,
                'interval_type': 'minutes',
                'numbercall': -1,
                'active': False,
            })
            res.cron_id = order_cron.id
        return res

    def write(self, vals):
        vals.update({'create_invoice': True})
        if 'active' in vals and not vals.get('active'):
            self.action_reauth()
            vals.update({'cron_active': False})
            order_name = 'IZI %s Order Scheduler %s' % (str(self.marketplace.capitalize()), str(self.id))
            cron_order = self.env['ir.cron'].sudo().search([('name', '=', order_name), ('active', '=', True)])
            if cron_order:
                cron_order.sudo().write({'active': False})

            return_name = 'IZI %s Return Scheduler %s' % (str(self.marketplace.capitalize()), str(self.id))
            return_order = self.env['ir.cron'].sudo().search([('name', '=', return_name), ('active', '=', True)])
            if return_order:
                return_order.sudo().write({'active': False})

            ship_name = 'IZI %s Auto Ship Order %s' % (str(self.marketplace.capitalize()), str(self.id))
            ship_order = self.env['ir.cron'].sudo().search([('name', '=', ship_name), ('active', '=', True)])
            if ship_order:
                ship_order.sudo().write({'active': False})

            webhook_name = 'IZI %s Process Webhook Order %s' % (str(self.marketplace.capitalize()), str(self.id))
            webhook_order = self.env['ir.cron'].sudo().search([('name', '=', webhook_name), ('active', '=', True)])
            if webhook_order:
                webhook_order.sudo().write({'active': False})

            attrib_name = 'IZI %s Attribute Scheduler %s' % (str(self.marketplace.capitalize()), str(self.id))
            attrib_order = self.env['ir.cron'].sudo().search([('name', '=', attrib_name), ('active', '=', True)])
            if attrib_order:
                attrib_order.sudo().write({'active': False})

            wallet_name = 'IZI %s Wallet Scheduler %s' % (str(self.marketplace.capitalize()), str(self.id))
            wallet_order = self.env['ir.cron'].sudo().search([('name', '=', wallet_name), ('active', '=', True)])
            if wallet_order:
                wallet_order.sudo().write({'active': False})
        res = super(MarketplaceAccount, self).write(vals)
        return res

    def unlink(self):
        order_name = 'IZI %s Order Scheduler %s' % (str(self.marketplace.capitalize()), str(self.id))
        cron_order = self.env['ir.cron'].sudo().search([('name', '=', order_name)])
        if cron_order:
            cron_order.sudo().unlink()

        return_name = 'IZI %s Return Scheduler %s' % (str(self.marketplace.capitalize()), str(self.id))
        return_order = self.env['ir.cron'].sudo().search([('name', '=', return_name)])
        if return_order:
            return_order.sudo().unlink()

        ship_name = 'IZI %s Auto Ship Order %s' % (str(self.marketplace.capitalize()), str(self.id))
        ship_order = self.env['ir.cron'].sudo().search([('name', '=', ship_name)])
        if ship_order:
            ship_order.sudo().unlink()

        webhook_name = 'IZI %s Process Webhook Order %s' % (str(self.marketplace.capitalize()), str(self.id))
        webhook_order = self.env['ir.cron'].sudo().search([('name', '=', webhook_name)])
        if webhook_order:
            webhook_order.sudo().unlink()

        attrib_name = 'IZI %s Attribute Scheduler %s' % (str(self.marketplace.capitalize()), str(self.id))
        attrib_order = self.env['ir.cron'].sudo().search([('name', '=', attrib_name)])
        if attrib_order:
            attrib_order.sudo().unlink()

        wallet_name = 'IZI %s Wallet Scheduler %s' % (str(self.marketplace.capitalize()), str(self.id))
        wallet_order = self.env['ir.cron'].sudo().search([('name', '=', wallet_name)])
        if wallet_order:
            wallet_order.sudo().unlink()

        return super(MarketplaceAccount, self).unlink()

    @api.constrains('marketplace')
    def check_marketplace_installed(self):
        for rec in self:
            module_name = 'izi_%s' % (rec.marketplace)
            check_module_install = self.env['ir.module.module'].sudo().search([
                ('name', '=', module_name),
                ('state', '=', 'installed'),
            ], count=True)
            if not check_module_install:
                raise ValidationError('Module %s not installed.' % (module_name))

    @api.constrains('name')
    def check_marketplace_name(self):
        for rec in self:
            if not rec.team_id:
                rec.team_id = self.env['crm.team'].create({'name': rec.name})

    @api.onchange('create_invoice')
    def onchange_create_invoice(self):
        if self.create_invoice:
            return {'warning': {'title': 'Warning Message',
                                'message': 'If you enable this feauture will be set product in order lines to ordered quantity'}}

    # @api.multi
    def _compute_mp_token(self):
        for mp_account in self:
            if mp_account.mp_token_ids:
                mp_token = mp_account.mp_token_ids.sorted('expired_date', reverse=True)[0]
                mp_token = mp_token.validate_current_token()
                mp_account.mp_token_id = mp_token.id
            else:
                mp_account.mp_token_id = False

    @api.model
    def _get_default_insurance_product_id(self):
        mp_insurance_product_tmpl = self.env.ref('izi_marketplace.product_tmpl_mp_insurance', raise_if_not_found=False)
        if mp_insurance_product_tmpl:
            return mp_insurance_product_tmpl.product_variant_id.id
        return False

    @api.model
    def _get_default_global_discount_product_id(self):
        mp_global_discount_product_tmpl = self.env.ref('izi_marketplace.product_tmpl_mp_global_discount',
                                                       raise_if_not_found=False)
        if mp_global_discount_product_tmpl:
            return mp_global_discount_product_tmpl.product_variant_id.id
        return False

    @api.model
    def _get_default_adjustment_product_id(self):
        mp_adjustment_product_tmpl = self.env.ref('izi_marketplace.product_tmpl_mp_adjustment',
                                                  raise_if_not_found=False)
        if mp_adjustment_product_tmpl:
            return mp_adjustment_product_tmpl.product_variant_id.id
        return False

    @api.model
    def _get_default_services_product_id(self):
        mp_services_product_tmpl = self.env.ref('izi_marketplace.product_tmpl_mp_services',
                                                  raise_if_not_found=False)
        if mp_services_product_tmpl:
            return mp_services_product_tmpl.product_variant_id.id
        return False

    # @api.multi
    def generate_context(self):
        self.ensure_one()
        context = self._context.copy()
        context.update({
            'mp_account_id': self.id,
            'force_update': self.debug_force_update,
            'force_update_raw': self.debug_force_update_raw,
            'store_product_img': self.debug_store_product_img,
            'product_limit': self.debug_product_limit,
            'order_limit': self.debug_order_limit,
            'skip_error': self.debug_skip_error,
            'timezone': self._context.get('tz') or 'UTC',
        })
        return context

    # @api.multi
    def action_reauth(self):
        self.ensure_one()
        token_raw = self.env['mp.token'].search([('mp_account_id', '=', self.id), ('expired_date', '>', datetime.now())])
        if token_raw:
            for token in token_raw:
                expire_date = token.expired_date
                if datetime.now() < fields.Datetime.from_string(expire_date):
                    token.sudo().write({'expired_date': datetime.now(), 'state': 'expired'})

        self.write({'state': 'authenticating'})

    # @api.multi
    def action_authenticate(self):
        self.ensure_one()
        if self.active:
            token_raw = self.env['mp.token'].search([('mp_account_id', '=', self.id), ('expired_date', '>', datetime.now())])
            if not token_raw:
                if hasattr(self, '%s_authenticate' % self.marketplace):
                    return getattr(self, '%s_authenticate' % self.marketplace)()

    # @api.multi
    def action_get_dependencies(self):
        self.ensure_one()
        if hasattr(self, '%s_get_dependencies' % self.marketplace):
            return getattr(self, '%s_get_dependencies' % self.marketplace)()

    # @api.multi
    def action_get_products(self, **kw):
        self.ensure_one()
        if hasattr(self, '%s_get_products' % self.marketplace):
            return getattr(self, '%s_get_products' % self.marketplace)(**kw)

    # @api.multi
    def register_webhooks(self):
        self.ensure_one()
        if hasattr(self, '%s_register_webhooks' % self.marketplace):
            return getattr(self, '%s_register_webhooks' % self.marketplace)()

    # @api.multi
    def unregister_webhooks(self):
        self.ensure_one()
        if hasattr(self, '%s_unregister_webhooks' % self.marketplace):
            return getattr(self, '%s_unregister_webhooks' % self.marketplace)()

    # @api.multi
    def action_map_product(self):
        product_map_obj = self.env['mp.map.product']

        self.ensure_one()

        product_map = product_map_obj.search([
            ('marketplace', '=', self.marketplace),
            ('mp_account_id', '=', self.id),
        ])

        if not product_map.exists():
            product_map = product_map_obj.create({
                'name': 'Product Mapping - %s' % self.name,
                'marketplace': self.marketplace,
                'mp_account_id': self.id,
            })

        action = self.env.ref('izi_marketplace.action_window_mp_map_product').read()[0]
        action.update({
            'res_id': product_map.id,
            'views': [(self.env.ref('izi_marketplace.form_mp_map_product').id, 'form')],
        })
        return action

    def action_view_mp_promotion(self):
        self.ensure_one()
        action = self.env.ref('izi_marketplace.action_window_mp_promotion_per_marketplace').read()[0]
        action.update({
            'domain': [('mp_account_id', '=', self.id)],
            'context': {
                'default_marketplace': self.marketplace,
                'default_mp_account_id': self.id
            }
        })
        return action

    # @api.multi
    def action_view_mp_product(self):
        self.ensure_one()
        action = self.env.ref('izi_marketplace.action_window_mp_product_view_per_marketplace').read()[0]
        action.update({
            'domain': [('mp_account_id', '=', self.id)],
            'context': {
                'default_marketplace': self.marketplace,
                'default_mp_account_id': self.id
            }
        })
        return action

    def action_view_mp_bank_statement(self):
        self.ensure_one()
        action = self.env.ref('izi_marketplace.action_window_mp_bank_statement_view_per_marketplace').read()[0]
        action.update({
            'domain': [('mp_account_id', '=', self.id)],
            'context': {
                'default_marketplace': self.marketplace,
                'default_mp_account_id': self.id,
                'default_journal_id': self.wallet_journal_id.id
            }
        })
        return action

    def action_view_mp_orders(self):
        self.ensure_one()
        action = self.env.ref('izi_marketplace.action_window_mp_order_per_marketplace').read()[0]
        action.update({
            'domain': [('mp_account_id', '=', self.id)],
            'context': {
                'default_marketplace': self.marketplace,
                'default_mp_account_id': self.id,
                'default_company_id': self.company_id.id,
                'create': False
            }
        })
        return action

    def action_view_mp_return(self):
        self.ensure_one()
        action = self.env.ref('izi_marketplace.action_window_mp_return_per_marketplace').read()[0]
        action.update({
            'domain': [('mp_account_id', '=', self.id)],
            'context': {
                'default_marketplace': self.marketplace,
                'default_mp_account_id': self.id,
                'default_company_id': self.company_id.id
            }
        })
        return action

    def action_view_mp_log_error(self):
        self.ensure_one()
        action = self.env.ref('izi_marketplace.action_window_mp_log_error').read()[0]
        action.update({
            'domain': [('mp_account_id', '=', self.id)]
        })
        return action

    def action_set_product(self, **kw):
        self.ensure_one()
        if hasattr(self, '%s_set_product' % self.marketplace):
            return getattr(self, '%s_set_product' % self.marketplace)(**kw)

    def process_webhook_orders(self, **kwargs):
        rec = self
        if kwargs.get('id', False):
            rec = self.browse(kwargs.get('id'))
        rec.ensure_one()
        if hasattr(rec, '%s_process_webhook_orders' % rec.marketplace):
            return getattr(rec, '%s_process_webhook_orders' % rec.marketplace)(**kwargs)

    def process_category_brand_attribute_manually(self, **kwargs):
        rec = self
        if kwargs.get('id', False):
            rec = self.browse(kwargs.get('id'))
        rec.ensure_one()
        if hasattr(rec, '%s_category_brand_attribute_manually' % rec.marketplace):
            return getattr(rec, '%s_category_brand_attribute_manually' % rec.marketplace)(**kwargs)

    def process_update_shopee_category_mapped_false(self, **kwargs):
        rec = self
        if kwargs.get('id', False):
            rec = self.browse(kwargs.get('id'))
        rec.ensure_one()
        self.env.cr.execute(
            'UPDATE mp_shopee_category SET attribute_mapped=false, brand_mapped=false'
        )

    def get_return(self, **kwargs):
        rec = self
        if kwargs.get('id', False):
            rec = self.browse(kwargs.get('id'))
        rec.ensure_one()
        if hasattr(rec, '%s_get_return' % rec.marketplace):
            return getattr(rec, '%s_get_return' % rec.marketplace)(**kwargs)

    def get_orders_wallet(self, **kwargs):
        rec = self
        if kwargs.get('id', False):
            rec = self.browse(kwargs.get('id'))
        rec.ensure_one()
        if hasattr(rec, '%s_get_orders_wallet' % rec.marketplace):
            return getattr(rec, '%s_get_orders_wallet' % rec.marketplace)(**kwargs)

    def sync_promotion(self, **kw):
        promotion_obj = self.env['mp.promotion.program']
        # search all promotion with state wait/run
        records = promotion_obj.search([('state', 'in', ['wait', 'run'])])
        for record in records:
            now = fields.Datetime.now()
            # manual set state refer to time now.
            if record.date_start < now and record.date_end > now:
                if record.state == 'wait':
                    record.state = 'run'
            elif record.date_start < now and record.date_end < now:
                if record.state == 'run':
                    record.state = 'stop'

    def auto_ship_orders(self, **kwargs):
        rec = self
        if kwargs.get('id', False):
            rec = self.browse(kwargs.get('id'))
        rec.ensure_one()
        if rec.auto_process_orders:
            if hasattr(rec, '%s_auto_ship_orders' % rec.marketplace):
                return getattr(rec, '%s_auto_ship_orders' % rec.marketplace)(**kwargs)

    def checking_cutoff_time(self, now=None, tz_now=None):
        if now and tz_now:
            # check configurarion order time
            order_time_config = self.env['mp.order.time'].sudo().search(
                [('active', '=', True), ('mp_account_ids', 'in', self.id)], limit=1)
            list_of_days = {}
            for order_day in order_time_config.line_ids:
                list_of_days[order_day['day']] = '{0:02.0f}:{1:02.0f}'.format(*divmod(order_day.cutoff_time * 60, 60))

            day = tz_now.strftime('%A').lower()
            float_now = tz_now.hour+now.minute/60.0
            time_now = '{0:02.0f}:{1:02.0f}'.format(*divmod(float_now * 60, 60))

            # checking today is day off or not
            for order_day_off in order_time_config.day_off_ids:
                if now > order_day_off.start_date and now < order_day_off.end_date:
                    return True

            # checking the time today is cutoff or not
            if day in list_of_days:
                if time_now > list_of_days[day]:
                    return True

        return False

    def action_open_seller_center(self):
        self.ensure_one()
        url_seller = self._get_url_seller_center(self.marketplace)
        return {
            'type': 'ir.actions.act_url',
            'url': url_seller,
            'target': 'new',
        }

    def _get_url_seller_center(self, marketplace=None):
        if marketplace is None or not marketplace:
            raise ValidationError('Marketplace not found.')
        country_code = self.env.company.country_id.code
        if not country_code:
            raise ValidationError('Country Code was not found. Please set the country code in your company settings')
        if marketplace == 'shopee':
            url_seller = HOSTS_SELLER['sp_%s' % country_code.lower()]
        elif marketplace == 'tokopedia':
            url_seller = HOSTS_SELLER['tp']
        elif marketplace == 'lazada':
            url_seller = HOSTS_SELLER['lz_%s' % country_code.lower()]
        elif marketplace == 'tiktok':
            url_seller = HOSTS_SELLER['tts_%s' % country_code.lower()]
        return url_seller