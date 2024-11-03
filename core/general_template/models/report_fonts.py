# -*- coding: utf-8 -*-
# Part of AppJetty. See LICENSE file for full copyright and licensing details.

import logging
import glob
import os

from reportlab import rl_config
from reportlab.pdfbase import ttfonts

from odoo import api, fields, models


_logger = logging.getLogger(__name__)

CustomTTFonts = []
# Search path for TTF files
TTFSearchPath = [
    '/usr/share/fonts/truetype',  # SuSE
    '/usr/share/fonts/dejavu', '/usr/share/fonts/liberation',  # Fedora, RHEL
    '/usr/share/fonts/truetype/*', '/usr/local/share/fonts'  # Ubuntu,
    '/usr/share/fonts/TTF/*',  # Mandriva/Mageia
    '/usr/share/fonts/TTF',  # Arch Linux
    '/usr/lib/openoffice/share/fonts/truetype/',
    '~/.fonts',
    '~/.local/share/fonts',

    # mac os X - from
    # http://developer.apple.com/technotes/tn/tn2024.html
    '~/Library/Fonts',
    '/Library/Fonts',
    '/Network/Library/Fonts',
    '/System/Library/Fonts',

    # windows
    'c:/winnt/fonts',
    'c:/windows/fonts'
]
BUILTIN_ALTERNATIVES = [
    ('Helvetica', "normal", ["DejaVuSans", "LiberationSans"]),
    ('Helvetica', "bold", ["DejaVuSans-Bold", "LiberationSans-Bold"]),
    ('Helvetica', 'italic', ["DejaVuSans-Oblique", "LiberationSans-Italic"]),
    ('Helvetica', 'bolditalic', [
     "DejaVuSans-BoldOblique", "LiberationSans-BoldItalic"]),
    ('Times', 'normal', ["LiberationSerif", "DejaVuSerif"]),
    ('Times', 'bold', ["LiberationSerif-Bold", "DejaVuSerif-Bold"]),
    ('Times', 'italic', ["LiberationSerif-Italic", "DejaVuSerif-Italic"]),
    ('Times', 'bolditalic', [
     "LiberationSerif-BoldItalic", "DejaVuSerif-BoldItalic"]),
    ('Courier', 'normal', ["FreeMono", "DejaVuSansMono"]),
    ('Courier', 'bold', ["FreeMonoBold", "DejaVuSansMono-Bold"]),
    ('Courier', 'italic', ["FreeMonoOblique", "DejaVuSansMono-Oblique"]),
    ('Courier', 'bolditalic', [
     "FreeMonoBoldOblique", "DejaVuSansMono-BoldOblique"]),
]


def list_all_sysfonts():
    """
        This function returns list of font directories of system.
    """
    filepath = []

    # Perform the search for font files ourselves
    searchpath = list(set(TTFSearchPath + rl_config.TTFSearchPath))
    for dirname in searchpath:
        for filename in glob.glob(os.path.join(os.path.expanduser(dirname), '*.[Tt][Tt][FfCc]')):
            filepath.append(filename)
    return filepath


class ReportFonts(models.Model):
    _name = 'report.fonts'
    _description = 'Fonts available'
    _order = 'family,name,id'
    _rec_name = 'family'

    family = fields.Char(string="Font family", required=True)
    name = fields.Char(string="Font Name", required=True)
    path = fields.Char(required=True)
    mode = fields.Char(required=True)

    _sql_constraints = [
        ('name_font_uniq', 'unique(family, name)',
         'You can not register two fonts with the same name'),
    ]

    @api.model
    def font_scan(self, lazy=False):
        """Action of loading fonts
        In lazy mode will scan the filesystem only if there is no founts in the database and sync if no font in CustomTTFonts
        In not lazy mode will force scan filesystem and sync
        """
        if lazy:
            # lazy loading, scan only if no fonts in db
            fonts = self.search([('path', '!=', '/dev/null')])
            if not fonts:
                # no scan yet or no font found on the system, scan the filesystem
                self._scan_disk()
            elif len(CustomTTFonts) == 0:
                # CustomTTFonts list is empty
                self._sync()
        else:
            self._scan_disk()
        return True

    def _scan_disk(self):
        """Scan the file system and register the result in database"""
        found_fonts = []
        for font_path in list_all_sysfonts():
            try:
                font = ttfonts.TTFontFile(font_path)
                _logger.debug("Found font %s at %s", font.name, font_path)
                found_fonts.append(
                    (font.familyName, font.name, font_path, font.styleName))
            except Exception as ex:
                _logger.warning(
                    "Could not register Font %s: %s", font_path, ex)

        for family, name, path, mode in found_fonts:
            if not self.search([('family', '=', family), ('name', '=', name)]):
                self.create({'family': family, 'name': name,
                             'path': path, 'mode': mode})

        # remove fonts not present on the disk anymore
        existing_font_names = [
            name for (family, name, path, mode) in found_fonts]
        # Remove inexistent fonts
        self.search([('name', 'not in', existing_font_names),
                     ('path', '!=', '/dev/null')]).unlink()

        return self._sync()

    def _sync(self):
        """Set the customfonts.CustomTTFonts list to the content of the database"""
        CustomTTFonts = []
        local_family_modes = set()
        local_font_paths = {}
        for font in self.search([('path', '!=', '/dev/null')]):
            local_family_modes.add((font.family, font.mode))
            local_font_paths[font.name] = font.path
            CustomTTFonts.append(
                (font.family, font.name, font.path, font.mode))

        # Attempt to remap the builtin fonts (Helvetica, Times, Courier) to better alternatives
        # if available, because they only support a very small subset of unicode
        # (missing 'č' for example)
        for builtin_font_family, mode, alts in BUILTIN_ALTERNATIVES:
            if (builtin_font_family, mode) not in local_family_modes:
                # No local font exists with that name, try alternatives
                for altern_font in alts:
                    if local_font_paths.get(altern_font):
                        altern_def = (builtin_font_family, altern_font,
                                      local_font_paths[altern_font], mode)
                        CustomTTFonts.append(altern_def)
                        _logger.debug("Builtin remapping %r", altern_def)
                        break
                else:
                    _logger.warning("No local alternative found for builtin font `%s` (%s mode)."
                                    "Consider installing the DejaVu fonts if you have problems "
                                    "with unicode characters in RML reports",
                                    builtin_font_family, mode)
        return True

    @classmethod
    def clear_caches(cls):
        """Force worker to resync at next report loading by setting an empty font list"""
        CustomTTFonts = []
        return super(ReportFonts, cls).clear_caches()
