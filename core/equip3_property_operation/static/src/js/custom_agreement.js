odoo.define("equip3_property_operation.custom_agreement", function (require) {
	"use strict";


	var ListController = require("web.ListController");
	var AgreementController = require("agreement_legal.agreement");
	
	var includeCtx = {
		renderButtons: function () {
			this._super.apply(this, arguments);
			if (this.modelName === "agreement" && this.$buttons) {
                var self = this;
                var data = this.model.get(this.handle);
                if (data.context.default_is_template === true) {
                    this.$buttons.find(".create_agreement_from_template").hide();
                } else {
                    this.$buttons.find(".o-kanban-button-new").hide();
                    this.$buttons.find(".o_list_button_add").hide();
                    this.$buttons.find(".o_form_button_create").hide();
                }
                this.$buttons
                    .find(".create_agreement_from_template")
                    .on("click", function () {
						if (data.context.active_model === 'product.product') {
							self.do_action(	
								"agreement_legal.create_agreement_from_template_action",
								{
									additional_context: {
										'active_id': data.context.active_id,
										'active_ids': data.context.active_ids,
										'active_model': data.context.active_model,
									},
								}
							);
						}
                    });
            }
		},
	};

	ListController.include(includeCtx);
	AgreementController.include(includeCtx);
});