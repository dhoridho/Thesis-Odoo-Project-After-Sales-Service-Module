odoo.define('awesome.FilterMenu', function (require) {
    "use strict";

    const CustomFilterItem = require('web.CustomFilterItem');
    const { Component } = owl;
    const AwesomeMenuPannel = require('awesome.MenuPannel')
    const { FACET_ICONS } = require("web.searchUtils");
    const { useModel } = require('web/static/src/js/model.js');

    /**
     * 'Filters' menu
     *
     * Simple rendering of the filters of type `filter` given by the control panel
     * model. It uses most of the behaviours implemented by the dropdown menu Component,
     * with the addition of a filter generator (@see CustomFilterItem).
     * @see Component for additional details.
     * @extends Component
     */
    class AwesomeFilterMenu extends AwesomeMenuPannel {

        constructor() {
            super(...arguments);

            this.model = useModel('searchModel');
        }

        //---------------------------------------------------------------------
        // Getters
        //---------------------------------------------------------------------

        /**
         * @override
         */
        get icon() {
            return FACET_ICONS.filter;
        }

        /**
         * @override
         */
        get items() {
            return this.model.get('filters', f => f.type === 'filter');
        }

        /**
         * @override
         */
        get title() {
            return this.env._t("Filters");
        }

        //---------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------

        /**
         * @private
         * @param {OwlEvent} ev
         */
        _onItemSelected(ev) {
            ev.stopPropagation();
            const { item, option } = ev.detail;
            if (option) {
                this.model.dispatch('toggleFilterWithOptions', item.id, option.id);
            } else {
                this.model.dispatch('toggleFilter', item.id);
            }
        }
    }

    AwesomeFilterMenu.components = Object.assign({}, AwesomeMenuPannel.components, {
        CustomFilterItem,
    });
    AwesomeFilterMenu.props = Object.assign({}, AwesomeMenuPannel.props, {
        fields: Object,
    });
    AwesomeFilterMenu.template = 'awesome.FilterMenu';

    return AwesomeFilterMenu;
});
