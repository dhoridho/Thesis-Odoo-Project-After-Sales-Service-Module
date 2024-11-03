# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError


class JobEstimate(models.Model):
    _inherit = 'job.estimate'

    is_engineering = fields.Boolean('Engineering', store=True)
    manufacture_line = fields.One2many('to.manufacture.line', 'job_estimate_id')

    hide_cascade = fields.Boolean('Hide cascade button', default=True, compute='_compute_hide_cascade')
    hide_undo = fields.Boolean('Hide undo button', default=True, compute='_compute_hide_undo')
    construction_type = fields.Selection(string="Construction Type", related='project_id.construction_type')

    def copy(self, default=None, context=None):
        if default is None:
            default = {}
        # Workaround for action_boq_revision, it somehow needs to be False
        # Add context conditional if this causes any conflict
        default.update({
            'project_scope_ids': False,
            'section_ids': False,
            'variable_ids': False,
            'manufacture_line': False,
            'quotation_id': False,
        })
        return super(JobEstimate, self).copy(default)

    @api.onchange('project_id')
    def onchange_project_enginerring(self):
        if self.project_id:
            # self.is_engineering = False
            if self.project_id.construction_type == 'engineering':
                self.is_engineering = True
            else:
                self.is_engineering = False

    @api.onchange('section_ids')
    def _onchange_section(self):
        res = super(JobEstimate, self)._onchange_section()
        for rec in self:
            if rec.is_engineering:
                changed_section = list()
                section_list = list()
                if len(rec.section_ids) > 0 or len(rec._origin.section_ids._origin):
                    for section in rec.section_ids:
                        # same logic as _onchange_project_scope
                        section_list.append(section.section_name.id)
                        if section._origin.section_name._origin.id:
                            if section.section_name.id != section._origin.section_name._origin.id:
                                changed_section.append(section._origin.section_name._origin.id)
                        else:
                            changed_section.append(section.section_name.id)
                if len(rec.manufacture_line) > 0:
                    for manufacture in rec.manufacture_line:
                        if manufacture.section_id.id in changed_section:
                            rec.manufacture_line = [(2, manufacture._origin.id, 0)]
                        if manufacture.section_id.id not in section_list:
                            rec.manufacture_line = [(2, manufacture.id, 0)]
        return res

    @api.onchange('manufacture_line')
    def _onchange_manufacture_line(self):
        for rec in self:
            if rec.is_engineering:
                # changed_manufacture = list()
                # manufacture_list = list()

                # if len(rec.manufacture_line) > 0 or len(rec._origin.manufacture_line._origin):
                #     for manufacture in rec.manufacture_line:
                #         manufacture_list.append(manufacture.finish_good_id.id)
                #         if manufacture._origin.finish_good_id._origin.id:
                #             if manufacture.finish_good_id.id != manufacture._origin.finish_good_id._origin.id:
                #                 changed_manufacture.append(manufacture._origin.finish_good_id._origin.id)
                #         else:
                #             changed_manufacture.append(manufacture.finish_good_id._origin.id)
                if len(rec.manufacture_line) > 0:
                    for manufacture in rec.manufacture_line:
                        if manufacture.parent_finish_good_id:
                            if manufacture.parent_finish_good_id.id not in rec.manufacture_line.mapped(
                                    'finish_good_id').ids:
                                rec.manufacture_line = [(2, manufacture._origin.id or manufacture.id, 0)]
                            # if manufacture.parent_finish_good_id.id not in manufacture_list:
                            #     rec.manufacture_line = [(2, manufacture.id, 0)]

                        retrieved_line = []
                        for line in manufacture.bom_id.bom_line_ids:
                            if line.product_id.id not in rec.material_estimation_ids.mapped('product_id').ids \
                                    and line.product_id.id not in rec.manufacture_line.mapped('finish_good_id').ids:
                                retrieved_line.append((0, 0, {
                                    'is_new': True,
                                    'project_scope': manufacture.project_scope_id.id,
                                    'section_name': manufacture.section_id.id,
                                    'variable_ref': manufacture.variable_ref.id or False,
                                    'finish_good_id': manufacture.finish_good_id.id,
                                    'bom_id': manufacture.bom_id.id,
                                    'group_of_product': line.group_of_product.id,
                                    'product_id': line.product_id.id,
                                    'description': line.product_id.display_name,
                                    'quantity': manufacture.quantity * line.product_qty,
                                    'uom_id': line.product_uom_id.id,
                                    'unit_price': line.cost,
                                    'subtotal': line.cost * (manufacture.quantity * line.product_qty),
                                    'operation_two_id': line.operation_two_id.id,
                                }))

                        if len(retrieved_line) > 0:
                            rec.material_estimation_ids = retrieved_line

    def set_manufacture_quantity(self, parent):
        for rec in self:
            child_manufacture = rec.manufacture_line.search([('parent_finish_good_id', '=', parent.finish_good_id.id)])
            i = 0
            next_manufacture = []
            while child_manufacture:
                for manufacture in child_manufacture:
                    parent_manufacture = rec.manufacture_line.search(
                        [('finish_good_id', '=', manufacture.parent_finish_good_id.id)])
                    if i == 0:
                        quantity = parent.quantity * manufacture.initial_quantity
                    else:
                        quantity = parent_manufacture.quantity * manufacture.initial_quantity
                    rec.manufacture_line = [(1,manufacture.id, {'quantity': quantity})]
                    manufacture.update({'quantity': quantity})
                    i += 1

                    temp_child_manufacture = rec.manufacture_line.search(
                        [('parent_finish_good_id', '=', manufacture.finish_good_id.id)])
                    for child in temp_child_manufacture:
                        if child not in next_manufacture:
                            next_manufacture.append(child)

                if len(next_manufacture) == 0:
                    return
                else:
                    child_manufacture = next_manufacture[0]
                    next_manufacture.pop(0)

    @api.onchange('manufacture_line')
    def _onchange_manufacture_line_queantity(self):
        for rec in self:
            for manufacture in rec.manufacture_line:
                if manufacture.is_changed:
                    manufacture.write({'is_changed': False})
                    rec.set_manufacture_quantity(manufacture)

    def action_job_estimate_revision(self, default=None):
        self.state = 'revised'
        self.state_new = 'revised'
        if self:
            self.ensure_one()
            self.is_revision_created = True
            if default is None:
                default = {}

            # Change name
            if self.is_revision_je:
                je_count = self.search(
                    [("main_revision_je_id", '=', self.main_revision_je_id.id), ('is_revision_je', '=', True)])
                split_name = self.name.split('/')
                if split_name[-1].startswith('R'):
                    split_name[-1] = 'R%d' % (len(je_count) + 1)
                else:
                    split_name.append('R%d' % (len(je_count) + 1))
                name = '/'.join(split_name)
            else:
                je_count = self.search([("main_revision_je_id", '=', self.id), ('is_revision_je', '=', True)])
                name = _('%s/R%d') % (self.name, len(je_count) + 1)

            # Setting the default values for the new record.
            if 'name' not in default:
                default['state'] = 'draft'
                default['revision_je_id'] = self.id
                default['is_revision_je'] = True
                if self.is_revision_je:
                    default['main_revision_je_id'] = self.main_revision_je_id.id
                else:
                    default['main_revision_je_id'] = self.id
                default['is_revision_created'] = False
                default['revision_count'] = 0

            new_project_id = self.copy(default=default)
            # Project Scope
            for scope_line in self.project_scope_ids:
                scope_line.copy({
                    'scope_id': new_project_id.id,
                })
            # Section
            for section_line in self.section_ids:
                section_line.copy({
                    'section_id': new_project_id.id,
                })
            # Variable
            for variable_line in self.variable_ids:
                variable_line.copy({
                    'variable_id': new_project_id.id,
                })
            # To Manufacture
            for manufacture_line in self.manufacture_line:
                manufacture_line.copy({
                    'job_estimate_id': new_project_id.id,
                })
            # Material Est
            for material_line in self.material_estimation_ids:
                material_line.copy({
                    'material_id': new_project_id.id,
                })
            # Labour Est
            for labour_line in self.labour_estimation_ids:
                labour_line.copy({
                    'labour_id': new_project_id.id,
                })
            # Overhead Est
            for overhead_line in self.overhead_estimation_ids:
                overhead_line.copy({
                    'overhead_id': new_project_id.id,
                })
            # Equipment Est
            for equipment_line in self.equipment_estimation_ids:
                equipment_line.copy({
                    'equipment_id': new_project_id.id,
                })
            # Asset Est
            for asset_line in self.internal_asset_ids:
                asset_line.copy({
                    'asset_job_id': new_project_id.id,
                })
            # Subcon Est
            for subcon_line in self.subcon_estimation_ids:
                subcon_line.copy({
                    'subcon_id': new_project_id.id,
                })
            # Approval Matrix Line
            for approval_line in self.job_estimate_user_ids:
                approval_line.copy({
                    'job_estimate_approver_id': new_project_id.id,
                })

            new_project_id.is_rejected = False
            new_project_id.is_cancelled = False
            new_project_id.job_estimate_user_ids = [(5, 0, 0)]
            new_project_id.write({'state': 'draft',
                          'state_new': 'draft',
                          'approved_user_ids': False,
                          'approved_user': False,
                          })
            new_project_id.onchange_approving_matrix_lines()

            if name.startswith('BOQ'):
                new_project_id.name = name

            if name.startswith('BOQ/VO'):
                new_project_id.name = name

            if self.is_revision_je:
                new_project_id.revision_history_id = [(6, 0, self.main_revision_je_id.ids + je_count.ids)]
            else:
                new_project_id.revision_history_id = [(6, 0, self.ids)]

        return {
            'type': 'ir.actions.act_window',
            'name': 'BOQ',
            'view_mode': 'form',
            'res_model': 'job.estimate',
            'res_id': new_project_id.id,
            'target': 'current'
        }
    
    def action_boq_revision(self, job, default=None):
        job.state = 'revised'
        job.state_new = 'revised'
        if job:
            job.ensure_one()
            job.is_revision_created = True
            if default is None:
                default = {}

            # Change name
            if job.is_revision_je:
                je_count = self.search([("main_revision_je_id", '=', job.main_revision_je_id.id), ('is_revision_je', '=', True)])
                split_name = job.name.split('/')
                if split_name[-1].startswith('R'):
                    split_name[-1] = 'R%d' % (len(je_count) + 1)
                else:
                    split_name.append('R%d' % (len(je_count) + 1))
                name = '/'.join(split_name)
            else:
                je_count = self.search([("main_revision_je_id", '=', job.id), ('is_revision_je', '=', True)])
                name = _('%s/R%d') % (job.name, len(je_count) + 1)

            # Setting the default values for the new record.
            if 'name' not in default:
                default['state'] = 'draft'
                default['revision_je_id'] = job.id 
                default['is_revision_je'] = True
                if self.is_revision_je:
                    default['main_revision_je_id'] = job.main_revision_je_id.id
                else:
                    default['main_revision_je_id'] = job.id
                default['is_revision_created'] = False
                default['revision_count'] = 0
                
            new_project_id = job.copy(default=default)
            # Project Scope
            for scope_line in job.project_scope_ids:
                scope_line.copy({
                    'scope_id': new_project_id.id,
                })
            # Section
            for section_line in job.section_ids:
                section_line.copy({
                    'section_id': new_project_id.id,
                })
            # Variable
            for variable_line in job.variable_ids:
                variable_line.copy({
                    'variable_id': new_project_id.id,
                })
            # To Manufacture
            for manufacture_line in job.manufacture_line:
                manufacture_line.copy({
                    'job_estimate_id': new_project_id.id,
                })
            # Material Est
            for material_line in job.material_estimation_ids:
                material_line.copy({
                    'material_id': new_project_id.id,
                })
            # Labour Est
            for labour_line in job.labour_estimation_ids:
                labour_line.copy({
                    'labour_id': new_project_id.id,
                })
            # Overhead Est
            for overhead_line in job.overhead_estimation_ids:
                overhead_line.copy({
                    'overhead_id': new_project_id.id,
                })
            # Equipment Est
            for equipment_line in job.equipment_estimation_ids:
                equipment_line.copy({
                    'equipment_id': new_project_id.id,
                })
            # Asset Est
            for asset_line in job.internal_asset_ids:
                asset_line.copy({
                    'asset_job_id': new_project_id.id,
                })
            # Subcon Est
            for subcon_line in job.subcon_estimation_ids:
                subcon_line.copy({
                    'subcon_id': new_project_id.id,
                })
            # Approval Matrix Line
            for approval_line in job.job_estimate_user_ids:
                approval_line.copy({
                    'job_estimate_approver_id': new_project_id.id,
                })

            new_project_id.is_rejected = False
            new_project_id.is_cancelled = False
            new_project_id.job_estimate_user_ids = [(5, 0, 0)]
            new_project_id.write({'state': 'draft',
                          'state_new': 'draft',
                          'approved_user_ids': False,
                          'approved_user': False,
                          })
            new_project_id.onchange_approving_matrix_lines()

            if name.startswith('BOQ'):
                new_project_id.name = name

            if name.startswith('BOQ/VO'):
                new_project_id.name = name

            if job.is_revision_je:
                new_project_id.revision_history_id = [(6, 0, job.main_revision_je_id.ids + je_count.ids)]
            else:
                new_project_id.revision_history_id = [(6, 0, job.ids)]
            

    @api.onchange('material_estimation_ids')
    def _check_exist_group_of_product_material(self):
        exist_section_group_list_material = []
        for line5 in self.material_estimation_ids:
            if self.is_engineering:
                if len(line5.finish_good_id) > 0 and len(line5.bom_id) > 0:
                    same3 = str(line5.project_scope.id) + ' - ' + str(line5.section_name.id) + ' - ' + str(
                        line5.product_id.id) + ' - ' + str(line5.finish_good_id.id) + ' - ' + str(
                        line5.bom_id.id) + ' - ' + str(line5.operation_two_id.id)
                    if (same3 in exist_section_group_list_material):
                        raise ValidationError(
                            _('The product "%s" already exists in the section "%s", finish good "%s", and bill of material "%s" please change the Section or Product selected.' % (
                                (line5.product_id.name), (line5.section_name.name), (line5.finish_good_id.name),
                                (line5.bom_id.name))))
                    exist_section_group_list_material.append(same3)
                else:
                    same3 = str(line5.project_scope.id) + ' - ' + str(line5.section_name.id) + ' - ' + str(
                        line5.product_id.id) + ' - ' + str(line5.operation_two_id.id)
                    if (same3 in exist_section_group_list_material):
                        raise ValidationError(
                            _('The product "%s" already exists in the section "%s", please change the Section or Product selected.' % (
                                (line5.product_id.name), (line5.section_name.name))))
                    exist_section_group_list_material.append(same3)
            else:
                same3 = str(line5.project_scope.id) + ' - ' + str(line5.section_name.id) + ' - ' + str(
                    line5.product_id.id) + ' - ' + str(line5.operation_two_id.id)
                if (same3 in exist_section_group_list_material):
                    raise ValidationError(
                        _('The product "%s" already exists in the section "%s", please change the Section or Product selected.' % (
                            (line5.product_id.name), (line5.section_name.name))))
                exist_section_group_list_material.append(same3)

    @api.constrains('material_estimation_ids')
    def _check_exist_group_of_product_material_2(self):
        exist_section_group_list_material = []
        for line5 in self.material_estimation_ids:
            if self.is_engineering:
                if len(line5.finish_good_id) > 0 and len(line5.bom_id) > 0:
                    same3 = str(line5.project_scope.id) + ' - ' + str(line5.section_name.id) + ' - ' + str(
                        line5.product_id.id) + ' - ' + str(line5.finish_good_id.id) + ' - ' + str(
                        line5.bom_id.id) + str(line5.operation_two_id.id)
                    if (same3 in exist_section_group_list_material):
                        raise ValidationError(
                            _('The product "%s" already exists in the section "%s", finish good "%s", and bill of material "%s" please change the Section or Product selected.' % (
                                (line5.product_id.name), (line5.section_name.name), (line5.finish_good_id.name),
                                (line5.bom_id.name))))
                    exist_section_group_list_material.append(same3)
                else:
                    same3 = str(line5.project_scope.id) + ' - ' + str(line5.section_name.id) + ' - ' + str(
                        line5.product_id.id) + ' - ' + str(line5.operation_two_id.id)
                    if (same3 in exist_section_group_list_material):
                        raise ValidationError(
                            _('The product "%s" already exists in the section "%s", please change the Section or Product selected.' % (
                                (line5.product_id.name), (line5.section_name.name))))
                    exist_section_group_list_material.append(same3)
            else:
                same3 = str(line5.project_scope.id) + ' - ' + str(line5.section_name.id) + ' - ' + str(
                    line5.product_id.id) + ' - ' + str(line5.operation_two_id.id)
                if (same3 in exist_section_group_list_material):
                    raise ValidationError(
                        _('The product "%s" already exists in the section "%s", please change the Section or Product selected.' % (
                            (line5.product_id.name), (line5.section_name.name))))
                exist_section_group_list_material.append(same3)

    @api.onchange('labour_estimation_ids')
    def _check_exist_group_of_product_labour(self):
        exist_section_group_list_labour1 = []
        exist_section_group_list_labour2 = []
        exist_section_group_list_labour3 = []
        exist_section_group_list_labour4 = []
        for line6 in self.labour_estimation_ids:
            if line6.project_scope and line6.section_name:
                if self.is_engineering:
                    if len(line6.finish_good_id) > 0 and len(line6.bom_id) > 0:
                        same41 = str(line6.project_scope.id) + ' - ' + str(line6.section_name.id) + ' - ' + str(
                            line6.product_id.id) + ' - ' + str(line6.finish_good_id.id) + ' - ' + str(
                            line6.bom_id.id) + ' - ' + str(line6.operation_two_id.id)
                        if (same41 in exist_section_group_list_labour1):
                            raise ValidationError(
                                _('The product "%s" already exists in project scope "%s", section "%s", finish good "%s", and bill of material "%s" please change the Project Scope or Section or Product selected.' % (
                                    (line6.product_id.name), (line6.project_scope.name), (line6.section_name.name),
                                    (line6.finish_good_id.name), (line6.bom_id.name))))
                        exist_section_group_list_labour1.append(same41)
                    else:
                        same41 = str(line6.project_scope.id) + ' - ' + str(line6.section_name.id) + ' - ' + str(
                            line6.product_id.id) + ' - ' + str(line6.operation_two_id.id)
                        if (same41 in exist_section_group_list_labour1):
                            raise ValidationError(
                                _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                                    (line6.product_id.name), (line6.project_scope.name), (line6.section_name.name))))
                        exist_section_group_list_labour1.append(same41)
                else:
                    same41 = str(line6.project_scope.id) + ' - ' + str(line6.section_name.id) + ' - ' + str(
                        line6.product_id.id) + ' - ' + str(line6.operation_two_id.id)
                    if (same41 in exist_section_group_list_labour1):
                        raise ValidationError(
                            _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                                (line6.product_id.name), (line6.project_scope.name), (line6.section_name.name))))
                    exist_section_group_list_labour1.append(same41)
            elif line6.project_scope and not line6.section_name:
                same42 = str(line6.project_scope.id) + ' - ' + str(line6.product_id.id) + ' - ' + str(
                    line6.operation_two_id.id)
                if (same42 in exist_section_group_list_labour2):
                    raise ValidationError(
                        _('The product "%s" already exists in the project scope "%s", please change the Project Scope or Product selected.' % (
                            (line6.product_id.name), (line6.project_scope.name))))
                exist_section_group_list_labour2.append(same42)
            elif not line6.project_scope and line6.section_name:
                same43 = str(line6.section_name.id) + ' - ' + str(line6.product_id.id) + ' - ' + str(
                    line6.operation_two_id.id)
                if (same43 in exist_section_group_list_labour3):
                    raise ValidationError(
                        _('The product "%s" already exists in the section "%s", please change the Section or Product selected.' % (
                            (line6.product_id.name), (line6.section_name.name))))
                exist_section_group_list_labour3.append(same43)
            elif not line6.project_scope and not line6.section_name:
                same44 = str(line6.product_id.id) + ' - ' + str(line6.operation_two_id.id)
                if (same44 in exist_section_group_list_labour4):
                    raise ValidationError(_('The product "%s" already exists, please change the Product selected.' % (
                        (line6.product_id.name))))
                exist_section_group_list_labour4.append(same44)

    @api.constrains('labour_estimation_ids')
    def _check_exist_group_of_product_labour_2(self):
        exist_section_group_list_labour1 = []
        exist_section_group_list_labour2 = []
        exist_section_group_list_labour3 = []
        exist_section_group_list_labour4 = []
        for line6 in self.labour_estimation_ids:
            if line6.project_scope and line6.section_name:
                if self.is_engineering:
                    if len(line6.finish_good_id) > 0 and len(line6.bom_id) > 0:
                        same41 = str(line6.project_scope.id) + ' - ' + str(line6.section_name.id) + ' - ' + str(
                            line6.product_id.id) + ' - ' + str(line6.finish_good_id.id) + ' - ' + str(
                            line6.bom_id.id) + ' - ' + str(line6.operation_two_id.id)
                        if (same41 in exist_section_group_list_labour1):
                            raise ValidationError(
                                _('The product "%s" already exists in project scope "%s", section "%s", finish good "%s", and bill of material "%s" please change the Project Scope or Section or Product selected.' % (
                                    (line6.product_id.name), (line6.project_scope.name), (line6.section_name.name),
                                    (line6.finish_good_id.name), (line6.bom_id.name))))
                        exist_section_group_list_labour1.append(same41)
                    else:
                        same41 = str(line6.project_scope.id) + ' - ' + str(line6.section_name.id) + ' - ' + str(
                            line6.product_id.id) + ' - ' + str(line6.operation_two_id.id)
                        if (same41 in exist_section_group_list_labour1):
                            raise ValidationError(
                                _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                                    (line6.product_id.name), (line6.project_scope.name), (line6.section_name.name))))
                        exist_section_group_list_labour1.append(same41)
                else:
                    same41 = str(line6.project_scope.id) + ' - ' + str(line6.section_name.id) + ' - ' + str(
                        line6.product_id.id) + ' - ' + str(line6.operation_two_id.id)
                    if (same41 in exist_section_group_list_labour1):
                        raise ValidationError(
                            _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                                (line6.product_id.name), (line6.project_scope.name), (line6.section_name.name))))
                    exist_section_group_list_labour1.append(same41)
            elif line6.project_scope and not line6.section_name:
                same42 = str(line6.project_scope.id) + ' - ' + str(line6.product_id.id) + ' - ' + str(
                    line6.operation_two_id.id)
                if (same42 in exist_section_group_list_labour2):
                    raise ValidationError(
                        _('The product "%s" already exists in the project scope "%s", please change the Project Scope or Product selected.' % (
                            (line6.product_id.name), (line6.project_scope.name))))
                exist_section_group_list_labour2.append(same42)
            elif not line6.project_scope and line6.section_name:
                same43 = str(line6.section_name.id) + ' - ' + str(line6.product_id.id) + ' - ' + str(
                    line6.operation_two_id.id)
                if (same43 in exist_section_group_list_labour3):
                    raise ValidationError(
                        _('The product "%s" already exists in the section "%s", please change the Section or Product selected.' % (
                            (line6.product_id.name), (line6.section_name.name))))
                exist_section_group_list_labour3.append(same43)
            elif not line6.project_scope and not line6.section_name:
                same44 = str(line6.product_id.id) + ' - ' + str(line6.operation_two_id.id)
                if (same44 in exist_section_group_list_labour4):
                    raise ValidationError(_('The product "%s" already exists, please change the Product selected.' % (
                        (line6.product_id.name))))
                exist_section_group_list_labour4.append(same44)

    @api.onchange('overhead_estimation_ids')
    def _check_exist_group_of_product_overhead(self):
        exist_section_group_list_overhead = []
        for line7 in self.overhead_estimation_ids:
            if self.is_engineering:
                if len(line7.finish_good_id) > 0 and len(line7.bom_id) > 0:
                    same5 = str(line7.project_scope.id) + ' - ' + str(line7.section_name.id) + ' - ' + str(
                        line7.product_id.id) + ' - ' + str(line7.finish_good_id.id) + ' - ' + str(
                        line7.bom_id.id) + ' - ' + str(line7.operation_two_id.id)
                    if (same5 in exist_section_group_list_overhead):
                        raise ValidationError(
                            _('The product "%s" already exists in the section "%s", finish good "%s", and bill of material "%s" please change the Section or Product selected.' % (
                                (line7.product_id.name), (line7.section_name.name), (line7.finish_good_id.name),
                                (line7.bom_id.name))))
                    exist_section_group_list_overhead.append(same5)
                else:
                    same5 = str(line7.project_scope.id) + ' - ' + str(line7.section_name.id) + ' - ' + str(
                        line7.product_id.id) + ' - ' + str(line7.operation_two_id.id)
                    if (same5 in exist_section_group_list_overhead):
                        raise ValidationError(
                            _('The product "%s" already exists in the section "%s", please change the Section or Product selected.' % (
                                (line7.product_id.name), (line7.section_name.name))))
                    exist_section_group_list_overhead.append(same5)
            else:
                same5 = str(line7.project_scope.id) + ' - ' + str(line7.section_name.id) + ' - ' + str(
                    line7.product_id.id) + ' - ' + str(line7.operation_two_id.id)
                if (same5 in exist_section_group_list_overhead):
                    raise ValidationError(
                        _('The product "%s" already exists in the section "%s", please change the Section or Product selected.' % (
                            (line7.product_id.name), (line7.section_name.name))))
                exist_section_group_list_overhead.append(same5)

    @api.constrains('overhead_estimation_ids')
    def _check_exist_group_of_product_overhead_2(self):
        exist_section_group_list_overhead = []
        for line7 in self.overhead_estimation_ids:
            if self.is_engineering:
                if len(line7.finish_good_id) > 0 and len(line7.bom_id) > 0:
                    same5 = str(line7.project_scope.id) + ' - ' + str(line7.section_name.id) + ' - ' + str(
                        line7.product_id.id) + ' - ' + str(line7.finish_good_id.id) + ' - ' + str(
                        line7.bom_id.id) + ' - ' + str(line7.operation_two_id.id)
                    if (same5 in exist_section_group_list_overhead):
                        raise ValidationError(
                            _('The product "%s" already exists in the section "%s", finish good "%s", and bill of material "%s" please change the Section or Product selected.' % (
                                (line7.product_id.name), (line7.section_name.name), (line7.finish_good_id.name),
                                (line7.bom_id.name))))
                    exist_section_group_list_overhead.append(same5)
                else:
                    same5 = str(line7.project_scope.id) + ' - ' + str(line7.section_name.id) + ' - ' + str(
                        line7.product_id.id) + ' - ' + str(line7.operation_two_id.id)
                    if (same5 in exist_section_group_list_overhead):
                        raise ValidationError(
                            _('The product "%s" already exists in the section "%s", please change the Section or Product selected.' % (
                                (line7.product_id.name), (line7.section_name.name))))
                    exist_section_group_list_overhead.append(same5)
            else:
                same5 = str(line7.project_scope.id) + ' - ' + str(line7.section_name.id) + ' - ' + str(
                    line7.product_id.id) + ' - ' + str(line7.operation_two_id.id)
                if (same5 in exist_section_group_list_overhead):
                    raise ValidationError(
                        _('The product "%s" already exists in the section "%s", please change the Section or Product selected.' % (
                            (line7.product_id.name), (line7.section_name.name))))
                exist_section_group_list_overhead.append(same5)

    @api.onchange('equipment_estimation_ids')
    def _check_exist_group_of_product_equipment(self):
        exist_section_group_list_equipment1 = []
        exist_section_group_list_equipment2 = []
        exist_section_group_list_equipment3 = []
        exist_section_group_list_equipment4 = []
        for line8 in self.equipment_estimation_ids:
            if line8.project_scope and line8.section_name:
                if len(line8.finish_good_id) > 0 and len(line8.bom_id) > 0:
                    same51 = str(line8.project_scope.id) + ' - ' + str(line8.section_name.id) + ' - ' + str(
                        line8.product_id.id) + ' - ' + str(line8.finish_good_id.id) + ' - ' + str(
                        line8.bom_id.id) + ' - ' + str(line8.operation_two_id.id)
                    if (same51 in exist_section_group_list_equipment1):
                        raise ValidationError(
                            _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                                (line8.product_id.name), (line8.project_scope.name), (line8.section_name.name))))
                    exist_section_group_list_equipment1.append(same51)
                else:
                    same51 = str(line8.project_scope.id) + ' - ' + str(line8.section_name.id) + ' - ' + str(
                        line8.product_id.id) + ' - ' + str(line8.operation_two_id.id)
                    if (same51 in exist_section_group_list_equipment1):
                        raise ValidationError(
                            _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                                (line8.product_id.name), (line8.project_scope.name), (line8.section_name.name))))
                    exist_section_group_list_equipment1.append(same51)
            elif line8.project_scope and not line8.section_name:
                same52 = str(line8.project_scope.id) + ' - ' + str(line8.product_id.id) + ' - ' + str(
                    line8.operation_two_id.id)
                if (same52 in exist_section_group_list_equipment2):
                    raise ValidationError(
                        _('The product "%s" already exists in the project scope "%s", please change the Project Scope or Product selected.' % (
                            (line8.product_id.name), (line8.project_scope.name))))
                exist_section_group_list_equipment2.append(same52)
            elif not line8.project_scope and line8.section_name:
                same53 = str(line8.section_name.id) + ' - ' + str(line8.product_id.id) + ' - ' + str(
                    line8.operation_two_id.id)
                if (same53 in exist_section_group_list_equipment3):
                    raise ValidationError(
                        _('The product "%s" already exists in the section "%s", please change the Section or Product selected.' % (
                            (line8.product_id.name), (line8.section_name.name))))
                exist_section_group_list_equipment3.append(same53)
            elif not line8.project_scope and not line8.section_name:
                same54 = str(line8.product_id.id) + ' - ' + str(line8.operation_two_id.id)
                if (same54 in exist_section_group_list_equipment4):
                    raise ValidationError(_('The product "%s" already exists, please change the Product selected.' % (
                        (line8.product_id.name))))
                exist_section_group_list_equipment4.append(same54)

    @api.constrains('equipment_estimation_ids')
    def _check_exist_group_of_product_equipment_2(self):
        exist_section_group_list_equipment1 = []
        exist_section_group_list_equipment2 = []
        exist_section_group_list_equipment3 = []
        exist_section_group_list_equipment4 = []
        for line8 in self.equipment_estimation_ids:
            if line8.project_scope and line8.section_name:
                if len(line8.finish_good_id) > 0 and len(line8.bom_id) > 0:
                    same51 = str(line8.project_scope.id) + ' - ' + str(line8.section_name.id) + ' - ' + str(
                        line8.product_id.id) + ' - ' + str(line8.finish_good_id.id) + ' - ' + str(
                        line8.bom_id.id) + ' - ' + str(line8.operation_two_id.id)
                    if (same51 in exist_section_group_list_equipment1):
                        raise ValidationError(
                            _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                                (line8.product_id.name), (line8.project_scope.name), (line8.section_name.name))))
                    exist_section_group_list_equipment1.append(same51)
                else:
                    same51 = str(line8.project_scope.id) + ' - ' + str(line8.section_name.id) + ' - ' + str(
                        line8.product_id.id) + ' - ' + str(line8.operation_two_id.id)
                    if (same51 in exist_section_group_list_equipment1):
                        raise ValidationError(
                            _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                                (line8.product_id.name), (line8.project_scope.name), (line8.section_name.name))))
                    exist_section_group_list_equipment1.append(same51)
            elif line8.project_scope and not line8.section_name:
                same52 = str(line8.project_scope.id) + ' - ' + str(line8.product_id.id) + ' - ' + str(
                    line8.operation_two_id.id)
                if (same52 in exist_section_group_list_equipment2):
                    raise ValidationError(
                        _('The product "%s" already exists in the project scope "%s", please change the Project Scope or Product selected.' % (
                            (line8.product_id.name), (line8.project_scope.name))))
                exist_section_group_list_equipment2.append(same52)
            elif not line8.project_scope and line8.section_name:
                same53 = str(line8.section_name.id) + ' - ' + str(line8.product_id.id) + ' - ' + str(
                    line8.operation_two_id.id)
                if (same53 in exist_section_group_list_equipment3):
                    raise ValidationError(
                        _('The product "%s" already exists in the section "%s", please change the Section or Product selected.' % (
                            (line8.product_id.name), (line8.section_name.name))))
                exist_section_group_list_equipment3.append(same53)
            elif not line8.project_scope and not line8.section_name:
                same54 = str(line8.product_id.id) + ' - ' + str(line8.operation_two_id.id)
                if (same54 in exist_section_group_list_equipment4):
                    raise ValidationError(_('The product "%s" already exists, please change the Product selected.' % (
                        (line8.product_id.name))))
                exist_section_group_list_equipment4.append(same54)

    @api.onchange('internal_asset_ids')
    def _check_exist_group_of_product_asset(self):
        exist_section_group_list_asset1 = []
        exist_section_group_list_asset2 = []
        exist_section_group_list_asset3 = []
        exist_section_group_list_asset4 = []
        for line9 in self.internal_asset_ids:
            if line9.project_scope and line9.section_name:
                if self.is_engineering:
                    if len(line9.finish_good_id) > 0 and len(line9.bom_id) > 0:
                        same71 = str(line9.project_scope.id) + ' - ' + str(line9.section_name.id) + ' - ' + str(
                            line9.asset_id.id) + str(line9.finish_good_id.id) + ' - ' + str(
                            line9.bom_id.id) + ' - ' + str(line9.operation_two_id.id)
                        if (same71 in exist_section_group_list_asset1):
                            raise ValidationError(
                                _('The product "%s" already exists in project scope "%s", section "%s", finish good "%s", bill of material "%s" please change the Project Scope or Section or Product selected.' % (
                                    (line9.asset_id.name), (line9.project_scope.name), (line9.section_name.name),
                                    (line9.finish_good_id.id), (line9.finish_good_id.id), (line9.bom_id.id))))
                        exist_section_group_list_asset1.append(same71)
                    else:
                        same71 = str(line9.project_scope.id) + ' - ' + str(line9.section_name.id) + ' - ' + str(
                            line9.asset_id.id) + ' - ' + str(line9.operation_two_id.id)
                        if (same71 in exist_section_group_list_asset1):
                            raise ValidationError(
                                _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                                    (line9.asset_id.name), (line9.project_scope.name), (line9.section_name.name))))
                        exist_section_group_list_asset1.append(same71)
                else:
                    same71 = str(line9.project_scope.id) + ' - ' + str(line9.section_name.id) + ' - ' + str(
                        line9.asset_id.id) + ' - ' + str(line9.operation_two_id.id)
                    if (same71 in exist_section_group_list_asset1):
                        raise ValidationError(
                            _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                                (line9.asset_id.name), (line9.project_scope.name), (line9.section_name.name))))
                    exist_section_group_list_asset1.append(same71)

            elif line9.project_scope and not line9.section_name:
                same72 = str(line9.project_scope.id) + ' - ' + str(line9.asset_id.id) + ' - ' + str(
                    line9.operation_two_id.id)
                if (same72 in exist_section_group_list_asset2):
                    raise ValidationError(
                        _('The product "%s" already exists in the project scope "%s", please change the Project Scope or Product selected.' % (
                            (line9.asset_id.name), (line9.project_scope.name))))
                exist_section_group_list_asset2.append(same72)
            elif not line9.project_scope and line9.section_name:
                same73 = str(line9.section_name.id) + ' - ' + str(line9.asset_id.id) + ' - ' + str(
                    line9.operation_two_id.id)
                if (same73 in exist_section_group_list_asset3):
                    raise ValidationError(
                        _('The product "%s" already exists in the section "%s", please change the Section or Product selected.' % (
                            (line9.asset_id.name), (line9.section_name.name))))
                exist_section_group_list_asset3.append(same73)
            elif not line9.project_scope and not line9.section_name:
                same74 = str(line9.asset_id.id) + ' - ' + str(line9.operation_two_id.id)
                if (same74 in exist_section_group_list_asset4):
                    raise ValidationError(_('The product "%s" already exists, please change the Product selected.' % (
                        (line9.asset_id.name))))
                exist_section_group_list_asset4.append(same74)

    @api.constrains('internal_asset_ids')
    def _check_exist_group_of_product_asset_2(self):
        exist_section_group_list_asset1 = []
        exist_section_group_list_asset2 = []
        exist_section_group_list_asset3 = []
        exist_section_group_list_asset4 = []
        for line9 in self.internal_asset_ids:
            if line9.project_scope and line9.section_name:
                if self.is_engineering:
                    if len(line9.finish_good_id) > 0 and len(line9.bom_id) > 0:
                        same71 = str(line9.project_scope.id) + ' - ' + str(line9.section_name.id) + ' - ' + str(
                            line9.asset_id.id) + str(line9.finish_good_id.id) + ' - ' + str(
                            line9.bom_id.id) + ' - ' + str(line9.operation_two_id.id)
                        if (same71 in exist_section_group_list_asset1):
                            raise ValidationError(
                                _('The product "%s" already exists in project scope "%s", section "%s", finish good "%s", bill of material "%s" please change the Project Scope or Section or Product selected.' % (
                                    (line9.asset_id.name), (line9.project_scope.name), (line9.section_name.name),
                                    (line9.finish_good_id.id), (line9.finish_good_id.id), (line9.bom_id.id))))
                        exist_section_group_list_asset1.append(same71)
                    else:
                        same71 = str(line9.project_scope.id) + ' - ' + str(line9.section_name.id) + ' - ' + str(
                            line9.asset_id.id) + ' - ' + str(line9.operation_two_id.id)
                        if (same71 in exist_section_group_list_asset1):
                            raise ValidationError(
                                _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                                    (line9.asset_id.name), (line9.project_scope.name), (line9.section_name.name))))
                        exist_section_group_list_asset1.append(same71)
                else:
                    same71 = str(line9.project_scope.id) + ' - ' + str(line9.section_name.id) + ' - ' + str(
                        line9.asset_id.id) + ' - ' + str(line9.operation_two_id.id)
                    if (same71 in exist_section_group_list_asset1):
                        raise ValidationError(
                            _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                                (line9.asset_id.name), (line9.project_scope.name), (line9.section_name.name))))
                    exist_section_group_list_asset1.append(same71)

            elif line9.project_scope and not line9.section_name:
                same72 = str(line9.project_scope.id) + ' - ' + str(line9.asset_id.id) + ' - ' + str(
                    line9.operation_two_id.id)
                if (same72 in exist_section_group_list_asset2):
                    raise ValidationError(
                        _('The product "%s" already exists in the project scope "%s", please change the Project Scope or Product selected.' % (
                            (line9.asset_id.name), (line9.project_scope.name))))
                exist_section_group_list_asset2.append(same72)
            elif not line9.project_scope and line9.section_name:
                same73 = str(line9.section_name.id) + ' - ' + str(line9.asset_id.id) + ' - ' + str(
                    line9.operation_two_id.id)
                if (same73 in exist_section_group_list_asset3):
                    raise ValidationError(
                        _('The product "%s" already exists in the section "%s", please change the Section or Product selected.' % (
                            (line9.asset_id.name), (line9.section_name.name))))
                exist_section_group_list_asset3.append(same73)
            elif not line9.project_scope and not line9.section_name:
                same74 = str(line9.asset_id.id) + ' - ' + str(line9.operation_two_id.id)
                if (same74 in exist_section_group_list_asset4):
                    raise ValidationError(_('The product "%s" already exists, please change the Product selected.' % (
                        (line9.asset_id.name))))
                exist_section_group_list_asset4.append(same74)

    @api.onchange('subcon_estimation_ids')
    def _check_exist_subcon(self):
        exist_section_subcon_list_subcon = []
        for line10 in self.subcon_estimation_ids:
            if len(line10.finish_good_id) > 0 and len(line10.bom_id) > 0:
                same8 = str(line10.project_scope.id) + ' - ' + str(line10.section_name.id) + ' - ' + str(
                    line10.variable.id) + str(line10.finish_good_id.id) + ' - ' + str(line10.bom_id.id) + ' - ' + str(
                    line10.operation_two_id.id)
                if (same8 in exist_section_subcon_list_subcon):
                    raise ValidationError(
                        _('The subcon "%s" already exists in project scope "%s", section "%s", finish good "%s", bill of material "%s" please change the Project Scope or Section or Subcon selected.' % (
                            (line10.variable.name), (line10.project_scope.name), (line10.section_name.name),
                            (line10.finish_good_id.id), (line10.finish_good_id.id), (line10.bom_id.id))))
                exist_section_subcon_list_subcon.append(same8)
            else:
                same8 = str(line10.project_scope.id) + ' - ' + str(line10.section_name.id) + ' - ' + str(
                    line10.variable.id) + ' - ' + str(line10.operation_two_id.id)
                if (same8 in exist_section_subcon_list_subcon):
                    raise ValidationError(
                        _('The subcon "%s" already exists in the section "%s", please change the Subcon.' % (
                            (line10.variable.name), (line10.section_name.name))))
                exist_section_subcon_list_subcon.append(same8)

    @api.constrains('subcon_estimation_ids')
    def _check_exist_subcon_2(self):
        exist_section_subcon_list_subcon = []
        for line10 in self.subcon_estimation_ids:
            if len(line10.finish_good_id) > 0 and len(line10.bom_id) > 0:
                same8 = str(line10.project_scope.id) + ' - ' + str(line10.section_name.id) + ' - ' + str(
                    line10.variable.id) + str(line10.finish_good_id.id) + ' - ' + str(line10.bom_id.id) + ' - ' + str(
                    line10.operation_two_id.id)
                if (same8 in exist_section_subcon_list_subcon):
                    raise ValidationError(
                        _('The subcon "%s" already exists in project scope "%s", section "%s", finish good "%s", bill of material "%s" please change the Project Scope or Section or Subcon selected.' % (
                            (line10.variable.name), (line10.project_scope.name), (line10.section_name.name),
                            (line10.finish_good_id.id), (line10.finish_good_id.id), (line10.bom_id.id))))
                exist_section_subcon_list_subcon.append(same8)
            else:
                same8 = str(line10.project_scope.id) + ' - ' + str(line10.section_name.id) + ' - ' + str(
                    line10.variable.id) + ' - ' + str(line10.operation_two_id.id)
                if (same8 in exist_section_subcon_list_subcon):
                    raise ValidationError(
                        _('The subcon "%s" already exists in the section "%s", please change the Subcon.' % (
                            (line10.variable.name), (line10.section_name.name))))
                exist_section_subcon_list_subcon.append(same8)

    @api.onchange('manufacture_line')
    def _check_exist_to_manufacture(self):
        for rec in self:
            if rec.is_engineering:
                exist_group_list = []
                for line in rec.manufacture_line:
                    same = str(line.project_scope_id.id) + ' - ' + str(line.section_id.id) + ' - ' + str(
                        line.finish_good_id.id) + ' - ' + str(line.bom_id.id)
                    if same in exist_group_list:
                        raise ValidationError(
                            _('The BOM "%s" already exists, please change the selected BOM.' % ((line.bom_id.name))))
                    exist_group_list.append(same)

    # @api.onchange('material_estimation_ids')
    # def _check_exist_product_id_material(self):
    # 	for rec in self:
    # 		if rec.is_engineering:
    # 			exist_group_list = []
    # 			for line in self.material_estimation_ids:
    # 				same = str(line.bom_id.id) + ' - ' + str(line.product_id.id)
    # 				if len(line.bom_id) == 0:
    # 					if same in exist_group_list:
    # 						raise ValidationError(_('The Product "%s" already exists, please change the selected Product.'%((line.product_id.name))))
    # 				else:
    # 					if same in exist_group_list:
    # 						raise ValidationError(_('The Product "%s" already exists in BOM "%s", please change the selected Product.'%((line.product_id.name),(line.bom_id.name))))
    # 				exist_group_list.append(same)

    # @api.onchange('labour_estimation_ids')
    # def _check_exist_product_id_labour(self):
    # 	for rec in self:
    # 		if rec.is_engineering:
    # 			exist_group_list = []
    # 			for line in self.labour_estimation_ids:
    # 				same = str(line.bom_id.id) + ' - ' + str(line.product_id.id)
    # 				if len(line.bom_id) == 0:
    # 					if same in exist_group_list:
    # 						raise ValidationError(_('The Product "%s" already exists, please change the selected Product.'%((line.product_id.name))))
    # 				else:
    # 					if same in exist_group_list:
    # 						raise ValidationError(_('The Product "%s" already exists in BOM "%s", please change the selected Product.'%((line.product_id.name),(line.bom_id.name))))
    # 				exist_group_list.append(same)

    # @api.onchange('overhead_estimation_ids')
    # def _check_exist_product_id_overhead(self):
    # 	for rec in self:
    # 		if rec.is_engineering:
    # 			exist_group_list = []
    # 			for line in self.overhead_estimation_ids:
    # 				same = str(line.bom_id.id) + ' - ' + str(line.product_id.id)
    # 				if len(line.bom_id) == 0:
    # 					if same in exist_group_list:
    # 						raise ValidationError(_('The Product "%s" already exists, please change the selected Product.'%((line.product_id.name))))
    # 				else:
    # 					if same in exist_group_list:
    # 						raise ValidationError(_('The Product "%s" already exists in BOM "%s", please change the selected Product.'%((line.product_id.name),(line.bom_id.name))))
    # 				exist_group_list.append(same)

    # @api.onchange('equipment_estimation_ids')
    # def _check_exist_product_id_equipment(self):
    # 	for rec in self:
    # 		if rec.is_engineering:
    # 			exist_group_list = []
    # 			for line in self.equipment_estimation_ids:
    # 				same = str(line.bom_id.id) + ' - ' + str(line.product_id.id)
    # 				if len(line.bom_id) == 0:
    # 					if same in exist_group_list:
    # 						raise ValidationError(_('The Product "%s" already exists, please change the selected Product.'%((line.product_id.name))))
    # 				else:
    # 					if same in exist_group_list:
    # 						raise ValidationError(_('The Product "%s" already exists in BOM "%s", please change the selected Product.'%((line.product_id.name),(line.bom_id.name))))
    # 				exist_group_list.append(same)

    # @api.onchange('internal_asset_ids')
    # def _check_exist_group_of_product_asset(self):
    # 	for rec in self:
    # 		if rec.is_engineering:
    # 			exist_group_list = []
    # 			for line in self.internal_asset_ids:
    # 				same = str(line.bom_id.id) + ' - ' + str(line.asset_id.id)
    # 				if len(line.bom_id) == 0:
    # 					if same in exist_group_list:
    # 						raise ValidationError(_('The Asset "%s" already exists, please change the selected Asset.'%((line.asset_id.name))))
    # 				else:
    # 					if same in exist_group_list:
    # 						raise ValidationError(_('The Asset "%s" already exists in BOM "%s", please change the selected Asset.'%((line.asset_id.name),(line.bom_id.name))))
    # 				exist_group_list.append(same)

    # @api.onchange('subcon_estimation_ids')
    # def _check_exist_subcon(self):
    # 	for rec in self:
    # 		if rec.is_engineering:
    # 			exist_subcon_list = []
    # 			for line in self.subcon_estimation_ids:
    # 				same = str(line.bom_id.id) + ' - ' + str(line.variable.id)
    # 				if len(line.bom_id) == 0:
    # 					if same in exist_subcon_list:
    # 						raise ValidationError(_('The Job Subcon "%s" already exists, please change the selected Job Subcon.'%((line.variable.name))))
    # 				else:
    # 					if same in exist_subcon_list:
    # 						raise ValidationError(_('The Job Subcon "%s" already exists in BOM "%s", please change the selected Job Subcon.'%((line.variable.name),(line.bom_id.name))))
    # 				exist_subcon_list.append(same)

    # @api.onchange('project_scope_ids')
    # def _onchange_project_scope_ids_lock(self):
    # 	res = super(JobEstimate, self)._onchange_project_scope_ids_lock()
    # 	for rec in self:
    # 		for scope in rec.project_scope_ids:
    # 			if scope.is_lock:
    # 				for manufacture in self.manufacture_line:
    # 					if manufacture.project_scope_id.id == scope.id:
    # 						manufacture.update({
    # 							'is_lock': True,
    # 						})
    # 			else:
    # 				for manufacture in self.manufacture_line:
    # 					if manufacture.project_scope_id.id == scope.id:
    # 						manufacture.update({
    # 							'is_lock': False,
    # 						})
    # 	return res
    #
    # @api.onchange('section_ids')
    # def _onchange_section_ids_lock(self):
    # 	res = super(JobEstimate, self)._onchange_section_ids_lock()
    # 	for section in self.section_ids:
    # 		if section.is_lock == True:
    # 			for manufacture in self.manufacture_line:
    # 				if manufacture.project_scope_id.id == section.project_scope.id \
    # 						and manufacture.section_id.id == section.section_name.id:
    # 					manufacture.update({
    # 						'is_lock': True,
    # 					})
    # 		else:
    # 			for manufacture in self.manufacture_line:
    # 				if manufacture.project_scope_id.id == section.project_scope.id \
    # 						and manufacture.section_id.id == section.section_name.id:
    # 					manufacture.update({
    # 						'is_lock': False,
    # 					})
    # 	return res
    #
    # @api.onchange('manufacture_line')
    # def _onchange_manufacture_line_lock(self):
    # 	for rec in self:
    # 		if rec.is_engineering:
    # 			for manufacture in rec.manufacture_line:
    # 				if manufacture.is_lock:
    # 					for material in self.material_estimation_ids:
    # 						if material.project_scope.id == manufacture.project_scope_id.id \
    # 								and material.section_name.id == manufacture.section_id.id \
    # 								and material.finish_good_id.id == manufacture.finish_good_id.id:
    # 							material.update({
    # 								'is_lock': True,
    # 							})
    # 					for labour in self.labour_estimation_ids:
    # 						if labour.project_scope.id == manufacture.project_scope_id.id \
    # 								and labour.section_name.id == manufacture.section_id.id \
    # 								and labour.finish_good_id.id == manufacture.finish_good_id.id:
    # 							labour.update({
    # 								'is_lock': True,
    # 							})
    # 					for overhead in self.overhead_estimation_ids:
    # 						if overhead.project_scope.id == manufacture.project_scope_id.id \
    # 								and overhead.section_name.id == manufacture.section_id.id \
    # 								and overhead.finish_good_id.id == manufacture.finish_good_id.id:
    # 							overhead.update({
    # 								'is_lock': True,
    # 							})
    # 					for asset in self.internal_asset_ids:
    # 						if asset.project_scope.id == manufacture.project_scope_id.id \
    # 								and asset.section_name.id == manufacture.section_id.id \
    # 								and asset.finish_good_id.id == manufacture.finish_good_id.id:
    # 							asset.update({
    # 								'is_lock': True,
    # 							})
    # 					for equipment in self.equipment_estimation_ids:
    # 						if equipment.project_scope.id == manufacture.project_scope_id.id \
    # 								and equipment.section_name.id == manufacture.section_id.id \
    # 								and equipment.finish_good_id.id == manufacture.finish_good_id.id:
    # 							equipment.update({
    # 								'is_lock': True,
    # 							})
    # 					for subcon in self.subcon_estimation_ids:
    # 						if subcon.project_scope.id == manufacture.project_scope_id.id \
    # 								and subcon.section_name.id == manufacture.section_id.id \
    # 								and subcon.finish_good_id.id == manufacture.finish_good_id.id:
    # 							subcon.update({
    # 								'is_lock': True,
    # 							})
    # 				else:
    # 					# for scope in self.project_scope_ids:
    # 					# 	if scope.project_scope.id == manufacture.project_scope_id.id and scope.is_lock == True:
    # 					# 		raise ValidationError(
    # 					# 			_(f"Project scope '{scope.project_scope.name}' in the project scope tab is locked. You need to unlock it first."))
    # 					# for section in self.section_ids:
    # 					# 	if section.section_name.id == manufacture.section_id.id and section.is_lock == True:
    # 					# 		raise ValidationError(
    # 					# 			_(f"Section '{section.section_name.name}' in the section tab is locked. You need to unlock it first."))
    # 					# if manufacture.variable_ref:
    # 					# 	for variable in self.variable_ids:
    # 					# 		if variable.variable_name == manufacture.variable_ref and variable.is_lock == True:
    # 					# 			raise ValidationError(
    # 					# 				_(f"Variable '{variable.variable_name}' in the variable tab is locked. You need to unlock it first."))
    # 					for material in self.material_estimation_ids:
    # 						if material.project_scope.id == manufacture.project_scope_id.id \
    # 								and material.section_name.id == manufacture.section_id.id \
    # 								and material.finish_good_id.id == manufacture.finish_good_id.id:
    # 							material.update({
    # 								'is_lock': False,
    # 							})
    # 					for labour in self.labour_estimation_ids:
    # 						if labour.project_scope.id == manufacture.project_scope_id.id \
    # 								and labour.section_name.id == manufacture.section_id.id \
    # 								and labour.finish_good_id.id == manufacture.finish_good_id.id:
    # 							labour.update({
    # 								'is_lock': False,
    # 							})
    # 					for overhead in self.overhead_estimation_ids:
    # 						if overhead.project_scope.id == manufacture.project_scope_id.id \
    # 								and overhead.section_name.id == manufacture.section_id.id \
    # 								and overhead.finish_good_id.id == manufacture.finish_good_id.id:
    # 							overhead.update({
    # 								'is_lock': False,
    # 							})
    # 					for asset in self.internal_asset_ids:
    # 						if asset.project_scope.id == manufacture.project_scope_id.id \
    # 								and asset.section_name.id == manufacture.section_id.id \
    # 								and asset.finish_good_id.id == manufacture.finish_good_id.id:
    # 							asset.update({
    # 								'is_lock': False,
    # 							})
    # 					for equipment in self.equipment_estimation_ids:
    # 						if equipment.project_scope.id == manufacture.project_scope_id.id \
    # 								and equipment.section_name.id == manufacture.section_id.id \
    # 								and equipment.finish_good_id.id == manufacture.finish_good_id.id:
    # 							equipment.update({
    # 								'is_lock': False,
    # 							})
    # 					for subcon in self.subcon_estimation_ids:
    # 						if subcon.project_scope.id == manufacture.project_scope_id.id \
    # 								and subcon.section_name.id == manufacture.section_id.id \
    # 								and subcon.finish_good_id.id == manufacture.finish_good_id.id:
    # 							subcon.update({
    # 								'is_lock': False,
    # 							})

    # @api.onchange('material_estimation_ids')
    # def _onchange_material_estimation_ids_lock(self):
    # 	res = super(JobEstimate, self)._onchange_material_estimation_ids_lock()
    # 	for rec in self:
    # 		for material in rec.material_estimation_ids:
    # 			if not material.is_lock:
    # 				for manufacture in rec.manufacture_line:
    # 					if material.finish_good_id.id == manufacture.finish_good_id.id and manufacture.is_lock == True:
    # 						raise ValidationError(
    # 							_(f"Finish good '{material.finish_good_id.name}' in the manufacture tab is locked. You need to unlock it first."))
    # 	return res
    #
    # @api.onchange('labour_estimation_ids')
    # def _onchange_labour_estimation_ids_lock(self):
    # 	res = super(JobEstimate, self)._onchange_labour_estimation_ids_lock()
    # 	for rec in self:
    # 		for labour in rec.labour_estimation_ids:
    # 			if not labour.is_lock:
    # 				for manufacture in rec.manufacture_line:
    # 					if labour.finish_good_id.id == manufacture.finish_good_id.id and manufacture.is_lock == True:
    # 						raise ValidationError(
    # 							_(f"Finish good '{labour.finish_good_id.name}' in the manufacture tab is locked. You need to unlock it first."))
    # 	return res
    #
    # @api.onchange('overhead_estimation_ids')
    # def _onchange_overhead_estimation_ids_lock(self):
    # 	res = super(JobEstimate, self)._onchange_overhead_estimation_ids_lock()
    # 	for rec in self:
    # 		for overhead in rec.overhead_estimation_ids:
    # 			if not overhead.is_lock:
    # 				for manufacture in rec.manufacture_line:
    # 					if overhead.finish_good_id.id == manufacture.finish_good_id.id and manufacture.is_lock == True:
    # 						raise ValidationError(
    # 							_(f"Finish good '{overhead.finish_good_id.name}' in the manufacture tab is locked. You need to unlock it first."))
    # 	return res
    #
    # @api.onchange('internal_asset_ids')
    # def _onchange_internal_asset_ids_lock(self):
    # 	res = super(JobEstimate, self)._onchange_internal_asset_ids_lock()
    # 	for rec in self:
    # 		for internal in rec.internal_asset_ids:
    # 			if not internal.is_lock:
    # 				for manufacture in rec.manufacture_line:
    # 					if internal.finish_good_idid.id == manufacture.finish_good_id.id and manufacture.is_lock == True:
    # 						raise ValidationError(
    # 							_(f"Finish good '{internal.finish_good_id.name}' in the manufacture tab is locked. You need to unlock it first."))
    # 	return res
    #
    # @api.onchange('equipment_estimation_ids')
    # def _onchange_equipment_estimation_ids_lock(self):
    # 	res = super(JobEstimate, self)._onchange_equipment_estimation_ids_lock()
    # 	for rec in self:
    # 		for equipment in rec.equipment_estimation_ids:
    # 			if not equipment.is_lock:
    # 				for manufacture in rec.manufacture_line:
    # 					if equipment.finish_good_id.id == manufacture.finish_good_id.id and manufacture.is_lock == True:
    # 						raise ValidationError(
    # 							_(f"Finish good '{equipment.finish_good_id.name}' in the manufacture tab is locked. You need to unlock it first."))
    # 	return res
    #
    # @api.onchange('subcon_estimation_ids')
    # def _onchange_subcon_estimation_ids_lock(self):
    # 	res = super(JobEstimate, self)._onchange_subcon_estimation_ids_lock()
    # 	for rec in self:
    # 		for subcon in rec.subcon_estimation_ids:
    # 			if not subcon.is_lock:
    # 				for manufacture in rec.manufacture_line:
    # 					if subcon.finish_good_id.id == manufacture.finish_good_id.id:
    # 						raise ValidationError(
    # 							_(f"Finish good '{subcon.finish_good_id.name}' in the manufacture tab is locked. You need to unlock it first."))
    # 	return res

    @api.onchange('variable_ids')
    def update_material(self):
        manufacture = []
        material = []
        labour = []
        subcon = []
        overhead = []
        equip = []
        asset = []
        variable_list = []

        for rec in self.variable_ids:
            scope = rec.project_scope
            section = rec.section_name
            variable = rec.variable_name
            var_quantity = rec.variable_quantity

            if scope and section and variable:
                if var_quantity > 0:
                    if rec.onchange_pass == False:
                        rec.write({'onchange_pass': True})

                        # for to manufacture
                        if variable.manufacture_line_variable:
                            for manuf in self.manufacture_line:
                                if manuf.project_scope_id != False and manuf.section_id != False and len(
                                        manuf.variable_ref) != 0:
                                    if manuf.project_scope_id == scope and manuf.section_id == section and manuf.variable_ref == variable:
                                        self.manufacture_line = [(2, manuf.id)]
                            for man in variable.manufacture_line_variable:
                                manx = (0, 0, {
                                    'is_lock': rec.is_lock,
                                    'is_new': False,
                                    'project_scope_id': scope.id,
                                    'section_id': section.id,
                                    'variable_ref': variable.id,
                                    'finish_good_id': man.finish_good_id.id,
                                    'bom_id': man.bom_id.id,
                                    'quantity': var_quantity * man.quantity,
                                    'uom': man.uom_id,
                                    'subtotal': man.subtotal * (var_quantity * man.quantity),
                                })
                                manufacture.append(manx)
                            self.manufacture_line = manufacture

                        # for material
                        if variable.material_variable_ids:
                            for mater in self.material_estimation_ids:
                                if mater.project_scope != False and mater.section_name != False and len(
                                        mater.variable_ref) != 0:
                                    if mater.project_scope == scope and mater.section_name == section and mater.variable_ref == variable:
                                        self.material_estimation_ids = [(2, mater.id)]
                            for mat in variable.material_variable_ids:
                                matx = (0, 0, {
                                    'is_lock': rec.is_lock,
                                    'is_new': False,
                                    'product_id': mat.product_id.id,
                                    'quantity': var_quantity * mat.quantity,
                                    'subtotal': mat.unit_price * (var_quantity * mat.quantity),
                                    'unit_price': mat.unit_price,
                                    'uom_id': mat.uom_id.id,
                                    'project_scope': scope.id,
                                    'section_name': section.id,
                                    'variable_ref': variable.id,
                                    'finish_good_id': mat.finish_good_id.id or False,
                                    'bom_id': mat.bom_id.id or False,
                                    'description': mat.description,
                                    'group_of_product': mat.group_of_product.id,
                                    'operation_two_id': mat.operation_two_id.id,
                                })
                                material.append(matx)
                            self.material_estimation_ids = material

                        # for labor
                        if variable.labour_variable_ids:
                            for labo in self.labour_estimation_ids:
                                if labo.project_scope != False and labo.section_name != False and len(
                                        labo.variable_ref) != 0:
                                    if labo.project_scope == scope and labo.section_name == section and labo.variable_ref == variable:
                                        self.labour_estimation_ids = [(2, labo.id)]
                            for lab in variable.labour_variable_ids:
                                labx = (0, 0, {
                                    'is_lock': rec.is_lock,
                                    'is_new': False,
                                    'product_id': lab.product_id.id,
                                    'quantity': lab.contractors * (var_quantity * lab.time),
                                    'subtotal': lab.unit_price * (lab.contractors * (var_quantity * lab.time)),
                                    'unit_price': lab.unit_price,
                                    'uom_id': lab.uom_id.id,
                                    'project_scope': scope.id,
                                    'section_name': section.id,
                                    'variable_ref': variable.id,
                                    'finish_good_id': lab.finish_good_id.id or False,
                                    'bom_id': lab.bom_id.id or False,
                                    'description': lab.description,
                                    'group_of_product': lab.group_of_product.id,
                                    'contractors': lab.contractors,
                                    'time': var_quantity * lab.time,
                                    'operation_two_id': lab.operation_two_id.id,
                                })
                                labour.append(labx)
                            self.labour_estimation_ids = labour

                        # for subcon
                        if variable.subcon_variable_ids:
                            for subc in self.subcon_estimation_ids:
                                if subc.project_scope != False and subc.section_name != False and len(
                                        subc.variable_ref) != 0:
                                    if subc.project_scope == scope and subc.section_name == section and subc.variable_ref == variable:
                                        self.subcon_estimation_ids = [(2, subc.id)]
                            for sub in variable.subcon_variable_ids:
                                subx = (0, 0, {
                                    'is_lock': rec.is_lock,
                                    'is_new': False,
                                    'variable': sub.variable.id,
                                    'quantity': var_quantity * sub.quantity,
                                    'subtotal': sub.unit_price * (var_quantity * sub.quantity),
                                    'unit_price': sub.unit_price,
                                    'uom_id': sub.uom_id.id,
                                    'project_scope': scope.id,
                                    'section_name': section.id,
                                    'variable_ref': variable.id,
                                    'finish_good_id': sub.finish_good_id.id or False,
                                    'bom_id': sub.bom_id.id or False,
                                    'description': sub.description,
                                    'operation_two_id': sub.operation_two_id.id,
                                })
                                subcon.append(subx)
                            self.subcon_estimation_ids = subcon

                        # for over
                        if variable.overhead_variable_ids:
                            for ov in self.overhead_estimation_ids:
                                if ov.project_scope != False and ov.section_name != False and len(ov.variable_ref) != 0:
                                    if ov.project_scope == scope and ov.section_name == section and ov.variable_ref == variable:
                                        self.overhead_estimation_ids = [(2, ov.id)]
                            for over in variable.overhead_variable_ids:
                                overx = (0, 0, {
                                    'is_lock': rec.is_lock,
                                    'is_new': False,
                                    'overhead_catagory': over.overhead_catagory,
                                    'product_id': over.product_id.id,
                                    'quantity': var_quantity * over.quantity,
                                    'subtotal': over.unit_price * (var_quantity * over.quantity),
                                    'unit_price': over.unit_price,
                                    'uom_id': over.uom_id.id,
                                    'project_scope': scope.id,
                                    'section_name': section.id,
                                    'variable_ref': variable.id,
                                    'finish_good_id': over.finish_good_id.id or False,
                                    'bom_id': over.bom_id.id or False,
                                    'description': over.description,
                                    'group_of_product': over.group_of_product.id,
                                    'operation_two_id': over.operation_two_id.id,
                                })
                                overhead.append(overx)
                            self.overhead_estimation_ids = overhead

                        # for equip
                        if variable.equipment_variable_ids:
                            for eq in self.equipment_estimation_ids:
                                if eq.project_scope != False and eq.section_name != False and len(eq.variable_ref) != 0:
                                    if eq.project_scope == scope and eq.section_name == section and eq.variable_ref == variable:
                                        self.equipment_estimation_ids = [(2, eq.id)]
                            for eqp in variable.equipment_variable_ids:
                                eqpx = (0, 0, {
                                    'is_lock': rec.is_lock,
                                    'is_new': False,
                                    'product_id': eqp.product_id.id,
                                    'quantity': var_quantity * eqp.quantity,
                                    'subtotal': eqp.unit_price * (var_quantity * eqp.quantity),
                                    'unit_price': eqp.unit_price,
                                    'uom_id': eqp.uom_id.id,
                                    'project_scope': scope.id,
                                    'section_name': section.id,
                                    'variable_ref': variable.id,
                                    'finish_good_id': eqp.finish_good_id.id or False,
                                    'bom_id': eqp.bom_id.id or False,
                                    'description': eqp.description,
                                    'group_of_product': eqp.group_of_product.id,
                                    'operation_two_id': eqp.operation_two_id.id,
                                })
                                equip.append(eqpx)
                            self.equipment_estimation_ids = equip

                        # for asset
                        if variable.asset_variable_ids:
                            for asse in self.internal_asset_ids:
                                if asse.project_scope != False and asse.section_name != False and len(
                                        asse.variable_ref) != 0:
                                    if asse.project_scope == scope and asse.section_name == section and asse.variable_ref == variable:
                                        self.internal_asset_ids = [(2, asse.id)]
                            for ass in variable.asset_variable_ids:
                                assx = (0, 0, {
                                    'is_lock': rec.is_lock,
                                    'is_new': False,
                                    'asset_category_id': ass.asset_category_id.id,
                                    'asset_id': ass.asset_id.id,
                                    'quantity': var_quantity * ass.quantity,
                                    'subtotal': ass.unit_price * (var_quantity * ass.quantity),
                                    'unit_price': ass.unit_price,
                                    'uom_id': ass.uom_id.id,
                                    'project_scope': scope.id,
                                    'section_name': section.id,
                                    'variable_ref': variable.id,
                                    'finish_good_id': ass.finish_good_id.id or False,
                                    'bom_id': ass.bom_id.id or False,
                                    'description': ass.description,
                                    'operation_two_id': ass.operation_two_id.id,
                                })
                                asset.append(assx)
                            self.internal_asset_ids = asset
                    variable_list.append((scope.name, section.name, variable.name))

        for man in self.manufacture_line:
            if man.project_scope_id != False and man.section_id != False and len(man.variable_ref) != 0:
                if (man.project_scope_id.name, man.section_id.name, man.variable_ref.name) not in variable_list:
                    self.manufacture_line = [(2, man.id)]
        for mat in self.material_estimation_ids:
            if mat.project_scope != False and mat.section_name != False and len(mat.variable_ref) != 0:
                if (mat.project_scope.name, mat.section_name.name, mat.variable_ref.name) not in variable_list:
                    self.material_estimation_ids = [(2, mat.id)]
        for lab in self.labour_estimation_ids:
            if lab.project_scope != False and lab.section_name != False and len(lab.variable_ref) != 0:
                if (lab.project_scope.name, lab.section_name.name, lab.variable_ref.name) not in variable_list:
                    self.labour_estimation_ids = [(2, lab.id)]
        for ov in self.overhead_estimation_ids:
            if ov.project_scope != False and ov.section_name != False and len(ov.variable_ref) != 0:
                if (ov.project_scope.name, ov.section_name.name, ov.variable_ref.name) not in variable_list:
                    self.overhead_estimation_ids = [(2, ov.id)]
        for asset in self.internal_asset_ids:
            if asset.project_scope != False and asset.section_name != False and len(asset.variable_ref) != 0:
                if (asset.project_scope.name, asset.section_name.name, asset.variable_ref.name) not in variable_list:
                    self.internal_asset_ids = [(2, asset.id)]
        for eq in self.equipment_estimation_ids:
            if eq.project_scope != False and eq.section_name != False and len(eq.variable_ref) != 0:
                if (eq.project_scope.name, eq.section_name.name, eq.variable_ref.name) not in variable_list:
                    self.equipment_estimation_ids = [(2, eq.id)]
        for sub in self.subcon_estimation_ids:
            if sub.project_scope != False and sub.section_name != False and len(sub.variable_ref) != 0:
                if (sub.project_scope.name, sub.section_name.name, sub.variable_ref.name) not in variable_list:
                    self.subcon_estimation_ids = [(2, sub.id)]

    @api.onchange('manufacture_line')
    def update_manuf_line(self, final_finih_good=False, parent_finish_godd=False):
        material = []
        labour = []
        overhead = []
        equip = []
        asset = []
        subcon = []
        fg_list = []
        existing_finish_good_list = self.manufacture_line.mapped('finish_good_id').ids

        for rec in self.manufacture_line:
            scope = rec.project_scope_id
            section = rec.section_id
            variable = rec.variable_ref
            # final_finish_good = rec.final_finish_good_id
            finish_good = rec.finish_good_id
            bom = rec.bom_id
            quantity = rec.quantity

            if scope and section and not variable and finish_good and bom:
                if quantity > 0:
                    if rec.onchange_pass == False:
                        rec.write({'onchange_pass': True})

                        if bom.can_be_subcontracted == True:
                            if bom.bom_line_ids or bom.labour_ids or bom.overhead_ids or bom.asset_ids or bom.equipment_ids:
                                for sub in self.subcon_estimation_ids:
                                    if sub.project_scope != False and sub.section_name != False and len(
                                            sub.finish_good_id) != 0 and len(sub.bom_id) != 0:
                                        if sub.project_scope == scope and sub.section_name == section and sub.finish_good_id == finish_good and sub.bom_id == bom:
                                            self.subcon_estimation_ids = [(2, sub.id)]
                                for sub in bom:
                                    subx = (0, 0, {
                                        'is_lock': rec.is_lock,
                                        'is_new': False,
                                        'project_scope': scope.id,
                                        'section_name': section.id,
                                        'variable_ref': variable.id or False,
                                        'parent_finish_good_id': parent_finish_godd,
                                        'final_finish_good_id': final_finih_good,
                                        'finish_good_id': finish_good.id,
                                        'bom_id': sub.id,
                                        'variable': sub.variable_ref.id,
                                        'description': finish_good.display_name,
                                        'quantity': quantity * sub.product_qty,
                                        'uom_id': sub.product_uom_id.id,
                                        'unit_price': sub.forecast_cost,
                                        'subtotal': sub.forecast_cost * (quantity * sub.product_qty),
                                        'operation_two_id': sub.operation_two_id.id,
                                    })
                                    subcon.append(subx)
                                self.subcon_estimation_ids = subcon

                        else:
                            # for material
                            if bom.bom_line_ids:
                                for mater in self.material_estimation_ids:
                                    if mater.project_scope != False and mater.section_name != False and len(
                                            mater.finish_good_id) != 0 and len(mater.bom_id) != 0:
                                        if mater.project_scope == scope and mater.section_name == section and mater.finish_good_id == finish_good and mater.bom_id == bom:
                                            self.material_estimation_ids = [(2, mater.id)]
                                for bom_mat in bom.bom_line_ids:
                                    matx = (0, 0, {
                                        'is_lock': rec.is_lock,
                                        'is_new': False,
                                        'project_scope': scope.id,
                                        'section_name': section.id,
                                        'variable_ref': variable.id or False,
                                        'parent_finish_good_id': parent_finish_godd,
                                        'final_finish_good_id': final_finih_good,
                                        'finish_good_id': finish_good.id,
                                        'bom_id': bom.id,
                                        'group_of_product': bom_mat.group_of_product.id,
                                        'product_id': bom_mat.product_id.id,
                                        'description': bom_mat.product_id.display_name,
                                        'quantity': quantity * bom_mat.product_qty,
                                        'uom_id': bom_mat.product_uom_id.id,
                                        'unit_price': bom_mat.cost,
                                        'subtotal': bom_mat.cost * (quantity * bom_mat.product_qty),
                                        'operation_two_id': bom_mat.operation_two_id.id,
                                    })
                                    material.append(matx)
                                self.material_estimation_ids = material

                            # for labor
                            if bom.labour_ids:
                                for labo in self.labour_estimation_ids:
                                    if labo.project_scope != False and labo.section_name != False and len(
                                            labo.finish_good_id) != 0 and len(labo.bom_id) != 0:
                                        if labo.project_scope == scope and labo.section_name == section and labo.finish_good_id == finish_good and labo.bom_id == bom:
                                            self.labour_estimation_ids = [(2, labo.id)]
                                for bom_lab in bom.labour_ids:
                                    labx = (0, 0, {
                                        'is_lock': rec.is_lock,
                                        'is_new': False,
                                        'project_scope': scope.id,
                                        'section_name': section.id,
                                        'variable_ref': variable.id or False,
                                        'parent_finish_good_id': parent_finish_godd,
                                        'final_finish_good_id': final_finih_good,
                                        'finish_good_id': finish_good.id,
                                        'bom_id': bom.id,
                                        'group_of_product': bom_lab.group_of_product.id,
                                        'product_id': bom_lab.product_id.id,
                                        'description': bom_lab.product_id.display_name,
                                        'contractors': bom_lab.contractors,
                                        'time': quantity * bom_lab.time,
                                        'uom_id': bom_lab.uom_id.id,
                                        'unit_price': bom_lab.cost,
                                        'quantity': bom_lab.contractors * (quantity * bom_lab.time),
                                        'subtotal': bom_lab.cost * (bom_lab.contractors * (quantity * bom_lab.time)),
                                        'operation_two_id': bom_lab.operation_two_id.id,
                                    })
                                    labour.append(labx)
                                self.labour_estimation_ids = labour

                            # for over
                            if bom.overhead_ids:
                                for ov in self.overhead_estimation_ids:
                                    if ov.project_scope != False and ov.section_name != False and len(
                                            ov.finish_good_id) != 0 and len(ov.bom_id) != 0:
                                        if ov.project_scope == scope and ov.section_name == section and ov.finish_good_id == finish_good and ov.bom_id == bom:
                                            self.overhead_estimation_ids = [(2, ov.id)]
                                for bom_over in bom.overhead_ids:
                                    overx = (0, 0, {
                                        'is_lock': rec.is_lock,
                                        'is_new': False,
                                        'project_scope': scope.id,
                                        'section_name': section.id,
                                        'variable_ref': variable.id or False,
                                        'parent_finish_good_id': parent_finish_godd,
                                        'final_finish_good_id': final_finih_good,
                                        'finish_good_id': finish_good.id,
                                        'bom_id': bom.id,
                                        'overhead_catagory': bom_over.overhead_catagory,
                                        'group_of_product': bom_over.group_of_product.id,
                                        'product_id': bom_over.product_id.id,
                                        'description': bom_over.product_id.display_name,
                                        'quantity': quantity * bom_over.quantity,
                                        'uom_id': bom_over.uom_id.id,
                                        'unit_price': bom_over.cost,
                                        'subtotal': bom_over.cost * (quantity * bom_over.quantity),
                                        'operation_two_id': bom_over.operation_two_id.id,
                                    })
                                    overhead.append(overx)
                                self.overhead_estimation_ids = overhead
                            # for equip
                            if bom.equipment_ids:
                                for eq in self.equipment_estimation_ids:
                                    if eq.project_scope != False and eq.section_name != False and len(
                                            eq.finish_good_id) != 0 and len(eq.bom_id) != 0:
                                        if eq.project_scope == scope and eq.section_name == section and eq.finish_good_id == finish_good and eq.bom_id == bom:
                                            self.equipment_estimation_ids = [(2, eq.id)]
                                for bom_eqp in bom.equipment_ids:
                                    eqpx = (0, 0, {
                                        'is_lock': rec.is_lock,
                                        'is_new': False,
                                        'project_scope': scope.id,
                                        'section_name': section.id,
                                        'variable_ref': variable.id or False,
                                        'parent_finish_good_id': parent_finish_godd,
                                        'final_finish_good_id': final_finih_good,
                                        'finish_good_id': finish_good.id,
                                        'bom_id': bom.id,
                                        'group_of_product': bom_eqp.group_of_product.id,
                                        'product_id': bom_eqp.product_id.id,
                                        'description': bom_eqp.product_id.display_name,
                                        'quantity': quantity * bom_eqp.quantity,
                                        'uom_id': bom_eqp.uom_id.id,
                                        'unit_price': bom_eqp.cost,
                                        'subtotal': bom_eqp.cost * (quantity * bom_eqp.quantity),
                                        'operation_two_id': bom_eqp.operation_two_id.id,
                                    })
                                    equip.append(eqpx)
                                self.equipment_estimation_ids = equip

                            # for asset
                            if bom.asset_ids:
                                for asse in self.internal_asset_ids:
                                    if asse.project_scope != False and asse.section_name != False and len(
                                            asse.finish_good_id) != 0 and len(asse.bom_id) != 0:
                                        if asse.project_scope == scope and asse.section_name == section and asse.finish_good_id == finish_good and asse.bom_id == bom:
                                            self.internal_asset_ids = [(2, asse.id)]
                                for bom_ass in bom.asset_ids:
                                    assx = (0, 0, {
                                        'is_lock': rec.is_lock,
                                        'is_new': False,
                                        'project_scope': scope.id,
                                        'section_name': section.id,
                                        'variable_ref': variable.id or False,
                                        'parent_finish_good_id': parent_finish_godd,
                                        'final_finish_good_id': final_finih_good,
                                        'finish_good_id': finish_good.id,
                                        'bom_id': bom.id,
                                        'asset_category_id': bom_ass.asset_category_id.id,
                                        'asset_id': bom_ass.asset_id.id,
                                        'description': bom_ass.asset_id.display_name,
                                        'quantity': quantity * bom_ass.quantity,
                                        'uom_id': bom_ass.uom_id.id,
                                        'unit_price': bom_ass.cost,
                                        'subtotal': bom_ass.cost * (quantity * bom_ass.quantity),
                                        'operation_two_id': bom_ass.operation_two_id.id,
                                    })
                                    asset.append(assx)
                                self.internal_asset_ids = asset

                    fg_list.append((scope.name, section.name, finish_good.name, bom.name))

        if len(existing_finish_good_list) > 0:
            for material in self.material_estimation_ids:
                if material.product_id.id in existing_finish_good_list:
                    self.material_estimation_ids = [(2, material.id, 0)]

        if not self.manufacture_line.variable_ref:

            for mater in self.material_estimation_ids:
                if mater.project_scope != False and mater.section_name != False and len(
                        mater.finish_good_id) != 0 and len(mater.bom_id) != 0:
                    if (mater.project_scope.name, mater.section_name.name, mater.finish_good_id.name,
                        mater.bom_id.name) not in fg_list:
                        self.material_estimation_ids = [(2, mater.id)]
            for labo in self.labour_estimation_ids:
                if labo.project_scope != False and labo.section_name != False and len(labo.finish_good_id) != 0 and len(
                        labo.bom_id) != 0:
                    if (labo.project_scope.name, labo.section_name.name, labo.finish_good_id.name,
                        labo.bom_id.name) not in fg_list:
                        self.labour_estimation_ids = [(2, labo.id)]
            for ov in self.overhead_estimation_ids:
                if ov.project_scope != False and ov.section_name != False and len(ov.finish_good_id) != 0 and len(
                        ov.bom_id) != 0:
                    if (
                            ov.project_scope.name, ov.section_name.name, ov.finish_good_id.name,
                            ov.bom_id.name) not in fg_list:
                        self.overhead_estimation_ids = [(2, ov.id)]
            for asse in self.internal_asset_ids:
                if asse.project_scope != False and asse.section_name != False and len(asse.finish_good_id) != 0 and len(
                        asse.bom_id) != 0:
                    if (asse.project_scope.name, asse.section_name.name, asse.finish_good_id.name,
                        asse.bom_id.name) not in fg_list:
                        self.internal_asset_ids = [(2, asse.id)]
            for eq in self.equipment_estimation_ids:
                if eq.project_scope != False and eq.section_name != False and len(eq.finish_good_id) != 0 and len(
                        eq.bom_id) != 0:
                    if (
                            eq.project_scope.name, eq.section_name.name, eq.finish_good_id.name,
                            eq.bom_id.name) not in fg_list:
                        self.equipment_estimation_ids = [(2, eq.id)]
            for sub in self.subcon_estimation_ids:
                if sub.project_scope != False and sub.section_name != False and len(sub.finish_good_id) != 0 and len(
                        sub.bom_id) != 0:
                    if (sub.project_scope.name, sub.section_name.name, sub.finish_good_id.name,
                        sub.bom_id.name) not in fg_list:
                        self.subcon_estimation_ids = [(2, sub.id)]

    def _compute_hide_cascade(self):
        for res in self:
            if res.manufacture_line:
                for line in res.manufacture_line:
                    if line.cascaded == False:
                        res.hide_cascade = False
                        return
                res.hide_cascade = True
                return
            else:
                res.hide_cascade = True
                return

    def _compute_hide_undo(self):
        for res in self:
            if res.manufacture_line:
                for line in res.manufacture_line:
                    if line.cascaded:
                        res.hide_undo = False
                        return
                res.hide_undo = True
                return
            else:
                res.hide_undo = True
                return

    def cascade_bom_button(self):
        def _get_manuf_line_cascade(line):
            return {
                'to_manuf_line_id': line.id,
                'project_scope': line.project_scope_id.id,
                'section_name': line.section_id.id,
                'final_finish_good_id': line.final_finish_good_id.id or False,
                'finish_good_id': line.finish_good_id.id,
                'finish_good_id_template': line.finish_good_id_template.id,
                'bom_id': line.bom_id.id,
                'product_qty': line.quantity,
                'is_child': line.is_child
            }

        manuf_line = []
        bom_list = self.manufacture_line.mapped('bom_id').ids
        for manufacture in self.manufacture_line:
            for line in manufacture.bom_id.bom_line_ids:
                bom = self.env['mrp.bom']._bom_find(product=line.product_id, company_id=self.company_id.id,
                                                    bom_type='normal')
                if len(bom) > 0 and not manufacture.cascaded:
                    manuf_line.append((0, 0, _get_manuf_line_cascade(manufacture)))
                elif len(bom) > 0 and manufacture.cascaded:
                    if bom.id not in bom_list:
                        manuf_line.append((0, 0, _get_manuf_line_cascade(manufacture)))

        if len(manuf_line) > 0:
            context = {
                'default_company_id': self.company_id.id,
                'default_project_id': self.project_id.id,
                'default_job_estimate_id': self.id,
                'default_hide_cost_sheet': True,
                'default_undo_cascade': False,
                'default_job_cascade_line_ids': manuf_line,
            }
            return {
                'type': 'ir.actions.act_window',
                'name': 'Create Quotation',
                'res_model': 'job.cascade.wizard',
                'context': context,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
            }
        else:
            context = {
                'default_company_id': self.company_id.id,
                'default_project_id': self.project_id.id,
                'default_job_estimate_id': self.id,
                'default_hide_cost_sheet': True,
                'default_undo_cascade': False,
                'default_job_cascade_line_ids': False,
            }

            return {
                'type': 'ir.actions.act_window',
                'name': 'Create Quotation',
                'res_model': 'job.cascade.wizard',
                'context': context,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
            }

    def undo_cascade_bom(self):
        def _get_manuf_line_undo(line):
            return {
                'to_manuf_line_id': line.id,
                'project_scope': line.project_scope_id.id,
                'section_name': line.section_id.id,
                'finish_good_id': line.finish_good_id.id,
                'finish_good_id_template': line.finish_good_id_template.id,
                'bom_id': line.bom_id.id,
                'product_qty': line.quantity,
            }

        manuf_line = []
        for line in self.manufacture_line.filtered(lambda l: l.cascaded == True and not l.parent_manuf_line):
            manuf_line.append((0, 0, _get_manuf_line_undo(line)))
        if len(manuf_line) > 0:
            context = {
                'default_company_id': self.company_id.id,
                'default_project_id': self.project_id.id,
                'default_job_estimate_id': self.id,
                'default_hide_cost_sheet': True,
                'default_undo_cascade': True,
                'default_job_cascade_line_ids': manuf_line,
            }
            return {
                'type': 'ir.actions.act_window',
                'name': 'Undo Cascade to Child BOM',
                'view_mode': 'form',
                'res_model': 'job.cascade.wizard',
                'target': 'new',
                'context': context
            }
        else:
            raise ValidationError("The to manufacture table is empty, please input at least one line!")


class ProductInherited(models.Model):
    _inherit = 'product.product'

    # has the exact same value as bom_count
    # somehow bom_count cannot be used as domain of finish_good_id, this is a workaround
    finish_goods_bom_count = fields.Integer(compute='_compute_finish_goods_bom_count', string='# of BOM',store=True,
                                            default=0)

    @api.depends('bom_ids')
    def _compute_finish_goods_bom_count(self):
        for product in self:
            product.finish_goods_bom_count = product.bom_count


class SectionEstimate(models.Model):
    _inherit = 'section.estimate'

    @api.onchange('section_name')
    def _onchange_section_name_handling(self):
        res = super(SectionEstimate, self)._onchange_section_name_handling()
        if self.section_id.is_engineering:
            if self._origin.section_name._origin.id:
                if self._origin.section_name._origin.id != self.section_name.id:
                    section_values = []

                    for section in self.section_id.section_ids:
                        section_values.append(section.section_name.id)
                    for manufacture in self.section_id.manufacture_line:
                        if manufacture.section_id.id not in section_values:
                            self.section_id.manufacture_line = [(3, manufacture.id, 0)]
            else:
                section_values = []

                for section in self.section_id.section_ids:
                    section_values.append(section.section_name.id)
                for manufacture in self.section_id.manufacture_line:
                    if manufacture.section_id.id not in section_values:
                        self.section_id.manufacture_line = [(3, manufacture.id, 0)]
        return res


class ToManufactureLine(models.Model):
    _name = 'to.manufacture.line'
    _description = 'To Manufacture Line'
    _rec_name = 'finish_good_id'
    _order = 'sequence'

    job_estimate_id = fields.Many2one('job.estimate', string="To Manufacture", ondelete='cascade')
    is_new = fields.Boolean('New', default=False)
    is_engin = fields.Boolean(related='job_estimate_id.is_engineering')
    sequence = fields.Integer(string="Sequence", default=0)
    number = fields.Integer('No.', compute="_sequence_ref")
    project_scope_id = fields.Many2one('project.scope.line', 'Project Scope')
    section_id = fields.Many2one('section.line', 'Section')
    finish_good_id = fields.Many2one('product.product', 'Finished Goods', required=True,
                                     options="{'no_create': True, 'no_create_edit':True}")
    final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')
    parent_finish_good_id = fields.Many2one('product.product', 'Parent Finish Goods')
    finish_good_id_template = fields.Many2one(related='finish_good_id.product_tmpl_id', string='Finish Goods Template',
                                              readonly=True)
    variable_ref = fields.Many2one('variable.template', string='Variable')
    bom_id = fields.Many2one('mrp.bom', 'BOM', required=True)
    quantity = fields.Float('Quantity', default=1.0)
    initial_quantity = fields.Float('Initial Quantity', default=1.0)
    uom = fields.Many2one('uom.uom', 'Unit Of Measure')
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    subtotal = fields.Monetary('Subtotal', compute="_amount_total_manuf")
    onchange_pass = fields.Boolean(string="Pass", default=False)
    cascaded = fields.Boolean(string="Cascaded", default=False)
    is_child = fields.Boolean(string="Is child", default=False)
    manuf_no = fields.Integer('No. of manufacturing order', default=1)
    parent_manuf_line = fields.Many2one('mrp.bom', string='Parent BOM')
    company_id = fields.Many2one(related='job_estimate_id.company_id', string='Company', readonly=True)
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    project_scope_computed = fields.Many2many('project.scope.line', string="computed scope lines",
                                              compute='get_scope_lines')
    current_quantity = fields.Float('Available Budget Quantity', compute="_onchange_current_qty")
    cost_sheet_ref = fields.Many2one(related="job_estimate_id.cost_sheet_ref", string='Cost Sheet')
    contract_category = fields.Selection(string="Contract Category", related='job_estimate_id.contract_category')
    is_engineering = fields.Boolean(related='job_estimate_id.is_engineering')
    is_lock = fields.Boolean(string='Locked', default=False)
    is_changed = fields.Boolean(string="Is changed")
    operation_two_id = fields.Many2one('mrp.bom.operation', string='Consumed in Operation')
    project_id = fields.Many2one(related='job_estimate_id.project_id', string='Project')

    @api.depends('job_estimate_id.section_ids', 'project_scope_id')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope_id:        
                if rec.material_id.section_ids:
                    for line in rec.material_id.section_ids:
                        if rec.project_scope_id.id == line.project_scope.id:
                            section.append(line.section_name.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]
    
    @api.onchange('quantity')
    def onchange_quantity_manuf(self):
        for rec in self:
            rec.write({'onchange_pass': False,
                       'is_changed': True,
                       })

    @api.onchange('bom_id')
    def _onchange_bom_id(self):
        self.quantity = self.bom_id and self.bom_id.product_qty or 1.0
        self.uom = self.bom_id.product_uom_id.id or False

    def _get_current_quantity(self, rec, project_scope_ref, section_ref):
        finish_good = rec.finish_good_id
        bom = rec.bom_id
        if project_scope_ref and section_ref and finish_good and bom:
            for cost in rec.cost_sheet_ref:
                same = cost.env['cost.manufacture.line'].search(
                    [('job_sheet_id', '=', rec.cost_sheet_ref.id), ('project_scope', '=', project_scope_ref.id),
                     ('section_name', '=', section_ref.id), ('finish_good_id', '=', finish_good.id),
                     ('bom_id', '=', bom.id)], limit=1)
                if len(same) > 0:
                    for sam in same:
                        rec.write({'current_quantity': sam.budgeted_qty_left})
                else:
                    rec.write({'current_quantity': 0})

    def _get_quantity(self):
        for rec in self:
            if rec.contract_category == 'var':
                if rec.cost_sheet_ref:

                    project_scope_ref = False
                    section_ref = False
                    for manuf in rec.cost_sheet_ref.manufacture_line:
                        if manuf.project_scope.name == rec.project_scope_id.name:
                            project_scope_ref = manuf.project_scope
                        if manuf.section_name.name == rec.section_id.name:
                            section_ref = manuf.section_name

                    rec._get_current_quantity(rec, project_scope_ref, section_ref)

                else:
                    rec.write({'current_quantity': 0})
            else:
                rec.write({'current_quantity': 0})

    @api.depends('contract_category', 'project_scope_id', 'section_id', 'finish_good_id', 'bom_id',
                 'cost_sheet_ref')
    def _onchange_current_qty(self):
        self._get_quantity()

    @api.onchange('contract_category', 'quantity')
    def _onchange_current_qty_and_quantity(self):
        for rec in self:
            if rec.contract_category == 'main':
                if rec.quantity <= 0:
                    raise ValidationError('Quantity should be greater than 0.')
            elif rec.contract_category == 'var':
                if rec.quantity == 0:
                    raise ValidationError('Quantity cannot be 0.')
                elif rec.current_quantity + rec.quantity < 0:
                    raise ValidationError(
                        _('You want to reduce quantity of this product and it exceeds the Budgeted Quantity on Job Cost Sheet.'))

    @api.depends('job_estimate_id.project_scope_ids')
    def get_scope_lines(self):
        for rec in self:
            if rec.job_estimate_id.project_scope_ids:
                rec.project_scope_computed = [(6, 0, rec.job_estimate_id.project_scope_ids.mapped("project_scope").ids)]
            else:
                rec.project_scope_computed = [(6, 0, [])]

    @api.depends('job_estimate_id.section_ids')
    def get_section_lines(self):
        for rec in self:
            if rec.job_estimate_id.section_ids:
                rec.project_section_computed = [(6, 0, rec.job_estimate_id.section_ids.mapped("section_name").ids)]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.onchange('project_scope_id')
    def _onchange_project_scope_id(self):
        if self._origin.project_scope_id._origin.id:
            if self._origin.project_scope_id._origin.id != self.project_scope_id.id:
                self.update({
                    'section_id': False,
                    'finish_good_id': False,
                    'bom_id': False,
                })
        else:
            self.update({
                'section_id': False,
                'finish_good_id': False,
                'bom_id': False,
            })

    @api.onchange('section_id')
    def _onchange_secion_id(self):
        if self._origin.section_id._origin.id:
            if self._origin.section_id._origin.id != self.section_id.id:
                self.update({
                    'finish_good_id': False,
                    'bom_id': False,
                })
        else:
            self.update({
                'finish_good_id': False,
                'bom_id': False,
            })

    @api.onchange('finish_good_id')
    def _onchange_finish_good_id(self):
        if self._origin.finish_good_id._origin.id:
            if self._origin.finish_good_id._origin.id != self.finish_good_id.id:
                self.update({
                    'bom_id': False,
                })
        else:
            self.update({
                'bom_id': False,
            })

        if self.finish_good_id:
            product_tmpl = self.finish_good_id.product_tmpl_id.id
            return {
                'domain': {'bom_id': [('product_tmpl_id', '=', product_tmpl)]}
            }

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.depends('job_estimate_id.manufacture_line', 'job_estimate_id.manufacture_line.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.number = no
            for l in line.job_estimate_id.manufacture_line:
                no += 1
                l.number = no

    @api.onchange('bom_id')
    def _onchange_bom(self):
        if self.bom_id:
            self.quantity = 1.0
            self.uom = self.bom_id.product_uom_id.id
        else:
            self.quantity = 1.0
            self.uom = False

    @api.depends('job_estimate_id.material_estimation_ids', 'job_estimate_id.labour_estimation_ids',
                 'job_estimate_id.overhead_estimation_ids', 'job_estimate_id.subcon_estimation_ids',
                 'job_estimate_id.equipment_estimation_ids', 'job_estimate_id.internal_asset_ids',
                 'job_estimate_id.material_estimation_ids.subtotal', 'job_estimate_id.labour_estimation_ids.subtotal',
                 'job_estimate_id.overhead_estimation_ids.subtotal', 'job_estimate_id.subcon_estimation_ids.subtotal',
                 'job_estimate_id.equipment_estimation_ids.subtotal', 'job_estimate_id.internal_asset_ids.subtotal')
    def _amount_total_manuf(self):
        for manuf in self:
            total_subtotal = 0.0
            if manuf.variable_ref:
                material_ids = manuf.job_estimate_id.material_estimation_ids.filtered(
                    lambda m: m.project_scope.id == manuf.project_scope_id.id and
                              m.section_name.id == manuf.section_id.id and
                              m.variable_ref.id == manuf.variable_ref.id and
                              m.finish_good_id.id == manuf.finish_good_id.id and
                              m.bom_id.id == manuf.bom_id.id)
            else:
                material_ids = manuf.job_estimate_id.material_estimation_ids.filtered(
                    lambda m: m.project_scope.id == manuf.project_scope_id.id and
                              m.section_name.id == manuf.section_id.id and
                              m.finish_good_id.id == manuf.finish_good_id.id and
                              m.bom_id.id == manuf.bom_id.id)
            for mat in material_ids:
                total_subtotal += mat.subtotal

            if manuf.variable_ref:
                labour_ids = manuf.job_estimate_id.labour_estimation_ids.filtered(
                    lambda m: m.project_scope.id == manuf.project_scope_id.id and
                              m.section_name.id == manuf.section_id.id and
                              m.variable_ref.id == manuf.variable_ref.id and
                              m.finish_good_id.id == manuf.finish_good_id.id and
                              m.bom_id.id == manuf.bom_id.id)
            else:
                labour_ids = manuf.job_estimate_id.labour_estimation_ids.filtered(
                    lambda m: m.project_scope.id == manuf.project_scope_id.id and
                              m.section_name.id == manuf.section_id.id and
                              m.finish_good_id.id == manuf.finish_good_id.id and
                              m.bom_id.id == manuf.bom_id.id)
            for lab in labour_ids:
                total_subtotal += lab.subtotal

            if manuf.variable_ref:
                overhead_ids = manuf.job_estimate_id.overhead_estimation_ids.filtered(
                    lambda m: m.project_scope.id == manuf.project_scope_id.id and
                              m.section_name.id == manuf.section_id.id and
                              m.variable_ref.id == manuf.variable_ref.id and
                              m.finish_good_id.id == manuf.finish_good_id.id and
                              m.bom_id.id == manuf.bom_id.id)
            else:
                overhead_ids = manuf.job_estimate_id.overhead_estimation_ids.filtered(
                    lambda m: m.project_scope.id == manuf.project_scope_id.id and
                              m.section_name.id == manuf.section_id.id and
                              m.finish_good_id.id == manuf.finish_good_id.id and
                              m.bom_id.id == manuf.bom_id.id)
            for ove in overhead_ids:
                total_subtotal += ove.subtotal

            if manuf.variable_ref:
                subcon_ids = manuf.job_estimate_id.subcon_estimation_ids.filtered(
                    lambda m: m.project_scope.id == manuf.project_scope_id.id and
                              m.section_name.id == manuf.section_id.id and
                              m.variable_ref.id == manuf.variable_ref.id and
                              m.finish_good_id.id == manuf.finish_good_id.id and
                              m.bom_id.id == manuf.bom_id.id)
            else:
                subcon_ids = manuf.job_estimate_id.subcon_estimation_ids.filtered(
                    lambda m: m.project_scope.id == manuf.project_scope_id.id and
                              m.section_name.id == manuf.section_id.id and
                              m.finish_good_id.id == manuf.finish_good_id.id and
                              m.bom_id.id == manuf.bom_id.id)
            for sub in subcon_ids:
                total_subtotal += sub.subtotal

            if manuf.variable_ref:
                equipment_ids = manuf.job_estimate_id.equipment_estimation_ids.filtered(
                    lambda m: m.project_scope.id == manuf.project_scope_id.id and
                              m.section_name.id == manuf.section_id.id and
                              m.variable_ref.id == manuf.variable_ref.id and
                              m.finish_good_id.id == manuf.finish_good_id.id and
                              m.bom_id.id == manuf.bom_id.id)
            else:
                equipment_ids = manuf.job_estimate_id.equipment_estimation_ids.filtered(
                    lambda m: m.project_scope.id == manuf.project_scope_id.id and
                              m.section_name.id == manuf.section_id.id and
                              m.finish_good_id.id == manuf.finish_good_id.id and
                              m.bom_id.id == manuf.bom_id.id)
            for equ in equipment_ids:
                total_subtotal += equ.subtotal

            if manuf.variable_ref:
                asset_ids = manuf.job_estimate_id.internal_asset_ids.filtered(
                    lambda m: m.project_scope.id == manuf.project_scope_id.id and
                              m.section_name.id == manuf.section_id.id and
                              m.variable_ref.id == manuf.variable_ref.id and
                              m.finish_good_id.id == manuf.finish_good_id.id and
                              m.bom_id.id == manuf.bom_id.id)
            else:
                asset_ids = manuf.job_estimate_id.internal_asset_ids.filtered(
                    lambda m: m.project_scope.id == manuf.project_scope_id.id and
                              m.section_name.id == manuf.section_id.id and
                              m.finish_good_id.id == manuf.finish_good_id.id and
                              m.bom_id.id == manuf.bom_id.id)
            for ass in asset_ids:
                total_subtotal += ass.subtotal

            manuf.subtotal = total_subtotal


class VariableEstimateInherit(models.Model):
    _inherit = "variable.estimate"

    is_engineering = fields.Boolean(related='variable_id.is_engineering')

    # @api.onchange('is_engineering')
    # def _onchange_is_engineering(self):
    # 	for rec in self:
    # 		company = rec.company_id
    # 		if rec.is_engineering == 'False':
    # 			return {
    # 				'domain': {'variable_name': [('variable_subcon', '=', False), ('construction_type', '=', 'construction'), ('company_id', '=', company)]}
    # 			}
    # 		else:
    # 			return {
    # 				'domain': {'variable_name': [('variable_subcon', '=', False), ('construction_type', 'in', ('construction', 'engineering')), ('company_id', '=', company)]}
    #           }


class MaterialEstimate(models.Model):
    _inherit = 'material.estimate'

    manufacture_finish_good = fields.Many2many('product.product', 'manufacture_finish_good_rel', 'material_id',
                                               'finish_good_id', 'Finish Goods', compute='_get_default_finish_good')
    finish_good_id = fields.Many2one('product.product', 'Finished Goods',
                                     options="{'no_create': True, 'no_create_edit':True}")
    parent_finish_good_id = fields.Many2one('product.product', 'Parent Finished Goods')
    final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')
    finish_good_id_template = fields.Many2one(related='finish_good_id.product_tmpl_id', string='Finish Goods Template',
                                              readonly=True)
    bom_id = fields.Many2one('mrp.bom', 'BOM')
    operation_two_id = fields.Many2one('mrp.bom.operation', string='Consumed in Operation')

    def _get_current_quantity(self, rec, project_scope_ref, section_ref):
        finish_good = rec.finish_good_id
        bom = rec.bom_id
        if project_scope_ref and section_ref and not finish_good and not bom:
            for cost in rec.cost_sheet_ref:
                same = cost.env['material.material'].search(
                    [('job_sheet_id', '=', rec.cost_sheet_ref.id), ('project_scope', '=', project_scope_ref.id),
                     ('section_name', '=', section_ref.id), ('group_of_product', '=', rec.group_of_product.id),
                     ('product_id', '=', rec.product_id.id), ('description', '=', rec.description)], limit=1)
                if len(same) > 0:
                    for sam in same:
                        rec.write({'current_quantity': sam.budgeted_qty_left})
                else:
                    rec.write({'current_quantity': 0})

        elif project_scope_ref and section_ref and finish_good and bom:
            for cost in rec.cost_sheet_ref:
                same = cost.env['material.material'].search(
                    [('job_sheet_id', '=', rec.cost_sheet_ref.id), ('project_scope', '=', project_scope_ref.id),
                     ('section_name', '=', section_ref.id), ('finish_good_id', '=', finish_good.id),
                     ('bom_id', '=', bom.id), ('group_of_product', '=', rec.group_of_product.id),
                     ('product_id', '=', rec.product_id.id), ('description', '=', rec.description)], limit=1)
                if len(same) > 0:
                    for sam in same:
                        rec.write({'current_quantity': sam.budgeted_qty_left})
                else:
                    rec.write({'current_quantity': 0})

        else:
            rec.write({'current_quantity': 0})

    @api.depends('contract_category', 'project_scope', 'section_name', 'finish_good_id', 'bom_id', 'group_of_product',
                 'product_id', 'description',
                 'cost_sheet_ref')
    def _onchange_current_qty(self):
        self._get_quantity()

    @api.depends('material_id', 'finish_good_id')
    def _get_default_finish_good(self):
        for rec in self:
            if len(rec.material_id.manufacture_line) > 0:
                for goods in rec.material_id.manufacture_line:
                    if len(goods.finish_good_id) > 0:
                        rec.manufacture_finish_good += goods.finish_good_id
                    else:
                        continue
            else:
                rec.manufacture_finish_good = False

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        res = super(MaterialEstimate, self)._onchange_project_scope_handling()
        if self.material_id.is_engineering:
            if self._origin.project_scope._origin.id:
                if self._origin.project_scope._origin.id != self.project_scope.id:
                    self.update({
                        'finish_good_id': False,
                        'bom_id': False
                    })
            else:
                self.update({
                    'finish_good_id': False,
                    'bom_id': False
                })
            return res

    @api.onchange('section_name')
    def _onchange_section_handling(self):
        res = super(MaterialEstimate, self)._onchange_section_handling()
        if self.material_id.is_engineering:
            if self._origin.section_name._origin.id:
                if self._origin.section_name._origin.id != self.section_name.id:
                    self.update({
                        'finish_good_id': False,
                        'bom_id': False
                    })
            else:
                self.update({
                    'finish_good_id': False,
                    'bom_id': False
                })
        return res

    @api.onchange('variable_ref')
    def _onchange_variable_handling(self):
        res = super(MaterialEstimate, self)._onchange_variable_handling()
        if self.material_id.is_engineering:
            if self._origin.variable_ref._origin.id:
                if self._origin.variable_ref._origin.id != self.variable_ref.id:
                    self.update({
                        'finish_good_id': False,
                        'bom_id': False
                    })
            else:
                self.update({
                    'finish_good_id': False,
                    'bom_id': False
                })
        return res

    @api.onchange('finish_good_id')
    def _onchange_finish_good_handling(self):
        if self._origin.finish_good_id._origin.id:
            if self._origin.finish_good_id._origin.id != self.finish_good_id.id:
                self.update({
                    'bom_id': False,
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'bom_id': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('bom_id')
    def _onchange_bom_handling(self):
        if self._origin.bom_id._origin.id:
            if self._origin.bom_id._origin.id != self.bom_id.id:
                self.update({
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'group_of_product': False,
                'product_id': False,
            })


class LabourEstimate(models.Model):
    _inherit = 'labour.estimate'

    manufacture_finish_good = fields.Many2many('product.product', 'manufacture_finish_good_rel', 'labour_id',
                                               'finish_good_id', 'Finish Goods', compute='_get_default_finish_good')
    finish_good_id = fields.Many2one('product.product', 'Finished Goods',
                                     options="{'no_create': True, 'no_create_edit':True}")
    parent_finish_good_id = fields.Many2one('product.product', 'Parent Finished Goods')
    final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')
    finish_good_id_template = fields.Many2one(related='finish_good_id.product_tmpl_id', string='Finish Goods Template',
                                              readonly=True)
    bom_id = fields.Many2one('mrp.bom', 'BOM')
    operation_two_id = fields.Many2one('mrp.bom.operation', string='Consumed in Operation')

    def _get_current_quantity(self, rec, project_scope_ref, section_ref):
        finish_good = rec.finish_good_id
        bom = rec.bom_id
        if project_scope_ref and section_ref and not finish_good and not bom:
            for cost in rec.cost_sheet_ref:
                same = cost.env['material.labour'].search(
                    [('job_sheet_id', '=', rec.cost_sheet_ref.id), ('project_scope', '=', project_scope_ref.id),
                     ('section_name', '=', section_ref.id), ('group_of_product', '=', rec.group_of_product.id),
                     ('product_id', '=', rec.product_id.id), ('description', '=', rec.description)], limit=1)
                if len(same) > 0:
                    for sam in same:
                        rec.write({'current_quantity': sam.budgeted_qty_left})
                else:
                    rec.write({'current_quantity': 0})

        elif project_scope_ref and section_ref and finish_good and bom:
            for cost in rec.cost_sheet_ref:
                same = cost.env['material.labour'].search(
                    [('job_sheet_id', '=', rec.cost_sheet_ref.id), ('project_scope', '=', project_scope_ref.id),
                     ('section_name', '=', section_ref.id), ('finish_good_id', '=', finish_good.id),
                     ('bom_id', '=', bom.id), ('group_of_product', '=', rec.group_of_product.id),
                     ('product_id', '=', rec.product_id.id), ('description', '=', rec.description)], limit=1)
                if len(same) > 0:
                    for sam in same:
                        rec.write({'current_quantity': sam.budgeted_qty_left})
                else:
                    rec.write({'current_quantity': 0})

        else:
            rec.write({'current_quantity': 0})

    @api.depends('contract_category', 'project_scope', 'section_name', 'finish_good_id', 'bom_id', 'group_of_product',
                 'product_id', 'description',
                 'cost_sheet_ref')
    def _onchange_current_qty(self):
        self._get_quantity()

    @api.depends('labour_id', 'finish_good_id')
    def _get_default_finish_good(self):
        for rec in self:
            if len(rec.labour_id.manufacture_line) > 0:
                for goods in rec.labour_id.manufacture_line:
                    if len(goods.finish_good_id) > 0:
                        rec.manufacture_finish_good += goods.finish_good_id
                    else:
                        continue
            else:
                rec.manufacture_finish_good = False

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        res = super(LabourEstimate, self)._onchange_project_scope_handling()
        if self.labour_id.is_engineering:
            if self._origin.project_scope._origin.id:
                if self._origin.project_scope._origin.id != self.project_scope.id:
                    self.update({
                        'finish_good_id': False,
                        'bom_id': False
                    })
            else:
                self.update({
                    'finish_good_id': False,
                    'bom_id': False
                })
        return res

    @api.onchange('section_name')
    def _onchange_section_handling(self):
        res = super(LabourEstimate, self)._onchange_section_handling()
        if self.labour_id.is_engineering:
            if self._origin.section_name._origin.id:
                if self._origin.section_name._origin.id != self.section_name.id:
                    self.update({
                        'finish_good_id': False,
                        'bom_id': False
                    })
            else:
                self.update({
                    'finish_good_id': False,
                    'bom_id': False
                })
        return res

    @api.onchange('variable_ref')
    def _onchange_variable_handling(self):
        res = super(LabourEstimate, self)._onchange_variable_handling()
        if self.labour_id.is_engineering:
            if self._origin.variable_ref._origin.id:
                if self._origin.variable_ref._origin.id != self.variable_ref.id:
                    self.update({
                        'finish_good_id': False,
                        'bom_id': False
                    })
            else:
                self.update({
                    'finish_good_id': False,
                    'bom_id': False
                })
        return res

    @api.onchange('finish_good_id')
    def _onchange_finish_good_handling(self):
        if self._origin.finish_good_id._origin.id:
            if self._origin.finish_good_id._origin.id != self.finish_good_id.id:
                self.update({
                    'bom_id': False,
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'bom_id': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('bom_id')
    def _onchange_bom_handling(self):
        if self._origin.bom_id._origin.id:
            if self._origin.bom_id._origin.id != self.bom_id.id:
                self.update({
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'group_of_product': False,
                'product_id': False,
            })


class OverheadEstimate(models.Model):
    _inherit = 'overhead.estimate'

    manufacture_finish_good = fields.Many2many('product.product', 'manufacture_finish_good_rel', 'overhead_id',
                                               'finish_good_id', 'Finish Goods', compute='_get_default_finish_good')
    parent_finish_good_id = fields.Many2one('product.product', 'Parent Finished Goods')
    finish_good_id = fields.Many2one('product.product', 'Finished Goods',
                                     options="{'no_create': True, 'no_create_edit':True}")
    final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')
    finish_good_id_template = fields.Many2one(related='finish_good_id.product_tmpl_id', string='Finish Goods Template',
                                              readonly=True)
    bom_id = fields.Many2one('mrp.bom', 'BOM')
    operation_two_id = fields.Many2one('mrp.bom.operation', string='Consumed in Operation')

    def _get_current_quantity(self, rec, project_scope_ref, section_ref):
        finish_good = rec.finish_good_id
        bom = rec.bom_id
        if project_scope_ref and section_ref and not finish_good and not bom:
            for cost in rec.cost_sheet_ref:
                same = cost.env['material.overhead'].search(
                    [('job_sheet_id', '=', rec.cost_sheet_ref.id), ('project_scope', '=', project_scope_ref.id),
                     ('section_name', '=', section_ref.id), ('overhead_catagory', '=', rec.overhead_catagory),
                     ('group_of_product', '=', rec.group_of_product.id), ('product_id', '=', rec.product_id.id),
                     ('description', '=', rec.description)], limit=1)
                if len(same) > 0:
                    for sam in same:
                        rec.write({'current_quantity': sam.budgeted_qty_left})
                else:
                    rec.write({'current_quantity': 0})

        elif project_scope_ref and section_ref and finish_good and bom:
            for cost in rec.cost_sheet_ref:
                same = cost.env['material.overhead'].search(
                    [('job_sheet_id', '=', rec.cost_sheet_ref.id), ('project_scope', '=', project_scope_ref.id),
                     ('section_name', '=', section_ref.id), ('finish_good_id', '=', finish_good.id),
                     ('bom_id', '=', bom.id), ('overhead_catagory', '=', rec.overhead_catagory),
                     ('group_of_product', '=', rec.group_of_product.id), ('product_id', '=', rec.product_id.id),
                     ('description', '=', rec.description)], limit=1)
                if len(same) > 0:
                    for sam in same:
                        rec.write({'current_quantity': sam.budgeted_qty_left})
                else:
                    rec.write({'current_quantity': 0})

        else:
            rec.write({'current_quantity': 0})

    @api.depends('contract_category', 'project_scope', 'section_name', 'finish_good_id', 'bom_id', 'overhead_catagory',
                 'group_of_product', 'product_id', 'description',
                 'cost_sheet_ref')
    def _onchange_current_qty(self):
        self._get_quantity()

    @api.depends('overhead_id', 'finish_good_id')
    def _get_default_finish_good(self):
        for rec in self:
            if len(rec.overhead_id.manufacture_line) > 0:
                for goods in rec.overhead_id.manufacture_line:
                    if len(goods.finish_good_id) > 0:
                        rec.manufacture_finish_good += goods.finish_good_id
                    else:
                        continue
            else:
                rec.manufacture_finish_good = False

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        res = super(OverheadEstimate, self)._onchange_project_scope_handling()
        if self.overhead_id.is_engineering:
            if self._origin.project_scope._origin.id:
                if self._origin.project_scope._origin.id != self.project_scope.id:
                    self.update({
                        'finish_good_id': False,
                        'bom_id': False
                    })
            else:
                self.update({
                    'finish_good_id': False,
                    'bom_id': False
                })
        return res

    @api.onchange('section_name')
    def _onchange_section_handling(self):
        res = super(OverheadEstimate, self)._onchange_section_handling()
        if self.overhead_id.is_engineering:
            if self._origin.section_name._origin.id:
                if self._origin.section_name._origin.id != self.section_name.id:
                    self.update({
                        'finish_good_id': False,
                        'bom_id': False
                    })
            else:
                self.update({
                    'finish_good_id': False,
                    'bom_id': False
                })
        return res

    @api.onchange('variable_ref')
    def _onchange_variable_handling(self):
        res = super(OverheadEstimate, self)._onchange_variable_handling()
        if self.overhead_id.is_engineering:
            if self._origin.variable_ref._origin.id:
                if self._origin.variable_ref._origin.id != self.variable_ref.id:
                    self.update({
                        'finish_good_id': False,
                        'bom_id': False
                    })
            else:
                self.update({
                    'finish_good_id': False,
                    'bom_id': False
                })
        return res

    @api.onchange('finish_good_id')
    def _onchange_finish_good_handling(self):
        if self._origin.finish_good_id._origin.id:
            if self._origin.finish_good_id._origin.id != self.finish_good_id.id:
                self.update({
                    'bom_id': False,
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'bom_id': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('bom_id')
    def _onchange_bom_handling(self):
        if self._origin.bom_id._origin.id:
            if self._origin.bom_id._origin.id != self.bom_id.id:
                self.update({
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'group_of_product': False,
                'product_id': False,
            })


class InternalAssets(models.Model):
    _inherit = 'internal.assets'

    manufacture_finish_good = fields.Many2many('product.product', 'manufacture_finish_good_rel', 'asset_id',
                                               'finish_good_id', 'Finish Goods', compute='_get_default_finish_good')
    finish_good_id = fields.Many2one('product.product', 'Finished Goods',
                                     options="{'no_create': True, 'no_create_edit':True}")
    parent_finish_good_id = fields.Many2one('product.product', 'Parent Finished Goods')
    final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')
    finish_good_id_template = fields.Many2one(related='finish_good_id.product_tmpl_id', string='Finish Goods Template',
                                              readonly=True)
    bom_id = fields.Many2one('mrp.bom', 'BOM')
    operation_two_id = fields.Many2one('mrp.bom.operation', string='Consumed in Operation')

    def _get_current_quantity(self, rec, project_scope_ref, section_ref):
        finish_good = rec.finish_good_id
        bom = rec.bom_id
        if project_scope_ref and section_ref and not finish_good and not bom:
            for cost in rec.cost_sheet_ref:
                same = cost.env['internal.asset'].search(
                    [('job_sheet_id', '=', rec.cost_sheet_ref.id), ('project_scope', '=', project_scope_ref.id),
                     ('section_name', '=', section_ref.id), ('asset_category_id', '=', rec.asset_category_id.id),
                     ('asset_id', '=', rec.asset_id.id)], limit=1)
                if len(same) > 0:
                    for sam in same:
                        rec.write({'current_quantity': sam.budgeted_qty_left})
                else:
                    rec.write({'current_quantity': 0})

        elif project_scope_ref and section_ref and finish_good and bom:
            for cost in rec.cost_sheet_ref:
                same = cost.env['internal.asset'].search(
                    [('job_sheet_id', '=', rec.cost_sheet_ref.id), ('project_scope', '=', project_scope_ref.id),
                     ('section_name', '=', section_ref.id), ('finish_good_id', '=', finish_good.id),
                     ('bom_id', '=', bom.id), ('asset_category_id', '=', rec.asset_category_id.id),
                     ('asset_id', '=', rec.asset_id.id), ('description', '=', rec.description)], limit=1)
                if len(same) > 0:
                    for sam in same:
                        rec.write({'current_quantity': sam.budgeted_qty_left})
                else:
                    rec.write({'current_quantity': 0})

        else:
            rec.write({'current_quantity': 0})

    @api.depends('contract_category', 'project_scope', 'section_name', 'finish_good_id', 'bom_id', 'asset_category_id',
                 'asset_id', 'description',
                 'cost_sheet_ref')
    def _onchange_current_qty(self):
        self._get_quantity()

    @api.depends('asset_job_id', 'finish_good_id')
    def _get_default_finish_good(self):
        for rec in self:
            if len(rec.asset_job_id.manufacture_line) > 0:
                for goods in rec.asset_job_id.manufacture_line:
                    if len(goods.finish_good_id) > 0:
                        rec.manufacture_finish_good += goods.finish_good_id
                    else:
                        continue
            else:
                rec.manufacture_finish_good = False

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        res = super(InternalAssets, self)._onchange_project_scope_handling()
        if self.asset_job_id.is_engineering:
            if self._origin.project_scope._origin.id:
                if self._origin.project_scope._origin.id != self.project_scope.id:
                    self.update({
                        'finish_good_id': False,
                        'bom_id': False
                    })
            else:
                self.update({
                    'finish_good_id': False,
                    'bom_id': False
                })
        return res

    @api.onchange('section_name')
    def _onchange_section_handling(self):
        res = super(InternalAssets, self)._onchange_section_handling()
        if self.asset_job_id.is_engineering:
            if self._origin.section_name._origin.id:
                if self._origin.section_name._origin.id != self.section_name.id:
                    self.update({
                        'finish_good_id': False,
                        'bom_id': False
                    })
            else:
                self.update({
                    'finish_good_id': False,
                    'bom_id': False
                })
        return res

    @api.onchange('variable_ref')
    def _onchange_variable_handling(self):
        res = super(InternalAssets, self)._onchange_variable_handling()
        if self.asset_job_id.is_engineering:
            if self._origin.variable_ref._origin.id:
                if self._origin.variable_ref._origin.id != self.variable_ref.id:
                    self.update({
                        'finish_good_id': False,
                        'bom_id': False,
                    })
            else:
                self.update({
                    'finish_good_id': False,
                    'bom_id': False,
                })
        return res

    @api.onchange('finish_good_id')
    def _onchange_finish_good_handling(self):
        if self._origin.finish_good_id._origin.id:
            if self._origin.finish_good_id._origin.id != self.finish_good_id.id:
                self.update({
                    'bom_id': False,
                    'asset_category_id': False,
                    'asset_id': False,
                })
        else:
            self.update({
                'bom_id': False,
                'asset_category_id': False,
                'asset_id': False,
            })

    @api.onchange('bom_id')
    def _onchange_bom_handling(self):
        if self._origin.bom_id._origin.id:
            if self._origin.bom_id._origin.id != self.bom_id.id:
                self.update({
                    'asset_category_id': False,
                    'asset_id': False,

                })
        else:
            self.update({
                'asset_category_id': False,
                'asset_id': False,
            })


class EquipmentEstimate(models.Model):
    _inherit = 'equipment.estimate'

    manufacture_finish_good = fields.Many2many('product.product', 'manufacture_finish_good_rel', 'equipment_id',
                                               'finish_good_id', 'Finish Goods', compute='_get_default_finish_good')
    finish_good_id = fields.Many2one('product.product', 'Finished Goods',
                                     options="{'no_create': True, 'no_create_edit':True}")
    parent_finish_good_id = fields.Many2one('product.product', 'Parent Finished Goods')
    final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')
    finish_good_id_template = fields.Many2one(related='finish_good_id.product_tmpl_id', string='Finish Goods Template',
                                              readonly=True)
    bom_id = fields.Many2one('mrp.bom', 'BOM')
    operation_two_id = fields.Many2one('mrp.bom.operation', string='Consumed in Operation')

    def _get_current_quantity(self, rec, project_scope_ref, section_ref):
        finish_good = rec.finish_good_id
        bom = rec.bom_id
        if project_scope_ref and section_ref and not finish_good and not bom:
            for cost in rec.cost_sheet_ref:
                same = cost.env['material.equipment'].search(
                    [('job_sheet_id', '=', rec.cost_sheet_ref.id), ('project_scope', '=', project_scope_ref.id),
                     ('section_name', '=', section_ref.id), ('group_of_product', '=', rec.group_of_product.id),
                     ('product_id', '=', rec.product_id.id), ('description', '=', rec.description)], limit=1)
                if len(same) > 0:
                    for sam in same:
                        rec.write({'current_quantity': sam.budgeted_qty_left})
                else:
                    rec.write({'current_quantity': 0})

        elif project_scope_ref and section_ref and finish_good and bom:
            for cost in rec.cost_sheet_ref:
                same = cost.env['material.equipment'].search(
                    [('job_sheet_id', '=', rec.cost_sheet_ref.id), ('project_scope', '=', project_scope_ref.id),
                     ('section_name', '=', section_ref.id), ('finish_good_id', '=', finish_good.id),
                     ('bom_id', '=', bom.id), ('group_of_product', '=', rec.group_of_product.id),
                     ('product_id', '=', rec.product_id.id), ('description', '=', rec.description)], limit=1)
                if len(same) > 0:
                    for sam in same:
                        rec.write({'current_quantity': sam.budgeted_qty_left})
                else:
                    rec.write({'current_quantity': 0})

        else:
            rec.write({'current_quantity': 0})

    @api.depends('contract_category', 'project_scope', 'section_name', 'finish_good_id', 'bom_id', 'group_of_product',
                 'product_id', 'description',
                 'cost_sheet_ref')
    def _onchange_current_qty(self):
        self._get_quantity()

    @api.depends('equipment_id', 'finish_good_id')
    def _get_default_finish_good(self):
        for rec in self:
            if len(rec.equipment_id.manufacture_line) > 0:
                for goods in rec.equipment_id.manufacture_line:
                    if len(goods.finish_good_id) > 0:
                        rec.manufacture_finish_good += goods.finish_good_id
                    else:
                        continue
            else:
                rec.manufacture_finish_good = False

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        res = super(EquipmentEstimate, self)._onchange_project_scope_handling()
        if self.equipment_id.is_engineering:
            if self._origin.project_scope._origin.id:
                if self._origin.project_scope._origin.id != self.project_scope.id:
                    self.update({
                        'finish_good_id': False,
                        'bom_id': False
                    })
            else:
                self.update({
                    'finish_good_id': False,
                    'bom_id': False
                })
        return res

    @api.onchange('section_name')
    def _onchange_section_handling(self):
        res = super(EquipmentEstimate, self)._onchange_section_handling()
        if self.equipment_id.is_engineering:
            if self._origin.section_name._origin.id:
                if self._origin.section_name._origin.id != self.section_name.id:
                    self.update({
                        'finish_good_id': False,
                        'bom_id': False
                    })
            else:
                self.update({
                    'finish_good_id': False,
                    'bom_id': False
                })
        return res

    @api.onchange('variable_ref')
    def _onchange_variable_handling(self):
        res = super(EquipmentEstimate, self)._onchange_section_handling()
        if self.equipment_id.is_engineering:
            if self._origin.variable_ref._origin.id:
                if self._origin.variable_ref._origin.id != self.variable_ref.id:
                    self.update({
                        'finish_good_id': False,
                        'bom_id': False
                    })
            else:
                self.update({
                    'finish_good_id': False,
                    'bom_id': False
                })
        return res

    @api.onchange('finish_good_id')
    def _onchange_finish_good_handling(self):
        if self._origin.finish_good_id._origin.id:
            if self._origin.finish_good_id._origin.id != self.finish_good_id.id:
                self.update({
                    'bom_id': False,
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'bom_id': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('bom_id')
    def _onchange_bom_handling(self):
        if self._origin.bom_id._origin.id:
            if self._origin.bom_id._origin.id != self.bom_id.id:
                self.update({
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'group_of_product': False,
                'product_id': False,
            })


class SubconEstimate(models.Model):
    _inherit = 'subcon.estimate'

    manufacture_finish_good = fields.Many2many('product.product', 'manufacture_finish_good_rel', 'subcon_id',
                                               'finish_good_id', 'Finish Goods', compute='_get_default_finish_good')
    finish_good_id = fields.Many2one('product.product', 'Finished Goods',
                                     options="{'no_create': True, 'no_create_edit':True}")
    parent_finish_good_id = fields.Many2one('product.product', 'Parent Finished Goods')
    final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')
    finish_good_id_template = fields.Many2one(related='finish_good_id.product_tmpl_id', string='Finish Goods Template',
                                              readonly=True)
    bom_id = fields.Many2one('mrp.bom', 'BOM')
    operation_two_id = fields.Many2one('mrp.bom.operation', string='Consumed in Operation')

    def _get_current_quantity(self, rec, project_scope_ref, section_ref):
        finish_good = rec.finish_good_id
        bom = rec.bom_id
        if project_scope_ref and section_ref and not finish_good and not bom:
            for cost in rec.cost_sheet_ref:
                same = cost.env['material.subcon'].search(
                    [('job_sheet_id', '=', rec.cost_sheet_ref.id), ('project_scope', '=', rec.project_scope.id),
                     ('section_name', '=', rec.section_name.id), ('variable', '=', rec.variable.id),
                     ('description', '=', rec.description)], limit=1)
                if len(same) > 0:
                    for sam in same:
                        rec.write({'current_quantity': sam.budgeted_qty_left})
                else:
                    rec.write({'current_quantity': 0})

        elif project_scope_ref and section_ref and finish_good and bom:
            for cost in rec.cost_sheet_ref:
                same = cost.env['material.subcon'].search(
                    [('job_sheet_id', '=', rec.cost_sheet_ref.id), ('project_scope', '=', project_scope_ref.id),
                     ('section_name', '=', section_ref.id), ('finish_good_id', '=', finish_good.id),
                     ('bom_id', '=', bom.id), ('variable', '=', rec.variable.id),
                     ('description', '=', rec.description)], limit=1)
                if len(same) > 0:
                    for sam in same:
                        rec.write({'current_quantity': sam.budgeted_qty_left})
                else:
                    rec.write({'current_quantity': 0})

        else:
            rec.write({'current_quantity': 0})

    @api.depends('contract_category', 'project_scope', 'section_name', 'finish_good_id', 'bom_id', 'variable',
                 'description',
                 'cost_sheet_ref')
    def _onchange_current_qty(self):
        self._get_quantity()

    @api.depends('subcon_id', 'finish_good_id')
    def _get_default_finish_good(self):
        for rec in self:
            if len(rec.subcon_id.manufacture_line) > 0:
                for goods in rec.subcon_id.manufacture_line:
                    if len(goods.finish_good_id) > 0:
                        rec.manufacture_finish_good += goods.finish_good_id
                    else:
                        continue
            else:
                rec.manufacture_finish_good = False

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        res = super(SubconEstimate, self)._onchange_project_scope_handling()
        if self.subcon_id.is_engineering:
            if self._origin.project_scope._origin.id:
                if self._origin.project_scope._origin.id != self.project_scope.id:
                    self.update({
                        'finish_good_id': False,
                        'bom_id': False
                    })
            else:
                self.update({
                    'finish_good_id': False,
                    'bom_id': False
                })
        return res

    @api.onchange('section_name')
    def _onchange_section_handling(self):
        res = super(SubconEstimate, self)._onchange_section_handling()
        if self.subcon_id.is_engineering:
            if self._origin.section_name._origin.id:
                if self._origin.section_name._origin.id != self.section_name.id:
                    self.update({
                        'finish_good_id': False,
                        'bom_id': False
                    })
            else:
                self.update({
                    'finish_good_id': False,
                    'bom_id': False
                })
        return res

    @api.onchange('variable_ref')
    def _onchange_variable_handling(self):
        res = super(SubconEstimate, self)._onchange_variable_handling()
        if self.subcon_id.is_engineering:
            if self._origin.variable_ref._origin.id:
                if self._origin.variable_ref._origin.id != self.variable_ref.id:
                    self.update({
                        'finish_good_id': False,
                        'bom_id': False
                    })
            else:
                self.update({
                    'finish_good_id': False,
                    'bom_id': False
                })
        return res

    @api.onchange('finish_good_id')
    def _onchange_finish_good_handling(self):
        if self._origin.finish_good_id._origin.id:
            if self._origin.finish_good_id._origin.id != self.finish_good_id.id:
                self.update({
                    'bom_id': False,
                    'variable': False,
                })
        else:
            self.update({
                'bom_id': False,
                'variable': False,
            })

    @api.onchange('bom_id')
    def _onchange_bom_handling(self):
        if self._origin.bom_id._origin.id:
            if self._origin.bom_id._origin.id != self.bom_id.id:
                self.update({
                    'variable': False,

                })
        else:
            self.update({
                'variable': False,
            })


class JobEstimateToVariationInheritAgain(models.TransientModel):
    _inherit = 'job.estimate.variation.const'

    def _prepare_value(self, main_contract):
        res = super(JobEstimateToVariationInheritAgain, self)._prepare_value(main_contract)
        res['manufacture_line'] = False

        return res

    # def action_confirm(self):
    # 	job_id = self.env['job.estimate'].browse([self._context.get('active_id')])
    # 	main_contract = self.env['sale.order.const'].search([('project_id', '=', job_id.project_id.id), ('contract_category', '=', 'main'), ('state', 'in', ['sale','done'])], limit=1)
    # 	job_cost_sheet = self.env['job.cost.sheet'].search([('project_id', '=', job_id.project_id.id)], limit=1)
    # 	job_id.write({'name': self.env['ir.sequence'].next_by_code('job.sequence.vo'),
    # 					'state':'draft',
    # 					'state_new':'draft',
    # 					'contract_category' :'var',
    # 					'main_contract_ref': main_contract,
    # 					'cost_sheet_ref': job_cost_sheet or False,
    # 					'project_scope_ids': False,
    # 					'section_ids': False,
    # 					'variable_ids': False,
    # 					'manufacture_line': False,
    # 					'material_estimation_ids': False,
    # 					'labour_estimation_ids': False,
    # 					'overhead_estimation_ids': False,
    # 					'equipment_estimation_ids': False,
    # 					'internal_asset_ids': False,
    # 					'subcon_estimation_ids': False,
    # 				})
