# -*- coding: utf-8 -*-

import logging
import re
import requests
import json
import base64
import hashlib
from lxml import etree
from hashlib import sha1
from werkzeug.urls import url_encode

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PosConfig(models.Model):
    _inherit = "pos.config"

    @api.model
    def _default_pos_receipt_template_id(self):
        pos_receipt_template_id = self.env.company.pos_def_receipt_template_id.id or False
        return pos_receipt_template_id


    def _get_group_pos_manager(self):
        return self.env.ref('equip3_pos_masterdata.group_pos_manager')

    def _get_group_pos_user(self):
        return self.env.ref('equip3_pos_masterdata.group_pos_user')

    # Turn of settings currency on pos
    # def _get_currency_id(self):
    #     currency_id = self.env.company.currency_id.id
    #     if self.company_id:
    #         currency_id = self.company_id.currency_id.id
    #     if self.journal_id:
    #         currency_id = self.journal_id.currency_id.id
    #     return currency_id


    group_pos_manager_id = fields.Many2one(default=_get_group_pos_manager, store=False)
    group_pos_user_id = fields.Many2one(default=_get_group_pos_user, store=False)
    pos_receipt_template_id = fields.Many2one('pos.receipt.template','New POS Receipt Template',default=_default_pos_receipt_template_id)
    order_loading_options = fields.Selection([("current_session","Load Orders Of Current Session"), ("all_orders","Load All Past Orders"), ("n_days","Load Orders Of Last 'n' Days")], default='current_session', string="Loading Options")
    number_of_days = fields.Integer(string='Number Of Past Days',default=10)
    weight_scale_barcode_format_id = fields.Many2one('weight.scale.barcode.format','Weight Scale Barcode Format')
    # Turn of settings currency on pos
    # currency_id = fields.Many2one('res.currency', compute=False, string="Currency",default=_get_currency_id)

    # Turn of settings currency on pos
    # @api.depends('use_pricelist', 'available_pricelist_ids')
    # def _compute_allowed_pricelist_ids(self):
    #     for config in self:
    #         if config.use_pricelist:
    #             config.allowed_pricelist_ids = config.available_pricelist_ids.ids
    #         else:
    #             config.allowed_pricelist_ids = self.env['product.pricelist'].search([('currency_id','=',config.currency_id.id or False)]).ids


    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=False, submenu=False):
        if view_type in ['form','kanban']:
            check_pos_configs = self.sudo().search([('product_configurator','=',True)])
            if check_pos_configs:
                check_pos_configs.write({'product_configurator':False})
        res = super(PosConfig, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        user_pos_not_create_edit =  self.env.user.has_group('equip3_pos_masterdata.group_pos_cashier') or self.env.user.has_group('equip3_pos_masterdata.group_pos_waiter') or self.env.user.has_group('equip3_pos_masterdata.group_pos_cooker')
        user_pos_have_create_edit =  self.env.user.has_group('equip3_pos_masterdata.group_pos_staff') or self.env.user.has_group('equip3_pos_masterdata.group_pos_supervisor') or self.env.user.has_group('equip3_pos_masterdata.group_pos_manager')
        if user_pos_not_create_edit and not user_pos_have_create_edit:
            root = etree.fromstring(res['arch'])
            root.set('edit', 'false')
            res['arch'] = etree.tostring(root)
            
        return res

    @api.constrains('number_of_days')
    def number_of_days_validation(self):
        if self.order_loading_options == 'n_days':
            if not self.number_of_days or self.number_of_days < 0:
                raise ValidationError("Please provide a valid value for the field 'Number Of Past Days'!!!")
        return True

        
    def updateCache(self):
        return self.env['pos.call.log'].refresh_logs()

    def init(self):
        self.env.cr.execute(
            """DELETE FROM ir_model_data WHERE model IN ('pos.bus', 'pos.bus.log', 'pos.tracking.client')""");

    def _get_product_field_char(self):
        product_fields = self.env['ir.model.fields'].sudo().search(
            [('model', '=', 'product.product'),
             ('ttype', '=', 'char')])
        return [
            (field.name, field.field_description)
            for field in sorted(product_fields, key=lambda f: f.field_description)
        ]

    def _get_customer_field_char(self):
        product_fields = self.env['ir.model.fields'].search(
            [('model', '=', 'res.partner'),
             ('ttype', '=', 'char')])
        return [
            (field.name, field.field_description)
            for field in sorted(product_fields, key=lambda f: f.field_description)
        ]

    def _get_picking_field_char(self):
        picking_fields = self.env['ir.model.fields'].search(
            [('model', '=', 'stock.picking'),
             ('ttype', '=', 'char')])
        return [
            (field.name, field.field_description)
            for field in sorted(picking_fields, key=lambda f: f.field_description)
        ]

    def _get_invoice_field_char(self):
        invoice_fields = self.env['ir.model.fields'].search(
            [('model', '=', 'account.move'),
             ('ttype', '=', 'char')])
        return [
            (field.name, field.field_description)
            for field in sorted(invoice_fields, key=lambda f: f.field_description)
        ]

    # Turn of settings currency on pos
    # @api.onchange('currency_id')
    # def onchange_currency_id(self):
    #     for data in self:
    #         data.available_pricelist_ids = False
    #         data.pricelist_id = False


    @api.depends('session_ids')
    def _compute_assigned_user_ids(self):
        for record in self:
            user_ids = record.session_ids.mapped('user_id.id') or []
            user_ids = list(set(user_ids))
            record.assigned_user_ids = [(6, 0, user_ids)]
    bnk_cash_control = fields.Boolean("Cash Control")

    
    restaurant_order = fields.Boolean('Restaurant Order')
    restaurant_order_login = fields.Char('Restaurant Order Login')
    restaurant_order_password = fields.Char('Restaurant Order Password') 
    

    pos_config_cashbox_lines_ids = fields.One2many('account.cashbox.line', 'pos_session_id', string='Config Cashbox Lines')
    pos_config_cashbox_clsosing_line_ids = fields.One2many('account.cashbox.line', 'pos_session_id', string='Config Cashbox Closing Lines')
    cashbox_lines_ids = fields.One2many('account.cashbox.line', 'pos_config_id', string='Cashbox Lines')

    # Added new field for avoiding override value via session
    pos_cashbox_lines_ids = fields.One2many('pos.account.cashbox.line', 'pos_config_id', string='POS Cashbox Lines')
    
    printer_id = fields.Many2one(
        'pos.epson',
        'Printer Network',
        help='If you choice printer here \n'
             'Receipt Invoice willl printing directly to this printer IP'
    )

    load_coupon_program = fields.Boolean(
        'Load Coupon Program',
        default=0,
    )
    coupon_program_apply_type = fields.Selection([
        ('manual', 'Manual Select'),
        ('auto', 'Automatic Apply when Pay')
    ], default='manual',
        help='If you choose [Manual Select], cashier required click to Coupons Programs button and choice Coupon Programs need applied \n'
             'If you choose [Automatic Apply when Pay], when cashier click Paid button, all Coupon Programs automatic add to Order '
    )
    coupon_program_ids = fields.Many2many(
        'coupon.program',
        'pos_config_coupon_program_rel',
        'pos_config_id',
        'coupon_id',
        domain=[('program_type', '=', 'promotion_program'), ('promo_applicability', '=', 'on_current_order')],
        string='Coupon Program')
    coupon_giftcard_ids = fields.Many2many(
        'coupon.program',
        'pos_config_coupon_giftcard_rel',
        'pos_config_id',
        'coupon_giftcard_id',
        domain=[('program_type', '=', 'coupon_program'), ('is_gift_card', '=', True)],
        string='Gift Card Program Template'
    )
    coupon_giftcard_create = fields.Boolean(
        'Allow POS Create Coupon',
        default=0,
    )
    user_id = fields.Many2one('res.users', 'Assigned to')
    allow_change_pos_profile = fields.Boolean('Allow Change POS Profile')
    allow_numpad = fields.Boolean('Allow Use Numpad', default=1)
    allow_discount = fields.Boolean('Allow Change Discount', default=1)
    allow_qty = fields.Boolean('Allow Change Quantity', default=1)
    allow_price = fields.Boolean('Allow Change Price', default=1)
    allow_remove_line = fields.Boolean('Allow Remove Line', default=1)
    allow_minus = fields.Boolean('Allow Minus (+/-)', default=1)
    allow_payment = fields.Boolean('Allow Payment', default=1)
    allow_customer = fields.Boolean('Allow set Customer', default=1)
    allow_add_order = fields.Boolean('Allow Add Order', default=1)
    allow_remove_order = fields.Boolean('Allow Remove Order', default=1)
    allow_add_product = fields.Boolean('Allow Add Product', default=1)
    allow_payment_zero = fields.Boolean(
        'Allow Payment Zero',
        default=1,
        help='If active, cashier can made order total amount smaller than or equal 0')
    allow_closing_session = fields.Boolean(
        default=1,
        string='Allow closing Session',
        help='If POS Users have not inside group Point Of Sale Manager \n'
             'And this field is un-checked \n'
             'POS Users will could not closing session'
    )
    allow_closing_all_sessions_online = fields.Boolean(
        default=0,
        string='Allow Closing All Sessions Online',
        help='If checked, this POS can closing all POS Sessions \n'
             'Of another POS Users direct on POS Screen'
    )
    allow_duplicate_session = fields.Boolean(
        'Allow Duplicate Session',
        help='If you checked (active) this checkbox \n'
             'Will allow user duplicate POS Screen Tab \n'
             'And opened POS Session at another Browse Device (Chrome, Firefox ...) \n'
             'If you uncheck, only allow 1 POS Session opened in 1 Current Time'
    )
    allow_otp = fields.Boolean(
        'Allow OTP',
        help='If you checked (active) this checkbox \n'
        'User need to verify their self using OTP \n'
        'User need to verify their self using OTP \n'
    )
    twilio_acc_sid = fields.Char('Account SID')
    twilio_auth_token = fields.Char('Authentication Token')
    pos_otp_reset_time = fields.Float('Reset Time')
    pos_otp_msg = fields.Text('Message')

  
    tax_affect_compliment = fields.Boolean(
        'Tax Affect Compliment',
        help='Tax that affect Items in Cart\n'
             'When the Cashier write the compliment, affect of the order tax will be listed')

    sale_order = fields.Boolean('Create Sale Order', default=0)
    sale_order_auto_confirm = fields.Boolean('Auto Confirm', default=0)
    sale_order_auto_invoice = fields.Boolean('Auto Paid', default=0)
    sale_order_auto_delivery = fields.Boolean('Auto Delivery', default=0)
    sale_order_required_signature = fields.Boolean(
        'SO Required Signature',
        help='Allow print receipt when create quotation/order')

    pos_orders_management = fields.Boolean(
        'POS Order Management',
        default=1)
    pos_order_tracking = fields.Boolean(
        'Tracking Order',
        help='Tracking Action of POS User on Order (example: remove/add order, change quantity/discount ....',
        default=0
    )
    pos_order_tracking_remove_when_closing_session = fields.Boolean(
        'Remove all Tracking Order Logs when Closing Session',
        default=0
    )
    shipping_order = fields.Boolean(
        'Shipping Order',
        default=1,
        help='Create Customer Order Delivery (COD) \n'
             'Allow cashiers create shipping address and save to Order, do partial payment Order \n'
             'When Delivery Man success shipping Order, Cashier confirm Order to Paid \n'
             'If you active this future, please active Partial Payment too\n'
             'For cashier add one part payment of Customer'
    )
    pos_orders_load_orders_another_pos = fields.Boolean(
        'Allow Loading Orders of another POS',
        default=1
    )
    pos_orders_filter_by_branch = fields.Boolean(
        'POS Order Filter Branch', default=0,
        help='If you checked it, \n'
             'pos session could not see orders of another branch')
    pos_order_period_return_days = fields.Float(
        'Return Period Days',
        help='This is period days allow customer \n'
             'can return Order or one part of Order',
        default=30)
    pos_allowed_return_category_ids = fields.Many2many(
        'pos.category',
        'pos_allowed_return_category_ids',
        'pos_config_id',
        'pos_category_id',
        string='Returnable Categories',
        )
    required_reason_return = fields.Boolean(
        'Required Reason Return',
        help='Required Cashiers input Reason Return each line if Order is return'
    )
    display_return_days_receipt = fields.Boolean('Display Return Days on Receipt', default=0)
    display_onhand = fields.Boolean(
        'Show Stock on Hand each Product', default=1,
        help='Display quantity on hand all products on pos screen')
    allow_order_out_of_stock = fields.Boolean(
        'Allow Order when Product Out Of Stock',
        help='If uncheck, any product out of stock will blocked sale',
        default=1)
    allow_pos_categories_out_of_stock = fields.Many2many(
        'pos.category',
        'allow_pos_categories_out_of_stock',
        'pos_config_id',
        'pos_category_id',
        string='Allow some POS Categories can Sale when Out of Stock',
        help='Normally if [Allow Order when Product Out Of Stock] uncheck, if Products out of stock, POS will blocked sale. But if you set Categories here, it mean if Products of Categories added here will allow Sale when Out of Stock'
    )
    hide_product_when_outof_stock = fields.Boolean(
        'Hide Product Out Of Stock',
        default=0)
    print_voucher = fields.Boolean(
        'Create Voucher',
        help='Allow cashiers create Voucher Manual on POS',
        default=0)
    voucher_sequence_id = fields.Many2one('ir.sequence', 'Voucher Sequence')
    expired_days_voucher = fields.Integer(
        'Expired days of Voucher',
        default=30,
        help='Total days keep voucher can use, \n'
             'if out of period days from create date, voucher will expired')
    sync_multi_session = fields.Boolean('Sync between Sessions', default=True)
    sync_play_sound = fields.Boolean('Sync Play Sound', default=0,
                                     help='When have new sync notification, browse will play sound')
    sync_multi_session_with = fields.Char('Sync with', compute='_get_sync_with_sessions')
    sync_multi_session_manual_stop = fields.Boolean('Sync Can manual stop by Users')
    sync_multi_session_alert_remove_order = fields.Boolean('Popup Alert when another Sessions Remove Orders')
    sync_multi_session_offline = fields.Boolean(
        'Sync Between Session with Local Network',
        default=0,
        help='If not checked, normal sync between Sessions required Server Online \n'
             'If checked, we dont care offline or not \n'
             'All sync datas will sync direct POS'
    )

    sync_to_pos_config_ids = fields.Many2many(
        'pos.config',
        'sync_session_rel',
        'from_id',
        'to_id',
        string='Sync with Point Of Sale',
        domain="['|', ('pos_branch_id', '=', pos_branch_id), ('pos_branch_id', '=', None)]",
        help='Select POS Configs need sync with this POS Config \n' \
             'Any event change orders from this Session of this POS will sync to your selected POS Config Sessions \n'
    )
    # sync_multi_session_offline_iot_ids = fields.Many2many(
    #     'pos.iot', 'pos_config_iot_rel', 'pos_config_id',
    #     'iot_box_id',
    #     string='IoT Boxes for Sync',
    #     help='Setup 1 pos/iot box \n'
    #          'And use it for Sync Point inside Your Shop/Restaurant Local Network \n'
    #          'This function only for our partnership \n'
    #          'If you need it, please go to our website: http://posodoo.com \n'
    #          'And looking to Professional Plan')
    sync_tracking_activities_user = fields.Boolean(
        'Tracking Activities User',
        default=1,
        help='Tracking all activities of POS User \n'
             'Example: add new product, remove line ....'
    )
    display_person_add_line = fields.Boolean(
        'Display information Lines',
        default=0,
        help="When you checked, on pos order lines screen, \n"
             "will display information person created order \n"
             "(lines) Eg: create date, updated date ..")

    internal_transfer = fields.Boolean(
        'Allow Internal Transfer',
        default=0,
        help='Go Inventory and active multi warehouse and location')
    internal_transfer_picking_type_id = fields.Many2one(
        'stock.picking.type',
        'Internal Transfer Picking Type'
    )
    discount = fields.Boolean('Active Global Discounts', default=0)
    discount_ids = fields.Many2many(
        'pos.global.discount',
        'config_discount_rel',
        'config_id',
        'discount_id',
        string='Global Discount Items'
    )
    delay = fields.Integer('Delay time', default=3000)

    discount_limit = fields.Boolean('Discount Limit', default=0)
    discount_limit_type = fields.Selection(
        selection=[('percentage','Percentage'), ('fixed','Fixed')], 
        default='percentage',
        string='Discount Limit Type')
    discount_limit_amount = fields.Float(
        'Discount Limit Amount',
        help='This is maximum disc cashier can set to each line',
        default=0)
    return_products = fields.Boolean('Return Products or Orders',
                                     help='Allow cashier return products or orders',
                                     default=0)
    return_method_id = fields.Many2one(
        'pos.payment.method',
        string='Return Method'
    )
    return_covert_to_coupon = fields.Boolean(
        'Return via Coupon',
        help='Normally you return Orders/Products of Customer via cash refund back \n'
             'This feature help you refund via Coupon Card \n'
             'And Customer save it and use Coupon in next Order'
    )
    return_coupon_program_id = fields.Many2one(
        'coupon.program',
        domain=[('program_type', '=', 'coupon_program'), ('is_gift_card', '=', True)],
        string='Refund via Coupon Program'
    )
    return_duplicate = fields.Boolean(
        'Allow duplicate Return Order',
        help='If checked, one Order can return many times'
    )
    return_viva_scan_barcode = fields.Boolean(
        'Scan Barcode auto Return Order',
        default=1,
    )

    validate_payment = fields.Boolean('Validate Payment')
    validate_remove_order = fields.Boolean('Validate Remove Order')
    validate_new_order = fields.Boolean('Validate New Order')
    validate_change_minus = fields.Boolean('Validate Pressed +/-')
    validate_quantity_change = fields.Boolean('Validate Quantity Change')
    validate_quantity_change_type = fields.Selection([
        ('increase', 'Increase'),
        ('decrease', 'Decrease'),
        ('both', 'Both')
    ], string='Type of Validation Qty change', default='decrease')
    validate_price_change = fields.Boolean('Validate Price Change')
    validate_price_change_type = fields.Selection([
        ('increase', 'Increase'),
        ('decrease', 'Decrease'),
        ('both', 'Both')
    ], string='Type of Validation Price change', default='decrease')
    validate_discount_change = fields.Boolean('Validate Discount Change')
    validate_discount_change_type = fields.Selection([
        ('increase', 'Increase'),
        ('decrease', 'Decrease'),
        ('both', 'Both')
    ], string='Type of Validation Discount change', default='increase')
    validate_remove_line = fields.Boolean('Validate Remove Line')
    validate_return = fields.Boolean('Validate Return')
    validate_coupon = fields.Boolean('Validate Coupon (Gift Cards)')

    product_operation = fields.Boolean(
        'Product Operation', default=0,
        help='Allow cashiers add pos categories and products on pos screen')
    note_order = fields.Boolean('Note Order', default=0)
    signature_order = fields.Boolean('Signature Order', default=0)

    booking_orders = fields.Boolean(
        'Booking Orders',
        default=0,
        help='Orders may be come from many sources locations\n'
             'Example: Web E-Commerce, Call center, or phone call order\n'
             'And your Cashiers will made Booking Orders and save it\n'
             'Your Shipper or customer come shop will delivery Orders')
    load_booked_orders_type = fields.Selection([
        ('last_7_days', 'Last 7 Days'),
        ('last_1_month', 'Last 1 Month'),
        ('last_1_year', 'Last 1 Year (365 days)'),
        ('load_all', 'Load All'),
    ],
        default='last_7_days',
        string='Period days loading Booked Orders'
    )
    booking_orders_load_orders_another_pos = fields.Boolean(
        'Allow Load Order of another POS',
        default=1
    )
    booking_orders_alert = fields.Boolean(
        'Alert Order Coming', default=0,
        help='When have any Booking Order come from another Source Location to POS\n'
             'POS will Alert one popup inform your cashier have new Order coming')
    booking_allow_confirm_sale = fields.Boolean(
        'Delivery Booked Orders', default=0,
        help='Allow Cashier can Confirm Booked Orders and create Delivery Order')
    booking_orders_display_shipping_receipt = fields.Boolean('Shipping Address Receipt', default=0)
    display_tax_orderline = fields.Boolean('Display Taxes Order Line', default=0)
    display_tax_receipt = fields.Boolean('Display Taxes Receipt', default=0)
    display_image_orderline = fields.Boolean('Display Image on Order Lines', default=0)
    display_amount_discount = fields.Boolean('Display Amount Discount', default=1)
    display_barcode = fields.Boolean('Display Barcode', default=1)
    quickly_look_up_product = fields.Boolean(
        'Automatic Lookup Product',
        default=1,
        help='When you typing correct Barcode or Internal Reference or PLU Number on search box of POS Product Screen \n'
             'POS Searchbox automatic lookup product have Internal Ref or PLU number or Barcode or Name \n'
             'The same with your type, and automatic add Product to Cart'
    )
    management_invoice = fields.Boolean('Display Invoices Screen', default=0)
    load_invoices_type = fields.Selection([
        ('today', 'Today'),
        ('last_3_days', 'Last 3 Days'),
        ('last_7_days', 'Last 7 Days'),
        ('last_1_month', 'Last 1 Month'),
        ('last_1_year', 'Last 1 Year (365 days)'),
        ('load_all', 'Load All'),
    ],
        default='last_7_days',
        string='Period days loading Invoices'
    )
    invoice_offline = fields.Boolean(
        'Invoice Offline Mode',
        help='Any Orders come from POS Session always create invoice \n'
             'Invoice will create few second after POS Orders created \n'
             'This future not print invoice number on POS Receipt \n'
             'Only create invoice each order and auto post invoice when POS Order submitted to backend \n'
             'Please set Customer Default or all orders on POS required set Customer before do payment'
    )

    wallet = fields.Boolean(
        'Wallet Card',
        help='Keeping all change money back to Customer Wallet Card\n'
             'Example: customer bought products with total amount is 9.5 USD\n'
             'Customer give your Cashier 10 USD, \n'
             'Default your cashier will return back change money 0.5 USD\n'
             'But Customer no want keep it, \n'
             'They need change money including to Wallet Card for next order\n'
             'Next Time customer come back, \n'
             'When your cashier choice client have Wallet Credit Amount bigger than 0\n'
             'Customer will have one more payment method via Wallet Credit')
    payment_journal_ids = fields.Many2many(
        'account.journal',
        'pos_config_invoice_journal_rel',
        'config_id',
        'journal_id',
        'Save Invoice Journal with this Journal',
        domain=[('type', '=', 'sale')],
        help="Default POS save Invoice Journal from only one Invoicing Journal of POS Config\n"
             "This future allow you add many Journals here\n"
             "And when your cashier choice Journal on POS\n"
             "Journal of Invoice will the same Journal selected by cashier")
    send_invoice_email = fields.Boolean(
        'Send email invoice',
        help='Help cashier send invoice to email of customer',
        default=0)
    customer_default_id = fields.Many2one(
        'res.partner',
        'Customer Default',
        help='This is customer automatic set to Order, \n'
             'When cashier create new order')
    auto_invoice = fields.Boolean(
        'Auto Order to Invoice',
        help='Auto check to button Invoice on POS Payment Screen',
        default=0)
    auto_invoice_with_customer_default = fields.Boolean(
        'Auto to Invoice if Customer default',
        help='Automatic Order to invoice if Customer Default',
        default=0
    )
    invoice_without_download = fields.Boolean(
        'Order to Invoice without Download',
        help='When cashier choose Invoice on Payment Screen \n'
             'POS will automatic made invoice for Order \n'
             'And blocked download Invoice Receipt Pdf'
    )
    fiscal_position_auto_detect = fields.Boolean(
        'Fiscal position auto detect',
        default=0
    )
    display_sale_price_within_tax = fields.Boolean(
        'Display Sale Price Within Taxes',
        default=1
    )
    display_cost_price = fields.Boolean('Display Cost Price', default=0)
    display_product_ref = fields.Boolean('Display Product Ref', default=0)
    display_margin = fields.Boolean('Display Margin', default=0)
    display_product_detail = fields.Boolean(
        'Display Product Detail',
        help='Display Product Detail and Purchased Histories of Customer',
        default=1
    )
    allow_remove_product = fields.Boolean(
        'Allow Remove Products',
        help='Allow cashier set Available in POS each Product to False'
    )
    allow_edit_product = fields.Boolean(
        'Allow Edit Product',
        help='Allow cashier edit Product (ex: Name, Category, Price ....)ừa'
    )
    display_product_name_without_product_code = fields.Boolean('Display Product Name without Product Code')
    product_virtual_keyboard = fields.Boolean('Virtual Keyboard')
    hide_product_image = fields.Boolean('Hide Product Image', default=0)
    multi_location = fields.Boolean('Update Stock each Location', default=0)
    update_stock_onhand = fields.Boolean('Allow Update Stock On Hand', default=0)
    multi_stock_operation_type = fields.Boolean('Multi Stock Operation Type')
    multi_stock_operation_type_ids = fields.Many2many(
        'stock.picking.type',
        'config_stock_picking_type_rel',
        'config_id',
        'stock_picking_type_id',
        string='Operation Types',
        domain="[('warehouse_id.company_id', '=', company_id)]"
    )
    product_view = fields.Selection([
        ('box', 'Box View'),
        ('list', 'List View'),
    ], default='box', string='Product Screen View Type', required=1)
    update_tax = fields.Boolean(
        'Modify Taxes of Lines',
        default=0,
        help='Allow Cashiers can change Taxes of Lines')
    update_tax_ids = fields.Many2many(
        'account.tax',
        'pos_config_tax_rel',
        'config_id',
        'tax_id', string='List Taxes')
    check_duplicate_email = fields.Boolean('Check duplicate email', default=0)
    check_duplicate_phone = fields.Boolean('Check duplicate phone', default=0)
    check_required_phone = fields.Boolean('Required Phone', default=0)
    check_required_email = fields.Boolean('Required Email', default=0)
    check_required_vat = fields.Boolean('Required Tax', default=0)

    add_sale_person = fields.Boolean('Add Sale Person', default=0)
    default_seller_id = fields.Many2one(
        'res.users',
        'Default Seller',
        help='This is Seller Automatic assigned to new Orders and new Order Lines'
    )
    seller_ids = fields.Many2many(
        'res.users',
        'pos_config_sellers_rel',
        'config_id',
        'user_id',
        string='Sellers',
        help='This is list sellers use for choice and add to Order or Order Line')
    force_seller = fields.Boolean(
        'Force Seller',
        help='When Your POS session select/change another Seller \n'
             'POS auto assigned New Seller to each Line of Order Cart',
        default=0)

    backup_orders = fields.Text('Backup Orders', readonly=1)
    backup_orders_automatic = fields.Boolean(
        'Automatic BackUp Orders',
        help='Schedule 5 seconds, POS Session automatic backup Orders to BackEnd \n'
             'If POS Sessions Screen crashed, Computer PC Crashed or Browse Crashed ... could not open POS back \n'
             'Them can change to another PC, Devices and Open POS Session back \n'
             'Last Orders not Paid will automatic restore \n'
             'Nothing Unpaid Orders lost on POS Session \n'
             'Only Case will lost UnPaid Orders: POS Users turnoff Internet and them Remove Cache of Browse (**)\n'
             'With (**), we have not solution for covert It. Required Input Orders Unpaid Manual back'
    )
    save_orders_removed = fields.Boolean(
        'Save Orders Removed',
        default=1,
        help='If you active this feature \n'
             'Any orders remove buy cashier will save to backend \n'
             'Allow you monitor who, when cashier removed orders \n'
             'Allow cashier restore back order.'
    )
    management_session = fields.Boolean(
        'Manual Cash Control',
        default=0,
        help='Allow pos users can take money in/out session\n'
             'If you active this future please active Cash Control of POS too'
    )
    default_set_cash_open = fields.Boolean('Automatic Set Cash Open')
    default_set_cash_amount = fields.Float('Default Cash Open Amount')
    default_set_cash_notes = fields.Text('Default Cash Open Notes', default='Automatic Set Cash Open Notes')
    cash_inout_reason_ids = fields.Many2many(
        'product.product',
        'pos_config_cash_inout_product_rel',
        'config_id',
        'product_id',
        string='Cash In/Out Reason')
    cash_inout_reason_ids = fields.Text('Cash In/Out Reason')
    barcode_receipt = fields.Boolean('Display Barcode (Ean13)', default=0)
    qrcode_receipt = fields.Boolean(
        'QrCode Link',
    )
    qrcode_ids = fields.One2many(
        'pos.qrcode',
        'config_id',
        string='Fields Display for Qrcode'
    )
    receipt_template = fields.Selection([
        ('arabic', 'Arabic Receipt'),
        ('odoo_original', 'Original POS Receipt Template'),
        ('retail', 'POS Retail Receipt Template (included custom)'),
    ], default='retail', string='Default POS Receipt Template', required=1)
    hide_mobile = fields.Boolean("Hide Client's Mobile", default=1)
    hide_phone = fields.Boolean("Hide Client's Phone", default=1)
    hide_email = fields.Boolean("Hide Client's Email", default=1)
    update_client = fields.Boolean(
        'Allow Update Clients',
        default=1,
        help='Uncheck if you dont want cashier change customer information on pos')
    add_client = fields.Boolean(
        'Allow Add Client',
        help='Allow POS Session can create new Client')
    archive_client = fields.Boolean(
        'Archive Client',
        default=0,
        help='Remove client out of POS, Customer set active is False \n'
             'Still saved at inside your database but not display in POS Clients Screen'
    )
    remove_client = fields.Boolean('Allow Remove Clients',
                                   help='Uncheck if you dont want cashier remove customers on pos')
    report_signature = fields.Boolean(string="Report Signature", default=0)

    report_product_summary = fields.Boolean(string="Report Product Summary", default=0)
    report_product_summary_auto_check_product = fields.Boolean('Auto Checked to Product Summary')
    report_product_summary_auto_check_category = fields.Boolean('Auto Checked to Product Category Summary')
    report_product_summary_auto_check_location = fields.Boolean('Auto Checked to Product Location Summary')
    report_product_summary_auto_check_payment = fields.Boolean('Auto Checked to Product Payment Summary')

    report_order_summary = fields.Boolean(string='Report Order Summary', default=0)
    report_order_summary_auto_check_order = fields.Boolean('Auto Checked to Order Summary')
    report_order_summary_auto_check_category = fields.Boolean('Auto Checked to Order Category Summary')
    report_order_summary_auto_check_payment = fields.Boolean('Auto Checked to Order Payment Summary')
    report_order_summary_default_state = fields.Selection([
        ('new', 'New'),
        ('paid', 'Paid'),
        ('posted', 'Posted'),
        ('invoiced', 'Invoiced'),
        ('all', 'All')
    ], string='Report with state', default='all')

    report_payment_summary = fields.Boolean(string="Report Payment Summary", default=0)
    report_sale_summary = fields.Boolean('Report Sale Summary (Z-Report)')
    report_sale_summary_show_profit = fields.Boolean('Report Sale Summary show Gross/Profit')

    default_product_sort_by = fields.Selection([
        ('a_z', 'Sort Name A to Z'),
        ('z_a', 'Sort Name Z to A'),
        ('low_price', 'Sort from Low to High Sale Price'),
        ('high_price', 'Sort from High to Low Sale Price'),
        ('pos_sequence', 'Product POS Sequence')
    ], string='Default Sort By', default='a_z')
    hide_order_screen = fields.Boolean(
        'Hide Order Screen',
        help='Hide Order Screen (Set KOT)',
        default=False)
    add_customer_before_products_already_in_shopping_cart = fields.Boolean(
        'Required choice Client before Add to Cart',
        help='Add customer before products \n'
             'already in shopping cart',
        default=0)
    allow_cashier_select_pricelist = fields.Boolean(
        'Allow Cashier select Pricelist',
        help='If uncheck, pricelist only work when select customer.\n'
             ' Cashiers could not manual choose pricelist',
        default=1)
    sale_with_package = fields.Boolean(
        'Sale with Package')
    allow_set_price_smaller_min_price = fields.Boolean(
        'Allow Cashier set Price smaller than Sale Price of Product',
        default=1)
    create_lots = fields.Boolean('Allow Create Lots/Serial', help='Allow cashier create Lots/Serials on pos')
    fullfill_lots_type = fields.Selection([('auto','Auto'), ('manual','Manual')], string='Fullfill Lot', default='manual')
    fullfill_lots = fields.Boolean('Auto fullfill Lot', default=1)
 
    stock_location_ids = fields.Many2many(
        'stock.location', string='Stock Locations',
        help='Stock Locations for cashier select checking stock on hand \n'
             'and made picking source location from location selected',
        domain=[('usage', '=', 'internal')])
    validate_by_manager = fields.Boolean('Validate by Managers')
    discount_unlock_by_manager = fields.Boolean('Unlock Limit Discount by Manager')
    assigned_user_ids = fields.Many2many('res.users',  compute='_compute_assigned_user_ids',
    string="Assigned Users", help='Users assigned to this pos config (multi session)')
    manager_ids = fields.Many2many('res.users', 'pos_config_res_user_manager_rel', 'config_id', 'user_id',
                                   string='Manager Validation')
    stock_location_id = fields.Many2one('stock.location', string='POS Default Source Location',
                                        related='picking_type_id.default_location_src_id',
                                        readonly=1)
    stock_location_dest_id = fields.Many2one('stock.location', string='POS Default Dest Location',
                                             related='picking_type_id.default_location_dest_id',
                                             readonly=1)
    discount_value = fields.Boolean('Discount Value')
    discount_value_limit = fields.Float(
        'Discount Value Limit',
        help='This is maximum Amount Discount Cashier can set to each Line'
    )
    discount_global_id = fields.Many2one(
        'product.product',
        string='Discount Product Value',
        domain=[('available_in_pos', '=', True), ('sale_ok', '=', True)]
    )
    posbox_save_orders = fields.Boolean('Save Orders on PosBox')
    # posbox_save_orders_iot_ids = fields.Many2many(
    #     'pos.iot',
    #     'pos_config_iot_save_orders_rel',
    #     'config_id',
    #     'iot_id',
    #     string='IoT Boxes for save Orders'
    # )
    posbox_save_orders_server_ip = fields.Char(
        'Public Ip Address',
        help='Example Ip: 192.168.100.100'
    )
    posbox_save_orders_server_port = fields.Char(
        'Public Port Number',
        default='8069',
        help='Example Port: 8069'
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        'Analytic Account'
    )
    limit_categories = fields.Boolean("Restrict Available Product Categories")
    iface_available_categ_ids = fields.Many2many(
        'pos.category',
        string='Available PoS Product Categories',
        help='The point of sale will only display products \n'
             'which are within one of the selected category trees. \n'
             'If no category is specified, all available products will be shown')
    barcode_scan_timeout = fields.Float(
        'Times timeout',
        default=1000,
        help='Period times timeout for next scan\n'
             '1000 = 1 second\n'
             'I good time for scan we think 1000'
    )
    rounding_automatic = fields.Boolean('Rounding Automatic',
                                        help='When cashier go to Payment Screen, POS auto rounding')
    rounding_type = fields.Selection([
        ('rounding_by_decimal_journal', 'By Decimal Rounding of Journal'),
        ('rounding_integer', 'Rounding to Integer'),
        ('rounding_up_down', 'Rounding Up and Down'),
    ],
        default='rounding_integer',
        help='1) * By Decimal Rounding of Payment Method [Rounding Amount]\n'
             '2) * Rounding to Integer: \n'
             '\n'
             'Rule 1: - From decimal from 0 to 0.25     become 0.0\n'
             'Rule 2: - From decimal from 0.25 to 0.75  become 0.5\n'
             'Rule 3: - From decimal from 0.75 to 0.999 become to 1 \n'
             '\n'
             '3) * Rounding up and down \n'
             'Rule 1: 0.1 to 0.4999 become 0.0 \n'
             'Rule 2: 0.5 to 0.9999 will  +1.0'
    )

    service_charge_ids = fields.Many2many(
        'pos.service.charge',
        'pos_config_service_charge_rel',
        'config_id',
        'charge_id',
        string='Services Charge on POS'
    )
    service_charge_type = fields.Selection(
        [
            ('tax_included', 'Taxes Included'),
            ('tax_excluded', 'Taxes Excluded')
        ]
        , default='tax_excluded'
        , string='Services Charge'
    )
    service_shipping_automatic = fields.Boolean(
        'Service Shipping Automatic',
        help='When cashier select Customer \n'
             'POS auto compute distance (km) from your Shop Stock Location to Partner Address \n'
             'And get distance for compute shipping cost, automatic add this cost to cart'
    )
    google_map_api_key = fields.Char('Google Map Api Key', invisible=True)
    payment_reference = fields.Boolean(
        'Payment Reference',
        help='Allow cashier add reference Note each payment line'
    )
    display_margin = fields.Boolean('Display Margin')
    start_session_oneclick = fields.Boolean(
        'Start Session One Click'
    )
    translate_products_name = fields.Boolean(
        'Load Translate Products Name',
        help='When active, all products name language will load correct language of language POS User started session',
        default=0
    )
    set_product_name_from_field = fields.Selection(
        _get_product_field_char,
        default='name',
        string='Product Name display by field',
        help="Choose the field of the table Product which will be used for Product Display"
    )
    replace_partners_name = fields.Boolean(
        'Replace Partners Name',
        help='When active, partners name will replace buy field you choose bellow',
        default=0
    )
    set_partner_name_from_field = fields.Selection(
        _get_customer_field_char,
        default='name',
        string='Customer Name display from field',
        help="Choose the field of the table Customer which will be used for Customer Display"
    )
    create_quotation = fields.Boolean(
        'Transfer Orders',
        help='Allow cashier create Quotation Order, \n'
             'And transfer Orders to another POS \n'
             'May your business have call center, you can active this feature'
    )
    assign_orders_to_config_ids = fields.Many2many(
        'pos.config',
        'pos_config_assign_orders_rel',
        'from_config_id',
        'assign_config_id',
        string='POS Received Orders'
    )
    product_generic_option = fields.Boolean(
        'Product Generic Option',
        help='Generic product options. \n'
             'It should be possible to define certain product options that can be applied to any product \n'
             'Example: "Whipped cream" or "Extra hot".\n'
             'Generic product options may have an additional cost and materials list. \n'
             'If you active this option, please go to Retail Operation / Product Generic Option and add datas'
    )
    mrp = fields.Boolean(
        'Manufacturing',
        help='If each POS Line, cashier select assign BOM (Bill Of Material)\n'
             'When Cashier finish input BOM each POS Line \n'
             'Manufacturing Order will create and automatic processing \n'
    )
    last_save_cache = fields.Char('Last Save Cache', compute='_get_last_save_cache')
    category_ancestors = fields.Char('Category Ancestors', compute='_get_category_ancestors')
    point_of_sale_update_stock_quantities = fields.Selection([
        ('closing', 'At the session closing (advised)'),
        ('real', 'In real time'),
    ],
        default='real',
        string="Update quantities in stock",
        required=1,
        help="At the session closing: A picking is created for the entire session when it's closed\n In real time: Each order sent to the server create its own picking"
    )
    multi_session = fields.Boolean(
        'Allow Multi Session',
        help='Each Employee will assign 1 POS Session \n'
             'Difference Employee is difference POS Session'
    )
    display_filter_product_categories = fields.Boolean(
        'Display Sale Product Category Filter',
        help='Allow Filter Products by Sale Products Category \n'
             'Like filter POS Category'
    )
    product_category_ids = fields.Many2many(
        'product.category',
        'pos_config_product_category_rel',
        'config_id',
        'category_id',
        string='Replace POS Categories by Sale Product Categories',
        help='If you select Sale Product Categories here \n'
             'All POS Categories will invisible \n'
             'POS Product Categories will replace by Sale Categories here'
    )
    sessions_opened = fields.Boolean(
        'Have Sessions Opened',
        compute='_check_has_sessions_not_closed'
    )
    search_query_only_start_when_enter = fields.Boolean(
        'Query Products when Enter Only',
        default=0,
        help='If you checked to this checkbox \n'
             'When you typing on Search Product box and required Press to Enter of your Keyboard \n'
             'POS will automatic search Product with value you typed \n'
             'If you not press to Enter, pos will not query Products'
    )
    create_category_direct = fields.Boolean('Create POS Category Direct')
    create_product_direct = fields.Boolean('Create Product Direct')
    customer_facing_screen = fields.Boolean('Customer Facing Screen', default=1)
    customer_facing_screen_width = fields.Integer('Width Customer Screen', default=1440)
    customer_facing_screen_height = fields.Integer('Height Customer Screen', default=900)
    rounding = fields.Boolean('Rounding')
    rounding_factor = fields.Float('Rounding Factor', default='1.0')
    decimal_places = fields.Integer('Decimal Places', default=0)

    font_family = fields.Char(
        'Font Family',
        default='"Montserrat", "Unicode Support Noto", sans-serif'
    )
    price_tag_color = fields.Char(
        'Price of Product Color',
        default='#FF5722',
        help='Price Color of Product'
    )
    header_background_color = fields.Char('Header Background App', default='#875A7B')
    cart_box_style = fields.Selection([
        ('left', 'Left of Page'),
        ('right', 'Right of Page')
    ], default='left', required=1, string='Cart position of Page')
    buttons_box_style = fields.Selection([
        ('left', 'Left of POS Screen'),
        ('center', 'Center of POS Screen'),
        ('right', 'Right of POS Screen')
    ], default='left', required=1, string='Buttons Box Position')
    background = fields.Char(
        'Background of App',
        default='#ffffff',
        help='Background almost Screens of POS'
    )
    product_screen_background = fields.Char('Product Screen Background', default='#ffffff')
    cart_background = fields.Char('Cart Background', default='#ffffff')
    payment_screen_background = fields.Char('Payment Screen Background', default='#ffffff')
    numpad_background = fields.Char('Numpad Button Background', default='#ffffff')

    product_categories_height = fields.Integer(
        'Product Categories Height (%)',
        help='You can set from 0 to 100%',
        default=8
    )
    product_width = fields.Integer(
        'Product Width (em)',
        default=16,
        help='Default width of Product box is 18em',
        required=1
    )
    product_height = fields.Integer(
        'Product Height (em)',
        default=16,
        help='Default height of Product box is 18em',
        required=1)
    product_margin = fields.Float(
        'Product Margin (em)',
        default=0.1,
        help='Default Margin between Products Box',
        required=1)
    product_image_width = fields.Integer(
        'Product Image Width (%)',
        default=50,
        help="Width of Product's Image, set between 0 to 100"
    )
    product_image_height = fields.Integer(
        'Product Image Height (%)',
        default=50,
        help="Height of Product's Image, set between 0 to 100"
    )
    product_name_font_size = fields.Integer(
        'Product Name Font Size',
        default=18,
        help="Font Size of Product's Name, set between 13 to 20"
    )
    display_mobile_mode = fields.Boolean(
        'Change to Mobile Mode',
        help='If active it, when your pos resize screen \n'
             'POS Screen automatic change to Mobile Mode'
    )
    display_mobile_screen_size = fields.Integer(
        'Automatic change to Mobile mode with width of Page smaller than (px)',
        default=1200
    )
    display_product_image = fields.Selection([
        ('none', 'Not Display'),
        ('inline-block', 'Display')
    ],
        default='inline-block',
        required=1,
        string="Display Product's Image")
    cart_width = fields.Integer(
        'Cart List Width (%)',
        help='Width of Cart List, suggest is 45 (%)',
        default=45
    )
    whatsapp_api = fields.Char('WhatApp Api')
    whatsapp_token = fields.Char('WhatApp Token')
    whatsapp_send_type = fields.Selection([
        ('automatic', 'Automatic'),
        ('manual', 'Manual')
    ], string='WhatApp send Receipt Type', default='manual')
    whatsapp_message_receipt = fields.Text(
        'WhatsApp Message Receipt',
        default='Thank you for giving us the opportunity to serve you. This is your receipt'
    )

    checkin_screen = fields.Boolean(
        'CheckIn Screen',
        help='Customer easy Check In via Phone/Mobile \n'
             'If Client not register before, them easy register new'
    )

    hidden_product_ids = fields.Many2many(
        'product.product',
        'pos_config_product_hidden_rel',
        'pos_config_id',
        'product_id',
        string="Hidden Products",
        help='Hidden Products selected here out of POS Products Screen'
    )

    warning_closing_session = fields.Boolean(
        'Warning Closing Session',
        default=1,
        help='Warning Users when them close session \n'
             'With 2 reason bellow, we will warning POS Users when them closing a POS Screen \n'
             '1. If have orders draft, not full fill payment and submit to Server \n'
             '2. If server offline, and users close POS, could not open POS screen back\n'
             'Will Warning for users'
    )
    warning_odoo_offline = fields.Boolean(
        'Warning Offline',
        default=1,
        help='When POS User finish and Validate Order \n'
             'If POS counter have internet problem (offline) \n'
             'Or Your Server Offline \n'
             'POS Screen automatic warning POS Users before Validate the Order'
    )
    pos_title = fields.Char('POS Title', default='POS TL Technologies')
    # show_all_payment_methods = fields.Boolean('Show All Payment Methods', default=0)
    sync_partners_realtime = fields.Boolean(
        'Automatic Sync Realtime Customers',
        default=0,
        help='If have any change Customers from backend \n'
             'When you go to POS Customers screen \n'
             'Automatic update and sync'
    )
    cache = fields.Selection([
        ('none', 'None'),
        ('browse', 'Browse'),
        ('iot', 'IOT')
    ],
        default='none',
        string='Turbo Starting POS Screen',
        help='Noted: POS Config and POS Session never cache, it will refresh with POS Screen refresh \n'
             '1) none: Loading all pos datas direct Server \n'
             '2) browse: All pos datas will Cached to Users Browse \n'
             '3) iot: all pos datas will cached on iotbox (required iot or posbox)'
    )

    local_network_printer = fields.Boolean(
        "Enable IP Network Printing",
        default=False,
        help="If you enable network printing,\
                Printing via IoT Box will be given second priority")
    local_network_printer_ip_address = fields.Char('Printer IP Address', size=45)
    local_network_printer_port = fields.Integer('Printer IP Port', default='9100')
    product_recommendation = fields.Boolean(
        'Showing Product Recommendations on Product Screen',
        help='Example: Last times have some customers buy Product X and Product Y and Z \n'
             'Another customer go to buy product X or Y or Z, will suggest on Products Screen Product X,Y,Z (like may you like products ...)'
    )
    product_recommendation_number = fields.Integer(
        'Products Recommendations Number',
        help='Total Products Recommendations will display POS Screen',
        default=20,
    )
    show_session_information = fields.Boolean(
        'Show Session Information on POS header',
        help='Show Session Name, Opened Date and Sale Orders count of Session on header of POS Screen'
    )
    tip_percent = fields.Boolean(
        'Tip (%)',
        help='Allow cashier set Tip (%) base on Total Paid of Order'
    )
    tip_percent_max = fields.Float(
        'Tip Maximum (%) can set',
        default=10,
        help='Maximum (%) Tip can set [0 to 100%]'
    )

    categ_dislay_type = fields.Selection([
        ('filter', 'Filter by Parent Category Selected'),
        ('all', 'All Sub and Childs of Category Selected')
    ],
        default='all',
        string='Categories Display Type',
        help='Filter: If You selected Category A, only display Category A1, A2 ... child of Category A \n'
             'All: Always show All your POS Categories you have'
    )
    custom_sale = fields.Boolean('Custom Sale')
    custom_sale_product_id = fields.Many2one(
        'product.product',
        string='Custom Product',
        domain=[('available_in_pos', '=', True)]
    )


    multi_currency = fields.Boolean(
        'Multi Currency',
        help='Allow cashier change currency of Order filter by Cash Currency customer need to paid'
    )
    multi_currency_ids = fields.Many2many(
        'res.currency',
        'pos_config_res_currency_rel',
        'config_id',
        'currency_id',
        string='Currencies'
    )
    
    allowed_employee_ids = fields.Many2many('hr.employee', string='Allowed Employees', compute='_compute_allowed_employee_ids')

    fire_appetizer = fields.Many2many('pos.category', 'pos_config_pos_category_fa_cat_rel','config_id','category_id')
    fire_main_course = fields.Many2many('pos.category', 'pos_config_pos_category_fmc_cat_rel','config_id','category_id')
    fire_dessert = fields.Many2many('pos.category', 'pos_config_pos_category_fd_cat_rel','config_id','category_id')
    enable_fire_appetizer = fields.Boolean('Enable Fire Appetizer')
    enable_fire_main_course = fields.Boolean('Enable Fire Main Course')
    enable_fire_dessert = fields.Boolean('Enable Fire Dessert')
    
    enable_seat_time = fields.Boolean()
    seat_time = fields.Float()
    show_product_template = fields.Boolean('Show Product Template?', help='Show Product Templates and select the variants in popup screen', default=True)

    available_product_domain = fields.Char(string="Available Product Domain", compute='_compute_available_product_domain')


    promotion_manual_select = fields.Boolean(
        'Promotion Manual Choice', default=0,
        help='When you check to this checkbox, \n'
             'your cashiers will have one button, \n'
             'when cashiers clicked on it, \n'
             'all promotions active will display for choose')
    promotion_auto_add = fields.Boolean(
        'Promotion Auto Apply',
        help='All Promotion Active with Condition Items in Cart \n'
             'When Cashier click Paid button, all Promotions Active will add to Order')

    promotion_ids = fields.Many2many(
        'pos.promotion',
        'pos_config_promotion_rel',
        'config_id',
        'promotion_id',
        string='Promotions Applied')

    is_manual_sync_for_sync_between_session = fields.Boolean('Manual sync for sync between session', 
        default=True,
        help='- Sync Order')
    is_manual_sync_masterdata = fields.Boolean('Manual sync master data', default=True)
    is_manual_sync_member = fields.Boolean('Manual sync member', default=True)
    is_auto_sync_product_stock = fields.Boolean('Auto Sync Product Stock', default=False, help='Auto sync Product Stock to get realtime stock')
    is_auto_sync_product_price = fields.Boolean('Auto Sync Product Price', default=False, help='Auto sync Product Price after change in the Backend') # Not used, because change to is_auto_sync_product
    is_auto_sync_product = fields.Boolean('Auto Sync Product', default=False, help='Auto sync Product "name, pos category, barcode, sales price" after change in the Backend')
    is_auto_sync_pricelist = fields.Boolean('Auto Sync Pricelist', default=False, help='Auto sync Pricelist after change in the Backend')
    is_auto_sync_promotion = fields.Boolean('Auto Sync Promotion', default=False, help='Auto sync Promotion after change in the Backend')
    is_auto_sync_coupon = fields.Boolean('Auto Sync Coupon', default=False, help='Auto sync Coupon after change in the Backend')
    is_monitor_auto_sync = fields.Boolean('Monitor Auto Sync', default=False)
    is_force_sync_promotion = fields.Boolean('Force Sync Promotion', default=False)
    filter_load_pos_order = fields.Selection([
        ('today', 'Today'),
        ('last_3_days', ' Last 3 Days'),
        ('last_7_days', 'Last 7 Days'),
        ('last_1_month', 'Last 1 Month'),
        ('last_1_year', 'Last 1 Year (365 days)'),
        ('load_all', 'Load All'),
    ], default='last_3_days')
    zone_id = fields.Many2one('pos.zone','Zone')
    product_voucher_service_id = fields.Many2one('product.product','Product Voucher Service')
    product_coupon_service_id = fields.Many2one('product.product','Product Coupon Service') # not used, need remove later

    @api.onchange('multi_location','multi_stock_operation_type')
    def onchange_reset_multi_location_and_op_type(self):
        if not self.multi_location:
            self.stock_location_ids = False
            self.update_stock_onhand = False
        if not self.multi_stock_operation_type:
            self.multi_stock_operation_type_ids = False


    # ----------- TODO: set pos link to our sub link -------------
    #
    def _get_pos_base_url(self):
        return '/pos/web'

    #
    # ----------- TODO: set pos link to our sub link -------------

    def send_message_via_whatsapp(self, pos_config_id, mobile_no, message):
        _logger.info('[send_message_via_whatsapp]: %s' % mobile_no)
        mobile_no = re.sub('[^0-9]', '', mobile_no)
        if not mobile_no:
            return False
        pos = self.sudo().browse(pos_config_id)
        endpoint = pos.whatsapp_api
        token = pos.whatsapp_token
        url = ''
        if all([endpoint, token]):
            url = f"{endpoint}/sendMessage?token={token}"
        else:
            ValidationError(_(f'Missing Whatsapp credentials, \ncontact to your Admin.'))
        if not url:
            return json.dumps("Missing Whatsapp configuration, contact to your Admin")
        headers = {
            'Content-Type': 'application/json',
        }
        payload = {
            'phone': mobile_no,
            'body': message,
        }
        try:
            req = requests.post(url, data=json.dumps(payload), headers=headers)
            response = req.json()
            if req.status_code == 201 or req.status_code == 200:
                _logger.info(
                    f"\n[send_message_via_whatsapp] Send Message successfully send to  phone number : {mobile_no}")
            else:
                if 'error' in response:
                    message = response['error']
                    _logger.error(f"[send_message_via_whatsapp] Reason: {req.reason}, Message:{message}")
            return response
        except Exception as e:
            _logger.error(e)
            return e

    def send_receipt_via_whatsapp(self, pos_config_id, ticket_img, mobile_no, message):
        _logger.info('[send_receipt_via_whatsapp]: %s' % mobile_no)
        mobile_no = re.sub('[^0-9]', '', mobile_no)
        if not mobile_no:
            return False
        if message:
            self.send_message_via_whatsapp(pos_config_id, mobile_no, message)
        pos = self.sudo().browse(pos_config_id)
        endpoint = pos.whatsapp_api
        token = pos.whatsapp_token
        url = ''
        if all([endpoint, token]):
            url = f"{endpoint}/sendFile?token={token}"
        else:
            ValidationError(_(f'Missing Whatsapp credentials, \ncontact to your Admin.'))
        if not url:
            return json.dumps("Missing Whatsapp configuration, contact to your Admin")
        headers = {
            'Content-Type': 'application/json',
        }
        payload = {
            'phone': mobile_no,
            'body': f"data:image/jpeg;base64,{ticket_img}",
            'filename': "POS-Receipt-%s.jpeg" % fields.Datetime.now()
        }
        try:
            req = requests.post(url, data=json.dumps(payload), headers=headers)
            response = req.json()
            if req.status_code == 201 or req.status_code == 200:
                _logger.info(
                    f"\n[send_receipt_via_whatsapp] Send Receipt successfully send to  phone number : {mobile_no}")
            else:
                if 'error' in response:
                    message = response['error']
                    _logger.error(f"[send_receipt_via_whatsapp] Reason: {req.reason}, Message:{message}")
            return response
        except Exception as e:
            _logger.error(e)
            return e

    def send_pdf_via_whatsapp(self, pos_config_id, file_name, report_ref, record_id, mobile_no, message):
        mobile_no = re.sub('[^0-9]', '', mobile_no)
        if not mobile_no:
            return False
        if message:
            self.send_message_via_whatsapp(pos_config_id, mobile_no, message)
        qr_pdf = self.env.ref(report_ref)._render_qweb_pdf(record_id)
        file = qr_pdf[0]
        qr_pdf = base64.b64encode(qr_pdf[0])
        pos = self.sudo().browse(pos_config_id)
        endpoint = pos.whatsapp_api
        token = pos.whatsapp_token
        url = ''
        if all([endpoint, token]):
            url = f"{endpoint}/sendFile?token={token}"
        else:
            ValidationError(_(f'Missing Whatsapp credentials, \ncontact to your Admin.'))
        if not url:
            return json.dumps("Missing Whatsapp configuration, contact to your Admin")
        headers = {
            'Content-Type': 'application/json',
        }
        payload = {
            'phone': mobile_no,
            'body': 'data:application/pdf;base64,' + str(qr_pdf)[2:-1],
            'filename': "%s-%s.pdf" % (file_name, fields.Datetime.now())
        }
        try:
            req = requests.post(url, data=json.dumps(payload), headers=headers)
            response = req.json()
            if req.status_code == 201 or req.status_code == 200:
                _logger.info(
                    f"\n[send_pdf_via_whatsapp] Send Receipt successfully send to  phone number : {mobile_no}")
            else:
                if 'error' in response:
                    message = response['error']
                    _logger.error(f"[send_pdf_via_whatsapp] Reason: {req.reason}, Message:{message}")
            return response
        except Exception as e:
            _logger.error(e)
            return e

    def revertToDefaultStyle(self):
        self.write({
            'background': '#ffffff',
            'price_tag_color': '#FF5722',
            'payment_screen_background': '#ffffff',
            'product_screen_background': '#ffffff',
            'cart_box_style': 'right',
            'product_width': 16,
            'product_height': 16,
            'product_margin': 0.1,
            'display_product_image': 'inline-block',
            'cart_width': 30,
            'cart_background': '#ffffff',
            'numpad_background': '#ffffff',
            'font_family': '"Montserrat", "Unicode Support Noto", sans-serif'
        })

    def _check_has_sessions_not_closed(self):
        for config in self:
            sessions = self.env['pos.session'].sudo().search([
                ('state', '!=', 'closed'),
                ('config_id', '=', config.id)
            ])
            if sessions:
                config.sessions_opened = True
            else:
                config.sessions_opened = False

    def _compute_allowed_employee_ids(self):
        for config in self:
            allowed_employee_ids = []
            if config.module_pos_hr:
                employee_ids = []
                for user in config.user_ids:
                    employee_ids += user.employee_ids.ids
                domain = [('id', 'in', employee_ids)]
                allowed_employee_ids = self.env['hr.employee'].search(domain)
            config.allowed_employee_ids = allowed_employee_ids

    def _get_sync_with_sessions(self):
        for config in self:
            config.sync_multi_session_with = ''
            if config.sync_multi_session:
                for c in config.sync_to_pos_config_ids:
                    config.sync_multi_session_with += c.name + ' / '

    @api.onchange('allow_numpad')
    def onchange_allow_numpad(self):
        if not self.allow_numpad:
            self.allow_discount = False
            self.allow_qty = False
            self.allow_price = False
            self.allow_remove_line = False
            self.allow_minus = False
        else:
            self.allow_discount = True
            self.allow_qty = True
            self.allow_price = True
            self.allow_remove_line = True
            self.allow_minus = True

    def _get_last_save_cache(self):
        for config in self:
            log = self.env['pos.call.log'].search([], limit=1)
            if log:
                config.last_save_cache = log.write_date
            else:
                config.last_save_cache = 'Not Install Before'

    def _get_category_ancestors(self):
        pos_categories = self.env['pos.category'].search_read([], ['id','name','child_id','parent_id'])
        root_category_id = 0
        category_childs = { cat['id']: cat['child_id'] for cat in pos_categories if cat['child_id']}
        category_childs[root_category_id] = [cat['id'] for cat in pos_categories if not cat['parent_id']]
        category_ancestors = {}

        def make_ancestors(cat_id, ancestors):
            import copy
            category_ancestors[cat_id] = ancestors;
            ancestors = copy.deepcopy(ancestors)
            ancestors.append(cat_id);
            for child in category_childs.get(cat_id, []):
                make_ancestors(child, ancestors);
                
        make_ancestors(root_category_id, []);

        for config in self:
            config.category_ancestors = json.dumps(category_ancestors)

    @api.onchange('sync_multi_session')
    def onchange_sync_multi_session(self):
        if not self.sync_multi_session:
            self.sync_multi_session_manual_stop = False

    def remove_sync_between_session_logs(self):
        for config in self:
            sessions = self.env['pos.session'].search([(
                'config_id', '=', config.id
            )])
        return True

    @api.onchange('discount')
    def onchange_discount(self):
        if self.discount:
            self.discount_limit_amount = 0
            self.discount_limit = False

    @api.onchange('multi_stock_operation_type')
    def onchange_multi_stock_operation_type(self):
        if not self.multi_stock_operation_type:
            self.multi_stock_operation_type_ids = [(6, 0, [])]

    def reinstall_database(self):
        ###########################################################################################################
        # new field append :
        #                    - update param
        #                    - remove logs datas
        #                    - remove cache
        #                    - reload pos
        #                    - reinstall pos data
        # reinstall data button:
        #                    - remove all param
        #                    - pos start save param
        #                    - pos reinstall with new param
        # refresh call logs:
        #                    - get fields domain from param
        #                    - refresh data with new fields and domain
        ###########################################################################################################
        parameters = self.env['ir.config_parameter'].sudo().search([
            ('key', 'in', [
                'product.product', 'res.partner',
                'account.move', 'account.move.line',
                'pos.order', 'pos.order.line',
                'sale.order', 'sale.order.line'
            ])])
        if parameters:
            parameters.sudo().unlink()
        self.env['pos.cache.database'].search([]).unlink()
        self.env['pos.call.log'].search([]).unlink()
        sessions_opened = self.env['pos.session'].sudo().search([('state', '=', 'opened')])
        sessions_opened.write({
            'required_reinstall_cache': True
        })
        for session in sessions_opened:
            self.env['bus.bus'].sendmany(
                [[(self.env.cr.dbname, 'pos.remote_sessions', session.user_id.id), json.dumps({
                    'remove_cache': True,
                    'database': self.env.cr.dbname,
                    'session_id': session.id
                })]])
        for config in self:
            sessions = self.env['pos.session'].sudo().search(
                [('config_id', '=', config.id), ('state', '=', 'opened')])
            if not sessions:
                return {
                    'type': 'ir.actions.act_url',
                    'url': '/pos/web?config_id=%d' % config.id,
                    'target': 'self',
                }
            sessions.write({'required_reinstall_cache': True})
            config_fw = config
            self.env['pos.session'].sudo().search(
                [('config_id', '!=', config.id), ('state', '=', 'opened')]).write({'required_reinstall_cache': True})
        return {
            'type': 'ir.actions.act_url',
            'url': '/pos/web?config_id=%d' % config_fw.id,
            'target': 'self',
        }

    def remote_sessions(self):
        return {
            'name': _('Remote sessions'),
            'view_type': 'form',
            'target': 'new',
            'view_mode': 'form',
            'res_model': 'pos.remote.session',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'context': {},
        }

    def validate_and_post_entries_session(self):
        for config in self:
            sessions = self.env['pos.session'].search([
                ('config_id', '=', config.id),
                ('state', '!=', 'closed'),
                ('rescue', '=', False)
            ])
            if not sessions:
                sessions = self.env['pos.session'].search([
                    ('config_id', '=', config.id),
                    ('state', '!=', 'closed'),
                    ('rescue', '=', True)
                ])
            if sessions:
                for session in sessions:
                    if session.cash_control and abs(
                            session.cash_register_difference) > session.config_id.amount_authorized_diff:
                        return {
                            'name': _('Session'),
                            'view_mode': 'form,tree',
                            'res_model': 'pos.session',
                            'res_id': session.id,
                            'view_id': False,
                            'type': 'ir.actions.act_window',
                        }
                    else:
                        session.force_action_pos_session_close()
                    vals = {
                        'validate_and_post_entries': True,
                        'session_id': session.id,
                        'config_id': session.config_id.id,
                        'database': self.env.cr.dbname
                    }
                    self.env['bus.bus'].sendmany(
                        [[(self.env.cr.dbname, 'pos.remote_sessions', session.user_id.id), json.dumps(vals)]])
            else:
                raise UserError('Have not any Sessions need Close')
        return True

    def write(self, vals):
        if vals.get('allow_discount', False) or vals.get('allow_qty', False) or vals.get('allow_price', False):
            vals['allow_numpad'] = True

        if vals.get('expired_days_voucher', None) and vals.get('expired_days_voucher') < 0:
            raise UserError('Expired days of voucher could not smaller than 0')
            if config.pos_order_period_return_days <= 0:
                raise UserError('Period days return orders and products required bigger than or equal 0 day')

        if vals.get('module_pos_restaurant'):
            vals['display_product_name_without_product_code'] = True

        res = super(PosConfig, self).write(vals)

        for config in self:
            if not self._context.get('action_applied_to_selected_promotions_pos') and vals.get('promotion_ids'):
                config.action_applied_to_selected_promotions_pos()
            if vals.get('management_session', False) and not vals.get('default_cashbox_id'):
                if not config.default_cashbox_id and not config.cash_control:
                    raise UserError(
                        'Your POS config missed config Default Opening (Cash Control), Please go to Cash control and set Default Opening')

            if 'name' in vals and config.sequence_id:
                config.sequence_id.write({
                    'name': _('POS Order %s', config.name),
                    'prefix': "%s/" % config.name,
                })

        if vals.get('google_map_api_key', None):
            self.env['ir.config_parameter'].sudo().set_param('base_geolocalize.google_map_api_key',
                                                             vals.get('google_map_api_key', None))

        if not self._context.get('apply_to_selected_pos'):
            if 'promotion_ids' in vals:
                promotions = self.env['pos.promotion'].sudo().search([('pos_apply','in',self.id)])
                for promotion in promotions:
                    if promotion.id not in self.promotion_ids.ids:
                        promotion.write({ 'pos_apply': [(3, self.id)] })
                        
        for c in self:
            sessions = self.env['pos.session'].search([
                ('config_id', '=', c.id),
                ('state', '=', 'opened')
            ])
            sessions.update_stock_at_closing = c.point_of_sale_update_stock_quantities == 'closing'
        return res

    
    @api.depends('write_date')
    def _compute_available_product_domain(self):
        for config in self:
            config.available_product_domain = json.dumps(self.env['product.product'].pos_product_domain())

    @api.onchange('module_pos_restaurant')
    def _onchange_module_pos_restaurant(self):
        if self.module_pos_restaurant:
            self.display_product_name_without_product_code = True

    def forceChangeUI(self):
        for config in self:
            sessions = self.env['pos.session'].search([
                ('config_id', '=', config.id),
                ('state', '=', 'opened')
            ])
            if sessions:
                config = self.search_read([
                    ('id', '=', config.id),
                ], [
                    'id',
                    'background',
                    'price_tag_color',
                    'cart_box_style',
                    'product_width',
                    'product_height',
                    'product_margin',
                    'cart_width',
                    'cart_background',
                    'font_family',
                    'display_product_image',
                    'payment_screen_background',
                ])[0]
                for s in sessions:
                    self.env['bus.bus'].sendmany(
                        [[(self.env.cr.dbname, 'pos.modifiers.background', s.user_id.id),
                          json.dumps(config)]])
        return True

    @api.constrains('picking_type_id')
    def _check_picking_type(self):
        for record in self:
            if record.picking_type_id.code != "outgoing":
                raise ValidationError(_("The selected Operation Type is not valid, Please select 'Delivery Orders' operation."))


    def action_applied_to_selected_promotions_pos(self):
        self.ensure_one()
        for promotion in self.promotion_ids:
            if self.id not in promotion.pos_apply.ids:
                promotion.with_context(action_applied_to_selected_promotions_pos=True).write({ 'pos_apply': [(4, self.id)] })
        return True

    @api.model
    def create(self, vals):
        if vals.get('allow_discount', False) or vals.get('allow_qty', False) or vals.get('allow_price', False):
            vals['allow_numpad'] = True
        if vals.get('expired_days_voucher', 0) < 0:
            raise UserError('Expired days of voucher could not smaller than 0')
        if vals.get('module_pos_restaurant'):
            vals['display_product_name_without_product_code'] = True
        config = super(PosConfig, self).create(vals)
        if config.pos_order_period_return_days <= 0:
            raise UserError('Period days return orders and products required bigger than or equal 0 day')
        if config.management_session and not config.default_cashbox_id and not config.cash_control:
            raise UserError(
                'Your POS config missed config Default Opening (Cash Control), Please go to Cash control and set Default Opening')
        if vals.get('google_map_api_key', None):
            self.env['ir.config_parameter'].sudo().set_param('base_geolocalize.google_map_api_key',
                                                             vals.get('google_map_api_key', None))

        if not self._context.get('action_applied_to_selected_promotions_pos') and vals.get('promotion_ids'):
            config.action_applied_to_selected_promotions_pos()
        return config


    @api.onchange('printer_id')
    @api.model
    def onchange_printer_id(self):
        if self.printer_id:
            self.is_posbox = True
            self.iface_print_via_proxy = True
            if not self.proxy_ip:
                warning = {
                    'title': _("Warning, input required !"),
                    'message': _('Please input IoT Box IP Address, it required')
                }
                return {'warning': warning}

    @api.onchange('cache')
    @api.model
    def onchange_cache(self):
        if ((self.cache == 'iot' and not self.is_posbox) or (self.cache == 'iot' and not self.proxy_ip)):
            warning = {
                'title': _("Warning, Input Required !"),
                'message': _('Please input IoT Box IP Address, it Required')
            }
            return {'warning': warning}

    @api.onchange('printer_ids')
    @api.model
    def onchange_printer_ids(self):
        if self.printer_ids:
            for printer in self.printer_ids:
                if printer.printer_type == 'network':
                    self.is_posbox = True
                    self.iface_print_via_proxy = True
                    if not self.proxy_ip:
                        warning = {
                            'title': _("Warning, input required !"),
                            'message': _('Please input IoT Box IP Address, it required')
                        }
                        return {'warning': warning}


    @api.onchange('is_posbox')
    def _onchange_is_posbox(self):
        super(PosConfig, self)._onchange_is_posbox()
        if not self.is_posbox:
            self.printer_id = False

    @api.model
    @api.onchange('management_session')
    def _onchange_management_session(self):
        self.cash_control = self.management_session

    def init_payment_method(self, journal_name, journal_sequence, journal_code, account_code, pos_method_type):
        Journal = self.env['account.journal'].sudo()
        Method = self.env['pos.payment.method'].sudo()
        IrModelData = self.env['ir.model.data'].sudo()
        IrSequence = self.env['ir.sequence'].sudo()
        Account = self.env['account.account'].sudo()
        user = self.env.user
        accounts = Account.search([
            ('code', '=', account_code), ('company_id', '=', self.company_id.id)])
        if accounts:
            accounts.sudo().write({'reconcile': True})
            account = accounts[0]
        else:
            account = Account.create({
                'name': journal_name,
                'code': account_code,
                'user_type_id': self.env.ref('account.data_account_type_current_assets').id,
                'company_id': self.company_id.id,
                'note': 'code "%s" auto give voucher histories of customers' % account_code,
                'reconcile': True
            })
            model_datas = IrModelData.search([
                ('name', '=', account_code + str(self.company_id.id)),
                ('module', '=', "equip3_pos_masterdata"),
                ('model', '=', 'account.account'),
                ('res_id', '=', account.id),
            ])
            if not model_datas:
                IrModelData.create({
                    'name': account_code + str(self.company_id.id),
                    'model': 'account.account',
                    'module': "equip3_pos_masterdata",
                    'res_id': account.id,
                    'noupdate': True,  # If it's False, target record (res_id) will be removed while module update
                })

        journals = Journal.search([
            ('code', '=', journal_code),
            ('company_id', '=', self.company_id.id),
        ])
        if journals:
            journals.sudo().write({
                'loss_account_id': account.id,
                'profit_account_id': account.id,
                'pos_method_type': pos_method_type,
                'sequence': journal_sequence,
            })
            journal = journals[0]
        else:
            new_sequence = IrSequence.create({
                'name': journal_name + str(self.company_id.id),
                'padding': 3,
                'prefix': account_code + str(self.company_id.id),
            })
            model_datas = IrModelData.search(
                [
                    ('name', '=', account_code + str(new_sequence.id)),
                    ('module', '=', "equip3_pos_masterdata"),
                    ('model', '=', 'ir.sequence'),
                    ('res_id', '=', new_sequence.id),
                ])
            if not model_datas:
                IrModelData.create({
                    'name': account_code + str(new_sequence.id),
                    'model': 'ir.sequence',
                    'module': "equip3_pos_masterdata",
                    'res_id': new_sequence.id,
                    'noupdate': True,
                })
            journal = Journal.create({
                'name': journal_name,
                'code': journal_code,
                'type': 'cash',
                'pos_method_type': pos_method_type,
                'company_id': self.company_id.id,
                'loss_account_id': account.id,
                'profit_account_id': account.id,
                'sequence': journal_sequence,
            })
            model_datas = IrModelData.search(
                [
                    ('name', '=', account_code + str(journal.id)),
                    ('module', '=', "equip3_pos_masterdata"),
                    ('model', '=', 'account.journal'),
                    ('res_id', '=', int(journal.id)),
                ])
            if not model_datas:
                IrModelData.create({
                    'name': account_code + str(journal.id),
                    'model': 'account.journal',
                    'module': "equip3_pos_masterdata",
                    'res_id': int(journal.id),
                    'noupdate': True,
                })
        methods = Method.search([
            ('name', '=', journal_name),
            ('company_id', '=', self.company_id.id)
        ])
        if not methods:
            method = Method.create({
                'name': journal_name,
                'receivable_account_id': account.id,
                'cash_journal_id': journal.id,
                'company_id': self.company_id.id,
            })
        else:
            method_ids = [method.id for method in methods]
            if len(method_ids) > 0:
                method_ids.append(0)
                self.env.cr.execute(
                    "UPDATE pos_payment_method SET is_cash_count=False where id in %s", (tuple(method_ids),))
            method = methods[0]
        for config in self:
            opened_session = config.mapped('session_ids').filtered(lambda s: s.state != 'closed')
            if not opened_session:
                payment_method_added_ids = [payment_method.id for payment_method in config.payment_method_ids]
                if method.id not in payment_method_added_ids:
                    payment_method_added_ids.append(method.id)
                    config.sudo().write({
                        'payment_method_ids': [(6, 0, payment_method_added_ids)],
                    })
        return True 

    def open_ui(self):
        self.ensure_one()
        if not self.picking_type_id.default_location_src_id:
            raise UserError(
                'It not possible start POS Session if your POS Operation Type: %s not set Default Source Location' % self.picking_type_id.name)
        # Validate branch
        if self.pos_branch_id and self.env.user.pos_branch_id and self.pos_branch_id.id != self.env.user.pos_branch_id.id:
            raise ValidationError('You can not open this POS session since the POS Branch : %s is not allowed for you!' % self.pos_branch_id.name)
        # self.init_payment_method('Voucher', 100, 'JV', 'AJV', 'voucher')
        # self.init_payment_method('Wallet', 101, 'JW', 'AJW', 'wallet')
        # self.init_payment_method('Credit', 102, 'JC', 'AJC', 'credit')
        # self.init_payment_method('Return Order', 103, 'JRO', 'AJRO', 'return')
        # self.init_payment_method('Rounding Amount', 100, 'JRA', 'AJRA', 'rounding')
        return super(PosConfig, self).open_ui()

    def open_session_cb(self, check_coa=True):
        self.ensure_one()
        if not self.picking_type_id.default_location_src_id:
            raise UserError(
                'It not possible start POS Session if your POS Operation Type: %s not set Default Source Location' % self.picking_type_id.name)
        # self.init_payment_method('Voucher', 100, 'JV', 'AJV', 'voucher')
        # self.init_payment_method('Wallet', 101, 'JW', 'AJW', 'wallet')
        # self.init_payment_method('Credit', 102, 'JC', 'AJC', 'credit')
        # self.init_payment_method('Return Order', 103, 'JRO', 'AJRO', 'return')
        # self.init_payment_method('Rounding Amount', 100, 'JRA', 'AJRA', 'rounding')

        if self.bnk_cash_control:
            view = self.env.ref('account.view_account_bnk_stmt_cashbox')
            curr_seesion = self.env['pos.session'].create({
                'user_id': self.env.uid,
                'config_id': self.id,
                'pos_config_cashbox_lines_ids': self.cashbox_lines_ids,
                'cash_control': True,
            })
            self.current_session_id.update({
                'state': 'opening_control',    
            })
            if self.current_session_id:
                pos_session_view = self.env.ref('point_of_sale.view_pos_session_form')
                return {
                    'name': self.current_session_id.name,
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'pos.session',
                    'views': [(pos_session_view.id, 'form')],
                    'res_id': self.current_session_id.id,
                    'target': 'current',
                    'domain': [('id', '=', self.current_session_id.id)],
                }
        else:
            self.write({ 'write_date': fields.Datetime.now() })
            return super(PosConfig, self).open_session_cb(check_coa)

    def get_voucher_number(self, config_id):
        config = self.browse(config_id)
        if not config.voucher_sequence_id:
            raise UserError(
                u'Your POS Config not setting Voucher Sequence, please contact your POS Manager setting it before try this feature')
        else:
            return config.voucher_sequence_id._next()

    # TODO: for supported multi pricelist difference currency
    @api.constrains('pricelist_id', 'use_pricelist', 'available_pricelist_ids', 'journal_id', 'invoice_journal_id',
                    'payment_method_ids')
    def _check_currencies(self):
        return True
        # for config in self:
        #     if config.use_pricelist and config.pricelist_id not in config.available_pricelist_ids:
        #         raise ValidationError(_("The default pricelist must be included in the available pricelists."))
        # if self.invoice_journal_id.currency_id and self.invoice_journal_id.currency_id != self.currency_id:
        #     raise ValidationError(_(
        #         "The invoice journal must be in the same currency as the Sales Journal or the company currency if that is not set."))
        # if any(
        #         self.payment_method_ids \
        #                 .filtered(lambda pm: pm.is_cash_count) \
        #                 .mapped(
        #             lambda pm: self.currency_id not in (self.company_id.currency_id | pm.cash_journal_id.currency_id))
        # ):
        #     raise ValidationError(_(
        #         "All payment methods must be in the same currency as the Sales Journal or the company currency if that is not set."))

    def new_rate(self, from_amount, to_currency):
        pricelist_currency = self.env['res.currency'].browse(to_currency)
        company_currency = self.company_id.currency_id
        new_rate = company_currency._convert(from_amount, pricelist_currency,
                                             self.company_id or self.env.user.company_id, fields.Date.today())
        return new_rate

    def _open_session(self, session_id):
        session_form = super(PosConfig, self)._open_session(session_id)
        session = self.env['pos.session'].browse(session_id)
        if session.config_id.start_session_oneclick and session.state != 'opened':
            session.action_pos_session_open()
            return session.open_frontend_cb()
        else:
            return session_form


    display_table = fields.Boolean(
        'Display Tables',
        help='Display Tables on Kitchen/bar screen',
        default=1)
    display_all_product = fields.Boolean(
        'Display all Products',
        default=1)
    product_categ_ids = fields.Many2many(
        'pos.category',
        'config_pos_category_rel',
        'config_id', 'categ_id',
        string='Product Categories Display',
        help='Categories of product will display on kitchen/bar screen')

    product_categ_display_names = fields.Char(string="Product Categories Display Names", compute='_compute_product_categ_display_names')

    set_lines_to_done = fields.Boolean(
        'Allow Set Lines to Done', default=1)

    order_receipt_tickets = fields.Text('Receipt Orders')
    qr_orders = fields.Text('QR Orders')

    login_title = fields.Text(
        'Login Title',
        default='Welcome to Restaurant'
    )
    login_required = fields.Boolean('Required Customer Login')
    login_create_partner = fields.Boolean(
        'Automatic Add Customer',
        help='When customer register name and mobile \n'
             'Automatic create new customer if mobile does not exist in system'
    )
    qrcode_order_screen = fields.Boolean(
        'QrCode Orders',
        help='Management QRCode orders order by Customer'
    )
    qrcode_order_auto_alert = fields.Boolean(
        'Alert Popup when new Order Coming'
    )


    customer_facing_display_html = fields.Html(string='Customer facing display content', translate=True, compute='_compute_customer_html')
    user_ids = fields.Many2many(
        'res.users', string="Users with access",
        help='If left empty, all users can log in to the PoS session')

    sync_manual_button = fields.Boolean(
        'Sync Manual Order',
        help='Allow POS Session of This Config send Orders to another Sessions direct \n'
             'If another Sessions have the same Order with current Sessions \n'
             'Orders of another Sessions will replace by Orders send from current Session',
        default=False)
    screen_type = fields.Selection([
        ('cashier', 'Cashier Screen'),
        ('waiter', 'Waiter Screen'),
    ],
        string='Screen Type',
        default='cashier',
        help='Waiter Screen: is screen of waiters/cashiers take Order and submit Order to Kitchen'
    )
    period_minutes_warning = fields.Float(
        'Period Minutes Warning Kitchen',
        default=15,
        help='Example input 15 (minutes) here, of each line request from Waiter to Kitchen \n'
             'have waiting (processing) times bigger than 15 minutes \n'
             'Item requested by Waiters on Kitchen Screen auto highlight red color'
    )

    enable_void_time = fields.Boolean()
    void_time = fields.Float()
    void_order_pin_ids = fields.Many2many('res.users',
        'pos_config_users_void_order_rel', 'pos_config_id', 'user_id', string='Void PIN')
    void_order_pins = fields.Char(compute='compute_void_order_pins', string='Void Order PINs', store=False)
    void_order_line_pin_ids = fields.Many2many('res.users',
        'pos_config_users_void_order_line_rel', 'pos_config_id', 'user_id', string='Void Order lines PIN')
    void_order_line_pins = fields.Char(compute='compute_void_order_line_pins', string='Void Order Line PINs', store=True)
    # Advertisement Fields
    advertisement_image_ids = fields.Many2many('advertisement.images', 'pos_config_advertisement_rel', 'advertisement_id', 'pos_config_id')
    marquee_type = fields.Selection([
        ('static', 'Static Message'),
        ('run', 'Running Message'),
    ], default='static', string="Display Type")
    marquee_text = fields.Char(string="Promotional Message")
    marque_color = fields.Char(string="Promotional Message Color", default='#FFFFFF')
    marque_bg_color = fields.Char(string="Promotional Background Color", default='#FFFFFF')
    marque_font_size = fields.Integer(string="Promotional Font Size", default=1)
    mute_video_sound = fields.Boolean(string="Mute Video Sound")
    ac_width = fields.Char(string="Width (%)")
    ac_height = fields.Char(string="Height (%)")
    ac_qrcod = fields.Boolean("Show QR Code on CDS")
    ac_qr_link = fields.Char("QR Code Link")

    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    is_order_rounding = fields.Boolean("Order Rounding")
    order_rounding_type = fields.Selection([('Up','Up'), ('Down','Down'), ('Half Up','Half Up')], string="Order Rounding Type")
    
    def _default_picking_type_id(self):
        record = self.env.ref('stock.picking_type_out', raise_if_not_found=False)
        return record and record.id or False
    
    picking_type_id = fields.Many2one('stock.picking.type', default=_default_picking_type_id)
    pos_branch_id = fields.Many2one(
        'res.branch',
        string = "Branch",
        default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, 
        domain=lambda self: [('id', 'in', self.env.branches.ids)])
    pos_branch_name = fields.Char(related='pos_branch_id.name', string='Branch Name')
    branch_telephone = fields.Char(related='pos_branch_id.telephone', string='Branch Telephone')
    branch_address = fields.Text(related='pos_branch_id.address', string='Branch Address')
    branch_street = fields.Char(related='pos_branch_id.street', string='Branch Street')
    branch_street_2 = fields.Char(related='pos_branch_id.street_2', string='Branch Street2')

    @api.onchange('restaurant_order')
    def onchange_restaurant_order(self):
        if self.restaurant_order:
            self.order_receipt_tickets = False
            self.backup_orders_automatic = False

    def save_order_tickets(self, tickets):
        return self.write({'order_receipt_tickets': json.dumps(tickets)})

    def save_qr_orders(self, qrorders):
        return self.write({'qr_orders': json.dumps(qrorders)})


    def _compute_product_categ_display_names(self): 
        for config in self:
            product_categ_display_names = []
            if config.display_all_product:
                product_categ_display_names += [False, 'undefined']
                categs = self.env['pos.category'].search_read([], ['display_name'])
                for categ in categs:
                    product_categ_display_names += [categ['display_name']]
            else:
                for categ in config.product_categ_ids:
                    product_categ_display_names += [categ.display_name]
            config.product_categ_display_names = json.dumps(product_categ_display_names)


    @api.onchange('pos_branch_id')
    def onchange_pos_branch_id_diego(self):
        if not self.pos_branch_id: return
        self.warehouse_id = self.env['stock.warehouse'].search([
            ('branch_id', '=', self.pos_branch_id.id)
        ], limit=1).id

    # @api.onchange('warehouse_id')
    # def onchange_warehouse_id_diego(self):
    #     if not self.warehouse_id: return
    #     self.picking_type_id = self.env['stock.picking.type'].search([
    #         ('warehouse_id', '=', self.warehouse_id.id)
    #     ], limit=1).id
    #     self.picking_type_id

    @api.depends('void_order_pin_ids')
    def compute_void_order_pins(self):
        for record in self:
            user_pin_data = []
            for user in record.void_order_pin_ids:
                if user.pos_security_pin:
                    user_pin_data.append(str(user.pos_security_pin))
            record.void_order_pins = ','.join(pin for pin in user_pin_data)

    @api.depends('void_order_pin_ids')
    def compute_void_order_line_pins(self):
        for record in self:
            user_pin_data = []
            for user in record.void_order_line_pin_ids:
                if user.pos_security_pin:
                    user_pin_data.append(str(user.pos_security_pin))
            record.void_order_line_pins = ','.join(pin for pin in user_pin_data)

    def _compute_customer_html(self):
        def image_url(record, field, size=None):
            """Returns a local url that points to the image field of a given browse record."""
            sudo_record = record.sudo()
            data = '%s' % getattr(sudo_record, '__last_update')
            data = data.encode("utf-8")
            sha = sha1(data).hexdigest()
            sha = sha[0:7]
            size = '' if size is None else '/%s' % size
            return '/web/image/%s/%s/%s%s?unique=%s' % (record._name, record.id, field, size, sha)

        for config in self:
            image_data = []
            first_img = {}
            ad_image = self.env['advertisement.images']
            image_ids = config.advertisement_image_ids.ids
            if image_ids:
                top_image_id = image_ids[0]
                del image_ids[0]
                image_obj = ad_image.browse(top_image_id)
                first_img['file_type'] = image_obj.file_type
                first_img['is_youtube_url'] = image_obj.is_youtube_url
                if image_obj.file_type == "image":
                    if image_obj.image_type == 'url':
                        first_img['img_link'] = image_obj.url
                    else:
                        first_img['img_link'] = image_url(image_obj, 'ad_image')
                elif image_obj.file_type == "video":
                    if image_obj.video_type == 'url':
                        first_img['img_link'] = image_obj.video_url
                        url_value = image_obj.video_url.split('/')
                        name_of_url = url_value[len(url_value) - 1]
                        first_img['name_of_url'] = name_of_url
                    else:
                        args = {
                            'id': image_obj.id,
                            'model': image_obj._name,
                            'filename_field': 'ad_video_fname',
                            'field': 'ad_video',
                        }
                        first_img['img_link'] = '/web/content?%s' % url_encode(args)

                first_img['name'] = image_obj.name
                first_img['description'] = image_obj.description
                first_img['image_duration'] = image_obj.image_duration * 1000
                for image_id in image_ids:
                    temp_file_dict = {}
                    ad_obj = ad_image.browse(image_id)
                    temp_file_dict['file_type'] = ad_obj.file_type
                    temp_file_dict['is_youtube_url'] = ad_obj.is_youtube_url
                    if ad_obj.file_type == "image":
                        if ad_obj.image_type == 'url':
                            temp_file_dict['img_link'] = ad_obj.url
                        else:
                            temp_file_dict['img_link'] = image_url(ad_obj, 'ad_image')

                    if ad_obj.file_type == "video":
                        if ad_obj.video_type == 'url':
                            temp_file_dict['img_link'] = ad_obj.video_url
                            url_value = (ad_obj.video_url).split('/')
                            name_of_url = url_value[len(url_value) - 1]
                            temp_file_dict['name_of_url'] = name_of_url
                        else:
                            args = {
                                'id': ad_obj.id,
                                'model': ad_obj._name,
                                'filename_field': 'ad_video_fname',
                                'field': 'ad_video',
                            }
                            temp_file_dict['img_link'] = '/web/content?%s' % url_encode(args)

                    temp_file_dict['name'] = ad_obj.name
                    temp_file_dict['description'] = ad_obj.description
                    temp_file_dict['image_duration'] = ad_obj.image_duration * 1000
                    image_data.append(temp_file_dict)

            vals = {
                "first_img": first_img,
                "image_link": image_data,
                "marquee_text": config.marquee_text,
                "marquee_type": config.marquee_type,
                "marque_color": config.marque_color,
                "marque_bg_color": config.marque_bg_color,
                "marque_font_size": config.marque_font_size,
                "ac_mute_video": config.mute_video_sound,
                "ac_width": str(config.ac_width) + '%' if config.ac_width else '100%',
                "ac_height": config.ac_height,
                "ac_height_style": "height:" + str(config.ac_height) + "px",
                "ac_qrcod": config.ac_qrcod,
                "ac_qr_link": config.ac_qr_link or False,
            }
            config.customer_facing_display_html = self.env['ir.qweb']._render('point_of_sale.customer_facing_display_html', vals)

    @api.onchange('company_id')
    def _get_default_pos_team(self):
        default_sale_team = self.env.ref('sales_team.pos_sales_team', raise_if_not_found=False).sudo()
        companies = self.env['res.company'].search_read([],['name'], limit=2)
        if len(companies) == 1:
            if default_sale_team and (default_sale_team.company_id == self.company_id):
                self.crm_team_id = default_sale_team
            else:
                self.crm_team_id = self.env['crm.team'].search(['|', ('company_id', '=', self.company_id.id), ('company_id', '=', False)], limit=1)
        else:
            self.crm_team_id = self.env['crm.team'].search(['|', ('company_id', '=', self.company_id.id), ('company_id', '=', False)], limit=1)

    def open_existing_session_cb(self):
        """ close session button

        access session form to validate entries
        """
        self.ensure_one()
        pos_session_obj = self.env['pos.session']
        data_ids = [self.current_session_id.id]
        pos_session_extra = pos_session_obj.search([('id','!=',self.current_session_id.id),('config_id','=',self.id),('state','!=','closed')]).ids
        if pos_session_extra:
            data_ids+=pos_session_extra
        domain = [('id','in',data_ids)]
        view_data = {
            'name': _('Session'),
            'res_model': 'pos.session',
            'view_id': False,
            'type': 'ir.actions.act_window',
        }
        if len(data_ids) > 1:
            view_data['view_mode'] = 'tree,form'
            view_data['domain'] = domain
        else:
            view_data['view_mode'] = 'form,tree'
            view_data['res_id'] = self.current_session_id.id

        return view_data