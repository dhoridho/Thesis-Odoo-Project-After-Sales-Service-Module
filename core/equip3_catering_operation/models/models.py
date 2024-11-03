# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, date, timedelta
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.float_utils import float_round
from odoo import tools

from lxml import etree
import json as simplejson

try:
    from num2words import num2words
except ImportError:
    logging.getLogger(__name__).warning(
        "The num2words python library is not installed, l10n_mx_edi features won't be fully available.")
    num2words = None

def convert_float_time(value):
    """ Return Hour & Minute of float_time widget: used to display integral or fractional values as
        human-readable time spans (e.g. 1.5 as "01:30").
    """
    hours, minutes = divmod(abs(value) * 60, 60)
    minutes = round(minutes)
    if minutes == 60:
        minutes = 0
        hours += 1
    return hours, minutes

class CateringOrder(models.Model):
    _name = 'catering.order'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.depends('order_line.price_total')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed = amount_tax = amount_disc = 0.0
            for line in order.order_line:
                amount_untaxed += line.subtotal
                amount_tax += line.price_tax
                amount_disc += line.disc_total
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
                'discount_amt': amount_disc
            })

    name = fields.Char("Reference Number", tracking=True)
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('order', 'Catering Order'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')
    customer_id = fields.Many2one("res.partner", "Customer", tracking=True)
    partner_invoice_id = fields.Many2one(
        'res.partner', string='Invoice Address',
        readonly=True, required=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", tracking=True,)
    partner_shipping_id = fields.Many2one(
        'res.partner', string='Delivery Address', readonly=True, required=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", tracking=True,)
    start_date = fields.Date("Start Date", default=fields.Date.today, tracking=True)
    expected_date = fields.Date("Expected End Date", compute="_compute_expected_date", store=True, tracking=True)
    creation_date = fields.Date("Creation Date", default=fields.Date.today, tracking=True)
    order_date = fields.Date("Order Date", default=fields.Date.today, tracking=True)
    reference = fields.Char("Reference", tracking=True)
    order_line = fields.One2many("catering.order.line", "order_id", string="Lines", tracking=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, tracking=True)
    branch_id = fields.Many2one('res.branch', string="Branch", required=True, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)], tracking=True)
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all', tracking=5)
    amount_by_group = fields.Binary(string="Tax amount by group", compute='_amount_by_group', help="type: [(name, amount, base, formated amount, formated base)]")
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all', tracking=True)
    discount_amt = fields.Monetary(compute='_amount_all', string='- Discount', digits='Discount', store=True, readonly=True, tracking=True)
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all', tracking=4)
    margin = fields.Monetary("Margin", compute='_compute_margin', store=True, tracking=True)
    margin_percent = fields.Float("Margin (%)", compute='_compute_margin', store=True, tracking=True)
    pricelist_id = fields.Many2one(
        'product.pricelist', string='Pricelist', check_company=True,  # Unrequired company
        required=False, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", tracking=1,
        help="If you change the pricelist, only newly added lines will be affected.")
    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency', required=True,store=True, tracking=True)
    note = fields.Text('Terms and conditions', tracking=True)
    terms_conditions_id = fields.Many2one('sale.terms.and.conditions', string='Terms and Conditions', tracking=True)
    warehouse_id = fields.Many2one(comodel_name='stock.warehouse', string='Warehouse', required=True, tracking=True)
    account_tag_ids = fields.Many2many(comodel_name='account.analytic.tag', string='Analytic Group', required=True, tracking=True)
    invoice_ids = fields.One2many(comodel_name='account.move', inverse_name='catering_id', string='Invoices', tracking=True)
    invoice_count = fields.Integer(string='Invoice Count', compute="_compute_invoice_count", tracking=True)
    picking_ids = fields.One2many(comodel_name='stock.picking', inverse_name='catering_id', string='Transfers', tracking=True)
    delivery_count = fields.Integer(string='Delivery Count', compute="_compute_delivery_count", tracking=True)
    last_auto_picking_date = fields.Date(string='Last Auto Picking Date', readonly=True, copy=False, tracking=True)
    amount_to_text = fields.Char(compute='_amount_in_words',
                                 string='In Words', help="The amount in words", tracking=True)
    
    is_external_link = fields.Boolean('Is External Link', default=False)

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=True, submenu=True):
        res = super(CateringOrder, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                            submenu=submenu)
        is_external_link = self.env.context.get("default_is_external_link")
        doc = etree.XML(res['arch'])
        if is_external_link and view_type == 'form':
            for node in doc.xpath("//field"):
                modifiers = simplejson.loads(node.get("modifiers"))
                modifiers['readonly'] = True
                node.set('modifiers', simplejson.dumps(modifiers))
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

    @api.onchange('branch_id','company_id')
    def set_warehouse_id(self):
        for res in self:
            stock_warehouse = res.env['stock.warehouse'].search([('company_id', '=', res.company_id.id),('branch_id', '=', res.branch_id.id)], order="id", limit=1)
            res.warehouse_id = stock_warehouse or False

    def _get_street(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
        # reload(sys)
        # sys.setdefaultencoding("utf-8")
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_address_details(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.city:
            address = "%s" % (partner.city)
        if partner.state_id.name:
            address += ", %s" % (partner.state_id.name)
        if partner.zip:
            address += ", %s" % (partner.zip)
        if partner.country_id.name:
            address += ", %s" % (partner.country_id.name)
        # reload(sys)
        # sys.setdefaultencoding("utf-8")
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False    

    @api.depends('amount_total')
    def _amount_in_words(self):
        for obj in self:
            if obj.customer_id.lang == 'nl_NL':
                obj.amount_to_text = amount_to_text.amount_to_text_nl(
                    obj.amount_total, currency='euro')
            else:
                try:
                    if obj.customer_id.lang:
                        obj.amount_to_text = num2words(
                            obj.amount_total, lang=obj.customer_id.lang).title()
                    else:
                        obj.amount_to_text = num2words(
                            obj.amount_total, lang='en').title()
                except NotImplementedError:
                    obj.amount_to_text = num2words(
                        obj.amount_total, lang='en').title()
    @api.model
    def default_get(self,fields):
        res = super(CateringOrder, self).default_get(fields)

        res.update({
            'account_tag_ids' : self.env.user.analytic_tag_ids.ids
            })

        return res

    @api.constrains('order_line')
    def _check_order_line(self):
        for record in self:
            if not record.order_line:
                raise ValidationError(_("Can't save order because there's no product in order line!"))
    
    @api.depends('picking_ids')
    def _compute_delivery_count(self):
        for i in self:
            i.delivery_count = len(i.picking_ids)
    
    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for i in self:
            i.invoice_count = len(i.invoice_ids)
    

    @api.depends('order_line', 'start_date')
    def _compute_expected_date(self):
        for res in self:
            sub = 0
            list_hari_tambahan = []
            for line in res.order_line:
                hari_tambahan = 0
                if line.package_id and line.qty_order > 0:
                    qty_order = line.qty_order
                    starting_point = self.start_date.weekday()
                    for i in range(int(line.qty_order == 1 and 2 or line.qty_order)):
                        if starting_point == 0:
                            if qty_order:
                                if line.package_id.monday:
                                    hari_tambahan +=1
                                    qty_order -= 1
                                else:
                                    hari_tambahan +=1
                                starting_point = 1
                        if starting_point == 1:
                            if qty_order>0:
                                if line.package_id.tuesday:
                                    hari_tambahan +=1
                                    qty_order -= 1
                                else:
                                    hari_tambahan +=1
                                starting_point = 2
                        if starting_point == 2:
                            if qty_order>0:
                                if line.package_id.wednesday:
                                    hari_tambahan +=1
                                    qty_order -= 1
                                else:
                                    hari_tambahan +=1
                                starting_point = 3
                        if starting_point == 3:
                            if qty_order>0:
                                if line.package_id.thursday:
                                    hari_tambahan +=1
                                    qty_order -= 1
                                else:
                                    hari_tambahan +=1
                                starting_point = 4
                        if starting_point == 4:
                            if qty_order>0:
                                if line.package_id.friday:
                                    hari_tambahan +=1
                                    qty_order -= 1
                                else:
                                    hari_tambahan +=1
                                starting_point = 5
                        if starting_point == 5:
                            if qty_order>0:
                                if line.package_id.saturday:
                                    hari_tambahan +=1
                                    qty_order -= 1
                                else:
                                    hari_tambahan +=1
                                starting_point = 6
                        if starting_point == 6:
                            if qty_order>0:
                                if line.package_id.sunday:
                                    hari_tambahan +=1
                                    qty_order -= 1
                                else:
                                    hari_tambahan +=1
                                starting_point = 0
                list_hari_tambahan.append(hari_tambahan-1)
            
            if list_hari_tambahan:
                sub = max(list_hari_tambahan)
                if sub <0:
                    sub = 0
            res.expected_date = res.start_date + timedelta(days=sub)

    @api.onchange('terms_conditions_id')
    def _onchange_terms_conditions_id(self):
        if self.terms_conditions_id:
            self.note = self.terms_conditions_id.terms_and_conditions

    @api.depends('order_line.margin', 'amount_untaxed')
    def _compute_margin(self):
        if not all(self._ids):
            for order in self:
                order.margin = sum(order.order_line.mapped('margin'))
                order.margin_percent = order.amount_untaxed and order.margin/order.amount_untaxed
        else:
            self.env["sale.order.line"].flush(['margin'])
            # On batch records recomputation (e.g. at install), compute the margins
            # with a single read_group query for better performance.
            # This isn't done in an onchange environment because (part of) the data
            # may not be stored in database (new records or unsaved modifications).
            grouped_order_lines_data = self.env['sale.order.line'].read_group(
                [
                    ('order_id', 'in', self.ids),
                ], ['margin', 'order_id'], ['order_id'])
            mapped_data = {m['order_id'][0]: m['margin'] for m in grouped_order_lines_data}
            for order in self:
                order.margin = mapped_data.get(order.id, 0.0)
                order.margin_percent = order.amount_untaxed and order.margin/order.amount_untaxed

    @api.onchange('customer_id')
    def _onchange_partner_id(self):
        addresses = self.customer_id.address_get(['delivery', 'invoice', 'contact'])
        self.partner_shipping_id = addresses and addresses.get('delivery')
        self.partner_invoice_id = addresses and addresses.get('invoice')

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('catering.order')
        res = super(CateringOrder, self).create(vals)
        return res

    def action_confirm(self):
        for res in self:
            if res.start_date and res.start_date < fields.Date.today():
                raise ValidationError(_("Cannot confirm back date record!!"))
            res._create_invoices()
            res._create_one_week_picking(is_confirm=True)
            # for line in res.order_line:
            #     picking_id = line._create_picking()
            res.state = 'order'

    def action_cancel(self):
        for res in self:
            res.state = 'cancel'

    def action_draft(self):
        for res in self:
            res.state = 'draft'

    def action_print(self):
        return self.env.ref('equip3_catering_operation.action_report_catering_order').report_action(self)

    @api.constrains('start_date')
    def _constrains_start_date(self):
        for i in self:
            if i.start_date and i.start_date < fields.Date.today():
                raise ValidationError(_("Cannot create back date record!!"))

    def _create_one_week_picking(self,is_confirm=False):
        today = date.today()
        now = datetime.now()
        if self:
            catering_orders = self
        else:
            catering_orders = self.search([('state','=','order'),('start_date','!=',False),('expected_date','!=',False)])
        for catering in catering_orders:
            is_same_week = catering.last_auto_picking_date and today.strftime('%U') == catering.last_auto_picking_date.strftime('%U') or False
            # import pdb;pdb.set_trace()
            if not is_same_week and ((today >= catering.start_date and today <= catering.expected_date) or (is_confirm and today <= catering.expected_date)):
                sisa_hari_minggu_ini = (7-int(today.strftime('%w')))+1
                for line in catering.order_line:
                    remaining = line.qty_remaining
                    for i in range(sisa_hari_minggu_ini):
                        if remaining > 0:
                            tanggal = ((is_confirm and catering.start_date > today) and datetime.combine(catering.start_date, datetime.min.time()) or now) + timedelta(days=i)
                            jam, menit = convert_float_time(line.package_id.meal_type_id.delivery_time)
                            tanggal = tanggal.replace(hour=int(jam-7), minute=int(menit), second=0)
                            cek_menu_planner = self.env['menu.planner'].sudo().search([
                                ('planner_date','=',tanggal.date()),
                                ('package_id','=',line.package_id.id),
                            ],limit=1)
                            menu_planner = cek_menu_planner and cek_menu_planner or False
                            CustomerLineObj = self.env['customer.line']
                            if menu_planner:
                                if int(tanggal.strftime('%w')) == 0 and line.package_id.sunday:
                                    picking_id = line._create_picking(tanggal,menu_planner)
                                    customer_line_id = CustomerLineObj.create({
                                        'menu_planner_id':menu_planner.id,
                                        'partner_id':picking_id.partner_id.id,
                                        'catering_id':picking_id.catering_id.id,
                                        'picking_id':picking_id.id,
                                    })
                                    remaining -= 1
                                elif int(tanggal.strftime('%w')) == 1 and line.package_id.monday:
                                    picking_id = line._create_picking(tanggal,menu_planner)
                                    customer_line_id = CustomerLineObj.create({
                                        'menu_planner_id':menu_planner.id,
                                        'partner_id':picking_id.partner_id.id,
                                        'catering_id':picking_id.catering_id.id,
                                        'picking_id':picking_id.id,
                                    })
                                    remaining -= 1
                                elif int(tanggal.strftime('%w')) == 2 and line.package_id.tuesday:
                                    picking_id = line._create_picking(tanggal,menu_planner)
                                    customer_line_id = CustomerLineObj.create({
                                        'menu_planner_id':menu_planner.id,
                                        'partner_id':picking_id.partner_id.id,
                                        'catering_id':picking_id.catering_id.id,
                                        'picking_id':picking_id.id,
                                    })
                                    remaining -= 1
                                elif int(tanggal.strftime('%w')) == 3 and line.package_id.wednesday:
                                    picking_id = line._create_picking(tanggal,menu_planner)
                                    customer_line_id = CustomerLineObj.create({
                                        'menu_planner_id':menu_planner.id,
                                        'partner_id':picking_id.partner_id.id,
                                        'catering_id':picking_id.catering_id.id,
                                        'picking_id':picking_id.id,
                                    })
                                    remaining -= 1
                                elif int(tanggal.strftime('%w')) == 4 and line.package_id.thursday:
                                    picking_id = line._create_picking(tanggal,menu_planner)
                                    customer_line_id = CustomerLineObj.create({
                                        'menu_planner_id':menu_planner.id,
                                        'partner_id':picking_id.partner_id.id,
                                        'catering_id':picking_id.catering_id.id,
                                        'picking_id':picking_id.id,
                                    })
                                    remaining -= 1
                                elif int(tanggal.strftime('%w')) == 5 and line.package_id.friday:
                                    picking_id = line._create_picking(tanggal,menu_planner)
                                    customer_line_id = CustomerLineObj.create({
                                        'menu_planner_id':menu_planner.id,
                                        'partner_id':picking_id.partner_id.id,
                                        'catering_id':picking_id.catering_id.id,
                                        'picking_id':picking_id.id,
                                    })
                                    remaining -= 1
                                elif int(tanggal.strftime('%w')) == 6 and line.package_id.saturday:
                                    picking_id = line._create_picking(tanggal,menu_planner)
                                    customer_line_id = CustomerLineObj.create({
                                        'menu_planner_id':menu_planner.id,
                                        'partner_id':picking_id.partner_id.id,
                                        'catering_id':picking_id.catering_id.id,
                                        'picking_id':picking_id.id,
                                    })
                                    remaining -= 1
            catering.last_auto_picking_date = today
        

    
    def action_view_invoice(self):
        invoices = self.mapped('invoice_ids')
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        context = {
            'default_move_type': 'out_invoice',
        }
        if len(self) == 1:
            context.update({
                'default_partner_id': self.customer_id.id,
                'default_partner_shipping_id': self.partner_shipping_id.id,
                # 'default_invoice_payment_term_id': self.payment_term_id.id or self.partner_id.property_payment_term_id.id or self.env['account.move'].default_get(['invoice_payment_term_id']).get('invoice_payment_term_id'),
                'default_invoice_origin': self.mapped('name'),
                'default_user_id': self.env.user.id,
            })
        action['context'] = context
        return action
    
    def action_view_delivery(self):
        '''
        This function returns an action that display existing delivery orders
        of given sales order ids. It can either be a in a list or in a form
        view, if there is only one delivery order to show.
        '''
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_picking_tree_all")

        pickings = self.mapped('picking_ids')
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            form_view = [(self.env.ref('stock.view_picking_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = pickings.id
        # Prepare the context.
        picking_id = pickings.filtered(lambda l: l.picking_type_id.code == 'outgoing')
        if picking_id:
            picking_id = picking_id[0]
        else:
            picking_id = pickings[0]
        action['context'] = dict(self._context, default_partner_id=self.customer_id.id, default_picking_type_id=picking_id.picking_type_id.id, default_origin=self.name, default_group_id=picking_id.group_id.id)
        return action

    # CREATE INVOICE
    def _create_invoices(self, date=None):
        """
        Create the invoice associated to the SO.
        :param grouped: if True, invoices are grouped by SO id. If False, invoices are grouped by
                        (partner_invoice_id, currency)
        :param final: if True, refunds will be generated if necessary
        :returns: list of created invoices
        """
        if not self.env['account.move'].check_access_rights('create', False):
            try:
                self.check_access_rights('write')
                self.check_access_rule('write')
            except AccessError:
                return self.env['account.move']

        # 1) Create invoices.
        invoice_vals_list = []
        invoice_item_sequence = 0 # Incremental sequencing to keep the lines order on the invoice.
        for order in self:
            order = order.with_company(order.company_id)

            invoice_vals = order._prepare_invoice()

            invoice_line_vals = []
            for line in order.order_line:
                invoice_line_vals.append(
                    (0, 0, line._prepare_invoice_line(
                        sequence=invoice_item_sequence,
                    )),
                )
                invoice_item_sequence += 1

            invoice_vals['invoice_line_ids'] += invoice_line_vals
            invoice_vals_list.append(invoice_vals)

        if not invoice_vals_list:
            raise self._nothing_to_invoice_error()

        # 3) Create invoices.

        # As part of the invoice creation, we make sure the sequence of multiple SO do not interfere
        # in a single invoice. Example:
        # SO 1:
        # - Section A (sequence: 10)
        # - Product A (sequence: 11)
        # SO 2:
        # - Section B (sequence: 10)
        # - Product B (sequence: 11)
        #
        # If SO 1 & 2 are grouped in the same invoice, the result will be:
        # - Section A (sequence: 10)
        # - Section B (sequence: 10)
        # - Product A (sequence: 11)
        # - Product B (sequence: 11)
        #
        # Resequencing should be safe, however we resequence only if there are less invoices than
        # orders, meaning a grouping might have been done. This could also mean that only a part
        # of the selected SO are invoiceable, but resequencing in this case shouldn't be an issue.

        # Manage the creation of invoices in sudo because a salesperson must be able to generate an invoice from a
        # sale order without "billing" access rights. However, he should not be able to create an invoice from scratch.
        moves = self.env['account.move'].sudo().with_context(default_move_type='out_invoice').create(invoice_vals_list)

        # 4) Some moves might actually be refunds: convert them if the total amount is negative
        # We do this after the moves have been created since we need taxes, etc. to know if the total
        # is actually negative or not
        for move in moves:
            move.message_post_with_view('mail.message_origin_link',
                values={'self': move, 'origin': move.line_ids.mapped('sale_line_ids.order_id')},
                subtype_id=self.env.ref('mail.mt_note').id
            )
        return moves

    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()
        journal = self.env['account.move'].with_context(default_move_type='out_invoice')._get_default_journal()
        if not journal:
            raise UserError(_('Please define an accounting sales journal for the company %s (%s).') % (self.company_id.name, self.company_id.id))

        invoice_vals = {
            'ref': self.reference or '',
            'move_type': 'out_invoice',
            'narration': self.note,
            'currency_id': self.currency_id.id,
            # 'campaign_id': self.campaign_id.id,
            # 'medium_id': self.medium_id.id,
            # 'source_id': self.source_id.id,
            'invoice_user_id': self.env.user.id,
            # 'team_id': self.team_id.id,
            'partner_id': self.partner_invoice_id.id,
            'partner_shipping_id': self.partner_shipping_id.id,
            # 'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id.get_fiscal_position(self.partner_invoice_id.id)).id,
            'partner_bank_id': self.company_id.partner_id.bank_ids[:1].id,
            'journal_id': journal.id,  # company comes from the journal
            'invoice_origin': self.name,
            # 'invoice_payment_term_id': self.payment_term_id.id,
            'payment_reference': self.reference,
            # 'transaction_ids': [(6, 0, self.transaction_ids.ids)],
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
            'catering_id':self.id,
            'branch_id': self.branch_id.id
        }
        return invoice_vals


class CateringOrderLine(models.Model):
    _name = 'catering.order.line'

    order_id = fields.Many2one("catering.order", "Catering")
    package_id = fields.Many2one("product.product", string="Package Product", required=True)
    product_tmpl_id = fields.Many2one("product.template", compute='compute_product_template', store=True)
    unit_price = fields.Float("Unit Price")
    qty_order = fields.Float("Qty Order", compute="_compute_qty_order", store=True)
    qty_delivered = fields.Float("Qty Delivered", compute="_compute_qty_delivered", store=True)
    qty_remaining = fields.Float("Qty Remaining", compute="_compute_qty_remaining", store=True)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure')
    taxes_id = fields.Many2many('account.tax', string='Taxes')
    disc = fields.Float(string='Discount (%)', digits='Discount', default=0.0)
    subtotal = fields.Float("Subtotal", compute='_compute_amount', store=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    margin = fields.Float(
        "Margin", compute='_compute_margin',
        digits='Product Price', store=True, groups="base.group_user")
    margin_percent = fields.Float(
        "Margin (%)", compute='_compute_margin', store=True, groups="base.group_user")
    purchase_price = fields.Float(
        string='Cost', compute="_compute_purchase_price",
        digits='Product Price', store=True, readonly=False,
        groups="base.group_user")
    currency_id = fields.Many2one(related='order_id.currency_id', depends=['order_id.currency_id'], store=True, string='Currency', readonly=True)
    price_tax = fields.Float(compute='_compute_amount', string='Total Tax', readonly=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', readonly=True, store=True)
    disc_total = fields.Monetary(compute='_compute_amount', string='Total Disc', readonly=True, store=True)
    picking_ids = fields.One2many(comodel_name='stock.picking', inverse_name='catering_line_id', string='Transfers')
    subscription_id = fields.Many2one('catering.subscription', 'Qty Order', required=True)

    qty_invoiced = fields.Float('Qty Invoiced', compute='_get_qty_invoiced', store=True)
    qty_to_invoice = fields.Float('Qty to Invoice', compute='_get_qty_invoiced', store=True)
    untaxed_amount_invoiced = fields.Float('Untaxed Amount Invoiced', compute='_compute_amount', store=True)
    untaxed_amount_to_invoice = fields.Float('Untaxed Amount To Invoice', compute='_compute_amount', store=True)
    untaxed_total = fields.Float('Untaxed Total', compute='_compute_amount', store=True)
    creation_date = fields.Date("Creation Date", default=fields.Date.today)
    warehouse_id = fields.Many2one(comodel_name='stock.warehouse', related='order_id.warehouse_id', store=True)
    branch_id = fields.Many2one('res.branch', string="Branch", related='order_id.branch_id', store=True)
    is_external_link = fields.Boolean('Is External Link', default=False)

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=True, submenu=True):
        res = super(CateringOrderLine, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                            submenu=submenu)
        is_external_link = self.env.context.get("default_is_external_link")
        doc = etree.XML(res['arch'])
        if is_external_link and view_type == 'form':
            for node in doc.xpath("//field"):
                modifiers = simplejson.loads(node.get("modifiers"))
                modifiers['readonly'] = True
                node.set('modifiers', simplejson.dumps(modifiers))
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

    def name_adjust(self):

        print("$$$$$$$$$$$$$$$",self.package_id.name_get())


    def _get_qty_invoiced(self):
        for record in self:
            invoice_line = self.env['account.move.line'].search([('catering_id', 'in', record.order_id.ids),('product_id', '=', record.package_id.id)])
            if invoice_line:
                record.qty_invoiced = sum(invoice_line.mapped('quantity'))
                record.qty_to_invoice = record.qty_order - record.qty_invoiced
            else:
                record.qty_invoiced = 0
                record.qty_to_invoice = 0

    @api.depends('package_id')
    def compute_product_template(self):
        for rec in self:
            if rec.package_id:
                rec.product_tmpl_id = rec.package_id.product_tmpl_id
            else:
                rec.product_tmpl_id = False

    @api.depends('picking_ids','picking_ids.state')
    def _compute_qty_delivered(self):   
        for i in self:
            i.qty_delivered = len(i.picking_ids.filtered(lambda x: x.state == 'done')) 

    @api.depends('package_id', 'company_id', 'currency_id', 'product_uom')
    def _compute_purchase_price(self):
        for line in self:
            if not line.package_id:
                line.purchase_price = 0.0
                continue
            line = line.with_company(line.company_id)
            product = line.package_id
            product_cost = product.standard_price
            if not product_cost:
                # If the standard_price is 0
                # Avoid unnecessary computations
                # and currency conversions
                if not line.purchase_price:
                    line.purchase_price = 0.0
                continue
            fro_cur = product.cost_currency_id
            to_cur = line.currency_id or line.order_id.currency_id
            if line.product_uom and line.product_uom != product.uom_id:
                product_cost = product.uom_id._compute_price(
                    product_cost,
                    line.product_uom,
                )
            line.purchase_price = fro_cur._convert(
                from_amount=product_cost,
                to_currency=to_cur,
                company=line.company_id or self.env.company,
                date=line.order_id.order_date or fields.Date.today(),
            ) if to_cur and product_cost else product_cost
            # The pricelist may not have been set, therefore no conversion
            # is needed because we don't know the target currency..

    @api.depends('subtotal', 'qty_order', 'purchase_price')
    def _compute_margin(self):
        for line in self:
            line.margin = line.subtotal - (line.purchase_price * line.qty_order)
            line.margin_percent = line.subtotal and line.margin/line.subtotal

    @api.onchange('package_id')
    def set_line(self):
        for res in self:
            if res.package_id:
                res.write({
                    'unit_price': res.package_id.lst_price,
                    'taxes_id': res.package_id.taxes_id,
                })


    @api.depends('package_id','unit_price','taxes_id','disc','qty_order','qty_invoiced','qty_to_invoice')
    def _compute_amount(self):
        for line in self:
            price = line.unit_price * (1 - (line.disc or 0.0) / 100.0)
            taxes_invoiced = line.taxes_id.compute_all(price, line.order_id.currency_id, 1, product=line.package_id, partner=line.order_id.partner_shipping_id)
            taxes_to_invoice = line.taxes_id.compute_all(price, line.order_id.currency_id, 1, product=line.package_id, partner=line.order_id.partner_shipping_id)
            taxes = line.taxes_id.compute_all(price, line.order_id.currency_id, 1, product=line.package_id, partner=line.order_id.partner_shipping_id)
            disc_total = (line.unit_price) - taxes['total_excluded']
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'subtotal': taxes['total_excluded'],
                'disc_total': disc_total,
                'untaxed_amount_invoiced': taxes_invoiced['total_excluded'],
                'untaxed_amount_to_invoice': taxes_to_invoice['total_excluded'],
                'untaxed_total': taxes['total_included']
            })
            if self.env.context.get('import_file', False) and not self.env.user.user_has_groups('account.group_account_manager'):
                line.tax_id.invalidate_cache(['invoice_repartition_line_ids'], [line.taxes_id.id])

    @api.depends('subscription_id')
    def _compute_qty_order(self):
        for i in self:
            qty = 0.0
            price = 0.0
            if i.subscription_id:
                qty = float(i.subscription_id.duration)
                price = float(i.subscription_id.price)
            i.qty_order = qty
            i.unit_price = price
    
    @api.depends('qty_order','qty_delivered')
    def _compute_qty_remaining(self):
        for i in self:
            i.qty_remaining = i.qty_order - i.qty_delivered

    def _prepare_invoice_line(self, **optional_values):
        """
        Prepare the dict of values to create the new invoice line for a sales order line.

        :param qty: float quantity to invoice
        :param optional_values: any parameter that should be added to the returned invoice line
        """
        self.ensure_one()
        res = {
            # 'display_type': self.display_type,
            # 'sequence': self.sequence,
            'name': self.package_id.display_name,
            'product_id': self.package_id.id,
            # 'product_uom_id': self.product_uom.id,
            'quantity': 1,
            'discount': self.disc,
            'price_unit': self.unit_price,
            'tax_ids': [(6, 0, self.taxes_id.ids)],
            # 'analytic_account_id': self.order_id.analytic_account_id.id,
            # 'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
            # 'sale_line_ids': [(4, self.id)],
        }
        if optional_values:
            res.update(optional_values)
        # if self.display_type:
        #     res['account_id'] = False
        return res

    # CREATE PICKING PER LINE
    def _create_picking(self, tanggal, menu_planner=False):
        self.ensure_one()
        picking_vals = self._prepare_picking(tanggal,menu_planner)
        picking_id = self.env['stock.picking'].create(picking_vals)
        return picking_id

    def _prepare_picking(self,tanggal,menu_planner=False):
        self.ensure_one()
        order = self.order_id
        picking_type_id = self.env['stock.picking.type'].search([('warehouse_id','=',order.warehouse_id.id),('code','=','outgoing')],limit=1)
        if not picking_type_id:
            raise ValidationError(_("No Delivery Operation for this warehouse!!!"))

        picking_lines = []
        if menu_planner:
            for menu_line in menu_planner.line_ids:
                vals_line = {
                    'product_id':menu_line.menu_id.id,
                    'name':menu_line.desc,
                    'product_uom_qty':menu_line.quantity,
                    'product_uom':menu_line.uom_id.id,
                }
                picking_lines.append((0,0,vals_line))
        else:
            vals_line = {
                'product_id':self.package_id.id,
                'name':self.package_id.display_name,
                'product_uom_qty':1,
                'product_uom':self.package_id.uom_id.id,
            }
            picking_lines.append((0,0,vals_line))
        picking_vals = {
            'partner_id':order.partner_shipping_id.id,
            'picking_type_id':picking_type_id.id,
            'analytic_account_group_ids':[(6,0,order.account_tag_ids.ids)],
            'scheduled_date':tanggal,
            'date_deadline':tanggal,
            'origin':order.name,
            'company_id':order.company_id.id,
            'location_id':order.warehouse_id.lot_stock_id.id,
            'location_dest_id':order.env['stock.location'].sudo().search([('usage','=','customer')],limit=1,order="id asc").id,
            'catering_id':order.id,
            'catering_line_id':self.id,
            'move_ids_without_package':picking_lines,
            'branch_id': self.branch_id.id
        }
        return picking_vals
    

    
class CateringTerms(models.Model):
    _inherit = 'sale.terms.and.conditions'

    is_external_link = fields.Boolean('Is External Link', default=False)

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=True, submenu=True):
        res = super(CateringTerms, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                      submenu=submenu)
        is_external_link = self.env.context.get("default_is_external_link")
        doc = etree.XML(res['arch'])
        if is_external_link and view_type == 'form':
            for node in doc.xpath("//field"):
                modifiers = simplejson.loads(node.get("modifiers"))
                modifiers['readonly'] = True
                node.set('modifiers', simplejson.dumps(modifiers))
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res
    
class CateringCurrency(models.Model):
    _inherit = 'res.currency'

    is_external_link = fields.Boolean('Is External Link', default=False)

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=True, submenu=True):
        res = super(CateringCurrency, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                      submenu=submenu)
        is_external_link = self.env.context.get("default_is_external_link")
        doc = etree.XML(res['arch'])
        if is_external_link and view_type == 'form':
            for node in doc.xpath("//field"):
                modifiers = simplejson.loads(node.get("modifiers"))
                modifiers['readonly'] = True
                node.set('modifiers', simplejson.dumps(modifiers))
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res
    
class CateringWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    is_external_link = fields.Boolean('Is External Link', default=False)

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=True, submenu=True):
        res = super(CateringWarehouse, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                      submenu=submenu)
        is_external_link = self.env.context.get("default_is_external_link")
        doc = etree.XML(res['arch'])
        if is_external_link and view_type == 'form':
            for node in doc.xpath("//field"):
                modifiers = simplejson.loads(node.get("modifiers"))
                modifiers['readonly'] = True
                node.set('modifiers', simplejson.dumps(modifiers))
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res
    
class CateringSubs(models.Model):
    _inherit = 'catering.subscription'

    is_external_link = fields.Boolean('Is External Link', default=False)

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=True, submenu=True):
        res = super(CateringSubs, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                      submenu=submenu)
        is_external_link = self.env.context.get("default_is_external_link")
        doc = etree.XML(res['arch'])
        if is_external_link and view_type == 'form':
            for node in doc.xpath("//field"):
                modifiers = simplejson.loads(node.get("modifiers"))
                modifiers['readonly'] = True
                node.set('modifiers', simplejson.dumps(modifiers))
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res
    
class CateringProduct(models.Model):
    _inherit = 'product.product'

    is_external_link = fields.Boolean('Is External Link', default=False)

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=True, submenu=True):
        res = super(CateringProduct, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                      submenu=submenu)
        is_external_link = self.env.context.get("default_is_external_link")
        doc = etree.XML(res['arch'])
        if is_external_link and view_type == 'form':
            for node in doc.xpath("//field"):
                modifiers = simplejson.loads(node.get("modifiers"))
                modifiers['readonly'] = True
                node.set('modifiers', simplejson.dumps(modifiers))
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res