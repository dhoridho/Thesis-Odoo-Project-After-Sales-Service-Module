
from odoo import models, fields, api, tools
from datetime import datetime, date
from odoo.exceptions import ValidationError
import requests
import time
from operator import itemgetter
from ...equip3_general_features.models.email_wa_parameter import waParam
headers = {'content-type': 'application/json'}
import logging
_logger = logging.getLogger(__name__)
class MailActivity(models.Model):
    _inherit = 'mail.activity'

    attachment_ids = fields.Many2many(
        'ir.attachment', 'mail_activity_attachment_rel',
        'message_id', 'attachment_id',
        string='Attachments')
    is_attachment_required = fields.Boolean(related='activity_type_id.attachment_required')
    list_user_ids = fields.Many2many('res.users', compute='_compute_list_users', store=True)
    list_partner_ids = fields.Many2many('res.partner', compute='_compute_list_users', store=True)
    done = fields.Boolean('Done', compute='_compute_list_users', store=False)
    opportunity_id = fields.Many2one('crm.lead', string="Opportunity", compute="_compute_opportunity_id", store=True)
    user_ids = fields.Many2many(related='opportunity_id.user_ids', string="Salesperson")
    customer_id = fields.Many2one(related='opportunity_id.partner_id', string="Customer")

    @api.depends('res_model','res_id')
    def _compute_opportunity_id(self):
        for rec in self:
            opportunity_id = False
            if rec.res_model == "crm.lead":
                crm_lead = self.env['crm.lead'].browse(rec.res_id)
                if crm_lead:
                    opportunity_id = crm_lead.id
            rec.opportunity_id = opportunity_id

    @api.depends('calendar_event_id','user_id')
    def _compute_list_users(self):
        for rec in self:
            if rec.calendar_event_id:
                rec.list_user_ids = [(6,0,rec.calendar_event_id.user_ids.ids)]
                rec.list_partner_ids = [(6,0,rec.calendar_event_id.partner_ids.ids)]
            else:
                rec.list_user_ids = [(6,0,rec.user_id.ids)]
                rec.list_partner_ids = [(6,0,rec.user_id.partner_id.ids)]
            rec.done = True

    def activity_format(self):
        res = super(MailActivity, self).activity_format()
        for line in res:
            if line.get('attachment_ids'):
                attachment_data = []
                attachment_ids = self.env['ir.attachment'].browse(line.get('attachment_ids'))
                for attachment in attachment_ids:
                    attachment_data.append({
                        'id': attachment.id,
                        'res_id': line.get('res_id'),
                        'res_model': line.get('res_model'),
                        'mimetype': attachment.mimetype,
                        'name': attachment.name,
                        'filename': attachment.name,
                    })
                line['attachment_ids'] = attachment_data
        return res

    @api.model
    def create(self, values):
        res = super(MailActivity, self).create(values)
        if res.res_model == "crm.lead":
            calendar_event_id = False
            if res.calendar_event_id:
                calendar_event_id = res.calendar_event_id.id
            res_activity_obj = self.env['res.mail.activity']
            res_activity_obj.create({
                'name': res.res_name,
                'summary': res.summary,
                'activity_type_id': res.activity_type_id.id,
                'date_deadline': res.date_deadline,
                'calendar_event_id': calendar_event_id,
                'state': res.state,
                'res_id': res.res_id,
                'act_id': res.id,
                'user_id': res.user_id.id,
                'attachment_ids': res.attachment_ids.ids
            })
            if not res.calendar_event_id:
                if res.activity_type_id.attachment_required and not res.attachment_ids:
                    raise ValidationError('Attachments are Required!')
                try:
                    crm_lead = self.env['crm.lead'].browse(res.res_id)
                    number_of_repetition = self.env['ir.config_parameter'].sudo().get_param('equip3_crm_operation.number_of_repetition')
                    crm_lead.number_of_repetition = number_of_repetition
                except:
                    pass
            lead = self.env[res.res_model].browse(res.res_id)
            lead.set_due_date_and_missed()
        return res

    def write(self, vals):
        res = super(MailActivity, self).write(vals)
        for record in self:
            if record.res_model == "crm.lead":
                if not record.calendar_event_id:
                    if record.activity_type_id.attachment_required and not record.attachment_ids:
                        raise ValidationError('Attachments are Required!')
        return res

    @api.model
    def auto_follow_up_leads_sales_team(self):
        start = time.time()
        template_id = self.env.ref('equip3_crm_operation.email_template_leader_team')
        saleperson_template_id = self.env.ref('equip3_crm_operation.email_template_salesperson')
        action_id = self.env.ref('crm.crm_lead_action_pipeline')
        query = """
            select id,user_id from mail_activity where res_model = 'crm.lead' and date_deadline < '%s' order by user_id
        """ % date.today()
        self.env.cr.execute(query)
        activity_ids = self.env.cr.dictfetchall()
        salespersons = self.env['res.users'].browse(list(dict.fromkeys(list(map(itemgetter('user_id'), activity_ids)))))
        seq = 1
        for salesperson in salespersons:
            ids = [
                dictionary['id'] for dictionary in activity_ids
                if dictionary['user_id'] == salesperson.id
            ]
            id_params = ''
            id_params += "id in ({})".format(ids).replace('[','').replace(']','')
            query = """
                select res_id,activity_type_id,date_deadline from mail_activity where {}
            """
            self.env.cr.execute(query.format(id_params))
            data_activity = self.env.cr.dictfetchall()
            leader_user_id = salesperson.sale_team_id and salesperson.sale_team_id.user_id or False
            list_act = []
            leader_activity_filtered = []
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            no = 1
            for activity in data_activity:
                lead = self.env['crm.lead'].sudo().browse(activity['res_id'])
                url = base_url + '/web#action='+ str(action_id.id) + '&view_type=form&model=crm.lead&id='+str(lead.id)
                vals = {
                    'leader':leader_user_id,
                    'salesperson':salesperson,
                    'sales_name':salesperson.name,
                    'lead':lead,
                    'lead_name':lead.name,
                    'name':self.env['mail.activity.type'].browse(activity['activity_type_id']).name,
                    'duedate':activity['date_deadline'].strftime("%Y-%m-%d"),
                    "url":url,
                    "no":no,
                }
                no+=1
                list_act.append(vals)
                if leader_user_id:
                    if vals['leader'] == leader_user_id:
                        vals['no'] = seq
                        leader_activity_filtered.append(vals)
                        seq+=1

            ctx = {
                'email_from' : self.env.user.company_id.email,
                'email_to' : salesperson.email,
                'list_act' : list_act,
                'sales_name': salesperson.name,
            }
            if list_act:
                saleperson_template_id.with_context(ctx).send_mail(list_act[-1]['lead'].id or False)
                self.send_activity_notification(list_act[-1]['lead'], ctx, saleperson_template_id, salesperson)
                self.send_activity_wa(ctx, salesperson, is_leader=False)

            if leader_activity_filtered and leader_user_id:
                ctx_leader = {
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : leader_user_id.email,
                    'list_act' : leader_activity_filtered,
                    'leader_name': leader_user_id.name,
                }
                template_id.with_context(ctx_leader).send_mail(list_act[-1]['lead'].id or False)
                self.send_activity_notification(list_act[-1]['lead'], ctx_leader, template_id, leader_user_id)
                self.send_activity_wa(ctx_leader, leader_user_id, is_leader=True)
        end = time.time()
        print("The time of execution of above program is :",
              (end-start) * 10**3, "ms")



    def send_activity_notification(self, record, ctx, template_id, user):
        if user and user.partner_id:
            body_html = (
                self.env['mail.render.mixin']
                .with_context(ctx)
                ._render_template(
                    template_id.body_html,
                    "crm.lead",
                    record.ids,
                    post_process=True
                )[record.id]
            )
            message_id = (
                self.env["mail.message"]
                    .sudo()
                    .create(
                    {
                        "subject": "AutoFollow Up Notification",
                        "body": body_html,
                        'message_type': 'notification',
                        "model": "crm.lead",
                        "res_id": record.id,
                        "partner_ids": user.partner_id.ids,
                        "author_id": self.env.user.partner_id.id,
                        "notification_ids": [(0, 0, {
                            'res_partner_id': user.partner_id.id,
                            'notification_type': 'inbox'
                        })]
                    }
                )
            )

    def send_activity_wa(self, ctx, user, is_leader=False):
        wa_sender = waParam()
        for record in ctx['list_act']:
            message = "Hello {}!\n".format(user.name)
            if is_leader:
                message += "Your team has *overdue* *activity*, please check below and remind your salesperson to do the follow up.\n\n"
                intro = "Your team has *overdue* *activity*, please check below and remind your salesperson to do the follow up.\n\n"
            else:
                intro = "You have *overdue activity*, please check below and do the follow up.\n\n"
                message += "You have *overdue activity*, please check below and do the follow up.\n\n"
            recap_msg = ""
            # for record in ctx['list_act']:
            recap_msg += self.recap_message_activity_wa(record,is_leader)
            message += recap_msg
            message += "\nThank you.\n*System* *Notification* *Hashmicro*"
            wa_template_id = self.env.ref('equip3_crm_operation.template_overdue_activity_crm_whatsapp')
            string_test = str(tools.html2plaintext(wa_template_id.message))
            if "${nama_tujuan}" in string_test:
                string_test = string_test.replace("${nama_tujuan}", user.name)
            if "${intro}" in string_test:
                string_test = string_test.replace("${intro}", intro)
            if "${message}" in string_test:
                string_test = string_test.replace("${message}", recap_msg)
            if "${br}" in string_test:
                string_test = string_test.replace("${br}", f"\n")
            phone_num = user.partner_id.mobile
            if phone_num:
                phone_num = phone_num.replace("+", "")
            wa_sender.set_wa_string(string_test, wa_template_id._name, template_id=wa_template_id)
            wa_sender.send_wa(phone_num)

    def recap_message_activity_wa(self,act,is_leader=False):
        msg =""
        if is_leader:
            msg += "*Salesperson* : {} \n".format(act['sales_name'])
        msg += "*Leads* : {}\n".format(act['lead_name'])
        msg += "*Activity* *Type* : {} \n".format(act['name'])
        # if act['summary'] :
        #     msg += "*Summary* : {} \n".format(act['summary'])
        # else :
        #     msg += "*Summary* : - \n"
        msg += "*Duedate* : {} \n".format(act['duedate'])
        msg += "---------------------------------------\n"
        return msg

    def _action_done(self, feedback=False, attachment_ids=None):
        for rec in self:
            res_act = self.env['res.mail.activity'].search([('act_id', '=', rec.id)])
            res_act.state = 'done'
            res_act.res_id.set_due_date_and_missed()
        res = super(MailActivity, self)._action_done(feedback=feedback, attachment_ids=attachment_ids)
        return res

    def action_cancel(self):
        for rec in self:
            res_act = self.env['res.mail.activity'].search([('act_id', '=', rec.id)])
            res_act.state = 'cancel'
            rec.unlink()

    @api.depends('date_deadline')
    def _compute_state(self):
        res = super(MailActivity, self)._compute_state()
        for rec in self:
            res_act = self.env['res.mail.activity'].search([('act_id', '=', rec.id)])
            res_act.state = rec.state
        return res

class ResMailActivity(models.Model):
    _name = 'res.mail.activity'
    _description = "Res Mail Activity"

    name = fields.Char("Document Type")
    activity_type_id = fields.Many2one(
        'mail.activity.type', 'Activity Type')
    summary = fields.Text("Summary")
    date_deadline = fields.Date("Due Date")
    calendar_event_id = fields.Many2one('calendar.event', string="Calendar Meeting", ondelete='cascade')
    res_id = fields.Many2one('crm.lead', string="Lead")
    act_id = fields.Many2one('mail.activity', string="Activity ID")
    state = fields.Selection([
        ('overdue', 'Overdue'),
        ('today', 'Today'),
        ('planned', 'Planned'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], 'State')
    user_id = fields.Many2one(
        'res.users', 'Assigned to',
        default=lambda self: self.env.user,
        index=True)
    attachment_ids = fields.Many2many(
        'ir.attachment', 'res_mail_activity_attachment_rel',
        'res_message_id', 'attachment_id',
        string='Attachments')
    state_2 = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Cancel')
    ], default='draft', string="State")
    user_ids = fields.Many2many(related='res_id.user_ids', string="Salesperson")
    customer_id = fields.Many2one(related='res_id.partner_id', string="Customer")
    list_users_ids = fields.Many2many(related='act_id.list_user_ids')
    list_partners_ids = fields.Many2many(related='act_id.list_partner_ids')

    def action_done(self):
        for rec in self:
            rec.state_2 = 'done'
            if rec.calendar_event_id:
                rec.calendar_event_id.state_3 = 'done'
            rec.act_id.action_done()

    def action_cancel(self):
        for rec in self:
            rec.state_2 = 'cancel'
            if rec.calendar_event_id:
                rec.calendar_event_id.state_3 = 'cancel'
            rec.act_id.action_cancel()

