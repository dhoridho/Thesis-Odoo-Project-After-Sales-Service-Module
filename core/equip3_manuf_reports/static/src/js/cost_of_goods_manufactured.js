odoo.define('equip3_manuf_reports.CostOfGoodsManufactured', function(require){
    "use strict";

    const AbstractAction = require('web.AbstractAction');
    const session = require('web.session');
    const core = require('web.core');
    const QWeb = core.qweb;

    const COGMAction = AbstractAction.extend({
        template: 'CostOfGoodsManufactured',

        events: {
            'show.bs.collapse tr': '_onCollapseShow',
            'hide.bs.collapse tr': '_onCollapseHide',
            'click .o_cogm_print_pdf': '_onPrintPdf',
            'click .o_cogm_print_xlsx': '_onPrintXlsx',
            'click .o_cogm_expand': '_onClickExpand',
            'click .o_cogm_filters': '_onClickFilters',
            'click .o_filter_select': '_onSelectFilter',
            'click .o_apply_filter': '_onClickApplyFilter'
        },

        init: function (parent, action, options) {
            this._super.apply(this, arguments);
            this.expanded = false;
            this.folded = [];

            this.model = 'cogm.report';
            this.res_id = false;

            this.filters = {
                date: ['this_month', 'This Month'],
                comparison: ['no_comparison', 'No Comparison']
            }

            this.$customDateFrom = $();
            this.$customDateTo = $();
            this.$prevNoOfPeriods = $();
            this.$sameNoOfPeriods = $();
        },

        willStart: function(){
            var dataProm = this._getData();
            return Promise.all([this._super.apply(this, arguments), dataProm]);
        },

        _getData: function(){
            var filters = this._buildFilters();

            var self = this;
            return this._rpc({
                method: 'get_report_data',
                model: this.model,
                args: [filters]
            }).then(function(result){
                self.data = result.data;
                self.currency = session.currencies[result.currency_id];
                _.each(self.data, function(d){
                    let classList = d.class.split(' ');
                    if (classList.includes('collapse') && !classList.includes('show')){
                        self.folded.push(d.section);
                    }
                });
            });
        },

        start: function(){
            this.$customDateFrom = this.$('.o_custom_date_from');
            this.$customDateEnd = this.$('.o_custom_date_to');
            this.$prevNoOfPeriods = this.$('.o_previous_no_of_periods');
            this.$sameNoOfPeriods = this.$('.o_same_no_of_periods');
            return this._super.apply(this, arguments);
        },

        format_currency: function(amount) {
            if (typeof(amount) === 'number'){
                let formatted = `${this.currency.symbol} ${Math.abs(amount).toLocaleString()}`;
                if (amount >= 0){
                    return formatted;
                }
                return '- ' + formatted;
            }
            return amount;
        },

        _onCollapseShow: function(ev){
            let $target = $(ev.currentTarget);
            let index = this.folded.indexOf($target.data('section'));
            this.folded.splice(index, 1);
            this._toggleCaret($target, true);
        },

        _onCollapseHide: function(ev){
            let $target = $(ev.currentTarget);
            this.$el.find($target.data('target')).collapse('hide');
            this.folded.push($target.data('section'));
            this._toggleCaret($target, false);
        },

        _toggleCaret: function($target, isShow){
            let parentSection = _.find(this.data, d => d.section === $target.data('section')).parent;
            let $parent = this.$el.find(`tr[data-section="${parentSection}"]`);
            $parent.find('span.fa').toggleClass('fa-caret-right', !isShow);
            $parent.find('span.fa').toggleClass('fa-caret-down', isShow);
        },

        _updateData: function(){
            let data = JSON.stringify({
                data: this.data,
                folded: this.folded,
                filters: this._buildFilters()
            });

            var self = this;
            if (!this.res_id){
                return this._rpc({
                    method: 'create',
                    model: this.model,
                    args: [{data: data}]
                }).then(function(recordId){
                    self.res_id = recordId;
                    return recordId;
                });
            } else {
                return this._rpc({
                    method: 'write',
                    model: this.model,
                    args: [[this.res_id], {data: data}]
                }).then(function(result){
                    if (result){
                        return self.res_id;
                    }
                });
            }
        },

        _defaultFormat: function(mom){
            return mom.format('YYYY-MM-DD');
        },

        _buildFilters: function(){

            let fDate = this.filters.date[0],
                fComp = this.filters.comparison[0],
                from = moment(),
                to = moment();

            if (fDate !== 'custom'){
                let prefix = fDate.split('_')[0],
                    dType = fDate.split('_')[1];
                if (prefix === 'last'){
                    from = from.subtract(1, `${dType}s`);
                    to = to.subtract(1, `${dType}s`);
                }
                from = from.startOf(dType);
                to = to.endOf(dType)
            } else if (value === 'custom'){
                from = this.$customDateFrom.val();
                to = this.$customDateTo.val();
            }

            let dateFromFromatted = this._defaultFormat(from),
                dateToFromatted = this._defaultFormat(to);
            
            let noOfPeriods = 0;
            if (fComp === 'previous'){
                noOfPeriods = parseInt(this.$prevNoOfPeriods.val());
            } else if (fComp === 'same'){
                noOfPeriods = parseInt(this.$sameNoOfPeriods.val());
            }

            let dateRanges = [{from: dateFromFromatted, to: dateToFromatted}],
                delta = (fDate !== 'custom' || fComp === 'same') ? 1 : to.diff(from, 'days'),
                dateType = fDate === 'custom' ? 'day' : fComp === 'same' ? 'year' : fDate.split('_')[1];
            
            for (let i=1; i < noOfPeriods + 1; i++){
                
                let nextFrom = from.clone().subtract(i * delta, `${dateType}s`),
                    nextTo = to.clone().subtract(i * delta, `${dateType}s`);
                if (fComp === 'previous'){
                    nextFrom = nextFrom.startOf(dateType);
                    nextTo = nextTo.endOf(dateType);
                }

                dateRanges.push({
                    from: this._defaultFormat(nextFrom),
                    to: this._defaultFormat(nextTo)
                });
            }
            
            return {
                active_date: this.filters.date,
                active_comparison: this.filters.comparison,
                date_from: dateFromFromatted,
                date_to: dateToFromatted,
                no_of_periods: noOfPeriods,
                date_ranges: dateRanges
            };
        },

        _onPrintPdf: async function(ev) {
            ev.preventDefault();
            let resId = await this._updateData();
            return this.do_action('equip3_manuf_reports.action_print_cogm_report', {
                additional_context: {
                    'active_id': resId,
                    'active_ids': [resId],
                    'active_model': this.model
                }
            });
        },

        _onPrintXlsx: async function(ev) {
            let resId = await this._updateData();

            var self = this;
            this._rpc({
                model: this.model,
                method: 'print_xlsx_report',
                args: [[resId]],
            }).then(function(attachmentId) {
                if (attachmentId) {
                    return self.do_action({
                        'type': 'ir.actions.act_url',
                        'url': '/web/content/' + attachmentId + '?download=true',
                        'target': 'self'
                    });
                }
            });
        },

        _onClickExpand: function(ev){
            let $target = $(ev.currentTarget);
            let $collapses = this.$el.find('.collapse');
            $collapses.collapse(!this.expanded ? 'show' : 'hide');
            $target.text(!this.expanded ? 'Collapse' : 'Expand');
            
            this.expanded = !this.expanded;
            this._toggleCaret($collapses, this.expanded);
        },

        _onClickFilters: function(ev){
            this.$el.find('.o_ocgm_filter_content').toggleClass('d-none');
        },

        _onSelectFilter: function(ev){
            let $target = $(ev.currentTarget),
                isOpen = $target.hasClass('o_open'),
                isDrop = $target.hasClass('o_drop');

            if (isOpen || isDrop){
                ev.stopPropagation();
                if (isDrop){
                    return;
                }
            };

            let $parent = $target.closest('.o_filter');

            $parent.find('.dropdown-item').removeClass('selected');
            $target.find('.dropdown-item').addClass('selected');
            $parent.find('.current_filter').text($target.attr('title'));

            $parent.find('.o_drop').addClass('d-none');
            if (isOpen){
                $parent.find($target.data('open')).toggleClass('d-none');
            }
        },

        _onClickApplyFilter: function(ev){
            ev.stopPropagation();
            var self = this;

            _.each(this.filters, function(filter, name){
                let $parent = self.$el.find(`.o_${name}_filter`);
                let $li = $parent.find('.dropdown-item.selected').closest('li');
                self.filters[[name]] = [$li.data('value'), $li.attr('title')];
            });
            
            return this._getData().then(function(){
                let $content = QWeb.render('COGMContent', {widget: self});
                self.$el.find('.o_cogm_content').html($content);
                self.$el.find('.o_ocgm_filter_content').addClass('d-none');
            });
        }

    });

    core.action_registry.add('cost_of_goods_manufactured', COGMAction);

    return COGMAction;
});