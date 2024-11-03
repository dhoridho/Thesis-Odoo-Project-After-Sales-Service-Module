odoo.define('awesome_theme_pro.DialogExtend', function (require) {
    "use strict";

    const OwlDialog = require('web.OwlDialog');
    const Dialog = require('web.Dialog')
    var BackendSetting = require('awesome_theme_pro.backend_setting')

    Dialog.include({
        open: function (options) {
            var pop_style = BackendSetting.settings.dialog_pop_style
            if (!BackendSetting.settings.dialog_pop_style) {
                return this._super.apply(this, arguments)
            } else {
                $('.tooltip').remove(); // remove open tooltip if any to prevent them staying when modal is opened

                var self = this;
                // add a popup style
                this.appendTo($('<div/>')).then(function () {
                    self.$modal.addClass(pop_style)
                    self.$modal.find(".modal-body").replaceWith(self.$el);
                    self.$modal.attr('open', true);
                    self.$modal.removeAttr("aria-hidden");
                    if (self.$parentNode) {
                        self.$modal.appendTo(self.$parentNode);
                    }
                    self.$modal.modal({
                        show: true,
                        backdrop: self.backdrop,
                    });
                    self._openedResolver();
                    if (options && options.shouldFocusButtons) {
                        self._onFocusControlButton();
                    }
                    // Notifies OwlDialog to adjust focus/active properties on owl dialogs
                    OwlDialog.display(self);
                });

                return self;
            }
        }
    });

    return Dialog;
});
