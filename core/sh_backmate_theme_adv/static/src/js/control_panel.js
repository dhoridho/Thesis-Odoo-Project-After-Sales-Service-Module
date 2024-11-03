odoo.define('sh_backmate_theme.SHSearchBar', function (require) {
	"use strict";

	const SearchBar = require('web.SearchBar');
	const ControlPanel = require('web.ControlPanel');
	const Pager = require('web.Pager');
	const ActionMenus = require('web.ActionMenus');
	const ComparisonMenu = require('web.ComparisonMenu');
	const ActionModel = require('web/static/src/js/views/action_model.js');
	const FavoriteMenu = require('web.FavoriteMenu');
	const FilterMenu = require('web.FilterMenu');
	const GroupByMenu = require('web.GroupByMenu');
	const { Component, hooks } = owl;
	const config = require('web.config');
	const { useRef, useSubEnv, useState } = hooks;

	ControlPanel.patch("sh_entmate_theme.ShControlPanel", (T) => {

		class ShControlPanel extends T {


			constructor() {
				super(...arguments);
				this.state = useState({
					isMobile: config.device.isMobile ? true : false
				});
			}

			get_current_view() {
				const current_view = this.props.views.find((view) => {
					return view.type === this.env.view.type
				})
				const view_icon = 'fa ' + current_view.icon
				return view_icon;
			}




		}
		return ShControlPanel
	});



	class SHSearchBar extends Component {
		constructor() {
			super(...arguments);

		}
		_onSearchInput(ev) {
			this.state.inputValue = ev.target.value;
			const wasVisible = this.state.sources.length;
			const query = this.state.inputValue.trim().toLowerCase();
			if (query.length) {
				this.state.sources = this._filterSources(query);
			} else if (wasVisible) {
				this._closeAutoComplete();
			}
		}

		_onEmptyAll() {
			// this.trigger_up('search_bar_cleared');
		}
		_toggleMobileSearchView() {
			if (config.device.isMobile) {
				$('.o_mobile_search').toggleClass('o_hidden');
				$('.o_cp_bottom').toggleClass('sh_o_cp_bottom');
				$('.o_cp_top').toggleClass('sh_o_cp_top');
				$('.o_cp_searchview').toggleClass('sh_o_cp_searchview');
				//			   $('.o_mobile_search_filter').toggleClass('o_hidden');

			}



			//	       if (!this.withBreadcrumbs || (this.$('.o_toggle_searchview_full').is(':visible') && !this.$('.o_mobile_search').is(':visible'))) {
			//	            this.$('.o_toggle_searchview_full').toggleClass('btn-secondary', !!this.state.query.length);
			//	            this.searchBar.$el.detach().insertAfter(this.$('.o_mobile_search'));
			//	        } else {
			//	            this.searchBar.$el.detach().insertAfter(this.$('.o_mobile_search_header'));
			//	        }
			//	       

		}

		_onSearchClick() {
			if (config.device.isMobile) {



				$('.o_cp_searchview').toggleClass('o_searchview_quick');

				//	         if($('.o_searchview_input_container').css("display"))
				//	         $('.o_searchview_input_container').toggleClass('o_hidden')

				//	        	 $('.o_searchview_input_container')
				//	             .toggleClass('o_hidden',!$('.o_cp_searchview').hasClass('o_searchview_quick'));

				$('.breadcrumb').toggleClass('o_hidden',
					$('.o_cp_searchview').hasClass('o_searchview_quick'));
				$('.o_toggle_searchview_full')
					.toggleClass('o_hidden')
					.toggleClass('btn-secondary', !!true);



				const searchBarEl = this.el.querySelector('.o_searchview_input_container');
				//	        $(tmp_info.component.el).appendTo($(searchBarEl))

				if ($('.o_toggle_searchview_full').is(':visible') && !$('.o_mobile_search').is(':visible')) {
					$('.o_toggle_searchview_full').toggleClass('btn-secondary', !!true);
					//this.searchBar.$el.detach().insertAfter(this.$('.o_mobile_search'));
				} else {
					// this.searchBar.$el.detach().insertAfter(this.$('.o_mobile_search_header'));
				}



				$('.o_enable_searchview')
					.toggleClass("fa-search")
					.toggleClass("fa-arrow-left")

				$('.o_cp_top')
					.toggleClass("sh_top1")



				if ($('.o_searchview_input_container').hasClass('sh_input_container')) {
					$('.o_searchview_input_container').removeClass("sh_input_container")
				} else {
					$('.o_searchview_input_container').addClass("sh_input_container")
				}

			}



		}


	}
	ControlPanel.components = {
		SearchBar, SHSearchBar,
		ActionMenus, Pager,
		ComparisonMenu, FilterMenu, GroupByMenu, FavoriteMenu,
	};
	//  
	//
	//   	
	//   SearchBar.components = {
	//		   SHSearchBar
	//   };
	//   SHSearchBar.defaultProps = {
	//     //  fields: {},
	//   };
	//   SHSearchBar.props = {
	//      // fields: Object,
	//   };

	SHSearchBar.template = 'sh_backmate_theme.SHSearchBar';

	return SHSearchBar


});