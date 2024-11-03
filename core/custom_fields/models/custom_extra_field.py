# -*- coding: utf-8 -*-

from lxml import etree
from lxml.builder import E

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

STANDARDPORTALCLASS = "col-12 col-md-6"
LABELCLASS = "col-form-label col-auto s_website_form_label customw_200"
LABELINNERCLASS = "s_website_form_label_content"
LABELREQUIREDMARK = "s_website_form_mark"
INNERDIVCLASS = "col-sm col-xs-12"
INNEROUTERDIVCLASS = "row s_col_no_resize s_col_no_bgcolor"
OUTERDIVCLASS = "form-group col-12 s_website_form_field type_visibility_depend"
FIELDSINPUTS = {
    "char": {"type" : "text", "class": "s_website_form_input form-control"},
    "integer": {"type" : "number", "class": "s_website_form_input form-control"},
    "float": {"type" : "number", "class": "s_website_form_input form-control", "step": "0.01"},
    "date": {"type" : "date", "class": "s_website_form_input form-control"},
    "datetime": {"type" : "datetime-local", "class": "s_website_form_input form-control"},
    "boolean": {"type" : "checkbox", "class": "s_website_form_input"},
    "text": {"class": "s_website_form_input form-control"},
    "html": {"class": "s_website_form_input form-control"},
    "selection": {"class": "s_website_form_input form-control"},
    "many2one": {"class": "s_website_form_input form-control"},
    "binary": {"type" : "file", "class": "s_website_form_input form-control"},
}


class custom_extra_field(models.AbstractModel):
    """
    The model to introduce custom fields classifier (needed to be extended in the corresponding models)

    Required model columns for inheritance:
     * _linked_model - char (e.g. 'crm.lead')
     * _field_code - char (e.g. 'ld') - used for generating custom field name (for the case of 'inherits')
     * _type_field - char (e.g. 'custom_type_id')
     * _type_field_model - char (e.g. 'lead.custom.type')
     * _portal_object_name - char (e.g. 'task')
     * _backend_views - xml_ids of dummy backend views (e.g. "opportunity_custom_fields.crm_lead_view_form_dummy")
     * _portal_views - xml_ids of dummy portal template views
     * _input_views - xml_ids of dummy website pages views
     * _extra_input_label_style - str - the added class for label

    Optional model columns:
     * _portal_classes - element class for each place on a website page

    Required fields for inherited models:
     * types_ids - m2m for custom types classifier

    Required xml places:
     * for backend - <group name="group_custom_fields"/>
     * for input - <div id="custom_input"/>

    Extra info:
     * in case you indicate _input_views, your module should have somehow dependance on website_form
     * in case you indicate _portal_views, your module should have somehow dependance on website
    """
    _name = "custom.extra.field"
    _description = "Custom Field"
    _field_code = False
    _linked_model = False
    _type_field = False
    _type_field_model = False
    _portal_object_name = False
    _backend_views = []
    _portal_views = []
    _input_views = []
    _portal_classes = {"after_descri": "col-12 col-md-12"}
    _extra_input_label_style = ""

    @api.model
    def _return_res_model(self):
        """
        Return available models for many2one
        """
        model_ids =  self.env['ir.model'].sudo().search([
            ('access_ids.group_id.users', '=', self.env.uid),
            ('transient', '=', False),
        ])
        return model_ids.mapped(lambda rec: (rec.model, rec.name))

    @api.model    
    def _default_sequence(self):
        """
        Default method for sequence
        """
        try:
            last_line = self.search([], limit=1, order='sequence desc')
        except:
            last_line = 0
        return last_line and last_line.sequence + 1 or 1


    def _inverse_active(self):
        """
        Inverse method for active
        """
        pass

    def _inverse_ttype(self):
        """
        Inverse method for Ttype
        """
        pass

    @api.constrains('ttype', 'input_placement')
    def _check_no_datetime_as_input(self):
        """
        Constraint to make sure is not selected as input
        """
        for cfield in self:
            if cfield.input_placement and cfield.ttype == "datetime":
                raise ValidationError(_("Datetime fields are not available for website input forms"))

    name = fields.Char(
        'Field Label',
        required=True,
    )
    ttype = fields.Selection(
        [
            ('char', 'Single Line Text'),
            ('text', 'Simple Text'),
            ('html', 'Rich Text'),
            ('integer', 'Integer Number'),
            ('float', 'Float Number'),
            ('selection', 'Dropdown'),
            ('boolean', 'Checkbox'),
            ('date', 'Date'),
            ('datetime', 'Date and time'),
            ('many2one', 'Reference (Many2one)'),
            ('binary', 'Binary'),
        ],
        string='Type',
        required=True,
        inverse=_inverse_ttype,
    )
    res_model = fields.Selection(
        _return_res_model,
        string="Related to",
    )
    sel_options_ids = fields.One2many(
        'custom.extra.field.selection',
        'field_id',
        string='Selection Options',
        domain=lambda self: [('model', '=', self._name)],
        auto_join=True,
        copy=False,
    )
    placement = fields.Selection(
        [("group_custom_fields", "Custom Tab"),],
        string="Backend Form View Placement",
        default="group_custom_fields",
    )
    portal_placement = fields.Selection(
        [("after_descri", "At the end"),],
        string="Portal Page Placement",
    )
    input_placement = fields.Selection(
        [("group_custom_fields", "At the end"),],
        string="Input Form Placement",
    )
    sequence = fields.Integer(
        'Sequence',
        default=_default_sequence,
        required=True,
    )
    field_id = fields.Many2one(
        "ir.model.fields",
        string="Field",
        copy=False,
    )
    binary_field_id = fields.Many2one(
        "ir.model.fields",
        string="Binary Field (File Name)",
        copy=False,
    )
    required = fields.Boolean(string="Required to enter a value")
    active = fields.Boolean(
        string="Active",
        default=True,
        help="Uncheck to archive this custom field",
        inverse=_inverse_active,
        copy=False,
    )

    _order = 'sequence, id'

    @api.model
    def create(self, values):
        """
        Overwriting to create a new instance of ir.model.fields and update view

        Methods:
         * _prepare_new_field() - to get values of created field
         * _generate_xml()
        """
        custom_field_id = super(custom_extra_field, self).create(values)
        field_id, binary_field_id = custom_field_id._prepare_new_field()
        custom_field_id.field_id = field_id
        custom_field_id.binary_field_id = binary_field_id
        custom_field_id.sudo()._generate_xml()
        return custom_field_id

    def write(self, values):
        """
        Overwriting to update fields and view

        We update xml each time of write diregarding of made changes, since there are to many cases
        when it should be updated

        Methods:
         * _return_new_field_values
         * _generate_xml()
        """
        custom_field_id = super(custom_extra_field, self).write(values)
        for field in self:
            if field.field_id:
                new_field_values = field.sudo()._return_new_field_values()
                field.field_id.sudo().write(new_field_values)
        self.sudo()._generate_xml()
        return custom_field_id

    def unlink(self):
        """
        Overwritting to delete the fields also and update xml
         Note: we can remove the field only in case it is not within xml

        Methods:
         * _generate_xml()
        """
        field_to_remove = self.mapped("field_id") + self.mapped("binary_field_id")
        custom_field_id = super(custom_extra_field, self).unlink()
        self.sudo()._generate_xml()
        field_to_remove.sudo().unlink()

    ############################ The methods for updating ir fields ####################################################
    def _prepare_new_field(self):
        """
        The method to create a new ir.models.field
         1. In case of related module uninstall, ids start from scratch, so we should make sure name is unique

        Methods:
         * _return_new_field_values()
         * _get_id of ir.model

        Returns:
         * ir.models.field object, ir.models.field object

        Extra info:
         * Binary fields for proper formatting requires filename
         * Expected singleton
        """
        self.ensure_one()
        field_values = self._return_new_field_values()
        # 1
        field_unique_name = "x_oz_{}_{}".format(self._field_code, self.id)
        core_name = field_unique_name
        itera = 0
        while self.env["ir.model.fields"].sudo().search([("name", "=", field_unique_name)], limit=1):
            field_unique_name = "{}_{}".format(core_name, itera)
            itera += 1
        field_values.update({
            "name": field_unique_name,
            "model_id": self.env["ir.model"].sudo()._get_id(self._linked_model),
            "ttype": self.ttype,
            "copied": True,
            "relation": self.ttype in ["many2one"] and self.res_model or False,
        })
        field_id = self.env["ir.model.fields"].sudo().create(field_values)
        binary_field_id = False
        if self.ttype == "binary":
            binary_field_values = {
                "name": field_unique_name + "_filename",
                "model_id": self.env["ir.model"].sudo()._get_id(self._linked_model),
                "ttype": "char",
                "copied": True,
                "field_description": u"{} File Name".format(self.name),
            }
            binary_field_id = self.env["ir.model.fields"].sudo().create(binary_field_values)
        return field_id, binary_field_id

    def _return_new_field_values(self):
        """
        The method to prepare field values

        Methods:
         * return_sel_keys() - to know possible values for selection

        Returns:
         * dict

        Extra info:
         * Expected singleton
        """
        self.ensure_one()
        field_values = {
            "field_description": self.name,
            "selection": self._return_sel_keys(),
        }
        return field_values

    def _return_sel_keys(self):
        """
        The method to apply selection of a field

        Returns:
         * list of typles for selection
         * False if no keys exist

        Extra info:
         * Expected singleton
        """
        self.ensure_one()
        res = False
        if self.sel_options_ids:
            res = str(self.sel_options_ids.mapped(lambda option: (option.key, option.value)))
        return res

    ############################ The methods for updating views ########################################################
    @api.model
    def _generate_xml(self, clean_xml=False):
        """
        Dummy method to be updated in inherited methods to generate backend views

        Args:
         * clean_xml: Boolean - to clean xml of custom fields disregarding their existance

        Extra info:
         * invoke under sudo()
        """
        self._prepare_backend_view_xml(clean_xml)
        self._prepare_portal_view_xml(clean_xml)
        self._prepare_input_view_xml(clean_xml)

    @api.model
    def _prepare_custom_view(self, view, xml_content):
        """
        The method to create new or update existing view

        Args:
         * view - ir.ui.view object
         * xml_content - new arch xml
        """
        xml_content = u"<data>{}</data>".format(xml_content)
        custom_view_name = u'{} custom'.format(view.name)
        custom_view_key = u'{}_xoz'.format(view.id)
        view_vals = {
            'arch': xml_content,
            'arch_fs': False,
            'name': custom_view_name,
            'key': custom_view_key,
            'inherit_id': view.id,
            'mode': "extension",
        }
        existing_view = self.env["ir.ui.view"].search([("key", "=", custom_view_key)], limit=1)
        if existing_view:
            existing_view.with_context(lang=None).write(view_vals)
        else:
            view.with_context(lang=None).copy(view_vals)

    @api.model
    def _prepare_backend_view_xml(self, clean_xml=False):
        """
        The method to prepare the backend view xmls for this object

        Args:
         * clean_xml - bool - to clean xml of custom fields disregarding their existance

        Methods:
         * _return_attrs_based_on_type()
         * _prepare_custom_view()

        To-do:
         * think of searching by XML tags to make sure place exists
        """
        for view_name in self._backend_views:
            view = self.sudo().env.ref(view_name, raise_if_not_found=False)
            if view and view.exists() and view._name == 'ir.ui.view':
                custom_field_ids = clean_xml and self.env[self._name] or self.search([])
                placement_ids = dict(self._fields['placement'].selection).keys()
                xml_content = ""
                for place in placement_ids:
                    xml = []
                    for customom_field in custom_field_ids:
                        if customom_field.placement == place:
                            attrs = customom_field._return_attrs_based_on_type()
                            field_name = customom_field.field_id and customom_field.field_id.name or False
                            if field_name:
                                if customom_field.ttype in ["binary"] and customom_field.binary_field_id:
                                    filename_attrs = {"invisible": "1"}
                                    xml.append(E.field(name=customom_field.binary_field_id.name, **filename_attrs))
                                xml.append(E.field(name=field_name, **attrs))
                                xml.append(E.newline())
                    invisible =  bool(xml) and "0" or "1"
                    gr_label = place in ["details_group_custom_fields"] and _(u"Custom Details") or ""
                    colspan = "1"
                    xml = E.group(E.group(*(xml), invisible=invisible, name=place, string=gr_label),
                                  name=place,
                                  position="replace",
                          )
                    xml_content += etree.tostring(xml, pretty_print=True, encoding="unicode")
                self._prepare_custom_view(view, xml_content)

    def _return_attrs_based_on_type(self):
        """
        The method to construct required / invisible if type is defined

        Returns:
         * dict of attributes

        Extra info:
         * Expected singleton
        """
        attrs = {}
        if self.types_ids:
            invisible = "'invisible' : [('{}', 'not in', {})],".format(self._type_field, self.types_ids.ids,)
            required = ""
            if self.required:
                required = "'required' : [('{}', 'in', {})],".format(self._type_field, self.types_ids.ids,)
            attrs['attrs'] = "{}{}{}{}".format("{", invisible, required, "}")
        elif self.required:
            attrs['required'] = "1"
        if self.ttype in ["binary"] and self.binary_field_id:
            attrs["filename"] = self.binary_field_id.name
        return attrs

    @api.model
    def _prepare_portal_view_xml(self, clean_xml=False):
        """
        The method to construct portal views

        Args:
         * clean_xml: Boolean - to clean xml of custom fields disregarding their existance

        Methods:
         * _prepare_custom_view
        """
        for view_name in self._portal_views:
            view = self.sudo().env.ref(view_name, raise_if_not_found=False)
            if view and view.exists() and view._name == 'ir.ui.view':
                custom_field_ids = clean_xml and self.env[self._name] \
                                   or self.env[self._name].search([("portal_placement", "!=", False)])
                placement_ids = dict(self._fields['portal_placement'].selection).keys()
                xml_content = ""
                for place in placement_ids:
                    final_xml = []
                    for customom_field in custom_field_ids:
                        if customom_field.portal_placement == place:
                            attrs = {}
                            field_name = customom_field.field_id and customom_field.field_id.name or False
                            if field_name:
                                inner_xml = []
                                inner_xml.append(E.strong(u"{}:".format(customom_field.name)))
                                if customom_field.ttype in ["binary"]:
                                    filename_field_name = customom_field.sudo().binary_field_id.name or ""
                                    spanxml = [(E.span({"t-field": "{}.{}".format(
                                                        self._portal_object_name,
                                                        filename_field_name)})
                                               )]
                                    spanxml.append(E.span({"class": "fa fa-download"}))
                                    content_href = "/web/content/{}/#{}/{}/#{}".format(
                                        self._linked_model,
                                        "{" + self._portal_object_name + ".id}",
                                        field_name,
                                        "{" + self._portal_object_name + "." + filename_field_name +"}",
                                    )
                                    inner_xml.append(E.a(*spanxml, {"t-attf-href": content_href, "target": "_blank"}))
                                else:
                                    inner_xml.append(E.span({"t-field": "{}.{}".format(
                                                        self._portal_object_name,
                                                        field_name)})
                                                    )
                                invisible = customom_field.types_ids and "{}.{}.id in {}".format(
                                               self._portal_object_name, self._type_field, customom_field.types_ids.ids,
                                            ) or False
                                attrs['t-if'] = invisible \
                                             and invisible + " and {}.{}".format(self._portal_object_name, field_name) \
                                             or "{}.{}".format(self._portal_object_name, field_name)
                                final_xml.append(E.div(*(inner_xml), attrs))
                    whole_div_attrs = self._portal_classes.get(place) is not None \
                                      and {"class": self._portal_classes.get(place)} \
                                      or {"class": STANDARDPORTALCLASS}
                    xml = E.div(E.div(*(final_xml), whole_div_attrs , id=place),
                                        id=place,
                                        position="replace",
                                     )
                    xml_content += etree.tostring(xml, pretty_print=True, encoding="unicode")
                self._prepare_custom_view(view, xml_content)

    @api.model
    def _prepare_input_view_xml(self, clean_xml=False):
        """
        The method to construct input views
         1. add label
         2. prepare input
         3. prepare inner div
         4. prepare first layer of outer div
         5. prepare outer div

        Methods:
         * _retrieve_type_input
         * _return_label_element
         * _return_input_elememt
         * formbuilder_whitelist of ir.model.fields (NOTE!: dependance of website_form is required!)
         * _prepare_custom_view

        Args:
         * clean_xml: Boolean - to clean xml of custom fields disregarding their existance
        """
        label_custom_class = self._extra_input_label_style and LABELCLASS + self._extra_input_label_style or LABELCLASS
        for view_name in self._input_views:
            view = self.sudo().env.ref(view_name, raise_if_not_found=False)
            if view and view.exists() and view._name == 'ir.ui.view':
                custom_field_ids = clean_xml and self.env[self._name] \
                                   or self.env[self._name].search([("input_placement", "!=", False)])
                whitelist_fields = custom_field_ids.mapped("field_id.name")
                self.env["ir.model.fields"].formbuilder_whitelist(self._linked_model, whitelist_fields)
                placement_ids = dict(self._fields['input_placement'].selection).keys()
                xml_content = ""
                type_input = self._retrieve_type_input()
                if len(type_input):
                    xml_content = etree.tostring(type_input, pretty_print=True, encoding="unicode")
                for place in placement_ids:
                    final_xml = []
                    for customom_field in custom_field_ids:
                        if customom_field.input_placement == place:
                            field_name = customom_field.field_id and customom_field.field_id.name or False
                            if field_name:
                                inner_xml = []
                                # 1
                                label_attrs = {"class": label_custom_class, "for": field_name}
                                label_inner_xml = customom_field._return_label_element()
                                # u"{}".format(customom_field.name)
                                inner_xml.append(E.label(*(label_inner_xml), label_attrs))
                                # 2
                                div_inner_xml = customom_field._return_input_elememt(field_name)
                                # 3
                                inner_div = E.div(*(div_inner_xml), {"class": INNERDIVCLASS})
                                inner_xml.append(inner_div)
                                # 4
                                outerxml = [E.div(*(inner_xml), {"class": INNEROUTERDIVCLASS})]
                                # 5
                                outer_div_class = customom_field.required and customom_field.ttype not in ["boolean"]\
                                                  and OUTERDIVCLASS + " o_website_form_required_custom" \
                                                  or OUTERDIVCLASS
                                final_xml.append(E.div(*(outerxml), {"class": outer_div_class}))

                    xml = E.div(E.div(*(final_xml), id=place), id=place, position="replace",)
                    xml_content += etree.tostring(xml, pretty_print=True, encoding="unicode")

                self._prepare_custom_view(view, xml_content)

    @api.model
    def _retrieve_type_input(self):
        """
        The method to prepare object type input (since it is not custom but an actual field)
         1. Create label
         2. Prepare input
         3. Prepare inner div
         4. prepare first layer of outer div
         5. Prepare outer div

        Methods:
         * formbuilder_whitelist of ir.model.fields (NOTE!: dependance of website_form is required!)

        Returns:
         * xml element
        """
        self.env["ir.model.fields"].formbuilder_whitelist(self._linked_model, [self._type_field])
        # 1
        label_custom_class = self._extra_input_label_style and LABELCLASS + self._extra_input_label_style or LABELCLASS
        label_attrs = {"class": label_custom_class, "for": self._type_field}
        inner_xml = [E.label(_("Type"), label_attrs)]
        # 2
        input_attrs = {"name": self._type_field, "class": "s_website_form_input form-control select_type_input"}
        options_xml = []
        available_types = self.env[self._type_field_model].search([("input_option", "=", True)])
        xml = False
        if available_types:
            for option in available_types:
                option_attrs = {
                    "value": str(option.id),
                    "t-att-selected": " 'selected' if {} == '{}' else null ".format(
                        self._type_field,
                        option.id
                    )
                }
                options_xml.append(E.option(u"{}".format(option.name), option_attrs))
            # 3
            div_inner_xml = [E.select(*(options_xml), input_attrs)]
            inner_div = E.div(*(div_inner_xml), {"class": INNERDIVCLASS})
            inner_xml.append(inner_div)
            # 4
            outerxml = [E.div(*(inner_xml), {"class": INNEROUTERDIVCLASS})]
            # 5
            final_xml = [E.div(*(outerxml), {"class": OUTERDIVCLASS})]
            xml = E.div(E.div(*(final_xml), id="custom_type_field"), id="custom_type_field", position="replace",)
        return xml

    def _return_label_element(self):
        """
        The method to generate spans for divs
        """
        final_xml = []
        final_xml.append(E.span(u"{}".format(self.name), {"class": LABELINNERCLASS}))
        if self.required and self.ttype not in ["boolean"]:
            final_xml.append(E.span((u" *"), {"class": LABELREQUIREDMARK}))
        return final_xml

    def _return_input_elememt(self, field_name):
        """
        The method to construct input xml for this field
         0. copy() for FIELDSINPUTS is requrired! Otherwise we update here global variable
         1. Define required and visibility attributes based on required and types
         2. Generate xml based on type

        Args:
          * field_name - name of ir.model.field

        Returns:
         * list of xml --> should be just xml tag
        """
        div_inner_xml = []
        input_attrs_new = FIELDSINPUTS.get(self.ttype) or FIELDSINPUTS.get("char")
        # 0
        input_attrs = input_attrs_new.copy()
        input_attrs.update({"name": field_name,})
        # 1
        if self.required and not self.ttype in ["boolean"]:
            input_attrs.update({"required": "True"})
        if self.types_ids:
            invisible = "{}".format(",".join(map(str, self.types_ids.ids)),)
            input_attrs.update({"invisible": invisible})
        # 2
        if self.ttype in ["char", "integer", "float", "date", "datetime", "boolean", "binary"]:
            input_attrs.update({"t-att-value": field_name,})
            div_inner_xml.append(E.input("", input_attrs))
        elif self.ttype in ["text", "html"]:
            div_inner_xml.append(E.textarea("", input_attrs))
        elif self.ttype in ["selection"]:
            options_xml = []
            options_xml.append(E.option(u"{}".format(""), {}))
            for option in self.sel_options_ids:
                option_attrs = {
                    "value": option.key,
                    "t-att-selected": " 'selected' if {} == '{}' else null ".format(
                        self.field_id.name,
                        option.key
                    )
                }
                options_xml.append(E.option(u"{}".format(option.value), option_attrs))
            div_inner_xml.append(E.select(*(options_xml), input_attrs))
        elif self.ttype in ["many2one"]:
            options_xml = []
            options_xml.append(E.option(u"{}".format(""), {}))
            options_foreach = etree.fromstring(
                u"""
                <t t-foreach="request.env['{res_model}'].sudo().search([])" t-as="line">
                    <option t-att-value="line.id" t-att-selected="'selected' if {field_name} == line.id else null">
                        <t t-esc="line.name_get()[0][1]"/>
                    </option>
                </t>
                """.format(res_model=self.res_model, field_name=self.field_id.name)
            )
            options_xml.append(options_foreach)
            div_inner_xml.append(E.select(*(options_xml), input_attrs))
        return div_inner_xml
