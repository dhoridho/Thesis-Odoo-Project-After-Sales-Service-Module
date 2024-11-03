odoo.define('equip3_inventory_masterdata.Package', function (require) {
"use strict";
    
var core = require('web.core');
var ListController = require('web.ListController');
    
var qweb = core.qweb;

    
ListController.include({

    renderButtons: function () {
        this._super.apply(this, arguments);
        if (this.modelName === "stock.quant.package") {
            var $buttons = $(qweb.render('StockQuantPackage.Buttons'));
            var $buttonPackage = $buttons.find('.o_button_unpack');
            $buttons.prependTo(this.$buttons);
            $buttonPackage.on('click', this._onUnpack.bind(this));
        }
    },

    _onUnpack: function () {
        var self = this;
        var records = this.getSelectedRecords();
        var valueSet = records.map(function (result) {
            return result.res_id;
        });
        return this._rpc({
            model: 'stock.quant.package',
            method: 'action_package_unpack',
            args: [valueSet]
        }).then(function () {
            return self.do_action('stock.action_package_view');
        });
    },

    _onSelectionChanged: function (ev) {
        this._super(ev);
        var $buttonPackage = this.$el.find('.o_button_unpack');
        if (this.getSelectedIds().length === 0){
            $buttonPackage.addClass('d-none');
        } else {
            $buttonPackage.removeClass('d-none');
        }
    },



});
});
    