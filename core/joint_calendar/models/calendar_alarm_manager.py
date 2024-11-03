# -*- coding: utf-8 -*-

import logging
import pytz

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class calendar_alarm_manager(models.AbstractModel):
    """
    Re-write to add the feature of notifications by joint events
    """
    _inherit = 'calendar.alarm_manager'

    @api.model
    def _get_next_potential_limit_alarm_joint(self, alarm_type, seconds=None, partner_id=None):
        """
        The method to search for required alarms by joint events
        """
        res = {}
        base_request = """
            SELECT
                cal.id,
                cal.date_start - interval '1' minute  * calcul_delta.max_delta AS first_alarm,
                cal.date_stop - interval '1' minute  * calcul_delta.min_delta AS last_alarm,
                cal.date_start as first_event_date,
                cal.date_stop as last_event_date,
                calcul_delta.min_delta,
                calcul_delta.max_delta
            FROM
                joint_event AS cal
                RIGHT JOIN (
                    SELECT
                        r.joint_event_rel, max(alarm.duration_minutes) max_delta,min(alarm.duration_minutes) min_delta
                    FROM
                        calendar_alarm_joint_event_rel_sp AS r
                            LEFT JOIN calendar_alarm AS alarm ON alarm.id = r.alarm_rel
                    WHERE alarm.alarm_type = %s
                    GROUP BY r.joint_event_rel) AS calcul_delta ON calcul_delta.joint_event_rel = cal.id
        """

        filter_user = """
            RIGHT JOIN calendar_event_res_partner_rel_sp AS part_rel ON part_rel.joint_even_rel = cal.id
                AND part_rel.part_rel = %s
        """
        tuple_params = (alarm_type,)
        if partner_id:
            base_request += filter_user
            tuple_params += (partner_id, )
        # Upper bound on first_alarm of requested events
        first_alarm_max_value = ""
        if seconds is None:
            tuple_params += (300,)
        else:
            tuple_params += (seconds,)

        self.env.cr.execute(
            """SELECT *
                FROM ( %s  ) AS ALL_EVENTS
                WHERE ALL_EVENTS.first_alarm < (now() at time zone 'utc' + interval '%%s' second )
                    AND ALL_EVENTS.last_event_date > (now() at time zone 'utc')
            """ % base_request, tuple_params
        )
        req_result = self.env.cr.fetchall()
        for event_id, first_alarm, last_alarm, first_meeting, last_meeting, min_duration, max_duration in req_result:
            res[event_id] = {
                'event_id': event_id,
                'first_alarm': first_alarm,
                'last_alarm': last_alarm,
                'first_meeting': first_meeting,
                'last_meeting': last_meeting,
                'min_duration': min_duration,
                'max_duration': max_duration,
            }
        return res
    
    @api.model
    def get_next_notif_joint(self):
        """
        The method to add notifications by joint events

        Methods:
         * super
         * _get_next_potential_limit_alarm_joint
         * do_check_alarm_for_one_date
         * _prepare_notification_data

        Returns:
         * list of dicts
        """
        partner = self.env.user.partner_id
        all_notif = []
        if partner:
            time_limit = 3600 * 24  # return alarms of the next 24 hours
            all_joint_events = self._get_next_potential_limit_alarm_joint(
                'notification',
                partner_id=partner.id,
            )
            for event_id in all_joint_events:
                max_delta = all_joint_events[event_id]['max_duration']
                cur_event = self.env['joint.event'].browse(event_id)
                in_date_format = fields.Datetime.from_string(cur_event.date_start)
                last_found = self.do_check_alarm_for_one_date(
                    in_date_format,
                    cur_event,
                    max_delta,
                    time_limit,
                    'notification',
                    after=partner.calendar_last_notif_ack,
                )
                if last_found:
                    for alert in last_found:
                        all_notif.append(self._prepare_notification_data(alert))
        return all_notif

    @api.model
    def action_next_mail_joint(self, context=None):
        """
        The method to find all joint events which require email notification
        
        Methods:
         * _get_next_potential_limit_alarm
         * do_check_alarm_for_one_date
         * _do_mail_reminder_joint
        """
        now = fields.Datetime.now()
        Config = self.env['ir.config_parameter'].sudo()
        last_notif_mail = Config.get_param('joint_calendar.last_notif_mail', default=now)
        cron = self.sudo().env.ref('joint_calendar.invoke_alarm', raise_if_not_found=False)
        if not cron:
            _logger.error("Cron for " + self._name + " can not be identified !")
            return False
       
        interval_to_second = {
            "weeks": 7 * 24 * 60 * 60,
            "days": 24 * 60 * 60,
            "hours": 60 * 60,
            "minutes": 60,
            "seconds": 1,
        }
        if cron.interval_type not in interval_to_second:
            _logger.error("Cron delay can not be computed !")
            return False
        cron_interval = cron.interval_number * interval_to_second[cron.interval_type]
        all_events = self._get_next_potential_limit_alarm_joint('email', seconds=cron_interval)
        for cur_event in self.env['joint.event'].browse(all_events.keys()):
            max_delta = all_events[cur_event.id]['max_duration']
            in_date_format = fields.Datetime.from_string(cur_event.date_start)
            last_found = self.do_check_alarm_for_one_date(
                in_date_format,
                cur_event, 
                max_delta,
                0,
                'email',
                after=last_notif_mail,
                missing=True,
            )
            for alert in last_found:
                self._do_mail_reminder_joint(alert)

        Config.set_param('joint_calendar.last_notif_mail', now)

    @api.model
    def _do_mail_reminder_joint(self, alert):
        """
        The method to prepare email notifications by found joint calendars
        
        Methods:
         * _format_datetime
         * _render_template
         * message_post
        """
        Config = self.env['ir.config_parameter'].sudo()
        event = self.env['joint.event'].browse(alert['event_id'])
        alarm = self.env['calendar.alarm'].browse(alert['alarm_id'])
        local_context = self.env.context.copy()
        template_id = self.env.ref('joint_calendar.notification_by_alarm')
        body_with_tz = {}
        if alarm.alarm_type == 'email':
            user_ids = self.env['res.users'].search([('partner_id', 'in', event.attendee.ids)])
            for user in user_ids:
                if user.tz not in body_with_tz:
                    local_context['display_date'] = self.with_user(user.id)._format_datetime(event.date_start)
                    body_with_tz[user.tz] = template_id.with_context(local_context)._render_template(
                        template_id.body_html,
                        'joint.event',
                        [event.id],
                    ).get(event.id)
                body_html = body_with_tz.get(user.tz, '')
                event.with_context(local_context).message_post(
                    body=body_html,
                    subject=_('Reminder by Event'),
                    subtype_xmlid='joint_calendar.mt_joint_event_notify',
                    partner_ids=[user.partner_id.id],
                )
        return True

    @api.model
    def _format_datetime(self, dt, tz=None):
        """
        The method to make date timezone adapted
        """
        user = self.env.user
        tz = tz or user.tz
        if tz and tz != 'UTC':
            dt = fields.Datetime.from_string(dt)
            dt = pytz.UTC.localize(dt).astimezone(pytz.timezone(tz or user.tz or 'UTC'))
            dt = fields.Datetime.to_string(dt)
        return dt

    @api.model
    def _prepare_notification_data(self, alert):
        """
        Methods to prepare popup notification data

        Returns:
         * dict
        """
        alarm = self.env['calendar.alarm'].browse(alert['alarm_id'])
        event = self.env['joint.event'].browse(alert['event_id'])
        if alarm.alarm_type == 'notification':
            message = self._format_datetime(event.date_start)
            delta = alert['notify_at'] - fields.Datetime.now()
            delta = delta.seconds + delta.days * 3600 * 24
            return {
                'event_id': event.id,
                'action': event.action.id,
                'title': event.name,
                'message': message,
                'timer': delta,
                'notify_at': fields.Datetime.to_string(alert['notify_at']),
                'joint': True,
            }

    def _notify_next_joint_alarm(self, partner_ids):
        """ 
        The method to send through the bus the next alarm of given partners 

        Args:
         * partner_ids - list of partners to notify
        """
        notifications = []
        users = self.env['res.users'].search([('partner_id', 'in', tuple(partner_ids))])
        for user in users:
            notif = self.with_user(user).with_context(allowed_company_ids=user.company_ids.ids).get_next_notif_joint()
            notifications.append([(self._cr.dbname, 'joint.event', user.partner_id.id), notif])
        if len(notifications) > 0:
            self.env['bus.bus'].sendmany(notifications)
