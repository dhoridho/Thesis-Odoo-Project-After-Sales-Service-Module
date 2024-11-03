odoo.define('equip3_inventory_control.InventoryValidationController', function (require) {
"use strict";

    var InventoryValidationController = require('stock.InventoryValidationController');
    var core = require('web.core');
    var StockOrderpointListController = require('stock.StockOrderpointListController');
    var StockOrderpointListModel = require('stock.StockOrderpointListModel');

    var _t = core._t;

    StockOrderpointListModel.include({
        on_replenish: function (records) {
          var self = this;
          var model = records[0].model;
          var recordResIds = _.pluck(records, 'res_id');
          var context = records[0].getContext();
          return this._rpc({
              model: model,
              method: 'action_replenish_orderpoint',
              args: [recordResIds],
              context: context,
          }).then(function () {
              return self.do_action('stock.action_replenishment');
          });
        },
    });

    StockOrderpointListController.include({
        renderButtons: function () {
            this._super.apply(this, arguments);
            var $buttonReplenish = this.$buttons.find('.o_button_replenish');
            $buttonReplenish.on('click', this._onClickReplenish.bind(this));
        },
        _onClickReplenish: function () {
            var records = this.getSelectedRecords();
            this.model.on_replenish(records);
        },
        _onSelectionChanged: function (ev) {
            this._super(ev);
            var $buttonReplenish = this.$el.find('.o_button_replenish');
            if (this.getSelectedIds().length === 0){
                $buttonReplenish.addClass('d-none');
            } else {
                $buttonReplenish.removeClass('d-none');
            }
        }
    });

    InventoryValidationController.include({
        events: _.extend({
            'click .o_button_complete_inventory': '_onCompleteInventory'
        }, InventoryValidationController.prototype.events),
        /**
         * Handler called when user click on validation button in inventory lines
         * view. Makes an rpc to try to validate the inventory, then will go back on
         * the inventory view form if it was validated.
         * This method could also open a wizard in case something was missing.
         *
         * @private
         */
        _onCompleteInventory: function () {
            var self = this;
            var prom = Promise.resolve();
            var recordID = this.renderer.getEditableRecordID();
            if (recordID) {
                // If user's editing a record, we wait to save it before to try to
                // validate the inventory.
                prom = this.saveRecord(recordID);
            }

            prom.then(function () {
                self._rpc({
                    model: 'stock.inventory',
                    method: 'action_complete',
                    args: [self.inventory_id]
                }).then(function (res) {
                    var exitCallback = function (infos) {
                        // In case we discarded a wizard, we do nothing to stay on
                        // the same view...
                        if (infos && infos.special) {
                            return;
                        }
                        // ... but in any other cases, we go back on the inventory form.
                        self.do_notify(
                            false,
                            _t("The inventory has been completed"));
                        self.trigger_up('history_back');
                    };

                    if (_.isObject(res)) {
                        self.do_action(res, { on_close: exitCallback });
                    } else {
                        return exitCallback();
                    }
                });
            });
        }
    });

});