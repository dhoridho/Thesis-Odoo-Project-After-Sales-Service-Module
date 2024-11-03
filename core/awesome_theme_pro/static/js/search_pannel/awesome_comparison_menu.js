odoo.define("awesome.ComparisonMenu", function (require) {
    "use strict";

    const { Component, hooks } = owl;
    const { FACET_ICONS } = require("web.searchUtils");
    const { useModel } = require("web/static/src/js/model.js");
    const AwesomeMenuPannel = require('awesome.MenuPannel')

    /**
     * "Comparison" menu
     *
     * Displays a set of comparison options related to the currently selected
     * date filters.
     * @extends Component
     */
    class AwesomeComparisonMenu extends AwesomeMenuPannel {
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
            return FACET_ICONS.comparison;
        }

        /**
         * @override
         */
        get items() {
            return this.model.get('filters', f => f.type === 'comparison');
        }

        /**
         * @override
         */
        get title() {
            return this.env._t("Comparison");
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
            const { item } = ev.detail;
            this.model.dispatch("toggleComparison", item.id);
        }
    }

    return AwesomeComparisonMenu;
});
