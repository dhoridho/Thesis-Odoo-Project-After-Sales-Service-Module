odoo.define('equip3_general_setting.UserFormView', function(require){
    "use strict";

    var FormController = require('web.FormController');
    var FormView = require('web.FormView');
    var viewRegistry = require('web.view_registry');
    var session = require('web.session');

    var UserFormController = FormController.extend({
        willStart: function(){
            var self = this;
            var defs = [this._super.apply(this, arguments)];
            defs.push(this._rpc({
                method: 'search_read',
                model: 'res.branch',
                fields: ['id', 'company_id']
            }).then(function(branches){
                self.branchCompany = {};
                _.each(branches, function(branch){
                    self.branchCompany[branch.id] = branch.company_id[0];
                });
            }));
            return Promise.all(defs);
        },

        _onSave: function (ev) {
            ev.stopPropagation(); // Prevent x2m lines to be auto-saved
            this._disableButtons();
            var state = this.model.get(this.handle);
            try {
                var user_company_id = state.data.company_id.res_id;
                var user_company_ids = state.data.company_ids.res_ids;
                var user_branch_ids = state.data.branch_ids.res_ids;
                var user_branches = session.user_branches.allowed_branches;
                var allowed_branch_ids = session.user_context.allowed_branch_ids;

                var user_branch_company_ids = [];
                _.each(user_branch_ids, function(bid){
                    var user_branch = _.find(user_branches, function(b){return b[0] == bid;});
                    if (user_branch && user_branch[2] === user_company_id){
                        user_branch_company_ids.push(bid);
                    }
                })

                var updated_allowed_branch_ids = _.filter(allowed_branch_ids, function(bid){return user_branches.includes(bid);});
                _.each(user_branch_company_ids, function(bid){
                    if (!updated_allowed_branch_ids.includes(bid)){
                        var branch = _.find(user_branches, function(b){return b[0] == bid;});
                        if (branch && user_company_ids.includes(branch[2])){
                            updated_allowed_branch_ids.push(bid);
                        }
                    }
                })
                session.user_context.allowed_branch_ids = updated_allowed_branch_ids;
                this.saveRecord().then(
                    this._checkShouldReload.bind(this)
                ).guardedCatch(this._enableButtons.bind(this));
                
            } catch (err){
                console.log(err);
                this._super.apply(this, arguments);
            }
        },

        _checkShouldReload: function(changedFields){
            var self = this;
            var state = this.model.get(this.handle);
            if (state.res_id === session.uid && (changedFields.includes('branch_id') || changedFields.includes('branch_ids'))){
                var active_company_id = session.company_id;
                var allowed_branch_ids = session.user_context.allowed_branch_ids;
                _.each(state.data.branch_ids.res_ids, function(bid){
                    if (self.branchCompany[bid] === active_company_id && !allowed_branch_ids.includes(bid)){
                        allowed_branch_ids.push(bid);
                    }
                })
                var main_branch_id = allowed_branch_ids[0];
                if (changedFields.includes('branch_id') && state.data.branch_id){
                    main_branch_id = state.data.branch_id.res_id;
                }

                session.setBranches(main_branch_id, allowed_branch_ids);
            } else {
                this._enableButtons(changedFields);
            }
        }
    });
    
    var UserFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Controller: UserFormController,
        }),
    });

    viewRegistry.add('user_form_view_reload', UserFormView);

    return {
        UserFormController: UserFormController,
        UserFormView: UserFormView
    }
});