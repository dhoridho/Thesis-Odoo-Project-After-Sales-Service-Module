# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import base64
import os

import xlsxwriter
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _
from odoo.modules import get_module_path


class HrRecruitmentStageLine(models.Model):
    _name = "job.stage.line"
    _inherit = ['mail.thread']
    _rec_name = 'stage_id'
    _order = "sequence"
    sequence = fields.Integer(
        "Sequence",
        help="Gives the sequence order when displaying a list of stages.")
    stage_id = fields.Many2one('hr.recruitment.stage', string="Stages", ondelete='cascade')
    fold = fields.Boolean(related='stage_id.fold')
    user_ids = fields.Many2many('res.users', string="PIC")
    remarks = fields.Text("Remarks")
    job_id = fields.Many2one('hr.job', "Job", ondelete='cascade')
    aplicant_ids = fields.One2many('hr.applicant', 'stage_replace_id')
    survey_id = fields.Many2one('survey.survey',"Technical Test")
    interview_id = fields.Many2one('survey.survey',"Interview")
    min_qualification = fields.Integer("Min Technical Score")
    min_skills_score = fields.Integer("Min Skills Score")
    min_personality_score = fields.Integer("Min Personality Score")
    stage_failed = fields.Many2one('hr.recruitment.stage', 'If Fail Move To', domain=[])
    is_apply_stage = fields.Boolean("First Stage")
    user_ids_hashgroup = fields.Many2many('res.users','user_flag','user_id',compute='hash_group_compute')
    template_wa_ids = fields.Many2many('master.template.message')
    is_final_stage = fields.Boolean("Final Stage")
    
         
    
    # @api.constrains('is_apply_stage','sequence')
    # def _constrain_is_apply_stage(self):
    #     for data in self:
    #         if data.is_apply_stage or data.sequence:
    #              other_stage = self.search([('job_id','=',self._origin.job_id.id)],order='sequence asc')
    #              list_sequence = [other.sequence for other in other_stage]
    #              if list_sequence:
    #                  if data.is_apply_stage:
    #                     if data.sequence != min(list_sequence):
    #                         raise ValidationError(f"The stage you are attempting to reorder: {data.stage_id.name}, is marked as a First Stage. Change the First Stage before reordering.")
                
  
      
    @api.onchange('is_apply_stage')
    def _onchange_is_apply_stage(self):
         for data in self:
             if data.is_apply_stage:
                 data.sequence = 0
                 other_stage = self.search([('job_id','=',self._origin.job_id.id),('id','!=',self._origin.id)],order='sequence asc')
                 new_seq = 1
                 if other_stage:
                     for line in other_stage:
                         new_seq += 1
                         line.sequence = new_seq
    
    @api.onchange('is_final_stage')
    def _onchange_is_final_stage(self):
         for data in self:
             if data.is_final_stage:
                other_stage = self.search([('job_id','=',self._origin.job_id.id),('id','!=',self._origin.id)],order='sequence asc')
                new_seq = 1
                if other_stage:
                    for line in other_stage:
                        new_seq += 1
                        line.sequence = new_seq
                    new_seq += 1
                data.sequence = new_seq
                     
 
 
 
 
    def hash_group_compute(self):
        for record in self:
            if record.id or record.stage_id:
                user=self.env['res.users'].search([])
                if user:
                    list = []
                    data = [line.id for line in user.filtered(lambda line:line.has_group('equip3_hr_accessright_settings.equip3_group_hr_recruitment_user'))]
                    list.extend(data)
                    if data:
                        record.user_ids_hashgroup = [(6,0,list)]
                    else:
                        record.user_ids_hashgroup = False
                else:
                    record.user_ids_hashgroup = False
            else:
                record.user_ids_hashgroup = False





    def send_notificaion_email(self):
        self.ensure_one()
        for user in self.user_ids:
            context = self.env.context = dict(self.env.context)
            context.update({
                'email_to': user.email,
                'name': user.name,
                'job_position': self.job_id.name
            })
            template = self.env.ref('equip3_hr_recruitment_extend.mail_template_applicant_list_stage')
            module_path = get_module_path('equip3_hr_recruitment_extend')
            fpath = module_path + '/generated_files'
            if not os.path.isdir(fpath):
                os.mkdir(fpath)
            workbook = xlsxwriter.Workbook(
                module_path + '/generated_files/' + f'{self.stage_id.name}-applicant' + '.xlsx')
            worksheet = workbook.add_worksheet()
            bold = workbook.add_format({
                'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter'})
            centerformmat = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
            })

            worksheet.write('A1', 'Name', bold)
            worksheet.write('B1', 'Job Position', bold)
            worksheet.write('C1', 'Email', bold)
            worksheet.write('D1', 'Score From Previous Stage', bold)
            row = 0
            col = 0
            worksheet.set_column(0, 5, 17)
            for record in self.aplicant_ids:
                row += 1
                worksheet.write(row, col, record.partner_name, centerformmat)
                worksheet.write(row, col + 1, record.job_id.name, centerformmat)
                worksheet.write(row, col + 2, record.email_from, centerformmat)
                worksheet.write(row, col + 3, record.previous_score, centerformmat)
            workbook.close()

            csv_filename = f'{self.stage_id.name}-applicant' + '.xlsx'
            with open(module_path + '/generated_files/' + csv_filename, 'rb') as opened_file:
                base64_csv_file = base64.b64encode(opened_file.read())
                attachment = self.env['ir.attachment'].create({
                    'name': csv_filename,
                    'type': 'binary',
                    'datas': base64_csv_file
                })
            template.attachment_ids = [(5, 0, 0)]
            template.attachment_ids = [(4, attachment.id)]
            template.send_mail(self.id, force_send=True)
            template.with_context(context)

            notification_ids = [((0, 0, {
                'res_partner_id': user.partner_id.id,
                'notification_type': 'inbox'}))]

            self.stage_id.message_post(
                body=f"Hello {user.name} \n"
                      f"You Have some applicant that already on your recruitment stages for {self.job_id.name} position",
                message_type='notification',
                author_id=self.env.user.partner_id.id,
                partner_ids=[user.partner_id.id],
                attachment_ids=[attachment.id],
                needaction_partner_ids=[user.partner_id.id],
                notification_ids=notification_ids
            )

    def unlink(self):
        job_id = self.job_id.id
        for data in self:  
            applicant = self.env['hr.applicant'].search([('stage_id','=',data.stage_id.id),('job_id','=',data.job_id.id)])
            if applicant:
                raise ValidationError(f"The stage you are attempting to delete contains an applicant data. Before you delete this stage: {data.stage_id.name}, move the applicant(s) to another stage.")
        res = super(HrRecruitmentStageLine, self).unlink()
        HrJob = self.env['hr.job'].search([('id','=',job_id)], limit=1)
        sequence_no = 1
        for stage in HrJob.stage_ids:
            stage.sequence = sequence_no
            sequence_no += 1
        return res