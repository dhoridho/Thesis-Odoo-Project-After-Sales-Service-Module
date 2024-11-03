# -*- coding: utf-8 -*-
from odoo import models, fields, api, _, tools
from datetime import datetime, date
from odoo.exceptions import UserError, ValidationError, Warning
from datetime import date, datetime, timedelta

class Restore(models.TransientModel):
    _name = "restore.lead.type"
    _description = "Restore"

    @api.model
    def _default_domain(self):
        secondary = self.env.ref('equip3_crm_operation.lead_type_restore_data_two').id
        recycle = self.env.ref('equip3_crm_operation.lead_type_restore_data_three').id
        return [('id', 'in', (secondary, recycle))]

    lead_type_id = fields.Many2one('crm.lead.type', string="Lead Type", domain=_default_domain)

    def action_submit(self):
        context = dict(self.env.context) or {}
        crm_lead_id = self.env['crm.lead'].browse(context.get('active_ids'))
        crm_lead_id.with_context(context).toggle_active()
        if crm_lead_id.probability == 0:
            crm_lead_id.probability = 0.1
            crm_lead_id.with_context(context).toggle_active()
        crm_lead_id.write({'active': True,'stage_id': self.env.ref('crm.stage_lead1').id, 'type_id': self.lead_type_id.id})


class CrmLeadSalespersonLine(models.Model):
    _name = 'crm.lead.salesperson.lines'
    _description = 'Salesperson'

    salesperson_id = fields.Many2one('res.users', string="Salesperson")
    weightage = fields.Float("Weightage")
    status = fields.Selection([
        ("main", "Main Salesperson"),
        ("pairing", "Pairing Salesperson"),
    ], string="Status")
    lead_id = fields.Many2one('crm.lead')

class CrmLeadProduct(models.Model):
    _name = 'crm.lead.product'
    _description = "CRM Lead Product"

    product_id =  fields.Many2one('product.product',string='Product', domain="[('type', '!=', 'asset')]")
    description = fields.Text(string='Description')
    qty = fields.Float(string='Ordered Qty',default=1.0)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure')
    price_unit = fields.Float(string='Unit Price')
    tax_id = fields.Many2many('account.tax', string='Taxes')
    lead_id = fields.Many2one('crm.lead')

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.description = self.product_id.name
            self.price_unit = self.product_id.lst_price
            self.product_uom = self.product_id.uom_id.id
            self.tax_id = self.product_id.taxes_id.ids

class Lead(models.Model):
    _inherit = 'crm.lead'

    meeting_ids = fields.One2many('calendar.event', 'opportunity_id')
    one_metting = fields.Boolean(string="Had first meeting", compute="_compute_meeting", store=True)
    is_due_date = fields.Boolean(string="Missed Follow Up", compute="_compute_due_date", store=True)
    multiple_metting = fields.Boolean(string="Had multiple meetings", compute="_compute_meeting", store=True)
    type_id = fields.Many2one('crm.lead.type', string="Types", tracking=True)
    decision_maker = fields.Boolean(string="Decision Maker?", tracking=True)
    has_budget = fields.Boolean(string="Has Budget?", tracking=True)
    activity_data = fields.One2many(
        'mail.activity', 'res_id', 'Next Activity',
        auto_join=True,
        groups="base.group_user", tracking=True)

    scale = fields.Selection([
        ('large', 'Large Company'),
        ('medium', 'Medium Company'),
        ('small', 'Small Company')
    ], string="Company Scale", tracking=True)
    einstein_score = fields.Float(string="Einstein Score", compute="_compute_einstein_score", store=True)
    einstein_score_text = fields.Html(string="Einstein Score Text", compute="_compute_einstein_score", store=True)
    # probability_new = fields.Float(string="Probability", related="einstein_score", store=True)
    probability_new = fields.Float(
        'Probability', group_operator="avg", copy=False,
        compute='_compute_probabilities_new', readonly=False, store=True, tracking=True)
    automated_probability_new = fields.Float('Automated Probability', compute='_compute_probabilities_new', readonly=True, store=True)
    salesperson_lines = fields.One2many('crm.lead.salesperson.lines', 'lead_id', string='Salesperson')

    dummy_boolean = fields.Boolean("Dummy", compute="set_user_ids", store=True)
    user_ids = fields.Many2many('res.users', string="Salesperson")
    one_metting_int = fields.Integer(string="Had first meeting", compute="_compute_meeting", store=True)
    multiple_metting_int = fields.Integer(string="Had multiple meetings", compute="_compute_meeting", store=True)
    number_of_repetition = fields.Integer(string="Number of Repetitions")
    lead_product_ids = fields.One2many('crm.lead.product','lead_id',string='Products For Quotation')
    res_activity_ids = fields.One2many('res.mail.activity', 'res_id', string='Activity')
    activity_count = fields.Integer("Activity Count", compute='_compute_activity_count')
    last_follow_up = fields.Date("Last Follow Up")
    order_ids = fields.One2many('sale.order', 'opportunity_id', string='Orders')
    due_date_activity = fields.Boolean("Due Date Activity")
    next_week_has_activity = fields.Boolean("Next Week has Activity")
    next_week_no_activity = fields.Boolean("Next Week no Activity")
    this_week_has_activity = fields.Boolean("This Week has Activity")
    this_week_no_activity = fields.Boolean("This Week no Activity")
    last_week_has_activity = fields.Boolean("Last Week has Activity")
    last_week_no_activity = fields.Boolean("Last Week no Activity")
    only_one_meeting = fields.Boolean("Only one meeting", compute="_compute_meeting", store=True)
    quot_count = fields.Integer(compute='_compute_quotation_data', string="Number of Quotation", store=True)
    city_id = fields.Many2one(
        "res.country.city", string='City',
        readonly=False, store=True,
        domain="[('state_id', '=?', state_id)]")
    is_similar = fields.Boolean(string='Is Similar', compute="_compute_is_similar")
    similar_leads_count = fields.Integer(string='Similar Leads Count', compute="_compute_is_similar")
    original_team_id = fields.Many2one('crm.team', string='Original Sales Team')

    # Fields for Tracking = true
    name = fields.Char(tracking=True)
    website = fields.Char(tracking=True)
    street = fields.Char(tracking=True)
    probability = fields.Float(tracking=True)
    function = fields.Char(tracking=True)
    mobile = fields.Char(tracking=True)
    lang_id = fields.Many2one(tracking=True)
    company_id = fields.Many2one(tracking=True)
    campaign_id = fields.Many2one(tracking=True)
    source_id = fields.Many2one(tracking=True)
    medium_id = fields.Many2one(tracking=True)
    date_deadline = fields.Date(tracking=True)
    tag_ids = fields.Many2many(tracking=True)

    day_open = fields.Float(tracking=True)
    day_close = fields.Float(tracking=True)
    referred = fields.Char(tracking=True)
    description = fields.Text(tracking=True)
    branch_id = fields.Many2one('res.branch', string='Branch', required=True, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
    tag = fields.Integer("Tag", compute="compute_some_tag", store=True)

    def handle_partner_assignment(self, force_partner_id=False, create_missing=True):
        for lead in self:
            if lead.partner_id:
                lead.partner_id.write({
                    'is_leads': True,
                    'is_customer': True
                })
        return super().handle_partner_assignment()

    @api.onchange('salesperson_lines')
    def set_main_salesperson(self):
        for rec in self:
            main = rec.salesperson_lines.filtered(lambda x: x.status == 'main' and x.salesperson_id.id == rec.user_id.id)
            if not main:
                for line in rec.salesperson_lines:
                    if line.status == 'main':
                        if rec.user_id.id == line.salesperson_id.id:
                            break
                        else:
                            rec.user_id = line.salesperson_id.id
                            break

    @api.depends('user_id', 'type', 'salesperson_lines')
    def _compute_team_id(self):
        res = super()._compute_team_id()
        if self.salesperson_lines.filtered(lambda x: x.status != 'main'):
            self.team_id = False
        return res

    @api.depends('order_ids.state', 'order_ids.currency_id', 'order_ids.amount_untaxed', 'order_ids.date_order', 'order_ids.company_id')
    def _compute_quotation_data(self):
        for lead in self:
            quotation_cnt = 0
            for order in lead.order_ids:
                if order.state in ('draft', 'sent'):
                    quotation_cnt += 1
            lead.quot_count = quotation_cnt

    @api.depends('tag_ids')
    def compute_some_tag(self):
        for rec in self:
            if rec.tag_ids:
                rec.tag = 1
            else:
                rec.tag = 0

    def _get_default_expected_revenue(self):
        order_ids = self.order_ids.filtered(lambda r: r.state not in ('sale', 'cancel') or r.is_quotation_cancel == True)
        expected_revenue = order_ids[0].amount_total if order_ids else False
        return expected_revenue

    expected_revenue = fields.Monetary(default=_get_default_expected_revenue)
    default_expected_revenue = fields.Monetary(currency_field='company_currency')
    is_automated_expected_revenue = fields.Boolean('Is automated expected revenue?')

    @api.onchange('expected_revenue', 'default_expected_revenue')
    def set_is_automated_expected_revenue(self):
        for lead in self:
            lead.is_automated_expected_revenue = tools.float_compare(lead.expected_revenue, lead.default_expected_revenue, 2) == 0

    def action_set_automated_expected_revenue(self):
        self.write({
            'expected_revenue': self.default_expected_revenue,
            'is_automated_expected_revenue': True
        })

    def find_leads_similar(self, name,website='',email_from='',phone='',mobile='',my_id=False):
        where_params = ''
        id_params = ''
        query = """
            SELECT id, name
            FROM crm_lead
            WHERE (lower(name) = lower('{}'){}){}
        """
        if website:
            where_params += " or website = '{}'".format(website)
        if email_from:
            where_params += " or email_from = '{}'".format(email_from)
        if phone:
            where_params += " or phone = '{}'".format(phone)
        if mobile:
            where_params += " or mobile = '{}'".format(mobile)
        if my_id:
            id_params += " and id != {}".format(my_id)
        self.env.cr.execute(query.format(name, where_params, id_params))
        query_result = self.env.cr.dictfetchall()
        return query_result

    @api.depends('website','phone','email_from','mobile')
    def _compute_is_similar(self):
        for i in self:
            is_similar = False
            similar_leads_count = 0
            name = i.name
            if i.name:
                if "'" in i.name:
                    name = name.replace("'","''")
                if '"' in i.name:
                    name = name.replace('"','""')
            get_leads = self.find_leads_similar(name, i.website,i.email_from,i.phone,i.mobile,my_id=i.id)
            if len(get_leads) > 0:
                is_similar = True
                similar_leads_count = len(get_leads)
            i.is_similar = is_similar
            i.similar_leads_count = similar_leads_count

    def action_open_similar_leads(self):
        name = self.name
        if self.name:
            if "'" in self.name:
                name = name.replace("'","''")
            if '"' in self.name:
                name = name.replace('"','""')
        get_leads = self.find_leads_similar(name, self.website,self.email_from,self.phone,self.mobile,my_id=self.id,)
        leads_ids = []
        for leads in get_leads:
            leads_ids.append(leads['id'])
        action = {
            'name': _('Similar Leads'),
            'view_mode': 'tree,form',
            'views': [(self.env.ref('equip3_crm_operation.crm_similar_leads_view_tree').id, 'tree'), (False, 'form')],
            'res_model': 'crm.lead',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', leads_ids)],
        }
        return action

    @api.depends('order_ids.state', 'order_ids.currency_id', 'order_ids.amount_untaxed', 'order_ids.date_order', 'order_ids.company_id')
    def _compute_sale_data(self):
        res = super(Lead, self)._compute_sale_data()
        for rec in self:
            order_ids = rec.order_ids.filtered(lambda r: r.state not in ('sale', 'cancel') or r.is_quotation_cancel == True)
            rec.default_expected_revenue = order_ids[0].amount_total if order_ids else False
            if rec.is_automated_expected_revenue:
                rec.expected_revenue = rec.default_expected_revenue
            rec.set_is_automated_expected_revenue()
        return res

    def set_due_date_and_missed(self):
        start_this_week =  date.today() - timedelta(days=date.today().isocalendar()[2]-1)
        end_this_week = date.today() - timedelta(days=date.today().isocalendar()[2]-7)
        start_last_week =  date.today() - timedelta(days=date.today().isocalendar()[2]+6)
        end_last_week = date.today() - timedelta(days=date.today().isocalendar()[2])
        start_next_week = date.today() + timedelta(days=date.today().isocalendar()[2]+4)
        end_next_week = date.today() + timedelta(days=date.today().isocalendar()[2]+10)
        for rec in self:
            next_week_has_activity = False
            next_week_no_activity = False
            # leads_not_updated = True
            # leads_updated = False
            this_week_has_activity = False
            this_week_no_activity = False
            last_week_has_activity = False
            last_week_no_activity = False
            due_date_activity = False
            rec._compute_due_date()
            # activity_ids = rec.res_activity_ids.filtered(lambda v: v.state != "done")
            activity_ids = rec.res_activity_ids
            for i in activity_ids:
                if i.date_deadline == date.today():
                    due_date_activity = True
                if i.activity_type_id.name == 'Meeting':
                    if i.calendar_event_id:
                        if i.calendar_event_id.state == 'meeting':
                            if not this_week_has_activity:
                                if i.calendar_event_id.start.date() and i.calendar_event_id.stop.date():
                                    if (start_this_week <= i.calendar_event_id.start.date() <= end_this_week) or (start_this_week <= i.calendar_event_id.stop.date() <= end_this_week):
                                        this_week_has_activity = True
                            if not last_week_has_activity:
                                if i.calendar_event_id.start.date() and i.calendar_event_id.stop.date():
                                    if (start_last_week <= i.calendar_event_id.start.date() <= end_last_week) or (start_last_week <= i.calendar_event_id.stop.date() <= end_last_week):
                                        last_week_has_activity = True
                            if not next_week_has_activity:
                                if i.calendar_event_id.start.date() and i.calendar_event_id.stop.date():
                                    if (start_next_week <= i.calendar_event_id.start.date() <= end_next_week) or (start_next_week <= i.calendar_event_id.stop.date() <= end_next_week):
                                        next_week_has_activity = True
                else:
                    if not this_week_has_activity:
                        if i.date_deadline:
                            if (start_this_week <= i.date_deadline <= end_this_week):
                                this_week_has_activity = True
                    if not last_week_has_activity:
                        if i.date_deadline:
                            if (start_last_week <= i.date_deadline <= end_last_week):
                                last_week_has_activity = True
                    if not next_week_has_activity:
                        if i.date_deadline:
                            if (start_next_week <= i.date_deadline <= end_next_week):
                                next_week_has_activity = True
            if this_week_has_activity:
                this_week_no_activity = False
            else:
                this_week_no_activity = True
            if last_week_has_activity:
                last_week_no_activity = False
            else:
                last_week_no_activity = True
            if next_week_has_activity:
                next_week_no_activity = False
            else:
                next_week_no_activity = True
            # for diary in rec.diary_ids:
            #     if start_this_week <= diary.creation_date.date() <= end_this_week:
            #         leads_updated = True
            #         leads_not_updated = False
            #     else:
            #         leads_updated = False
            #         leads_not_updated = True
            rec.write({
                'this_week_has_activity': this_week_has_activity,
                'this_week_no_activity': this_week_no_activity,
                'last_week_has_activity': last_week_has_activity,
                'last_week_no_activity': last_week_no_activity,
                'next_week_has_activity': next_week_has_activity,
                'next_week_no_activity': next_week_no_activity,
                'due_date_activity':due_date_activity,
                # 'leads_not_updated': leads_not_updated,
                # 'leads_updated': leads_updated
            })

    def cron_due_date_and_missed(self):
        records = self.env['crm.lead'].search([])
        for rec in records:
            rec.set_due_date_and_missed()

    def _compute_activity_count(self):
        for res in self:
            rec = self.env['res.mail.activity'].search([('res_id', '=', res.id)])
            res.activity_count = len(rec)

    def action_schedule_activity(self):
        views = [(self.env.ref('equip3_crm_operation.res_mail_activity_view_tree').id, 'tree')]
        return {
            'type': 'ir.actions.act_window',
            'name': 'Schedule Activity',
            'view_mode': 'tree,form',
            'views':views,
            'res_model': 'res.mail.activity',
            'domain': [('res_id', '=', self.id)],
            'target': 'current',
        }

    @api.constrains('salesperson_lines')
    def _constrains_mandatory_salesperson_lines(self):
        for rec in self:
            if rec.salesperson_lines:
                for line in rec.salesperson_lines:
                    if not line.salesperson_id or not line.weightage or not line.status:
                        raise ValidationError('All the salesperson field must be filled!')

    def action_create_quotation(self):
        pricelist_id = self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist
        if not pricelist_id:
            self.partner_id.property_product_pricelist = self.env['product.pricelist'].search([('customer_category', '=', self.partner_id.customer_category.id)], limit=1)
            pricelist_id = self.partner_id.property_product_pricelist
        res = super().action_create_quotation()
        res['context']['default_branch_id'] = self.branch_id.id
        #     pricelist_id = self.env['product.pricelist'].search([
        #         '|', ('company_id', '=', False),
        #         ('company_id', '=', self.env.company.id)], limit=1)
        res['context']['default_pricelist_id'] = pricelist_id.id
        res['context']['default_currency_id'] = pricelist_id.currency_id.id
        return res


    def update_cron_auto_follow_up_sales_team(self):
        is_auto_follow_up = bool(self.env['ir.config_parameter'].sudo().get_param('equip3_crm_operation.is_auto_follow_up'))
        if is_auto_follow_up:
            cron = self.env.ref('equip3_crm_operation.auto_follow_up_leads_sales_team').active = True
        else:
            cron = self.env.ref('equip3_crm_operation.auto_follow_up_leads_sales_team').active = False

    def action_set_lost(self, **additional_values):
        res = super(Lead, self).action_set_lost()
        self.probability_new = 0
        self.probability = 0
        self.lost_reason = dict(additional_values)['lost_reason']
        return res

    def active_toggle(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Restore Lead Type',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'restore.lead.type',
            'target': 'new',
        }

    @api.depends('activity_ids')
    def _compute_due_date(self):
        today_date = date.today()
        for record in self:
            is_due_date = False
            for activity_id in record.activity_ids:
                if activity_id.date_deadline < today_date:
                    is_due_date = True
            record.is_due_date = is_due_date

    def _compute_meeting_count(self):
        if self.ids:
            meeting_data = self.env['calendar.event'].sudo().search([('state', 'not in', ['rescheduled', 'cancel']),('opportunity_id', 'in', self.ids)])
        else:
            mapped_data = 0
        for lead in self:
            lead.meeting_count = len(meeting_data)

    def action_send_wa(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Send ChatRoom Message',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'acrux.chat.message.wizard',
            'target': 'new',
            'context': {
                'default_partner_id': self.partner_id.id or self.env.user.partner_id.id,
                'default_phone': self.phone,
                'default_is_crm': True
            },
        }

    def action_send_message_wa_mass(self):
        message = []
        for rec in self:
            created_message = rec.env['acrux.chat.message.wizard'].with_context({
                'default_partner_id': rec.partner_id.id,
                'default_opportunity_id': rec.id,
                'default_mobile': rec.mobile,
                'default_whatsapp_template_id': self.env['whatsapp.template'].search([('is_default','=',True)]),
                'default_text': self.env['whatsapp.template'].search([('is_default','=',True)]).message,
                'custom_model': 'crm.lead',
                'opportunity_id': rec.id,
            }).create({}).id
            message.append(created_message)
        return {
            'name': 'Send Message Mass',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'crm.send.message.mass',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': {'default_message_chat_ids': message, 'default_total_row': len(self)},
        }

    def crm_whatsapp(self):
        res = super(Lead, self).crm_whatsapp()
        res['context'].update({
            'default_crm_lead': True,
            'default_company_name': self.partner_name,
            'res_id': self.id,
            'default_user_id': False,
            'default_mobile_number' : self.mobile})
        return res

    @api.depends('salesperson_lines')
    def set_user_ids(self):
        for res in self:
            res.user_ids = [(6, 0, [])]
            for line in res.salesperson_lines:
                if line.salesperson_id.id not in res.user_ids.ids:
                    res.user_ids = [(4, line.salesperson_id.id)]
                    if line.status == 'main':
                        # res.user_id = line.salesperson_id.id
                        user_id = self.env['crm.lead.salesperson.lines'].search([('lead_id', '=', res.id),('salesperson_id', '=', line.salesperson_id.id),('status', '!=', 'main')])
                        user_id.weightage = 100
                        salesperson = self.env['crm.lead.salesperson.lines'].search([('lead_id', '=', res.id),('salesperson_id', '=', line.salesperson_id.id),('status', '=', 'main')])
                        if user_id and salesperson:
                            if salesperson:
                                res.salesperson_lines = [(3, salesperson.id)]
                            res.salesperson_lines[0].status = 'main'
                    res.dummy_boolean = True



    def action_schedule_meeting(self):
        res = super(Lead, self).action_schedule_meeting()
        res['domain'] = [('opportunity_id', '=', self.id)]
        return res

    @api.model
    def create(self, vals):
        #     if res.partner_id:
        #         new_partner = res.partner_id.copy({
        #             'is_customer': False,
        #             'is_leads' : True,
        #             'customer_rank' : 0
        #         })
        #         res.partner_id = new_partner.id
        tot_weightage = 0
        status_main = 0

        vals_list = vals.get('salesperson_lines')
        if vals_list:
            for line in vals_list:
                if 'weightage' in line[2]:
                    tot_weightage = tot_weightage + line[2]['weightage']
                if 'status' in line[2]:
                    if line[2]['status'] == 'main':
                        status_main = status_main + 1

            if tot_weightage != 100:
                raise ValidationError("Weightage should be 100!")
            if status_main < 1:
                raise ValidationError("Please select main salesperson.")
            if status_main > 1:
                raise ValidationError("There should be only 1 main salesperson!")

        res = super(Lead, self).create(vals)
        if res.partner_name:
            cust_id = self.env['res.partner'].create({
                'name': res.partner_name,
                'street': res.street,
                'street2': res.street2,
                'city': res.city,
                'state_id': res.state_id.id or False,
                'zip': res.zip,
                'country_id': res.country_id.id or False,
                'email': res.email_from,
                'phone': res.phone,
                'mobile': res.mobile,
                'is_leads': True,
                'type': 'contact'
            })
            res.partner_id = cust_id.id
        return res

    @api.depends('email_from', 'phone', 'partner_id')
    def _compute_ribbon_message(self):
        # if self.partner_id.name != self.partner_name:
        #     self.partner_id = False
        res = super(Lead, self)._compute_ribbon_message()
        return res

    def write(self, vals):
        tot_weightage = 0
        status_main = 0
        for rec in self:
            if 'stage_id' in vals:
                if rec.type == 'opportunity':
                    if rec.stage_id.is_won or rec.stage_id.is_lost:
                        if rec.stage_id.id != vals['stage_id']:
                            raise ValidationError("Cannot move opportunities in won/lost state!")
            if vals.get('user_id'):
                sp_recs = self.env['crm.lead.salesperson.lines'].search([('lead_id', '=', self.id)], limit=1)
                sp_recs.write({'salesperson_id': vals.get('user_id')})

            vals_list = vals.get('salesperson_lines')
            if vals_list:
                for index, line in enumerate(vals_list):
                    if line[0] == 4:  # Already stored record
                        stored_rec = self.env['crm.lead.salesperson.lines'].search([('id', '=', line[1])])
                        tot_weightage = tot_weightage + stored_rec.weightage
                        if stored_rec.status == 'main':
                            status_main = status_main + 1

                    if line[0] == 1:  # Already stored but changed record
                        stored_rec = self.env['crm.lead.salesperson.lines'].search([('id', '=', line[1])])
                        # Changer user_id if first record
                        if 'salesperson_id' in line[2] and index == 0:
                            self.write({'user_id': line[2]['salesperson_id']})

                        if 'weightage' in line[2]:
                            tot_weightage = tot_weightage + line[2]['weightage']
                        else:
                            tot_weightage = tot_weightage + stored_rec.weightage

                        if 'status' in line[2]:
                            if line[2]['status'] == 'main':
                                status_main = status_main + 1
                        else:
                            if stored_rec.status == 'main':
                                status_main = status_main + 1

                    if line[0] == 0:   # new record
                        if 'weightage' in line[2]:
                            tot_weightage = tot_weightage + line[2]['weightage']
                        if 'status' in line[2]:
                            if line[2]['status'] == 'main':
                                status_main = status_main + 1

                    if line[0] == 3:
                        lines = self.env['crm.lead.salesperson.lines'].search([('lead_id','=', self.id)])
                        for line in lines:
                            tot_weightage += line.weightage
                            if line.status == 'main':
                                status_main = status_main + 1


                if tot_weightage != 100:
                    raise ValidationError("Weightage should be 100!")
                if status_main < 1:
                    raise ValidationError("Please select main salesperson.")
                if status_main > 1:
                    raise ValidationError("There should be only 1 main salesperson!")

            if 'stage_id' in vals:
                stage_id = self.env['crm.stage'].browse(vals['stage_id'])
                if stage_id.is_won:
                    vals.update({'probability_new': 100, 'automated_probability_new': 100})

            res = super(Lead, self).write(vals)
            if rec.partner_id:
                if rec.partner_id.name == rec.partner_name:
                    rec.partner_id.write({
                        'name': rec.partner_name,
                        'street': rec.street,
                        'street2': rec.street2,
                        'city': rec.city,
                        'state_id': rec.state_id.id or False,
                        'zip': rec.zip,
                        'country_id': rec.country_id.id or False,
                        'email': rec.email_from,
                        'phone': rec.phone,
                        'mobile': rec.mobile,
                        'is_leads': True,
                        'type': 'contact'
                    })
                # else:
                    # rec.partner_id = False
                    # cust_id = rec.env['res.partner'].create({
                    #     'name': rec.partner_name,
                    #     'street': rec.street,
                    #     'street2': rec.street2,
                    #     'city': rec.city,
                    #     'state_id': rec.state_id.id or False,
                    #     'zip': rec.zip,
                    #     'country_id': rec.country_id.id or False,
                    #     'email': rec.email_from,
                    #     'phone': rec.phone,
                    #     'mobile': rec.mobile,
                    #     'type': 'contact'
                    # })
                    # rec.partner_id = cust_id.id
            else:
                if rec.partner_name:
                    cust_id = self.env['res.partner'].create({
                        'name': rec.partner_name,
                        'street': rec.street,
                        'street2': rec.street2,
                        'city': rec.city,
                        'state_id': rec.state_id.id or False,
                        'zip': rec.zip,
                        'country_id': rec.country_id.id or False,
                        'email': rec.email_from,
                        'phone': rec.phone,
                        'mobile': rec.mobile,
                        'is_leads': True,
                        'type': 'contact'
                    })
                    rec.partner_id = cust_id.id
            return res

    def default_get(self, fields):
        rec = super(Lead, self).default_get(fields)
        number_of_repetition = self.env['ir.config_parameter'].sudo().get_param('equip3_crm_operation.number_of_repetition')
        rec.update({
            "salesperson_lines": [(0, 0, {'salesperson_id': self.env.uid, 'weightage': 100, 'status': 'main'})],
            "number_of_repetition": number_of_repetition,
        })
        return rec

    @api.onchange('stage_id')
    def _onchange_stage_id(self):
        for rec in self:
            if rec.stage_id.is_won:
                raise UserError(_('Please use Mark Won button !'))
            if rec.stage_id.is_lost:
                raise UserError(_('Please use Mark Lost button !'))
            if rec.stage_id.is_won:
                rec.probability = 100
                rec.probability_new = 100
                rec.partner_id.write({
                    'is_leads' : False,
                    'is_customer' : True,
                    'customer_rank' : 1
                })
            elif rec.stage_id.change_probability:
                rec.probability = rec.stage_id.probability
                rec.probability_new = rec.stage_id.probability

    @api.depends('has_budget','decision_maker', 'partner_name', 
                'street2', 'street', 'city', 'state_id', 'zip', 
                'country_id', 'website', 'scale', 'meeting_ids', 'meeting_ids.state',
                'order_ids', 'order_ids.state')
    def _compute_einstein_score(self):
        for rec in self:
            total = 0
            message = "<div class='einstein_score_text ml-5 mt-4'><p class='mb-4 top_positive'>Top Positives</p>"
            if rec.decision_maker:
                total += 10
                message += "<p>Decision Maker is True</p>"
            else:
                message += "<p>Decision Maker is False</p>"
            if rec.has_budget:
                total += 10
                message += "<p>Has Budget is True</p>"
            else:
                message += "<p>Has Budget is False</p>"
            all_fields_filled = 0
            if rec.partner_name:
                total += 7
                all_fields_filled += 1
            if rec.street2 or rec.street or rec.city or rec.state_id or rec.zip or rec.country_id:
                total += 7
                all_fields_filled += 1
            if rec.website:
                total += 6
                all_fields_filled += 1
            if all_fields_filled == 3:
                message += "<p>Company is Specified</p>"
            elif all_fields_filled == 1 or all_fields_filled == 2:
                message += "<p>Company is Almost Specified</p>"
            else:
                message += "<p>Company is Not Specified</p>"

            if rec.scale and rec.scale == "large":
                total += 20
                message += "<p>Company Scale is Large</p>"
            elif rec.scale and rec.scale == "medium":
                total += 15
                message += "<p>Company Scale is Medium</p>"
            elif rec.scale and rec.scale == "small":
                total += 10
                message += "<p>Company Scale is Small</p>"
            meeting_count = rec.meeting_ids.filtered(lambda r:r.state in ('meeting', 'done'))
            if len(meeting_count) == 1:
                total += 5
                message += "<p>1 Meeting</p>"
            elif len(meeting_count) == 2:
                total += 10
                message += "<p>2 Meetings</p>"
            elif len(meeting_count) == 3:
                total += 15
                message += "<p>3 Meetings</p>"
            elif len(meeting_count) > 3:
                total += 20
                message += "<p>%d Meetings</p>" %(len(meeting_count))
            if len(rec.order_ids.filtered(lambda r:r.state != 'cancel')) > 0:
                total += 20
                message += "<p>Quotation is Created</p>"
            message += "</div>"
            rec.einstein_score = total
            rec.einstein_score_text = message

    @api.depends('meeting_ids', 'meeting_ids.state')
    def _compute_meeting(self):
        for rec in self:
            # meeting_count = len(rec.meeting_ids)
            meeting_count = len(rec.meeting_ids.filtered(lambda r: r.state in ('meeting', 'done')))
            if meeting_count == 1:
                rec.only_one_meeting = True
            else:
                rec.only_one_meeting = False
            if meeting_count >= 1:
                rec.one_metting = True
                rec.one_metting_int = 1
            else:
                rec.one_metting = False
                rec.one_metting_int = 0
            if meeting_count > 1:
                rec.multiple_metting = True
                rec.multiple_metting_int = 1
            else:
                rec.multiple_metting = False
                rec.multiple_metting_int = 0

    def action_set_won_rainbowman(self):
        res = super(Lead, self).action_set_won_rainbowman()
        self.probability_new = 100
        self.probability = 100
        if self.partner_id:
            self.partner_id.write({
                'is_leads' : False,
                'is_customer' : True,
                'customer_rank' : 1
            })
        return res

    def action_set_automated_probability(self):
        res = super(Lead,self).action_set_automated_probability()
        self.write({'probability_new': self.automated_probability_new})

    @api.depends('stage_id','stage_id.probability')
    def _compute_probabilities_new(self):
        for lead in self:
            was_automated = lead.active and tools.float_compare(lead.probability_new, lead.automated_probability_new, 2) == 0
            if lead.stage_id.change_probability:
                lead.automated_probability_new = lead.stage_id.probability or 0
            if was_automated:
                lead.probability_new = lead.automated_probability_new

    @api.depends('probability_new', 'automated_probability_new')
    def _compute_is_automated_probability(self):
        """ If probability and automated_probability are equal probability computation
        is considered as automatic, aka probability is sync with automated_probability """
        # super(Lead,self)._compute_is_automated_probability()
        for lead in self:
            lead.is_automated_probability = tools.float_compare(lead.probability_new, lead.automated_probability_new, 2) == 0

    def action_schedule_meeting(self):
        res = super(Lead,self).action_schedule_meeting()
        is_multi_salesperson = self.env.user.id in self.env.ref('equip3_crm_operation.group_use_multi_salesperson_on_leads').users.ids
        partner_ids = []
        meeting_salesperson_lines = []
        if is_multi_salesperson and self.salesperson_lines:
            for line in self.salesperson_lines:
                partner_ids.append(line.salesperson_id.partner_id.id)
                # vals = {
                #     'salesperson_id':line.salesperson_id.id,
                #     'weightage':line.weightage,
                #     'status':line.status,
                # }
                meeting_salesperson_lines.append(line.salesperson_id.id)

        else:
            partner_ids = self.env.user.partner_id.ids
        if self.partner_id:
            partner_ids.append(self.partner_id.id)
        
        res['context']['default_meeting_salesperson_ids'] = [(6,0,meeting_salesperson_lines)]
        res['context']['default_partner_ids'] = partner_ids
        res['context']['search_default_meeting'] = 1
        res['domain'] = [('opportunity_id', '=', self.id)]
        return res

    # SET FALSE ALL BOOLEAN DEFAULT ODOO IN GENERAL SETTINGS SECTION CRM>LEAD GENERATION
    @api.model
    def _set_false_boolean_lead_generation(self):
        self.env["ir.config_parameter"].sudo().set_param("crm.module_crm_iap_lead_website", False)
        self.env["ir.config_parameter"].sudo().set_param("crm.module_crm_iap_lead_enrich", False)
        self.env["ir.config_parameter"].sudo().set_param("crm.module_crm_iap_lead", False)
        self.env["ir.config_parameter"].sudo().set_param("crm.module_mail_client_extension", False)
        to_uninstall_modules_name = ['crm_iap_lead','crm_iap_lead_website','crm_iap_lead_enrich','mail_client_extension']
        IrModule = self.env['ir.module.module']
        to_uninstall_modules = self.env['ir.module.module']
        for module_name in to_uninstall_modules_name:
            module = IrModule.sudo().search([('name', '=', module_name)], limit=1)
            if module.state in ('installed', 'to upgrade'):
                to_uninstall_modules += module
        if to_uninstall_modules:
            to_uninstall_modules.sudo().button_immediate_uninstall()

    def action_set_won_rainbowman(self):
        res = super().action_set_won_rainbowman()
        for rec in self:
            if rec.salesperson_lines:
                for line in rec.salesperson_lines:
                    target = self.env['crm.target'].search([('salesperson_id','=',line.salesperson_id.id),('state','=','approved'),('start_date','<=',fields.Date.today()),('end_date','>=',fields.Date.today())])
                    if target:
                        if target.based_on == 'expected_revenue':
                            target.current_achievement += rec.expected_revenue * (line.weightage / 100)
        return res
    
    