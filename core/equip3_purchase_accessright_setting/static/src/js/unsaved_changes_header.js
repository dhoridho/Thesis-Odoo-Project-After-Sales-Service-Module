odoo.define('equip3_purchase_accessright_setting.unsaved_changes_header', function (require) {
    "use strict";

    var FormView = require('web.FormView');
    var core = require('web.core');
    var _t = core._t;

    FormView.include({
        init: function (viewInfo, params) {
            this._super.apply(this, arguments);
            this.is_changed = false; // Flag untuk mendeteksi perubahan
        },

        // Override method on_change untuk mendeteksi perubahan data
        confirmChange: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                if (!self.$(".o_dirty_warning").length) {
                    self.$('.o_statusbar_buttons')
                        .append($('<span/>', {text: _t("Unsaved changes"), class: 'text-muted ml-2 o_dirty_warning'}))
                }
            });
        },

        // Memeriksa apakah ada perubahan
        _checkUnsavedChanges: function () {
            if (!this.is_changed) {
                this.is_changed = true;
                this._updateHeader(); // Memperbarui header jika ada perubahan
            }
        },

        // Memperbarui header dengan menampilkan pesan
        _updateHeader: function () {
            var header = this.$el.find('.o_form_view .o_form_buttons_view');
            if (header.length) {
                var unsavedText = $('<span class="unsaved_changes">Unsaved changes</span>');
                if (header.find('.unsaved_changes').length === 0) {
                    header.append(unsavedText); // Menambahkan teks di header
                }
            }
        },

        // Menghapus tanda perubahan setelah disimpan
        save_record: function () {
            var self = this;
            this._super.apply(this, arguments).done(function () {
                self.is_changed = false; // Reset perubahan
                self._removeUnsavedChangesText(); // Menghapus teks perubahan
            });
        },

        // Menghapus teks perubahan saat disimpan
        _removeUnsavedChangesText: function () {
            this.$el.find('.unsaved_changes').remove();
        }
    });
});
