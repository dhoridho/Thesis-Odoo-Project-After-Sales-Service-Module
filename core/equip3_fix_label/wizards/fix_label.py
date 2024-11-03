# -*- coding: utf-8 -*-

from odoo import models, fields, api



class FixLabel(models.TransientModel):
    _name = 'fix.label'
    _description = 'Fix Label'

    def get_data(self):
        if self.selection_by_history_or_data == 'data':
            query = '''
                SELECT id, name, field_description, model_id, ttype
                    FROM ir_model_fields
                    WHERE (field_description, model_id) IN (
                        SELECT field_description, model_id
                        FROM ir_model_fields
                        GROUP BY field_description, model_id
                        HAVING COUNT(*) > 1
                    )
                    order by field_description,model_id;
            '''
        if self.selection_by_history_or_data == 'history':
            query = '''
                SELECT id, name, field_description, model_id, ttype
                FROM ir_model_fields
                WHERE is_rename = True
                ORDER BY field_description;
            '''
        self._cr.execute(query)

        values = self._cr.fetchall()
        line_values = []
        for data in values:
            line_values.append((0,0,{
                'fix_label_header_id': self._origin.id,
                'name': data[1],
                'model_id' : data[3],
                'field_description' : data[2],
                'field_description_origin' : data[2],
                'type' : data[4],
                'ir_model_field_id' : data[0],
            }))
        return line_values

    fix_label_line_ids = fields.One2many('fix.label.line', 'fix_label_header_id', string='Fix Label Line Ids')
    selection_by_history_or_data = fields.Selection([('history','History'),
                                                     ('data','Data'),],
                                                     string = "Selection by History or Data")

    mass_edit = fields.Boolean('Mass Edit', default=False)
    notes = fields.Char('Notes', default='when field mass edit is True, it will edit the label field according to the system example: Is approve Button, Is approve Button 2, Is approve Button 3')

    @api.onchange('selection_by_history_or_data')
    def _onchange_selection_by_history_or_data(self):
        if self.selection_by_history_or_data:
            if self.selection_by_history_or_data == 'history':
                data = self.get_data()
                self.fix_label_line_ids = [(5,0,0)]
                self.fix_label_line_ids = data

            if self.selection_by_history_or_data == 'data':
                data = self.get_data()
                self.fix_label_line_ids = [(5,0,0)]
                self.fix_label_line_ids = data


    def confirm(self):
        if self.mass_edit == False:
            for record in self.fix_label_line_ids.filtered(lambda x:x.is_rename == True):
                query = f'''
                    UPDATE ir_model_fields
                        SET
                            field_description = '{record.field_description}',
                            is_rename = True
                        WHERE
                            id = {record.ir_model_field_id.id}
                '''
                self._cr.execute(query)
                self._cr.commit()
        else:
            field_desc = self.fix_label_line_ids[0].field_description
            number = 1
            for record in self.fix_label_line_ids:
                if record.field_description == field_desc:
                    name_combine = str(record.field_description) + ' ' + str(number)
                    query = f''' UPDATE ir_model_fields
                             SET
                                 field_description = '{name_combine}',
                                 is_rename = True
                             WHERE
                                 id = {record.ir_model_field_id.id}
                     '''
                    self._cr.execute(query)
                    self._cr.commit()
                    number += 1

                else:
                    number = 1
                    field_desc = record.field_description
                    name_combine = str(record.field_description) + ' ' + str(number)
                    query = f''' UPDATE ir_model_fields
                             SET
                                 field_description = '{name_combine}',
                                 is_rename = True
                             WHERE
                                 id = {record.ir_model_field_id.id}
                     '''
                    self._cr.execute(query)
                    self._cr.commit()
                    number += 1
        return {
            'type' : 'ir.actions.act_url',
            'url' : '/web/clear_cache/%d' % self.env.user.id,
            'target' : 'self'
            }


class FixLabelLine(models.TransientModel):
    _name = 'fix.label.line'
    _description = 'Fix Label Line'

    fix_label_header_id = fields.Many2one('fix.label', string='Fix Label Header ID')
    name = fields.Char(string='name')
    model_id = fields.Many2one('ir.model',string='Model')
    field_description = fields.Char(string='Field Description')
    field_description_origin = fields.Char(string='Field Description Origin')
    type = fields.Char(string='Type')
    ir_model_field_id = fields.Many2one('ir.model.fields',string='Ir Model Field ID')
    is_rename = fields.Boolean('Is Rename',compute='change_field_description', default=False)

    @api.depends('field_description')
    def change_field_description(self):
        for rec in self:
            if rec.field_description != rec.field_description_origin:
                rec.is_rename = True
            else:
                rec.is_rename = False
