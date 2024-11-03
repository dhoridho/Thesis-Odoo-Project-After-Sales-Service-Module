# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields
import base64

class res_company(models.Model):
    _inherit = 'res.company'
    
    company_name_logo = fields.Binary(string="Company Name Logo")
 
class sh_back_theme_config_settings(models.Model):
    _name = 'sh.back.theme.config.settings'
    _description = 'Back Theme Config Settings'    

    name = fields.Char(string="Theme Settings")
    
    theme_color = fields.Selection([
        ('color_1','Blue'),
        ('color_2','Cyan'),
        ('color_3','Deep Orange'),
        ('color_4','Green'),
        ('color_5','Orange'),
        ('color_6','Navy Blue'),
        ('color_7','Green'),
        ],string = "Theme Color")
    
    theme_style = fields.Selection([
        ('style_1','Style 1'),
        ('style_2','Style 2'),
        ('style_3','Style 3')
        ],string = "Theme Style")
    
    pre_theme_style = fields.Selection([
        ('pre_color_1','Style 1'),
        ('pre_color_2','Style 2'),
        ('pre_color_3','Style 3')
        ],string ="Pre defined Theme Style")
    
    primary_color = fields.Char(string = 'Primary Color')
    primary_hover = fields.Char(string = 'Primary Hover')    
    primary_active = fields.Char(string = 'Primary Active')
    gradient_color = fields.Char(string="Gradient Color")
    
    secondary_color = fields.Char(string = 'Secondary Color')
    secondary_hover = fields.Char(string = 'Secondary Hover')    
    secondary_active = fields.Char(string = 'Secondary Active')        
    
    header_background_color = fields.Char(string = 'Header Background Color')
    header_font_color =  fields.Char(string = 'Header Font Color')
    header_hover_color = fields.Char(string = 'Header Hover Color')
    header_active_color = fields.Char(string = 'Header Active Color')    
    
    
    h1_color = fields.Char(string = 'H1 Color')
    h2_color = fields.Char(string = 'H2 Color')    
    h3_color = fields.Char(string = 'H3 Color')
    h4_color = fields.Char(string = 'H4 Color')
    h5_color = fields.Char(string = 'H5 Color')
    h6_color = fields.Char(string = 'H6 Color')
    p_color = fields.Char(string = 'P Color')
    
    h1_size = fields.Integer(string = 'H1 Size')
    h2_size = fields.Integer(string = 'H2 Size')    
    h3_size = fields.Integer(string = 'H3 Size')
    h4_size = fields.Integer(string = 'H4 Size')
    h5_size = fields.Integer(string = 'H5 Size')
    h6_size = fields.Integer(string = 'H6 Size')
    p_size = fields.Integer(string = 'P Size')    
    
    body_font_color = fields.Char(string = 'Body Font Color')
    body_background_type = fields.Selection([
        ('bg_color','Color'),
        ('bg_img','Image')
        ],string = "Body Background Type", default = "bg_color")    
    
    body_background_color = fields.Char(string = 'Body Background Color')   
    body_background_image = fields.Binary(string = 'Body Background Image')


    body_font_family = fields.Selection([
        ('Roboto','Roboto'),
        ('Raleway','Raleway'),
        ('Poppins','Poppins'),
        ('Oxygen','Oxygen'),
        ('OpenSans','OpenSans'),
        ('KoHo','KoHo'),
        ('Ubuntu','Ubuntu'),
        ('custom_google_font','Custom Google Font'),        
        ],string = 'Body Font Family')
    
    body_google_font_family = fields.Char(string = "Google Font Family")
    is_used_google_font = fields.Boolean(string = "Is use google font?")
 
    button_style = fields.Selection([
        ('style_1','Style 1'),
        ('style_2','Style 2'),
        ('style_3','Style 3'),        
        ('style_4','Style 4'),   
        ('style_5','Style 5'),           
        ],string = 'Button Style')
    is_button_with_icon_text = fields.Boolean(string = "Button with text and icon?")
    is_button_with_box_shadow = fields.Boolean(string = "Button with Box shadow?")
        
    separator_style = fields.Selection([
        ('style_1','Style 1'),
        ('style_2','Style 2'),
        ('style_3','Style 3'),        
        ('style_4','Style 4'),   
        ('style_5','Style 5'),   
        ('style_6','Style 6'),  
        ('style_7','Style 7'),                        
        ],string = 'Separator Style')  
    
    separator_color = fields.Char(string = "Separator Color")
    
    
   
    sidebar_background_style = fields.Selection([('color','Color'),('image','Image')],default='color')
    sidebar_background_image = fields.Binary(string = 'Sidebar Background Image')
    sidebar_background_color = fields.Char(string = 'Sidebar Background Color')   
        
    sidebar_font_color =  fields.Char(string = 'Sidebar Font Color')
    sidebar_font_hover_color = fields.Char(string = 'Sidebar Font Hover Color')    
    sidebar_font_hover_background_color = fields.Char(string = 'Sidebar Font Hover Background Color')  
  
    
    sidebar_is_show_nav_bar = fields.Boolean(string = "Top Bar?")
    sidebar_collapse_style = fields.Selection([
        ('collapsed','Collapsed'),
        ('expanded','Expanded')                                            
        ], string = 'Sidebar View Style')            
    
    
    loading_style = fields.Selection([
        ('style_1', 'Style 1'),
        ('style_2', 'Style 2'),
        ('style_3', 'Style 3'),
        ('style_4', 'Style 4'),
        ('style_5', 'Style 5'),
        ('style_6', 'Style 6'),
        ('style_7', 'Style 7'),
        ('style_8', 'Style 8'),
        ('style_9', 'Style 9'),
        ('style_10', 'Style 10'),
        ('style_11', 'Style 11'),
        ('style_12', 'Style 12'),
        ], string='Loading Style', default="style_1")

    progress_style = fields.Selection([
        ('style_1', 'Style 1'),
        ('none', 'None'),
        ], string='Progress Bar Style', default="style_1")


    progress_height = fields.Char("Height")
    progress_color = fields.Char("Color")

    
    loading_gif = fields.Binary(string = "Loading GIF",attachment=False) 
    loading_gif_file_name = fields.Char(string = "Loading GIF File Name")


    list_view_border = fields.Selection([
        ('bordered','Bordered'),
        ('without_border','Without Border')
        ], default = 'without_border', string = "List View Border")
    
    list_view_is_hover_row = fields.Boolean(string = "Rows Hover?")
    list_view_hover_bg_color = fields.Char(string = "Hover Background Color")
    list_view_even_row_color = fields.Char(string = "Even Row Color")
    list_view_odd_row_color = fields.Char(string = "Odd Row Color")
    
    
    login_page_style = fields.Selection([
        ('style_0','Odoo Standard'),
        ('style_1','Style 1'),
        ('style_2','Style 2'),  
        ('style_3','Style 3'),  
         ('style_4','Style 4'),                
        ],default = "style_0", string = "Style")
    
    login_page_background_type = fields.Selection([
        ('bg_color','Color'),
        ('bg_img','Image')
        ],string = "Background Type", default = "bg_color")    
    
    login_page_background_color = fields.Char(string = 'Background Color')   
    login_page_background_image = fields.Binary(string = 'Background Image',attachment=False)    
    login_page_box_color = fields.Char(string = 'Box Color')      
    login_page_banner_image = fields.Char(string = 'Banner Image',attachment=False)
    login_page_icon_img = fields.Char(string = 'Login Icon Image',attachment=False)
    login_page_icon_img_long = fields.Char(string = 'Login Icon Image',attachment=False)
    #Sticky
    is_sticky_form = fields.Boolean(string = "Form Status Bar")
    is_sticky_chatter = fields.Boolean(string = "Chatter")
    is_sticky_list = fields.Boolean(string = "List View")
    is_sticky_list_inside_form = fields.Boolean(string = "List View Inside Form")
                
    #icon style
    icon_style = fields.Selection([('standard','Standard'),('2d','2D'),('3d','3D')],string="Icon Style",
                                  default='standard')
    #Modal Popup
    modal_popup_style = fields.Selection([
        ('style_1','Style 1'),
        ('style_2','Style 2'),
        ('style_3','Style 3'),        
        ('style_4','Style 4'),   
        ('style_5','Style 5'),   
        ('style_6','Style 6'),   
        ('style_7','Style 7'),   
        ('style_8','Style 8'),   
        ('style_9','Style 9'),     
        ('style_10','Style 10'),                                                
        ],string = 'Popup Style')  
    
    
    tab_style = fields.Selection([('horizontal','Horizontal'),('vertical','Vertical')],string="Tab Style (Desktop)",default='horizontal')    
    tab_style_mobile = fields.Selection([('horizontal','Horizontal'),('vertical','Vertical')],string="Tab Style (Mobile)",default='horizontal')                    
    
    horizontal_tab_style = fields.Selection([
        ('style_1','Style 1'),
        ('style_2','Style 2'),
        ('style_3','Style 3'),
        ('style_4','Style 4'),
        ('style_5','Style 5'),
        ('style_6','Style 6'),
        ('style_7','Style 7'),       
        ],string = 'Horizontal Tab Style',default='style_1') 
    
    vertical_tab_style = fields.Selection([
        ('style_1','Style 1'),
        ('style_2','Style 2'),
        ('style_3','Style 3'),    
        ('style_4','Style 4'),
        ('style_5','Style 5'),
        ('style_6','Style 6'),
        ('style_7','Style 7'),     
        ],string = 'Vertical Tab Style',default='style_1')
    
    
    form_element_style = fields.Selection([
        ('style_1','Style 1'),
        ('style_2','Style 2'),
        ('style_3','Style 3'), 
        ('style_4','Style 4'),   
        ('style_5','Style 5'),
        ('style_6','Style 6'),
        ('style_7','Style 7'),   
        ('style_8','Style 8'),
        ],string = 'Form Element Style',default='style_1') 
    
    search_style = fields.Selection([('collapsed','Collapsed'),
        ('expanded','Expanded')],string="Search Style (Desktop)",default='collapsed')
    
    breadcrumb_style = fields.Selection([
        ('style_1','Style 1'),
        ('style_2','Style 2'),
        ('style_3','Style 3'),
        ('style_4','Style 4'),
        ('style_5','Style 5'),
        ('style_6','Style 6'),
        ('style_7','Style 7'), 
        ],string = 'Breadcrumb Style',default='style_1') 

    chatter_position = fields.Selection([('normal','Normal'),('sided','Sided')],string="Chatter Position",default='normal')
    
        
    def search_primary_var_template(self):
        if self.env.ref('sh_backmate_theme_adv.sh_assets_primary_variables'):
            return self.env.ref('sh_backmate_theme_adv.sh_assets_primary_variables').active
    
    def deactivate_primary_variable_scss(self):
        if self.env.ref('sh_backmate_theme_adv.sh_assets_primary_variables'):
            self.env.ref('sh_backmate_theme_adv.sh_assets_primary_variables').write({'active':False})
        if self.env.ref('sh_backmate_theme_adv.sh_assets_night_variable_scss'):
            self.env.ref('sh_backmate_theme_adv.sh_assets_night_variable_scss').write({'active':False})
        if self.env.ref('sh_backmate_theme_adv.sh_assets_background_color_scss'):
            self.env.ref('sh_backmate_theme_adv.sh_assets_background_color_scss').write({'active':True})
        if self.env.ref('sh_backmate_theme_adv.sh_assets_night_scss'):
            self.env.ref('sh_backmate_theme_adv.sh_assets_night_scss').write({'active':True})
            
        return True
    
    def activate_primary_variable_scss(self):
        if self.env.ref('sh_backmate_theme_adv.sh_assets_primary_variables'):
            self.env.ref('sh_backmate_theme_adv.sh_assets_primary_variables').write({'active':True})
        if self.env.ref('sh_backmate_theme_adv.sh_assets_night_variable_scss'):
            self.env.ref('sh_backmate_theme_adv.sh_assets_night_variable_scss').write({'active':True})
        if self.env.ref('sh_backmate_theme_adv.sh_assets_background_color_scss'):
            self.env.ref('sh_backmate_theme_adv.sh_assets_background_color_scss').write({'active':False})
        if self.env.ref('sh_backmate_theme_adv.sh_assets_night_scss'):
            self.env.ref('sh_backmate_theme_adv.sh_assets_night_scss').write({'active':False})
            
        return True

#     @api.onchange('body_font_family')
#     def onchage_body_font_family(self):
#         if self.body_font_family == 'custom_google_font':
#             self.is_used_google_font = True
#         else:
#             self.is_used_google_font = False
#             self.body_google_font_family = False
        
    
#     def action_preview_theme_style(self):
#         if self:
#             
#             context = dict(self.env.context or {})
#             img_src = ""
#             if context and context.get('which_style','') == 'theme':
#                 img_src = "/sh_backmate_theme_adv/static/src/img/preview/theme/style_theme.png"
#                 
#             if context and context.get('which_style','') == 'button':
#                 img_src = "/sh_backmate_theme_adv/static/src/img/preview/button/style_button.png"
#                                 
#             if context and context.get('which_style','') == 'separator':
#                 img_src = "/sh_backmate_theme_adv/static/src/img/preview/separator/style_separator.png"
# 
#             if context and context.get('which_style','') == 'sidebar':
#                 img_src = "/sh_backmate_theme_adv/static/src/img/preview/sidebar/style sidebar.png"
#                 
#             if context and context.get('which_style','') == 'login_page':
#                 img_src = "/sh_backmate_theme_adv/static/src/img/preview/login_page/style_login.jpg"
#                 
#                             
#             context['default_img_src'] = img_src
#             
#             return {
#                 'name': _('Preview Style'),
#                 'view_mode': 'form',
#                 'res_model': 'sh.theme.preview.wizard',
#                 'view_id': self.env.ref('sh_backmate_theme_adv.sh_back_theme_config_theme_preview_wizard_form').id,
#                 'type': 'ir.actions.act_window',
#                 'context': context,
#                 'target': 'new',
#                 'flags': {'form': {'action_buttons': False}}
#             }             
#             
        
        
        
    
    def action_change_theme_style(self):
        if self:
            return
            
#     @api.onchange('sidebar_style')
#     def _onchange_sidebar_style(self):
#         if self.sidebar_style == 'style_9':
#             if self.env.ref('sh_backmate_theme_adv.backmate_assets_backend_app_menu'):
#                 self.env.ref('sh_backmate_theme_adv.backmate_assets_backend_app_menu').write({'active':True})
#         else:
#             self.enable_list_footer_view_status_bar = False
#             if self.env.ref('sh_backmate_theme_adv.backmate_assets_backend_app_menu'):
#                 self.env.ref('sh_backmate_theme_adv.backmate_assets_backend_app_menu').write({'active':False})
                
                
#     @api.onchange('theme_style')
#     def onchage_theme_style(self):
#          
#         if self and self.theme_style:
#             selected_theme_style_dict = dict_theme_style.get(self.theme_style,False)
#             if selected_theme_style_dict:         
#                 self.update(selected_theme_style_dict)
            
 

    def write(self,vals):
        """
           Write theme settings data in a less file
        """
                 
        res = super(sh_back_theme_config_settings,self).write(vals)
        

        
        if self: 
            for rec in self:
                                       
                content = """   
$o-enterprise-color: %s;
$primaryColor:%s;
$primary_hover:%s;
$primary_active:%s;
$gradient_color:%s;
$secondaryColor:%s;
$secondary_hover:%s;
$secondary_active:%s;
$list_td_th:0.75rem !important;
 
$header_bg_color:%s;
$header_font_color:%s;
$header_hover_color:%s;
$header_active_color:%s;
 
$h1_color:%s;
$h2_color:%s;
$h3_color:%s;
$h4_color:%s;
$h5_color:%s;
$h6_color:%s;
$p_color:%s;
 
$h1_size:%spx;
$h2_size:%spx;
$h3_size:%spx;
$h4_size:%spx;
$h5_size:%spx;
$h6_size:%spx;
$p_size:%spx;
 
$body_font_color:%s;
$body_background_type:%s;
$body_background_color:%s;
$body_font_family:%s;
 
$button_style:%s;
$o-mail-attachment-image-size: 100px !default;
 
$sidebar_background_style:%s;
$sidebar_bg_color:%s;
$sidebar_font_color:%s;
$sidebar_font_hover_color:%s;
$sidebar_font_hover_bg_color:%s;
$sidebar_is_show_nav_bar:%s;
$sidebar_collapse_style:%s;
 
 
$separator_style:%s;
$separator_color:%s;
$icon_style:%s;
$o-community-color:%s;
$o-tooltip-background-color:%s;
$o-brand-secondary:%s;
$o-brand-odoo: $o-community-color;
$o-brand-primary: $o-community-color;
 
$is_button_with_icon_text:%s;
$is_button_with_box_shadow:%s;
 
$body_google_font_family:%s;
$is_used_google_font:%s;
 
$list_view_border:%s;
$list_view_is_hover_row:%s;
$list_view_hover_bg_color:%s;
$list_view_even_row_color:%s;
$list_view_odd_row_color:%s;
 
$login_page_style: %s;
$login_page_background_type: %s;
$login_page_background_color:%s;
$login_page_box_color:%s;
$theme_style: %s;
 
$is_sticky_form:%s;
$is_sticky_chatter:%s;
$is_sticky_list:%s;
$is_sticky_list_inside_form:%s;
 
$modal_popup_style:%s;
$tab_style: %s;
$tab_style_mobile: %s;
$horizontal_tab_style: %s;
$vertical_tab_style: %s;
$form_element_style: %s;
$search_style: %s;
$breadcrumb_style:%s;
$chatter_position:%s;
$loading_style:%s;
$progress_style:%s;
$progress_height:%s;
$progress_color:%s;
                """ % (
                     
                    rec.primary_color,
                    rec.primary_color,
                    rec.primary_hover,
                    rec.primary_active,
                    rec.gradient_color,
                     
                    rec.secondary_color,
                    rec.secondary_hover,
                    rec.secondary_active,
                     
                    rec.header_background_color,
                    rec.header_font_color,
                    rec.header_hover_color,
                    rec.header_active_color,
                     
                     
                    rec.h1_color,
                    rec.h2_color,
                    rec.h3_color,
                    rec.h4_color,
                    rec.h5_color,
                    rec.h6_color,
                    rec.p_color,
                     
                     
                    rec.h1_size,
                    rec.h2_size,
                    rec.h3_size,
                    rec.h4_size,
                    rec.h5_size,
                    rec.h6_size,
                    rec.p_size,                    
                     
                    rec.body_font_color,
                    rec.body_background_type,
                    rec.body_background_color,                    
                    rec.body_font_family,
                     
                    rec.button_style,
                     
                     
                    rec.sidebar_background_style,
                    rec.sidebar_background_color,
                    rec.sidebar_font_color,
                    rec.sidebar_font_hover_color,
                    rec.sidebar_font_hover_background_color,
                    rec.sidebar_is_show_nav_bar,
                    rec.sidebar_collapse_style,
                                         
 
                     
                    rec.separator_style,
                    rec.separator_color,
                    rec.icon_style,
                    rec.primary_color,
                    rec.primary_color,
                    rec.secondary_color,
                    rec.is_button_with_icon_text,
                    rec.is_button_with_box_shadow,                    
                     
                    rec.body_google_font_family,
                    rec.is_used_google_font,
                     
                    rec.list_view_border,
                    rec.list_view_is_hover_row,
                    rec.list_view_hover_bg_color,
                    rec.list_view_even_row_color,
                    rec.list_view_odd_row_color,
                     
                    rec.login_page_style,
                    rec.login_page_background_type,
                    rec.login_page_background_color,
                    rec.login_page_box_color,
                    rec.theme_style,                                         
                        
                    rec.is_sticky_form,
                    rec.is_sticky_chatter,
                    rec.is_sticky_list,
                    rec.is_sticky_list_inside_form,
 
                    rec.modal_popup_style,
                    rec.tab_style,
                    rec.tab_style_mobile,
                    rec.horizontal_tab_style,
                    rec.vertical_tab_style,
                    rec.form_element_style,
                    rec.search_style,
                    rec.breadcrumb_style,
                    rec.chatter_position,
                       rec.loading_style,
                    rec.progress_style,
                    rec.progress_height,
                    rec.progress_color,
                       )
                     
                 
                 
                IrAttachment = self.env["ir.attachment"]
                # search default attachment by url that will created when app installed...
                url = "/sh_backmate_theme_adv/static/src/scss/back_theme_config_main_scss.scss"        
                 
                search_attachment = IrAttachment.sudo().search([
                    ('url','=',url),
                    ],limit = 1)
                 
#                 print("\n\n\n\n theme datas ==>",content)
                                     
                # Check if the file to save had already been modified
                datas = base64.b64encode((content or "\n").encode("utf-8"))
                 
                if search_attachment:
                    # If it was already modified, simply override the corresponding attachment content
                    search_attachment.sudo().write({"datas": datas})     
                     
                else:
                    # If not, create a new attachment
                    new_attach = {
                        "name": "Back Theme Settings scss File",
                        "type": "binary",
                        "mimetype": "text/scss",
                        "datas": datas,
                        "url": url,
                        "public": True,
                        "res_model": "ir.ui.view",
                    }
 
                    IrAttachment.sudo().create(new_attach)                    
                                    
                                         
                # clear the catch to applied our new theme effects.
                self.env["ir.qweb"].clear_caches()
                 
        return res    
#     
#     
#       
