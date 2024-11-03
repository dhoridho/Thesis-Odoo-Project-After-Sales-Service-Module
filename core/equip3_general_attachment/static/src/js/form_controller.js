odoo.define('equip3_general_attachment.FormController', function (require) {
"use strict";

	const FormController = require('web.FormController');
    const core = require('web.core');
    var framework = require('web.framework');

    FormController.include({
    	renderButtons: function ($node) {
    		this._super.apply(this, arguments);
            if(this.$buttons){
                this.$buttons.on('click', '.o_form_refresh_cp', this._onRefreshCP.bind(this));
            }

    	},
        _onRefreshCP: function () {
            var self = this
            var  actionMenus = this.controlPanelProps.actionMenus
            self.updateControlPanel({
                actionMenus: null
            });
            setTimeout(function () {
                self.updateControlPanel({
                    actionMenus: actionMenus
                });
                framework.unblockUI();
            }, 1500);
	    },
    });


});