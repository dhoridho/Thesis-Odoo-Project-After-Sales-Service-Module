/**
 * awesome_theme action manager
 */
odoo.define('awesome_theme_pro.ActionManager', function(require) {
    "use strict";

    var core = require('web.core');
    var ActionManager = require('web.ActionManager');
    var AwsomeMultiTabPage = require('awesome_theme_pro.multi_tab_page')
    var dom = require('web.dom');
    var Widget = require('web.Widget');

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var dom = require('web.dom');
    var Widget = require('web.Widget');
    var BackendSetting = require('awesome_theme_pro.backend_setting')
    var web_client = require('web.web_client');

    var Context = require('web.Context');
    var pyUtils = require('web.py_utils');

    var _t = core._t;

    var AwesomeThemeActionManager = ActionManager.include({

        template: "awesome_theme_pro.action_manager",
        multi_tab_widget: undefined,
        awesome_current_controller: undefined,
        action_controller_statck: {},
        action_map: {},

        // custom events
        custom_events: _.extend({}, ActionManager.prototype.custom_events, {
            "awesome_tab_restore_action": "_awesome_tab_restore_action",
            "awesome_remove_action": "_awesome_remove_action"
        }),

        init: function() {
            this._super.apply(this, arguments)
            this.enable_multi_tab = BackendSetting.settings.multi_tab_mode
        },

        /*
         * add the pager header and page footer
         */
        start: function() {
            // return if it is not multi tab mode
            if (!this.enable_multi_tab) {
                return this._super.apply(this, arguments)
            }

            var self = this;
            return this._super.apply(this, arguments).then(function() {
                self.multi_tab_widget = new AwsomeMultiTabPage(self);
                self.multi_tab_widget.appendTo(self.$('.awesome_multi_tab_container'));
            })
        },

        show_awesome_tab: function() {
            this.$('.awesome_multi_tab').removeClass('d-none')
        },

        /**
         * just restore the action
         * @param {} action_info 
         */
        _awesome_tab_restore_action: function(event) {
            var action_info = event.data

            var action = action_info.action
            if (this.currentDialogController) {
                this._closeDialog();
            } else {
                var actionID = action.jsID;
                this._awesome_resotre_action_last_controller(actionID);
            }
        },

        /**
         * actionID
         * @param {*} actionID 
         */
        _awesome_resotre_action_last_controller: function(actionID, options) {
            var controllerStatck = this.action_controller_statck[actionID]
            if (controllerStatck.length > 0) {
                var controller = undefined;
                if (options && options.clear_breadcrumbs) {
                    controller = controllerStatck[0]
                } else {
                    controller = controllerStatck[controllerStatck.length - 1]
                }
                this._restoreController(controller, true);
            }
        },

        /**
         * get the current action
         * @param {g} event 
         */
        get_current_action: function(event) {
            var current_controller = this.getCurrentController()
            if (current_controller) {
                return this.actions[current_controller.actionID];
            } else {
                return undefined;
            }
        },

        /**
         * rewrite ite to save the action info, check the action exits
         */
        _executeAction: function(action, options) {

            // return if it is not multi tab mode
            if (!this.enable_multi_tab) {
                return this._super.apply(this, arguments)
            } else {

                if (action.refAction) {
                    options["ignore_tab"] = true
                }

                var self = this;
                var action_info = this.multi_tab_widget.get_action_info(action, options);
                if (action_info) {
                    var actionID = action_info.action.jsID;
                    this._awesome_resotre_action_last_controller(actionID, options);
                    this.multi_tab_widget.active_tab(actionID);
                    // return the action info
                    return Promise.resolve(action_info);
                } else {
                    var prom = this._super.apply(this, arguments)
                    if (prom) {
                        prom.then(function() {
                            if (!options.ignore_tab && action.target != 'new') {
                                if (self.multi_tab_widget) {
                                    options['ignore_tab'] = true
                                    var controllerId = action.controllerID;
                                    var controller = self.controllers[controllerId]
                                    var title = controller.title
                                    options.title = title
                                    action.tab_title = title
                                    self.multi_tab_widget.on_excute_action(action, options);
                                }
                            }
                        })
                    }
                    return prom || Promise.resolve();
                }
            }
        },

        /**
         * rewrite to change the controller location
         */
        _appendController: function(controller) {

            dom.append(this.$('.awesome_controller_container'), controller.widget.$el, {
                in_DOM: this.isInDOM,
                callbacks: [{ widget: controller.widget }],
            });

            if (controller.scrollPosition) {
                this.trigger_up('scrollTo', controller.scrollPosition);
            }

            // return if it is not multi tab mode
            if (this.enable_multi_tab) {
                // update the currnet controller
                this.currentController = controller
            }
        },

        /**
         * bind the controller stack with action
         * @param {*} action_id 
         */
        _awesomeGetControllerStack: function(actioID) {
            // return if it is not multi tab mode
            if (!this.enable_multi_tab) {
                return this.controllerStack;
            } else {
                if (actioID in this.action_controller_statck) {
                    return this.action_controller_statck[actioID]
                } else {
                    this.action_controller_statck[actioID] = []
                }
                return this.action_controller_statck[actioID]
            }
        },

        /**
         * bind the controller stack with action
         * @param {*} action_id 
         */
        _awesomeGetControllerStack: function(actioID, options) {
            // return if it is not multi tab mode
            if (!this.enable_multi_tab) {
                return this.controllerStack;
            } else {
                var action = this.action_map[actioID]
                if (actioID in this.action_controller_statck) {
                    if (action.refAction) {
                        return this.action_controller_statck[action.refAction.jsID];
                    } else {
                        return this.action_controller_statck[actioID]
                    }
                } else {
                    // check if it is menu click
                    if (action.refAction) {
                        return this.action_controller_statck[action.refAction.jsID];
                    } else {
                        // use the current action stack
                        this.action_controller_statck[actioID] = []
                    }
                }
                return this.action_controller_statck[actioID]
            }
        },

        /**
         * Returns the last controller in the controllerStack, i.e. the currently
         * displayed controller in the main window (not in a dialog), and
         * null if there is no controller in the stack.
         *
         * @returns {Object|null}
         */
        getCurrentController: function() {

            // return if it is not multi tab mode
            if (!this.enable_multi_tab) {
                return this._super.apply(this, arguments)
            }

            return this.currentController;
        },

        /**
         * change the controller stack to keep action infos
         */
        _pushController: function(controller, options) {

            var action = this.actions[controller.actionID];

            // return if it is not multi tab mode
            if (!this.enable_multi_tab) {

                var self = this;

                // detach the current controller
                if (options &&
                    options.viewType == 'form' &&
                    (options.context.pop_up_form || BackendSetting.settings.form_style == 'awesome_popup') &&
                    action.views.length > 1) {
                    controller.widget.$el.addClass('awesome_pop_form');
                }

                // detach the current controller
                if (!options || options.change_current_controller) {
                    this._detachCurrentController();
                }

                // push the new controller to the stack at the given position, and
                // destroy controllers with an higher index
                var toDestroy = this.controllerStack.slice(controller.index);
                // reject from the list of controllers to destroy the one that we are
                // currently pushing, or those linked to the same action as the one
                // linked to the controller that we are pushing
                toDestroy = _.reject(toDestroy, function(controllerID) {
                    return controllerID === controller.jsID ||
                        self.controllers[controllerID].actionID === controller.actionID;
                });
                this._removeControllers(toDestroy);

                this.controllerStack = this.controllerStack.slice(0, controller.index);
                this.controllerStack.push(controller.jsID);

                // append the new controller to the DOM
                if (!options || options.change_current_controller) {
                    this._appendController(controller);
                }

                // restore the control pannel
                if (controller.widget.withControlPanel) {
                    var props = controller.widget._controlPanelWrapper.props;
                    props.isActive = true
                    controller.widget._controlPanelWrapper.update(props)
                }

                // notify the environment of the new action
                this.trigger_up('current_action_updated', {
                    action: this.getCurrentAction(),
                    controller: controller,
                });

                // close all dialogs when the current controller changes
                core.bus.trigger('close_dialogs');

                // toggle the fullscreen mode for actions in target='fullscreen'
                this._toggleFullscreen();
            } else {
                var self = this;
                if (controller.widget.pop_up_form) {
                    controller.widget.$el.addClass('awesome_pop_form');
                } else {
                    if (!options || options.change_current_controller) {
                        // this._detachCurrentController();
                        // detach all the controller
                        this._detachCurrentController();
                    }
                }

                // get the action controller stack, rewrite here, add by awsome odoo
                var actioID = controller.actionID
                var controller_stack = this._awesomeGetControllerStack(actioID)

                // reject from the list of controllers to destroy the one that we are
                // currently pushing, or those linked to the same action as the one
                // linked to the controller that we are pushing
                var action = this.action_map[actioID]
                if (!action.refAction) {
                    // push the new controller to the stack at the given position, and
                    // destroy controllers with an higher index
                    var toDestroy = controller_stack.slice(controller.index);
                    toDestroy = _.reject(toDestroy, function(controllerID) {
                        return controllerID === controller.jsID ||
                            self.controllers[controllerID].actionID === controller.actionID;
                    });
                    this._removeControllers(toDestroy);

                    // controller stack bind with action 
                    controller_stack = controller_stack.slice(0, controller.index);
                }

                controller_stack.push(controller.jsID);

                // record controller stacks
                this.action_controller_statck[actioID] = controller_stack

                // append the new controller to the DOM, add the action
                if (!options || options.change_current_controller) {
                    this._appendController(controller);
                }

                // restore the control pannel
                if (controller.widget.withControlPanel) {
                    var props = controller.widget._controlPanelWrapper.props;
                    props.isActive = true
                    controller.widget._controlPanelWrapper.update(props)
                }

                // notify the environment of the new action
                this.trigger_up('current_action_updated', {
                    action: this.getCurrentAction(),
                    controller: controller,
                });

                // close all dialogs when the current controller changes
                core.bus.trigger('close_dialogs');

                // toggle the fullscreen mode for actions in target='fullscreen'
                this._toggleFullscreen();
            }

            // add the awesome show to slide it
            controller.widget.$el.addClass('awesome_show');
        },

        /**
         * only can remove action from tab, bu from the breadcrumb
         */
        _removeController: function(actionID) {

            // return if it is not multi tab mode
            if (!this.enable_multi_tab) {
                return this._super.apply(this, arguments)
            }

            var action = this.actions[actionID];
            var controller = this.controllers[action.controllerID];
            var controllerStack = this._awesomeGetControllerStack()
            if (controllerStack.length > 1) {
                delete this.controllers[action.controllerID];
                delete controllerStatck[controller.controllerID];
                controller.widget.destroy();
            } else {
                // remove portal content
                controller.widget._controlPanelWrapper.props.isActive = false;
                // just detach it, if need delete only can from the action tab
                controller.widget.detach();
            }
        },

        /**
         * remove the action
         * @param {*} actionID 
         */
        _awesome_remove_action: function(event) {
            var action_info = event.data

            var self = this;
            var call_back = action_info.call_back
            this.clearUncommittedChanges().then(function() {
                var action = action_info.action;
                var actionID = action.jsID;
                var controllerStack = self._awesomeGetControllerStack(actionID);
                // remove all the controller
                _.each(controllerStack, function(jsID) {
                    // need to check is editing?
                    if (self.controllers[jsID]) {
                        if (jsID == self.currentController.jsID) {
                            self.currentController = undefined;
                        }
                        var controller = self.controllers[jsID];
                        delete self.controllers[jsID];
                        if (controller.widget) {
                            controller.widget.destroy();
                        }
                    }
                })
                delete self.actions[actionID];
                delete self.action_map[actionID];
                self.action_controller_statck[actionID] = []
                call_back()
            })
        },


        /**
         * rewrite it to use the right controller stack
         * @private
         */
        _onHistoryBack: function() {

            // return if it is not multi tab mode
            if (!this.enable_multi_tab) {
                return this._super.apply(this, arguments)
            }

            if (this.currentDialogController) {
                this._closeDialog();
            } else {
                var controller = this.getCurrentController()
                var actionID = controller.actionID
                var controllerStack = this._awesomeGetControllerStack(actionID)
                var length = controllerStack.length;
                if (length > 1) {
                    this._restoreController(controllerStack[length - 2]);
                }
            }
        },

        /**
         * restore controller
         */
        _restoreController: function(controllerID) {

            // return if it is not multi tab mode
            if (!this.enable_multi_tab) {
                return this._super.apply(this, arguments)
            }

            var self = this;
            var controller = this.controllers[controllerID];

            // AAB: AbstractAction should define a proper hook to execute code when
            // it is restored (other than do_show), and it should return a promise

            var action = this.actions[controller.actionID];
            var def;
            if (action.on_reverse_breadcrumb) {
                def = action.on_reverse_breadcrumb();
            }

            return Promise.resolve(def).then(function() {
                return Promise.resolve(controller.widget.do_show()).then(function() {
                    // change by awsome, use action controller stack
                    var controller_stack = self.action_controller_statck[action.jsID]
                    var index = _.indexOf(controller_stack, controllerID);
                    self._pushController(controller, index);
                });
            });
        },

        /**
         * Executes actions of type 'ir.actions.client'.
         *
         * @private
         * @param {Object} action the description of the action to execute
         * @param {string} action.tag the key of the action in the action_registry
         * @param {Object} options @see doAction for details
         * @returns {Promise} resolved when the client action has been executed
         */
        _executeClientAction: function(action, options) {

            // return if it is not multi tab mode
            if (!this.enable_multi_tab) {
                return this._super.apply(this, arguments)
            }

            var self = this;
            var ClientAction = core.action_registry.get(action.tag);
            if (!ClientAction) {
                console.error("Could not find client action " + action.tag, action);
                return Promise.reject();
            }
            if (!(ClientAction.prototype instanceof Widget)) {
                // the client action might be a function, which is executed and
                // whose returned value might be another action to execute
                var next = ClientAction(this, action);
                if (next) {
                    return this.doAction(next, options);
                }
                return Promise.resolve();
            }
            if (!(ClientAction.prototype instanceof AbstractAction)) {
                console.warn('The client action ' + action.tag + ' should be an instance of AbstractAction!');
            }

            var controllerID = _.uniqueId('controller_');

            // rewrite here
            var index = this._getControllerStackIndex(options, action);
            // var index = this._getControllerStackIndex(options);

            var controllerStack = this._awesomeGetControllerStack(action.jsID)
            options.breadcrumbs = this._getBreadcrumbs(controllerStack.slice(0, index));
            options.controllerID = controllerID;
            var widget = new ClientAction(this, action, options);
            var controller = {
                actionID: action.jsID,
                index: index,
                jsID: controllerID,
                title: widget.getTitle(),
                widget: widget,
            };
            this.controllers[controllerID] = controller;
            // current controller id
            action.controllerID = controllerID;
            // execute action
            var prom = this._executeAction(action, options);
            prom.then(function(old_action_info) {
                if (old_action_info) {
                    return
                }
                self._pushState(controllerID, {});
            });
            return prom;
        },

        /**
         * add the exectue in dialog flag
         * @param {} action 
         * @param {*} options 
         * @returns 
         */
        _executeActionInDialog: function(action, options) {
            // return if it is not multi tab mode
            var controller = this.controllers[action.controllerID];
            controller.executeInDialog = true
            action.executeInDialog = true
            return this._super.apply(this, arguments)
        },

        _detachCurrentController: function() {
            var currentController = this.getCurrentController();
            if (currentController) {
                // set the control pannel deactive
                dom.detach([{ widget: currentController.widget }]);
                // remove the awesome show class
                currentController.widget.$el.removeClass('awesome_show')
                var self = this
                _.defer(function() {
                    if (currentController.widget.withControlPanel) {
                        var props = currentController.widget._controlPanelWrapper.props;
                        props.isActive = false
                        currentController.widget._controlPanelWrapper.update(props)
                        currentController.scrollPosition = self._getScrollPosition();
                    }
                })
            }
        },

        /**
         * detach all the controller
         * @param {*} actionID 
         */
        _detachAllController: function(actionID) {
            var self = this
            var controller_stack = this._awesomeGetControllerStack(actionID);
            _.each(controller_stack, function(jsID) {
                var currentController = this.controllers[jsID];
                // if detached
                if (!controller_stack.widget.$el.parent()) {
                    return
                }
                // set the control pannel deactive
                dom.detach([{ widget: currentController.widget }]);
                currentController.widget.$el.removeClass('awesome_show')

                _.defer(function() {
                    if (currentController.withControlPanel) {
                        var props = currentController.widget._controlPanelWrapper.props;
                        props.isActive = false
                        currentController.widget._controlPanelWrapper.update(props)
                        currentController.scrollPosition = self._getScrollPosition();
                    }
                })
            })
        },

        /**
         * rewrite it to keep the action in action map
         *
         * @param {Object} action
         * @param {Object} options see @doAction options
         */
        _preprocessAction: function(action, options) {
            this._super.apply(this, arguments);
            this.action_map[action.jsID] = action;
        },

        /**
         * Executes actions of type 'ir.actions.server'.
         *
         * @private
         * @param {Object} action the description of the action to execute
         * @param {integer} action.id the db ID of the action to execute
         * @param {Object} [action.context]
         * @param {Object} options @see doAction for details
         * @returns {Promise} resolved when the action has been executed
         */
        _executeServerAction: function(action, options) {
            var menu_click = action.menu_click
            var self = this;
            var runDef = this._rpc({
                route: '/web/action/run',
                params: {
                    action_id: action.id,
                    context: action.context || {},
                },
            });
            return this.dp.add(runDef).then(function(action) {
                action = action || { type: 'ir.actions.act_window_close' };
                action.menu_click = menu_click
                return self.doAction(action, options);
            });
        },


        /**
         * rewrite this function to add ref action
         */
        _handleAction: function(action, options) {

            // return if it is not multi tab mode
            if (!this.enable_multi_tab) {
                return this._super.apply(this, arguments)
            }

            var action_info = this.multi_tab_widget.get_action_info(action, options);
            if (action_info) {
                var actionID = action_info.action.jsID;

                // remove the action do not equal the action
                var toDestroy = []
                var controller_stack = this._awesomeGetControllerStack(actionID)
                for (var i = controller_stack.length - 1; i >= 0; i--) {
                    var controller_id = controller_stack[i];
                    var controller = this.controllers[controller_id];
                    var actioID = controller.actionID
                    var tmp_action = this.action_map[actioID]
                    if (tmp_action.id != action.id) {
                        toDestroy.push(controller_id);
                    } else {
                        // controller stack bind with action 
                        controller_stack = controller_stack.slice(0, i + 1);
                        this.action_controller_statck[actioID] = controller_stack
                        break;
                    }
                }
                this._removeControllers(toDestroy);

                this._awesome_resotre_action_last_controller(actionID);
                this.multi_tab_widget.active_tab(actionID);

                // return the action info
                return Promise.resolve(action_info);
            } else {
                if (!action.menu_click && !options.force_new_tab) {
                    var refAction = this.getCurrentAction()
                    action.refAction = refAction
                }

                return this._super.apply(this, arguments);
            }
        },
    })

    return AwesomeThemeActionManager
});