odoo.define('equip3_rental_masterdata.rental_product_confirm_on_save', function (require) {
    "use strict";

    var ajax = require('web.ajax');
    var AbstractView = require('web.AbstractView');
    var FormController = require('web.FormController');
    var Dialog = require('web.Dialog');
    var session = require('web.session');

    AbstractView.include({

        init: function (viewInfo, params) {
            var self = this;
            this._super.apply(this, arguments);
            var confirm = this.arch.attrs.confirm ? this.arch.attrs.confirm : false;
            var alert = this.arch.attrs.alert ? this.arch.attrs.alert : false;
            self.controllerParams.activeActions.confirm = confirm;
            self.controllerParams.activeActions.alert = alert;
        },

    });

    FormController.include({

        check_condition: function (modelName, record_id, data_changed) {
            var def = this._rpc({
                "model": modelName,
                "method": "check_condition_show_dialog",
                "args": [record_id, data_changed]
            });
            return def;
        },

        checkCanBeSaved: function (recordID) {
            var fieldNames = this.renderer.canBeSaved(recordID || this.handle);
            if (fieldNames.length) {
                return false;
            }
            return true;
        },

        getMissingValues: function (rentPerMonth, rentPerWeek, rentPerDay, rentPerHour) {
            var missingValues = []
            if (parseFloat(rentPerMonth) == 0 || rentPerMonth == "") {
                missingValues.push("Monthly Rental");
            }

            if (parseFloat(rentPerWeek) == 0 || rentPerWeek == "") {
                missingValues.push("Weekly Rental");
            }

            if (parseFloat(rentPerDay) == 0 || rentPerDay == "") {
                missingValues.push("Daily Rental");
            }

            if (parseFloat(rentPerHour) == 0 || rentPerHour == "") {
                missingValues.push("Hourly Rental");
            }

            return missingValues;
        },

        checkIsRentalProduct: function () {
            var rentOkDiv = document.querySelector('div[name="rent_ok"]');
            var isChecked = false

            if (rentOkDiv) {
                var rentOkChecbox = rentOkDiv.querySelector('input[type="checkbox"]');
                if (rentOkChecbox) {
                    isChecked = rentOkChecbox.checked
                }
            }

            return isChecked
        },

        _onSave: function (ev) {
            var self = this;
            var modelName = 'product.template';
            var record = this.model.get(this.handle, { raw: true });
            var data_changed = record ? record.data : false;
            var record_id = data_changed && data_changed.id ? data_changed.id : false;
            var confirm = self.activeActions.confirm = true;
            var alert = self.activeActions.alert = true;
            var canBeSaved = record && record.id ? self.checkCanBeSaved(record.id) : false;
            var rentPerMonth = this.$('input[name="rent_per_month"]').val();
            var rentPerWeek = this.$('input[name="rent_per_week"]').val();
            var rentPerDay = this.$('input[name="rent_per_day"]').val();
            var rentPerHour = this.$('input[name="rent_per_hour"]').val();
            var missingValues = self.getMissingValues(rentPerMonth, rentPerWeek, rentPerDay, rentPerHour)
            var isRentalProduct = self.checkIsRentalProduct()

            function saveAndExecuteAction() {
                ev.stopPropagation(); // Prevent x2m lines to be auto-saved
                self._disableButtons();
                self.saveRecord().then(self._enableButtons.bind(self)).guardedCatch(self._enableButtons.bind(self));
            }

            if (isRentalProduct && missingValues.length > 0) {
                if (missingValues.length < 4) {
                    var joinMisingValues = missingValues.join("/");
                    var warningMessage = `Are you sure you don't want to add the rental value (${joinMisingValues}) for this product?`;
                    if (this.controlPanelProps && this.controlPanelProps.action && this.controlPanelProps.action.xml_id == "product.product_template_action") {
                        if (canBeSaved && modelName && (confirm || alert)) {
                            self.check_condition(modelName, record_id, data_changed).then(function (opendialog) {
                                if (!opendialog) {
                                    saveAndExecuteAction();
                                } else {
                                    if (confirm) {
                                        var def = new Promise(function (resolve, reject) {
                                            Dialog.confirm(self, warningMessage, {
                                                confirm_callback: saveAndExecuteAction,
                                            }).on("closed", null, resolve);
                                        });
                                    }
                                }
                            });
                        } else {
                            saveAndExecuteAction();
                        }
                    } else {
                        saveAndExecuteAction();
                    }
                } else {
                    saveAndExecuteAction();
                }
            } else {
                saveAndExecuteAction();
            }
        },

    });

});