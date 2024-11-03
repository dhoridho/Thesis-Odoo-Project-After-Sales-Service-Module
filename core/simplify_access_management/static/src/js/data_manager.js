odoo.define('simplify_access_management.data_manager', function (require) {
    "use strict";
    
    var config = require('web.config');
    var rpc = require('web.rpc');
    var utils = require('web.utils');

    var DataManager = require('web.data_manager');

    // Patch load view methos // remove restricted views 
    DataManager.load_views = async function ({ model, context, views_descr } , options = {}) {
        views_descr = await rpc.query({
            args: [],
            kwargs: { context, options, views: views_descr },
            model,
            method: 'load_views',
        }).then(result => {
            // Freeze the fields dict as it will be shared between views and
            // no one should edit it
            utils.deepFreeze(result.fields);
            const rest_views_pos = [];
            let views_to_load = views_descr ;
            views_descr.forEach(element => {
                const is_in  = _.contains(Object.keys(result.fields_views),element[1])
                if(!is_in){
                    views_to_load = _.filter(views_to_load, function(elem) {
                        return elem[1] != element[1];
                    });
                }
            });
            views_descr = views_to_load;
            // if(rest_views_pos.length){
            //     views_descr.splice(rest_views_pos,rest_views_pos.length)
            // }
            return views_descr
        });

        const viewsKey = this._gen_key(model, views_descr, options, context);
        const filtersKey = this._gen_key(model, options.action_id);
        const withFilters = Boolean(options.load_filters);
        const shouldLoadViews = config.isDebug('assets') || !this._cache.views[viewsKey];
        const shouldLoadFilters = config.isDebug('assets') || (
            withFilters && !this._cache.filters[filtersKey]
        );
        
        if (shouldLoadViews) {
            // Views info should be loaded
            options.load_filters = shouldLoadFilters;
            this._cache.views[viewsKey] = rpc.query({
                args: [],
                kwargs: { context, options, views: views_descr },
                model,
                method: 'load_views',
            }).then(result => {
                // Freeze the fields dict as it will be shared between views and
                // no one should edit it
                utils.deepFreeze(result.fields);
                for (const [viewId, viewType] of views_descr) {
                    if(_.contains(Object.keys(result.fields_views),viewType)){
                        const fvg = result.fields_views[viewType];
                        fvg.viewFields = fvg.fields;
                        fvg.fields = result.fields;
                    }
                }

                // Insert filters, if any, into the filters cache
                if (shouldLoadFilters) {
                    this._cache.filters[filtersKey] = Promise.resolve(result.filters);
                }
                return result.fields_views;
            }).guardedCatch(() => this._invalidate('views', viewsKey));
        }
        const result = await this._cache.views[viewsKey];
        if (withFilters && result.search) {
            if (shouldLoadFilters) {
                await this.load_filters({
                    actionId: options.action_id,
                    context,
                    forceReload: false,
                    modelName: model,
                });
            }
            result.search.favoriteFilters = await this._cache.filters[filtersKey];
        }
        return result;
    }
});