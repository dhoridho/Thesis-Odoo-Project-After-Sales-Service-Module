odoo.define('xf_purchase_dashboard', function (require) {
    "use strict";

    const core = require('web.core');
    const AbstractAction = require('web.AbstractAction');
    const QWeb = core.qweb;


    const XFPurchaseDashboard = AbstractAction.extend({
        template: 'XFPurchaseDashboardMain',
        hasControlPanel: true,
        loadControlPanel: true,
        dashboard_widgets: {},
        dashboard_years: {},
        current_year: null,
        default_group_by: 'user_id',

        events: {
            "click .o_xf_purchase_dashboard_widget_line": function (ev) {
                const self = this;
                ev.preventDefault();
                let domain = $(ev.currentTarget).data('domain');
                this.do_action({
                    type: 'ir.actions.act_window',
                    name: 'Purchase Orders',
                    res_model: 'purchase.order',
                    views: [[false, 'list'], [false, 'form']],
                    view_mode: 'tree,form',
                    domain: domain,
                });
            },
        },

        init(parent, action, options = {}) {
            this._super(...arguments);
            // dashboard params
            this.current_year = moment().year();
            this.group_by = this.default_group_by;
            // control panel attributes
            this.action = action;
            this.actionManager = parent;
            this.searchModelConfig.modelName = 'purchase.order';
            this.options = options;
        },

        willStart: function () {
            return $.when(
                this._super.apply(this, arguments),
                this.fetch_years(),
                this.fetch_data(),
            );
        },

        fetch_years: function () {
            const self = this;
            return this._rpc({
                model: 'purchase.order',
                method: 'get_dashboard_years'
            }).then(function (years) {
                self.dashboard_years = years;
            });
        },

        fetch_data: function () {
            const self = this;
            return this._rpc({
                model: 'purchase.order',
                method: 'get_dashboard_widgets',
                args: [self.current_year, self.group_by],
            }).then(function (response) {
                self.dashboard_widgets = response;
            });
        },

        start: function () {
            const self = this;
            this._computeControlPanelProps();
            return this._super().then(function () {
                self.render_dashboard_widgets();
            });
        },

        /**
         * @private
         */
        _computeControlPanelProps() {
            const $buttons = $(QWeb.render("XFPurchaseDashboardButtons", {
                'dashboard_years': this.dashboard_years,
                'current_year': this.current_year,
                'group_by': this.group_by,
            }));
            $buttons.find('a[data-group_by]').click((ev) => {
                ev.preventDefault();
                $buttons.find('a.active[data-group_by]').removeClass('active');
                $(ev.target).addClass('active');
                this.on_group_by_button($(ev.target).data('group_by'));
            });

            $buttons.find('a[data-year]').click((ev) => {
                ev.preventDefault();
                $buttons.find('a.active[data-year]').removeClass('active');
                $(ev.target).addClass('active');
                $buttons.find('span.current_year').text($(ev.target).data('year'));
                this.on_select_year_button($(ev.target).data('year'));
            });

            this.controlPanelProps.cp_content = {$buttons};
        },

        on_group_by_button: function (group_by) {
            const allowed_group_by_fields = ['user_id', 'partner_id', 'product_id']
            if (!allowed_group_by_fields.includes(group_by)) {
                console.log('Unknown group_by option. Choose between [user_id, partner_id, product_id]');
                return;
            }
            this.group_by = group_by;

            const self = this;
            Promise.resolve(this.fetch_data()).then(function () {
                self.render_dashboard_widgets();
            });
        },

        on_select_year_button: function (year) {
            this.current_year = year;
            const self = this;
            Promise.resolve(this.fetch_data()).then(function () {
                self.render_dashboard_widgets();
            });
        },

        render_dashboard_widgets: function () {
            const self = this;
            let $content_block = self.$el.find('.o_xf_purchase_dashboard_widgets .row');
            $content_block.empty();
            _.each(self.dashboard_widgets, function (dashboard_widget) {
                $content_block.append(
                    QWeb.render("XFPurchaseDashboardWidget", {'dashboard_widget': dashboard_widget})
                );
            });
        },
    });

    core.action_registry.add('xf_purchase_dashboard.main', XFPurchaseDashboard);

    return XFPurchaseDashboard;

});