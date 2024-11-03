import math
from ...equip3_general_features.models.email_wa_parameter import EmailParam
from odoo import models,fields,api,_
from lxml import etree
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime, timedelta, time
import pandas as pd
from datetime import date as dateonly
from pytz import timezone
from odoo.exceptions import ValidationError


class applicantSchedullingMeeting(models.Model):
    _name='applicant.schedulling.meeting'
    _description = 'Applicant Scheduling Meeting'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char()
    recruiter = fields.Many2many('res.users')
    date_from = fields.Date()
    date_to = fields.Date()
    calendar_count = fields.Integer(compute='_get_calendar_count')
    line_ids = fields.One2many('applicant.schedulling.meeting.line','meeting_id')
    is_hide_generate = fields.Boolean(default=False)
        
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=False, submenu=False):
        res = super(applicantSchedullingMeeting, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=True)
        root = etree.fromstring(res['arch'])
        root.set('duplicate', 'false')
        res['arch'] = etree.tostring(root)
        
        return res

    def _get_calendar_count(self):
        for record in self:
            count =0
            meeting_count = self.env['applicant.schedulling.meeting.result'].search([('meeting_id','=',record.id)])
            if meeting_count:
                for data in meeting_count:
                    count+=1
            record.calendar_count = count
    def days_between(self,d1, d2):
        d1 = datetime.strptime(d1, DEFAULT_SERVER_DATE_FORMAT)
        d2 = datetime.strptime(d2, DEFAULT_SERVER_DATE_FORMAT)
        return abs((d2 - d1).days)
    
    
    def gey_days_list(self):
        if self.line_ids:
            days = [data.days for data in self.line_ids]
            return days
        return False
    
    def days_string(self,day):
        date_string = pd.Timestamp(day).day_name()
        return date_string
            
        
    def get_clock(self,days_string):
        line = self.line_ids.filtered(lambda line:line.days == str(days_string).lower())
        if line:
            return line
            
    def create_shcedule_object(self,date,recruiter,day_string):
        clock = self.get_clock(day_string)
        for data_line in clock:
            data = {'interviewer':recruiter.id,
                    'date':date,
                    'from_time':data_line.from_time,
                    'to_time':data_line.to_time,
                    'applicant_slots':data_line.applicant_slots,
                    'meeting_id':self.id
                    
                    }
        
            self.env[calendarSchedullingMeetingResult._name].create(data)
        
    
    def create_schedule(self,recruiter):
        date_range= self.days_between(str(self.date_from),str(self.date_to))
        days = -1 
        date_from = datetime.strptime(str(self.date_from),DEFAULT_SERVER_DATE_FORMAT)
        for range_schecule in range(date_range + 1):
            days+=1
            date_for_create = date_from + timedelta(days=days)
            day_string = self.days_string(date_for_create)
            day_list = self.gey_days_list()
            if str(day_string).lower() in day_list:
                self.create_shcedule_object(date_for_create,recruiter,day_string)
            
            
    def get_applicant(self,applicant_list):
        for data in applicant_list:
            data.invitation_interview()
            data.is_invite = True
    
    
    def action_generate(self):
        for record in self:
            applicant_list =  self.env['hr.applicant'].search([('user_id','in',record.recruiter.ids),('is_invite','=',False)])
            if applicant_list:
                self.get_applicant(applicant_list)
                
            for recruiter in record.recruiter:
                self.create_schedule(recruiter)
            record.is_hide_generate = True
                
                
    
    def get_calendar(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Schedulling Meeting'),
            'res_model': 'applicant.schedulling.meeting.result',
            'view_mode': 'calendar,tree',
            'domain': [('meeting_id','=',self.id)],
            'context':{}
          
        }
    
    @api.constrains('date_from', 'create_date')
    def _check_is_date_from_less_than_create_date(self):
        for record in self:
            if record.date_from < record.create_date.date():
                raise ValidationError(_("The start date shoud be greater than the current date/creation date."))
    
    @api.constrains('date_to', 'date_from')
    def _check_is_date_to_less_than_date_from(self):
        for record in self:
            if record.date_to < record.date_from:
                raise ValidationError(_("The end date should past the start date."))
    
    @api.constrains('line_ids')
    def _check_availability_lines(self):
        for record in self:
            if record.line_ids:
                prev_days = None
                prev_from_time = None
                prev_to_time = None
                for availability in record.line_ids:
                    if prev_days != availability.days:
                        prev_days = availability.days
                        prev_from_time = availability.from_time
                        prev_to_time = availability.to_time

                        from_time_hours = int(availability.from_time)
                        from_time_minutes = round((availability.from_time - from_time_hours) * 60)
                        from_time_str = '{:02d}:{:02d}'.format(from_time_hours, from_time_minutes)

                        to_time_hours = int(availability.to_time)
                        to_time_minutes = round((availability.to_time - to_time_hours) * 60)
                        to_time_str = '{:02d}:{:02d}'.format(to_time_hours, to_time_minutes)

                        try:
                            converted_from_time = datetime.strptime(from_time_str, '%H:%M')
                            converted_to_time = datetime.strptime(to_time_str, '%H:%M')
                        except ValueError:
                            raise ValidationError(_("The range of time must be in between 00:00 - 23:59"))

                        try:
                            duration = converted_to_time - converted_from_time
                            duration_str = str(duration).split(':')
                            duration_obj = timedelta(
                                hours=int(duration_str[0]),
                                minutes=int(duration_str[1]),
                                seconds=int(duration_str[2]))
                            total_seconds = duration_obj.total_seconds()
                            total_minutes = int(total_seconds // 60)
                        except ValueError:
                            raise ValidationError(_("The start hours should be less than end hour."))

                        if total_minutes >= 10:
                            if availability.applicant_slots <= 0:
                                raise ValidationError(_("The applicant slots should be more than 0"))
                        else:
                            raise ValidationError(_("The meeting duration should be at least 10 minutes"))
                    else:
                        if prev_days == availability.days:
                            from_time_hours = int(availability.from_time)
                            from_time_minutes = round((availability.from_time - from_time_hours) * 60)
                            from_time_str = '{:02d}:{:02d}'.format(from_time_hours, from_time_minutes)

                            to_time_hours = int(availability.to_time)
                            to_time_minutes = round((availability.to_time - to_time_hours) * 60)
                            to_time_str = '{:02d}:{:02d}'.format(to_time_hours, to_time_minutes)

                            try:
                                converted_from_time = datetime.strptime(from_time_str, '%H:%M')
                                converted_to_time = datetime.strptime(to_time_str, '%H:%M')
                            except ValueError:
                                raise ValidationError(_("The range of time must be in between 00:00 - 23:59"))

                            try:
                                duration = converted_to_time - converted_from_time
                                duration_str = str(duration).split(':')
                                duration_obj = timedelta(
                                    hours=int(duration_str[0]),
                                    minutes=int(duration_str[1]),
                                    seconds=int(duration_str[2]))
                                total_seconds = duration_obj.total_seconds()
                                total_minutes = int(total_seconds // 60)
                            except ValueError:
                                raise ValidationError(_("The start hours should be less than end hour."))

                            if total_minutes >= 10:
                                if availability.applicant_slots <= 0:
                                    raise ValidationError(_("The applicant slots should be more than 0"))
                            else:
                                raise ValidationError(_("The meeting duration should be at least 10 minutes"))
                            
                            if availability.from_time >= prev_from_time and availability.from_time <= prev_to_time:
                                raise ValidationError(_("The range of the start time and end time of the same day must not overlap each other"))
            else:
                raise ValidationError(_("Availabillity field is required"))
    
    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('schedulling.sequence')
        res = super(applicantSchedullingMeeting, self).create(vals)
        return res
    
class applicantSchedullingMeetingLine(models.Model):
    _name='applicant.schedulling.meeting.line'
    _description = 'Line Scheduling Meeting'
    
    meeting_id = fields.Many2one('applicant.schedulling.meeting')
    days = fields.Selection([('monday','Monday'),('tuesday','Tuesday'),
                             ('wednesday','Wednesday'),
                             ('thursday','Thursday'),
                             ('friday','Friday'),
                             ('saturday','Saturday'),
                             ('sunday','Sunday')
                             ])
    from_time =  fields.Float("From")
    to_time =  fields.Float("To")
    applicant_slots = fields.Integer("Applicant Slots")
    
class calendarSchedullingMeetingResultHistory(models.Model):
    _name = 'applicant.schedulling.meeting.result.history'

    name = fields.Char("Title")
    when = fields.Text("When")
    location = fields.Char("Location")
    status = fields.Char("Status")
    reasons = fields.Char("Reasons")
    applicant_id = fields.Many2one("hr.applicant",'Applicant')
    meeting_result_id = fields.Many2one('applicant.schedulling.meeting.result')

class calendarSchedullingMeetingResult(models.Model):
    _name = 'applicant.schedulling.meeting.result'
    
    _rec_name= 'title'
    
    
    name = fields.Text(compute='_compute_name')
    title = fields.Text(compute='_compute_title')
    meeting_id = fields.Many2one('applicant.schedulling.meeting')
    applicant_id = fields.Many2one('hr.applicant','Applicant')
    date = fields.Date()
    from_time =  fields.Float("From")
    to_time =  fields.Float("To")
    interviewer = fields.Many2one('res.users')
    applicant_slots = fields.Integer("Applicant Slots")
    line_ids = fields.One2many("applicant.schedulling.meeting.result.confirmed",'parent_id')
    applicant_ids =  fields.Many2many('hr.applicant', column1='meeting_id', column2='applicant_id', string='Applicants',compute='_get_applicant_ids')
    is_applicant = fields.Boolean(compute='_compute_is_applicant')
    is_applicant_shadow = fields.Boolean()
    calendar_event_id = fields.Many2one('calendar.event')
    history_line_ids = fields.One2many("applicant.schedulling.meeting.result.history",'meeting_result_id')
    
    
    
    def get_date_now(self):
        return datetime.now().date()
        
    def get_name_list(self):
        name_list = []
        today_name_list = self.search([('interviewer','=',self.interviewer.id),('date','=',datetime.now(timezone(self.env.user.tz if self.env.user.tz else 'UTC')).date())])
        for data in today_name_list:
            time = '{0:02.0f}:{1:02.0f}'.format(*divmod(data.from_time * 60, 60))
            name_list.extend([f"-{record.partner_name}-{record.job_id.name}-{time}" for record in data.applicant_ids])
        return name_list
    
    def _send_email_reminder(self):
        context = EmailParam()
        context.set_email(self.interviewer.email)
        template = self.env.ref('equip3_hr_recruitment_extend.mail_template_reminder_interviewer')
        my_context = self.env.context = dict(self.env.context)
        my_context.update(context.get_context())
        template.send_mail(self.id, force_send=True)
        template.with_context(my_context)
        
    
    @api.model
    def _cron_reminder_schedule(self):
        query_parameter = []
        query_statement = """
                    SELECT distinct  interviewer from applicant_schedulling_meeting_result WHERE date = %s AND is_applicant_shadow IS TRUE
                """
        query_parameter.append(datetime.now(timezone(self.env.user.tz if self.env.user.tz else 'UTC')).date())
        self.env.cr.execute(query_statement, query_parameter)
        applicant_limit_ids = self._cr.dictfetchall()
        if applicant_limit_ids:
            meeting_result_ids = set([data['interviewer'] for data in applicant_limit_ids])
            for interviewer in meeting_result_ids:
                result_to_send = self.search([('interviewer','=',interviewer)],limit=1)
                result_to_send._send_email_reminder()
            
    
    
    @api.depends('applicant_ids')
    def _compute_is_applicant(self):
        for record in self:
            if len(record.applicant_ids) > 0:
                record.is_applicant = True
                record.is_applicant_shadow = True
            else:
                record.is_applicant = False
                record.is_applicant_shadow = False
    
    
    def _compute_name(self):
        for record in self:
            hour_from, minute_from = self.float_time_convert(record.from_time)
            hour_to, minute_to = self.float_time_convert(record.to_time)
            if minute_from == 0:
                minute_from = f"00"
            if  minute_to == 0:
                minute_to = f"00"
            applicant_name_ids = [f"-{data.name}({data.job_id.name})" for data in record.applicant_ids]
            name_ids = "\n".join(applicant_name_ids)
            record.name = f"{name_ids}"
            
            
    def _compute_title(self):
        for record in self:
            hour_from, minute_from = self.float_time_convert(record.from_time)
            hour_to, minute_to = self.float_time_convert(record.to_time)
            if minute_from == 0:
                minute_from = f"00"
            if  minute_to == 0:
                minute_to = f"00"
            applicant_name_ids = [f"{data.name}" for data in record.applicant_ids]
            name_ids = ",".join(applicant_name_ids)
            record.title = f"{record.interviewer.name} {name_ids}"
        
    
    
    def float_time_convert(self, float_val):    
        factor = float_val < 0 and -1 or 1    
        val = abs(float_val)    
        return (factor * int(math.floor(val)), int(round((val % 1) * 60)))
        
    # @api.model
    # def name_get(self):
    #     result = []
    #     for record in self:
    #         applicant_name_ids = [f"{record.name}" for data in record.applicant_ids]
    #         name_ids = ",".join(applicant_name_ids)
    #         result.append((record.id, f"{name_ids}"))
    #     return result


    def _get_applicant_ids(self):
        for record in self:
            applicant_ids = []
            for line in record.line_ids:
                if line.applicant_id:
                    applicant_ids.append(line.applicant_id.id)
            if applicant_ids:
                applicant_ids = [(6, 0, applicant_ids)]
            else:
                applicant_ids = False
            record.applicant_ids = applicant_ids

    def get_list_schedule(self):
        today = dateonly.today()
        result = self.env['applicant.schedulling.meeting.result'].sudo().search([('applicant_slots','>',0),('meeting_id','!=',False),('date','>=',today)],order='date asc, from_time asc')
        return result
    
    def get_time_already_schedule(self,applicant_id):
        schedule = []
        print(applicant_id,'applicant_idapplicant_idapplicant_id')
        if applicant_id:
            applicant_id = int(applicant_id)
        count = ((self.to_time - self.from_time)*60) / self.applicant_slots
        count = count / 60
        time = self.from_time
        endtime = self.to_time 
        schedule.append('{0:02.0f}:{1:02.0f}'.format(*divmod(time * 60, 60))+' - '+'{0:02.0f}:{1:02.0f}'.format(*divmod(endtime * 60, 60)))
        if self.applicant_slots <= len(self.applicant_ids.ids):
            schedule = []
        if applicant_id:
            if schedule and applicant_id in self.applicant_ids.ids:
                schedule = []
        # applicant_slots = self.applicant_slots
        # c_applicant_slots = 1
        # if applicant_slots:
        #     while c_applicant_slots != applicant_slots:
        #         c_applicant_slots+=1
        #         time+=count
        #         schedule.append('{0:02.0f}:{1:02.0f}'.format(*divmod(time * 60, 60)))
        #     for line in self.line_ids:
        #         time = '{0:02.0f}:{1:02.0f}'.format(*divmod(line.time * 60, 60))
        #         schedule.remove(time)
        return schedule


    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=False, submenu=False):
        res = super(calendarSchedullingMeetingResult, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=True)
        root = etree.fromstring(res['arch'])
        root.set('create', 'false')
        root.set('edit', 'false')
        root.set('delete', 'false')
        res['arch'] = etree.tostring(root)
        
        return res


class calendarSchedullingMeetingResultconfirmed(models.Model):
    _name = 'applicant.schedulling.meeting.result.confirmed'

    applicant_id = fields.Many2one('hr.applicant','Applicant')
    date = fields.Date("Date",related='parent_id.date')
    time =  fields.Float("Time")
    parent_id = fields.Many2one("applicant.schedulling.meeting.result",ondelete='cascade')
    interviewer = fields.Many2one('res.users',related='parent_id.interviewer')
    from_time =  fields.Float("From",related='parent_id.from_time')
    to_time =  fields.Float("To",related='parent_id.to_time')
    
    
    
    def float_time_convert(self, float_val):    
        factor = float_val < 0 and -1 or 1    
        val = abs(float_val)    
        return (factor * int(math.floor(val)), int(round((val % 1) * 60)))
        
    
    def name_get(self):
        result = []
        for record in self:
            hour_from, minute_from = self.float_time_convert(record.time)
            if minute_from == 0:
                minute_from = f"00"
            if hour_from == 0:
                hour_from = f"00"
            result.append((record.id, f"{record.applicant_id.partner_name} {hour_from}:{minute_from}"))
        return result
    