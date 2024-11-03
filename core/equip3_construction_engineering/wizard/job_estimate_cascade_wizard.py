from odoo import _, api, fields, models
from datetime import datetime
from odoo.exceptions import ValidationError


class JobCascadeWizard(models.TransientModel):
    _name = 'job.cascade.wizard'
    _description = "BOQ Cascade Manufacture"

    # fields
    company_id = fields.Many2one('res.company', string="Company", required=True, readonly=True)
    project_id = fields.Many2one(comodel_name='project.project', string='Project', required=True)
    job_estimate_id = fields.Many2one(comodel_name='job.estimate', string='BOQ')
    cost_sheet = fields.Many2one('job.cost.sheet', string='Cost Sheet', force_save="1")
    hide_cost_sheet = fields.Boolean(string="Hide cost sheet", default=False)
    hide_job_estimate = fields.Boolean(string="Hide BOQ", default=False)
    undo_cascade = fields.Boolean(string="Undo Cascade", default=False)
    job_cascade_line_ids = fields.One2many('job.cascade.wizard.line', 'job_cascade_id', string='Manufacture Line')

    def _create_new_line(self, product_id, bom, parent_bom, prod_quantity, initial_quantity, parent_line_scope, parent_line_sec,
                         parent_fg, bom_ref=False):
        if self.job_estimate_id:
            self.env['to.manufacture.line'].create({
                'job_estimate_id': self.job_estimate_id.id,
                'project_scope_id': parent_line_scope.id,
                'section_id': parent_line_sec.id,
                'finish_good_id': product_id.id,
                'bom_id': bom.id,
                'parent_manuf_line': parent_bom.id,
                'initial_quantity': initial_quantity,
                'quantity': prod_quantity,
                'uom': bom.product_uom_id.id,
                'cascaded': True,
                'is_child': True,
                'parent_finish_good_id': bom_ref,
                'final_finish_good_id': parent_fg.id,
            })
        elif self.cost_sheet:
            self.env['cost.manufacture.line'].create({
                'job_sheet_id': self.cost_sheet.id,
                'project_scope': parent_line_scope.id,
                'section_name': parent_line_sec.id,
                'finish_good_id': product_id.id,
                'bom_id': bom.id,
                'parent_manuf_line': parent_bom.id,
                'product_qty': prod_quantity,
                'uom_id': bom.product_uom_id.id,
                'cascaded': True,
                'is_child': True,
                'final_finish_good_id': parent_fg.id,
            })

    def get_quantity(self, bom_line, parent_line):
        for rec in self:
            quantity = parent_line.product_qty
            line = bom_line
            i = 0
            while line:
                bom_ref = rec.env['product.product'].search(
                    [('product_tmpl_id', '=', line.bom_id.product_tmpl_id.id)])
                prev_bom = rec.env['mrp.bom']._bom_find(product=bom_ref, company_id=self.company_id.id,
                                                        bom_type='normal')
                parent_bom_line = prev_bom.bom_line_ids.search([('product_id', '=', bom_ref.id)])

                if len(parent_bom_line) > 0:
                    if i == 0:
                        quantity = quantity * parent_bom_line.product_qty * line.product_qty
                        i += 1
                    else:
                        quantity = parent_bom_line.product_qty * quantity
                    line = parent_bom_line
                else:
                    if i == 0:
                        quantity = parent_line.product_qty * bom_line.product_qty
                        return quantity
                    else:
                        return quantity

            return quantity

    def cascade_button(self):
        for rec in self:
            line_ids = self.job_cascade_line_ids.filtered(lambda l: l.is_active)

            if len(line_ids) == 0:
                raise ValidationError("The Cascade line is empty!")
            for line in line_ids:
                parent_line_scope_id = line.project_scope
                parent_line_sec_id = line.section_name

                bom_line_ids = line.bom_id.bom_line_ids
                next_bom = []
                while bom_line_ids:
                    if line.is_child:
                        parent_fg_id = line.final_finish_good_id
                    else:
                        parent_fg_id = line.finish_good_id
                    parent_bom = line.bom_id

                    for bom_line in bom_line_ids:
                        product_id = bom_line.product_id

                        bom = self.env['mrp.bom']._bom_find(product=product_id, company_id=self.company_id.id,
                                                            bom_type='normal')
                        if bom:
                            bom_ref = rec.env['product.product'].search(
                                [('product_tmpl_id', '=', bom_line.bom_id.product_tmpl_id.id)])

                            prod_quantity = rec.get_quantity(bom_line, line)

                            rec._create_new_line(product_id, bom, parent_bom, prod_quantity, bom_line.product_qty,
                                                 parent_line_scope_id,
                                                 parent_line_sec_id, parent_fg_id, bom_ref.id)

                            if self.job_estimate_id:
                                line.to_manuf_line_id.cascaded = True
                                rec.job_estimate_id.update_manuf_line(parent_fg_id.id, bom_ref.id)
                            elif self.cost_sheet:
                                line.cost_manuf_line_id.cascaded = True

                            if bom not in next_bom:
                                next_bom.append(bom)
                    if len(next_bom) > 0:
                        bom_line_ids = next_bom[0].bom_line_ids
                        next_bom.pop(0)
                    else:
                        break

    def undo_button(self):
        for line in self.job_cascade_line_ids.filtered(lambda l: l.is_active):
            if self.job_estimate_id:
                manuf_line = self.job_estimate_id.manufacture_line.filtered(
                    lambda m: m.project_scope_id.id == line.project_scope.id and
                              m.section_id.id == line.section_name.id and
                              m.final_finish_good_id.id == line.finish_good_id.id)
            elif self.cost_sheet:
                manuf_line = self.cost_sheet.manufacture_line.filtered(
                    lambda m: m.project_scope.id == line.project_scope.id and
                              m.section_name.id == line.section_name.id and
                              m.final_finish_good_id.id == line.finish_good_id.id)
            if self.job_estimate_id:
                for job_line in manuf_line:
                    self.job_estimate_id.manufacture_line = [(2, job_line.id)]
                line.to_manuf_line_id.update({
                    'cascaded': False,
                })
            else:
                for job_line in manuf_line:
                    self.cost_sheet.manufacture_line = [(2, job_line.id)]
                line.cost_manuf_line_id.update({
                    'cascaded': False,
                })


class JobCascadeWizardLine(models.TransientModel):
    _name = 'job.cascade.wizard.line'
    _description = "BOQ Cascade Manufacture Line"
    _order = 'sequence'

    job_cascade_id = fields.Many2one("job.cascade.wizard", string="BOQ Cascade Wizard")
    to_manuf_line_id = fields.Many2one("to.manufacture.line", string="Line id")
    cost_manuf_line_id = fields.Many2one("cost.manufacture.line", string="Line id")
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    is_active = fields.Boolean(string="Active", default=True)
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', required=True)
    section_name = fields.Many2one('section.line', string='Section', required=True)
    final_finish_good_id = fields.Many2one('product.product', 'Final Finish Goods')
    finish_good_id = fields.Many2one('product.product', 'Finish Goods', required=True)
    finish_good_id_template = fields.Many2one(related='finish_good_id.product_tmpl_id', string='Finish Goods Template',
                                              readonly=True)
    bom_id = fields.Many2one('mrp.bom', 'BOM', required=True)
    product_qty = fields.Float('Quantity', default=1.00)
    is_child = fields.Boolean('Is Child')

    @api.depends('job_cascade_id.job_cascade_line_ids', 'job_cascade_id.job_cascade_line_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.job_cascade_id.job_cascade_line_ids:
                no += 1
                l.sr_no = no
