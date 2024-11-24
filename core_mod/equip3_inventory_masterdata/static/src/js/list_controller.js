odoo.define('equip3_inventory_masterdata.ListController', function (require) {
"use strict";

    var ListController = require('web.ListController');
    var session = require('web.session');

    ListController.include({
        /**
         * @constructor
         * @override
         * @param {Object} params
         * @param {boolean} params.editable
         * @param {boolean} params.hasActionMenus
         * @param {Object[]} [params.headerButtons=[]]: a list of node descriptors
         *    for controlPanel's action buttons
         * @param {Object} params.toolbarActions
         * @param {boolean} params.noLeaf
         */
        init: function (parent, model, renderer, params) {
            this._super.apply(this, arguments);
            var self = this;
            if (this.modelName !== undefined &&
                this.modelName === "stock.location") {
                const acl = session.user_has_group('equip3_inventory_accessright_setting.group_is_three_dimension_warehouse').then(hasGroup => {
                    if (!hasGroup) {
                        self.controlPanelProps.views = self.controlPanelProps.views.filter(k => k.type !== "threedview");
                    }
                });
            }
        },
    });

});