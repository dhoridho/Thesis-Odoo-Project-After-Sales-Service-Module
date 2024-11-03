# -*- coding: utf-8 -*-
{
	'name': 'List View Manager',

	'summary': """
List view search,Global Search,Quick Search,Search engine,advance 
        filter,Field Search,advanced search,Tree view,document management 
        system,Resize columns,Export Current View,auto suggestion,Hide column,
        show column,rename column,reorder column
""",

	'description': """
List View ,
	Advance Search ,
	Read/Edit Mode ,
	Dynamic List ,
	Hide/Show list view columns ,
	List View Manager ,
	Odoo List View ,
	Odoo Advanced Search ,
	Odoo Connector ,
	Odoo Manage List View ,
	Drag and edit columns ,
	Dynamic List View Apps , 
	Advance Dynamic Tree View ,
	Dynamic Tree View Apps ,
	Advance Tree View Apps ,
	List/Tree View Apps ,
	Tree/List View Apps  ,
	Freeze List View Header ,
	List view Advance Search ,
	Tree view Advance Search ,
	Best List View Apps ,
	Best Tree View Apps ,
	Tree View Apps ,
	List View Apps ,
	List View Management Apps ,
	Treeview ,
	Listview ,
	Tree View ,
	one2many view, 
        list one2many view, 
        sticky header, 
        report templates, 
        sale order lists, 
        approval check lists, 
        pos order lists, 
        orders list in odoo,
        top app, 
        best app, 
        best apps
""",

	'author': 'Ksolves India Ltd.',

	'sequence': 1,

	'website': 'https://store.ksolves.com/',

	'live_test_url': 'https://listview14.kappso.com/web/demo_login',

	'category': 'Tools',

	'version': '14.0.1.3.41',

	'depends': ['base', 'base_setup'],

	'license': 'OPL-1',

	'currency': 'EUR',

	'price': 136.8,

	'maintainer': 'Ksolves India Ltd.',

	'support': 'sales@ksolves.com',

	'images': ['static/description/Financial_Year_sale.gif'],

	'data': ['views/ks_list_view_manager_assets.xml', 'views/ks_res_config_settings.xml', 'security/ir.model.access.csv', 'security/ks_security_groups.xml'],

	'qweb': ['static/src/xml/ks_list_templates.xml', 'static/src/xml/ks_advance_search.xml', 'static/src/xml/ks_cancel_edit_template.xml', 'static/src/xml/ks_lvm_button.xml'],

	'post_init_hook': 'post_install_hook',

	'uninstall_hook': 'uninstall_hook',
}
