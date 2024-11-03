odoo.define('equip3_hashmicro_ui.SearchBar', function (require) {
    "use strict";

    const searchBar = require('web.SearchBar');
    const { onMounted, onPatched } = owl.hooks;

    const processFacets = function(){
        $('.o_facet_dropdown_menu').on('click', function(ev){ev.stopPropagation();});
        _.each($('.o_searchview_facet'), function(facet, i){
            $(facet).find('.o_facet_color').addClass('o_indicator_' + (i % 5));
        });
    }

    class SearchBar extends searchBar {
        constructor() {
            super(...arguments);
            onMounted(() => processFacets());
            onPatched(() => processFacets());
        }

        _onFacetRemove(facet) {
            this.model.dispatch('deactivateGroup', facet.groupId);
            $('.o_facet_dropdown_menu').toggleClass('show', $('.o_searchview_facet').length > 1);
        }
    }

    return SearchBar;
});