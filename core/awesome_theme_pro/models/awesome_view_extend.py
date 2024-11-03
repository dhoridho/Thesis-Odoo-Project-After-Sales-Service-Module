# -*- coding: utf-8 -*-

import inspect

from odoo import models, _
from odoo.exceptions import AccessError
from odoo.models import check_method_name


class AwesomeViewExtend(models.Model):
    '''
    awesome view extend
    '''
    _inherit = 'ir.ui.view'

    def _render_template(self, template, values=None, engine='ir.qweb'):
        """
        rewrite to change the title
        :param template:
        :param values:
        :param engine:
        :return:
        """
        if template in ['web.login', 'web.webclient_bootstrap']:
            if not values:
                values = {}
            values["title"] = self.env['ir.config_parameter'].sudo().get_param(
                "awesome_theme_pro.window_default_title", "Awesome Odoo")
        return super(AwesomeViewExtend, self)._render_template(
            template, values=values, engine=engine)

    def _validate_tag_button(self, node, name_manager, node_info):
        '''
        over load this function to support special val save_and_return
        :param node:
        :param name_manager:
        :param node_info:
        :return:
        '''
        name = node.get('name')
        special = node.get('special')
        type_ = node.get('type')
        if special:
            if special not in ('cancel', 'save', 'add', 'save_and_return', 'save_and_notify'):
                self.handle_view_error(_("Invalid special '%(value)s' in button", value=special))
        elif type_:
            if type_ == 'edit':  # list_renderer, used in kanban view
                return
            elif not name:
                self.handle_view_error(_("Button must have a name"))
            elif type_ == 'object':
                func = getattr(type(name_manager.Model), name, None)
                if not func:
                    msg = _(
                        "%(action_name)s is not a valid action on %(model_name)s",
                        action_name=name, model_name=name_manager.Model._name,
                    )
                    self.handle_view_error(msg)
                try:
                    check_method_name(name)
                except AccessError:
                    msg = _(
                        "%(method)s on %(model)s is private and cannot be called from a button",
                        method=name, model=name_manager.Model._name,
                    )
                    self.handle_view_error(msg)
                try:
                    inspect.signature(func).bind(self=name_manager.Model)
                except TypeError:
                    msg = "%s on %s has parameters and cannot be called from a button"
                    self.handle_view_error(msg % (name, name_manager.Model._name), raise_exception=False)
            elif type_ == 'action':
                # logic mimics /web/action/load behaviour
                action = False
                try:
                    action_id = int(name)
                except ValueError:
                    model, action_id = self.env['ir.model.data'].xmlid_to_res_model_res_id(name,
                                                                                           raise_if_not_found=False)
                    if not action_id:
                        msg = _("Invalid xmlid %(xmlid)s for button of type action.", xmlid=name)
                        self.handle_view_error(msg)
                    if not issubclass(self.pool[model], self.pool['ir.actions.actions']):
                        msg = _(
                            "%(xmlid)s is of type %(xmlid_model)s, expected a subclass of ir.actions.actions",
                            xmlid=name, xmlid_model=model,
                        )
                        self.handle_view_error(msg)
                action = self.env['ir.actions.actions'].browse(action_id).exists()
                if not action:
                    msg = _(
                        "Action %(action_reference)s (id: %(action_id)s) does not exist for button of type action.",
                        action_reference=name, action_id=action_id,
                    )
                    self.handle_view_error(msg)

            name_manager.has_action(name)
        elif node.get('icon'):
            description = 'A button with icon attribute (%s)' % node.get('icon')
            self._validate_fa_class_accessibility(node, description)
