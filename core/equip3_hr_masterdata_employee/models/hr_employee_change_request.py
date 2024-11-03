from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import json

class EmployeeChangeRequestImage(models.Model):
    _name = 'employee.change.request.image'
    _inherit = ['image.mixin']
    _order = 'sequence, id'

    name = fields.Char("Name", required=True)
    change_id_str = fields.Char("")
    sequence = fields.Integer(default=10, index=True)
    image = fields.Image(required=True)
    image_detection = fields.Image()
    change_id = fields.Many2one('hr.employee.change.request', "change", index=False, ondelete=False)
    before_change_id = fields.Many2one('hr.employee.change.request', "before change", index=False, ondelete=False)
    after_change_id = fields.Many2one('hr.employee.change.request', "after change", index=False, ondelete=False)
    descriptor = fields.Char("Descriptor FR", readonly=False)

    _sql_constraints = [
        ('check_descriptor', 'check(length(descriptor)>50)', 'Descriptor length must be more then 50'),
    ]

    @api.model
    def create(self, vals):
        parent_obj = self.env['hr.employee.change.request']
        obj = self.env['employee.change.request.image']

        if vals.get('change_id'):
            # query_statement = """DELETE FROM employee_change_request_image WHERE before_change_id = %s and change_id<>%s;"""
            # self.env.cr.execute(query_statement, [vals['change_id'],vals['change_id']])

            # query_statement = """UPDATE employee_change_request_image SET before_change_id=%s, after_change_id=NULL  WHERE after_change_id = %s;"""
            # self.env.cr.execute(query_statement, [vals['change_id'],vals['change_id']])


            if vals.get('o_kanban_button_edit_face_table'):
                query_statement = """DELETE FROM employee_change_request_image WHERE  change_id=%s;"""
                self.env.cr.execute(query_statement, [vals['change_id'],])
                del vals['o_kanban_button_edit_face_table']

                # query_statement = """UPDATE employee_change_request_image SET change_id=NULL WHERE before_change_id = %s;"""
                # self.env.cr.execute(query_statement, [vals['change_id'],])
                # del vals['o_kanban_button_edit_face_table']

                    

            
        rec = super(EmployeeChangeRequestImage, self).create(vals)
        # if vals.get('change_id'):
        #     query_statement = """UPDATE employee_change_request_image SET after_change_id=%s WHERE change_id = %s;"""
        #     self.env.cr.execute(query_statement, [vals['change_id'],vals['change_id']])
        return rec



class HREmployeeChangeRequest(models.Model):
    _name = 'hr.employee.change.request'
    _description = 'Employee Change Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee',string='Employee',default=lambda self:self.env.user.employee_id.id)
    name=fields.Char("Name",related='employee_id.name')
    sequence_code = fields.Char(related='employee_id.sequence_code', string='Employee ID')
    job_id = fields.Many2one(related='employee_id.job_id', string='Job Position')
    department_id = fields.Many2one(related='employee_id.department_id', string='Department')
    location_id = fields.Many2one(related='employee_id.location_id', string='Work Location')
    date_of_joining = fields.Date(related='employee_id.date_of_joining', string='Date of Joining')
    state = fields.Selection([('draft', 'Draft'), ('to_approve', 'To Approve'),
                            ('approved', 'Approved'), ('rejected', 'Rejected')], default='draft', string='Status')
    ## Private Contact & Status ##
    private_email = fields.Char('Email')
    phone = fields.Char('Phone')
    km_home_work = fields.Integer('Home-Work Distance')
    religion_id = fields.Many2one('employee.religion', string='Religion')
    race_id = fields.Many2one('employee.race', string='Race')
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], string='Gender', groups="hr.group_hr_user", tracking=True)
    marital = fields.Many2one('employee.marital.status', string='Marital Status')
    ## Citizenship ##
    country_id = fields.Many2one(
        'res.country', 'Nationality (Country)', groups="hr.group_hr_user", tracking=True)
    state_id = fields.Many2one('res.country.state', "Province(State)")
    identification_id = fields.Char('Identification No')
    passport_id = fields.Char('Passport No')
    birthday = fields.Date('Date of Birth')
    place_of_birth = fields.Char('Place of Birth')
    country_of_birth = fields.Many2one('res.country', string='Country of Birth')
    ## Medical Information ##
    blood_type = fields.Char('Blood Type')
    height = fields.Float('Height (CM)')
    weight = fields.Float('Weight (KG)')
    ## Work Permit ##
    visa_no = fields.Char('Visa No')
    permit_no = fields.Char('Work Permit No')
    visa_expire = fields.Date('Visa Expire Date')

    change_request_line_ids = fields.One2many('hr.employee.change.request.line','change_request_id', string='Change Request')

    address_before_ids = fields.One2many('hr.employee.address.before.change', 'change_request_id', string="Before")
    emergency_before_ids = fields.One2many('employee.emergency.contact.before.change', 'change_request_id', string="Before")
    bank_before_ids = fields.One2many('bank.account.before.change', 'change_request_id', string="Before")
    fam_before_ids = fields.One2many('hr.employee.family.before.change', 'change_request_id', string="Before")
    education_before_ids = fields.One2many('hr.employee.education.before.change', 'change_request_id', string="Before")
    health_before_ids = fields.One2many('employee.health.records.before.change', 'change_request_id', string="Before")

    address_ids = fields.One2many('hr.employee.address', 'change_request_id', string="Addresses")
    emergency_ids = fields.One2many('employee.emergency.contact', 'change_request_id', string="Emergency Contact")
    bank_ids = fields.One2many('bank.account', 'change_request_id', string="Bank Account")
    fam_ids = fields.One2many('hr.employee.family', 'change_request_id', string="Family")
    education_ids = fields.One2many('hr.employee.education', 'change_request_id', string="Education")
    health_ids = fields.One2many('employee.health.records', 'change_request_id', string="Health Record")
    # Get Records
    get_address_ids = fields.One2many('hr.employee.address.change.line', 'change_request_id', string="Addresses")
    get_emergency_ids = fields.One2many('employee.emergency.contact.change.line', 'change_request_id', string="Emergency Contact")
    get_bank_ids = fields.One2many('bank.account.change.line', 'change_request_id', string="Bank Account")
    get_fam_ids = fields.One2many('hr.employee.family.change.line', 'change_request_id', string="Family")
    get_education_ids = fields.One2many('hr.employee.education.change.line', 'change_request_id', string="Education")
    get_health_ids = fields.One2many('employee.health.records.change.line', 'change_request_id', string="Health Record")
    #Many2many Get orginal Records of Modified
    org_address_ids = fields.Many2many('hr.employee.address', string="Addresses List")
    org_emergency_ids = fields.Many2many('employee.emergency.contact',  string="Emergency Contact List")
    org_bank_ids = fields.Many2many('bank.account', string="Bank Account List")
    org_fam_ids = fields.Many2many('hr.employee.family', string="Family List")
    org_education_ids = fields.Many2many('hr.employee.education', string="Education List")
    org_health_ids = fields.Many2many('employee.health.records', string="Health Record List")
    # After Changed Records
    address_after_ids = fields.One2many('hr.employee.address.change.line', 'change_request_id',
                                         string="After", domain=[('is_changed','=', True)])
    emergency_after_ids = fields.One2many('employee.emergency.contact.change.line', 'change_request_id',
                                         string="After", domain=[('is_changed','=', True)])
    bank_after_ids = fields.One2many('bank.account.change.line', 'change_request_id', string="After",  domain=[('is_changed','=', True)])
    fam_after_ids = fields.One2many('hr.employee.family.change.line', 'change_request_id', string="After", domain=[('is_changed','=', True)])
    education_after_ids = fields.One2many('hr.employee.education.change.line', 'change_request_id', string="After", domain=[('is_changed','=', True)])
    health_after_ids = fields.One2many('employee.health.records.change.line', 'change_request_id', string="After", domain=[('is_changed','=', True)])
    #Boolean
    address_available = fields.Boolean('Is Records Available')
    emergency_address_available = fields.Boolean('Is Records Available')
    bank_available = fields.Boolean('Is Records Available')
    family_available = fields.Boolean('Is Records Available')
    education_available = fields.Boolean('Is Records Available')
    health_available = fields.Boolean('Is Records Available')
    # Many2many Get All Records
    all_address_ids = fields.Many2many('hr.employee.address', 'all_add_ids', string="Addresses List")
    all_emergency_ids = fields.Many2many('employee.emergency.contact', 'all_emg_id', string="Emergency Contact List")
    all_bank_ids = fields.Many2many('bank.account', 'all_bank_ids', string="Bank Account List")
    all_fam_ids = fields.Many2many('hr.employee.family', 'all_fam_ids', string="Family List")
    all_education_ids = fields.Many2many('hr.employee.education', 'all_edu_ids', string="Education List")
    all_health_ids = fields.Many2many('employee.health.records', 'all_health_ids', string="Health Record List")
    approvers_ids = fields.Many2many('res.users', 'emp_change_req_approvers_rel', string='Approvers List')
    approved_user_ids = fields.Many2many('res.users', string='Approved by User')
    is_approver = fields.Boolean(string="Is Approver", compute='_compute_can_approve')
    approval_line_ids = fields.One2many('employee.change.request.approval.line', 'change_request_id')
    is_readonly = fields.Boolean(compute='_compute_readonly')
    face_ids = fields.One2many('employee.change.request.image', 'change_id', string="Face recognition images")
    before_face_ids = fields.One2many('employee.change.request.image', 'before_change_id', string="before Face recognition images")
    after_face_ids = fields.One2many('employee.change.request.image', 'after_change_id', string="after Face recognition images")
    trigger_change_image = fields.Char("trigger_change_image",copy=False)
    state1 = fields.Selection([('draft', 'Draft'), ('to_approve', 'To Approve'),
                            ('approved', 'Submitted'), ('rejected', 'Rejected')], tracking=False, default='draft',
                              copy=False,
                              store=True, string='Status', compute='_compute_state1')
    is_employee_change_req_approval_matrix = fields.Boolean("Is Employee Change Request Approval Matrix", related='employee_id.is_employee_change_req_approval_matrix')

    @api.depends('state')
    def _compute_state1(self):
        for record in self:
            record.state1 = record.state

    @api.onchange('trigger_change_image')
    def onchange_trigger_change_image(self):
        if self.trigger_change_image:
            list_img = json.loads(self.trigger_change_image)
            if list_img.get('o_kanban_button_edit_face_table'):
                self.face_ids = False
                del list_img['o_kanban_button_edit_face_table']
            self.face_ids = [(0,0,list_img)]

    
    @api.depends('employee_id')
    def _compute_readonly(self):
        for record in self:
            if self.env.user.has_group('hr.group_hr_user') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader'):
                record.is_readonly = True
            else:
                record.is_readonly = False
    
    
       

    @api.onchange('employee_id')
    def onchange_employee(self):
        if self.employee_id:
            self.private_email = self.employee_id.private_email
            self.phone = self.employee_id.phone
            self.km_home_work = self.employee_id.km_home_work
            self.religion_id = self.employee_id.religion_id.id or False
            self.race_id = self.employee_id.race_id.id or False
            self.gender = self.employee_id.gender
            self.marital = self.employee_id.marital.id or False
            self.country_id = self.employee_id.country_id.id or False
            self.state_id = self.employee_id.state_id.id or False
            self.identification_id = self.employee_id.identification_id
            self.passport_id = self.employee_id.passport_id
            self.birthday = self.employee_id.birthday
            self.place_of_birth = self.employee_id.place_of_birth
            self.country_of_birth = self.employee_id.country_of_birth.id or False
            self.blood_type = self.employee_id.blood_type
            self.height = self.employee_id.height
            self.weight = self.employee_id.weight
            self.visa_no = self.employee_id.visa_no
            self.permit_no = self.employee_id.permit_no
            self.visa_expire = self.employee_id.visa_expire

            self.address_ids = self.employee_id.address_ids.ids or False
            self.emergency_ids = self.employee_id.emergency_ids.ids or False
            self.bank_ids = self.employee_id.bank_ids.ids or False
            self.fam_ids = self.employee_id.fam_ids.ids or False
            self.education_ids = self.employee_id.education_ids.ids or False
            self.health_ids = self.employee_id.health_ids.ids or False
            if self.employee_id.user_id.res_users_image_ids:
                face_ids = []
                self.face_ids = False
                if self.employee_id.user_id.res_users_image_ids:
                    for p in self.employee_id.user_id.res_users_image_ids:
                        if p.image and p.name and p.image_detection:
                            face_ids.append((0,0,{
                                'name':p.name,
                                'sequence':p.sequence,
                                'image':p.image,
                                'image_detection':p.image_detection,
                                'descriptor':p.descriptor,

                            }))
                    if face_ids:
                        self.face_ids = face_ids
            self.remove_line_item()
            self.update_line_items()
            # setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_masterdata_employee.employee_change_request_approval_method')
            setting_emp_change_req_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_masterdata_employee.emp_change_req_approval_matrix')
            setting_emp_change_req_approval_method = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_masterdata_employee.emp_change_req_approval_method')
            if setting_emp_change_req_approval_matrix:
                if self.approval_line_ids:
                    remove = []
                    for line in self.approval_line_ids:
                        remove.append((2, line.id))
                    self.approval_line_ids = remove
                # if setting == 'employee_hierarchy':
                #     self.approval_line_ids = self.changes_emp_by_hierarchy(self)
                #     self.app_list_changes_emp_by_hierarchy()
                # else:
                if setting_emp_change_req_approval_method == 'approval_matrix':
                    self.changes_approval_by_matrix(self)
                if setting_emp_change_req_approval_method == 'employee_hierarchy':
                    self.approval_line_ids = self.changes_emp_by_hierarchy(self)
                    self.app_list_changes_emp_by_hierarchy()

    def update_line_items(self):
        for rec in self:
            data_address = []
            for line in rec.employee_id.address_ids:
                data_address.append((0, 0, {'employee_id': line.employee_id.id,
                                                   'sequence': line.sequence,
                                                   'address_type': line.address_type,
                                                   'street': line.street,
                                                   'location': line.location,
                                                   'country_id': line.country_id.id,
                                                   'state_id': line.state_id.id,
                                                   'postal_code': line.postal_code,
                                                   'tel_number': line.tel_number,
                                                    'address_id': line.id}))

            data_emergency = []
            for line in rec.employee_id.emergency_ids:
                data_emergency.append((0, 0, {'employee_id': line.employee_id.id,
                                                     'name': line.name,
                                                     'phone': line.phone,
                                                     'relation_id': line.relation_id.id,
                                                     'address': line.address,
                                                     'emergency_address_id': line.id}))

            data_bank = []
            for line in rec.employee_id.bank_ids:
                data_bank.append((0, 0, {'employee_id': line.employee_id.id,
                                                'is_used': line.is_used,
                                                'name': line.name,
                                                'bank_unit': line.bank_unit,
                                                'acc_number': line.acc_number,
                                                'bank_account_id': line.id}))

            data_fam = []
            for line in rec.employee_id.fam_ids:
                data_fam.append((0, 0, {'employee_id': line.employee_id.id,
                                               'relation_id': line.relation_id.id,
                                               'member_name': line.member_name,
                                               'member_contact': line.member_contact,
                                               'birth_date': line.birth_date,
                                               'hr_emp_family_id': line.id}))

            data_education = []
            for line in rec.employee_id.education_ids:
                data_education.append((0, 0, {'employee_id': line.employee_id.id,
                                                     'certificate': line.certificate,
                                                     'study_field': line.study_field,
                                                     'study_school': line.study_school,
                                                     'city': line.city,
                                                     'graduation_year': line.graduation_year,
                                                     'gpa_score': line.gpa_score,
                                                     'emp_education_id': line.id}))

            data_health = []
            for line in rec.employee_id.health_ids:
                data_health.append((0, 0, {'employee_id': line.employee_id.id,
                                                  'name': line.name,
                                                  'illness_type': line.illness_type,
                                                  'medical_checkup': line.medical_checkup,
                                                  'date_from': line.date_from,
                                                  'date_to': line.date_to,
                                                  'notes': line.notes,
                                                  'emp_health_id': line.id}))

            rec.get_address_ids = data_address
            rec.get_emergency_ids = data_emergency
            rec.get_bank_ids = data_bank
            rec.get_fam_ids = data_fam
            rec.get_education_ids = data_education
            rec.get_health_ids = data_health

    def remove_line_item(self):
        for rec in self:
            if rec.get_address_ids:
                remove = []
                for line in rec.get_address_ids:
                    remove.append((2, line.id))
                rec.get_address_ids = remove
            if rec.get_emergency_ids:
                remove = []
                for line in rec.get_emergency_ids:
                    remove.append((2, line.id))
                rec.get_emergency_ids = remove
            if rec.get_bank_ids:
                remove = []
                for line in rec.get_bank_ids:
                    remove.append((2, line.id))
                rec.get_bank_ids = remove
            if rec.get_fam_ids:
                remove = []
                for line in rec.get_fam_ids:
                    remove.append((2, line.id))
                rec.get_fam_ids = remove
            if rec.get_education_ids:
                remove = []
                for line in rec.get_education_ids:
                    remove.append((2, line.id))
                rec.get_education_ids = remove
            if rec.get_health_ids:
                remove = []
                for line in rec.get_health_ids:
                    remove.append((2, line.id))
                rec.get_health_ids = remove

    def changes_emp_by_hierarchy(self, changes):
        approval_ids = []
        seq = 1
        data = 0
        line = self.get_manager(changes, changes.employee_id, data, approval_ids, seq)
        return line
    
    def get_manager(self, changes, employee_manager, data, approval_ids, seq):
        setting_level = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_masterdata_employee.emp_change_req_level')
        if not setting_level:
            raise ValidationError("Level not set")
        if not employee_manager['parent_id']['user_id']:
            return approval_ids
        while data < int(setting_level):
            approval_ids.append(
                (0, 0, {'user_ids': [(4, employee_manager['parent_id']['user_id']['id'])]}))
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager(changes, employee_manager['parent_id'], data, approval_ids, seq)
                break
        return approval_ids
    
    def app_list_changes_emp_by_hierarchy(self):
        for changes in self:
            app_list = []
            for line in changes.approval_line_ids:
                app_list.append(line.user_ids.id)
            changes.approvers_ids = app_list
    
    def get_manager_hierarchy(self, changes, employee_manager, data, manager_ids, seq, level):
        if not employee_manager['parent_id']['user_id']:
            return manager_ids
        while data < int(level):
            manager_ids.append(employee_manager['parent_id']['user_id']['id'])
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager_hierarchy(changes, employee_manager['parent_id'], data, manager_ids, seq, level)
                break
        return manager_ids
    
    def changes_approval_by_matrix(self, changes):
        app_list = []
        approval_matrix = self.env['employee.change.request.config'].search([])
        matrix = approval_matrix
        if matrix:
            data_approvers = []
            for line in matrix[0].approval_config_ids:
                if line.approver_types == "specific_approver":
                    data_approvers.append((0, 0, {'minimum_approver': line.minimum_approver,
                                                  'user_ids': [(6, 0, line.approvers.ids)]}))
                    for approvers in line.approvers:
                        app_list.append(approvers.id)
                elif line.approver_types == "by_hierarchy":
                    manager_ids = []
                    seq = 1
                    data = 0
                    approvers = self.get_manager_hierarchy(changes, changes.employee_id, data, manager_ids, seq,
                                                           line.minimum_approver)
                    for approver in approvers:
                        data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                        app_list.append(approver)
            changes.approvers_ids = app_list
            changes.approval_line_ids = data_approvers
    
    @api.depends('approval_line_ids')
    def _compute_can_approve(self):
        for changes in self:
            if changes.approvers_ids:
                # setting = self.env['ir.config_parameter'].sudo().get_param(
                #     'equip3_hr_masterdata_employee.employee_change_request_approval_method')
                # setting_level = self.env['ir.config_parameter'].sudo().get_param(
                #     'equip3_hr_masterdata_employee.employee_change_request_approval_levels')
                # app_level = int(setting_level)
                current_user = changes.env.user
                # if setting == 'employee_hierarchy':
                #     matrix_line = sorted(changes.approval_line_ids.filtered(lambda r: r.is_approve == True))
                #     app = len(matrix_line)
                #     a = len(changes.approval_line_ids)
                #     if app < app_level and app < a:
                #         if current_user in changes.approval_line_ids[app].user_ids:
                #             changes.is_approver = True
                #         else:
                #             changes.is_approver = False
                #     else:
                #         changes.is_approver = False
                # elif setting == 'approval_matrix':
                if changes.approvers_ids:
                    matrix_line = sorted(changes.approval_line_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(changes.approval_line_ids)
                    if app < a:
                        for line in changes.approval_line_ids[app]:
                            if current_user in line.user_ids:
                                changes.is_approver = True
                            else:
                                changes.is_approver = False
                    else:
                        changes.is_approver = False
                else:
                    changes.is_approver = False
            else:
                changes.is_approver = False

    def confirm(self):
        self.address_list()
        self.emergency_address_list()
        self.bank_list()
        self.fam_list()
        self.education_list()
        self.health_list()
        self.update_before_line_item()
        self.is_line_items_rec_available()
        self.update_before_deleted_line_item()
        face_obj = self.env['employee.change.request.image'].sudo()
        for rec in self:
            face_ids = face_obj.search([('change_id','=',rec.id)])
            if face_ids:
                face_ids.write({'after_change_id': rec.id})


            before_face_ids = []
            rec.before_face_ids = False
            if rec.employee_id.user_id.res_users_image_ids:
                for p in rec.employee_id.user_id.res_users_image_ids:
                    if p.image and p.name and p.image_detection:
                        face_obj.create({
                            'name':p.name,
                            'sequence':p.sequence,
                            'image':p.image,
                            'image_detection':p.image_detection,
                            'descriptor':p.descriptor,
                            'before_change_id':rec.id
                        })
    

            for line in rec.approval_line_ids:
                line.write({'approver_state': 'draft'})
            rec.change_request_line_ids = [(5, 0, 0)]
            data_changes = []


            if rec.employee_id.private_email != rec.private_email:
                name_field = self._fields['private_email'].string
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': rec.employee_id.private_email,
                                            'after': rec.private_email}))
            
            if rec.employee_id.phone != rec.phone:
                name_field = self._fields['phone'].string
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': rec.employee_id.phone,
                                            'after': rec.phone}))

            if rec.employee_id.km_home_work != rec.km_home_work:
                name_field = self._fields['km_home_work'].string
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': rec.employee_id.km_home_work,
                                            'after': rec.km_home_work}))

            if rec.employee_id.religion_id != rec.religion_id:
                name_field = self._fields['religion_id'].string
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': rec.employee_id.religion_id.name,
                                            'after': rec.religion_id.name}))

            if rec.employee_id.race_id != rec.race_id:
                name_field = self._fields['race_id'].string
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': rec.employee_id.race_id.name,
                                            'after': rec.race_id.name}))

            if rec.employee_id.gender != rec.gender:
                name_field = self._fields['gender'].string
                before = dict(self.env['hr.employee'].fields_get(allfields=['gender'])['gender']['selection'])[rec.employee_id.gender]
                after = dict(self.fields_get(allfields=['gender'])['gender']['selection'])[rec.gender]
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': before,
                                            'after': after}))

            if rec.employee_id.marital != rec.marital:
                name_field = self._fields['marital'].string
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': rec.employee_id.marital.name,
                                            'after': rec.marital.name}))

            if rec.employee_id.country_id != rec.country_id:
                name_field = self._fields['country_id'].string
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': rec.employee_id.country_id.name,
                                            'after': rec.country_id.name}))

            if rec.employee_id.state_id != rec.state_id:
                name_field = self._fields['state_id'].string
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': rec.employee_id.state_id.name,
                                            'after': rec.state_id.name}))

            if rec.employee_id.identification_id != rec.identification_id:
                name_field = self._fields['identification_id'].string
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': rec.employee_id.identification_id,
                                            'after': rec.identification_id}))

            if rec.employee_id.passport_id != rec.passport_id:
                name_field = self._fields['passport_id'].string
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': rec.employee_id.passport_id,
                                            'after': rec.passport_id}))

            if rec.employee_id.birthday != rec.birthday:
                name_field = self._fields['birthday'].string
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': rec.employee_id.birthday,
                                            'after': rec.birthday}))

            if rec.employee_id.place_of_birth != rec.place_of_birth:
                name_field = self._fields['place_of_birth'].string
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': rec.employee_id.place_of_birth,
                                            'after': rec.place_of_birth}))

            if rec.employee_id.country_of_birth != rec.country_of_birth:
                name_field = self._fields['country_of_birth'].string
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': rec.employee_id.country_of_birth.name,
                                            'after': rec.country_of_birth.name}))

            if rec.employee_id.blood_type != rec.blood_type:
                name_field = self._fields['blood_type'].string
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': rec.employee_id.blood_type,
                                            'after': rec.blood_type}))

            if rec.employee_id.height != rec.height:
                name_field = self._fields['height'].string
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': rec.employee_id.height,
                                            'after': rec.height}))

            if rec.employee_id.weight != rec.weight:
                name_field = self._fields['weight'].string
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': rec.employee_id.weight,
                                            'after': rec.weight}))

            if rec.employee_id.visa_no != rec.visa_no:
                name_field = self._fields['visa_no'].string
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': rec.employee_id.visa_no,
                                            'after': rec.visa_no}))

            if rec.employee_id.permit_no != rec.permit_no:
                name_field = self._fields['permit_no'].string
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': rec.employee_id.permit_no,
                                            'after': rec.permit_no}))

            if rec.employee_id.visa_expire != rec.visa_expire:
                name_field = self._fields['visa_expire'].string
                data_changes.append((0, 0, {'name_of_field': name_field,
                                            'before': rec.employee_id.visa_expire,
                                            'after': rec.visa_expire}))

            rec.change_request_line_ids = data_changes
            setting_emp_change_req_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_masterdata_employee.emp_change_req_approval_matrix')
            if setting_emp_change_req_approval_matrix:
                rec.state = "to_approve"
                rec.approver_mail()
            else:
                rec.state = 'approved'

    def address_list(self):
        for rec in self:
            app_list = []
            all_rec = []
            for line in rec.get_address_ids:
                #all ids
                if line.address_id:
                    all_rec.append(line.address_id.id)
                if line.address_id and line.is_changed:
                    app_list.append(line.address_id.id)
            rec.all_address_ids = all_rec
            rec.org_address_ids = app_list

    def emergency_address_list(self):
        for rec in self:
            app_list = []
            all_rec = []
            for line in rec.get_emergency_ids:
                # all ids
                if line.emergency_address_id:
                    all_rec.append(line.emergency_address_id.id)
                if line.emergency_address_id and line.is_changed:
                    app_list.append(line.emergency_address_id.id)
            rec.all_emergency_ids = all_rec
            rec.org_emergency_ids = app_list

    def bank_list(self):
        for rec in self:
            app_list = []
            all_rec = []
            for line in rec.get_bank_ids:
                if line.bank_account_id:
                    all_rec.append(line.bank_account_id.id)
                if line.bank_account_id and line.is_changed:
                    app_list.append(line.bank_account_id.id)
            rec.all_bank_ids = all_rec
            rec.org_bank_ids = app_list

    def fam_list(self):
        for rec in self:
            app_list = []
            all_rec = []
            for line in rec.get_fam_ids:
                if line.hr_emp_family_id:
                    all_rec.append(line.hr_emp_family_id.id)
                if line.hr_emp_family_id and line.is_changed:
                    app_list.append(line.hr_emp_family_id.id)
            rec.all_fam_ids = all_rec
            rec.org_fam_ids = app_list

    def education_list(self):
        for rec in self:
            app_list = []
            all_rec = []
            for line in rec.get_education_ids:
                if line.emp_education_id:
                    all_rec.append(line.emp_education_id.id)
                if line.emp_education_id and line.is_changed:
                    app_list.append(line.emp_education_id.id)
            rec.all_education_ids = all_rec
            rec.org_education_ids = app_list

    def health_list(self):
        for rec in self:
            app_list = []
            all_rec = []
            for line in rec.get_health_ids:
                if line.emp_health_id:
                    all_rec.append(line.emp_health_id.id)
                if line.emp_health_id and line.is_changed:
                    app_list.append(line.emp_health_id.id)
            rec.all_health_ids = all_rec
            rec.org_health_ids = app_list

    def update_before_line_item(self):
        for rec in self:
            data_address_before = []
            for line in rec.employee_id.address_ids:
                if line.id in rec.org_address_ids.ids:
                    data_address_before.append((0, 0, {'employee_id': line.employee_id.id,
                                                       'sequence': line.sequence,
                                                       'address_type': line.address_type,
                                                       'street': line.street,
                                                       'location': line.location,
                                                       'country_id': line.country_id.id,
                                                       'state_id': line.state_id.id,
                                                       'postal_code': line.postal_code,
                                                       'tel_number': line.tel_number,
                                                       'address_id': line.id}))

            data_emergency_before = []
            for line in rec.employee_id.emergency_ids:
                if line.id in rec.org_emergency_ids.ids:
                    data_emergency_before.append((0, 0, {'employee_id': line.employee_id.id,
                                                         'name': line.name,
                                                         'phone': line.phone,
                                                         'relation_id': line.relation_id.id,
                                                         'address': line.address,
                                                         'emergency_address_id': line.id}))

            data_bank_before = []
            for line in rec.employee_id.bank_ids:
                if line.id in rec.org_bank_ids.ids:
                    data_bank_before.append((0, 0, {'employee_id': line.employee_id.id,
                                                    'is_used': line.is_used,
                                                    'name': line.name.id,
                                                    'bank_unit': line.bank_unit,
                                                    'acc_number': line.acc_number,
                                                    'bank_account_id': line.id}))

            data_fam_before = []
            for line in rec.employee_id.fam_ids:
                if line.id in rec.org_fam_ids.ids:
                    data_fam_before.append((0, 0, {'employee_id': line.employee_id.id,
                                                   'relation_id': line.relation_id.id,
                                                   'member_name': line.member_name,
                                                   'member_contact': line.member_contact,
                                                   'birth_date': line.birth_date,
                                                   'hr_emp_family_id': line.id}))

            data_education_before = []
            for line in rec.employee_id.education_ids:
                if line.id in rec.org_education_ids.ids:
                    data_education_before.append((0, 0, {'employee_id': line.employee_id.id,
                                                         'certificate': line.certificate,
                                                         'study_field': line.study_field,
                                                         'study_school': line.study_school,
                                                         'city': line.city,
                                                         'graduation_year': line.graduation_year,
                                                         'gpa_score': line.gpa_score,
                                                         'emp_education_id': line.id}))

            data_health_before = []
            for line in rec.employee_id.health_ids:
                if line.id in rec.org_health_ids.ids:
                    data_health_before.append((0, 0, {'employee_id': line.employee_id.id,
                                                      'name': line.name,
                                                      'illness_type': line.illness_type,
                                                      'medical_checkup': line.medical_checkup,
                                                      'date_from': line.date_from,
                                                      'date_to': line.date_to,
                                                      'notes': line.notes,
                                                      'emp_health_id': line.id}))

            rec.address_before_ids = data_address_before
            rec.emergency_before_ids = data_emergency_before
            rec.bank_before_ids = data_bank_before
            rec.fam_before_ids = data_fam_before
            rec.education_before_ids = data_education_before
            rec.health_before_ids = data_health_before

    def update_before_deleted_line_item(self):
        for rec in self:
            data_address_before = []
            for line in rec.employee_id.address_ids:
                if line.id not in rec.all_address_ids.ids:
                    rec.address_available = True
                    data_address_before.append((0, 0, {'employee_id': line.employee_id.id,
                                                       'sequence': line.sequence,
                                                       'address_type': line.address_type,
                                                       'street': line.street,
                                                       'location': line.location,
                                                       'country_id': line.country_id.id,
                                                       'state_id': line.state_id.id,
                                                       'postal_code': line.postal_code,
                                                       'tel_number': line.tel_number,
                                                       'address_id': line.id}))

            data_emergency_before = []
            for line in rec.employee_id.emergency_ids:
                if line.id not in rec.all_emergency_ids.ids:
                    rec.emergency_address_available = True
                    data_emergency_before.append((0, 0, {'employee_id': line.employee_id.id,
                                                         'name': line.name,
                                                         'phone': line.phone,
                                                         'relation_id': line.relation_id.id,
                                                         'address': line.address,
                                                         'emergency_address_id': line.id}))

            data_bank_before = []
            for line in rec.employee_id.bank_ids:
                if line.id not in rec.all_bank_ids.ids:
                    rec.bank_available = True
                    data_bank_before.append((0, 0, {'employee_id': line.employee_id.id,
                                                    'is_used': line.is_used,
                                                    'name': line.name.id,
                                                    'bank_unit': line.bank_unit,
                                                    'acc_number': line.acc_number,
                                                    'bank_account_id': line.id}))

            data_fam_before = []
            for line in rec.employee_id.fam_ids:
                if line.id not in rec.all_fam_ids.ids:
                    rec.family_available = True
                    data_fam_before.append((0, 0, {'employee_id': line.employee_id.id,
                                                   'relation_id': line.relation_id.id,
                                                   'member_name': line.member_name,
                                                   'member_contact': line.member_contact,
                                                   'birth_date': line.birth_date,
                                                   'hr_emp_family_id': line.id}))

            data_education_before = []
            for line in rec.employee_id.education_ids:
                if line.id not in rec.all_education_ids.ids:
                    rec.education_available = True
                    data_education_before.append((0, 0, {'employee_id': line.employee_id.id,
                                                         'certificate': line.certificate,
                                                         'study_field': line.study_field,
                                                         'study_school': line.study_school,
                                                         'city': line.city,
                                                         'graduation_year': line.graduation_year,
                                                         'gpa_score': line.gpa_score,
                                                         'emp_education_id': line.id}))

            data_health_before = []
            for line in rec.employee_id.health_ids:
                if line.id not in rec.all_health_ids.ids:
                    rec.health_available = True
                    data_health_before.append((0, 0, {'employee_id': line.employee_id.id,
                                                      'name': line.name,
                                                      'illness_type': line.illness_type,
                                                      'medical_checkup': line.medical_checkup,
                                                      'date_from': line.date_from,
                                                      'date_to': line.date_to,
                                                      'notes': line.notes,
                                                      'emp_health_id': line.id}))

            rec.address_before_ids = data_address_before
            rec.emergency_before_ids = data_emergency_before
            rec.bank_before_ids = data_bank_before
            rec.fam_before_ids = data_fam_before
            rec.education_before_ids = data_education_before
            rec.health_before_ids = data_health_before

    def is_line_items_rec_available(self):
        for rec in self:
            if rec.address_after_ids:
                rec.address_available = True
            else:
                rec.address_available = False
            if rec.emergency_after_ids:
                rec.emergency_address_available = True
            else:
                rec.emergency_address_available = False
            if rec.bank_after_ids:
                rec.bank_available = True
            else:
                rec.bank_available = False
            if rec.fam_after_ids:
                rec.family_available = True
            else:
                rec.family_available = False
            if rec.education_after_ids:
                rec.education_available = True
            else:
                rec.education_available = False
            if rec.health_after_ids:
                rec.health_available = True
            else:
                rec.health_available = False

    def prepare_data_employee(self):
        employee_dict = {'private_email': self.private_email,
                        'phone': self.phone,
                        'km_home_work': self.km_home_work,
                        'religion_id': self.religion_id.id or False,
                        'race_id': self.race_id.id or False,
                        'gender': self.gender,
                        'marital': self.marital.id or False,
                        'country_id': self.country_id.id or False,
                        'state_id': self.state_id.id or False,
                        'identification_id': self.identification_id,
                        'passport_id': self.passport_id,
                        'birthday': self.birthday,
                        'place_of_birth': self.place_of_birth,
                        'country_of_birth': self.country_of_birth.id or False,
                        'blood_type': self.blood_type,
                        'height': self.height,
                        'weight': self.weight,
                        'visa_no': self.visa_no,
                        'permit_no': self.permit_no,
                        'visa_expire': self.visa_expire}
        return employee_dict
    
    def prepare_data_employee_lines(self):
        self.remove_employee_line_items()
        for rec in self:
            if rec.get_address_ids:
                for line in rec.get_address_ids:
                    if line.is_changed:
                        if line.address_id:
                            line.address_id.write({'employee_id': line.employee_id.id,
                                                   'sequence': line.sequence,
                                                   'address_type': line.address_type,
                                                   'street': line.street,
                                                   'location': line.location,
                                                   'country_id': line.country_id.id,
                                                   'state_id': line.state_id.id,
                                                   'postal_code': line.postal_code,
                                                   'tel_number': line.tel_number
                                                   })
                        if not line.address_id:
                            line.address_id.create({'employee_id': rec.employee_id.id,
                                                    'sequence': line.sequence,
                                                    'address_type': line.address_type,
                                                    'street': line.street,
                                                    'location': line.location,
                                                    'country_id': line.country_id.id,
                                                    'state_id': line.state_id.id,
                                                    'postal_code': line.postal_code,
                                                    'tel_number': line.tel_number
                                                    })
            if rec.get_emergency_ids:
                for line in rec.get_emergency_ids:
                    if line.is_changed:
                        if line.emergency_address_id:
                            line.emergency_address_id.write({'employee_id': line.employee_id.id,
                                                             'name': line.name,
                                                             'phone': line.phone,
                                                             'relation_id': line.relation_id.id,
                                                             'address': line.address,
                                                             })
                        if not line.emergency_address_id:
                            line.emergency_address_id.create({'employee_id': rec.employee_id.id,
                                                              'name': line.name,
                                                              'phone': line.phone,
                                                              'relation_id': line.relation_id.id,
                                                              'address': line.address,
                                                              })
            if rec.get_bank_ids:
                for line in rec.get_bank_ids:
                    if line.is_changed:
                        if line.bank_account_id:
                            line.bank_account_id.write({'employee_id': line.employee_id.id,
                                                        'is_used': line.is_used,
                                                        'name': line.name.id,
                                                        'bank_unit': line.bank_unit,
                                                        'acc_number': line.acc_number,
                                                        })
                        if not line.bank_account_id:
                            line.bank_account_id.create({'employee_id': rec.employee_id.id,
                                                         'is_used': line.is_used,
                                                         'name': line.name.id,
                                                         'bank_unit': line.bank_unit,
                                                         'acc_number': line.acc_number,
                                                         })
            if rec.get_fam_ids:
                for line in rec.get_fam_ids:
                    if line.is_changed:
                        if line.hr_emp_family_id:
                            line.hr_emp_family_id.write({'employee_id': line.employee_id.id,
                                                         'relation_id': line.relation_id.id,
                                                         'member_name': line.member_name,
                                                         'member_contact': line.member_contact,
                                                         'birth_date': line.birth_date,
                                                         })
                        if not line.hr_emp_family_id:
                            line.hr_emp_family_id.create({'employee_id': rec.employee_id.id,
                                                          'relation_id': line.relation_id.id,
                                                          'member_name': line.member_name,
                                                          'member_contact': line.member_contact,
                                                          'birth_date': line.birth_date,
                                                          })
            if rec.get_education_ids:
                for line in rec.get_education_ids:
                    if line.is_changed:
                        if line.emp_education_id:
                            line.emp_education_id.write({'employee_id': line.employee_id.id,
                                                         'certificate': line.certificate,
                                                         'study_field': line.study_field,
                                                         'study_school': line.study_school,
                                                         'city': line.city,
                                                         'graduation_year': line.graduation_year,
                                                         'gpa_score': line.gpa_score,
                                                         })
                        if not line.emp_education_id:
                            line.emp_education_id.create({'employee_id': rec.employee_id.id,
                                                          'certificate': line.certificate,
                                                          'study_field': line.study_field,
                                                          'study_school': line.study_school,
                                                          'city': line.city,
                                                          'graduation_year': line.graduation_year,
                                                          'gpa_score': line.gpa_score,
                                                          })
            if rec.get_health_ids:
                for line in rec.get_health_ids:
                    if line.is_changed:
                        if line.emp_health_id:
                            line.emp_health_id.write({'employee_id': line.employee_id.id,
                                                      'name': line.name,
                                                      'illness_type': line.illness_type,
                                                      'medical_checkup': line.medical_checkup,
                                                      'date_from': line.date_from,
                                                      'date_to': line.date_to,
                                                      'notes': line.notes,
                                                      })
                        if not line.emp_health_id:
                            line.emp_health_id.create({'employee_id': rec.employee_id.id,
                                                       'name': line.name,
                                                       'illness_type': line.illness_type,
                                                       'medical_checkup': line.medical_checkup,
                                                       'date_from': line.date_from,
                                                       'date_to': line.date_to,
                                                       'notes': line.notes,
                                                       })

    def remove_employee_line_items(self):
        for rec in self:
            ## start remove lines from employee ##
            data_address_remove = []
            for data in rec.employee_id.address_ids:
                if data.id not in rec.all_address_ids.ids:
                    data_address_remove.append(data)
            if data_address_remove:
                rec.employee_id.write({'address_ids': [(2, line.id) for line in data_address_remove]})

            data_emergency_remove = []
            for data in rec.employee_id.emergency_ids:
                if data.id not in rec.all_emergency_ids.ids:
                    data_emergency_remove.append(data)
            if data_emergency_remove:
                rec.employee_id.write({'emergency_ids': [(2, line.id) for line in data_emergency_remove]})

            data_bank_remove = []
            for data in rec.employee_id.bank_ids:
                if data.id not in rec.all_bank_ids.ids:
                    data_bank_remove.append(data)
            if data_bank_remove:
                rec.employee_id.write({'bank_ids': [(2, line.id) for line in data_bank_remove]})

            data_fam_remove = []
            for data in rec.employee_id.fam_ids:
                if data.id not in rec.all_fam_ids.ids:
                    data_fam_remove.append(data)
            if data_fam_remove:
                rec.employee_id.write({'fam_ids': [(2, line.id) for line in data_fam_remove]})

            data_education_remove = []
            for data in rec.employee_id.education_ids:
                if data.id not in rec.all_education_ids.ids:
                    data_education_remove.append(data)
            if data_education_remove:
                rec.employee_id.write({'education_ids': [(2, line.id) for line in data_education_remove]})

            data_health_remove = []
            for data in rec.employee_id.health_ids:
                if data.id not in rec.all_health_ids.ids:
                    data_health_remove.append(data)
            if data_health_remove:
                rec.employee_id.write({'health_ids': [(2, line.id) for line in data_health_remove]})
            ## end remove lines from employee ##

    def approve(self):
        rec_face_ids = self.env['employee.change.request.image'].sudo().search([('change_id','=',self.id)])
        for rec in self:
            if rec.employee_id.user_id.res_users_image_ids:
                rec.employee_id.user_id.res_users_image_ids.unlink()

            res_users_image_ids = []
            if rec_face_ids:
                for p in rec_face_ids:
                    if p.image and p.name and p.image_detection:
                        res_users_image_ids.append((0,0,{
                            'name':p.name,
                            'sequence':p.sequence,
                            'image':p.image,
                            'image_detection':p.image_detection,
                            'descriptor':p.descriptor,

                        }))
                if res_users_image_ids:
                    rec.employee_id.user_id.res_users_image_ids = res_users_image_ids

        self.approval_line_ids.update_approver_state()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'employee.change.approval.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name':"Confirmation Message",
            'target': 'new',
            'context':{'default_changes_request_id':self.id, 'default_state': 'approved'},
        }

    def reject(self):
        self.approval_line_ids.update_approver_state()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'employee.change.approval.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name':"Confirmation Message",
            'target': 'new',
            'context':{'default_changes_request_id':self.id, 'default_state': 'rejected'},
        }

    def get_menu(self):
        views = [(self.env.ref('equip3_hr_masterdata_employee.hr_employee_change_request_tree_view').id, 'tree'),
                 (self.env.ref('equip3_hr_masterdata_employee.hr_employee_change_request_form_view').id, 'form')]
        if self.env.user.has_group('hr.group_hr_user') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Employee Change Request',
                'res_model': 'hr.employee.change.request',
                'view_mode': 'tree,form',
                'views': views,
                'domain': [('employee_id','=',self.env.user.employee_id.id)],
                'context': {}

            }
        elif self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_officer'):
            employee_ids = []
            my_employee = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id),('company_id','in',self.env.company.ids)])
            if my_employee:
                for child_record in my_employee.child_ids:
                    employee_ids.append(my_employee.id)
                    employee_ids.append(child_record.id)
                    child_record._get_amployee_hierarchy(employee_ids, child_record.child_ids, my_employee.id)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Employee Change Request',
                'res_model': 'hr.employee.change.request',
                'view_mode': 'tree,form',
                'views': views,
                'domain': [('employee_id','in',employee_ids)],
                'context': {}

            }
            
            
        return {
                'type': 'ir.actions.act_window',
                'name': 'Employee Change Request',
                'res_model': 'hr.employee.change.request',
                'view_mode': 'tree,form',
                'views': views,
                'domain': [],
                'context': {}

            }

    def get_url(self, obj):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action_id = self.env.ref('equip3_hr_masterdata_employee.action_hr_employee_change_request')
        url = base_url + '/web#id=' + str(obj.id) + '&action=' + str(action_id.id) + '&view_type=form&model=hr.employee.change.request'
        return url

    def approver_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.approval_line_ids:
                matrix_line = sorted(rec.approval_line_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.approval_line_ids[len(matrix_line)]
                for user in approver.user_ids:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_masterdata_employee',
                            'email_template_approver_of_emp_change_req')[1]
                    except ValueError:
                        template_id = False
                    ctx = self._context.copy()
                    url = self.get_url(self)
                    ctx.update({
                        'email_from': self.env.user.email,
                        'email_to': user.email,
                        'url': url,
                        'approver_name': user.name,
                        'emp_name': self.employee_id.name,
                    })
                    self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id,force_send=True)
                break

    @api.model
    def get_auto_follow_up_approver(self):
        ir_model_data = self.env['ir.model.data']
        number_of_repetitions_emp_change = int(
            self.env['ir.config_parameter'].sudo().get_param('equip3_hr_masterdata_employee.number_of_repetitions_emp_change'))
        emp_change_approve = self.search([('state', '=', 'to_approve')])
        for rec in emp_change_approve:
            if rec.approval_line_ids:
                matrix_line = sorted(rec.approval_line_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.approval_line_ids[len(matrix_line)]
                for user in approver.user_ids:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_masterdata_employee',
                            'email_template_approver_of_emp_change_req')[1]
                    except ValueError:
                        template_id = False
                    ctx = self._context.copy()
                    url = self.get_url(rec)
                    ctx.update({
                        'email_from': self.env.user.email,
                        'email_to': user.email,
                        'url': url,
                        'approver_name': user.name,
                        'emp_name': rec.employee_id.name,
                    })
                    if not approver.is_auto_follow_approver:
                        count = number_of_repetitions_emp_change - 1
                        query_statement = """UPDATE employee_change_request_approval_line set is_auto_follow_approver = TRUE, repetition_follow_count = %s WHERE id = %s """
                        self.sudo().env.cr.execute(query_statement, [count, approver.id])
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                  force_send=True)
                    elif approver.is_auto_follow_approver:
                        if user not in approver.approved_employee_ids and approver.repetition_follow_count > 0:
                            count = approver.repetition_follow_count - 1
                            query_statement = """UPDATE employee_change_request_approval_line set repetition_follow_count = %s WHERE id = %s """
                            self.sudo().env.cr.execute(query_statement, [count, approver.id])
                            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id, force_send=True)

class HREmployeeChangeRequestLine(models.Model):
    _name = 'hr.employee.change.request.line'

    change_request_id = fields.Many2one('hr.employee.change.request', ondelete="cascade")
    name_of_field = fields.Char('Name of field')
    before = fields.Char('Before')
    after = fields.Char('After')

class HrEmployeeAddress(models.Model):
    _name = 'hr.employee.address.before.change'
    _description = 'Address Employee Before Change'

    change_request_id = fields.Many2one('hr.employee.change.request')
    employee_id = fields.Many2one('hr.employee')
    sequence = fields.Integer()
    address_type = fields.Selection([('current','Current Address'),('identity','Identity Address')])
    street = fields.Char()
    location  = fields.Char()
    country_id = fields.Many2one('res.country')
    state_id = fields.Many2one('res.country.state')
    postal_code = fields.Char()
    tel_number = fields.Char()
    address_id = fields.Many2one('hr.employee.address')

class EmployeeEmergencyContact(models.Model):
    _name = 'employee.emergency.contact.before.change'
    _description = 'Employee Emergency Contact Before Change'

    change_request_id = fields.Many2one('hr.employee.change.request')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    name = fields.Char(string='Name')
    phone = fields.Char(string='Phone')
    relation_id = fields.Many2one('hr.employee.relation', string='Relation')
    address = fields.Char(string='Address')
    emergency_address_id = fields.Many2one('employee.emergency.contact')

class EmployeeBankAccount(models.Model):
    _name = 'bank.account.before.change'

    change_request_id = fields.Many2one('hr.employee.change.request')
    is_used = fields.Boolean("Primary Account")
    name = fields.Many2one('res.bank',"Name Of Bank")
    bic = fields.Char(related='name.bic',string="Bank Identifier Code")
    bank_unit = fields.Char(string="KCP / Unit")
    acc_number = fields.Char("Account Number")
    acc_holder = fields.Char(related='employee_id.name', string="Holder Name")
    employee_id = fields.Many2one('hr.employee')
    bank_account_id = fields.Many2one('bank.account')

class HrEmployeeFamilyInfo(models.Model):
    _name = 'hr.employee.family.before.change'
    _description = 'HR Employee Family Before Change'

    change_request_id = fields.Many2one('hr.employee.change.request')
    employee_id = fields.Many2one('hr.employee', string="Employee", help='Select corresponding Employee',
                                  invisible=1)
    relation_id = fields.Many2one('hr.employee.relation', string="Relation", help="Relationship with the employee")
    member_name = fields.Char(string='Name')
    member_contact = fields.Char(string='Contact No')
    birth_date = fields.Date(string="DOB")
    age = fields.Integer("Age")
    education = fields.Char("Education")
    occupation = fields.Char()
    city = fields.Char()
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], string='Gender')
    hr_emp_family_id = fields.Many2one('hr.employee.family')

class HrEmployeeEducation(models.Model):
    _name = 'hr.employee.education.before.change'
    _description = 'HR Employee Education Before Change'

    change_request_id = fields.Many2one('hr.employee.change.request')
    employee_id = fields.Many2one('hr.employee', "Employee")
    certificate = fields.Selection([
        ('graduate', 'Graduate'),
        ('bachelor', 'Bachelor'),
        ('master', 'Master'),
        ('doctor', 'Doctor'),
        ('other', 'Other'),
    ], 'Certificate Level', default='other')
    study_field = fields.Char("Field of Study")
    study_school = fields.Char("School")
    city = fields.Char(string='City')
    graduation_year = fields.Char(string='Graduation Year')
    gpa_score = fields.Float(string='GPA Score')
    emp_education_id = fields.Many2one('hr.employee.education')

class EmployeeHealthRecords(models.Model):
    _name = 'employee.health.records.before.change'
    _description = 'Employee Health Records Before Change'

    change_request_id = fields.Many2one('hr.employee.change.request')
    name = fields.Integer("Sequence")
    employee_id = fields.Many2one('hr.employee', "Employee")
    illness_type = fields.Char("Illness Type")
    medical_checkup = fields.Char("Medical Checkup")
    date_from = fields.Date(string='Date from')
    date_to = fields.Date(string='Date to')
    notes = fields.Char(string='Notes')
    emp_health_id = fields.Many2one('employee.health.records')

class HrEmployeeAddress(models.Model):
    _inherit = 'hr.employee.address'

    change_request_id = fields.Many2one('hr.employee.change.request')

class EmployeeEmergencyContact(models.Model):
    _inherit = 'employee.emergency.contact'

    change_request_id = fields.Many2one('hr.employee.change.request')

class EmployeeBankAccount(models.Model):
    _inherit = 'bank.account'

    change_request_id = fields.Many2one('hr.employee.change.request')

class HrEmployeeFamilyInfo(models.Model):
    _inherit = 'hr.employee.family'

    change_request_id = fields.Many2one('hr.employee.change.request')

class HrEmployeeEducation(models.Model):
    _inherit = 'hr.employee.education'

    change_request_id = fields.Many2one('hr.employee.change.request')

class EmployeeHealthRecords(models.Model):
    _inherit = 'employee.health.records'

    change_request_id = fields.Many2one('hr.employee.change.request')


class HrEmployeeAddressChange(models.Model):
    _name = 'hr.employee.address.change.line'
    _description = 'Address Employee'

    employee_id = fields.Many2one('hr.employee')
    sequence = fields.Integer()
    address_type = fields.Selection([('current','Current Address'),('identity','Identity Address')])
    street = fields.Char()
    location  = fields.Char()
    country_id = fields.Many2one('res.country')
    state_id = fields.Many2one('res.country.state')
    postal_code = fields.Char()
    tel_number = fields.Char()
    change_request_id = fields.Many2one('hr.employee.change.request')
    address_id = fields.Many2one('hr.employee.address')
    is_changed = fields.Boolean('Is this Line-item Changed')

    @api.onchange('sequence', 'address_type', 'street', 'location', 'country_id', 'state_id', 'postal_code', 'tel_number')
    def is_line_changed(self):
        for rec in self:
            if rec.address_id.sequence != rec.sequence:
                rec.is_changed = True
            elif rec.address_id.address_type != rec.address_type:
                rec.is_changed = True
            elif rec.address_id.street != rec.street:
                rec.is_changed = True
            elif rec.address_id.location != rec.location:
                rec.is_changed = True
            elif rec.address_id.country_id != rec.country_id:
                rec.is_changed = True
            elif rec.address_id.state_id != rec.state_id:
                rec.is_changed = True
            elif rec.address_id.postal_code != rec.postal_code:
                rec.is_changed = True
            elif rec.address_id.tel_number != rec.tel_number:
                rec.is_changed = True
            else:
                rec.is_changed = False

class EmployeeEmergencyContactChange(models.Model):
    _name = 'employee.emergency.contact.change.line'
    _description = 'Employee Emergency Contact Change'

    employee_id = fields.Many2one('hr.employee', string='Employee')
    name = fields.Char(string='Name')
    phone = fields.Char(string='Phone')
    relation_id = fields.Many2one('hr.employee.relation', string='Relation')
    address = fields.Char(string='Address')
    #
    change_request_id = fields.Many2one('hr.employee.change.request')
    emergency_address_id = fields.Many2one('employee.emergency.contact')
    is_changed = fields.Boolean('Is this Line-item Changed')

    @api.onchange('name', 'phone', 'relation_id', 'address')
    def is_line_changed(self):
        for rec in self:
            if rec.emergency_address_id.name != rec.name:
                rec.is_changed = True
            elif rec.emergency_address_id.phone != rec.phone:
                rec.is_changed = True
            elif rec.emergency_address_id.relation_id != rec.relation_id:
                rec.is_changed = True
            elif rec.emergency_address_id.address != rec.address:
                rec.is_changed = True
            else:
                rec.is_changed = False

class EmployeeBankAccountChange(models.Model):
    _name = 'bank.account.change.line'

    change_request_id = fields.Many2one('hr.employee.change.request')
    is_used = fields.Boolean("Primary Account")
    name = fields.Many2one('res.bank',"Name Of Bank")
    bic = fields.Char(related='name.bic',string="Bank Identifier Code")
    bank_unit = fields.Char(string="KCP / Unit")
    acc_number = fields.Char("Account Number")
    acc_holder = fields.Char(related='employee_id.name', string="Holder Name")
    employee_id = fields.Many2one('hr.employee')
    #
    bank_account_id = fields.Many2one('bank.account')
    is_changed = fields.Boolean('Is this Line-item Changed')

    @api.onchange('is_used', 'name', 'bic', 'bank_unit', 'acc_number', 'acc_holder')
    def is_line_changed(self):
        for rec in self:
            if rec.bank_account_id.is_used != rec.is_used:
                rec.is_changed = True
            elif rec.bank_account_id.name != rec.name:
                rec.is_changed = True
            elif rec.bank_account_id.bic != rec.bic:
                rec.is_changed = True
            elif rec.bank_account_id.bank_unit != rec.bank_unit:
                rec.is_changed = True
            elif rec.bank_account_id.acc_number != rec.acc_number:
                rec.is_changed = True
            elif rec.bank_account_id.acc_holder != rec.acc_holder:
                rec.is_changed = True
            else:
                rec.is_changed = False

class HrEmployeeFamilyInfoChange(models.Model):
    _name = 'hr.employee.family.change.line'
    _description = 'HR Employee Family Change'

    change_request_id = fields.Many2one('hr.employee.change.request')
    employee_id = fields.Many2one('hr.employee', string="Employee", help='Select corresponding Employee',
                                  invisible=1)
    relation_id = fields.Many2one('hr.employee.relation', string="Relation", help="Relationship with the employee")
    member_name = fields.Char(string='Name')
    member_contact = fields.Char(string='Contact No')
    birth_date = fields.Date(string="DOB")
    age = fields.Integer("Age")
    education = fields.Char("Education")
    occupation = fields.Char()
    city = fields.Char()
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], string='Gender')
    #
    hr_emp_family_id = fields.Many2one('hr.employee.family')
    is_changed = fields.Boolean('Is this Line-item Changed')

    @api.onchange('relation_id', 'member_name', 'gender', 'age', 'education', 'occupation', 'city')
    def is_line_changed(self):
        for rec in self:
            if rec.hr_emp_family_id.relation_id != rec.relation_id:
                rec.is_changed = True
            elif rec.hr_emp_family_id.member_name != rec.member_name:
                rec.is_changed = True
            elif rec.hr_emp_family_id.gender != rec.gender:
                rec.is_changed = True
            elif rec.hr_emp_family_id.age != rec.age:
                rec.is_changed = True
            elif rec.hr_emp_family_id.education != rec.education:
                rec.is_changed = True
            elif rec.hr_emp_family_id.occupation != rec.occupation:
                rec.is_changed = True
            elif rec.hr_emp_family_id.city != rec.city:
                rec.is_changed = True
            else:
                rec.is_changed = False

class HrEmployeeEducationChange(models.Model):
    _name = 'hr.employee.education.change.line'
    _description = 'HR Employee Education Change'

    change_request_id = fields.Many2one('hr.employee.change.request')
    employee_id = fields.Many2one('hr.employee', "Employee")
    certificate = fields.Selection([
        ('graduate', 'Graduate'),
        ('bachelor', 'Bachelor'),
        ('master', 'Master'),
        ('doctor', 'Doctor'),
        ('other', 'Other'),
    ], 'Certificate Level', default='other')
    study_field = fields.Char("Field of Study")
    study_school = fields.Char("School")
    city = fields.Char(string='City')
    graduation_year = fields.Char(string='Graduation Year')
    gpa_score = fields.Float(string='GPA Score')
    #
    emp_education_id = fields.Many2one('hr.employee.education')
    is_changed = fields.Boolean('Is this Line-item Changed')

    @api.onchange('certificate', 'study_field', 'study_school', 'city', 'graduation_year', 'gpa_score')
    def is_line_changed(self):
        for rec in self:
            if rec.emp_education_id.certificate != rec.certificate:
                rec.is_changed = True
            elif rec.emp_education_id.study_field != rec.study_field:
                rec.is_changed = True
            elif rec.emp_education_id.study_school != rec.study_school:
                rec.is_changed = True
            elif rec.emp_education_id.city != rec.city:
                rec.is_changed = True
            elif rec.emp_education_id.graduation_year != rec.graduation_year:
                rec.is_changed = True
            elif rec.emp_education_id.gpa_score != rec.gpa_score:
                rec.is_changed = True
            else:
                rec.is_changed = False

class EmployeeHealthRecordsChange(models.Model):
    _name = 'employee.health.records.change.line'
    _description = 'Employee Health Records Change'

    change_request_id = fields.Many2one('hr.employee.change.request')
    name = fields.Integer("Sequence", compute="fetch_sl_no", store=True)
    employee_id = fields.Many2one('hr.employee', "Employee")
    illness_type = fields.Char("Illness Type")
    medical_checkup = fields.Char("Medical Checkup")
    date_from = fields.Date(string='Date from')
    date_to = fields.Date(string='Date to')
    notes = fields.Char(string='Notes')
    #
    emp_health_id = fields.Many2one('employee.health.records')
    is_changed = fields.Boolean('Is this Line-item Changed')

    @api.onchange('name', 'employee_id', 'illness_type', 'medical_checkup', 'date_from', 'date_to', 'notes')
    def is_line_changed(self):
        for rec in self:
            if rec.emp_health_id.name != rec.name:
                rec.is_changed = True
            elif rec.emp_health_id.employee_id != rec.employee_id:
                rec.is_changed = True
            elif rec.emp_health_id.illness_type != rec.illness_type:
                rec.is_changed = True
            elif rec.emp_health_id.medical_checkup != rec.medical_checkup:
                rec.is_changed = True
            elif rec.emp_health_id.date_from != rec.date_from:
                rec.is_changed = True
            elif rec.emp_health_id.date_to != rec.date_to:
                rec.is_changed = True
            elif rec.emp_health_id.notes != rec.notes:
                rec.is_changed = True
            else:
                rec.is_changed = False

    @api.depends('change_request_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.change_request_id.get_health_ids:
            sl = sl + 1
            line.name = sl

class EmployeeChangeRequestApprovalLine(models.Model):
    _name = 'employee.change.request.approval.line'

    change_request_id = fields.Many2one('hr.employee.change.request', ondelete='cascade')
    sequence = fields.Integer('Sequence', compute="fetch_sl_no")
    user_ids = fields.Many2many('res.users', string="Approvers")
    approved_employee_ids = fields.Many2many('res.users', 'emp_change_req_line_approve_ids', string="Approved user")
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('refuse', 'Refused')], default='', string="State")
    approval_status = fields.Char('Approval Status')
    timestamp = fields.Text('Timestamp')
    feedback = fields.Text('Feedback')
    minimum_approver = fields.Integer(default=1)
    is_approve = fields.Boolean(string="Is Approve", default=False)
    #
    is_auto_follow_approver = fields.Boolean()
    repetition_follow_count = fields.Integer()
    #parent status
    state = fields.Selection(string='Parent Status', related='change_request_id.state')

    @api.depends('change_request_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.change_request_id.approval_line_ids:
            sl = sl + 1
            line.sequence = sl

    def update_approver_state(self):
        for rec in self:
            if rec.change_request_id.state == 'to_approve':
                if not rec.approved_employee_ids:
                    rec.approver_state = 'draft'
                elif rec.approved_employee_ids and rec.minimum_approver == len(rec.approver_confirm):
                    rec.approver_state = 'approved'
                else:
                    rec.approver_state = 'pending'
            if rec.change_request_id.state == 'rejected':
                rec.approver_state = 'refuse'