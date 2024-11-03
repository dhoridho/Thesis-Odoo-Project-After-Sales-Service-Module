odoo.define('equip3_sale_masterdata.ProductPricelistView', function(require){
    "use strict";

    var ListController = require('web.ListController');
    var ListView = require('web.ListView');
    var FormController = require('web.FormController');
    var FormView = require('web.FormView');
    var KanbanController = require('web.KanbanController');
    var KanbanView = require('web.KanbanView');
    var viewRegistry = require('web.view_registry');
    var session = require('web.session');

    var PricelistListController = ListController.extend({
        willStart() {
            const sup = this._super(...arguments);
            const acl = session.user_has_group('equip3_sale_accessright_setting.group_sale_pricelist_approval').then(hasGroup => {
                if (hasGroup){
                    this.activeActions['create'] = false;
                    this.activeActions['edit'] = false;
                }
            });
            return Promise.all([sup, acl]);
        },
    });

    var PricelistListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: PricelistListController,
        }),
    });

    var PricelistFormController = FormController.extend({
        willStart() {
            const sup = this._super(...arguments);
            const acl = session.user_has_group('equip3_sale_accessright_setting.group_sale_pricelist_approval').then(hasGroup => {
                if (hasGroup){
                    this.activeActions['create'] = false;
                    this.activeActions['edit'] = false;
                }
            });
            return Promise.all([sup, acl]);
        },
    });

    var PricelistFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Controller: PricelistFormController,
        }),
    });

    var PricelistKanbanController = KanbanController.extend({
        willStart() {
            const sup = this._super(...arguments);
            const acl = session.user_has_group('equip3_sale_accessright_setting.group_sale_pricelist_approval').then(hasGroup => {
                if (hasGroup){
                    this.activeActions['create'] = false;
                    this.activeActions['edit'] = false;
                }
            });
            return Promise.all([sup, acl]);
        },
    });

    var PricelistKanbanView = KanbanView.extend({
        config: _.extend({}, KanbanView.prototype.config, {
            Controller: PricelistKanbanController,
        }),
    });

    var RequestFormController = FormController.extend({
        updateButtons: function ($node) {
            this._super.apply(this, arguments);
            if (!this.$buttons) {
                return;
            }
            var state = this.model.get(this.handle);
            var is_draft = state.data.state === 'draft';

            this.$buttons.find('.o_form_button_edit').toggleClass('o_hidden', !is_draft);
        }
    });

    var RequestFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Controller: RequestFormController,
        }),
    });

    viewRegistry.add('product_pricelist_list', PricelistListView);
    viewRegistry.add('product_pricelist_form', PricelistFormView);
    viewRegistry.add('product_pricelist_kanban', PricelistKanbanView);

    viewRegistry.add('pricelist_request_form', RequestFormView);

    return {
        PricelistListController: PricelistListController,
        PricelistListView: PricelistListView,
        PricelistFormController: PricelistFormController,
        PricelistFormView: PricelistFormView,
        PricelistKanbanController: PricelistKanbanController,
        PricelistKanbanView: PricelistKanbanView,

        RequestFormController: RequestFormController,
        RequestFormView: RequestFormView
    };

});