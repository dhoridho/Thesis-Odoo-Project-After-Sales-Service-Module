odoo.define('equip3_pos_cashbox.CashControlFormController', function(require) {
    "use strict";

    var FormController = require('web.FormController');
    var Dialog = require('web.Dialog');
    var core = require('web.core');
    var _t = core._t;

    let CashControlFormController = FormController.include({

        _actionClosingCashControl: function(ev) {
            let self = this; 
            let message = _('Are you sure want to Confirm and Save this Cash Control?');
            let $content = $(`
                <div class="d-flex align-items-center justify-content-center">
                    <div class="message w-100">${message}</div>
                </div>
            `);

            function disable_popup($el) {
                $el.find('.message').html('<div class="text-center"><div class="spinner-border text-warning"></div><div>Loading...</div></div>');
                $el.find('button').css({'pointer-events': 'none', 'opacity': '0.5'});
                $el.find('[data-dismiss="modal"]').hide();
            }

            function enable_popup($el) {
                $el.find('.message').text(message);
                $el.find('button').css({'pointer-events': 'auto', 'opacity': '1'});
                $el.find('[data-dismiss="modal"]').show();
            }

            let dialog = new Dialog(self, {
                title: _t('Confirmation'),
                $content: $content,
                buttons: [
                    {
                        text: _t('Ok'), 
                        name: 'confirm_action_closing_cash_control',
                        classes: 'btn-primary', 
                        close: false, 
                        click: function () {
                            disable_popup(dialog.$modal);

                            self._disableButtons();
                            var attrs = ev.data.attrs;
                            function saveAndExecuteAction () {
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

                            var def = saveAndExecuteAction();
                            // Kind of hack for FormViewDialog: button on footer should trigger the dialog closing
                            // if the `close` attribute is set
                            def.then(function () {
                                enable_popup(dialog.$modal);
                                self._enableButtons();
                                if (attrs.close) {
                                    self.trigger_up('close_dialog');
                                }
                            }).guardedCatch(function () {
                                self._enableButtons.bind(self);
                                enable_popup(dialog.$modal);
                            });

                        }
                    }, 
                    {   
                        text: _t('Cancel'), 
                        close: true
                    }
                ],
                size: false,
            });

            dialog.opened().then(function () {   });
            dialog.open();
        },

        _onButtonClicked: function (ev) {
            if (ev.data.attrs.name == 'action_closing_cash_control') {
                this._actionClosingCashControl(ev);
            } else {
                this._super.apply(this, arguments);
            }
        }
    });

    return CashControlFormController;

});