odoo.define('pragmatic_odoo_delivery_boy', function (require) {
"use strict";
    var ListController = require('web.ListController');
    var ListView = require('web.ListView');

    var KanbanController = require('web.KanbanController');

    var KanbanView = require('web.KanbanView');

    var viewRegistry = require('web.view_registry');

    function renderGenerateMultiAssignButton() {
        console.log("renderGenerateMultiAssignButton called...")
        if (this.$buttons) {
            var self = this;
            var lead_type = self.initialState.getContext()['default_type'];
            this.$buttons.on('click', '.o_button_generate_multi_assign', function () {
                self.do_action({
                    name: 'Assign Delivery Boy',
                    type: 'ir.actions.act_window',
                    res_model: 'picking.order.multiple.assign',
                    target: 'new',
                    views: [[false, 'form']],
                });
            });
        }
    }

    var MultiAssignRequestListController = ListController.extend({
        willStart: function() {
            var self = this;
            var ready = this.getSession().user_has_group('stock.group_stock_manager')
                .then(function (is_stock_manager) {
                    if (is_stock_manager) {
                        self.buttons_template = 'MultiAssignRequestListView.buttons';
                    }
                });
            return Promise.all([this._super.apply(this, arguments), ready]);
        },
        renderButtons: function () {
            this._super.apply(this, arguments);
            this.$buttons.find('.o_list_button_add').css({'display': 'none'});
            renderGenerateMultiAssignButton.apply(this, arguments);
        }
    });

    var MultiAssignRequestListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: MultiAssignRequestListController,
        }),
    });

    var MultiAssignRequestKanbanController = KanbanController.extend({
        willStart: function() {
            var self = this;

            var ready = this.getSession().user_has_group('stock.group_stock_manager')
                .then(function (is_stock_manager) {
                    if (is_stock_manager) {
                        self.buttons_template = 'MultiAssignRequestKanbanView.buttons';
                    }
                });

            return Promise.all([this._super.apply(this, arguments), ready]);
        },
        renderButtons: function () {
            this._super.apply(this, arguments);
            this.$buttons.find('.o-kanban-button-new').css({'display': 'none'});
            renderGenerateMultiAssignButton.apply(this, arguments);
        }
    });

    var MultiAssignRequestKanbanView = KanbanView.extend({
        config: _.extend({}, KanbanView.prototype.config, {
            Controller: MultiAssignRequestKanbanController,
        }),
    });

    viewRegistry.add('picking_order_multi_assign_request_tree_view', MultiAssignRequestListView);
    viewRegistry.add('picking_order_multi_assign_request_kanban', MultiAssignRequestKanbanView);
});