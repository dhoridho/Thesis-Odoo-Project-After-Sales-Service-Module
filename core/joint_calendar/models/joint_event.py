# -*- coding: utf-8 -*-

import itertools

from collections import defaultdict

from odoo import _, api, fields, models

from odoo.exceptions import AccessError


class joint_event(models.Model):
    """
    The key model to show on the joint calendar interface
    """
    _name = "joint.event"
    _inherit = ["mail.activity.mixin", "mail.thread"]
    _description = "Joint Event"

    @api.model
    def _selection_res_reference(self):
        """
        The method to return all available models which might be used to be joined
        """
        self._cr.execute("SELECT model, name FROM ir_model ORDER BY name")
        return self._cr.fetchall()

    @api.model
    def _default_res_model(self):
        """
        Default method for res_model
        """
        return self.env['ir.model'].search([('model', '=', 'joint.event')], limit=1)

    @api.model
    def _default_action(self):
        """
        Default method for action
        """
        action = False
        try:
            action = self.sudo().env.ref('joint_calendar.joint_event_action')
        except:
            action = self.sudo().env['ir.actions.act_window'].search(
                [('res_model', '=', self.res_model_domain)], limit=1
            )
        return action

    @api.depends('res_id', 'res_model')
    def _compute_res_reference(self):
        """
        Compute method for res_reference
        """
        for event in self:
            res_reference = False
            if event.res_model_domain and event.res_id:
                res_reference = '{},{}'.format(event.res_model_domain, event.res_id)
            event.res_reference = res_reference

    @api.depends("attendee")
    def _compute_access_user_ids(self):
        """
        Compute method for access_user_ids
        """
        for event in self:
            event.access_user_ids = event.attendee.mapped("user_ids")

    def _inverse_event_properties(self):
        """
        Inverse method for all event properties: Change parent object, when event is modified
        """
        for event in self:
            if event.res_reference and event.rule_id and event.res_reference._name != self._name:
                item = event.res_reference
                rule = event.rule_id
                data = {}
                if rule.field_start and not rule.field_start.readonly:
                    old_datetime = False
                    if item[rule.field_start.name]:
                        old_datetime = fields.Datetime.from_string(item[rule.field_start.name])
                    new_datetime = False
                    if event.date_start:
                        new_datetime = fields.Datetime.from_string(event.date_start)
                    if old_datetime != new_datetime:
                        data.update({rule.field_start.name: event.date_start,})
                if rule.field_stop and not rule.field_stop.readonly:
                    old_datetime = False
                    if item[rule.field_stop.name]:
                        old_datetime = fields.Datetime.from_string(item[rule.field_stop.name])
                    new_datetime = False
                    if event.date_stop:
                        new_datetime = fields.Datetime.from_string(event.date_stop)
                    if old_datetime != new_datetime:
                        data.update({rule.field_stop.name: event.date_stop,})
                if rule.field_delay \
                        and not rule.field_delay.readonly \
                        and (item[rule.field_delay.name] != event.date_delay):
                    data.update({rule.field_delay.name: event.date_delay,})
                if not rule.always_all_day \
                        and rule.field_all_day \
                        and item[rule.field_start.name] \
                        and item[rule.field_stop.name] \
                        and not rule.field_all_day.readonly \
                        and (item[rule.field_all_day.name] != event.all_day):
                    data.update({rule.field_all_day.name: event.all_day,})
                if rule.field_name and not rule.field_name.readonly and (item[rule.field_name.name] != event.name):
                    data.update({rule.field_name.name: event.name,})
                if rule.field_description \
                        and not rule.field_description.readonly \
                        and (item[rule.field_description.name] != event.description):
                    data.update({rule.field_description.name: event.description,})
                if rule.fields_extra_partner_id \
                        and not rule.fields_extra_partner_id.readonly \
                        and (item[rule.fields_extra_partner_id.name] != event.partner_id):
                    data.update({
                        rule.fields_extra_partner_id.name: event.partner_id.id,
                    })
                if data:
                    item.sudo().write(data)

    def _inverse_res_model(self):
        """
        Inverse method for res_model
        """
        for event in self:
            if event.res_model:
                event.res_model_domain = event.res_model.model
            else:
                event.res_model_domain = 'joint.event'

    def _inverse_res_reference(self):
        """
        Inverse method for res_reference
        """
        for event in self:
            if event.res_reference:
                values = {
                    'res_model_domain': event.res_reference._model._model,
                    'res_id': event.res_reference.id,
                }
            else:
                values = {
                    'res_model_domain': False,
                    'res_id': False,
                }  
            event.write(values)

    name = fields.Char(
        string='Title', 
        required=True,
    )
    res_id = fields.Integer(string='Related Object ID')
    res_model = fields.Many2one(
        'ir.model',
        string='Model',
        default=_default_res_model,
        inverse=_inverse_res_model,
        required=True,
        ondelete="cascade",
    )
    action = fields.Many2one(
        'ir.actions.act_window',
        string='Action',
        domain="[('res_model', '=', res_model_domain)]",
        required=True,
        default=_default_action,
        help='Which form view to open when clicking on an event card',
    )
    res_model_domain = fields.Selection(
        _selection_res_reference,
        string='Target Document',
        default='joint.event',
        required=True,
    )
    joint_calendar_id = fields.Many2one(
        'joint.calendar',
        string='Joint Calendar',
        ondelete="cascade",
    )
    rule_id = fields.Many2one(
        'event.rule',
        string='Rule',
        help='The rule, which makes this event happen',
        ondelete="cascade",
    )
    date_start = fields.Datetime(
        string='Start',
        inverse=_inverse_event_properties,
    )
    date_stop = fields.Datetime(
        string='End',
        inverse=_inverse_event_properties,
    )
    date_delay = fields.Float(
        string='Delay',
        inverse=_inverse_event_properties,
    )
    all_day = fields.Boolean(
        string='Whole Day',
        inverse=_inverse_event_properties,
    )
    attendee = fields.Many2many(
        'res.partner',
        'calendar_event_res_partner_rel_sp',
        'joint_even_rel',
        'part_rel',
        string='Attendees',
        default=lambda self: self.env.user.partner_id,
    )
    access_user_ids = fields.Many2many(
        "res.users",
        "res_user_joint_event_rel_table",
        "res_user_rel_id",
        "joint_event_rel_id",
        compute=_compute_access_user_ids,
        compute_sudo=True,
        store=True,
    )
    description = fields.Html(
        string='Description',
        inverse=_inverse_event_properties,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Contact", 
        inverse=_inverse_event_properties,            
    )
    res_reference = fields.Reference(
        selection='_selection_res_reference',
        string='Parent Object',
        compute=_compute_res_reference,
        inverse=_inverse_res_reference,
    )
    alarm_ids = fields.Many2many(
        'calendar.alarm',
        'calendar_alarm_joint_event_rel_sp',
        'joint_event_rel',
        'alarm_rel',
        string='Alarms',
    )
    privacy = fields.Selection(
        [
            ('public', 'Public'), 
            ('private', 'Private')
        ],
        string='Privacy',
        required=True,
        default='public',
        help="""
            * Public - a joint event would be visible for everybody
            * Private - a joint event would be visible only for attendees
        """,
    )

    @api.model
    def check(self, mode, values=None):
        """
        The method to check rights for joint events
        The rights to joint event are the same as for the parent object.
        The logic is taken for the same mechanics for ir.attachment
        """
        if self.env.is_superuser() or self.env.su:
            return True
        if not (self.env.is_admin() or self.env.user.has_group('base.group_user')):
            raise AccessError(_("Sorry, you are not allowed to access this document."))

        model_ids = defaultdict(set)
        if self:
            self.env['joint.event'].flush(['res_model_domain', 'res_id'])
            self._cr.execute('SELECT res_model_domain, res_id FROM joint_event WHERE id IN %s', [tuple(self.ids)])
            for res_model_domain, res_id in self._cr.fetchall():
                if not (res_model_domain and res_id):
                    continue
                model_ids[res_model_domain].add(res_id)
        if values and values.get('res_model_domain') and values.get('res_id'):
            model_ids[values['res_model_domain']].add(values['res_id'])

        for res_model, res_ids in model_ids.items():
            if res_model not in self.env:
                continue
            if res_model == 'res.users' and len(res_ids) == 1 and self.env.uid == list(res_ids)[0]:
                continue
            records = self.env[res_model].browse(res_ids).exists()
            access_mode = 'write' if mode in ('create', 'unlink') else mode
            records.check_access_rights(access_mode)
            records.check_access_rule(access_mode)

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        """
        Re-write to add check by res_model and res_id (similar to how ir_attachment _search works)
        """
        ids = super(joint_event, self)._search(
            args, offset=offset, limit=limit, order=order, count=False, access_rights_uid=access_rights_uid
        )

        if self.env.is_superuser():
            return len(ids) if count else ids
        if not ids:
            return 0 if count else []

        orig_ids = ids
        ids = set(ids)

        model_joint_events = defaultdict(lambda: defaultdict(set))  
        self._cr.execute(
            """SELECT id, res_model_domain, res_id FROM joint_event WHERE id IN %s""", [tuple(ids)]
        )
        
        for row in self._cr.dictfetchall():
            if not row['res_model_domain']:
                continue
            if row["res_model_domain"] == "mail.activity":
                activity = self.env[row["res_model_domain"]].browse(row["res_id"]).exists()
                if activity:
                    activity = activity.sudo()
                    model_joint_events[activity.res_model][activity.res_id].add(row['id'])
            else:
                model_joint_events[row['res_model_domain']][row['res_id']].add(row['id'])

        for res_model, targets in model_joint_events.items():
            if res_model not in self.env:
                continue
            if not self.env[res_model].check_access_rights('read', False):
                ids.difference_update(itertools.chain(*targets.values()))
                continue
            target_ids = list(targets)
            if res_model != "joint.event":
                # stand alone joint events are checked in _super
                allowed = self.env[res_model].with_context(active_test=False).search([('id', 'in', target_ids)])
                for res_id in set(target_ids).difference(allowed.ids):
                    ids.difference_update(targets[res_id])

        result = [id for id in orig_ids if id in ids]
        if len(orig_ids) == limit and len(result) < len(orig_ids):
            result.extend(self._search(args, offset=offset + len(orig_ids),
                                       limit=limit, order=order, count=count,
                                       access_rights_uid=access_rights_uid)[:limit - len(result)])
        return len(result) if count else list(result)


    def read(self, fields_to_read=None, load='_classic_read'):
        self.check(mode='read')
        return super(joint_event, self).read(fields_to_read, load=load)

    def write(self, vals):
        self.check(mode='write', values=vals)
        res = super(joint_event, self).write(vals)
        self.env["calendar.alarm_manager"]._notify_next_joint_alarm(self.mapped("attendee").ids)
        return res

    def copy(self, default=None):
        if default is None:
            default = {}
        self.check(mode='write')
        return super(joint_event, self).copy(default)

    def unlink(self):
        self.check(mode='unlink')
        self.env["calendar.alarm_manager"]._notify_next_joint_alarm(self.mapped("attendee").ids)
        res = super(joint_event, self).unlink()
        return res

    @api.model
    def create(self, vals):
        self.check(mode='write', values=vals)
        new_event =  super(joint_event, self).create(vals)
        self.env["calendar.alarm_manager"]._notify_next_joint_alarm(self.mapped("attendee").ids)
        return new_event
