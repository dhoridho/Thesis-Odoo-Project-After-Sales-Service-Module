from odoo import fields, models, api
import time
import datetime
from datetime import datetime, timedelta
from odoo.tools import config
from odoo.addons import decimal_precision as dp
from odoo.tools.translate import _
# from dateutil import relativedelta
import calendar
from odoo import exceptions, _
from odoo.exceptions import Warning
from odoo.exceptions import except_orm, UserError
from dateutil.relativedelta import relativedelta


# @api.multi
def get_price(self, pricelist_ids, price):
    price_amt = 0.0
    pricelist_item_ids = []
    if self._context is None:
        self._context = {}

    date = time.strftime('%Y-%m-%d')
    if 'date' in self._context:
        date = self._context['date']

    currency_obj = self.env['res.currency']
    product_pricelist_version_obj = self.env['product.pricelist.item']
    user_browse = self.env['res.users'].browse()
    company_obj = self.env['res.company']
    company_id = company_obj.browse(user_browse.company_id.id)
    #    print company_id.currency_id.id ,"company_idccccc"
    pricelist_obj = self.env['product.pricelist'].browse(pricelist_ids)
    if pricelist_ids:
        pricelist_item_ids.append(pricelist_ids)
        pricelist_obj = self.env['product.pricelist'].browse(pricelist_ids)

    pricelist_item_ids = list(set(pricelist_item_ids))
    plversions_search_args = [
        ('pricelist_id', 'in', pricelist_item_ids),
        '|',
        ('date_start', '=', False),
        ('date_start', '<=', date),
        '|',
        ('date_end', '=', False),
        ('date_end', '>=', date),
    ]

    plversion_ids = product_pricelist_version_obj.search(
        plversions_search_args)

    # print("\n\n\n plversion_ids ==== ", plversion_ids)

    if not plversion_ids:
        msg = "At least one pricelist item has not declared !\nPlease create pricelist item."
        #         raise osv.except_osv(_('Warning !'), _(msg))
        raise exceptions.except_orm(_('Warning !'), _(msg))

    self._cr.execute(
        'SELECT i.* '
        'FROM product_pricelist_item AS i '
        'WHERE id = ' + str(plversion_ids[0].id) + '')

    res1 = self._cr.dictfetchall()
    if pricelist_obj:
        price = currency_obj.compute(price, pricelist_obj.currency_id, round)
    for res in res1:
        if res:
            price_limit = price
            x = (1.0 + (res['price_discount'] or 0.0))
            price = price * (1.0 + (res['price_discount'] or 0.0))
            price += (res['price_surcharge'] or 0.0)
            if res['price_min_margin']:
                price = max(price, price_limit + res['price_min_margin'])
            if res['price_max_margin']:
                price = min(price, price_limit + res['price_max_margin'])
            break

    price_amt = price
    return price_amt


class CrmLead2OpportunityPartner(models.TransientModel):
    _inherit = 'crm.lead2opportunity.partner'
    _description = 'Lead To Opportunity Partner'

    @api.model
    def default_get(self, fields):
        """
        Default get for name, opportunity_ids.
        If there is an exisitng partner link to the lead, find all existing
        opportunities links with this partner to merge all information together
        """
        res = {}
        if 'action' in fields:
            res.update({'action': 'create'})
        if 'name' in fields:
            res.update({'name': 'convert'})
        return res

    # @api.multi
    @api.model
    def action_apply(self):
        """
        Convert lead to opportunity or merge lead and opportunity and open
        the freshly created opportunity view.
        """
        print("CONTEXT==>>>>>>>>>",self._context)
        if self._context is None:
            self._context = {}
        if 'banquet_id' in self._context:
            banq_browse = self.env['banquet.quotation'].browse(
                self._context['banquet_id'])

            ctx = dict(self._context)
            ctx['active_id'] = banq_browse.lead.id
            ctx['active_ids'] = [banq_browse.lead.id]

        #             self._context.update({'active_id' :banq_browse.lead.id,'active_ids':[banq_browse.lead.id]})
        #         lead = self.env['crm.lead'].browse(self._context.get('active_ids'))[0]
        lead = self.env['crm.lead'].browse(ctx['active_id'])
        #         lead_ids = self._context.get('active_ids', [])
        lead_ids = ctx['active_ids']
        self._convert_opportunity({'lead_ids': lead_ids})
        return lead.redirect_lead_opportunity_view()


class CrmLead(models.Model):
    _name = 'crm.lead'
    _inherit = 'crm.lead'
    _description = 'User Modification'

    via = fields.Selection(
        [('direct', 'Direct'), ('agent', 'Agent')], 'Via', default=lambda *a: 'direct')
    agent_id = fields.Many2one('res.partner', 'Agent')
    lead_sequence = fields.Char('Lead Number',  readonly=True)
    banquets_ids = fields.One2many(
        'banquet.quotation.lead.history', 'ref_id', 'Banquet Quotation History')
    shop_id = fields.Many2one('sale.shop', 'Shop', required=True,
                              help="Will show only open leads for the selected shop.")

    # @api.multi
    def name_get(self):
        if not len(self._ids):
            return []
        res = [(r['id'], r['lead_sequence'])
               for r in self.read(fields=['lead_sequence'])]
        return res

    @api.model
    def create(self, vals):
        # function overwrites create method and auto generate request no.
        req_no = self.env['ir.sequence'].next_by_code('crm.lead') or 'New'
        vals['lead_sequence'] = req_no
        return super(CrmLead, self).create(vals)

    # @api.one
    def unlink(self):
        """
        Allows to delete lead which are created once
        """
        for rec in self.browse():
            raise exceptions.except_orm(
                _('Invalid action !'), _('Cannot delete these Lead.!'))
        return super(CrmLead, self).unlink()

    @api.onchange('shop_id')
    def on_change_shop_id(self):
        if not self.shop_id:
            return {'value': {}}
        temp = self.env['sale.shop'].browse(self.shop_id.id)
        return {'value': {'company_id': temp.company_id.id}}


class DepositPaymentPolicy(models.Model):
    _name = "deposit.payment.policy"
    _description = "Deposit Payment Policy"

    start_date = fields.Date("From Date", required=True)
    name = fields.Char('Policy Name',  required=True)
    percentage = fields.Float("Percentage", required=True)
    min_amount = fields.Float("Minimum Deposit Amount", required=True)
    shop_id = fields.Many2one('sale.shop', 'Shop', required=True,
                              help="Will show list of shop that belongs to allowed companies of logged-in user. \n -Assign a shop to configure shop-wise deposit  policy.")
    company_id = fields.Many2one(
        related='shop_id.company_id',  string='Company', store=True)

    # _sql_constraints = [
    #     ('policy_name_uniq', 'unique(name,shop_id)',
    #      'Policy Name must be unique for selected shop !'),
    #     ('start_date_uniq', 'unique(start_date,shop_id)',
    #      'Start Date must be unique for selected shop !')
    # ]


class ThemePlan(models.Model):
    _name = "theme.plan"
    _description = "Theme Plan"

    name = fields.Char('Theme Name',  required=True)
    code = fields.Char('Code')

    # _sql_constraints = [
    #     ('theme_name_uniq', 'unique(name)', 'Theme Name must be unique !'),
    # ]


class SeatingPlan(models.Model):
    _name = "seating.plan"
    _description = "Seating Plan"

    name = fields.Char('Name', required=True)
    code = fields.Char('Code')

    # _sql_constraints = [
    #     ('theme_name_uniq', 'unique(name)', 'Seating Name must be unique !'),
    # ]


class BanquetQuotation(models.Model):
    _name = "banquet.quotation"
    _description = "Banquet Quotation"

    # @api.one
    def unlink(self):
        """
        Allows to delete Product Category which are not defined in demo data
        """
        for rec in self.browse():
            raise exceptions.except_orm(_('Invalid action !'), _(
                'Cannot delete these Quotation.!'))
        #             raise osv.except_osv(_('Invalid action !'), _('Cannot delete these Quotation.!'))
        return super(BanquetQuotation, self).unlink()

    @api.onchange('pricelist_id')
    @api.depends('room_ids', 'food_items_ids', 'other_items_ids')
    def onchange_pricelist_id(self):
        # print("clean::::::::::::::::::;")
        if not self.pricelist_id:
            return {}
        temp = 0
        if self.pricelist_id:
            if not self.room_ids == [(6, 0, [])] and len(self.room_ids) != 1:
                temp = 1
            if not self.food_items_ids == [(6, 0, [])] and len(self.food_items_ids) != 1:
                temp = 1
            if not self.other_items_ids == [(6, 0, [])] and len(self.other_items_ids) != 1:
                temp = 1
        if temp == 0:
            return {}

        # print("self.pricelist_id:::::::::::::::::::", self.pricelist_id)
        # warning = {
        #     'title': _('Pricelist Warning!'),
        #     'message': _('If you change the pricelist of this order (and eventually the currency), prices of existing order lines will not be updated.')
        # }

    @api.model
    def create(self, vals):
        # function overwrites create method and auto generate request no.
        req_no = self.env['ir.sequence'].next_by_code(
            'banquet.quotation') or 'New'
        vals['name'] = req_no
        lead_browse = self.env['crm.lead'].browse(vals['lead'])
        if (not lead_browse.email_from) and 'email_id' in vals and vals['email_id']:
            lead_browse.write({'email_from': vals['email_id']})
        if (not lead_browse.mobile) and 'mobile' in vals and vals['mobile']:
            lead_browse.write({'mobile': vals['mobile']})
        if (not lead_browse.contact_name) and 'contact_name' in vals and vals['contact_name']:
            lead_browse.write({'contact_name': vals['contact_name']})
        return super(BanquetQuotation, self).create(vals)

    def _get_total_amt_pur(self):
        # print("666666666666")
        res = {}
        for obj in self:
            # print("obj.pur_untax_amt:::::::::::::;", obj.pur_untax_amt)
            obj.pur_total_amt = obj.pur_untax_amt + obj.pur_tax_amt

    # @api.multi
    def _amount_line_tax_pur(self, line):
        val = 0.0
        taxes = line.pur_tax_ids.compute_all(
            line.cost_price_unit * (1 - (line.discount or 0.0) / 100.0), None, 1)
        val = taxes['total_included'] - taxes['total_excluded']
        return val

    # @api.multi
    def _amount_line_tax_pur_food_other(self, line):
        val = 0.0
        taxes = line.pur_tax_ids.compute_all(
            line.cost_price_unit * (1 - (line.discount or 0.0) / 100.0), None, 1)
        val = taxes['total_included'] - taxes['total_excluded']
        return val

    def _get_tax_amt_pur(self):
        res = {}
        total = 0.00
        val = 0.00
        cur_obj = self.env['res.currency']
        res_user = self.env['res.users']
        for obj in self:
            user_id = res_user.browse()
            cur = user_id.company_id.currency_id
            for line in obj.room_ids:
                val += self._amount_line_tax_pur(line)
            for line in obj.food_items_ids:
                val += self._amount_line_tax_pur_food_other(line)
            for line in obj.other_items_ids:
                val += self._amount_line_tax_pur_food_other(line)
            #             res[obj.id] = cur_obj.round(val)
            obj.update({
                'pur_tax_amt': val,
            })

    #         return res

    def _get_untax_amt_pur(self):
        res = {}
        total = 0.00
        for obj in self:
            for service in obj.room_ids:
                total += service.cost_price_subtotal
            for food in obj.food_items_ids:
                total += food.cost_price_subtotal
            for other in obj.other_items_ids:
                total += other.cost_price_subtotal
            #             res[obj.id] = total
            obj.pur_untax_amt = total
            # print("obj:::::::::::", obj.pur_untax_amt)

    #         return res

    def _get_total_amt_sale(self):
        res = {}
        for obj in self:
            obj.sale_total_amt = obj.sale_untax_amt + obj.sale_tax_amt

    #         return res

    # @api.multi
    def _amount_line_tax(self, line):
        val = 0.0
        taxes = line.taxes_id.compute_all(
            line.price * (1 - (line.discount or 0.0) / 100.0), None, line.number_of_days)
        # print("RESERVATION LINE===>>>>", taxes)
        val = taxes['total_included'] - taxes['total_excluded']
        return val

    # @api.multi
    def _amount_food_tax(self, line):
        val = 0.0
        taxes = line.tax_id.compute_all(
            line.price_subtotal * (1 - (line.discount or 0.0) / 100.0), None, 1)
        val = taxes['total_included'] - taxes['total_excluded']
        return val

    # @api.multi
    def _amount_other_tax(self, line):
        val = 0.0
        taxes = line.tax_id.compute_all(
            line.price_subtotal * (1 - (line.discount or 0.0) / 100.0), None, 1)
        val = taxes['total_included'] - taxes['total_excluded']
        return val

    def _get_tax_amt_sale(self):
        res = {}
        val = 0.00
        cur_obj = self.env['res.currency']
        res_user = self.env['res.users']
        for obj in self:
            user_id = res_user.browse()
            cur = user_id.company_id.currency_id
            for line in obj.room_ids:
                val += self._amount_line_tax(line)
            for line in obj.food_items_ids:
                val += self._amount_food_tax(line)
            for line in obj.other_items_ids:
                val += self._amount_other_tax(line)
            #             res[obj.id] = cur_obj.round(val)
            obj.update({
                'sale_tax_amt': val,
            })

    #         return res

    def _get_untax_amt_sale(self):
        res = {}
        total = 0.00
        for obj in self:
            for service in obj.room_ids:
                total += service.sub_total1
            for food in obj.food_items_ids:
                total += food.price_subtotal
            for other in obj.other_items_ids:
                total += other.price_subtotal
            obj.update({
                'sale_untax_amt': total,
            })

    #             res[obj.id] = total
    #         return res

    # @api.multi
    def count_total_rooms(self):
        res = {}
        for obj in self:
            count1 = 0
            for line in obj.room_ids:
                count1 += 1
        self.number_of_rooms = count1

    def count_total_days(self):
        for obj in self:
            if obj.company_id.id == self.env.user.company_id.id:
                policy_obj = self.env['checkout.configuration'].search(
                    [('shop_id', '=', obj.line_id.shop_id.id)])
                if not policy_obj:
                    # print('_________________2', obj.line_id.shop_id.name)
                    raise UserError(
                        'Configuration Error! Checkout policy is not define for selected shop.')
                policy_browse = self.env['checkout.configuration'].browse(
                    policy_obj.id)
                check_in = obj.checkin_date
                check_out = obj.checkout_date
                day_count1 = (check_out - check_in).days + 1
                if not policy_browse[0].name == '24hour':
                    wd_count = 0
                    time_con = str(policy_browse[0].time)
                    check_out_cons = obj.checkin_date + ' ' + time_con + ':00:00'
                    for count in range(0, (int(day_count1))):
                        single_date = check_in + relativedelta(days=count)
                        if str(single_date)[0:10] == obj.checkin_date[0:10]:
                            time_con = str(policy_browse[0].time)
                            check_out_cons = obj.checkin_date + ' ' + time_con + ':00:00'

                            if obj.checkin_date < check_out_cons:
                                wd_count += 1
                            if obj.checkout_date > check_out_cons:
                                wd_count += 1
                        elif str(single_date)[0:10] == obj.checkout_date[0:10]:
                            time_con = str(policy_browse[0].time)
                            check_out_cons = obj.checkout_date[0:10] + \
                                ' ' + time_con + ':00:00'
                            if obj.checkout_date > check_out_cons:
                                wd_count += 1
                        if (str(single_date)[0:10] != obj.checkin_date[0:10]) and (
                                str(single_date)[0:10] != obj.checkout_date[0:10]):
                            time_con = str(policy_browse[0].time)
                            check_out_cons = obj.checkin_date[0:10] + \
                                ' ' + time_con + ':00:00'
                            if obj.checkout_date > check_out_cons:
                                wd_count += 1
                    day_count1 = wd_count
                else:
                    day_count = (check_out - check_in).days
                    time_in = obj.checkin_date
                    time_out = obj.checkout_date
                    time_count1 = (time_out - time_in)
                    if time_count1 > 0:
                        day_count += 1
                    day_count1 = round(day_count)
                obj.update({
                    'number_of_days': day_count1
                })

    @api.model
    def _get_default_shop(self):
        user = self.env['res.users'].browse(self._uid)
        company_id = user.company_id.id
        shop_ids = self.env['sale.shop'].search(
            [('company_id', '=', company_id)])
        if not shop_ids:
            raise exceptions.except_orm(_('Error!'), _(
                'There is no default shop for the current user\'s company!'))
        return shop_ids[0]

    @api.onchange('shop_id')
    def onchange_shop_id(self):
        v = {}
        if self.shop_id:
            shop = self.env['sale.shop'].browse(self.shop_id.id)
            if shop.pricelist_id:
                v['pricelist_id'] = shop.pricelist_id.id
        return {'value': v}

    name = fields.Char("Quotation No.",  readonly=True)
    current_date = fields.Date("Enquiry Date", required=True, readonly=True, states={
        'draft': [('readonly', False)]}, default=time.strftime('%Y-%m-%d'))
    lead = fields.Many2one('crm.lead', 'Lead', required=True, readonly=True, states={
        'draft': [('readonly', False)]}, )
    contact_name = fields.Char('Contact Name', readonly=True, states={
                               'draft': [('readonly', False)]}, )
    address = fields.Char('Address',  readonly=True, states={
                          'draft': [('readonly', False)]}, )
    email_id = fields.Char('Email Id', readonly=True, states={
                           'draft': [('readonly', False)]}, )
    #                'tour_name':fields.char('Banquet Name',readonly=True, states={'draft': [('readonly', False)]},),
    mobile = fields.Char('Mobile Number', required=True, readonly=True,
                         states={'draft': [('readonly', False)]}, )
    adult = fields.Integer("Adult Persons", readonly=True, states={
                           'draft': [('readonly', False)]}, )
    child = fields.Integer("Child", readonly=True, states={
                           'draft': [('readonly', False)]}, )
    checkin_date = fields.Datetime("Prefer start Date", required=True, readonly=True,
                                   states={'draft': [('readonly', False)]})
    checkout_date = fields.Datetime("Prefer End Date", required=True, readonly=True,
                                    states={'draft': [('readonly', False)]}, )
    via = fields.Selection([('direct', 'Direct'), ('agent', 'Agent')], "Via", readonly=True, states={
        'draft': [('readonly', False)]}, default='direct')
    agent_id = fields.Many2one('res.partner', 'Agent', readonly=True, states={
                               'draft': [('readonly', False)]}, )
    room_ids = fields.One2many('hotel.reservation.line', 'banquet_id',
                               'Room Details', readonly=True, states={'draft': [('readonly', False)]}, )
    food_items_ids = fields.One2many('food.items', 'banquet_id', 'Food Items')
    other_items_ids = fields.One2many(
        'other.items', 'banquet_id', 'Other Items')
    number_of_days = fields.Integer(compute='count_total_days', string="Number Of Days",
                                     default=1,
                                    help="Shall be computed based on check out policy configured for selected shop.")
    number_of_rooms = fields.Integer(
        compute='count_total_rooms', string="Number Of Rooms")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('send_to', 'Sent To Customer'),
        ('approve', 'Approved'),
        #                        ('create_tour', 'Create Banquet Booking'),
        ('done', 'Done'),
        ('refused', 'Refused'),
    ], 'Status', default='draft')  # ,readonly=True),

    theme_id = fields.Many2one('theme.plan', 'Theme', required=True, readonly=True, states={
        'draft': [('readonly', False)]}, )
    board_toread = fields.Char("Board to Read", readonly=True, states={
        'draft': [('readonly', False)]}, )
    seating_id = fields.Many2one('seating.plan', 'Seating Plan', required=True, readonly=True, states={
        'draft': [('readonly', False)]}, )
    sale_untax_amt = fields.Float(
        compute='_get_untax_amt_sale', string="Sale Untaxed Amount")
    sale_tax_amt = fields.Float(
        compute='_get_tax_amt_sale', string="Sale Taxes ")
    pur_untax_amt = fields.Float(
        compute='_get_untax_amt_pur', string="Purchase Untaxed Amount")
    pur_tax_amt = fields.Float(
        compute='_get_tax_amt_pur', string="Purchase Taxes ")
    sale_total_amt = fields.Float(
        compute='_get_total_amt_sale', string="Sale Total Amount")
    pur_total_amt = fields.Float(
        compute='_get_total_amt_pur', string="Purchase Total Amount")
    deposit_policy = fields.Selection([('percentage', 'Deposit Percentage'), ('no_deposit', 'No Deposit')],
                                      'Deposit Policy', required=True, readonly=True,
                                      states={'draft': [('readonly', False)]}, default='no_deposit')
    percentage = fields.Float("Percentage/Deposit Amount",
                              readonly=True, states={'draft': [('readonly', False)]}, )
    min_dep_amount = fields.Float("Minimum Deposit Amount", readonly=True, states={
                                  'draft': [('readonly', False)]}, )
    invoiced = fields.Boolean('Invoiced', default=False)
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist', required=True, readonly=True,
                                   states={'draft': [('readonly', False)]})
    shop_id = fields.Many2one('sale.shop', 'Shop', required=True, readonly=True, states={'draft': [(
        'readonly', False)]}, default=_get_default_shop,
        help="Will show list of shop that belongs to allowed companies of logged-in user.")
    company_id = fields.Many2one(
        related='shop_id.company_id',  string='Company', store=True)

    # _sql_constraints = [
    #     ('check_in_out_dates', 'CHECK (checkin_date<=checkout_date)',
    #      'Prefer start Date Should be lesser than the Prefer End Date!'),
    # ]

    @api.onchange('lead')
    def on_change_lead_id(self):
        result = {}
        if self.lead:
            res = self.env['crm.lead'].browse(self.lead.id)
            address = ''
            if res.street:
                address += res.street + ' '
            if res.street2:
                address += res.street2 + ' '
            if res.city:
                address += res.city + ' '
            if res.zip:
                address += res.zip
            result['address'] = address
            result['contact_name'] = res.contact_name
            result['mobile'] = res.mobile
            result['email_id'] = res.email_from
            result['via'] = res.via
            result['agent_id'] = res.agent_id.id
        return {'value': result}

    @api.onchange('shop_id', 'checkin_date', 'checkout_date')
    def on_change_checkout(self):
        #         self.checkin_date =time.strftime('%Y-%m-%d %H:%M:%S')
        #         self.checkout_date=time.strftime('%Y-%m-%d %H:%M:%S')
        val = {}
        if not self.shop_id:
            raise Warning('Shop is not selected.')
        #             raise exceptions.except_orm('Warning', 'Shop is not selected.')

        if not self.checkout_date:
            self.checkout_date = time.strftime('%Y-%m-%d %H:%M:%S')
        if self.checkin_date and self.shop_id.id:
            new_date = str(self.checkin_date)
            self._cr.execute(
                'select max(start_date) from deposit_payment_policy where start_date <= %s and shop_id = %s',
                (new_date, self.shop_id.id,))
            a = self._cr.fetchone()
            if not a[0]:
                raise Warning('Deposit policy is not define.')
            #                 raise exceptions.except_orm('Configuration Error', 'Deposit policy is not define.')
            pay_obj = self.env['deposit.payment.policy'].search(
                [('start_date', '=', a[0])])
            val = {'value': {
                'percentage': pay_obj.percentage, 'min_dep_amount': pay_obj.min_amount}}
        return val

    def compute(self):
        res = {}
        total = 0.00
        val = 0.00
        pur_total = 0.00
        pur_val = 0.00
        cur_obj = self.env['res.currency']
        res_user = self.env['res.users']
        for obj in self:
            user_id = res_user.browse()
            cur = user_id.company_id.currency_id
            for line in obj.room_ids:
                total += line.sub_total1
                val += self._amount_line_tax(line)
                pur_total += line.cost_price_subtotal
                pur_val += self._amount_line_tax_pur(line)
            for line in obj.food_items_ids:
                total += line.price_subtotal
                val += self._amount_food_tax(line)
                pur_total += line.cost_price_subtotal
                pur_val += self._amount_line_tax_pur_food_other(line)
            for line in obj.other_items_ids:
                total += line.price_subtotal
                val += self._amount_other_tax(line)
                pur_total += line.cost_price_subtotal
                pur_val += self._amount_line_tax_pur_food_other(line)
            res[obj.id] = cur_obj.round(val)
        sum = total + val
        # print("\n\n\n sum ======== ", sum)
        pur_sum = pur_total + pur_val
        self.write({'sale_tax_amt': val, 'sale_total_amt': sum, 'sale_untax_amt': total,
                    'pur_tax_amt': pur_val, 'pur_total_amt': pur_sum, 'pur_untax_amt': pur_total
                    })
        return True

    def action_confirm(self):
        for obj in self:
            if not obj.room_ids:
                raise exceptions.except_orm(
                    _("Warning"), _("Room Details are missing."))
            for room in obj.room_ids:
                room_line_id = self.env['hotel.room'].search(
                    [('product_id', '=', room.room_number.id)])
                room_line_browse = self.env['hotel.room'].browse(
                    room_line_id.id)
                if room_line_browse.room_folio_ids:
                    for history in room_line_browse.room_folio_ids:
                        if history.state == 'done':
                            history_start_date = history.check_in
                            history_end_date = history.check_out
                            reservation_start_date = obj.checkin_date
                            reservation_end_date = obj.checkout_date
                            if (history_start_date <= reservation_start_date < history_end_date) or (
                                    history_start_date < reservation_end_date <= history_end_date) or (
                                    (reservation_start_date < history_start_date) and (
                                    reservation_end_date > history_end_date)):
                                if not (obj == history.booking_id):
                                    raise exceptions.except_orm(_("Warning"), _(
                                        "You tried to confirm reservation with room  %s which is already reserved in this reservation period !") % (
                                        room.room_number.name))

        self.write({'state': 'confirm'})
        return True

    def action_approve(self):
        for obj in self:
            data_obj = self.env['ir.model.data']
            data_id = data_obj._get_id(
                'crm', 'view_crm_lead2opportunity_partner')
            view_id1 = False
            if self._context is None:
                self._context = {}
            ctx = dict(self._context)
            ctx['active_ids'] = [obj.id]
            ctx['banquet_id'] = obj.id

            if data_id:
                view_id1 = data_obj.browse(data_id).res_id
            value = {
                'name': _('Create Partner'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'crm.lead2opportunity.partner',
                'view_id': False,
                'context': ctx,
                'views': [(view_id1, 'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
                'nodestroy': True
            }

            id_lead = self.env['crm.lead'].browse(obj.lead.id)
            rejected_history_id = self.env['banquet.quotation.lead.history'].search(
                [('ref_id', '=', id_lead.id)])
            if rejected_history_id:
                for id in rejected_history_id:
                    self.env['banquet.quotation.lead.history'].write(
                        {'state': 'refused', 'update_date': time.strftime('%Y-%m-%d')})
            history_id = self.env['banquet.quotation.lead.history'].search(
                [('name', '=', obj.name), ('ref_id', '=', id_lead.id)])
            if history_id:
                self.env['banquet.quotation.lead.history'].write(
                    {'state': 'approve', 'update_date': time.strftime('%Y-%m-%d')})

            rejected_itinary = self.search([('lead', '=', id_lead.id)])
            if rejected_itinary:
                for id in rejected_itinary:
                    self.write({'state': 'refused'})
        self.write({'state': 'approve'})
        return value

    def action_refuse(self):
        for obj in self:
            id_lead = self.env['crm.lead'].browse(obj.lead.id)
            history_id = self.env['banquet.quotation.lead.history'].search(
                [('name', '=', obj.name), ('ref_id', '=', id_lead.id)])
            if history_id:
                self.env['banquet.quotation.lead.history'].write(
                    {'state': 'refused', 'update_date': time.strftime('%Y-%m-%d')})
        self.write({'state': 'refused'})
        return True

    def action_sent(self):
        for obj in self:
            id_lead = self.env['crm.lead'].browse(obj.lead.id)
            itinarary_id = self.env['banquet.quotation.lead.history'].create({
                'name': obj.name,
                'contact_name': obj.contact_name,
                'state': 'send_to',
                'ref_id': id_lead.id,
                'current_date': time.strftime('%Y-%m-%d'),
                'update_date': time.strftime('%Y-%m-%d'),
            })
            stage = self.env['crm.stage'].search(
                [('name', '=', 'Proposition')])
            if stage:
                self.env['crm.lead'].write({'stage_id': stage.id})
        self.write({'state': 'send_to'})
        return True

    def action_create_tour(self):
        for obj in self:
            #             shop = self.env['sale.shop'].search([])
            if not self.shop_id:
                raise exceptions.except_orm(
                    'Configuration Error', 'Shop is not define.')
            shop_id = self.env['sale.shop'].browse(self.shop_id.id)
            if not obj.lead.partner_id:
                raise exceptions.except_orm(_("Warning"), _(
                    "Please convert the Lead '%s' in Opportunity first!") % (obj.lead.lead_sequence))
            banquet_id = self.env['hotel.reservation'].create({
                'shop_id': obj.shop_id.id,
                'pricelist_id': obj.pricelist_id.id,
                'banq_bool': True,
                'partner_id': obj.lead.partner_id.id,
                'checkin': obj.checkin_date,
                'checkout': obj.checkout_date,
                'adults': obj.adult,
                'childs': obj.child,
                'deposit_policy': obj.deposit_policy,
                'percentage': obj.percentage,
                'min_dep_amount': obj.min_dep_amount,
                'banquet_id': obj.id,
                'via': obj.via,
                'agent_id': obj.agent_id.id,
                'source': 'internal_reservation',
            })

            for room in obj.room_ids:
                tax_ids = []
                for tax_line in room.taxes_id:
                    tax_ids.append(tax_line.id)
                room_booking_id = self.env['hotel.reservation.line'].create({
                    'room_number': room.room_number.id,
                    'price': room.price,
                    'categ_id': room.categ_id.id,
                    'discount': room.discount,
                    'taxes_id': [(6, 0, tax_ids)],
                    'line_id': banquet_id.id,
                    'checkin': room.checkin,
                    'checkout': room.checkout,
                })
            for room in obj.food_items_ids:
                tax_ids = []
                for tax_line in room.tax_id:
                    tax_ids.append(tax_line.id)
                room_booking_id = self.env['food.items'].create({
                    'product_id': room.product_id.id,
                    'name': room.product_id.name,
                    'price_unit': room.price_unit,
                    'discount': room.discount,
                    'tax_id': [(6, 0, tax_ids)],
                    'food_items_id': banquet_id.id,
                    'product_uom': room.product_uom.id,
                    'product_uom_qty': room.product_uom_qty
                })
            for room in obj.other_items_ids:
                tax_ids = []
                for tax_line in room.tax_id:
                    tax_ids.append(tax_line.id)
                room_booking_id = self.env['other.items'].create({
                    'product_id': room.product_id.id,
                    'name': room.product_id.name,
                    'price_unit': room.price_unit,
                    'discount': room.discount,
                    'tax_id': [(6, 0, tax_ids)],
                    'other_items_id': banquet_id.id,
                    'product_uom': room.product_uom.id,
                    'product_uom_qty': room.product_uom_qty
                })
            # print("\n\n\n banquet_id =====", banquet_id)
            # print("\n\n\n banquet_id =====", banquet_id.id)
            tour_search = self.env['hotel.reservation'].search(
                [('id', '=', banquet_id.id)])
            # print("\n\n\n tour_search =====", tour_search)
            custom_tour = self.env['hotel.reservation'].browse(tour_search.id)
        self.write({'state': 'done'})
        return True


class HotelReservationLine(models.Model):
    _inherit = "hotel.reservation.line"
    _description = "Reservation Line"

    def count_total_days(self):

        res = {}
        for obj in self:
            if obj.company_id.id == self.env.user.company_id.id:
                policy_obj = self.env['checkout.configuration'].search(
                    [('shop_id', '=', obj.line_id.shop_id.id)])
                # print("obj:::::::::",policy_obj,obj.line_id.shop_id.id)
                if not policy_obj:
                    # print('_________________3',obj.id, obj.line_id.shop_id.name)
                    raise UserError(
                        'Configuration Error! Checkout policy is not define for selected shop.')
                policy_browse = self.env['checkout.configuration'].browse(
                    policy_obj.id)

                ch_in = obj.checkin

                ch_out = obj.checkout
                check_in = obj.checkin
                check_out = obj.checkout
                day_count1 = (check_out - check_in).days
                if day_count1 == 0:
                    day_count1 = 1
                # if not policy_browse.name == '24hour':
                #     wd_count = 0
                #     time_con = str(policy_browse.time)
                #     check_out_cons = obj.checkin
                #     for count in range(0, (int(day_count1))):
                #         single_date = check_in + relativedelta(days=count)
                #         day = calendar.weekday(int(single_date.strftime("%Y")), int(
                #             single_date.strftime("%m")), int(single_date.strftime("%d")))
                #         if str(single_date) == obj.checkin:
                #             time_con = str(policy_browse.time)
                #             check_out_cons = obj.checkin
                #             if obj.checkin < check_out_cons:
                #                 wd_count += 1
                #             if obj.checkout > check_out_cons:
                #                 wd_count += 1
                #         elif str(single_date) == obj.checkout:
                #             time_con = str(policy_browse.time)
                #             check_out_cons = obj.checkout
                #             if obj.checkout > check_out_cons:
                #                 wd_count += 1
                #         if (str(single_date) != obj.checkin) and (str(single_date) != obj.checkout):
                #             time_con = str(policy_browse.time)
                #             check_out_cons = obj.checkin
                #             if obj.checkout > check_out_cons:
                #                 wd_count += 1
                #     day_count1 = wd_count
                # else:
                #     day_count = (check_out - check_in).days + 1

                #     time_in = obj.checkin
                #     time_out = obj.checkout
                #     time_count1 = (time_out - time_in)
                    # if time_count1 > timedelta(0):
                    #     day_count += 1
                # day_count1 = round(day_count)
                obj.update({
                    'number_of_days': day_count1,
                })

    @api.depends('number_of_days', 'discount', 'price', 'taxes_id')
    def count_price(self):
        # print("rrrrrrrrrrrrrrrrrrrr")
        tax_obj = self.env['account.tax']
        cur_obj = self.env['res.currency']
        res_user = self.env['res.users']
        res = {}
        if self._context is None:
            self._context = {}
        for line in self:
            if line.line_id:
                # print("inside====if")
                price = line.price * (1 - (line.discount or 0.0) / 100.0)
                # print("\n\n\n price ======", line.number_of_days)
                taxes = line.taxes_id.compute_all(
                    price, None, line.number_of_days)
                val = taxes['total_excluded']
                cur = line.line_id.pricelist_id.currency_id
                line.update({
                    'sub_total1': cur.round(val),
                })
                # print("\n\n\n if val ======", val)
            else:
                # print("inside else=======")
                price = line.price * (1 - (line.discount or 0.0) / 100.0)
                taxes = line.taxes_id.compute_all(
                    price, None, line.number_of_days)
                val = taxes['total_excluded']
                user_id = res_user.browse(self._uid)
                cur = user_id.company_id.currency_id
                line.update({
                    'sub_total1': cur.round(val),
                })

    def _amount_line_cost(self):
        res_user = self.env['res.users']
        res = {}
        if self._context is None:
            context = {}
        for line in self:
            if line.banquet_id:
                price = line.cost_price_unit
                taxes = line.pur_tax_ids.compute_all(
                    price, None, line.number_of_days)
                val = taxes['total_excluded']
                user_id = res_user.browse(self._uid)
                cur = user_id.company_id.currency_id
            line.update({
                'cost_price_subtotal': cur.round(val),
            })

    @api.onchange('room_number')
    @api.depends('checkin', 'checkout', 'banquet_id.pricelist_id', 'banquet_id', 'line_id.partner_id', 'number_of_days',
                 'banquet_id.source')
    def onchange_room_id(self):
        # print("ffffffffffffffff222222222222222222222222222")
        if self.line_id:
            pricelist = self.line_id.pricelist_id.id
            parent_id = self.line_id
        if self.banquet_id:
            pricelist = self.banquet_id.pricelist_id.id
            parent_id = self.banquet_id
        room_id = self.room_number
        # print("\n\n\n room_id =====", room_id, room_id.id)
        v = {}
        res_list = []
        warning = ''
        if self.banquet_id:
            # print("vcccccccccccccccccccccccc")
            if not pricelist:
                raise exceptions.except_orm(
                    _("Warning"), _("PriceList is not Selected !"))

            product_browse = room_id
            ctx = self._context and self._context.copy() or {}
            ctx.update({'date': self.checkin})

            price = self.env['product.pricelist'].with_context(ctx).price_get(
                room_id.id, self.number_of_days, {
                    'uom': product_browse.uom_id.id,
                    'start_date': self.checkin,
                })[pricelist]
            if price is False:
                raise exceptions.except_orm(_("Warning"), _(
                    "Couldn't find a pricelist line matching this product!"))
            v['price'] = price
            tax_ids = []
            for tax_line in product_browse.taxes_id:
                tax_ids.append(tax_line.id)
            # print("\n\n\n tax_ids ===", tax_ids)
            v['taxes_id'] = [(6, 0, tax_ids)]
            v['checkin'] = self.checkin
            v['checkout'] = self.checkout

            cost_price_unit = get_price(
                self, pricelist, product_browse.standard_price)
            # print("\n\n\n cost_price_unit ======", cost_price_unit)
            v['cost_price_unit'] = cost_price_unit

            room_line_id = self.env['hotel.room'].search(
                [('product_id', '=', room_id.id)])
            # print("\n\n\n room_line_id =======", room_line_id)
            room_line_browse = self.env['hotel.room'].browse(room_line_id.id)
            # print("\n\n\n room_line_browse =======", room_line_browse)
            if room_line_browse.room_folio_ids:
                for history in room_line_browse.room_folio_ids:
                    if history.state == 'done':
                        history_start_date = history.check_in
                        history_end_date = history.check_out
                        reservation_start_date = self.checkin
                        reservation_end_date = self.checkout
                        #############################Added by Pornima############
                        housekeeping_room = self.env['hotel.housekeeping'].search(
                            [('room_no', '=', room_line_browse.product_id.id), ('state', '=', 'dirty')])
                        if housekeeping_room:
                            for house1 in housekeeping_room:
                                #print("\n\n\n\n house1 =========", house1, house1.id)
                                # house = self.env['hotel.housekeeping'].browse(house1.id)
                                house = house1
                                # print("\n\n\n house ======", house)
                                house_current_date = (datetime.strptime(
                                    house.current_date, '%Y-%m-%d')).date()
                                house_end_date = (datetime.strptime(
                                    house.end_date, '%Y-%m-%d')).date()
                                start_reser = datetime.strptime(
                                    self.checkin, '%Y-%m-%d %H:%M:%S').date()
                                end_reser = datetime.strptime(
                                    self.checkout, '%Y-%m-%d %H:%M:%S').date()

                                if (house_current_date <= start_reser <= house_end_date) or (
                                        house_current_date <= end_reser <= house_end_date) or (
                                        (start_reser < house_current_date) and (end_reser > house_end_date)):
                                    # if (((start_reser < house_current_date)
                                    # and (end_reser > house_end_date)) or
                                    # (house_current_date <= start_reser <
                                    # house_end_date) or (house_current_date <
                                    # end_reser <= house_end_date)) and
                                    # (house.state == 'dirty'):
                                    raise exceptions.except_orm(_("Warning"),
                                                                _("Room  %s is not clean for reservation period !") % (
                                                                    room_line_browse[0].name))

                        #############################Added by Pornima##########
                        if (history_start_date <= reservation_start_date < history_end_date) or (
                                history_start_date < reservation_end_date <= history_end_date) or (
                                (reservation_start_date < history_start_date) and (
                                reservation_end_date > history_end_date)):
                            if not (parent_id == history.booking_id.id):
                                raise exceptions.except_orm(_("Warning"), _(
                                    "Room  %s is booked in this reservation period !") % (room_line_browse[0].name))
        else:

            if self.line_id:
                if not self.line_id.pricelist_id:
                    raise Warning("PriceList is not Selected !")
                if self.room_number:
                    # print(self.room_number.id, "room_number")
                    product_browse = self.room_number
                    product_id = product_browse.id

                    price = product_browse.lst_price
                    # print("11111111111111111111111111111111111111111111111111111111", price)

                    if price is False:
                        raise Warning(
                            "Couldn't find a pricelist line matching this product!1")

                    # print("self.checkin:::::::::::::::;", )

                    ctx = self._context and self._context.copy() or {}
                    ctx.update({'date': self.checkin})

                    price = self.env['product.pricelist'].with_context(ctx).price_get(
                        room_id.id, self.number_of_days, {
                            'uom': product_browse.uom_id.id,
                            'date': self.checkin,
                        })[pricelist]

                    # print("self.number_of_days:::::::::", self.number_of_days, product_browse.uom_id.id, self.checkin)
                    v['price'] = price
                    tax_ids = []
                    for tax_line in product_browse.taxes_id:
                        tax_ids.append(tax_line.id)
                    v['taxes_id'] = [(6, 0, tax_ids)]
                    v['checkin'] = self.checkin
                    v['checkout'] = self.checkout

                    room_line_id = self.env['hotel.room'].search(
                        [('product_id', '=', product_id)])
                    housekeeping_room = self.env['hotel.housekeeping'].search(
                        [('room_no', '=', room_line_id.id), ('state', '=', 'dirty')])
                    if housekeeping_room:
                        for house1 in housekeeping_room:
                            # house = self.env['hotel.housekeeping'].browse(house1)
                            house = house1

                            house_current_date = (datetime.strptime(
                                str(house.current_date), '%Y-%m-%d')).date()
                            house_end_date = (datetime.strptime(
                                str(house.end_date), '%Y-%m-%d')).date()
                            start_reser = datetime.strptime(
                                str(self.checkin), '%Y-%m-%d %H:%M:%S').date()
                            end_reser = datetime.strptime(
                                str(self.checkout), '%Y-%m-%d %H:%M:%S').date()
                            if (house_current_date <= start_reser <= house_end_date) or (
                                    house_current_date <= end_reser <= house_end_date) or (
                                    (start_reser < house_current_date) and (end_reser > house_end_date)):
                                raise Warning(
                                    "Room  %s is not clean for reservation period !" % (room_line_id.name))

                    ###################################################################

                    if room_line_id.room_folio_ids:
                        for history in room_line_id.room_folio_ids:
                            if history.state == 'done':
                                history_start_date = history.check_in
                                history_end_date = history.check_out
                                reservation_start_date = self.checkin
                                reservation_end_date = self.checkout
                                if (history_start_date <= reservation_start_date < history_end_date) or (
                                        history_start_date < reservation_end_date <= history_end_date) or (
                                        (reservation_start_date < history_start_date) and (
                                        reservation_end_date > history_end_date)):

                                    if not (self.line_id.id == history.booking_id.id):
                                        raise Warning(
                                            "Room  %s is booked in this reservation period !" % (room_line_id.name,))

        return {'value': v, 'warning': warning}

    currency_id = fields.Many2one(
        related='line_id.currency_id', store=True, string='Currency', readonly=True)
    banquet_id = fields.Many2one('banquet.quotation', 'Banquet Id')
    sub_total = fields.Float(compute='count_price',
                             string="sub total")
    cost_price_unit = fields.Float('Cost Price', digits='Cost Price')
    cost_price_subtotal = fields.Float(
        compute='_amount_line_cost', string='Cost Subtotal', digits='Cost Price')
    pur_tax_ids = fields.Many2many(
        'account.tax', 'pur_hotel_line_tax_rel', 'hotel_line_id', 'tax_id', 'Purchase Taxes')
    purches_bol = fields.Boolean('Show Purchase Tax')
    number_of_days = fields.Integer(
        compute='count_total_days', string="Number Of Days")


class HotelReservation(models.Model):
    _inherit = "hotel.reservation"
    _description = "Reservation"

    @api.onchange('deposit_policy')
    def onchange_deposit_policy(self):
        v = {}
        if self.deposit_policy == 'no_deposit':
            v['percentage'] = 0.0
        return {'value': v}

    def _get_subtotal_amount(self):
        line_subtotal = super(HotelReservation, self)._get_subtotal_amount()
        total = 0.00
        tax_obj = self.env['account.tax']
        for obj in self:
            cur = obj.pricelist_id.currency_id
            for line in obj.reservation_line:
                price = line.price * (1 - (line.discount or 0.0) / 100.0)
                taxes = line.taxes_id.compute_all(
                    price, None, line.number_of_days)
                cur = line.line_id.pricelist_id.currency_id
                total += line.sub_total1
            for food in obj.food_items_ids:
                total += food.price_subtotal
            for other in obj.other_items_ids:
                total += other.price_subtotal
            obj.update({
                'untaxed_amt': obj.pricelist_id.currency_id.round(total),
            })

    def _get_total_tax(self):
        res = {}
        total = 0.00
        val = 0.00
        total_val = 0.00
        tax_obj = self.env['account.tax']
        cur_obj = self.env['res.currency']
        for obj in self:
            cur = obj.pricelist_id.currency_id
            for line in obj.reservation_line:
                val += self._amount_line_tax(line)
                # print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!",
                #       val)
            for line in obj.food_items_ids:
                total += line.price_subtotal
                val += self._amount_food_tax(line)
            # print("VALUES===>>>", val)
            for line in obj.other_items_ids:
                total += line.price_subtotal
                # print("OTHER ITEM TAX====>>>>>line.tax_id", line.product_id)

                val += self._amount_other_tax(line)
                # print("OTHER ITEM TAX====>>>>>", val)
            obj.update({
                'total_tax': cur.round(val),
            })

    def _amount_other_tax(self, line):
        val = 0.0
        # print("TAX ID====>>>>", line.tax_id)
        taxes = line.tax_id.compute_all(
            line.price_subtotal * (1 - (line.discount or 0.0) / 100.0), None, 1)
        # print("TAXES==>>>>", taxes)
        val = taxes['total_included'] - taxes['total_excluded']
        # print("AMOUNT OTHER TAX===>>>>", val)
        return val

    def _amount_food_tax(self, line):
        val = 0.0
        taxes = line.tax_id.compute_all(
            line.price_subtotal * (1 - (line.discount or 0.0) / 100.0), None, 1)
        val = taxes['total_included'] - taxes['total_excluded']
        return val

    # @api.multi
    def _get_total_rental_cost(self):
        # total amount after deduction by tax
        res = {}
        total = 0.00
        val = 0.00
        sum = 0.00
        cur_obj = self.env['res.currency']
        for obj in self:
            total = 0.00
            val = 0.00
            sum = 0.00
            cur = obj.pricelist_id.currency_id
            for line in obj.reservation_line:
                total += line.sub_total1
                # print("total===========================_get_total_rental_cost==========================", total)
                val += self._amount_line_tax(line)
                # print("val===========================_get_total_rental_cost==========================", val)
            for line in obj.food_items_ids:
                total += line.price_subtotal
                val += self._amount_food_tax(line)
            for line in obj.other_items_ids:
                total += line.price_subtotal
                val += self._amount_other_tax(line)
            if cur:
                sum = cur.round(total) + cur.round(val)
            #             obj.update({
            #                 'total_cost1': sum,
            #             })
            obj.total_cost1 = sum
        # print("\n\n\n _get_total_rental_costttttttttttt")

    def _get_deposit_cost1(self):
        total = 0
        for obj in self:
            if obj.deposit_policy == 'percentage':
                for rental_line in obj.reservation_line:
                    room_line_id = self.env['hotel.room'].search(
                        [('product_id', '=', rental_line.room_number.id)])
                    if room_line_id:
                        room_line_browse = self.env['hotel.room'].browse(room_line_id)[
                            0].id
                        # print(room_line_browse, '===============room_line_browse=========')
                        if room_line_id.deposit_bool:
                            # print(rental_line.sub_total1, "rental_line.total_rent")
                            total += (rental_line.sub_total1 + self._amount_line_tax(
                                rental_line)) * obj.percentage / 100
                # print(total, "total$$$$$$$$$$$$$$$$$$4444")
                if total and (total < obj.min_dep_amount):
                    total = obj.min_dep_amount
            elif obj.deposit_policy == 'no_deposit':
                total = 0.0
            # print("total===============", total)
            #             obj.update({
            #                 'deposit_cost': total,
            #             })
            obj.deposit_cost = total

    # @api.onchange('checkout_date')
    @api.depends('checkin_date')
    def on_change_checkout(self):
        self.checkin_date = time.strftime('%Y-%m-%d %H:%M:%S')
        self.checkout_date = time.strftime('%Y-%m-%d %H:%M:%S')
        delta = timedelta(days=1)
        if not self.checkout_date:
            self.checkout_date = time.strftime('%Y-%m-%d %H:%M:%S')
        addDays = datetime.datetime(
            *time.strptime(self.checkout_date, '%Y-%m-%d %H:%M:%S')[:5]) + delta
        if self.checkin_date:
            new_date = str(self.checkin_date)
            self._cr.execute(
                'select max(start_date) from deposit_payment_policy where start_date <= %s ', (new_date,))
            a = self._cr.fetchone()
            if not a[0]:
                raise exceptions.except_orm(
                    'Configuration Error', 'Deposit policy is not define.')
            pay_obj = self.env['deposit.payment.policy'].search(
                [('start_date', '=', a[0])])
            dep_obj = self.env['deposit.payment.policy'].browse(pay_obj[0])
        val = {'value': {'dummy': addDays.strftime(
            '%Y-%m-%d %H:%M:%S'), 'percentage': dep_obj.percentage, 'min_dep_amount': dep_obj.min_amount}}
        return val

    banq_bool = fields.Boolean('Banquet Booking', default=False)
    deposit_policy = fields.Selection([('percentage', 'Deposit Percentage'), ('no_deposit', 'No Deposit')],
                                      'Deposit Policy', required=True, readonly=True,
                                      states={'draft': [('readonly', False)]}, default='no_deposit')
    percentage = fields.Float("Percentage/Deposit Amount")
    min_dep_amount = fields.Float("Minimum Deposit Amount")
    deposit_recv_acc = fields.Many2one('account.account', string="Deposit Account", required=False,
                                       company_dependent=True)
    food_items_ids = fields.One2many(
        'food.items', 'food_items_id', 'Food Items')
    other_items_ids = fields.One2many(
        'other.items', 'other_items_id', 'Other Items')
    untaxed_amt = fields.Float(
        compute='_get_subtotal_amount', string="Untaxed Amount")
    total_tax = fields.Float(compute='_get_total_tax', type="float", string="Reservation Tax",
                             help="The amount without tax.")
    total_cost1 = fields.Float(
        compute='_get_total_rental_cost', string="Total Reservation cost", )
    deposit_cost = fields.Float(
        compute='_get_deposit_cost1', string="Deposit Cost", )
    banquet_id = fields.Many2one(
        'banquet.quotation', 'Booking Ref.', readonly=True)
    agent_comm = fields.Float("Commision")

    # @api.multi
    @api.onchange('deposit_policy')
    def onchange_deposit_policy(self):
        if self.deposit_policy == 'percentage':
            self.deposit_recv_acc = self.partner_id.property_account_receivable_id

    # @api.multi
    def done(self):
        # print("\n\n in done 11111111 =======")
        active_id = self._ids
        for reservation in self:
            self.write({'agent_comm': reservation.total_cost1, })
            if reservation.deposit_cost2:
                data_obj = self.env['ir.model.data']
                data_id = data_obj._get_id(
                    'hotel_management', 'deposit_journal_entry_wizard1')
                view_id1 = False
                if self._context is None:
                    self._context = {}
                ctx = dict(self._context)
                ctx['active_ids'] = [reservation.id]
                ctx['booking_id'] = reservation.id
                if data_id:
                    view_id1 = data_obj.browse(data_id).res_id
                value = {
                    'name': _('Advance Payment Entry'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'deposit_journal_entry.wizard1',
                    'view_id': False,
                    'context': ctx,
                    'views': [(view_id1, 'form')],
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'nodestroy': True
                }
                return value
            elif (reservation.banq_bool and reservation.deposit_cost2):
                data_obj = self.env['ir.model.data']
                data_id = data_obj._get_id(
                    'banquet_managment', 'deposit_journal_entry_wizard')
                view_id1 = False
                if self._context is None:
                    self._context = {}
                ctx = dict(self._context)
                ctx['active_ids'] = [reservation.id]
                ctx['booking_id'] = reservation.id
                if data_id:
                    view_id1 = data_obj.browse(data_id).res_id
                value = {
                    'name': _('Deposit amount entry'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'deposit_journal_entry.wizard',
                    'view_id': False,
                    'context': ctx,
                    'views': [(view_id1, 'form')],
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'nodestroy': True
                }
                return value
            else:
                # print("\n\n in done create folio =======")
                so = self.create_folio()
                # print("\n\n in done create folio === so====", so)
                return so


class FoodItems(models.Model):
    _name = "food.items"
    _description = "Food Items Details"

    def _amount_line_tax_for_food(self, line):
        val = 0.0
        taxes = line.tax_id.compute_all(line.price_unit * (1 - (line.discount or 0.0) / 100.0), None,
                                        line.product_uom_qty)
        val = taxes['total_included'] - taxes['total_excluded']
        return val

    def _amount_line(self):
        res = {}
        cur_obj = self.env['res.currency']
        res_user = self.env['res.users']
        if self._context is None:
            self._context = {}
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            if line.food_items_id:
                taxes = line.tax_id.compute_all(
                    price, None, line.product_uom_qty)
                val = taxes['total_excluded']
                cur = line.food_items_id.pricelist_id.currency_id
            else:
                taxes = line.tax_id.compute_all(
                    price, None, line.product_uom_qty)
                val = taxes['total_excluded']
                user_id = res_user.browse()
                cur = user_id.company_id.currency_id
            #             line.update({
            #                 'price_subtotal': val,
            #             })
            line.price_subtotal = val

    def _amount_line_cost(self):
        res_user = self.env['res.users']
        res = {}
        if self._context is None:
            context = {}
        for line in self:
            if line.banquet_id:
                price = line.cost_price_unit
                taxes = line.pur_tax_ids.compute_all(
                    price, None, line.product_uom_qty)
                val = taxes['total_excluded']
                user_id = res_user.browse(self._uid)
                cur = user_id.company_id.currency_id
            #             line.update({
            #                 'cost_price_subtotal': cur.round(val),
            #             })
            line.cost_price_subtotal = cur.round(val)
        return res

    @api.onchange('product_id')
    @api.depends('banquet_id.pricelist_id', 'product_uom_qty')
    def onchange_product_id(self):
        res = {}
        pricelist = self.food_items_id.pricelist_id.id
        if not pricelist:
            # print("hfjdshfjdhfkjdhfdjfhfhsfd122222222212121212121212121212",
            #       pricelist, self.banquet_id)
            raise exceptions.except_orm(
                'Warning', 'Price List is not define1.')
        if self.product_id:
            record = self.env['product.product'].browse(self.product_id.id)
            price_unit = self.env['product.pricelist'].price_get(
                self.product_id.id, self.product_uom_qty, {
                    'uom': record.uom_id.id,
                })[pricelist]

            if price_unit is False:
                raise exceptions.except_orm(_("Warning"), _(
                    "Couldn't find a pricelist line matching this product!"))
            res['price_unit'] = price_unit
            res['price_unit'] = get_price(self, pricelist, record.list_price)
            res['cost_price_unit'] = get_price(
                self, pricelist, record.standard_price)
            res['cost_price_unit'] = record.standard_price
            res['product_uom'] = record.uom_id.id
            res['name'] = record.name
            tax_ids = []
            for tax_line in record.taxes_id:
                tax_ids.append(tax_line.id)
            res['tax_id'] = [(6, 0, tax_ids)]
        return {'value': res}

    def get_subcategory_ids(self, parent_id):
        all_categ_ids = []
        get_ids = []
        if parent_id:
            categ_sub_ids = self.env['product.category'].search(
                [('parent_id', '=', parent_id)])
            if categ_sub_ids:
                for categ_sub in categ_sub_ids:
                    all_categ_ids.append(categ_sub)
                    get_ids = self.get_subcategory_ids(categ_sub)
                    if get_ids:
                        for get_sub_id in get_ids:
                            all_categ_ids.append(get_sub_id)
        return all_categ_ids

    def get_category_id(self):
        food_categ = []
        obj = self.env['product.category'].search([('name', '=', 'Foods')])
        categ_ids = self.env['product.category'].search(
            [('parent_id', '=', obj[0])])
        if categ_ids:
            for categ in categ_ids:
                food_categ.append(categ)
                get_categ_ids = self.get_subcategory_ids(categ)
                if get_categ_ids:
                    for get_categ_id in get_categ_ids:
                        food_categ.append(get_categ_id)
        food_categ.append(obj[0])
        # print("food categ", food_categ)
        return food_categ

    food_items_id = fields.Many2one('hotel.reservation')
    name = fields.Char('Description', required=True, index=True)
    product_id = fields.Many2one('product.product', 'Product', domain=[(
        'sale_ok', '=', True)], change_default=True,
        help="Will list out all food items that belong to company of selected shop. \n It also shows global product as well.")
    price_unit = fields.Float(
        'Unit Price', required=True, digits='Sale Price', default=0.0)
    price_subtotal = fields.Float(
        compute='_amount_line', string='Subtotal', digits='Sale Price')
    tax_id = fields.Many2many(
        'account.tax', 'food_item_tax', 'order_line_id', 'tax_id', 'Taxes')
    product_uom_qty = fields.Float(
        'Quantity (UoM)', digits='Product UoS', default=1)
    product_uom = fields.Many2one('uom.uom', 'UoM', required=True)
    discount = fields.Float('Discount (%)', digits=(16, 2), default=0.0)
    banquet_id = fields.Many2one('banquet.quotation')
    cost_price_unit = fields.Float('Cost Price', digits='Cost Price')
    cost_price_subtotal = fields.Float(
        compute='_amount_line_cost', string='Cost Subtotal', digits='Cost Price')
    pur_tax_ids = fields.Many2many(
        'account.tax', 'pur_tax_tax_line_rel', 'food_id', 'tax_id', 'Purchase Taxes')
    purches_bol = fields.Boolean('Show Purchase Tax')
    category_id = fields.Char('Category',  default='get_category_id')


class OtherItems(models.Model):
    _name = "other.items"

    _description = "Other Items Details"

    def _amount_line(self):
        res = {}
        cur_obj = self.env['res.currency']
        res_user = self.env['res.users']
        if self._context is None:
            self._context = {}
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            if line.other_items_id:
                taxes = line.tax_id.compute_all(
                    price, None, line.product_uom_qty)
                val = taxes['total_excluded']
                cur = line.other_items_id.pricelist_id.currency_id
            else:
                taxes = line.tax_id.compute_all(
                    price, None, line.product_uom_qty)
                val = taxes['total_excluded']
                user_id = res_user.browse()
                cur = user_id.company_id.currency_id
            #             line.update({
            #                 'price_subtotal': val,
            #             })
            line.price_subtotal = val

    @api.onchange('product_id')
    @api.depends('banquet_id.pricelist_id', 'product_uom_qty')
    def onchange_product_id(self):
        res = {}
        # banquet_id=self.env['banquet.quotation'].search([])
        # print("iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiii",pk)
        pricelist = self.other_items_id.pricelist_id.id
        if not pricelist:
            raise Warning('Price List is not define.')
        if self.product_id:
            record = self.env['product.product'].browse(self.product_id.id)
            price_unit = self.env['product.pricelist'].price_get(
                self.product_id.id, self.product_uom_qty, {
                    'uom': record.uom_id.id,
                })[pricelist]
            if price_unit is False:
                raise exceptions.except_orm(_("Warning"), _(
                    "Couldn't find a pricelist line matching this product!"))
            res['price_unit'] = price_unit
            res['cost_price_unit'] = record.standard_price
            res['product_uom'] = record.uom_id.id
            res['name'] = record.name
            tax_ids = []
            for tax_line in record.taxes_id:
                tax_ids.append(tax_line.id)
            # print("TAX IDSSS===>>>", tax_ids)
            # res['tax_id'] = [(6, 0, tax_ids)]
            self.tax_id = [(6, 0, tax_ids)]
        return {'value': res}

    def _amount_line_cost(self):
        res = {}
        tax_obj = self.env['account.tax']
        cur_obj = self.env['res.currency']
        res_user = self.env['res.users']
        if self._context is None:
            self._context = {}
        for line in self:
            if line.banquet_id:
                price = line.cost_price_unit
                taxes = line.pur_tax_ids.compute_all(
                    price, None, line.product_uom_qty)
                val = taxes['total_excluded']
                user_id = res_user.browse()
                cur = user_id.company_id.currency_id
            #             line.update({
            #                 'cost_price_subtotal': cur.rount(val),
            #             })
            line.cost_price_subtotal = cur.round(val)

    @api.depends('price_unit', 'discount')
    def _get_price_reduce(self):
        for line in self:
            line.price_reduce = line.price_unit * (1.0 - line.discount / 100.0)

    other_items_id = fields.Many2one('hotel.reservation')
    name = fields.Char('Description', required=True, index=True)
    product_id = fields.Many2one('product.product', 'Product', domain=[
                                 ('sale_ok', '=', True), ('isservice', '=', True)], change_default=True)
    price_unit = fields.Float(
        'Unit Price', required=True, digits='Sale Price', default=0.0)
    price_subtotal = fields.Float(
        compute='_amount_line', string='Subtotal', digits='Sale Price')
    tax_id = fields.Many2many(
        'account.tax', 'other_service_tax', 'order_line_id', 'tax_id', 'Taxes')
    product_uom_qty = fields.Float(
        'Quantity (UoM)', digits='Product UoS', default=1)
    product_uom = fields.Many2one('uom.uom', 'UoM', required=True)
    discount = fields.Float('Discount (%)', digits=(16, 2), deafult=0.0)
    banquet_id = fields.Many2one('banquet.quotation')
    cost_price_unit = fields.Float('Cost Price', digits='Cost Price')
    cost_price_subtotal = fields.Float(
        compute='_amount_line_cost', string='Cost Subtotal', digits='Cost Price')
    pur_tax_ids = fields.Many2many(
        'account.tax', 'pur_other_tax_line_rel', 'other_id', 'tax_id', 'Purchase Taxes')
    purches_bol = fields.Boolean('Show Purchase Tax')

    # promocodes fields/////////
    is_reward_line = fields.Boolean('Is a program reward line')
    price_reduce = fields.Float(compute='_get_price_reduce', string='Price Reduce',
                                digits='Product Price', readonly=True, store=True)

    # promocode fields end ///////

    def unlink(self):
        print("unlink working")
        if self.is_reward_line:
            print("reward_line inside")
            self.other_items_id.update({
                'code_promo_program_id': False,
            })
        res = super(OtherItems, self).unlink()
        return res


class HotelRoom(models.Model):
    _inherit = "hotel.room"
    _description = "room Inherit "

    deposit_bool = fields.Boolean('Is Deposit Applicable', default=True)


class BanquetQuotationLeadHistory(models.Model):
    _name = 'banquet.quotation.lead.history'
    _description = 'itinerary lead history'

    ref_id = fields.Many2one('crm.lead', 'History', required=True)
    name = fields.Char("Banquet Quotation No.", readonly=True)
    contact_name = fields.Char('Contact Name',  readonly=True, )
    current_date = fields.Date("Creation Date", required=True, )
    update_date = fields.Date("Last Updated Date", required=True, )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('send_to', 'Send To Customer'),
        ('approve', 'Approved'),
        ('refused', 'Refused'),
        #                               ('create_tour', 'Create Tour'),
    ], 'Status', readonly=True)
