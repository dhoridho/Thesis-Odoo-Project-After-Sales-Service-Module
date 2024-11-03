odoo.define('awesome_theme_pro.ControlPannel', function (require) {
    "use strict";

    const ActionMenus = require('web.ActionMenus');
    const ComparisonMenu = require('web.ComparisonMenu');
    const FavoriteMenu = require('web.FavoriteMenu');
    const FilterMenu = require('web.FilterMenu');
    const GroupByMenu = require('web.GroupByMenu');
    const Pager = require('web.Pager');
    const SearchBar = require('web.SearchBar');
    const ControlPanel = require('web.ControlPanel');
    const config = require('web.config')

    const AwesomeComparisonMenu = require('awesome.ComparisonMenu')
    const AwesomeFavoriteMenu = require('awesome.FavoriteMenu')
    const AwesomeFilterMenu = require('awesome.FilterMenu')
    const AwesomeGroupByMenu = require('awesome.GroupByMenu')

    const ActionModel = require('web/static/src/js/views/action_model.js');

    const { misc, hooks } = owl;
    const { Portal } = misc;
    const { useState, useRef, useExternalListener } = hooks;

    // add portal support
    ControlPanel.components = {
        Portal,
        SearchBar,
        ActionMenus, Pager,
        ComparisonMenu, FilterMenu, GroupByMenu, FavoriteMenu,
        AwesomeComparisonMenu, AwesomeFavoriteMenu, AwesomeFilterMenu, AwesomeGroupByMenu
    };

    ControlPanel.defaultProps = {
        breadcrumbs: [],
        fields: {},
        searchMenuTypes: [],
        views: [],
        withBreadcrumbs: true,
        withSearchBar: true,
        isActive: true
    };

    ControlPanel.props = {
        action: Object,
        breadcrumbs: Array,
        searchModel: ActionModel,
        cp_content: { type: Object, optional: 1 },
        fields: Object,
        pager: { validate: p => typeof p === 'object' || p === null, optional: 1 },
        searchMenuTypes: Array,
        actionMenus: { validate: s => typeof s === 'object' || s === null, optional: 1 },
        title: { type: String, optional: 1 },
        view: { type: Object, optional: 1 },
        views: Array,
        withBreadcrumbs: Boolean,
        withSearchBar: Boolean,
        isActive: Boolean
    };

    ControlPanel.patch("awesome.ControlPanel", T =>
        class extends T {
            constructor() {
                super(...arguments);
                this.state = useState({
                    isMobile: config.device.isMobile ? true : false,
                    awesome_hook_hide: false
                });
                config.device.bus.on('size_changed', this, this._onDeviceSizeChanged);
                this.optionDropDown = useRef('optionDropDown');
                useExternalListener(window, 'click', this._hideOptions);
            }

            _onDeviceSizeChanged() {
                this.state.isMobile = config.device.isMobile ? true : false
            }

            get_active_view_icon(env) {
                var activeView = _.findWhere(this.props.views, { type: env.view.type });
                return activeView.icon
            }

            _OptionDropdownToggleClick(event) {
                this.optionDropDown.el.classList.add('show');
            }

            _hideOptions(event) {
                if (!this.optionDropDown.el) {
                    return
                }
                // check if it need to hide the option
                if (!$(event.target).is($(".awesome_search_option_dropdown, .awesome_search_option_dropdown *, .search_option_dropdown_toggler"))) {
                    this.optionDropDown.el.classList.remove('show');
                }
            }
        }
    );
})