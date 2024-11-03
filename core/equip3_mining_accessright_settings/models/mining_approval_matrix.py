from werkzeug.urls import url_encode
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import format_datetime
from odoo.addons.equip3_mining_accessright_settings.models.acrux_chat_connector import ca_request
from odoo.addons.equip3_mining_accessright_settings.models.qiscus_connector import qiscus_request


class MiningApprovalMatrix(models.Model):
    _name = 'mining.approval.matrix'
    _description = 'Mining Approval Matrix'
    _inherit = 'mail.thread'

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id', False)
        if default_branch_id:
            return default_branch_id
        return self.env.branch.id if len(self.env.branches) == 1 else False

    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids)]

    name = fields.Char(string='Name', required=True, copy=False, tracking=True)
    company_id = fields.Many2one(
        comodel_name='res.company', 
        required=True, 
        default=lambda self: self.env.company, 
        readonly=True,
        copy=False,
        string='Company'
    )
    
    branch_id = fields.Many2one(
        comodel_name='res.branch', 
        required=True, 
        default=_default_branch, 
        domain=_domain_branch,
        copy=False,
        string='Branch',
        tracking=True)
    
    line_ids = fields.One2many('mining.approval.matrix.line', 'matrix_id',  string='Approval Lines')

    @api.constrains('line_ids')
    def _constraint_line_ids(self):
        for matrix in self:
            if not matrix.line_ids:
                raise ValidationError(_('Please set Approver Lines!'))

    def get_approval_entries(self, Model, states=None):
        self.ensure_one()
        entry = self.env['mining.approval.matrix.entry']
        field_id = self.env['ir.model.fields'].sudo().search([
            ('model', '=', Model._name),
            ('ttype', '=', 'one2many'),
            ('relation_field', 'in', tuple(entry._fields.keys())),
            ('relation', '=', entry._name)
        ], limit=1)
        entry_ids = Model[field_id.name]
        if states is None:
            return entry_ids
        if isinstance(states, list) or isinstance(states, tuple):
            return entry_ids.filtered(lambda m: m.state in states)
        return entry_ids.filtered(lambda m: m.state == states)

    def get_approvers(self, included=None, excluded=None):
        self.ensure_one()
        approver_ids = self.line_ids.mapped('approver_ids')
        if isinstance(included, type(self.env['res.users'])):
            approver_ids |= included
        if isinstance(excluded, type(self.env['res.users'])):
            approver_ids -= excluded
        return approver_ids.mapped('partner_id')

    def get_company_model(self, Model):
        if 'company_id' in Model._fields:
            return Model.company_id
        elif 'company' in Model._fields:
            return Model.company
        return self.env.company

    def get_branch_model(self, Model):
        if 'branch_id' in Model._fields:
            return Model.branch_id
        elif 'branch' in Model._fields:
            return Model.branch
        return self.env.user.branch_id

    def get_model_action_xmlid(self):
        return

    def get_model_menu_xmlid(self):
        return

    def get_form_url(self, Model, full=True):
        self.ensure_one()
        action_xmlid = self.get_model_action_xmlid()
        menu_xmlid = self.get_model_menu_xmlid()

        try:
            action_id = self.env.ref(action_xmlid).id
        except Exception:
            action_id = ''

        try:
            menu_id = self.env.ref(menu_xmlid).id
        except Exception:
            menu_id = ''
        
        params = {
            'id': Model.id,
            'model': Model._name,
            'action': action_id,
            'menu_id': menu_id,
            'view_type': 'form'
        }
        form_url = '/web#%s' % url_encode(params)
        if not full:
            return form_url
        return self.env['ir.config_parameter'].sudo().get_param('web.base.url') + form_url

    def _render_decode(self, xml_id, values):
        self.ensure_one()
        Qweb = self.env['ir.qweb'].sudo()
        return Qweb._render(xml_id, values).decode()

    def _prepare_template_values(self, Model, requested_time):
        self.ensure_one()
        company = self.get_company_model(Model)
            
        return {
            'user': self.env.user,
            'object_label': Model._description,
            'object_ref': Model[Model._rec_name],
            'requested_time': requested_time,
            'company': company,
            'full_form_url': self.get_form_url(Model),
            'form_url': self.get_form_url(Model, full=False)
        }

    def _prepare_send_whatsapp_notification(self, partner_ids):
        for partner_id in partner_ids:
            if not partner_id.mobile:
                raise ValidationError(_("Please set mobile number for %s!" % partner_id.name))

    def post_log(self, Model, partner_ids, values):
        self.ensure_one()
        partner_names = '/'.join(partner.name for partner in partner_ids)

        xml_id = 'equip3_mining_accessright_settings.mining_approval_html_body'
        values.update({'partner_name': partner_names})
        Model.message_post(body=self._render_decode(xml_id, values))

    def send_system_notification(self, Model, partner_id, values):
        self.ensure_one()
        xml_id = 'equip3_mining_accessright_settings.mining_approval_html_body'
        odoobot_id = self.env['ir.model.data'].xmlid_to_res_id('base.partner_root')

        self.env['mail.notification'].sudo().create({
            'mail_message_id': self.env['mail.message'].sudo().create({
                'author_id': odoobot_id,
                'message_type': 'user_notification',
                'is_internal': True,
                'body': self._render_decode(xml_id, values)
            }).id,
            'notification_type': 'email',
            'res_partner_id': partner_id.id
        })

    def send_email_notification(self, Model, partner_id, values):
        self.ensure_one()
        xml_id = 'equip3_mining_accessright_settings.mining_approval_mail_reuse'
        company = self.get_company_model(Model)
        mail_from = '"%s" <%s>' % (company.name, company.email or self.env.user.partner_id.email)
        odoobot_id = self.env['ir.model.data'].xmlid_to_res_id('base.partner_root')

        Mail = self.env['mail.mail'].sudo().create({
            'subject': 'Request for Approval %s' % values.get('object_ref'),
            'author_id': odoobot_id,
            'email_from': mail_from,
            'recipient_ids': [(6, 0, partner_id.ids)],
            'message_type': 'email',
            'model': Model._name,
            'res_id': Model.id,
            'auto_delete': True,
            'body_html': self._render_decode(xml_id, values)
        })
        Mail.send(raise_exception=False)

    def send_whatsapp_notification(self, Model, partner_id, values):
        self.ensure_one()
        xml_id = 'equip3_mining_accessright_settings.mining_approval_text_body'
        
        message = self._render_decode(xml_id, values)
        if partner_id.mobile:
            phone_number = partner_id.mobile.replace('+', '')
        else:
            phone_number = partner_id.mobile
        qiscus_request(self, message, phone_number)

    def process_notifications(self, Model, options, requested_time):
        self.ensure_one()
        if options is None:
            options = {}

        partner_ids = self.get_approvers()
        values = self._prepare_template_values(Model, requested_time)

        # send one log message for all approvers
        if options.get('post_log', False):
            self.post_log(Model, partner_ids, values)

        # send message for each approvers
        for partner_id in partner_ids:
            values.update({'partner_name': partner_id.name})
            if options.get('send_system', False):
                self.send_system_notification(Model, partner_id, values)
            if options.get('send_email', False):
                self.send_email_notification(Model, partner_id, values)
            if options.get('send_whatsapp', False):
                self.send_whatsapp_notification(Model, partner_id, values)

    def action_approval(self, Model, options=None):
        self.ensure_one()
        now = fields.Datetime.now()
        entry_ids = self.get_approval_entries(Model)
        for entry in entry_ids:
            entry.write({
                'requested_id': self.env.user.id,
                'requested_time': now,
                'line_ids': [(0, 0, {
                    'approver_id': approver.id,
                    'state': 'to_approve'
                }) for approver in entry.approver_ids]
            })

        now_formatted = format_datetime(self.env, now)
        self.process_notifications(Model, options, now_formatted)
        return True

    def action_approve(self, Model):
        self.ensure_one()
        now = fields.Datetime.now()
        now_formatted = format_datetime(self.env, now)
        entry_ids = self.get_approval_entries(Model, states='to_approve')

        for entry in entry_ids:
            entry_lines = entry.line_ids
            entry_line_id = entry_lines.filtered(lambda l: l.approver_id == self.env.user)
            if not entry_line_id:
                continue
            entry.write({
                'line_ids': [(1, entry_line_id.id, {
                    'state': 'approved',
                    'note': 'Approved By: %s, %s' % (self.env.user.name, now_formatted),
                    'action_time': now
                })],
            })
        return True

    def action_reject(self, Model, reason=False):
        self.ensure_one()

        if not self.env.context.get('skip_reject_wizard'):
            return {
                'type': 'ir.actions.act_window',
                'name': _('Reject Reason'),
                'res_model': 'mining.approval.matrix.reject',
                'target': 'new',
                'view_mode': 'form',
                'context': {
                    'default_model_name': Model._name,
                    'default_model_id': Model.id
                }
            }

        now = fields.Datetime.now()
        now_formatted = format_datetime(self.env, now)
        entry_ids = self.get_approval_entries(Model, states='to_approve')

        for entry in entry_ids:
            entry_lines = entry.line_ids
            entry_line_id = entry_lines.filtered(lambda l: l.approver_id == self.env.user)
            if not entry_line_id:
                continue
            note = 'Rejected By: %s, %s' % (self.env.user.name, now_formatted)
            if reason:
                note += ', Reason: %s' % reason
            entry.write({
                'line_ids': [(1, entry_line_id.id, {
                    'state': 'rejected',
                    'note': note,
                    'action_time': now
                })],
            })
        return True

    def toggle_on_off(self, Model, is_on):
        field_id = self.env['ir.model.fields'].sudo().search([
            ('model', '=', Model._name),
            ('ttype', '=', 'many2one'),
            ('relation', '=', 'mining.approval.matrix')
        ], limit=1)
        approval_matrix_id = False
        if is_on:
            company = self.get_company_model(Model)
            branch = self.get_branch_model(Model)
            approval_matrix_id = Model._default_approval_matrix(company=company, branch=branch)
        Model.write({field_id.name: approval_matrix_id})


class MiningApprovalMatrixLine(models.Model):
    _name = 'mining.approval.matrix.line'
    _description = 'Mining Approval Matrix Line'

    @api.depends('matrix_id', 'matrix_id.line_ids', 'matrix_id.line_ids.approver_ids')
    def _compute_added_approvers(self):
        for record in self:
            added_approvers = record.matrix_id.line_ids.mapped('approver_ids')
            record.added_approver_ids = [(6, 0, added_approvers.ids)]

    @api.depends('matrix_id', 'matrix_id.line_ids')
    def _compute_sequence(self):
        for record in self:
            lines = record.matrix_id.line_ids
            for sequence, line in enumerate(lines):
                line.sequence = sequence + 1

    matrix_id = fields.Many2one('mining.approval.matrix', 'Approval Matrix')

    sequence = fields.Integer('Sequence', compute=_compute_sequence)
    sequence_handle = fields.Integer('Sequence Handle')
    
    # cannot add same approver on diffrent line 
    added_approver_ids = fields.Many2many('res.users', compute=_compute_added_approvers)
    approver_ids = fields.Many2many('res.users', string='Approver', domain="[('id', 'not in', added_approver_ids)]")
    
    minimum_approver = fields.Integer('Minimum Approver', default=1, required=True)
