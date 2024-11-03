odoo.define('awesome.FavoriteMenu', function (require) {
    "use strict";

    const Dialog = require('web.OwlDialog');
    const { Component, hooks } = owl;
    const AwesomeMenuPannel = require('awesome.MenuPannel')
    const FavoriteMenu = require('web.FavoriteMenu')
    const { FACET_ICONS } = require("web.searchUtils");
    const Registry = require('web.Registry');
    const { useModel } = require('web/static/src/js/model.js');

    
    class AwesomeFavoriteMenu extends AwesomeMenuPannel {
        constructor() {
            super(...arguments);

            this.model = useModel('searchModel');
            this.state.deletedFavorite = false;
        }

        //---------------------------------------------------------------------
        // Getters
        //---------------------------------------------------------------------

        /**
         * @override
         */
        get icon() {
            return FACET_ICONS.favorite;
        }

        /**
         * @override
         */
        get items() {
            const favorites = this.model.get('filters', f => f.type === 'favorite');
            const registryMenus = FavoriteMenu.registry.values().reduce(
                (menus, Component) => {
                    if (Component.shouldBeDisplayed(this.env)) {
                        menus.push({
                            key: Component.name,
                            groupNumber: Component.groupNumber,
                            Component,
                        });
                    }
                    return menus;
                },
                []
            );
            return [...favorites, ...registryMenus];
        }

        /**
         * @override
         */
        get title() {
            return this.env._t("Favorites");
        }

        //---------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------

        /**
         * @private
         * @param {OwlEvent} ev
         */
        _onItemRemoved(ev) {
            const favorite = this.items.find(fav => fav.id === ev.detail.item.id);
            this.state.deletedFavorite = favorite;
        }

        /**
         * @private
         * @param {OwlEvent} ev
         */
        _onItemSelected(ev) {
            ev.stopPropagation();
            this.model.dispatch('toggleFilter', ev.detail.item.id);
        }

        /**
         * @private
         */
        async _onRemoveFavorite() {
            this.model.dispatch('deleteFavorite', this.state.deletedFavorite.id);
            this.state.deletedFavorite = false;
        }
    }

    // AwesomeFavoriteMenu.registry = new Registry();

    AwesomeFavoriteMenu.components = Object.assign({}, AwesomeMenuPannel.components, {
        Dialog,
    });
    AwesomeFavoriteMenu.template = 'awesome.FavoriteMenu';

    return AwesomeFavoriteMenu;
});
