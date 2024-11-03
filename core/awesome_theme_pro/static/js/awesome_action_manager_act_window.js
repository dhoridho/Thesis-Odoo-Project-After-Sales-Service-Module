odoo.define('awesome_theme_pro.ActWindowActionManager', function (require) {
    "use strict";

    var ActionManager = require('web.ActionManager');
    var config = require('web.config');
    var BackendSetting = require('awesome_theme_pro.backend_setting')

    require('web.ActWindowActionManager');
    require('awesome_theme_pro.ActionManager')

    ActionManager.include({

        init: function () {
            this._super.apply(this, arguments)
            this.enable_multi_tab = BackendSetting.settings.multi_tab_mode
        },

        is_window_action_manager: function() {
            return true;
        },

        _createViewController: function (action, viewType, viewOptions, options) {
            
            if (!this.enable_multi_tab) {
                return this._super.apply(this, arguments)
            }
            
            var self = this;
            var viewDescr = _.findWhere(action.views, { type: viewType });
            if (!viewDescr) {
                // the requested view type isn't specified in the action (e.g.
                // action with list view only, user clicks on a row in the list, it
                // tries to switch to form view)
                return Promise.reject();
            }

            options = options || {};
            var index = options.index || 0;
            var controllerID = options.controllerID || _.uniqueId('controller_');
            var controller = {
                actionID: action.jsID,
                className: 'o_act_window', // used to remove the padding in dialogs
                index: index,
                jsID: controllerID,
                viewType: viewType,
                action: action
            };
            Object.defineProperty(controller, 'title', {
                get: function () {
                    // handle the case where the widget is lazy loaded
                    return controller.widget ?
                        controller.widget.getTitle() :
                        (action.display_name || action.name);
                },
            });
            this.controllers[controllerID] = controller;

            if (!options.lazy) {
                // build the view options from different sources
                var controller_stack = []
                if (!action.refAction) {
                    controller_stack = this._awesomeGetControllerStack(action.jsID)
                } else {
                    controller_stack = this._awesomeGetControllerStack(action.refAction.jsID)
                }
                
                var flags = action.flags || {};
                viewOptions = _.extend({}, flags, flags[viewType], viewOptions, {
                    action: action,
                    breadcrumbs: this._getBreadcrumbs(controller_stack.slice(0, index)),
                    // pass the controllerID to the views as an hook for further
                    // communication with trigger_up
                    controllerID: controllerID,
                });
                var rejection;
                var view = new viewDescr.Widget(viewDescr.fieldsView, viewOptions);
                var def = new Promise(function (resolve, reject) {
                    rejection = reject;
                    view.getController(self).then(function (widget) {
                        if (def.rejected) {
                            // the promise has been rejected meanwhile, meaning that
                            // the action has been removed, so simply destroy the widget
                            widget.destroy();
                        } else {
                            controller.widget = widget;
                            resolve(controller);
                        }
                    }).guardedCatch(reject);
                });
                // Need to define an reject property to call it into _destroyWindowAction
                def.reject = rejection;
                def.guardedCatch(function () {
                    def.rejected = true;
                    delete self.controllers[controllerID];
                });
                action.controllers[viewType] = def;
            } else {
                action.controllers[viewType] = Promise.resolve(controller);
            }
            return action.controllers[viewType];
        },

        /**
         * change the controller stack source
         * @param {*} options 
         */
        _getControllerStackIndex: function (options, action) {
            if (!this.enable_multi_tab) {
                var index;
                if ('index' in options) {
                    index = options.index;
                } else if (options.clear_breadcrumbs) {
                    index = 0;
                } else if (options.replace_last_action) {
                    index = this.controllerStack.length - 1;
                } else {
                    index = this.controllerStack.length;
                }
                return index;
            } else {
                var index;
                if (options["index"]) {
                    index = options.index;
                } else if (options.clear_breadcrumbs) {
                    index = 0;
                } else if (options.replace_last_action) {
                    var controllerStack = this._awesomeGetControllerStack(action.jsID)
                    index = controllerStack.length - 1;
                } else {
                    var controllerStack = this._awesomeGetControllerStack(action.jsID)
                    index = controllerStack.length;
                }
                return index;
            }
        },

        _onBreadcrumbClicked: function (ev) {
            ev.stopPropagation();
            this._restoreController(ev.data.controllerID);
        },

        /**
         * Handles the switch from a controller to another (either inside the same
         * window action, or from a window action to another using the breadcrumbs).
         *
         * @private
         * @param {Object} controller the controller to switch to
         * @param {Object} [viewOptions]
         * @return {Promise} resolved when the new controller is in the DOM
         */
        /**
         * Handles the switch from a controller to another (either inside the same
         * window action, or from a window action to another using the breadcrumbs).
         *
         * @private
         * @param {Object} controller the controller to switch to
         * @param {Object} [viewOptions]
         * @return {Promise} resolved when the new controller is in the DOM
         */
         _switchController: function (action, viewType, viewOptions) {
            if (!this.enable_multi_tab) {
                var self = this;
                var view = _.findWhere(action.views, { type: viewType });
                if (!view) {
                    // can't switch to an unknown view
                    return Promise.reject();
                }
                var currentController = this.getCurrentController();
                var index;
                if (!currentController || currentController.actionID !== action.jsID) {
                    // the requested controller is from another action, so we went back
                    // to a previous action using the breadcrumbs
                    var controller = _.findWhere(this.controllers, {
                        actionID: action.jsID,
                        viewType: viewType,
                    });
                    index = _.indexOf(this.controllerStack, controller.jsID);
                } else {
                    // the requested controller is from the same action as the current
                    // one, so we either
                    //   1) go one step back from a mono record view to a multi record
                    //      one using the breadcrumbs
                    //   2) or we switched from a view to another  using the view
                    //      switcher
                    //   3) or we opened a record from a multi record view
                    if (view.multiRecord) {
                        // cases 1) and 2) (with multi record views): replace the first
                        // controller linked to the same action in the stack
                        index = _.findIndex(this.controllerStack, function (controllerID) {
                            return self.controllers[controllerID].actionID === action.jsID;
                        });
                    } else if (!_.findWhere(action.views, { type: currentController.viewType }).multiRecord) {
                        // case 2) (with mono record views): replace the last
                        // controller by the new one if they are from the same action
                        // and if they both are mono record
                        index = this.controllerStack.length - 1;
                    } else {
                        // case 3): insert the controller on the top of the controller
                        // stack
                        index = this.controllerStack.length;
                    }
                }

                var newController = function (controllerID) {
                    var options = {
                        controllerID: controllerID,
                        index: index,
                    };
                    return self
                        ._createViewController(action, viewType, viewOptions, options)
                        .then(function (controller) {
                            return self._startController(controller);
                        });
                };

                var controllerDef = action.controllers[viewType];
                if (controllerDef) {
                    controllerDef = controllerDef.then(function (controller) {
                        if (!controller.widget) {
                            // lazy loaded -> load it now (with same jsID)
                            return newController(controller.jsID);
                        } else {
                            return Promise.resolve(controller.widget.willRestore()).then(function () {
                                viewOptions = _.extend({}, viewOptions, {
                                    breadcrumbs: self._getBreadcrumbs(self.controllerStack.slice(0, index)),
                                    shouldUpdateSearchComponents: true,
                                });
                                return controller.widget.reload(viewOptions).then(function () {
                                    return controller;
                                });
                            });
                        }
                    }, function () {
                        // if the controllerDef is rejected, it probably means that the js
                        // code or the requests made to the server crashed.  In that case,
                        // if we reuse the same promise, then the switch to the view is
                        // definitely blocked.  We want to use a new controller, even though
                        // it is very likely that it will recrash again.  At least, it will
                        // give more feedback to the user, and it could happen that one
                        // record crashes, but not another.
                        return newController();
                    });
                } else {
                    controllerDef = newController();
                }

                return this.dp.add(controllerDef).then(function (controller) {
                    // add context
                    return self._pushController(controller, {
                        "viewType": viewType,
                        "context": action.context,
                        // use this to check need to update the portal
                        "change_current_controller": currentController.jsID != controller.jsID
                    });
                });
            } else {
                var self = this;
                var view = _.findWhere(action.views, { type: viewType });
                if (!view) {
                    // can't switch to an unknown view
                    return Promise.reject();
                }

                // change here
                var controller_stack = this._awesomeGetControllerStack(action.jsID)
                var currentController = this.getCurrentController();
                var index;
                if (!currentController || currentController.actionID !== action.jsID) {
                    // the requested controller is from another action, so we went back
                    // to a previous action using the breadcrumbs
                    var controller = _.findWhere(this.controllers, {
                        actionID: action.jsID,
                        viewType: viewType,
                    });
                    index = _.indexOf(controller_stack, controller.jsID);
                } else {
                    // the requested controller is from the same action as the current
                    // one, so we either
                    //   1) go one step back from a mono record view to a multi record
                    //      one using the breadcrumbs
                    //   2) or we switched from a view to another using the view
                    //      switcher
                    //   3) or we opened a record from a multi record view
                    if (view.multiRecord) {
                        // cases 1) and 2) (with multi record views): replace the first
                        // controller linked to the same action in the stack
                        index = _.findIndex(controller_stack, function (controllerID) {
                            return self.controllers[controllerID].actionID === action.jsID;
                        });
                    } else if (!_.findWhere(action.views, { type: currentController.viewType }).multiRecord) {
                        // case 2) (with mono record views): replace the last
                        // controller by the new one if they are from the same action
                        // and if they both are mono record
                        index = controller_stack.length - 1;
                    } else {
                        // case 3): insert the controller on the top of the controller
                        // stack
                        index = controller_stack.length;
                    }
                }

                var newController = function (controllerID) {
                    var options = {
                        controllerID: controllerID,
                        index: index,
                    };
                    return self
                        ._createViewController(action, viewType, viewOptions, options)
                        .then(function (controller) {
                            return self._startController(controller);
                        });
                };

                var controllerDef = action.controllers[viewType];
                if (controllerDef) {
                    controllerDef = controllerDef.then(function (controller) {
                        if (!controller.widget) {
                            // lazy loaded -> load it now (with same jsID)
                            return newController(controller.jsID);
                        } else {
                            return Promise.resolve(controller.widget.willRestore()).then(function () {
                                viewOptions = _.extend({}, viewOptions, {
                                    breadcrumbs: self._getBreadcrumbs(controller_stack.slice(0, index)),
                                    shouldUpdateSearchComponents: true,
                                });
                                // do not reload
                                if (viewOptions.tabRestore) {
                                    return controller;
                                } else {
                                    return controller.widget.reload(viewOptions).then(function () {
                                        return controller;
                                    });
                                }
                            });
                        }
                    }, function () {
                        // if the controllerDef is rejected, it probably means that the js
                        // code or the requests made to the server crashed.  In that case,
                        // if we reuse the same promise, then the switch to the view is
                        // definitely blocked.  We want to use a new controller, even though
                        // it is very likely that it will recrash again.  At least, it will
                        // give more feedback to the user, and it could happen that one
                        // record crashes, but not another.
                        return newController();
                    });
                } else {
                    controllerDef = newController();
                }

                return this.dp.add(controllerDef).then(function (controller) {
                    // add context
                    return self._pushController(controller, {
                        "viewType": viewType,
                        "context": action.context,
                        "change_current_controller": currentController? currentController.jsID != controller.jsID : true
                    });
                });
            }
        },

        /**
         * Override to handle the case of lazy-loaded controllers, which may be the
         * last controller in the stack, but which should not be considered as
         * current controller as they don't have an alive widget.
         *
         * Note: this function assumes that there can be at most one lazy loaded
         * controller in the stack
         *
         * @override
         */
        getCurrentController: function () {

            if (!this.enable_multi_tab) {
                return this._super.apply(this, arguments)
            }

            var currentController = this.currentController
            var action = currentController && this.actions[currentController.actionID];
            if (action && action.type === 'ir.actions.act_window' && !currentController.widget) {

                // changes
                var controller_stack = this._awesomeGetControllerStack(action.jsID)
                var lastControllerID = controller_stack.pop();
                currentController = _.last(controller_stack)
                controllerStack.push(lastControllerID);

                // var lastControllerID = this.controllerStack.pop();
                // currentController = this._super.apply(this, arguments);
                // this.controllerStack.push(lastControllerID);
            }
            return currentController;
        },


        /**
         * rewrite to use action controller stack
        */
        _executeWindowAction: function (action, options) {

            if (!this.enable_multi_tab) {
                return this._super.apply(this, arguments)
            } else {
                var self = this;
                return this.dp.add(this._loadViews(action)).then(function (fieldsViews) {

                    var views = self._generateActionViews(action, fieldsViews);
                    action._views = action.views; // save the initial attribute
                    action.views = views;
                    action.controlPanelFieldsView = fieldsViews.search;
                    action.controllers = {};

                    // select the current view to display, and optionally the main view
                    // of the action which will be lazyloaded
                    var curView = options.viewType && _.findWhere(views, { type: options.viewType });
                    var lazyView;
                    if (curView) {
                        if (!curView.multiRecord && views[0].multiRecord) {
                            lazyView = views[0];
                        }
                    } else {
                        curView = views[0];
                    }

                    // use mobile-friendly view by default in mobile, if possible
                    if (config.device.isMobile) {
                        if (!curView.isMobileFriendly) {
                            curView = self._findMobileView(views, curView.multiRecord) || curView;
                        }
                        if (lazyView && !lazyView.isMobileFriendly) {
                            lazyView = self._findMobileView(views, lazyView.multiRecord) || lazyView;
                        }
                    }

                    var lazyViewDef;
                    var lazyControllerID;
                    if (lazyView) {
                        // if the main view is lazy-loaded, its (lazy-loaded) controller is inserted
                        // into the controller stack (so that breadcrumbs can be correctly computed),
                        // so we force clear_breadcrumbs to false so that it won't be removed when the
                        // current controller will be inserted afterwards
                        options.clear_breadcrumbs = false;
                        // this controller being lazy-loaded, this call is actually sync
                        lazyViewDef = self._createViewController(action, lazyView.type, {}, { lazy: true })
                            .then(function (lazyLoadedController) {
                                lazyControllerID = lazyLoadedController.jsID;
                                // self.controllerStack.push(lazyLoadedController.jsID);
                                var controller_stack = self._awesomeGetControllerStack(action.jsID)
                                controller_stack.push(lazyLoadedController.jsID);
                            });
                    }
                    return self.dp.add(Promise.resolve(lazyViewDef))
                        .then(function () {
                            var viewOptions = {
                                controllerState: options.controllerState,
                                currentId: options.resID,
                            };
                            var curViewDef = self._createViewController(action, curView.type, viewOptions, {
                                index: self._getControllerStackIndex(options, action),
                            });
                            return self.dp.add(curViewDef);
                        }).then(function (controller) {
                            action.controllerID = controller.jsID;
                            return self._executeAction(action, options);
                        })
                        .guardedCatch(function () {
                            if (lazyControllerID) {
                                var index = self.controllerStack.indexOf(lazyControllerID);
                                self.controllerStack = self.controllerStack.slice(0, index);
                            }
                            self._destroyWindowAction(action);
                        });
                });
            }
        },

        _restoreController: function (controllerID, tabRestore) {

            // return if not multi tab mode
            if (!this.enable_multi_tab) {
                return this._super.apply(this, arguments)
            }

            var self = this;
            var controller = this.controllers[controllerID];
            var action = this.actions[controller.actionID];
            if (action.type === 'ir.actions.act_window') {
                return this.clearUncommittedChanges().then(function () {
                    // AAB: this will be done directly in AbstractAction's restore
                    // function
                    var def = Promise.resolve();
                    if (action.on_reverse_breadcrumb) {
                        def = action.on_reverse_breadcrumb();
                    }
                    return Promise.resolve(def).then(function () {
                        return self._switchController(action, controller.viewType, {
                            tabRestore
                        });
                    });
                });
            }

            return this._super.apply(this, arguments);
        }
    })
})