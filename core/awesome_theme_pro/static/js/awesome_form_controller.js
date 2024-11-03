odoo.define('awesome_theme_pro.FormController', function (require) {
    "use strict";

    var FormController = require('web.FormController');
    const OverLay = require('awesome_theme_pro.overlay');
    var BackendSetting = require('awesome_theme_pro.backend_setting')
    var theme_bus = require('awesome_theme_pro.bus')
    var Dialog = require('web.Dialog');

    var FormController = FormController.include({
        overlay: undefined,
        
        custom_events: _.extend({}, FormController.prototype.custom_events, {
            'awesome_overlay_clicked': '_on_overlay_clicked'
        }),

        /**
         * record is need to pop up the form
         */
        init: function (parent, model, renderer, params) {
            // maybe it is not a action manager
            if (params
                && params.actionViews) {
                if (!params.actionViews || params.actionViews.length == 1) {
                    this.pop_up_form = false;
                } else {
                    if (BackendSetting.settings.form_style == 'awesome_popup') {
                        this.pop_up_form = true;
                    }
                }
            }
            this.overlay = undefined;
            this._super.apply(this, arguments)
            if (this.pop_up_form) {
                this.createOverlay();
            }
        },

        get_control_pannel_template: function () {
            if (this.pop_up_form) {
                return 'awesome_theme_pro.pop_form_control_pannel';
            } else {
                return this._super.apply(this, arguments);
            }
        },

        on_attach_callback: function () {
            this._super.apply(this, arguments)
            if (this.pop_up_form) {
                if (!this.overlay.is_visible()) {
                    this.createOverlay();
                }
            }
        },

        on_detach_callback() {
            this._super.apply(this, arguments)
            if (this.overlay) {
                this.overlay.hide();
            }
        },

        _on_overlay_clicked: function () {
            if (this.overlay) {
                this.trigger_up('history_back');
                var self = this;
                _.defer(function () {
                    self.overlay.hide();
                })
            }
        },

        createOverlay: function () {
            if (!this.overlay) {
                this.overlay = new OverLay(this)
                var $body = $("body");
                this.overlay.appendTo($body)
            } else {
                this.overlay.show();
            }
        },

        /**
         * @private
         * @param {OdooEvent} ev
         */
        _onButtonClicked: function (ev) {
            // stop the event's propagation as a form controller might have other
            // form controllers in its descendants (e.g. in a FormViewDialog)
            ev.stopPropagation();
            var self = this;
            var def;

            this._disableButtons();

            function saveAndExecuteAction() {
                return self.saveRecord(self.handle, {
                    stayInEdit: true,
                }).then(function () {
                    // we need to reget the record to make sure we have changes made
                    // by the basic model, such as the new res_id, if the record is
                    // new.
                    var record = self.model.get(ev.data.record.id);
                    return self._callButtonAction(attrs, record);
                });
            }

            function SaveAndReturnRecord() {
                return self.saveRecord(self.handle, {
                    stayInEdit: true,
                }).then(function () {
                    var record = self.model.get(ev.data.record.id);
                    var action = { type: 'ir.actions.act_window_close', infos: record }
                    return self.do_action(action, {})
                });
            }

            function SaveAndNotify(msg_name) {
                return self.saveRecord(self.handle, {
                    stayInEdit: true,
                }).then(function () {
                    // we need to reget the record to make sure we have changes made
                    // by the basic model, such as the new res_id, if the record is
                    // new.
                    var record = self.model.get(ev.data.record.id);
                    theme_bus.trigger(msg_name, record);
                });
            }

            var attrs = ev.data.attrs;
            if (attrs.confirm) {
                def = new Promise(function (resolve, reject) {
                    Dialog.confirm(this, attrs.confirm, {
                        confirm_callback: saveAndExecuteAction,
                    }).on("closed", null, resolve);
                });
            } else if (attrs.special === 'cancel') {
                def = this._callButtonAction(attrs, ev.data.record);
            } else if (attrs.special === 'save_and_return') {
                // extend to save and retur record
                def = SaveAndReturnRecord();
            } else if (attrs.special === 'save_and_notify') {
                def = SaveAndNotify(attrs.name);
            } else if (!attrs.special || attrs.special === 'save') {
                // save the record but don't switch to readonly mode
                def = saveAndExecuteAction();
            } else {
                console.warn('Unhandled button event', ev);
                return;
            }

            // Kind of hack for FormViewDialog: button on footer should trigger the dialog closing
            // if the `close` attribute is set
            def.then(function () {
                self._enableButtons();
                if (attrs.close) {
                    self.trigger_up('close_dialog');
                }
            }).guardedCatch(this._enableButtons.bind(this));
        }
    })
})