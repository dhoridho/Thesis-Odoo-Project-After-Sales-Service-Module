odoo.define('sh_backmate_theme_adv.theme_config_systray', function (require) {
	"use strict";

	var core = require('web.core');
	var Dialog = require('web.Dialog');
	var Widget = require('web.Widget');
	var rpc = require('web.rpc');
	var SystrayMenu = require('web.SystrayMenu');
	var session = require('web.session');
	var _t = core._t;
	var QWeb = core.qweb;
	var UserMenu = require('web.UserMenu');
	UserMenu.prototype.sequence = 2;

	var ThemeConfigurationTemplate = Widget.extend({
		template: "ThemeConfigurationTemplate",
		events: {
		},
		init: function () {
			this._super.apply(this, arguments);
			var self = this;
		},
	});

	ThemeConfigurationTemplate.prototype.sequence = 0;
	session.user_has_group('sh_backmate_theme_adv.group_theme_configuration').then(function (has_group) {
		if (has_group) {
			SystrayMenu.Items.push(ThemeConfigurationTemplate);
		}
	});

	return {
		ThemeConfigurationTemplate: ThemeConfigurationTemplate,
	};
});

odoo.define('sh_backmate_theme_adv.theme_configuration', function (require) {


	var ajax = require('web.ajax');
	var core = require('web.core');
	var rpc = require('web.rpc');

	var qweb = core.qweb;
	var _t = core._t;

	var theme_configuration = require('sh_backmate_theme_adv.theme_configuration_widget');


	$(document).ready(function () {

		var color_change = false;
		$('.o_web_client').on('click', '.close_setting', function (event) {
			$('.backmate_theme_layout').removeClass('sh_theme_model');

		});

		$('.o_web_client').on('click', '.theme_configuration', function (event) {


			if ($('.backmate_theme_layout').length) {

				if ($('.sh_theme_model').length) {

					$('.backmate_theme_layout').removeClass('sh_theme_model');
					//	$('.o_action_manager').css("margin-right" , '0px'); 
				} else {
					$('.backmate_theme_layout').addClass('sh_theme_model');
					var radioValue = $("input[name='body_background_type']:checked").val();
					if (radioValue == 'bg_color') {
						$('#body_background_color').css("display", "block");
						$('#body_background_img').css("display", "none");
					} else {
						$('#body_background_color').css("display", "none");
						$('#body_background_img').css("display", "block");
					}


					var radioValue = $("input[name='sidebar_background_style']:checked").val();
					if (radioValue == 'color') {
						$('#sidebar_background_color').css("display", "block");
						$('#sidebar_background_img').css("display", "none");
					} else {
						$('#sidebar_background_color').css("display", "none");
						$('#sidebar_background_img').css("display", "block");
					}
				}
			} else {

				this.body_container = new theme_configuration();
				this.body_container.appendTo($('.o_web_client')).then(function () {
					$('.backmate_theme_layout').addClass('sh_theme_model');

					ajax.jsonRpc('/get_theme_style', 'call', {}).then(function (data) {
						$('.sh_style_plates').append(data['data_html']);
						$('.sh_color_plates').append(data['data_color']);
						$('.sh_pre_color_plates').append(data['data_pre_color']);





						var active_style = $('.current_active_style').val();
						if (active_style) {
							$('#' + active_style).find('input[name="themeStyle"]').attr('checked', true);
						}
						var active_color = $('.current_active_color').val();
						if (active_color) {
							$('#' + active_color).find('input[name="themeColor"]').attr('checked', true);
						}
						var active_pre_color = $('.current_active_pre_color').val();
						if (active_pre_color) {
							$('#' + active_pre_color).find('input[name="preThemeColor"]').attr('checked', true);
						}
						if (active_pre_color == 'pre_color_3') {
							$('.gradient_tr').css("display", "contents");
						} else {
							$('.gradient_tr').css("display", "none");
						}

						var current_active_style_pallete = data['current_active_style_pallete'];
						if (current_active_style_pallete) {
							$('#' + current_active_style_pallete).find('input[name="themeStyle"]').attr('checked', true);
						}
						var current_active_color_pallete = data['current_active_color_pallete'];
						if (current_active_color_pallete) {
							$('#' + current_active_color_pallete).find('input[name="themeColor"]').attr('checked', true);
						}
						var current_active_pre_color_pallete = data['current_active_pre_color_pallete'];
						if (current_active_pre_color_pallete) {
							$('#' + current_active_pre_color_pallete).find('input[name="preThemeColor"]').attr('checked', true);
						}



						var primary_color = data['primary_color']
						if (primary_color) {
							$('#primary_color_id').val(primary_color);
						}
						var primary_hover = data['primary_hover']
						if (primary_hover) {
							$('#primary_hover_id').val(primary_hover);
						}
						var primary_active = data['primary_active']
						if (primary_active) {
							$('#primary_active_id').val(primary_active);
						}
						var gradient_color = data['gradient_color']
						if (gradient_color) {
							$('#gradient_color').val(gradient_color);
						}



						var secondary_color = data['secondary_color']
						if (secondary_color) {
							$('#secondary_color_id').val(secondary_color);
						}
						var secondary_hover = data['secondary_hover']
						if (secondary_hover) {
							$('#secondary_hover_id').val(secondary_hover);
						}
						var secondary_active = data['secondary_active']
						if (secondary_active) {
							$('#secondary_active_id').val(secondary_active);
						}
						var header_background_color = data['header_background_color']
						if (header_background_color) {
							$('#header_background_color').val(header_background_color);
						}
						var header_font_color = data['header_font_color']
						if (header_font_color) {
							$('#header_font_color').val(header_font_color);
						}
						var header_hover_color = data['header_hover_color']
						if (header_hover_color) {
							$('#header_hover_color').val(header_hover_color);
						}
						var header_active_color = data['header_active_color']
						if (header_active_color) {
							$('#header_active_color').val(header_active_color);
						}
						var body_font_color = data['body_font_color']
						if (body_font_color) {
							$('#body_font_color').val(body_font_color);
						}
						var body_background_color = data['body_background_color']
						if (body_background_color) {
							$('#body_background_color').val(body_background_color);
						}
						var body_font_family = data['body_font_family']
						if (body_font_family) {
							$('#body_font_family').val(body_font_family);
						}


						var body_font_family = $('#body_font_family').val();
						if (body_font_family == 'custom_google_font') {

							$("#body_google_font_family").css("display", "block");
							$("#body_google_font_family_label").css("display", "block");
						} else {
							$("#body_google_font_family").css("display", "none");
							$("#body_google_font_family_label").css("display", "none");
						}
						var body_google_font_family = data['body_google_font_family']
						if (body_google_font_family) {
							$('#body_google_font_family').val(body_google_font_family);
						}

						var body_background_type = data['body_background_type']
						if (body_background_type == 'bg_img') {
							$('#bg_img').attr('checked', true);
							$('#body_background_color').css("display", "none");
							$('#body_background_img').css("display", "block");
						} else if (body_background_type == 'bg_color') {
							$('#bg_color').attr('checked', true);
							$('#body_background_color').css("display", "block");
							$('#body_background_img').css("display", "none");
						}


						var h1_color = data['h1_color']
						if (h1_color) {
							$('#h1_color').val(h1_color);
						}
						var h2_color = data['h2_color']
						if (h2_color) {
							$('#h2_color').val(h2_color);
						}
						var h3_color = data['h3_color']
						if (h3_color) {
							$('#h3_color').val(h3_color);
						}
						var h4_color = data['h4_color']
						if (h4_color) {
							$('#h4_color').val(h4_color);
						}
						var h5_color = data['h5_color']
						if (h5_color) {
							$('#h5_color').val(h5_color);
						}
						var h6_color = data['h6_color']
						if (h6_color) {
							$('#h6_color').val(h6_color);
						}
						var p_color = data['p_color']
						if (p_color) {
							$('#p_color').val(p_color);
						}
						var h1_size = data['h1_size']
						if (h1_size) {
							$('#h1_size').val(h1_size);
						}
						var h2_size = data['h2_size']
						if (h2_size) {
							$('#h2_size').val(h2_size);
						}
						var h3_size = data['h3_size']
						if (h3_size) {
							$('#h3_size').val(h3_size);
						}
						var h4_size = data['h4_size']
						if (h4_size) {
							$('#h4_size').val(h4_size);
						}
						var h5_size = data['h5_size']
						if (h5_size) {
							$('#h5_size').val(h5_size);
						}
						var h6_size = data['h6_size']
						if (h6_size) {
							$('#h6_size').val(h6_size);
						}
						var p_size = data['p_size']
						if (p_size) {
							$('#p_size').val(p_size);
						}
						var button_style = data['button_style']
						if (button_style) {
							$('#button_style').val(button_style);
						}
						var separator_style = data['separator_style']
						if (separator_style) {
							$('#separator_style').val(separator_style);
						}
						var separator_color = data['separator_color']
						if (separator_color) {
							$('#separator_color').val(separator_color);
						}
						var icon_style = data['icon_style']
						if (icon_style) {
							$('#icon_style').val(icon_style);
						}
						var is_button_with_icon_text = data['is_button_with_icon_text']
						if (is_button_with_icon_text) {
							$('#is_button_with_icon_text').attr('checked', true);
						}
						var is_button_with_box_shadow = data['is_button_with_box_shadow']
						if (is_button_with_box_shadow) {
							$('#is_button_with_box_shadow').attr('checked', true);
						}


						var sidebar_font_color = data['sidebar_font_color']
						if (sidebar_font_color) {
							$('#sidebar_font_color').val(sidebar_font_color);
						}
						var sidebar_font_hover_color = data['sidebar_font_hover_color']
						if (sidebar_font_hover_color) {
							$('#sidebar_font_hover_color').val(sidebar_font_hover_color);
						}
						var sidebar_background_style = data['sidebar_background_style']
						if (sidebar_background_style == 'color') {
							$('#sidebar_color').attr('checked', true);
							$('#sidebar_background_color').css("display", "block");
							$('#sidebar_background_img').css("display", "none");

						} else if (sidebar_background_style == 'image') {
							$('#sidebar_image').attr('checked', true);
							$('#sidebar_background_color').css("display", "none");
							$('#sidebar_background_img').css("display", "block");
						}




						var sidebar_background_color = data['sidebar_background_color']
						if (sidebar_background_color) {
							$('#sidebar_background_color').val(sidebar_background_color);
						}
						var sidebar_font_hover_background_color = data['sidebar_font_hover_background_color']
						if (sidebar_font_hover_background_color) {
							$('#sidebar_font_hover_background_color').val(sidebar_font_hover_background_color);
						}

						var sidebar_collapse_style = data['sidebar_collapse_style']
						if (sidebar_collapse_style == 'collapsed') {
							$('#sidebar_collapsed').attr('checked', true);
						} else if (sidebar_collapse_style == 'expanded') {
							$('#sidebar_expanded').attr('checked', true);
						}

						var list_view_border = data['list_view_border']
						if (list_view_border) {
							$('#list_view_border').val(list_view_border);
						}
						var list_view_even_row_color = data['list_view_even_row_color']
						if (list_view_even_row_color) {
							$('#list_view_even_row_color').val(list_view_even_row_color);
						}
						var list_view_odd_row_color = data['list_view_odd_row_color']
						if (list_view_odd_row_color) {
							$('#list_view_odd_row_color').val(list_view_odd_row_color);
						}
						var list_view_is_hover_row = data['list_view_is_hover_row']
						if (list_view_is_hover_row) {
							$('#list_view_is_hover_row').attr('checked', true);
							$(".is_row_color_hover").css("display", "table-row");
						} else {
							$('#list_view_is_hover_row').attr('checked', false);
							$(".is_row_color_hover").css("display", "none");
						}
						var list_view_hover_bg_color = data['list_view_hover_bg_color']
						if (list_view_hover_bg_color) {
							$('#list_view_hover_bg_color').val(list_view_hover_bg_color);
						}
						var login_page_style = data['login_page_style']
						if (login_page_style) {
							$('#login_page_style').val(login_page_style);
						}


						var login_page_box_color = data['login_page_box_color']
						if (login_page_box_color) {
							$('#login_page_box_color').val(login_page_box_color);
						}
						var login_page_background_color = data['login_page_background_color']
						if (login_page_background_color) {
							$('#login_page_background_color').val(login_page_background_color);
						}


						if (login_page_style == 'style_0') {
							$(".login_bg_type").css("display", "none");
							$(".login_box_color").css("display", "none");
							$(".login_bg_img").css("display", "none");
							$(".login_bg_color").css("display", "none");
							$(".login_bg_img_title").css("display", "none");
							$(".login_banner_img").css("display", "none");
							$('.company_icon_image').css("display", "none");
							$('.company_name_image').css("display", "none");
						} else if (login_page_style == 'style_1') {
							$(".login_bg_type").css("display", "none");
							$(".login_box_color").css("display", "none");
							$(".login_bg_img").css("display", "none");
							$(".login_bg_img_title").css("display", "none");
							$(".login_bg_color").css("display", "none");
							$(".login_banner_img").css("display", "none");
							$('.company_icon_image').css("display", "none");
							$('.company_name_image').css("display", "none");
						}
						else if (login_page_style == 'style_2') {

							$(".login_bg_type").css("display", "none");
							$(".login_bg_color").css("display", "none");
							$(".login_box_color").css("display", "block");

							$(".login_bg_img_title").css("display", "none");
							$(".login_bg_img").css("display", "none");


							$(".login_banner_img").css("display", "block");
							$('.company_icon_image').css("display", "none");
							$('.company_name_image').css("display", "none");


						} else if (login_page_style == 'style_3') {

							$(".login_bg_type").css("display", "block");
							$(".login_bg_color").css("display", "block");
							$(".login_box_color").css("display", "none");
							$(".login_bg_img_title").css("display", "block");
							$(".login_bg_img").css("display", "none");

							$(".login_banner_img").css("display", "none");
							$('.company_icon_image').css("display", "block");
							$('.company_name_image').css("display", "block");
							var login_page_background_type = data['login_page_background_type']
							if (login_page_background_type == 'bg_img') {
								$('#login_bg_img').attr('checked', true);
								$('#login_page_background_color').css("display", "none");
								$('#login_page_background_img').css("display", "block");
							} else if (login_page_background_type == 'bg_color') {
								$('#login_bg_color').attr('checked', true);
								$('#login_page_background_color').css("display", "block");
								$('#login_page_background_img').css("display", "none");
							}


						} else if (login_page_style == 'style_4') {

							$(".login_bg_type").css("display", "block");

							$(".login_bg_color").css("display", "block");
							$(".login_box_color").css("display", "none");
							$(".login_bg_img_title").css("display", "block");
							$(".login_bg_img").css("display", "none");


							$(".login_banner_img").css("display", "none");
							$('.company_icon_image').css("display", "block");
							$('.company_name_image').css("display", "none");
							var login_page_background_type = data['login_page_background_type']
							if (login_page_background_type == 'bg_img') {
								$('#login_bg_img').attr('checked', true);
								$('#login_page_background_color').css("display", "none");
								$('#login_page_background_img').css("display", "block");
							} else if (login_page_background_type == 'bg_color') {
								$('#login_bg_color').attr('checked', true);
								$('#login_page_background_color').css("display", "block");
								$('#login_page_background_img').css("display", "none");
							}

						}



						var is_sticky_form = data['is_sticky_form']
						if (is_sticky_form) {
							$('#is_sticky_form').attr('checked', true);
						}
						var is_sticky_chatter = data['is_sticky_chatter']
						if (is_sticky_chatter) {
							$('#is_sticky_chatter').attr('checked', true);
						}
						var is_sticky_list = data['is_sticky_list']
						if (is_sticky_list) {
							$('#is_sticky_list').attr('checked', true);
						}
						var is_sticky_list_inside_form = data['is_sticky_list_inside_form']
						if (is_sticky_list_inside_form) {
							$('#is_sticky_list_inside_form').attr('checked', true);
						}
						var modal_popup_style = data['modal_popup_style']
						if (modal_popup_style) {
							$('#modal_popup_style').val(modal_popup_style);
						}


						var tab_style = data['tab_style']
						if (tab_style == 'horizontal') {
							$('#tab_horizontal').attr('checked', true);
						} else if (tab_style == 'vertical') {
							$('#tab_vertical').attr('checked', true);
						}

						var tab_mobile_style = data['tab_mobile_style']
						if (tab_mobile_style == 'horizontal') {
							$('#tab_mobile_horizontal').attr('checked', true);
						} else if (tab_mobile_style == 'vertical') {
							$('#tab_mobile_vertical').attr('checked', true);
						}


						var horizontal_tab_style = data['horizontal_tab_style']
						if (horizontal_tab_style) {
							$('#horizontal_tab_style').val(horizontal_tab_style);
						}


						var vertical_tab_style = data['vertical_tab_style']
						if (vertical_tab_style) {
							$('#vertical_tab_style').val(vertical_tab_style);
						}
						var form_element_style = data['form_element_style']
						if (form_element_style) {
							$('#form_element_style').val(form_element_style);
						}

						var search_style = data['search_style']
						if (search_style == 'collapsed') {
							$('#search_collapsed').attr('checked', true);
						} else if (search_style == 'expanded') {
							$('#search_expanded').attr('checked', true);
						}

						var breadcrumb_style = data['breadcrumb_style']
						if (breadcrumb_style) {
							$('#breadcrumb_style').val(breadcrumb_style);
						}
						var chatter_position = data['chatter_position']
						if (chatter_position == 'normal') {
							$('#chatter_position_normal').attr('checked', true);
						} else if (chatter_position == 'sided') {
							$('#chatter_position_sided').attr('checked', true);
						}

						var loading_style = data['loading_style']
						if (loading_style) {
							$('#loading_style').val(loading_style);
						}
						var progress_style = data['progress_style']
						if (progress_style) {
							$('#progress_style').val(progress_style);
						}
						var progress_height = data['progress_height']
						if (progress_height) {
							$('#progress_height').val(progress_height);
						}


						if (progress_style == 'style_1') {
							$("#progress_color_height").css("display", "table-row");
						} else {
							$("#progress_color_height").css("display", "none");
						}
						var progress_color = data['progress_color']
						if (progress_color) {
							$('#progress_color').val(progress_color);
						}


					});
				});

			}
		});

		$('.o_web_client').on('click', '.theme_style_box', function (ev) {
			ev.stopPropagation();
			ev.preventDefault();

			_.each($('.theme_style_box'), function (event) {
				$(event).removeClass('active');
				$(event).find('input[name="themeStyle"]').attr('checked', false);
			})

			var color_id = $(ev.currentTarget).attr('id');

			$(ev.currentTarget).addClass('active');
			$(ev.currentTarget).find('input[name="themeStyle"]').attr('checked', true);

			color_change = true;
			ajax.jsonRpc('/update/theme_style', 'call',
				{ 'color_id': color_id }).then(function () {
					location.reload();
				});
		});

		$('.o_web_client').on('click', '.theme_color_box', function (ev) {
			ev.stopPropagation();
			ev.preventDefault();

			var color_id = $(ev.currentTarget).attr('id');

			_.each($('.theme_color_box'), function (event) {
				$(event).removeClass('active');
				$(event).find('input[name="themeColor"]').attr('checked', false);
			})


			$(ev.currentTarget).addClass('active');
			$(ev.currentTarget).find('input[name="themeColor"]').attr('checked', true);

			color_change = true;
			ajax.jsonRpc('/update/theme_style_color', 'call',
				{ 'color_id': color_id }).then(function () {
					location.reload();
				});
		});
		$('.o_web_client').on('click', '.pre_theme_color_box', function (ev) {
			ev.stopPropagation();
			ev.preventDefault();

			var pre_color_id = $(ev.currentTarget).attr('id');

			_.each($('.pre_theme_color_box'), function (event) {
				$(event).removeClass('active');
				$(event).find('input[name="preThemeColor"]').attr('checked', false);
			})


			$(ev.currentTarget).addClass('active');
			$(ev.currentTarget).find('input[name="preThemeColor"]').attr('checked', true);

			if (pre_color_id == 'pre_color_3') {
				$('.gradient_tr').css("display", "contents");
			} else {
				$('.gradient_tr').css("display", "none");
			}

			color_change = true;
			ajax.jsonRpc('/update/theme_style_pre_color', 'call',
				{ 'pre_color_id': pre_color_id }).then(function () {
					location.reload();
				});
		});

		$('.o_web_client').on('click', '.discard_color', function (ev) {
			location.reload();
		});

		$('.o_web_client').on('click', '.save_color', function (ev) {
			if (color_change == false) {


				var primary_color_id = $('#primary_color_id').val();
				var primary_hover_id = $('#primary_hover_id').val();
				var primary_active_id = $('#primary_active_id').val();
				var gradient_color = $('#gradient_color').val();
				var secondary_color_id = $('#secondary_color_id').val();
				var secondary_hover_id = $('#secondary_hover_id').val();
				var secondary_active_id = $('#secondary_active_id').val();
				var header_background_color = $("#header_background_color").val();
				var header_font_color = $("#header_font_color").val();
				var header_hover_color = $("#header_hover_color").val();
				var header_active_color = $("#header_active_color").val();
				var body_font_color = $("#body_font_color").val();
				var body_background_color = $("#body_background_color").val();
				var body_font_family = $("#body_font_family").val();
				var body_google_font_family = $("#body_google_font_family").val();
				var body_background_type = $("input[name='body_background_type']:checked").val();
				var h1_color = $('#h1_color').val();
				var h2_color = $('#h2_color').val();
				var h3_color = $('#h3_color').val();
				var h4_color = $('#h4_color').val();
				var h5_color = $('#h5_color').val();
				var h6_color = $('#h6_color').val();
				var p_color = $('#p_color').val();
				var h1_size = $('#h1_size').val();
				var h2_size = $('#h2_size').val();
				var h3_size = $('#h3_size').val();
				var h4_size = $('#h4_size').val();
				var h5_size = $('#h5_size').val();
				var h6_size = $('#h6_size').val();
				var p_size = $('#p_size').val();
				var button_style = $("#button_style").val();
				var separator_style = $("#separator_style").val();
				var separator_color = $("#separator_color").val();
				var icon_style = $("#icon_style").val();
				var is_button_with_icon_text = $("#is_button_with_icon_text").prop("checked");
				var is_button_with_box_shadow = $("#is_button_with_box_shadow").prop("checked");
				var body_background_img = $('#body_background_img').val();
				var sidebar_font_color = $('#sidebar_font_color').val();
				//				var sidebar_background_type = $("input[name='sidebar_background_type']:checked").val();
				var sidebar_font_hover_color = $('#sidebar_font_hover_color').val();
				var sidebar_background_color = $('#sidebar_background_color').val();
				var sidebar_background_style = $("input[name='sidebar_background_style']:checked").val();
				var sidebar_background_img = $('#sidebar_background_img').val();
				var sidebar_font_hover_background_color = $('#sidebar_font_hover_background_color').val();
				//			var sidebar_is_show_navbar = $("#sidebar_is_show_navbar").prop("checked");
				var sidebar_collapse_style = $("input[name='sidebar_collapse_style']:checked").val();
				var list_view_border = $("#list_view_border").val();
				var list_view_even_row_color = $("#list_view_even_row_color").val();
				var list_view_odd_row_color = $("#list_view_odd_row_color").val();
				var list_view_is_hover_row = $("#list_view_is_hover_row").prop("checked");
				var list_view_hover_bg_color = $("#list_view_hover_bg_color").val();
				var login_page_style = $("#login_page_style").val();
				var login_page_background_type = $("input[name='login_page_background_type']:checked").val();
				var login_page_box_color = $("#login_page_box_color").val();
				var login_page_background_color = $("#login_page_background_color").val();

				var is_sticky_form = $("#is_sticky_form").prop("checked");
				var is_sticky_chatter = $("#is_sticky_chatter").prop("checked");
				var is_sticky_list = $("#is_sticky_list").prop("checked");
				var is_sticky_list_inside_form = $("#is_sticky_list_inside_form").prop("checked");
				var modal_popup_style = $("#modal_popup_style").val();

				var tab_style = $("input[name='tab_style']:checked").val();
				var tab_style_mobile = $("input[name='tab_mobile_style']:checked").val();
				var horizontal_tab_style = $("#horizontal_tab_style").val();
				var vertical_tab_style = $("#vertical_tab_style").val();
				var form_element_style = $("#form_element_style").val();
				var search_style = $("input[name='search_style']:checked").val();
				var breadcrumb_style = $("#breadcrumb_style").val();
				var chatter_position = $("input[name='chatter_position']:checked").val();
				var loading_style = $("#loading_style").val();
				var progress_style = $("#progress_style").val();
				var progress_height = $("#progress_height").val();
				var progress_color = $("#progress_color").val();

				var form = $('#body_background_img')[0];
				var data = new FormData(form);
				$.ajax({
					type: "POST",
					enctype: 'multipart/form-data',
					url: "/api/upload/multi",
					data: data,
					processData: false,
					contentType: false,
					cache: false,
					timeout: 600000,
					success: function (data) {

						console.log("SUCCESS : ", data);
						location.reload();
					},
					error: function (e) {

						console.log("ERROR : ", e);

					}
				});


				var sidebar_background_img_form = $('#sidebar_background_img')[0];
				var data5 = new FormData(sidebar_background_img_form);
				$.ajax({
					type: "POST",
					enctype: 'multipart/form-data',
					url: "/api/upload/multi",
					data: data5,
					processData: false,
					contentType: false,
					cache: false,
					timeout: 600000,
					success: function (data) {

						console.log("SUCCESS : ", data);
						location.reload();
					},
					error: function (e) {

						console.log("ERROR : ", e);

					}
				});


				var login_page_banner_img = $('#login_page_banner_img')[0];
				var data2 = new FormData(login_page_banner_img);
				$.ajax({
					type: "POST",
					enctype: 'multipart/form-data',
					url: "/api/upload/multi",
					data: data2,
					processData: false,
					contentType: false,
					cache: false,
					timeout: 600000,
					success: function (data) {

						console.log("SUCCESS : ", data);
						location.reload();
					},
					error: function (e) {

						console.log("ERROR : ", e);

					}
				});
				var login_page_icon_img = $('#login_page_icon_img')[0];
				var data2 = new FormData(login_page_icon_img);
				$.ajax({
					type: "POST",
					enctype: 'multipart/form-data',
					url: "/api/upload/multi",
					data: data2,
					processData: false,
					contentType: false,
					cache: false,
					timeout: 600000,
					success: function (data) {

						console.log("SUCCESS : ", data);
						location.reload();
					},
					error: function (e) {

						console.log("ERROR : ", e);

					}
				});
				var login_page_icon_img_long = $('#login_page_icon_img_long')[0];
				var data2 = new FormData(login_page_icon_img_long);
				$.ajax({
					type: "POST",
					enctype: 'multipart/form-data',
					url: "/api/upload/multi",
					data: data2,
					processData: false,
					contentType: false,
					cache: false,
					timeout: 600000,
					success: function (data) {

						console.log("SUCCESS : ", data);
						location.reload();
					},
					error: function (e) {

						console.log("ERROR : ", e);

					}
				});

				var login_page_background_img = $('#login_page_background_img')[0];
				var data3 = new FormData(login_page_background_img);
				$.ajax({
					type: "POST",
					enctype: 'multipart/form-data',
					url: "/api/upload/multi",
					data: data3,
					processData: false,
					contentType: false,
					cache: false,
					timeout: 600000,
					success: function (data) {

						console.log("SUCCESS : ", data);
						location.reload();
					},
					error: function (e) {

						console.log("ERROR : ", e);

					}
				});

				var loading_gif = $('#loading_gif')[0];
				var data4 = new FormData(loading_gif);
				$.ajax({
					type: "POST",
					enctype: 'multipart/form-data',
					url: "/api/upload/multi",
					data: data4,
					processData: false,
					contentType: false,
					cache: false,
					timeout: 600000,
					success: function (data) {

						console.log("SUCCESS : ", data);
						location.reload();
					},
					error: function (e) {

						console.log("ERROR : ", e);

					}
				});

				ajax.jsonRpc('/update/theme_color', 'call', {
					'primary_color_id': primary_color_id,
					'primary_hover_id': primary_hover_id,
					'primary_active_id': primary_active_id,
					'gradient_color': gradient_color,
					'secondary_color_id': secondary_color_id,
					'secondary_hover_id': secondary_hover_id,
					'secondary_active_id': secondary_active_id,
					'header_background_color': header_background_color,
					'header_font_color': header_font_color,
					'header_hover_color': header_hover_color,
					'header_active_color': header_active_color,
					'body_font_color': body_font_color,
					'body_background_color': body_background_color,
					'body_font_family': body_font_family,
					'body_google_font_family': body_google_font_family,
					'body_background_type': body_background_type,
					'h1_color': h1_color,
					'h2_color': h2_color,
					'h3_color': h3_color,
					'h4_color': h4_color,
					'h5_color': h5_color,
					'h6_color': h6_color,
					'p_color': p_color,
					'h1_size': h1_size,
					'h2_size': h2_size,
					'h3_size': h3_size,
					'h4_size': h4_size,
					'h5_size': h5_size,
					'h6_size': h6_size,
					'p_size': p_size,
					'button_style': button_style,
					'separator_style': separator_style,
					'separator_color': separator_color,
					'icon_style': icon_style,
					'is_button_with_icon_text': is_button_with_icon_text,
					'is_button_with_box_shadow': is_button_with_box_shadow,
					'sidebar_font_color': sidebar_font_color,
					//					'sidebar_background_type':sidebar_background_type,
					'sidebar_font_hover_color': sidebar_font_hover_color,
					'sidebar_background_style': sidebar_background_style,
					'sidebar_background_color': sidebar_background_color,
					'sidebar_font_hover_background_color': sidebar_font_hover_background_color,
					//				'sidebar_is_show_navbar':sidebar_is_show_navbar,
					'sidebar_collapse_style': sidebar_collapse_style,
					'list_view_border': list_view_border,
					'list_view_even_row_color': list_view_even_row_color,
					'list_view_odd_row_color': list_view_odd_row_color,
					'list_view_is_hover_row': list_view_is_hover_row,
					'list_view_hover_bg_color': list_view_hover_bg_color,
					'login_page_style': login_page_style,
					'login_page_background_type': login_page_background_type,
					'login_page_box_color': login_page_box_color,
					'login_page_background_color': login_page_background_color,
					'is_sticky_form': is_sticky_form,
					'is_sticky_chatter': is_sticky_chatter,
					'is_sticky_list': is_sticky_list,
					'is_sticky_list_inside_form': is_sticky_list_inside_form,
					'modal_popup_style': modal_popup_style,
					'tab_style': tab_style,
					'tab_style_mobile': tab_style_mobile,
					'horizontal_tab_style': horizontal_tab_style,
					'vertical_tab_style': vertical_tab_style,
					'form_element_style': form_element_style,
					'search_style': search_style,
					'breadcrumb_style': breadcrumb_style,
					'chatter_position': chatter_position,
					'loading_style': loading_style,
					'progress_style': progress_style,
					'progress_height': progress_height,
					'progress_color': progress_color,
				}).then(function () {
					location.reload();
				});

			}
		});
		$('.o_web_client').on('click', "#progress_style", function (ev) {
			var progress_style = $("#progress_style").val();
			if (progress_style == 'style_1') {
				$("#progress_color_height").css("display", "table-row");
			} else {
				$("#progress_color_height").css("display", "none");
			}
		});

		$('.o_web_client').on('click', "input[name='body_background_type']", function (ev) {

			var radioValue = $("input[name='body_background_type']:checked").val();
			if (radioValue == 'bg_color') {
				$('#body_background_color').css("display", "block");
				$('#body_background_img').css("display", "none");
			} else {
				$('#body_background_color').css("display", "none");
				$('#body_background_img').css("display", "block");
			}
		});

		$('.o_web_client').on('click', "input[name='sidebar_background_style']", function (ev) {

			var radioValue = $("input[name='sidebar_background_style']:checked").val();
			if (radioValue == 'color') {
				$('#sidebar_background_color').css("display", "block");
				$('#sidebar_background_img').css("display", "none");
			} else {
				$('#sidebar_background_color').css("display", "none");
				$('#sidebar_background_img').css("display", "block");
			}
		});

		$('.o_web_client').on('click', "#list_view_is_hover_row", function (ev) {
			var list_view_is_hover_row = $("#list_view_is_hover_row").prop("checked");
			if (list_view_is_hover_row) {
				$(".is_row_color_hover").css("display", "table-row");
			} else {
				$(".is_row_color_hover").css("display", "none");
			}
		});
		$('.o_web_client').on('change', "#body_font_family", function (ev) {
			var body_font_family = $('#body_font_family').val();
			if (body_font_family == 'custom_google_font') {

				$("#body_google_font_family").css("display", "block");
				$("#body_google_font_family_label").css("display", "block");
			} else {
				$("#body_google_font_family").css("display", "none");
				$("#body_google_font_family_label").css("display", "none");
			}
		});
		$('.o_web_client').on('change', "#login_page_style", function (ev) {
			var login_page_style = $('#login_page_style').val();
			if (login_page_style == 'style_0') {
				$(".login_bg_type").css("display", "none");
				$(".login_box_color").css("display", "none");
				$(".login_bg_img").css("display", "none");
				$(".login_bg_color").css("display", "none");
				$(".login_bg_img_title").css("display", "none");
				$(".login_banner_img").css("display", "none");
				$('.company_icon_image').css("display", "none");
				$('.company_name_image').css("display", "none");
			} else if (login_page_style == 'style_1') {
				$(".login_bg_type").css("display", "none");
				$(".login_box_color").css("display", "none");
				$(".login_bg_img").css("display", "none");
				$(".login_bg_img_title").css("display", "none");
				$(".login_bg_color").css("display", "none");
				$(".login_banner_img").css("display", "none");
				$('.company_icon_image').css("display", "none");
				$('.company_name_image').css("display", "none");
			}
			else if (login_page_style == 'style_2') {

				$(".login_bg_type").css("display", "none");
				$(".login_bg_color").css("display", "none");
				$(".login_box_color").css("display", "block");
				$(".login_bg_img_title").css("display", "none");
				$(".login_bg_img").css("display", "none");
				$(".login_box_color").val("#FFFFFF");

				$(".login_banner_img").css("display", "block");
				$('.company_icon_image').css("display", "none");
				$('.company_name_image').css("display", "none");


			} else if (login_page_style == 'style_3') {

				$(".login_bg_type").css("display", "block");
				$(".login_box_color").css("display", "none");
				$(".login_bg_img_title").css("display", "block");

				$(".login_bg_img_title").css("display", "block");
				$("#login_bg_img").attr('checked', true);
				$(".login_bg_img").css("display", 'block');
				$(".login_bg_color").css("display", "none");


				$(".login_banner_img").css("display", "none");
				$('.company_icon_image').css("display", "block");
				$('.company_name_image').css("display", "block");


			} else if (login_page_style == 'style_4') {

				$(".login_bg_type").css("display", "block");

				$(".login_box_color").css("display", "none");

				$(".login_bg_img_title").css("display", "block");
				$("#login_bg_img").attr('checked', true);
				$(".login_bg_img").css("display", 'block');
				$(".login_bg_color").css("display", "none");

				$(".login_banner_img").css("display", "none");
				$('.company_icon_image').css("display", "block");
				$('.company_name_image').css("display", "none");


			}

		});
		$('.o_web_client').on('click', "input[name='login_page_background_type']", function (ev) {
			var radioValue = $("input[name='login_page_background_type']:checked").val();
			if (radioValue == 'bg_color') {
				$('#login_page_background_color').css("display", "block");
				$('#login_page_background_img').css("display", "none");
			} else {
				$('#login_page_background_color').css("display", "none");
				$('#login_page_background_img').css("display", "block");
			}
		});
		$('.o_web_client').on('click', ".o_action_manager", function (ev) {
			//$('.sh_search_results').css("display","none");
			$('.backmate_theme_layout').removeClass("sh_theme_model");
			if ($('.sh_calc_util').hasClass('active')) {
				$('.open_calc').click();
			}
			//	$('.o_action_manager').css("margin-right","0px")
			$('.sh_search_results').css("display", "none");
		});
	});
});;
